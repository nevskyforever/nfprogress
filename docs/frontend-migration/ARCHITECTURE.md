# nfprogress frontend migration architecture

## Goals and current boundary

Vue/Ionic is the supported interface over a shared, Qt-free application layer.
Historical PySide6 source remains only for behavior and pickle compatibility;
it is not built or published. Ownership is per subsystem, so SQLite and PKL
currently coexist. Neither the API nor the frontend reads PKL directly; the
Python compatibility layer does so for PKL-owned domains.

```text
Vue/Ionic clients
    ├── Web / Capacitor ── HTTPS ─────────────┐
    └── Tauri 2 ── local Nuitka sidecar ─────┤
                                             v
                    FastAPI ── services ── compatibility domain model
                                      │                 │
                                      └──── repositories┘
                                                │
                         ┌──────────────────────┴──────────────────────┐
                         v                                             v
              PKL compatibility stores                         SQLite database
              (projects and game authoritative)          (settings/Notes authoritative;
                                                         projects/game mirror)
```

### Current transitional desktop architecture

```text
Desktop Vue/TypeScript
   ├─ Rust/Tauri ───────────────→ SQLite
   │                               ├─ settings authoritative
   │                               └─ notes authoritative
   └─ local FastAPI/Python sidecar
       ├─ SQLite authoritative settings/Notes compatibility operations
       └─ PKL authoritative projects/stages/progress and game
```

Tauri still launches the Python/Nuitka sidecar for project mutations,
statistics, game, filesystem integrations and map compatibility workflows.
Notes ordinary CRUD/order and ordinary settings commands already have a direct
Rust/SQLite path.

### Target desktop architecture

```text
Vue / TypeScript
       ↓
TypeScript Core
       ↓
Rust / Tauri storage boundary
       ↓
SQLite
```

The target removes the local FastAPI sidecar, Nuitka packaging and runtime PKL
reads. A separately deployed FastAPI/Python server may remain for Web/cloud;
that server decision is independent of the desktop target.

For the new desktop read path the boundary is:

```text
                         READ
                          ↓
                 ┌── SQLite (healthy) ──┐
                 │                      ↓
Vue → ProjectReadRepository → TypeScript Core
                 │
                 └── API → Python

                         WRITE
                          ↓
Vue → API → Python → PKL → SQLite mirror
```

The Python core wraps proven logic in `engine.py`, `game.py`, and
`game_data.py` rather than rewriting its formulas. Keeping `Project`, `Stage`,
`Gamer`, and `Buff` at their legacy module paths is deliberate: existing pickle
payloads encode those paths, and moving them would require a data migration
without improving the service boundary. The service and API layers, including
these compatibility domain modules, have no PySide6 or UI imports; a subprocess
regression test enforces that Python-only boundary.

## Source boundaries

| Area | Legacy source | Shared/new source | Boundary |
| --- | --- | --- | --- |
| Projects, stages, progress, statistics, streaks | `engine.py` | `nfprogress/core/services/projects.py` + `frontend/src/core/statistics` | TypeScript owns verified pure calculations and some desktop reads; Python/PKL remains authoritative for mutations, progress history and streak/freeze state |
| Storage | `engine.py`, `game.py` | `nfprogress/core/repositories/storage.py` | Explicit data root, in-process/cross-process locking, atomic legacy files |
| Game rules | `game.py`, `game_data.py` | `nfprogress/core/services/game.py` | `Gamer` remains authoritative; commands return JSON-safe projections |
| Desktop orchestration | `main_UI.py`, `game_UI.py` | FastAPI routers and Vue pages | UI validation and rewards move behind application commands |
| Project notes | legacy `project_notes` in `engine.py`/PKL | `nfprogress/core/sqlite/notes.py` + `nfprogress/core/services/notes.py` | SQLite is authoritative; PKL records are compatibility input only, while map documents remain transitional Python-owned data |
| Mind maps | `engine.py`, `mindmap.py`, `mindmap_assets/` | notes service plus Vue adapter | Notes are SQLite-authoritative, but map normalization, combined maps and XMind import still use Python/API |
| Settings | `engine.py`, Qt settings dialog | `nfprogress/core/services/settings.py` | Backend exposes only allow-listed, platform-applicable keys |
| Localization/help | `localization.py`, `translations_catalog.py`, `help_content.py` | content service, exporter, Vue locale/help clients | Russian catalog and `HELP_SECTIONS` remain canonical |
| Word/Scrivener | `engine.py`, `scrivener_parser.py`, Qt workers | `nfprogress/core/services/integrations.py` | Desktop paths or explicit `.docx` upload; progress still uses project service |

## Source layout

```text
nfprogress/
  core/
    services/          # application use cases, no Qt imports
    repositories/      # storage boundary and explicit data-dir context
    serialization/     # JSON-safe projection helpers
backend/app/
  main.py              # FastAPI app factory and desktop sync lifecycle
  routers/             # thin HTTP adapters
  schemas.py           # Pydantic request and selected response models
frontend/
  src/
    core/projects/       # framework-independent, side-effect-free calculations
    api/               # the only HTTP transport implementation
    components/        # reusable Vue single-file components
    composables/       # platform, theme, network, and runtime behavior
    platform/          # guarded local platform capabilities and Canvas export
    layouts/           # adaptive desktop/mobile application shell
    pages/             # projects, notes, game, integrations, help, settings
    router/             # shared Web/Tauri/Capacitor routes
    stores/             # Pinia locale/theme/notifications and client state
    types/              # stable TypeScript contract
  src-tauri/            # Tauri 2 shell and sidecar lifecycle
  android/              # Capacitor Android project
  ios/                  # Capacitor iOS project
```

`scripts/export_frontend_content.py` can deterministically export the Python
catalog and help data to `frontend/src/i18n/generated/` for drift checks. The
runtime deliberately reads the same data from the content API instead of
shipping a second independently consumed locale catalog.

## Dependency direction

Pure project calculations are a lower-level dependency and import no Vue,
Pinia, API, platform, DOM, filesystem, or storage code. They accept explicit
dates and return JSON-safe values; an infinite goal is represented by the
existing `infinite` flag and `null`, never JavaScript `Infinity`.

```text
Vue SFC pages/components
    ↓
Pinia stores and composables
    ↓
typed API modules (`frontend/src/api/`)
    ↓
FastAPI routers and Pydantic request validation
    ↓
application services
    ↓
legacy-compatible domain models
    ↓
repositories and explicit filesystem integrations
```

There is one frontend request implementation in `frontend/src/api/client.ts`.
Tauri supplies a runtime base URL and session token; Web/Capacitor supply the
remote base URL. Feature modules do not scatter direct `fetch()` calls or use a
different desktop contract.

## Stable identifiers and JSON contract

- Projects use `Project.project_id`; stages use `Stage.stage_id`.
- Notes and custom awards expose stable IDs. Mind-map nodes retain the current
  canonical map identifiers.
- Canonical status, unit, item, buff, challenge, specialization, and session
  keys remain unchanged even when display names are localized.
- Infinite goals use an explicit `infinite` flag and JSON `null`, never JSON
  `Infinity`.
- Dates and datetimes cross the API boundary as ISO 8601 strings.
- Project names, stage names, custom awards, file paths, note content, and other
  user data are never translated.
- The frontend never receives Python instances or pickle payloads.

Pydantic validates command input and page-facing response envelopes for
projects/integrations, content/settings, notes/maps, and complete game
state/catalog/commands. Mind Elixir documents, unknown legacy inventory
metadata, and history/result payloads deliberately retain JSON-safe extensible
fields rather than pretending their compatibility format is closed.

## Persistence and data safety

`data.pkl` remains authoritative for projects/stages/progress and `gamer.pkl`
remains authoritative for game. Settings are authoritative in the `settings`
table of `nfprogress.db`; `settings.pkl` is a retained legacy/import artifact
and does not affect runtime after cutover. Notes are authoritative in the
`notes` table; legacy note records inside `data.pkl` do not affect runtime after
cutover. On Tauri desktop, TypeScript uses typed Rust settings commands with
fixed SQL.
Repository operations are serialized
by a shared process lock and a cross-platform advisory lock scoped to the
explicit data directory. Writes use the existing atomic replacement behavior.
Streak rewards keep an idempotency
marker in `gamer.pkl`, allowing a later request to repair the compatibility
marker in `data.pkl` without granting a second reward after an interrupted
two-file update.

Successful repository writes best-effort rebuild the SQLite mirror after the
PKL write. Mirror failures are logged and marked dirty; they never fail the
user operation or modify PKL. Full rebuild is explicit with
`python -m nfprogress.sqlite_migrate --data-dir PATH`; it creates a timestamped
backup first and rebuilds only PKL-owned domains. Authoritative SQLite domains
must be recovered from the database backup, not reconstructed from stale PKL.
`python -m nfprogress.sqlite_verify --data-dir PATH` performs a semantic
comparison for applicable legacy-owned domains and returns non-zero on
mismatch. Original pickle files are never deleted or rewritten in a SQLite
operation. Tests use temporary directories only.

Storage ownership is tracked independently of mirror health in the versioned
`storage_ownership` table. Current owners are `projects = pickle`,
`settings = sqlite`, `notes = sqlite`, and `game = pickle`. The projects domain
includes projects, stages, and progress entries. Mirror rebuilds synchronize
only pickle-owned domains, so a SQLite-owned domain is never overwritten by a
normal PKL rebuild. Settings and Notes have completed controlled cutovers;
Projects and Game have not.

```text
                 ownership
                    ↓

projects → pickle ─────→ SQLite mirror
settings → sqlite ─────── SQLite authoritative
notes    → sqlite ─────── SQLite authoritative
game     → pickle ─────→ SQLite mirror
```

Startup imports the complete legacy settings and Notes state, verifies each JSON
projection, and commits each ownership switch in its own SQLite transaction.
Notes are reconstructed from `Project.project_notes` and `Stage.project_notes`;
map-note text is materialized from `mindmap_data` while `source_map_id` and
`source_node_id` preserve the bidirectional link. Missing legacy note IDs get
deterministic UUID5 identities. PKL note records remain as compatibility data,
but are never read by the Notes service after the switch. Normal backups always
include `nfprogress.db`. There is no restore wizard; a PKL-only legacy backup
is imported on startup when the Notes ownership row is still `pickle`.

Python selects `SQLiteNotesRepository` after cutover and uses PKL only for
project/stage metadata and map documents. Tauri exposes fixed parameterized
Notes commands with a fixed DB path, ownership and healthy-mirror relation
guards, and no database creation or arbitrary SQL. Native map/XMind operations
remain API-only during this phase so Mind Elixir normalization stays in Python.
Legacy PKL data is retained only for PKL-owned domains and a future explicit
import/recovery path; it is not a target desktop runtime store.

The command checks `mirror_state.sync_status = 'healthy'` and runs fixed
`SELECT` statements for projects, stages, and progress entries. A
storage-neutral mapper reconstructs the API `Project` DTO, using `payload_json`
only for fields not yet normalized. Missing, unhealthy, malformed, or
unavailable SQLite data falls back to the API. Manual project ordering remains
API owned because the mirror does not yet contain `project_order`.

The historical UI still has direct read-modify-write sequences that do not
acquire the repository's cross-process transaction lock. It is unsupported and
must not be run against the same data directory as FastAPI/Tauri. Tauri itself
enforces one desktop backend owner.

## FastAPI application layer

The application factory creates one repository and the project, notes, game,
settings, content, and document-integration services. Thin routers expose:

- `/health` and generated OpenAPI;
- project/stage CRUD, lifecycle, progress, statistics, and the shared
  all-project writing-day summary;
- project-note and normalized Mind Elixir data;
- complete commands used by the game workspace;
- settings, language catalogs, localized help, and the versioned user
  agreement;
- desktop synchronization and explicit uploaded `.docx` workflows.

Domain errors are normalized centrally. Mutating game responses contain
server-computed state and rewards; client-supplied XP, coins, inventory counts,
or achievement outcomes are never accepted.

## Runtime transports

### Web and Capacitor

Web, iOS, and Android receive the FastAPI origin through
`VITE_API_BASE_URL`. They use the same typed client and require a separately
deployed HTTPS backend. Ordinary CPython is not embedded in Capacitor.

Remote clients cannot pass arbitrary server-side local paths. A user may
explicitly select and upload a `.docx`; the backend validates archive size,
counts symbols, and applies the total through `ProjectService`, including its
normal progress and game rules. Remote Scrivener-project upload is not
implemented because a browser selection does not provide the persistent local
directory access expected by that workflow.

The Web output includes responsive pages and a manifest. The hosting layer
must provide HTTPS, any required authentication, and history fallback to
`index.html`. There is no offline mutation queue or service-worker claim in the
current implementation.

### Tauri desktop sidecar

Tauri reserves an ephemeral `127.0.0.1` port and generates a random per-run
session token. It launches the target-triple-named Nuitka sidecar with the
loopback address, port, token, and owning Tauri PID, waits up to the configured
startup window for `/health`, and publishes connection details to the webview
through one Rust command.

Normal Tauri shutdown kills the stored child handle. The Python sidecar also
watches the parent PID and exits when the native process disappears, preventing
an orphan after a Tauri crash. The token is not persisted, hard-coded, or
included in the Vite bundle. The backend rejects a desktop/session-token bind
outside loopback.

Tauri permissions are limited to core window behavior, explicit file dialogs,
allow-listed HTTP/HTTPS external links, update check/install, and application
restart. Direct filesystem paths are consumed only by the local Python
integration service after the user has selected them.

### Signed desktop updates

Official Windows desktop releases compile with `NFPROGRESS_UPDATER_ENABLED=1`; local
and debug builds omit it and expose no updater UI. A release-only Tauri config
overlay embeds the public updater key and the HTTPS GitHub Releases
`latest.json` endpoint. The frontend checks after startup and once per hour,
offers a manual check in Settings, displays download progress, and delegates
installation and restart to the Tauri updater plugin.

Tauri requires its own minisign-style update signature and verifies it before
install. It is a free application-owned key pair, not a commercial Windows
publisher certificate. The Windows workflow creates the static manifest only
after the updater artifact exists and never publishes the historical
self-replacing ZIP/updater executable. The sidecar retains stable product and
version metadata and omits onefile payload compression.

### Desktop background synchronization

The desktop backend owns an asynchronous lifecycle task. Once per minute it
reads the `background_synch` setting outside the event loop. When enabled for
the first time or when the effective writing day changes, it runs every
configured active Word/Scrivener source with `asyncio.to_thread`. One broken
source is returned as an item-level failure and does not stop other sources or
the worker. The task is cancelled and awaited during backend shutdown.

This worker is deliberately absent from Web, iOS, and Android. Those clients
have no automatic access to local manuscripts.

## Vue/Ionic application

The adaptive shell exposes these real routes:

```text
/projects
/projects/:projectId
/projects/:projectId/notes
/game
/integrations
/help
/settings
```

The project workspace covers search, sorting/filtering, project and stage
lifecycle, all existing progress units, deadlines, structured statistics,
browser-native 1080 × 1080 progress-card export, and the optional
core-calculated all-project writing-day summary. Finite projects and stages use
the same Canvas renderer; its menu has separate image-clipboard and local
PNG-save actions, so one action never silently becomes the other.
The card is rendered wholly in the client and never sends manuscript or note
content to the backend. Its own filter
and sort choices are persisted under explicit frontend UI-state keys, while
historical preference keys remain untouched for data compatibility.
Notes use autosave and the existing `#карта` synchronization rules. Game
commands refresh authoritative server state after mutation. The integrations
page changes behavior by platform capability: local paths and Scrivener on
desktop, explicit `.docx` upload elsewhere. Direct sources are snapshotted
before application: missing, stale, unreadable, future-dated, or changing
sources preserve both progress and the configured binding. Help searches the
canonical localized section tree. Settings expose language, theme, writing-day
start, notification duration, game mode, the infinite shared project, global
streak, the all-project daily total, inventory category, and desktop background
synchronization. The shared notification stack consumes the stored duration.
The global notification center reads persisted bank and streak events through
the same API contract, keeps unread/read history server-side, and never
translates stored user-facing event text in the browser.
Before Vue routes render, bootstrap reads those preferences and presents the
shared versioned agreement gate when acceptance is missing.

## Developer data parity

Source-mode `main_UI.py` imports `engine` with `dev_mode=True`. The import
refreshes every top-level pickle store in `get_app_data_dir()/test_data` from
the working copy and then routes reads and writes to that test copy. The API
CLI exposes the same
behavior through `--dev-data`; it calls `engine.sync_test_data()` and passes
the resulting directory explicitly to `PickleRepository`. `Run Web.sh` uses
this flag, while a Tauri debug build adds it to the sidecar arguments. Release
Tauri bundles do not add the flag and retain their normal per-user app-data
path. An explicit `--data-dir` remains available for isolated empty test
fixtures and cannot be combined with `--dev-data`.

The Vue workspace deliberately preserves the legacy application's central
interaction cues while modernizing layout and responsiveness: projects use
circular progress indicators, progress entry is presented as a prominent
"new entry" action, and notes remain paper-like colored cards. A project-local
sync action first discovers all effective project bindings. The in-place data
refresh deliberately keeps the workspace mounted during synchronization. For a staged
project, this means every stage: existing Word/Scrivener sources run together
with the same semantics as the legacy PySide6 action, rather than requiring a
user to reconnect or choose the particular configured stage. When no binding
exists, the workspace deep-links to `/integrations` with stable project and
stage IDs so setup starts in the correct context.

Stages are responsive circular-progress tiles. Selecting one opens a focused
stage route with the same project command contract, fixing progress,
statistics, notes, and actions to that stable stage ID while the parent project
remains the persisted owner of the data.

The design uses Vue single-file components and CSS design tokens, with separate
wide-screen navigation and touch navigation. Semantic labels, live command
feedback, visible focus styles, scalable text, minimum touch targets, and
reduced-motion rules are part of the shared layer. Browser zoom is not disabled.

## Mind Elixir integration

The existing `mindmap_assets/` editor remains the implementation. A Vite plugin
copies the required assets into the public output. A Vue component owns the
editor frame, while a TypeScript adapter calls the existing initialization,
serialization, focus, and event functions on `window.nfprogressMindMap`.

Every saved map passes through the notes API and the server-side
`engine.normalize_mindmap_data()` validation before persistence. This removes
the Qt WebView and Python-to-JavaScript bridge from the new client without
inventing a second map format.

## Localization and help

Russian remains the canonical source language. `translations_catalog.py` and
the overrides in `localization.py` provide English, Spanish, German, French,
and Brazilian Portuguese. `ContentService` serves the canonical catalogs and
localized `HELP_SECTIONS` to the frontend at runtime.

`scripts/export_frontend_content.py` creates deterministic locale/help JSON and
supports `--check` for drift detection; these generated artifacts are not an
independently maintained translation system. The source extractor also scans
Vue/TypeScript user-facing strings so new frontend text can enter the same
catalog-generation workflow. User data and canonical Russian game keys are not
translated.

## Game state and achievement evidence

The game frontend exposes overview/profile, buffs, freezes, writing sessions,
daily and weekly challenges, inventory/shop with its persisted category,
inspiration, creative events,
specializations/mastery, skills, quests, cabinet/relics/sets, custom awards,
and bank operations. Python remains the source of truth and reserializes state
after every command.

There is no independent legacy `Achievement` model to migrate. Legacy quest
badges are created by `quest_award()` in `game_data.py` as ordinary `Item`
objects with canonical category `Награды`; `ITEM_REGISTRY['Награды']` is the
registry, and `Gamer.items['Награды']` is the persisted ownership evidence. The
new UI preserves that evidence through the quest state and inventory category.
Manuscript milestones and relic achievements remain the separate cabinet
projection. Custom user-defined awards are exposed by their own game commands.
Creating a duplicate generic "achievements" store would fork the actual legacy
data model, so none is introduced.

## Platform capability matrix

| Capability | Web | Tauri desktop | Capacitor iOS/Android |
| --- | --- | --- | --- |
| Shared FastAPI contract | Remote HTTPS | Local sidecar | Remote HTTPS |
| Local Python install for end user | Server-side only | No; bundled sidecar | No CPython in app |
| Direct local Word `.docx` path | No | Yes, after file dialog | No |
| Explicit `.docx` upload | Yes | Available through API contract | Yes |
| Scrivener binder/path sync | No | Yes | No |
| Automatic background file sync | No | Yes, when enabled | No |
| Native updater | Deployment-specific | Signed Tauri updater in official release builds | Store/distribution-specific |

## Security model

- The backend validates every progress, reward, inventory, challenge, session,
  bank, and custom-award mutation.
- User manuscript and note text is not included in normal request logging.
- Desktop listens only on loopback and requires the random session header.
- Allowed CORS origins are explicit. A non-loopback CLI bind requires
  `--allow-remote` and is intended only behind an external HTTPS/authentication
  boundary.
- `VITE_*` values contain public transport configuration only, never secrets.
- The API dependency boundary can accept future authentication without
  changing feature routes, but no account system is claimed today.

## Remaining platform debt

The following behavior remains incomplete or platform-specific:

- a real `.doc` reader, if that obsolete Word format is again made a supported
  product workflow (the current API accepts `.docx`);
- full browser-driven Playwright coverage of the critical end-to-end flows;
- a Windows CI execution with repository updater keys, plus macOS,
  iOS, and Android store/notarization verification.

PySide6 and its old updater remain historical source, not a supported fallback.
Compatibility classes whose module paths are encoded in existing pickle files
must remain until a separately tested data migration makes them unnecessary.

## Architectural decisions

1. Preserve pickle during parity instead of combining UI migration with an
   irreversible data migration.
2. Wrap the proven `Project`, `Stage`, note, and `Gamer` behavior rather than
   duplicating formulas in TypeScript.
3. Use one HTTP contract for all clients; desktop connection discovery changes
   transport configuration, not API semantics.
4. Reuse Mind Elixir and replace only its Qt transport bridge.
5. Restrict automatic local-file synchronization to the desktop sidecar.
6. Keep only the Python compatibility paths required to load existing data;
   build and publish the Tauri desktop application exclusively.
