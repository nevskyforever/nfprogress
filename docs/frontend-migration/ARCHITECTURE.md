# NFProgress — migration architecture

Baseline: `04b62c3970b22c43b9f604f79ee6de17243179f2`.

The supported user interface is Vue/Ionic in `frontend/`. PySide6 is legacy
source and is not part of the supported desktop architecture.

The detailed fast-track evidence, data inventory and compatibility window are
in [`FAST_TRACK_AUDIT.md`](FAST_TRACK_AUDIT.md). The implementation sequence is
in [`MIGRATION_PLAN.md`](MIGRATION_PLAN.md).

## Current desktop architecture

```text
Vue / TypeScript
   ├─ typed Rust/Tauri ───────────────→ SQLite
   │    ├─ Settings authoritative
   │    ├─ Notes CRUD/order authoritative
   │    └─ Projects read projection
   └─ HTTP client → local FastAPI/Nuitka sidecar
        ├─ Projects/Stages/Progress mutation → PKL → best-effort SQLite mirror
        ├─ Game → gamer.pkl → best-effort SQLite mirror
        ├─ Notes map/XMind compatibility operations
        ├─ Documents → documents.json
        └─ Word/Scrivener/background synchronization
```

Current ownership is deliberately explicit:

```text
projects/stages/progress = pickle authoritative
settings                 = SQLite authoritative
notes                    = SQLite authoritative
game                     = pickle authoritative
```

The v3 database is a shadow/read model for PKL-owned domains. It is not a
lossless copy of the pickle envelope. In particular, the project projection
omits actual `synch`/`last_synch` bindings and does not contain top-level
`project_folders`, notifications or global streak state. Documents are stored
in `documents.json`, which is currently not included by the backup routine.

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

The desktop target does not start FastAPI, Python, Nuitka or a PKL runtime in
normal operation. FastAPI/Python can remain as a separately deployed Web/cloud
backend, with its own server storage and lifecycle.

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

The existing Python mirror and sidecar are not permanent target layers.

## Storage and migration rules

SQLite migrations currently run in Python through
`nfprogress.core.sqlite.connection.open_database()` and schema v3. Rust opens
the database but does not yet apply those migrations. F1 must close that gap.

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
| Word | TS `mammoth`/`docx` conversion, Python local path/count | TS conversion plus Rust local file/hash boundary |
| Scrivener | Python XML/RTF/filesystem parser | Rust package/XML/RTF parser and worker |
| Documents | Vue/Tiptap + Python `documents.json` | SQLite document repository + Rust file boundary |
| Background sync | FastAPI lifespan task and Python services | cancellable Rust worker with explicit locks/events |
| Web/cloud | remote FastAPI contract | independent server deployment; not a desktop blocker |

Mind Elixir does not justify a Python bridge: the editor is already
JavaScript-based, and normalization/reconciliation are portable data rules.
XMind parsing is isolated enough for a direct bounded Rust port. Filesystem-
heavy Word/Scrivener behavior belongs in Rust; existing TS DOCX dependencies
can be reused where parity tests confirm the result.

## Startup and packaging boundary

Current Tauri setup in `frontend/src-tauri/src/lib.rs` reserves a loopback port,
creates a token, starts `nfprogress-backend`, waits for `/health`, and exposes
the sidecar URL to the webview. `tauri.conf.json` includes
`binaries/nfprogress-backend` as `externalBin`; build scripts compile it with
Nuitka.

F6 removes the sidecar child state, token/port health flow, backend connection
command, `externalBin`, sidecar build artifacts and mandatory Python startup.
Direct Tauri commands open/upgrade SQLite and expose migration status. Web and
Capacitor keep their remote API client independently.

## Backup and recovery boundary

Final backup/restore covers SQLite, Documents records/content, unknown JSON
metadata and a manifest of external files with hashes and timestamps. Restore
validates in a clean profile before activation and retains the previous
profile. A corrupt SQLite database is not repaired by copying a stale mirror;
legacy import is explicit recovery. PKL files remain untouched until recovery
and rollback tests have passed.
