# NFProgress — migration status

Updated: 2026-09-04

This status distinguishes implemented application features from authoritative
storage ownership. A feature marked done does not mean Python/PKL has already
left the desktop runtime.

## Completed migration foundations

- [x] SQLite schema and versioned migration runner.
- [x] Shadow mirror, ownership table, mirror health and verifier.
- [x] Explicit data roots, process/advisory locking and atomic PKL writes.
- [x] SQLite database included in backups.
- [x] TypeScript pure project calculations.
- [x] TypeScript pure statistics subset and parity tests.
- [x] Read-only SQLite project repository through Rust/Tauri.
- [x] Complete SQLite project read model, including persisted project ordering
  and safe fallback for incomplete ordering.
- [x] Settings controlled cutover to SQLite.
- [x] Notes controlled cutover to SQLite, including stable IDs and map metadata.
- [x] P2 typed project metadata/order boundary; Projects remain PKL-authoritative.

## Current ownership

```text
projects/stages/progress = pickle authoritative
settings                 = SQLite authoritative
notes                    = SQLite authoritative
game                     = pickle authoritative
```

| Domain | Owner | Current desktop path | Migration state |
| --- | --- | --- | --- |
| Projects/stages/progress | PKL | SQLite read projection; typed metadata/order desktop commands call the Python authoritative service; API remains for compatibility mutations | P2 boundary, not cut over |
| Settings | SQLite | typed Rust commands for ordinary settings; API for coupled transitions | cut over |
| Notes | SQLite | typed Rust CRUD/order; API/Python for map/XMind compatibility operations | cut over |
| Game | PKL | API/Python service and PKL persistence | not cut over |

## Feature implementation status

| Area | Status | Actual boundary and remaining work |
| --- | --- | --- |
| Project calculations | done | Pure TypeScript calculations exist; persisted project rules remain Python-owned. |
| Statistics | partial migration | Pure subset exists, but the UI still requests the complete API response because freezes, streaks and other state are Python/game-owned. |
| Project read repository | read model complete | Healthy Tauri reads use the ordered SQLite mirror for projects, stages, and progress; API remains the fallback for stale, unhealthy, missing, or malformed mirror data. Projects remain PKL-authoritative. |
| Projects/stages/progress feature | implemented, not migrated | CRUD, lifecycle, units, goals, deadlines and statistics are API-backed over PKL. Project mutation side effects can update streak/game state. |
| Notes/Mind Elixir | storage cut over | Notes ordinary CRUD/order use SQLite; map normalization, combined maps, XMind import and map reconciliation remain API/Python-backed. |
| Settings | storage cut over | Ordinary settings use SQLite; project-coupled destructive transitions still use Python/API. |
| Game | implemented, not migrated | Profile, rewards, sessions, challenges, cabinet, inventory and notifications remain PKL/Python authoritative. |
| Word/Scrivener | implemented, Python-dependent | Local parsing, source snapshots and progress application run in the Python sidecar. |
| Documents | partial migration | Vue editor is TypeScript, but metadata, project relations and local integration workflows remain API/Python-dependent. |
| Background synchronization | Python-dependent | Desktop sidecar worker runs configured Word/Scrivener sources. |
| Backup/restore | mixed | DB is backed up with PKL; no complete SQLite restore wizard exists. |
| Desktop startup | Python-dependent | Tauri launches target-specific Nuitka FastAPI sidecar, waits for `/health`, then Vue connects. |
| Web/cloud | separate backend | Web and Capacitor use a separately deployed FastAPI HTTP backend; this is not a reason to retain Python in desktop. |

## Remaining dependency stages

1. **Audit and plan** — current stage; documentation only, ownership unchanged.
2. **P1 project read model** — complete project DTO, persisted ordering, effective
   dates and progress projections in SQLite without changing owner. **Complete**
   for the current read contract; this is not a Projects storage cutover.
3. **P2 project metadata/order boundary** — typed Rust commands and
   storage-neutral interfaces for non-progress project metadata and ordering.
4. **P3 progress/calculation boundary** — move progress history and exact
   writing-day/unit rules toward SQLite and TypeScript Core.
5. **P4 project/stage lifecycle** — migrate lifecycle, relations, deletion and
   backups after game/streak side effects have a single-source contract.
6. **P5 desktop integrations** — replace or isolate Word, Scrivener, documents,
   XMind, Mind Elixir persistence and background sync from Python.
7. **P6 game pure rules** — separate portable game calculations/catalogs from
   persistent `Gamer` state.
8. **P7 game persistence and events** — move game state to SQLite and make
   progress/reward effects transaction-safe across domains.
9. **P8 Python-free desktop runtime** — remove sidecar startup, FastAPI local
   dependency, Nuitka packaging and mandatory Python startup checks.
10. **P9 legacy recovery** — retain only an explicit, tested PKL importer and
    SQLite-native backup/restore path.

Projects migration is intentionally split across P1–P4. Game integration and
filesystem integrations are blockers for a safe final owner switch, not reasons
to make one oversized cutover.

## Python desktop dependency inventory

| Dependency | Why it remains | Target / blocker |
| --- | --- | --- |
| FastAPI sidecar | Current Tauri transport for project mutations, statistics, game, integrations and maps | Remove only after P2–P8 commands exist. |
| `engine.py` models | PKL class paths and project/progress/map compatibility | Replace with SQLite DTOs plus legacy importer. |
| `game.py` / `game_data.py` | Persistent game state and reward invariants | P6–P7; depends on project progress events. |
| Word/Scrivener parsers | Local filesystem synchronization | Rust implementation required for Python-free desktop. |
| Mind Elixir normalization/XMind | Combined maps and map-note reconciliation | TS/Rust map core or explicitly server-only import. |
| Background worker | Scheduled local manuscript sync | Rust worker with locking and lifecycle semantics. |
| PKL files | Projects and game are still authoritative | Remove runtime reads only after P4/P7; preserve importer if needed. |

## Platform state

- Web production build and remote API configuration are available; HTTPS,
  authentication and SPA fallback remain deployment concerns.
- Tauri macOS ARM/Intel app and sidecar checks are documented; Windows release
  and signing still require the appropriate CI/host credentials.
- Capacitor projects and sync exist; native iOS/Android builds remain
  toolchain-blocked on the audit host.
- Tauri cannot yet be called Python-free: `externalBin` still names
  `nfprogress-backend`, and `lib.rs` launches the sidecar.

## Next recommended stage

Do not start it automatically. The next implementation stage is **P3:
progress/calculation boundary**. P2 added only the typed metadata/order
boundary; lifecycle, progress, and game side effects remain in the compatibility
path.
