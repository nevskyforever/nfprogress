# NFProgress — F8 production migration matrix

Статус аудита: 2026-09-04, baseline `e49069834793fe3151fcedf14e7308a577f37ea1`.
Матрица описывает фактический результат текущего кода, а не желаемое
поведение. Legacy PKL никогда не читается Tauri: его читает только отдельный
migration/recovery helper.

F9 adds the qualified helper path for legacy profiles without changing the
Tauri authority model. The helper detects and previews a copy of the source,
emits MigrationBundle v1, and activates a verified SQLite v6 staging database.
Ambiguous/corrupt profiles remain manual recovery.

## Decision key

| Outcome | Meaning in F8 |
| --- | --- |
| direct seamless upgrade | Native app opens/updates the profile without a legacy decoder; all authority markers are already canonical. |
| bridge update required | A preceding Python production release must normalize/materialize data before Tauri can be installed. |
| explicit migration helper | User runs a separately packaged local helper; source files are retained and the helper emits/activates canonical SQLite. |
| web legacy converter | Only an isolated, opt-in service may decode PKL and return a MigrationBundle. |
| unsupported/manual recovery | No automatic source selection; user must choose a valid backup or manual recovery route. |

## Source-state matrix

| ID / source state | Current result | Required action | Authority after success |
| --- | --- | --- | --- |
| A. Fresh install | PASS | direct seamless | New schema v6, all four owners SQLite, empty Game aggregate |
| B. Current prepared SQLite install | PASS WITH LIMITATION | direct seamless only when schema v6, healthy mirror, all owners SQLite and document marker are present | Existing SQLite remains authoritative |
| C. SQLite v6 | PASS WITH LIMITATION | direct seamless if the v6 database is structurally/semantically valid and all non-SQLite state is already materialized; otherwise helper | Validated v6 SQLite |
| D. SQLite v5 | PASS WITH LIMITATION | native v5→v6 upgrade only for an already SQLite-authoritative profile; PKL-backed v5 needs helper | v6 SQLite after staged schema upgrade |
| E. SQLite v4 | bridge/helper required | v4 is a Projects substrate; it cannot prove complete Game/Documents state | v6 SQLite only after complete import |
| F. SQLite v3 | bridge/helper required | v3 projection omits envelope fields, bindings and documents | v6 SQLite only after complete import |
| G. Partial SQLite migration | unsupported/manual recovery | reject marker/table/relationship disagreement; restore a valid backup or run an explicit source-specific helper | No authority switch until verification |
| H. SQLite + stale PKL | PASS WITH LIMITATION | stale PKL is ignored when owners are SQLite; otherwise helper | SQLite; PKL remains recovery-only |
| I. SQLite + stale `documents.json` | PASS WITH LIMITATION | existing document rows win via migration marker/`INSERT OR IGNORE`; require marker in production qualification | SQLite documents; JSON retained as artifact |
| J. PKL-only installation | helper required | local helper, then trusted SQLite import; web converter is fallback only | SQLite v6 |
| K. PKL + `gamer.pkl` + `documents.json` | helper required | one complete multi-domain helper is required; current Tauri startup does not orchestrate it | SQLite v6 with documents/Game/settings/notes verified |
| L. Old backup | helper/manual recovery | validate legacy unsealed snapshot; upgrade only in staging; retain original | New validated SQLite profile |
| M. Corrupt SQLite | unsupported/manual recovery | explicit `database_corrupt`; never fall back to stale PKL | Valid restored backup or explicit import |
| N. Missing SQLite, no legacy files | PASS | direct fresh initialization | New empty SQLite v6 |
| O. SQLite with missing external files | PASS WITH LIMITATION | open internal document; expose `missing_external`; rebind explicitly | Internal SQLite document preserved |
| P. Restored backup | PASS WITH LIMITATION | checksum/integrity validation, staged schema upgrade, atomic activation | Restored SQLite; previous profile retained |
| Q. Interrupted migration | helper/manual recovery | use source fingerprint and pre-migration backup; retry only from unchanged source | Deterministic verified SQLite or unchanged old profile |
| R. Interrupted update | PASS WITH LIMITATION | retry signed updater; use installer rollback; do not downgrade schema blindly | Previous app or new app with same data root |

## Historical versions and minimum source

The migration runner has explicit SQL files for v1–v6. Qualification tests
construct a valid empty profile at each marker, validate it, then upgrade it to
v6. This proves the runner chain; populated historical fixtures still need to
be rehearsed from copies of real profiles.

The minimum *seamless* source is not a Python release number that can be proven
from repository metadata. It is this exact technical condition:

```text
schema_info.schema_version = 6
storage_ownership contains exactly projects/settings/notes/game with owner=sqlite
mirror_state.id=1 and sync_status=healthy
documents_json_migration.status=complete
project_order and stage/progress relations are valid and contiguous
SQLite integrity_check and foreign_key_check pass
```

The current production version is `5.3.9`, but its version number alone does
not establish this condition. Therefore no Python production version is
currently proven to upgrade seamlessly from PKL-backed state to Tauri.

## Canonical bundle boundary

`MigrationBundle` is version 1. Its actual sections are:

```text
dto_version
projects (with stages, progress, payload, extra_fields, bindings)
project_order
folders
project_metadata
root_extensions
source_manifest
optional game
optional documents
optional document_bindings
optional external_file_manifest
```

There are no `settings` or `notes` sections in this DTO. Settings and Notes
use their existing cutover APIs; claiming one bundle is a complete profile
would be incorrect until a multi-domain helper orchestrates those APIs and
verifies them together. Unknown top-level fields are rejected. Unknown fields
inside JSON payload/extensions are retained. A newer DTO version is rejected;
an older supported version must pass an explicit converter before import.

Validation occurs before the transaction: version, JSON size/depth/string
limits, stable IDs, duplicate IDs, project/stage ownership, complete order,
folder references, bindings, document relations, source metadata and JSON
values. The Projects import then replaces the Projects representation in one
SQLite transaction and switches ownership only after semantic readback.

## Legacy PKL and web converter policy

The recommended production path is Option B plus Option C:

1. offer a monotonic Python bridge release while the helper is being packaged;
2. ship a local migration helper for users with PKL-only or ambiguous profiles;
3. offer the opt-in Web Legacy Migration Service only as a fallback.

The Web service must receive only a validated MigrationBundle. PKL decoding is
an isolated worker concern and must never execute in the web process.
