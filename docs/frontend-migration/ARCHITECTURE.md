# NFProgress — migration architecture

F7 implementation baseline: `e49069834793fe3151fcedf14e7308a577f37ea1`.
F8 qualification is recorded in
[`F8_RELEASE_QUALIFICATION.md`](F8_RELEASE_QUALIFICATION.md) and is currently
`BLOCKED` for production rollout.

The supported user interface is Vue/Ionic in `frontend/`. PySide6 is legacy
source and is not part of the supported desktop architecture.

The detailed fast-track evidence, data inventory and compatibility window are
in [`FAST_TRACK_AUDIT.md`](FAST_TRACK_AUDIT.md). The implementation sequence is
in [`MIGRATION_PLAN.md`](MIGRATION_PLAN.md).

## Current desktop architecture (F7)

```text
Vue / TypeScript
       ↓ typed Tauri commands
Rust services and repositories
       ↓
SQLite + filesystem
```

Current ownership is deliberately explicit:

```text
projects/stages/progress = SQLite authoritative
settings                 = SQLite authoritative
notes                    = SQLite authoritative
game                     = SQLite authoritative
documents                = SQLite authoritative
external files           = user-owned synchronization peers
```

The v6 database is authoritative for the cut-over Projects, Game and Documents domains.
It adds typed folders, project/stage sync bindings, stable progress ordering,
extension payloads, Game provenance and retryable domain-event processing.
Legacy PKL is retained only as a recovery/migration artifact. The one-shot
canonical importer still reads legacy PKL and `documents.json` in migration
tooling; Documents and external files are not yet part of the authority
cutover. Documents are migrated from `documents.json` once at native database
open; the JSON file is retained as a recovery artifact and is not a normal
runtime source after its migration marker is committed.

F8 adds bounded local backup/restore and MigrationBundle validation primitives
for a separately packaged migration/recovery helper. They are not imported by
the Tauri runtime. A PKL-backed profile still requires that helper (or an
explicit bridge/Web conversion); a native SQLite error never falls back to a
stale PKL source.

## Target desktop architecture

```text
Vue / TypeScript
       ↓
TypeScript Core
       ↓ typed Tauri commands
Rust services and repositories
       ↓ transactions, filesystem and OS boundaries
SQLite + validated external user files
```

The normal desktop target starts no FastAPI, Python, Nuitka or PKL runtime.
Projects, Settings, Notes, Game, maps, Documents, Word, Scrivener and sync use
the typed Rust/Tauri boundary. FastAPI/Python remains a separately deployed
Web/cloud backend, and Python migration/recovery/oracle tooling is invoked only
outside normal desktop startup.

## Ownership model after cutover

Keep the four coarse domains, but make their aggregate contents explicit:

| Domain | Final contents | Authority |
| --- | --- | --- |
| Projects | projects, stages, progress, order, folders and project-local Word/Scrivener bindings | SQLite |
| Settings | preferences and settings-coupled configuration | SQLite |
| Notes | notes, canonical map-note relations and map payload reference | SQLite |
| Game | Gamer state, quests, rewards, notifications, global streak and event journal | SQLite/event journal |

Documents become a SQLite-backed record set with external files referenced by
validated path/hash manifests. Static Mind Elixir assets remain application
resources, not user data.

Projects should switch atomically as one storage domain. Lifecycle and progress
operations must validate and persist through the same Rust transaction boundary.
Game rewards do not have to be implemented before the Projects storage switch,
but F2 must record an idempotent progress/lifecycle event; it must not create a
second writer or claim that a deferred reward is already applied.

## Layer responsibilities

### TypeScript Core

- UI-independent unit conversion, rounding, progress, dates and statistics;
- canonical frontend domain models and typed repositories;
- pure Game, map and import normalization rules after parity fixtures exist;
- presentation-independent use-cases where a browser-independent test gives
  better coverage.

TypeScript must not be trusted as the only security boundary for desktop
mutations.

### Rust/Tauri

- SQLite schema migration/open checks and parameterized repositories;
- transactions, ownership guards, idempotency and durable event handling;
- trusted validation and typed commands;
- filesystem access, atomic writes, source snapshots, hashes and watchers;
- local DOCX/Scrivener/XMind boundaries and OS integrations;
- direct desktop startup and backup/restore orchestration.

Pure business rules do not move to Rust merely because SQLite lives there.

### Python

Python remains outside the target desktop runtime while it is useful as:

- Web/cloud FastAPI backend;
- behavioral oracle for parity fixtures;
- one-shot migration or recovery tooling until all supported profiles migrate;
- compatibility source for legacy PKL class paths.

The existing Python mirror and Web API adapters remain supported outside the
desktop runtime. They are not fallback paths for native failures and do not
read or write desktop PKL after the ownership switches.

## Storage and migration rules

SQLite migrations are shared SQL files through schema v6. Python's
`open_database()` remains available for Web and migration tooling, while the
Rust Tauri opener executes the same versioned migrations without Python.

The final release requires a separately tested one-shot importer for:

```text
PKL-only profile
current v3 mirror profile
settings/Notes already cut over
partial or corrupt database
restored backup
fresh profile
```

The importer reads legacy files without rewriting them, imports omitted
envelope/document/binding data, verifies IDs and relations, records checksums,
and atomically stages the new SQLite database. Failed or ambiguous migration
must stop with a diagnostic and recovery path; it must never fall back to a
second writer or silently discard PKL-only data.

## Data representation

Normalized columns provide constraints and query performance. `payload_json`
preserves extensible project/stage, Game and Note data, but is versioned input
to canonical repositories rather than an assertion of lossless pickle
serialization. Derived fields such as today goals, remaining amounts and
statistics summaries are rebuilt from canonical state, settings and the
writing-day clock.

Stable project, stage and progress IDs are preserved exactly, including IDs
deterministically repaired for old rows. Effective writing-day timestamps and
legacy list ordering are part of the compatibility contract. Unknown Note
metadata and JSON-safe Settings keys are preserved; unknown Project attributes
and top-level pickle fields need explicit importer rules.

## Feature boundaries

| Feature | Current dependency | Final boundary |
| --- | --- | --- |
| Projects/Stages/Progress | `engine.py`, `ProjectService`, PKL and Python sidecar | TS use-cases → typed Rust transactions → SQLite |
| Game | `game.py`, `game_data.py`, PKL and data-envelope side effects | TS pure rules → Rust commands/events → SQLite |
| Notes CRUD | Rust fixed SQL after Notes cutover | Retain direct Rust/SQLite path |
| Mind Elixir | JS editor, Python normalization/reconciliation | Existing JS editor + TS pure map core + Rust/SQLite |
| XMind | Python ZIP/XML importer | Rust bounded archive/XML parser + TS tree mapper |
| Word | TS editor conversion, Python local path/count | Rust bounded DOCX parser/generator and file/hash boundary |
| Scrivener | Python XML/RTF/filesystem parser | Rust bounded package/XML/RTF read/count boundary |
| Documents | Vue/Tiptap + Python `documents.json` | SQLite document repository + Rust file boundary |
| Background sync | FastAPI lifespan task and Python services | native Tauri timer → idempotent Rust batch command |
| Web/cloud | remote FastAPI contract | independent server deployment; not a desktop blocker |

Mind Elixir does not justify a Python bridge: the editor is already
JavaScript-based, and normalization/reconciliation are portable data rules.
XMind parsing is isolated enough for a direct bounded Rust port. Filesystem-
heavy Word/Scrivener behavior belongs in Rust. Existing TS DOCX dependencies
remain for Web/browser compatibility and are not used by native editor
import/export/synchronization.

## Startup and packaging boundary

F7 removes the former sidecar child state, token/port health flow, backend
connection command, `externalBin`, sidecar build artifacts and mandatory
Python startup. Tauri setup opens/migrates SQLite directly and initializes
native services. Web and Capacitor keep their remote API client independently.

## Backup and recovery boundary

Final backup/restore covers SQLite, Documents records/content, unknown JSON
metadata and a manifest of external files with hashes and timestamps. Restore
validates in a clean profile before activation and retains the previous
profile. A corrupt SQLite database is not repaired by copying a stale mirror;
legacy import is explicit recovery. PKL files remain untouched until recovery
and rollback tests have passed.

## F2 Projects ownership

F2 changes the local desktop ownership matrix to SQLite for Projects, Stages,
Progress, ordering, folders, bindings and extensions. The Tauri sidecar runs a
verified, idempotent `MigrationBundle` import before the ownership transaction;
healthy SQLite reads have no PKL/API fallback. Rust Tauri services own
validation, transactions and persistence, while Game/Notes/document effects
remain explicit boundaries. See `F2_PROJECTS_SQLITE_CUTOVER.md`.

## F3 Game ownership

F3 imports `gamer.pkl` and Game-owned envelope fields into a versioned
`game_state` JSON DTO, verifies semantic readback, and switches the Game owner
only after verification. The F2 outbox is consumed by deterministic rules in
the trusted Rust boundary (and by the transitional SQLite compatibility
consumer), with Game state and its processed marker committed together. See
`F3_GAME_SQLITE_CUTOVER.md`.

## F4 Game runtime completion

F4 moves the Vue Game adapter to explicit typed Tauri commands. Rust owns the
Game application service, transactional state transitions, strict request
DTOs, catalog projection, injectable RNG boundary, lottery, economy, XP/level,
inventory, sessions, bank operations, challenge/specialization mutations and
the pending domain-event consumer. Python remains a behavioral oracle, Web
backend implementation and migration/recovery source, not a normal desktop
Game dependency. See [`F4_GAME_RUNTIME_COMPLETION.md`](F4_GAME_RUNTIME_COMPLETION.md).

## F5 Mind Elixir/XMind boundary

F5 completes the development desktop boundary for maps:

```text
Vue/Mind Elixir → MindMapRepository → typed Tauri commands
  → bounded Rust map core → SQLite projects/stages payload_json
```

The persisted map remains the existing opaque `mindmap` JSON section inside
the owning Project or Stage payload. This avoids a second map authority while
preserving the Mind Elixir envelope, child order, stable node IDs, free nodes,
layout/style fields and unknown extensions. Only the root/node shape and the
editor-owned free-node/floating-node fields are bounded and normalized.

Map Notes remain separate rows in the SQLite `notes` table. A map note is
identified by `source_type=mindmap` and `source_node_id`; `source_map_id` is
updated from the map root ID and the system tag is `карта`. Map save and Note
content/delete mutations reconcile both records in one transaction. The
legacy Python normalizer/importer remains an oracle, Web implementation and
isolated migration input, not a normal Tauri dependency.

XMind import reads only `content.json` or `content.xml` directly from a ZIP in
Rust and returns structural sheets to Vue. It does not extract files, follow
links, fetch network resources or import attachments/images/relationships or
proprietary styling. Archive entry count, compressed input size, declared
uncompressed size, content size, sheet count, node count, depth and topic size
are bounded; unsafe paths and XML DTD/entity declarations are rejected.
Multiple sheets are presented to the user for explicit selection. See
[`F5_MINDMAP_XMIND_RUNTIME.md`](F5_MINDMAP_XMIND_RUNTIME.md) for the complete
audit and verification matrix.

## F6 Documents and integrations boundary

The development desktop path is now:

```text
Vue/Tiptap → typed TS adapters → typed Tauri commands
  → Rust DocumentService/FileService/WordCodec/Scrivener boundary
  → SQLite documents + user-owned external files
```

Schema v6 adds `documents`, `document_bindings`, `document_metadata` and
`document_migration_orphans`. The migration preserves existing IDs, derives a
deterministic ID from the stable project/stage scope when an old record has no
ID, stores structured Tiptap JSON with `tiptap-json/v1`, and places unknown
legacy fields in `extensions_json`. A marker makes the `documents.json`
conversion idempotent; stale JSON cannot overwrite SQLite on later startups.

Word is bounded DOCX ZIP/XML parsing and deterministic generation in Rust; it
does not invoke Office, fetch relationships or execute macros. Scrivener
supports the audited binder XML shape and RTF item counting under `Files/Docs`
or `Files/Data`, rejecting malformed XML, unsafe symlinks and oversized trees.
External sync uses SHA-256 plus internal revision and reports
`synced`, `local_changed`, `external_changed`, `conflict`,
`missing_external`/typed errors. Conflicts are never auto-resolved. Writes use
an fsynced temporary file and replacement; external files are never deleted by
document metadata lifecycle operations. The native 60-second polling command
coalesces unchanged hashes and records expected self-write hashes.

F6 preserves the FastAPI implementation for Web clients, the legacy Python
oracle and migration tooling. It does not remove global sidecar startup or
Nuitka packaging; those are explicitly F7.
