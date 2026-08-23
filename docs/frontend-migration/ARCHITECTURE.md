# nfprogress frontend migration architecture

## Goals and current boundary

The migration keeps the existing PySide6 application operational while a
shared, Qt-free application layer and Vue/Ionic clients are introduced. The
legacy pickle files remain authoritative during the parity phase. Neither the
API nor the frontend reads or writes pickle directly.

```text
Legacy PySide6 UI ───────────────┐
                                │
                                v
                    legacy-compatible domain model
                                ^          │
                                │          v
Vue/Ionic ── HTTP ── FastAPI ── services ── repositories
    │                                      │
    ├── Web                                └── atomic data.pkl/settings.pkl/gamer.pkl
    ├── Capacitor iOS/Android
    └── Tauri 2 ── local Nuitka Python sidecar
```

The Python core currently wraps proven logic in `engine.py`, `game.py`, and
`game_data.py` rather than rewriting its formulas. This is a compatibility
extraction, not yet a physical move of every domain class into `nfprogress/`.
The service and API layers have no PySide6 dependency; legacy Qt orchestration
may continue to call compatibility functions until its remaining workflows are
replaced and verified.

## Source boundaries

| Area | Legacy source | Shared/new source | Boundary |
| --- | --- | --- | --- |
| Projects, stages, progress, statistics, streaks | `engine.py` | `nfprogress/core/services/projects.py` | Stable-ID commands wrap the existing models and calculations |
| Storage | `engine.py`, `game.py` | `nfprogress/core/repositories/storage.py` | Explicit data root, in-process/cross-process locking, atomic legacy files |
| Game rules | `game.py`, `game_data.py` | `nfprogress/core/services/game.py` | `Gamer` remains authoritative; commands return JSON-safe projections |
| Desktop orchestration | `main_UI.py`, `game_UI.py` | FastAPI routers and Vue pages | UI validation and rewards move behind application commands |
| Project notes | `project_notes.py` | `nfprogress/core/services/notes.py` | Preserve save-compatible note records and `#карта` synchronization |
| Mind maps | `engine.py`, `mindmap.py`, `mindmap_assets/` | notes service plus Vue adapter | Keep server normalization and reuse Mind Elixir without the Qt bridge |
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

`data.pkl`, `settings.pkl`, and `gamer.pkl` remain the production persistence
format. Repository operations are serialized by a shared process lock and a
cross-platform advisory lock scoped to the explicit data directory. Writes use
the existing atomic replacement behavior. Streak rewards keep an idempotency
marker in `gamer.pkl`, allowing a later request to repair the compatibility
marker in `data.pkl` without granting a second reward after an interrupted
two-file update.

Tests and sidecar smoke checks use an explicit temporary data directory via a
context-local override, so they do not migrate real user files. No JSON or
SQLite conversion runs automatically, and original pickle files are not
deleted. Any future format migration must be a separate versioned operation
that first creates a timestamped backup, writes a new destination, validates
it, and leaves the source intact.

The legacy UI still has direct read-modify-write sequences that do not acquire
the repository's new cross-process transaction lock. The legacy executable and
the FastAPI/Tauri backend must therefore not edit the same data directory
concurrently. Tauri enforces one desktop backend owner, but developers must
also respect this rule when launching the legacy and new applications by hand.

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

Tauri permissions are limited to the core window behavior, explicit file
dialogs, and allow-listed HTTP/HTTPS external links. Direct filesystem paths
are consumed only by the local Python integration service after the user has
selected them.

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
the same Canvas renderer; image clipboard writes are attempted only where the
platform permits them and otherwise fall back to an explicit local PNG download.
The card is rendered wholly in the client and never sends manuscript or note
content to the backend. Its own filter
and sort choices are persisted under explicit frontend UI-state keys, while
legacy list preferences remain untouched for the PySide6 fallback.
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
| Native updater | Deployment-specific | Disabled until signed Tauri releases | Store/distribution-specific |

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

## Remaining legacy debt

The following behavior remains intentionally legacy-only or incomplete:

- the Qt update checker/installer and signed legacy release channel; native
  Tauri updates stay disabled until signed Tauri artifacts exist;
- a real `.doc` reader, if that obsolete Word format is again made a supported
  product workflow (the current legacy selector asks for `.docx`, as does the
  new API);
- the native macOS `NSUserInterfaceItemSearching` Help-menu integration (Vue
  has its own localized in-app help search);
- full browser-driven Playwright coverage of the critical end-to-end flows;
- Windows, macOS Intel, iOS, and Android native release builds and signing.

The PySide6 files cannot be removed until these gaps and platform verification
are addressed. Sequential access to the existing data keeps the legacy app a
valid fallback.

## Architectural decisions

1. Preserve pickle during parity instead of combining UI migration with an
   irreversible data migration.
2. Wrap the proven `Project`, `Stage`, note, and `Gamer` behavior rather than
   duplicating formulas in TypeScript.
3. Use one HTTP contract for all clients; desktop connection discovery changes
   transport configuration, not API semantics.
4. Reuse Mind Elixir and replace only its Qt transport bridge.
5. Restrict automatic local-file synchronization to the desktop sidecar.
6. Keep PySide6 as a supported fallback until every remaining workflow and
   target is verified.
