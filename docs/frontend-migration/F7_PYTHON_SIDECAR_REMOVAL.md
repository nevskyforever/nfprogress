# NFProgress — F7 Python sidecar and legacy desktop backend removal

F7 implementation baseline: `e49069834793fe3151fcedf14e7308a577f37ea1`.
This is an architecture/runtime milestone, not release qualification. F8
remains pending.

## Result

Normal desktop startup is now:

```text
Tauri
  → native SQLite open and migrations
  → Rust services/watchers
  → Vue/TypeScript window
```

The desktop bundle no longer declares or builds `nfprogress-backend`, has no
Nuitka backend step, and does not reserve a loopback port, negotiate a token,
poll `/health`, or manage a Python child process. Native failures are returned
as native errors; there is no fallback to the Web API.

On a genuinely empty data directory, the native startup initializer creates the
latest SQLite state, marks the four local authorities as SQLite-owned, creates
the healthy mirror row and an empty Game aggregate. If `data.pkl`, `gamer.pkl`,
`settings.pkl` or `documents.json` is present, startup leaves the migration
boundary unchanged; those recovery artifacts are never silently promoted.

## Dependency audit

| File/module | Caller | Purpose | Classification | F7 result / replacement |
| --- | --- | --- | --- | --- |
| `frontend/src-tauri/src/lib.rs` | Tauri setup | sidecar spawn, health, token and child lifecycle | desktop runtime | removed; direct `sqlite::open_database()` |
| `frontend/src/platform/runtime.ts` | Tauri bootstrap | backend URL/session discovery and sync timer | desktop runtime | runtime metadata command; native sync timer remains |
| `frontend/src/api/client.ts` | Web API adapters | HTTP base URL and request transport | Web/mobile | retained, without desktop session header |
| `frontend/src/api/*.ts` | platform adapters | Web compatibility API | Web | retained behind explicit Web branches |
| `frontend/src/infrastructure/projects/projectReadRepository.ts` | project store | native read fallback to API | obsolete desktop bridge | fallback removed; native errors propagate |
| `frontend/src/content/bundledContent.ts` | desktop content bootstrap | locale/help/agreement content | desktop runtime | bundled generated catalogs; Web API remains |
| `scripts/build-backend-sidecar.py` | release scripts/CI | Nuitka backend executable | obsolete packaging | removed |
| `backend_sidecar.py` | Nuitka entry point | packaged FastAPI launcher | obsolete packaging | removed |
| `scripts/configure-tauri-intel-python.sh` | Intel wrappers | Python/Nuitka environment | obsolete packaging | removed |
| `backend/`, `nfprogress/`, `engine.py`, `main_UI.py` | Web, migration, oracle and legacy tooling | Python application/runtime source | Web/migration/test | retained outside normal Tauri startup |
| `scripts/*.py` release helpers | local/CI build metadata | versioning, manifests and artifact checks | development/release utility | retained; not bundled or launched by desktop |

Remaining Python, FastAPI and token references in tests and backend modules are
Web/API contract, migration, recovery or oracle coverage. They are not imported
by Tauri startup. The generated Tauri schema still describes the generic shell
plugin vocabulary; the shell plugin is not a dependency of the application and
no shell capability is granted in `capabilities/main.json`.

## Packaging and CI

`frontend/src-tauri/tauri.conf.json` has no `bundle.externalBin` entry. The
macOS local build, Intel wrapper and Windows workflow build only the frontend
and native Tauri application. The workflow retains Python setup because its
Web/oracle tests still require Python, but it no longer installs Nuitka,
builds a sidecar, copies or signs a backend executable, or smoke-tests a
localhost service.

The updater's native process permission remains intentionally limited to the
existing exit/restart flow. Rust `Command` calls that remain are updater shell
helpers, not Python/backend launches.

## Compatibility boundary

Web remains `Vue/TypeScript → FastAPI/Python`, and legacy conversion remains:

```text
untrusted PKL → isolated migration/recovery helper → MigrationBundle → importer
```

PKL, `documents.json` and other legacy recovery artifacts are not deleted and
do not become authoritative again. A PKL-only installation still requires the
legacy migration path; that compatibility matrix and production rollout belong
to F8. Maintenance Bridge Updates on the current Python production line remain
allowed if testing finds an old-data gap.

F7 does not publish a release, alter updater manifests, redesign SQLite, or
begin F8 historical upgrade/backup qualification.

F8 qualification is now documented separately. The architecture remains
complete, but production rollout is blocked until a complete migration helper
or bridge path, cross-generation updater proof, fresh signed artifacts and
Windows qualification are available. See
[`F8_RELEASE_QUALIFICATION.md`](F8_RELEASE_QUALIFICATION.md).
