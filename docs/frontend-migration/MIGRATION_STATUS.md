# NFProgress — migration status

Updated for F9 against implementation baseline `e70ba022989d70d6ca4d8aaf4703486dad045999`
on 2026-09-04. F9 qualification is `BLOCKED — migration path qualified;
release engineering blockers remain`; the final implementation commit
is recorded after the qualification checks.

This status distinguishes implemented features from authoritative storage.
F1/F2 storage foundations and the F3 Game owner switch are implemented. The
Normal desktop runtime is Python-free after F7. FastAPI/Python remains for
Web, migration/recovery and oracle tooling outside normal Tauri startup.

## Current ownership

```text
projects/stages/progress = SQLite authoritative
settings                 = SQLite authoritative
notes                    = SQLite authoritative
game                     = SQLite authoritative
documents                = SQLite authoritative; documents.json is migration/recovery input only
Word/Scrivener/sync      = typed Tauri commands → Rust bounded filesystem services
```

| Domain | Current desktop path | Status |
| --- | --- | --- |
| Projects/stages/progress | Typed Vue/Tauri commands → Rust → SQLite, with durable Game outbox events | SQLite-authoritative; Python remains the web/compatibility adapter |
| Settings | Typed Rust SQLite commands | SQLite-authoritative; Web keeps its API adapter |
| Notes/maps | Typed Rust SQLite Notes CRUD/order plus typed map load/save/import | SQLite-authoritative; normal desktop map/XMind path is Python-free, Web remains API-backed |
| Game | Vue typed Tauri commands → Rust Game service → SQLite; Web keeps API adapter | SQLite-authoritative; normal desktop has no Python Game dependency |
| Documents | Vue/Tiptap → typed Tauri commands → Rust → SQLite | SQLite-authoritative; legacy JSON is not normal source |
| Word/Scrivener/sync | Tauri → bounded Rust DOCX/Scrivener/filesystem boundary | Python-free feature path; Web remains API-backed |

## Completed foundations

- versioned SQLite schema through v6, ownership table, mirror health and
  semantic verifier;
- explicit data roots, process/advisory locking and atomic PKL writes;
- SQLite Settings and Notes controlled cutovers;
- complete ordered Projects/Stages/Progress read projection;
- P2 typed metadata/order boundary;
- P3 typed manual progress add/delete boundary and parity-tested TS
  conversion/normalization/statistics helpers;
- typed Tauri DTOs and fixed SQL for current direct Settings/Notes/read paths;
- shared Python/Rust migration files, canonical Projects migration DTO,
  transactional/idempotent import, typed Rust Projects repository primitives,
  folders/bindings/extensions and Notes-safe FK policy.

F3 adds GameMigrationBundle v1, owner verification/guard, SQLite Gamer
encoding with unknown-field preservation, Game-owned notifications and
global/project streak materialization, plus atomic retryable outbox consumers
in Python compatibility and trusted Rust boundaries.

These foundations are retained. Documents and external-file manifests remain
F6 concerns; the SQLite backup now contains authoritative Game state.

## Audit conclusions

- `projects`, `stages`, `progress_entries`, `project_order`, Settings, Notes
  and broad Game JSON are present in SQLite under the conditions described in
  [`FAST_TRACK_AUDIT.md`](FAST_TRACK_AUDIT.md).
- Project folders, actual `synch`/`last_synch` bindings, unknown
  Project/Stage fields and stable progress order are now represented in v4.
- Notifications/global streak are now Game-owned in SQLite; F6 has moved
  `documents.json` records to SQLite and keeps external files as user-owned
  synchronization peers.
- A migration-only Python helper is selected for legacy PKL parsing. Rust does
  not execute arbitrary pickle object behavior and now runs the shared schema
  migrations at DB open.
- F8 adds a sealed application-state backup/restore primitive and strict bundle
  validation for that helper. It is not imported by the Tauri runtime.
- The F9 helper is the default explicit migration path. A Bridge Release is not
  required for regular rollout; it remains a fallback for users unable to run
  the separate helper. Neither path is invoked by normal Tauri startup.

## Known baseline Python failures

The suite at the F6 baseline reports `542 passed, 3 failed, 15 skipped,
2 subtests passed`.

| Test | Classification | Migration impact |
| --- | --- | --- |
| `tests/test_accessibility.py::test_ui_templates_expose_names_labels_and_tab_order` | Legacy PySide6 UI template: `lottery_ticket.ui` has focusable controls but no `<tabstops>` | Obsolete for Vue/Tauri; does not block desktop migration, but must be retired or fixed before claiming the full legacy suite is green. |
| `tests/test_api_game_contracts.py::test_openapi_exposes_game_state_catalog_and_command_models` | Game API schema contract: developer endpoint returns `DeveloperModeResponse`, while the test assumes all non-read paths are `GameCommandResponse` | Relevant to the Python oracle/API contract; resolve or explicitly narrow the test before F3 parity sign-off. |
| `tests/test_quests_catalog.py::test_week_symbol_quest_counts_last_seven_days` | Week quest boundary/date behavior does not match the test fixture | Relevant to F3 only; not a storage blocker, but must be fixed or retired before quest parity. |

The accessibility failure is legacy UI-only. The OpenAPI failure is a contract
test mismatch, not evidence of SQLite storage loss. The week quest failure is
the remaining relevant legacy-oracle issue and is recorded for parity follow-up.

## New roadmap status

| Milestone | Status | Risk / Codex recommendation |
| --- | --- | --- |
| F1 storage contract, Rust migrations and one-shot legacy importer | Complete (storage foundation) | Very High / Luna High; importer packaging/source matrix remains an F2 blocker |
| F2 Projects/Stages/Progress SQLite-authoritative cutover | Complete | Very High / Luna High; regression and baseline classification in `F2_PROJECTS_SQLITE_CUTOVER.md` |
| F3 Game SQLite/event cutover | Complete (development authority) | Very High / Luna High |
| F4 Game runtime completion | Complete (development desktop path) | Very High / Luna High; production upgrade remains separate |
| F5 Mind Elixir/XMind | Complete (development desktop path) | High / Luna Medium–High; production legacy-variant qualification remains F8 |
| F6 Documents/Word/Scrivener/background sync | Complete (development desktop path) | High / external-format and release qualification remain F8 |
| F7 Python-free Tauri sidecar/packaging removal | Complete (development desktop path) | High / release qualification remains F8 |
| F8 migration, backup/restore and release qualification | F8 blocked; F9 migration path qualified | Very High; cross-generation update and signing/Windows evidence remain |

## F9 migration helper

`nfprogress/migration_helper.py` is an explicit CLI/API boundary. It detects
fresh, PKL-only, mixed v3/v4/v5/v6 and prepared-v6 profiles read-only, statically
inspects pickle opcodes, converts Projects/Settings/Notes/Game/Maps/Documents
and bindings to MigrationBundle v1, validates the DTO, imports a staging v6
database, runs integrity/FK and semantic checks, and atomically activates only
after success. `scripts/build-migration-helper.py` produces the separate
PyInstaller artifact. The Tauri startup gate returns `migration_required` for
legacy data unless the prepared marker and all SQLite owners are complete.

P1–P3 are complete foundations and are absorbed into F1/F2. P4 is absorbed
into F2 with a durable Game event contract. P5 is split into F5 and F6. P6/P7
are completed by F3/F4. P8 is F7. P9 is split between F1 and F8.

## F6 implementation status

F6 moves the normal desktop Documents/integration path to SQLite and typed
Tauri commands. The Rust boundary owns document migration, stable IDs,
structured Tiptap JSON, SHA-256 file identity, bounded DOCX parsing/generation,
Scrivener binder inspection/read counting, atomic Word writes, conflict states,
and trusted idempotent progress events. A native 60-second polling task invokes
the Rust batch command; unchanged hashes are coalesced and self-writes record
the expected final hash. F7 removes the former global sidecar; Python remains
only in Web, migration/recovery and oracle paths.

## F1 boundary

F1 does not switch ownership, stop PKL writes, delete Python/sidecar/PKL, or
begin Projects/Game/Integration runtime cutover. The next milestone is F2 and
requires a separate explicit task.

## F2 boundary

F2 switches the local Tauri desktop Projects owner to SQLite only after
MigrationBundle verification. Normal desktop Projects reads/writes use typed
TS → Tauri → Rust → SQLite commands; PKL project access is guarded. Web remains
the independent FastAPI/Python adapter, Game is SQLite-owned, and document,
filesystem and Game-rule migrations remain future work. The durable outbox is
an explicit retry boundary, not distributed Game/Projects transactionality.

## F3 boundary

Game ownership is SQLite-authoritative. A failed verifier leaves the owner as
pickle; a second startup does not reimport PKL; and Game state plus event
processed marker commit together. F4 moves normal desktop Game reads and
mutations to typed Tauri/Rust commands. The Python Game service remains for
Web, migration/recovery and oracle tests only; other sidecar subsystems remain
until F7.

## Production Bridge Release Strategy

Production Python continues receiving maintenance and bugfix releases during
F3–F8. Additional bridge releases may monotonically normalize Game state,
materialize stable IDs or export a canonical MigrationBundle. Development
authority readiness does not imply production upgrade readiness: F8 names the
minimum seamless-upgrade version. Older profiles use the migration-only helper
or the sandboxed Legacy Migration Service, in the order prepared SQLite,
bridge-updated Python, temporary helper, then isolated web conversion.

## F5 status

F5 is complete for normal desktop development runtime. The desktop map path
has zero map HTTP calls and zero Python calls:

```text
Vue/Mind Elixir → storage-neutral MindMapRepository
  → load_map/save_map/import_xmind → Rust → SQLite
```

Project and Stage payloads retain the canonical opaque Mind Elixir JSON, while
Notes remain separate SQLite entities linked by stable `source_node_id` and
`source_map_id`. Map save, map-note reconciliation, Note content edits and
map-note deletion have explicit transaction boundaries. Stable IDs, ordering,
freeNodes, styles/layout and unknown JSON fields survive ordinary mutations.
The Rust XMind parser is structural-only, direct-from-ZIP, bounded against
archive/path/XML/resource abuse, and returns all sheets for explicit UI
selection. Python map code is retained for Web, migration and parity oracle
coverage. Full details are in `F5_MINDMAP_XMIND_RUNTIME.md`.
