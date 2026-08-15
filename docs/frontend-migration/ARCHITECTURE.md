# nfprogress frontend migration architecture

## Goals

The migration keeps the existing PySide6 application operational while a
shared Python application layer and a new Vue/Ionic client are introduced.
The legacy pickle files remain the authoritative persistence format during
the transition. Neither the API nor the frontend reads pickle directly.

```text
Legacy PySide6 UI ───────────────┐
                                v
                         Python domain model
                                ^
Vue/Ionic ── HTTP ── FastAPI ── application services
    │                           repository layer
    ├── Web / PWA                    │
    ├── Capacitor iOS/Android        └── existing atomic pickle files
    └── Tauri 2 ── local Python sidecar
```

## Current system boundaries

| Area | Current source | Classification | Migration boundary |
| --- | --- | --- | --- |
| Projects, stages, progress, statistics, streak calculations | `engine.py` | Mostly domain logic plus file-location/pickle concerns | Reuse models and calculations behind repositories and application services |
| Desktop orchestration | `main_UI.py` | Qt UI plus application workflows and platform integration | Move workflows into services; keep Qt as a compatibility client |
| Game state and calculations | `game.py`, `game_data.py` | Mostly domain logic with persistence calls embedded in some methods | Execute under repository storage context and expose typed commands |
| Game presentation | `game_UI.py` | Qt UI and some application orchestration | Move orchestration to game service; keep calculations in `Gamer` |
| Project notes | `project_notes.py` | Pure normalization/synchronization mixed with QObject/WebView UI | Provide a Qt-free notes service using the same save-compatible records |
| Mind maps | `engine.py`, `mindmap.py`, `mindmap_assets/` | Server normalization plus Qt bridge plus an existing JS editor | Keep Python normalization; host the existing Mind Elixir assets in Vue and replace the Qt bridge with a TypeScript adapter |
| Localization | `localization.py`, `translations_catalog.py` | Shared catalog with Qt runtime adapter | Export generated frontend locale JSON from the canonical Python catalog |
| Help | `help_content.py` | Pure canonical content consumed by Qt | Export/serve the same section tree to the frontend |
| Word/Scrivener | `engine.py`, `scrivener_parser.py`, `main_UI.py` | Pure readers plus Qt file selection/background workers | Move reads to integration service; platform-specific clients only choose/upload explicit files |
| Persistence | `engine.py`, `game.py` | Atomic pickle files in the application data directory | Hide behind repository; retain source files and add explicit backup/snapshot operations |

## Target source layout

```text
nfprogress/
  core/
    services/          # application use cases, no Qt imports
    repositories/      # storage boundary and explicit data-dir context
    serialization/     # JSON-safe projections of legacy domain objects
backend/app/
  main.py              # FastAPI application factory
  routers/             # thin HTTP adapters
  schemas/             # Pydantic request/response models
frontend/
  src/
    api/               # the only HTTP transport implementation
    components/        # reusable Vue SFC components
    composables/       # platform, theme, network and session behavior
    pages/              # responsive route-level views
    stores/             # Pinia state with server-authoritative mutations
    types/              # stable JSON contract
    i18n/               # generated locales and runtime adapter
  src-tauri/            # Tauri 2 desktop shell and sidecar lifecycle
  android/              # generated Capacitor Android target
  ios/                  # generated Capacitor iOS target
```

## Dependency direction

```text
Vue components
    ↓
Pinia stores / composables
    ↓
typed API client
    ↓
FastAPI routers + Pydantic schemas
    ↓
application services
    ↓
legacy-compatible domain models
    ↓
repositories / filesystem integrations
```

Qt modules are not imported by the service, repository, serialization, or API
layers. The legacy UI may call the same services incrementally, but it remains
free to use compatibility functions in `engine.py` until each workflow is
verified.

## Stable identifiers and JSON contract

- Projects use `Project.project_id`; stages use `Stage.stage_id`.
- Canonical status, unit, game item, buff, challenge, specialization, and
  session keys remain unchanged. Display text is a separate localized field.
- Infinite goals are represented by an explicit `infinite` flag and a JSON
  `null` goal, never by JSON `Infinity`.
- Dates and datetimes are ISO 8601 strings at the API boundary.
- Project names, stage names, custom awards, note content, and other user data
  are never translated.
- The frontend never receives Python objects or pickle payloads.

## Persistence and data safety

The first production API continues to read and atomically write `data.pkl`,
`settings.pkl`, and `gamer.pkl`. Repository operations are serialized by a
shared process lock and a cross-platform advisory lock scoped to the explicit
data directory. Streak rewards keep an idempotency marker in `gamer.pkl`; this
allows a later request to repair the compatibility marker in `data.pkl` without
issuing the reward twice if a process stops between the two atomic replaces.
Tests and sidecar smoke checks use an explicit temporary data directory through
a context-local override, so real user data is not touched.

The unmodified legacy UI still performs some direct read-modify-write sequences
outside the repository transaction. Until those callers are moved behind the
shared service, the legacy executable and the new sidecar must not edit the
same data directory concurrently. The packaged Tauri runtime enforces a single
backend owner; this restriction is also documented for development runs.

Any future durable JSON/SQLite migration must be a separate, versioned change:
create a timestamped backup first, write to a new destination, validate the
result, and leave the pickle source intact. JSON snapshots in this migration
are export/diagnostic artifacts, not a silent storage replacement.

## Runtime targets

### Web and mobile

Web and Capacitor clients obtain the remote HTTPS API URL from
`VITE_API_BASE_URL`. They use the same client and contract. Mobile never embeds
ordinary CPython. File access is limited to explicit browser/native selection
and upload.

### Tauri desktop

Tauri starts a bundled Nuitka Python sidecar on `127.0.0.1` using an available
ephemeral port. It generates an in-memory session token, passes it to the
sidecar through the child environment, waits for `/health`, and exposes the
connection details to the webview through one command. The child is terminated
when the application exits. The sidecar also watches the owning Tauri PID and
exits if the native process crashes, so a Nuitka onefile child cannot remain
orphaned. The token is not persisted or built into Vite.

The API accepts only explicitly configured origins and requires the session
header when a desktop token is configured. Tauri capabilities are kept to the
smallest set needed for connection discovery, file dialogs, and external links.

## Mind Elixir integration

The existing `mindmap_assets/` editor remains the implementation. A build-time
asset sync copies it into the frontend public output. A Vue component owns the
editor frame, while a TypeScript adapter calls `initialize`, `getDataString`,
`focusNode`, and save/event functions on `window.nfprogressMindMap`. Saved data
always passes through the FastAPI mind-map endpoint and
`engine.normalize_mindmap_data()` before persistence.

## Localization and help

Russian stays canonical. `scripts/export_frontend_content.py` exports all six
locale catalogs and the `HELP_SECTIONS` tree. Generated JSON is validated for
missing language files and canonical keys. This makes the Python catalog the
single translation source while allowing the browser runtime to remain free of
Python and Qt.

## Security model

- All project, progress, reward, inventory, challenge, and session changes are
  commands validated by Python.
- No reward amount sent by a client is trusted.
- User manuscript/note text is not logged by request handlers.
- Desktop listens on loopback only; remote deployments are expected to be
  terminated behind HTTPS.
- Authentication is represented by a replaceable dependency boundary, but no
  account system is introduced without product requirements.

## Architectural decisions

1. Preserve pickle during the parity phase instead of combining UI migration
   with an irreversible storage migration.
2. Wrap proven `Project`, `Stage`, `Note`, and `Gamer` behavior rather than
   reimplementing formulas in TypeScript.
3. Use one HTTP contract for all clients; desktop connection discovery changes
   transport configuration, not API semantics.
4. Keep Mind Elixir as the editor and replace only the Qt transport bridge.
5. Keep legacy PySide6 as a supported fallback until parity checks cover each
   migrated workflow.
