# NFProgress — fast-track migration audit

Audit baseline: `04b62c3970b22c43b9f604f79ee6de17243179f2` (2026-09-04).

This document is the evidence record for the fast-track replan. It supersedes
the old assumption that every transitional state must be releasable. It does
not authorize an implementation milestone.

## Executive decisions

1. The current production SQLite preparation is useful, but it is not a
   complete lossless export of the user profile. It is a projection, not a
   migration source for every field.
2. A direct upgrade to the final Python-free desktop is safe only if the final
   distribution contains a separately tested, one-shot legacy importer. The
   existing `python -m nfprogress.sqlite_migrate` command cannot be that
   mechanism because it requires Python and only rebuilds the current mirror.
3. The recommended fast path is no additional user-facing bridge release:
   ship a migration-only helper with the final release/update flow, keep it
   outside normal desktop runtime, and run it before the first Python-free
   launch. Rust is the preferred final implementation; a separately packaged
   Python legacy helper is an acceptable fallback only if it is not part of the
   running desktop and its packaging/recovery lifecycle is explicit.
4. If a standalone helper cannot be delivered and tested, the product must
   schedule an explicit bridge release. There is no safe silent fallback from
   missing SQLite fields to PKL.
5. The Projects cutover should be one ownership switch for projects, stages,
   progress, order, folders, and project-local bindings. Global streak and
   notifications should be moved into the Game/event transaction rather than
   creating a fifth ownership subsystem.

## Evidence inspected

The audit checked the five migration documents, SQLite migrations and
repositories, Python services and legacy models, Tauri commands/startup,
frontend repositories, document/integration code, packaging scripts, and the
existing Python test suite.

Important implementation facts:

- `CURRENT_SCHEMA_VERSION` is `3`; migrations `001_initial.sql` through
  `003_project_order.sql` are executed by Python
  `nfprogress.core.sqlite.connection.open_database()`.
- Rust currently opens `nfprogress.db`, but does not run those migrations.
  Normal startup therefore still depends on the Python sidecar to initialize
  or upgrade the database.
- `SQLiteMirrorRepository.sync_projects()` writes the explicit
  `serialize_project()` projection, not the complete pickle envelope.
- `serialize_project()` includes a rich `payload_json` for projects and stages,
  but omits `synch` and `last_synch`; it also cannot include top-level envelope
  values such as `project_folders` and notifications.
- `sync_game()` serializes `vars(gamer)` into `game_state.payload_json`, which
  is broad enough for the current Gamer fields but remains a JSON projection,
  not a pickle-compatible object graph.
- `documents.json` is an independent store. `PickleRepository.create_backup()`
  currently copies the three PKL stores and `nfprogress.db`, but not
  `documents.json` or referenced external files.
- `sqlite_verify` verifies only the selected owner projections. A healthy
  mirror therefore does not prove that omitted envelope fields, bindings,
  documents, or external files are recoverable from SQLite.

## Data inventory at the current release

“Present in SQLite” below means present in the current mirror or authoritative
table. It does not mean that the value is already SQLite-authoritative.

| User data | Present in SQLite now | SQLite representation | Current authority | Fast-track implication |
| --- | --- | --- | --- | --- |
| Projects | Yes, when mirror is complete/healthy | `projects` normalized columns plus full-ish `payload_json` | `data.pkl` | Import from the projection only after a parity check; retain PKL for omitted fields. |
| Stages | Yes, when mirror is complete/healthy | `stages` columns plus `payload_json` | `data.pkl` | Stable `stage_id`, parent relation, order-by-rowid projection must be checked. |
| Progress history | Yes, when mirror is complete/healthy | `progress_entries` columns plus `payload_json` | `data.pkl` | IDs, list order, totals, symbols, contribution and effective timestamp are available; no revisions/bulk history exist in the legacy model. |
| `project_order` | Yes | `project_order(project_id, position)` | `data.pkl` | The table is complete only after a healthy rebuild and contiguous-position validation. |
| Settings | Yes | `settings(key, value_json)` | SQLite after settings cutover | Unknown JSON-safe keys survive; legacy `settings.pkl` is not authoritative after cutover. |
| Project Notes | Yes | `notes` normalized records plus `metadata` | SQLite after Notes cutover | IDs, note content, tags, checklist, map-note links and revisions are available. |
| `mindmap_data` | Usually yes in project/stage `payload_json` | Nested JSON inside the project/stage payload | PKL project object | The full map is mirrored opportunistically, but map normalization/reconciliation still reads and writes PKL through Python. It is not an independent authoritative map store. |
| Game state | Yes, when game mirror is complete | `game_state.payload_json`, `schema_version = 1` | `gamer.pkl` | Broad JSON state is available for a port, but class behavior and coupled data-envelope effects still require parity/import rules. |
| Game notifications | No dedicated SQLite record | Stored in `data.pkl` top-level `notifications`; only exposed by Python GameService | `data.pkl` | Must be imported into the final Game/event store; cannot be reconstructed from `game_state` alone. |
| Global streak state | No dedicated SQLite record | `data.pkl` top-level fields such as `global_streaks` and reward markers | `data.pkl` | Must move with the progress/Game event contract before PKL writes stop. |
| Folders/catalog | No | `project_folders` is top-level in `data.pkl`; only `folder_id` is in project payload | `data.pkl` | Add to the Projects aggregate import and repository. |
| Project cover | Yes for current format | `cover_image` inside project `payload_json` as bounded data URL | `data.pkl` | No separate file migration is needed for current inline covers; validate size/type during import. |
| Integration bindings | Partial | `work_method` and `sync_available` are projected; actual `synch` path/type/item and `last_synch` are omitted | `data.pkl` | PKL or a migration helper is mandatory for configured Word/Scrivener sources. |
| Documents metadata/content | No | `documents.json` records, including Tiptap content and DOCX hashes/paths | `documents.json` | Include this file in migration and backup, or move it to SQLite before release. |
| External Word/Scrivener files | No | User-selected paths and files outside the data root | External filesystem | Migration verifies accessibility and preserves bindings; it must not copy or silently detach files. |
| Custom/unknown Note fields | Yes | Canonical `metadata` JSON | SQLite Notes | Preserve the metadata object during every port. |
| Custom/unknown Settings fields | Yes if JSON-safe | `value_json` keyed rows | SQLite Settings | Preserve unknown keys unless an explicit product policy retires them. |
| Custom/unknown Project fields | Not guaranteed | Not included by `serialize_project()` | `data.pkl` | Classify each legacy attribute before port; do not claim `payload_json` is lossless. |
| Custom/unknown Gamer fields | Broadly yes if JSON-safe | Recursive `vars(gamer)` projection | `gamer.pkl` | Compare JSON projection with pickle fixtures; non-JSON object semantics need explicit conversion. |
| Entity/progress IDs | Yes in projection | Project/stage/entry IDs | PKL, with deterministic repair for old rows | Preserve IDs exactly; do not regenerate on every import. |
| Timestamps | Partially | Entity, progress, Note, and map timestamps in payloads | Mixed PKL/SQLite Notes | Sync timestamps and some envelope timestamps are missing; preserve timezone/effective-writing-day semantics. |
| Schema versions | SQLite v3; Game payload v1 | `schema_info`, ownership rows, `game_state.schema_version` | SQLite metadata | Rust/final helper must apply and verify upgrades; current Rust path cannot do this yet. |

## Classification required by the final importer

### Normalized SQLite columns

`projects`, `stages`, `progress_entries`, `notes`, `settings`, ownership and
mirror metadata, and `project_order` have explicit columns. These columns are
good for constraints and queries, but they are not the complete user model.

### `payload_json`

Project/stage payloads contain goals, totals, statuses, dates, streak display
data, project notes, maps, cover data, folder IDs and UI-facing projections.
`game_state.payload_json` contains the recursive JSON-safe Gamer projection.
Notes contain a canonical record and an extensible `metadata` object. Payload
JSON must be treated as versioned input to a canonical importer, not copied
blindly into a new schema.

### Still PKL-only or not guaranteed by SQLite

The project envelope (`last`, `project_folders`, notifications, global streak
fields and any future unknown top-level fields), actual sync bindings and
`last_synch`, unprojected custom Project attributes, and exact Python object
semantics remain PKL-only. The authoritative Game state is also still PKL,
even though its broad mirror is available.

### Separate JSON/external filesystem state

`documents.json` is outside SQLite and outside the current backup copy list.
Linked DOCX/Scrivener content is outside the data root. Static Mind Elixir
assets are application resources, not user state. Current covers are embedded
data URLs, not external cover files.

### Derived/rebuildable state

`today_goal`, `planning_date`, `added_today`, `remaining`, statistics summaries,
catalog projections and other display values are rebuildable from canonical
state plus settings and the current writing day. They must not be the only
migration source. Map-note cards can be rebuilt from normalized map data, but
only after the canonical map itself is preserved.

## Existing-user upgrade decision

The currently released SQLite version is not sufficient as the sole migration
source. A healthy v3 database can seed most Projects/Stages/Progress/Game
records, Settings, Notes, IDs and maps, but it cannot prove recovery of
folders, top-level streak/notification state, integration bindings,
`documents.json`, unknown project fields, or external files.

Recommended direct upgrade:

1. The installer/updater creates a read-only snapshot of every available
   source: `nfprogress.db`, `data.pkl`, `settings.pkl`, `gamer.pkl`,
   `documents.json`, and a manifest of configured external paths.
2. A migration-only helper detects the source combination and imports the
   complete canonical model into the new SQLite schema. It uses SQLite values
   only where they are authoritative or where PKL parity proves the projection
   complete; otherwise it reads the legacy source.
3. The helper validates IDs, parent relations, order, JSON payloads, document
   keys, binding paths, timestamps, and source hashes. It writes no PKL.
4. It records migration status and source checksums, commits an atomic DB
   upgrade, and leaves old files untouched for rollback/recovery.
5. The Python-free app opens only the upgraded SQLite database. If migration
   is incomplete or ambiguous, startup stops with a recoverable diagnostic; it
   does not fall back to a second writer or silently drop fields.

This means no additional user-facing bridge release is needed in the
recommended plan, but the one-shot importer is a hard F1/release dependency.
Without it, a bridge release is required and must be an explicit product
decision.

### Existing-user migration matrix

| Source version/state | PKL present? | SQLite present/schema | Expected migration | Expected authoritative result | Recovery path |
| --- | --- | --- | --- | --- | --- |
| Old PKL-only installation | `data.pkl`, usually `settings.pkl` and `gamer.pkl` | Missing or no supported DB | Import the complete legacy envelope and stores; create the current schema | One new SQLite authority with Projects, Settings, Notes, Game and Documents data | Keep originals; restore from pre-import snapshot and rerun after repair |
| Current released mirror installation | Yes; required to recover omitted fields | `nfprogress.db`, schema v3, possibly healthy mirror | Verify v3 against PKL, import folders, envelope fields, bindings and documents, then upgrade | SQLite vNext contains the complete canonical aggregate; original PKL is read-only recovery data | If parity fails, stop and use source-specific diagnostic; never choose the incomplete mirror silently |
| Settings already cut over | `settings.pkl` may be stale | Settings owner `sqlite` | Treat SQLite settings as authoritative; validate, do not overwrite from stale PKL | Settings remain SQLite-authoritative; import only missing non-settings domains | Restore the DB snapshot or explicitly import a legacy settings backup |
| Notes already cut over | `data.pkl` note records may be stale | Notes owner `sqlite` | Treat SQLite Notes as authoritative; preserve IDs/metadata/map-note links | Notes remain SQLite-authoritative; project/map data is reconciled separately | Restore the DB snapshot; legacy notes are fallback input only when ownership is explicitly pickle |
| Partially migrated or corrupt DB | Any combination | Missing tables, invalid schema, bad JSON, unhealthy mirror or broken ownership rows | Snapshot all sources; validate DB; rebuild/import from the safest complete source in a staging DB | No active authority until verification succeeds; then atomically activate SQLite | User-visible recovery diagnostic, clean-profile restore, or explicit legacy import |
| Fresh install | No | Missing | Create schema, defaults, ownership rows and empty canonical state | Empty SQLite-authoritative profile | Recreate clean profile; no Python or PKL required |
| Restored backup | Depends on backup generation | DB and possibly PKL/Documents snapshot | Identify backup manifest/version, validate checksums, apply schema upgrade, import legacy pieces if needed | Restored SQLite snapshot is authoritative after verification | Retain current profile and offer rollback; do not overwrite in place before validation |

### Direct upgrade chain

For the recommended release the exact chain is:

```text
installed profile
  → snapshot DB + PKL + documents.json + external-file manifest
  → validate v3 SQLite when present
  → one-shot legacy/canonical importer
  → SQLite schema vNext migration
  → parity, relation, checksum and backup verification
  → atomic activation of SQLite authority
  → Python-free desktop startup
```

There is no safe chain of `v3 SQLite → vNext SQLite` for every user because
the current v3 projection omits data listed above. A pure SQLite upgrade is
allowed only after the importer has proved that the profile is complete and
has materialized all non-SQLite sources. If the final installer cannot run a
migration-only helper, the product must first publish a bridge that performs
that materialization; this is a fallback decision, not the recommended plan.

## Minimum legacy compatibility window

| Capability | Keep until | Classification |
| --- | --- | --- |
| Legacy PKL reads during one-shot upgrade | All supported source combinations pass importer and upgrade tests | Migration-only dependency |
| PKL reads for failed/incomplete DB recovery | SQLite restore and legacy recovery workflow are verified | Recovery-only dependency |
| PKL writes | Immediately before Projects/Game ownership switch, after a final backup and parity snapshot | Removable at cutover; never keep a hidden write fallback |
| Mirror rebuild from PKL | After final import, verifier, rollback and recovery tests pass | Remove from normal runtime; keep only as legacy tooling if useful |
| Python/FastAPI desktop sidecar | After every desktop feature has a direct TS/Rust path and startup has no sidecar caller | Runtime dependency to remove |
| Python web/cloud backend | No desktop milestone requires its removal | Separate web/cloud dependency; may remain |
| Nuitka sidecar build path | After the last desktop sidecar artifact is no longer shipped | Desktop packaging dependency to remove |
| PySide6 and legacy updater | Not part of supported Vue/Tauri runtime; remove only after pickle class paths are no longer needed by recovery tooling | Historical/recovery source |

## Earliest safe Projects cutover

The earliest safe point is after F1 and F2, not after P3 alone. P3 proves the
manual progress boundary and calculations, but its Tauri commands still call
the authenticated Python sidecar and Python writes PKL first.

F2 must provide one authoritative Projects aggregate containing:

- projects, stages, progress entries, IDs, list order and project folders;
- all create/update/delete/archive/complete/reopen/stage-transform operations;
- project-local Word/Scrivener binding metadata, even if file parsing is a
  later F5 concern;
- Notes cleanup for project/stage deletion through a transaction or durable
  command boundary;
- a durable event/outbox for progress and lifecycle effects consumed by Game;
- atomic validation against the selected project/stage and no write fallback to
  PKL.

Game rewards need not block the storage switch if F2 records an idempotent
domain event and does not pretend the reward is already applied. There must be
one writer for the Projects tables. Python may continue serving Web from its
own backend, but it must not mutate the desktop data root after the switch.

## Target ownership and layering

Keep the four coarse domains, with explicit aggregate coverage:

```text
Projects = projects + stages + progress + project_order + folders + bindings
Settings = settings and settings-coupled preferences
Notes    = notes and canonical map-note relations
Game     = Gamer state + notifications + global streak/reward event state
```

The final desktop path is:

```text
Vue / TypeScript
    ↓
TS repositories and use-cases
    ↓ typed Tauri commands
Rust services/repositories
    ↓ transactions, filesystem and OS boundaries
SQLite + external user files
```

TypeScript owns UI-independent calculations, domain models and
presentation-independent use-cases where they are easier to test. Rust owns
SQLite transactions, schema upgrades, filesystem access, watchers, local
parsers and trusted desktop validation. Pure rules do not move to Rust merely
because persistence does.

## Desktop dependency audit

| Feature | Current Python dependency | Target | TS library status | Can be postponed? |
| --- | --- | --- | --- | --- |
| Projects/stages/progress/lifecycle | `engine.py`, `ProjectService`, PKL | TS use-cases + Rust repositories/services | Existing TS calculation and repository boundaries | No for ownership; business parity is F2. |
| Game | `game.py`, `game_data.py`, PKL and data-envelope effects | TS pure rules + Rust/SQLite state and event transactions | No replacement yet; build from catalog/parity fixtures | No for final runtime, after Projects event contract. |
| Mind Elixir | Python normalization, reconciliation and map persistence | TS normalizer/editor adapter + Rust/SQLite map payload | Editor already JS; F5 native normalizer and repository are implemented | No for normal desktop; Python remains Web/oracle/migration. |
| XMind | `xmind_import.py`, Python ZIP/XML parser | Rust ZIP/XML parser and TS tree mapper | Rust `zip`, `quick-xml` and bounded parser are implemented | No for normal desktop; historical variants remain F8 qualification. |
| Word `.docx` | Python counting/local path service | TS `mammoth`/`docx` for conversion; Rust or TS for local file boundary/count | `mammoth` and `docx` already installed | Yes, until F6. |
| Scrivener | `scrivener_parser.py`, `striprtf`, Python filesystem | Rust archive/XML/RTF parser and worker | No existing TS parser dependency | Yes, until F6. |
| Documents | `documents.py`, `documents.json` | SQLite document repository; Rust file/hash/write boundary; TS Tiptap model | Tiptap model already exists | The editor can stay TS while storage moves. |
| Background sync | FastAPI lifespan task + `asyncio.to_thread` | Tauri/Rust worker, explicit lock, cancellation and per-source failures | Not applicable | Yes, but blocks sidecar removal. |
| Startup | Tauri sidecar health/token flow | Direct Rust DB migration/open and TS bootstrap | Not applicable | No for F7. |
| Web/cloud | FastAPI HTTP backend | May remain Python/FastAPI | Shared API can remain server-side | Independent of desktop. |

### Mind Elixir

The editor is already JavaScript-based. Python remains because
`engine.normalize_mindmap_data()`, combined-map split/compose logic, note
reconciliation and persistence still run in the Notes API. The direct path is
to port the pure normalization/reconciliation fixtures to TypeScript, store
the canonical map payload in the Projects/Notes SQLite contract, and use Rust
only for transaction and storage boundaries. Do not retain a Python bridge
solely because the editor assets are historical.

### XMind

The importer is isolated and uses ZIP plus JSON/XML tree parsing. Port its
bounded archive checks, title/tree validation, stable mapping and error
semantics to Rust, then map the result through the same TS Mind Elixir adapter.
Use parity fixtures for both `content.json` and `content.xml`, malformed
archives, limits, IDs and multi-sheet behavior.

### Word, Scrivener and Documents

Keep the document model/editor in TypeScript. Keep filesystem-heavy operations
in Rust: selected paths, atomic writes, source snapshots, hashes, stale/future
timestamp checks, file watching and worker cancellation. Use existing TS
`mammoth`/`docx` where it matches current behavior. Implement Scrivener
package/binder discovery, XML parsing and RTF symbol counting in Rust. Store
document records in SQLite and include their assets/paths in backup manifests.

## Startup and sidecar removal checklist

| Current feature | Current caller | Replacement milestone |
| --- | --- | --- |
| Reserve loopback port/session token | `frontend/src-tauri/src/lib.rs` setup | F7: remove both for local DB commands |
| `app.shell().sidecar("nfprogress-backend")` | Tauri setup in `lib.rs` | F7: delete startup branch and child state |
| `/health` readiness polling | `wait_for_backend()` | F7: replace with direct DB migration/open health |
| `backend_connection` and runtime base URL/token | `frontend/src/platform/runtime.ts`, API client | F7: local commands use typed `invoke`; remote API remains Web-only |
| Project metadata/order/progress commands | Rust wrappers calling API paths | F2: direct typed Rust commands/services |
| Notes map/XMind API paths | Vue Notes API and FastAPI notes router | F5: direct map/import repositories |
| Game API commands | Vue Game API and FastAPI game router | F4: direct typed Game commands |
| Documents API | Vue documents API and `ProjectDocumentService` | F6: SQLite/filesystem commands |
| Word/Scrivener sync API and minute task | integrations router and `backend/app/main.py` | F6: Rust worker |
| Sidecar child kill/watchdog | `stop_backend`, `backend_sidecar.py` | F7: delete with sidecar |
| Dev `--dev-data` sidecar mode | `backend/app/__main__.py`, Run scripts | Keep for Web/legacy tests; remove from desktop path |
| `externalBin` bundle entry | `frontend/src-tauri/tauri.conf.json` | F7: delete |
| Sidecar build and target scripts | `scripts/build-backend-sidecar.py`, Tauri build scripts | F7: delete desktop path; retain only separately documented migration-tool build if needed |

## PKL removal checklist

1. Add and test a complete importer for all supported source combinations.
2. Import and verify `data.pkl`, `gamer.pkl`, `settings.pkl`, `documents.json`
   and external-file manifest without mutating originals.
3. Switch Projects ownership only after every desktop Projects writer uses
   SQLite and the event/outbox contract.
4. Switch Game ownership only after its state, notifications, global streaks,
   rewards, quests and progress events are SQLite/event authoritative.
5. Stop normal desktop PKL reads and writes; do not leave a write-on-error
   fallback.
6. Stop mirror rebuilds from PKL in normal startup and ordinary writes.
7. Keep PKL class paths and a recovery importer until rollback and legacy
   backup restore are proven; classify that code as migration/recovery-only.
8. Verify a Python-absent desktop profile, including clean install, upgrade,
   restored backup and corrupted DB behavior.

## Backup and restore requirements

The final backup is an application snapshot, not just a DB copy. It contains:

- SQLite database plus schema/ownership/migration manifest;
- document records and embedded content;
- project/game/notes/settings data and unknown JSON metadata;
- a manifest of external files, paths, sizes, hashes and last-seen timestamps;
- version, source revision and integrity checksums.

Restore must write to a clean profile, validate the complete snapshot before
switching it into service, apply schema upgrades, report missing external
files without deleting bindings, and retain the prior profile for rollback.
Corrupt SQLite must not be overwritten by a stale PKL mirror; legacy import is
an explicit recovery action.

## F1 implementation update

The F1 storage audit confirmed the v3 gaps and materialized the Projects
substrate in schema v4. The v3 core tables remain compatible; v4 adds
`project_metadata`, `project_folders`, `project_bindings`,
`project_folder_members`, `project_extensions` and `progress_order`. Actual `synch`/`last_synch` data is
now represented as typed binding columns plus the original JSON-safe binding
payload. Unknown Project/Stage attributes and root extensions are preserved in
extension/metadata rows; valid Mind Elixir data remains in the entity payload.
Notes FKs are now RESTRICT so storage rebuild/delete cannot silently remove
SQLite-authoritative Notes.

The migration-only Python helper produces DTO version 1 and imports it in a
single idempotent transaction. A Rust restricted pickle parser was not added:
arbitrary pickle class behavior is unsafe and unnecessary for this substrate.
Rust embeds and executes the same SQL migration files as Python, rejects
future/corrupt schema metadata, and exposes typed internal repository
primitives. Normal Tauri still starts the legacy sidecar and Projects writes
still go to PKL until F2.

Remaining F2 blockers are the controlled ownership guard/cutover, complete
Projects business-lifecycle parity, explicit Notes/document relation cleanup,
and the durable Game progress-event contract. F3 remains responsible for
notifications, global streak and Gamer state; F6 remains responsible for
`documents.json` records and external-file manifests.

## F2 implementation update

The controlled ownership guard/cutover, scoped Projects lifecycle parity,
explicit Notes cleanup and durable Game event boundary are implemented.
`cutover_projects()` imports and verifies MigrationBundle v1 before switching
ownership; startup is idempotent and the old PKL is recovery-only. Typed Rust
commands cover project metadata/general update, creation/deletion, ordering,
folders, stage lifecycle and progress add/delete. Manual progress rejects
explicit synchronized work methods and sync bindings. Unknown fields, maps,
bindings and document references are preserved.

The complete mutation matrix, failure semantics and sandboxed legacy migration
service are recorded in `F2_PROJECTS_SQLITE_CUTOVER.md`.

## F3 implementation update

F3 is present in the current F4 starting HEAD and is an ancestor of it. The
remaining transitional Python Game façade was the blocker that required the
additional F4 milestone.

F3 moves Game authority to SQLite schema v5. The actual legacy Gamer inventory
is the 46-field `Gamer.__dict__`; it includes profile/economy, coefficients,
skills, health, buffs/debuffs, quests, bank, inventory/custom awards,
motivation/challenges/sessions, specializations/mastery/cooldowns,
manuscript journeys/cabinet, and durable reward markers. `data.pkl` separately
contains notifications, global streak state and project/stage streak evidence.

`GameMigrationBundle` v1 serializes these values as a versioned JSON payload;
unknown fields are retained as JSON or tagged legacy-object extensions. The
importer verifies canonical readback before changing `storage_ownership.game`.
On later startup the owner guard returns without reading `gamer.pkl` or
`data.pkl`. The old files remain recovery artifacts only.

F2 events are consumed deterministically in `(created_at,event_id)` order.
Game state and `processed_at/status` are committed in one SQLite transaction;
duplicate event IDs are harmless, failures retry with bounded diagnostics,
and the third failure becomes a retained poison event. `ProgressDeleted` is
non-reversible because the Python oracle does not claw back prior rewards.
Completion and deletion events preserve one-time reward evidence and stable
project references. The Rust trusted boundary uses the same event DTO and
pure transition contract.

This is development architecture readiness, not the final production upgrade
gate. A production bridge release remains allowed and must be monotonic; F8
will define the minimum seamless-upgrade version and the fallback to the
sandboxed Legacy Migration Service for older profiles.

## F4 implementation update

The supported desktop Game call path is now:

```text
Vue gameApi → TauriGameRepository adapter → explicit Tauri command
  → Rust GameApplicationService → SQLite transaction
```

The audited normal desktop operations are state/notifications/catalog,
developer-only controls, sessions, streak freeze, daily/weekly challenges,
inspiration and creative events, specializations, skills, quests, inventory
buy/sell/use, lottery, custom awards and bank products. They have explicit
command names and strict `deny_unknown_fields` DTOs. Rust consumes pending F2
events before reads and mutations, uses a transaction for each stateful
operation, retains tagged/unknown Gamer fields, and exposes typed error
classification.

The Web adapter still calls the Python API by design. The desktop adapter has
zero Game localhost HTTP calls and zero Python/pickle calls. The sidecar itself
remains in scope for Documents and integrations until F7. F4 does not start
Mind Elixir, XMind, Word, Scrivener, document storage or watcher migration.

Static catalog parity is checked against `game_data.ITEM_REGISTRY`; lottery
uses an injectable 5-of-30 RNG and persists its draw history. Production
Python bridge maintenance and the isolated Legacy Migration Service remain
separate from development runtime completion.

## F5 implementation audit

The map audit is now implemented at the desktop boundary.
`SQLiteNotesRepository` uses typed `load_map`, `save_map` and `import_xmind`
commands; the Web adapter continues to use the existing API independently.
Rust updates only the owning Project/Stage `mindmap` payload and reconciles
separate SQLite Notes in one transaction. Existing Python normalization and
XMind tests remain the oracle; the normal Tauri path does not invoke them. See
[`F5_MINDMAP_XMIND_RUNTIME.md`](F5_MINDMAP_XMIND_RUNTIME.md) for the operation
matrix, contract, limits, deletion semantics and verification results.

## F6 Documents/Word/Scrivener/filesystem implementation audit

The audited legacy runtime consisted of `ProjectDocumentService` storing
records in `documents.json`, `DocumentIntegrationService` mutating project
`synch`/`last_synch` fields and counting Word/Scrivener sources, and the
FastAPI lifespan task polling configured sources every 60 seconds. The Vue
editor had a 700 ms autosave, a five-second external check, a serialized
persistence queue, and protections against stale initial-load and save
responses. The persisted document fields were:

```text
project_id, stage_id, content, exists, updated_at, docx_path,
sync_state, last_synced_hash, last_synced_at, local_dirty, word_dirty,
symbols, has_content
```

F6 adds SQLite schema v6 with `documents`, `document_bindings`,
`document_metadata` and `document_migration_orphans`. Document content remains
structured Tiptap JSON (`tiptap-json/v1`). Existing IDs are retained; missing
IDs use SHA-256 of stable project/stage scope. Unknown legacy fields are kept
in `extensions_json`. The migration is transactionally marked and idempotent;
later stale `documents.json` content is ignored. Backups copy the legacy JSON
as recovery evidence and include an external binding manifest, while linked
user files are not copied or deleted implicitly.

| Operation | Native desktop target | Web compatibility | External side effect |
| --- | --- | --- | --- |
| create/open/list/save/rename/delete | typed Tauri → Rust → SQLite | existing FastAPI repository | metadata delete never removes user files |
| project/stage document relation | stable IDs; first-stage conversion preserves binding | existing service semantics | none |
| Word import/count/export | bounded Rust DOCX parser/generator | existing Python endpoint | only explicit selected output writes |
| Word binding/sync | Rust binding/hash/revision service | existing Python service | selected `.docx` read; atomic write on request |
| Scrivener inspect/sync | Rust binder/XML/RTF boundary | existing Python parser | source tree is read-only |
| external change/background sync | native timer → idempotent Rust batch; editor poll | Python lifespan poll | hash coalescing and self-write suppression |

DOCX is limited to 100 MiB input, 10,000 entries and 250 MiB declared
expansion. Traversal, malformed archives, DTD/entity constructs and non-DOCX
extensions are rejected; relationships are never fetched and macros are not
executed. Supported formatting is paragraphs, headings, bold/italic/
underline/strike, tabs and line breaks. Scrivener supports the observed
`project.scrivx`, root `.scrivx` and `binder.scrivproj` binder hierarchy plus
RTF files under `Files/Docs` or `Files/Data`; unsupported Scrivener metadata,
snapshots, research, comments, compile settings and attachments remain
outside the contract.

The feature-specific native command surface and remaining sidecar boundary are
documented in `F6_DOCUMENTS_INTEGRATIONS_RUNTIME.md`.

## F7 completion addendum

The preceding sections record the pre-F7 audit and intentionally contain
historical sidecar references. F7 completed that boundary: Tauri setup now
opens/migrates SQLite directly, `backend_connection` and session-token
plumbing are gone, `externalBin` is empty, and desktop build/CI scripts no
longer build or package Nuitka. `PlatformProjectReadRepository` does not fall
back from native SQLite errors to the API. Bundled locale/help/agreement
catalogs keep desktop bootstrap offline; Web API adapters remain supported.

Final classification is: Desktop normal runtime — zero Python process and zero
localhost FastAPI calls; Web/backend — Python retained; migration/recovery and
oracle — Python retained and explicitly invoked; release metadata helpers —
Python retained as development utilities; obsolete sidecar launcher/build
files — removed. Release qualification, upgrade matrices and production
readiness remain F8.
