# NFProgress — полный план миграции

Актуально после Notes cutover commit
`9862658b7eede1cbcce098ac4b255f5f7171d888`.

Этот документ описывает миграцию runtime и ownership, а не только наличие
готовых Vue/API экранов. `done` для feature означает реализованный workflow;
мигрированным считается только subsystem, для которого authoritative state и
mutations переведены на целевой storage.

## Целевая архитектура

### Desktop

```text
Vue / TypeScript
       ↓
TypeScript Core
       ↓
Rust / Tauri storage boundary
       ↓
SQLite
```

Desktop не должен требовать Python, FastAPI, Nuitka sidecar или PKL для
обычной работы. Legacy PKL importer может оставаться отдельным recovery/import
инструментом.

### Web и cloud

```text
Vue / TypeScript → HTTPS → server backend → SQLite
```

FastAPI/Python не удаляется только потому, что он больше не нужен desktop.
Будущий web/cloud backend может остаться Python/FastAPI либо быть заменён
отдельным server implementation; это не является desktop dependency.

## Текущая точка

```text
projects/stages/progress = pickle authoritative
settings                 = SQLite authoritative
notes                    = SQLite authoritative
game                     = pickle authoritative
```

```text
Desktop Vue/TS
   ├─ typed Rust → SQLite (settings, Notes CRUD/order, project reads)
   └─ FastAPI/Python sidecar → SQLite + PKL (остальные операции)
```

SQLite остаётся mirror для PKL-owned projects/stages/progress и game. Mirror не
имеет права перезаписывать SQLite-owned settings или Notes.

## Уже завершено

1. SQLite schema/migration runner, shadow mirror, ownership table, explicit data
   roots, locking, backup и verifier.
2. TypeScript Core для pure project calculations.
3. TypeScript Core для pure statistics subset; UI пока получает полный
   statistics contract через API из-за Python-owned freezes/streaks.
4. Read-only SQLite → Rust → TypeScript project repository с API fallback.
5. Settings cutover: import/verify/switch transactionally; `settings.pkl` —
   legacy/non-authoritative.
6. Notes cutover: canonical DTO, stable IDs, map metadata, transaction-safe
   import, SQLite Python repository, typed Rust CRUD/order, API fallback для
   Mind Elixir/XMind, lifecycle deletion handling.

## Runtime inventory и оставшиеся Python dependencies

| Subsystem | Current owner | Why Python is still required | Target | Blocker / stage |
| --- | --- | --- | --- | --- |
| Project/stage/progress mutations | PKL | `ProjectService`, legacy model, writing-day rules, validation and persistence run in Python; Vue sends mutations to API | TS Core rules + Rust SQLite commands/transactions | split storage and game side effects; stages P2–P4 |
| Project reads | PKL, SQLite mirror | desktop reads the complete ordered SQLite projection when healthy; API remains the safe fallback | complete SQLite read model including `project_order` | P1 |
| Statistics | derived from PKL progress | full response still includes Python-owned streak/freeze semantics | TS Core + SQLite progress/read model | P3 |
| Notes ordinary CRUD | SQLite | desktop direct path is Rust; Web/API compatibility remains Python | Rust SQLite + API server adapter | completed |
| Notes map/XMind | SQLite note state + PKL map document | `engine.normalize_mindmap_data`, combined maps and XMind parser/reconciliation are Python | Rust/TS map core and SQLite map/document state, or retained server adapter | blocks Python removal for map workflows; P5 |
| Settings | SQLite | project-coupled transitions (`inf_project`, global streak) still use API/Python | Rust transactions for all settings/project transitions | P4 |
| Game state/rules | PKL | `game.py`, `game_data.py`, rewards, sessions, streaks, cabinet and inventory | TS Core + SQLite game tables/JSON DTO | depends on project/progress event contract; P6–P7 |
| Word `.docx` | project PKL via Python service | local file parsing and progress application run in Python sidecar | Rust/TS DOCX reader and project command boundary | blocks sidecar removal; P5 |
| Scrivener | project PKL via Python service | package/binder parsing, source snapshots and sync rules run in Python | Rust filesystem/parser service | blocks sidecar removal; P5 |
| Documents | PKL/API | document metadata and project relation are served by Python; browser editor is TS | SQLite document repository + Rust local-file boundary | relation contract; P5 |
| XMind import | API/Python | `xmind_import.py` and validation are server-side | TS/Rust importer or explicit server-only feature | blocks Python-free import; P5 |
| Background synchronization | Python sidecar | async worker calls Word/Scrivener services and applies progress | Rust background worker with explicit event/locking model | blocks sidecar removal; P5 |
| Startup | FastAPI/Nuitka sidecar | Tauri launches backend, waits for `/health`, obtains token/base URL | Tauri opens SQLite and initializes TS app directly | P8 |
| Backup/restore/import | mixed | backup copies PKL and DB; no complete restore wizard exists | SQLite snapshot/restore plus isolated legacy importer | recovery design; P8 |

Compatibility imports of `engine.Project`, `Stage`, `Gamer`, and `Buff` must
remain until all required legacy data can be read without those Python module
paths.

## Dependency-driven remaining stages

### Audit stage — current

Keep ownership unchanged. Maintain a dependency inventory, explicit desktop/web
boundary, and exit criteria. No runtime cutover belongs in this stage.

### P1. Complete SQLite project read model

Add stable representations for `project_order`, all project/stage fields used by
Vue, effective writing-day dates and progress projections. Verify read parity
without changing the project owner. P1 completes the SQLite project read model,
including persisted project ordering; it is not a Projects storage cutover.

### P2. Project metadata and ordering boundary

Move project ordering and non-progress metadata commands behind storage-neutral
interfaces and typed Rust commands. Keep project/stage lifecycle in compatibility
mode until relation, Notes cleanup, backup and game side effects are covered.

### P3. Progress and calculation boundary

Move progress entries, unit conversion, goals, deadlines, writing-day semantics
and pure statistics inputs to SQLite/TypeScript Core. Preserve exact legacy
rounding and dates. Define a durable progress event/transaction contract before
changing project ownership.

### P4. Project/stage lifecycle and cross-domain effects

Migrate create/update/delete/archive/complete flows, stage lifecycle, rename/move,
manual ordering, Notes relations, map relations and backup behavior. Project and
stage deletion must remove SQLite-owned Notes consistently. Do not switch owner
until game/streak side effects have a defined single source of truth.

### P5. Desktop filesystem and document boundary

Replace or isolate Python implementations for Word, Scrivener, document metadata,
XMind import, Mind Elixir map persistence and background synchronization. A
temporary API-only path is acceptable, but it cannot satisfy the final
Python-free desktop exit criteria. Verify local paths, stale/future sources,
atomic detach, map reconciliation and imports.

### P6. Game read model and pure rules

Separate pure calculations from persistent `Gamer` state. Port catalog lookups,
levels, rewards, challenges, sessions, motivation, mastery, cabinet and other
pure rules to TypeScript Core with canonical Russian keys unchanged. Keep game
owner PKL while parity tests and event inputs are built.

### P7. Game persistence and project event integration

Move game state to SQLite and make project progress/reward effects transactional
or event-driven. Verify that one progress action cannot update PKL game and
SQLite project state inconsistently. Only after this stage may project and game
ownership switches be completed.

### P8. Remove desktop Python runtime

Move remaining startup, settings transitions, backup/restore, imports and local
file operations behind Tauri/Rust. Remove FastAPI sidecar launch, `externalBin`
Python backend, Nuitka desktop packaging and mandatory Python startup checks.
Retain FastAPI as a separately deployed Web/cloud backend if desired.

### P9. Legacy retirement and recovery

Keep a separately tested PKL importer for existing users if required. PKL must
not be read as runtime state. Define SQLite backup restore, schema upgrades,
corruption recovery and migration diagnostics. Do not delete legacy data until
recovery and release rollback procedures are proven.

## Projects cutover blockers

Projects cannot be switched as one blind monolith while project progress still
triggers Python-owned game/streak updates. The safe decomposition is P1–P4,
followed by P5 filesystem relations and P6–P7 game integration. Specific checks:

- project/stage IDs and `project_order` must survive migration;
- progress entries must preserve unit conversion, effective writing day,
  deadlines, goals and statistics history;
- Notes and Mind Elixir relations must use IDs, not object identity or position;
- project/stage deletion must explicitly delete SQLite-owned Notes;
- game rewards, streaks, freezes, sessions and creative-rhythm state must not
  have a second authoritative copy;
- Word/Scrivener/document bindings and backups must remain recoverable.

Therefore Projects migration must be split into several stages, not implemented
as a single storage flip.

## Integration policy

| Integration | Transitional policy | Final desktop target | Blocks Python removal |
| --- | --- | --- | --- |
| Word `.docx` | Python sidecar/API | Rust/TS local parser and progress command | yes |
| Scrivener | Python sidecar/API | Rust parser and filesystem worker | yes |
| XMind | API/Python | TS/Rust importer or explicitly server-only Web feature | yes for local desktop import |
| Mind Elixir | TS editor, Python map normalization | TS/Rust canonical map core and SQLite persistence | yes while map edits require API |
| Documents | TS editor + Python metadata API | SQLite metadata and Rust file boundary | yes if desktop needs local sync |
| Background sync | Python only | Rust worker with explicit lock/event model | yes |

## Backup, restore and compatibility

`nfprogress.db` is already included in backups and contains authoritative
settings and Notes. During mixed mode, backups also retain `data.pkl`,
`settings.pkl`, and `gamer.pkl` for PKL-owned domains. The current repository has
no complete restore wizard; replacing an SQLite-owned database with a legacy
PKL-only backup must be an explicit compatibility import, never a silent startup
fallback. Future recovery must restore SQLite as the authoritative snapshot and
run PKL import only in a controlled, verified path.

## Final desktop exit criteria

- [ ] projects/stages/progress are SQLite-authoritative;
- [x] settings are SQLite-authoritative;
- [x] notes are SQLite-authoritative;
- [ ] game is SQLite-authoritative;
- [ ] all desktop business logic works without Python;
- [ ] imports/exports work without the Python sidecar, or are explicitly
  documented as server-only for Web;
- [ ] Word/Scrivener have non-Python desktop implementations;
- [ ] XMind import and Mind Elixir persistence work without Python;
- [ ] backup/restore is SQLite-authoritative and tested;
- [ ] startup does not launch FastAPI sidecar;
- [ ] Tauri `externalBin` Python backend is removed;
- [ ] Nuitka backend is absent from desktop builds;
- [ ] PKL is not used as runtime storage;
- [ ] legacy PKL import remains separately tested if retained;
- [ ] desktop tests pass without an installed Python runtime;
- [ ] Web/cloud backend contract is independently tested and documented.

## Rules for each cutover

Use a canonical DTO, controlled import, parity verification, transaction-safe
ownership switch, explicit owner guards, idempotent startup, no write fallback
to PKL after cutover, and focused cross-language tests. Never combine a storage
switch with unrelated UI refactoring or the next subsystem migration.
