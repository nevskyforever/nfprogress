# nfprogress

nfprogress is a progress tracker for writers. It organizes writing projects,
stages, deadlines, notes, statistics, and optional game mechanics that turn
regular writing into challenges and rewards.

The project is migrating from PySide6 to Vue 3, TypeScript, Ionic, FastAPI,
Tauri 2, and Capacitor. The published desktop application still uses PySide6;
the legacy UI remains available while the new clients reach and verify
functional parity.

## Architecture

```text
Legacy PySide6 UI ───────────────┐
                                │
                                v
                         shared Python Core
                                │
                                ├── repositories ── atomic legacy pickle files
                                │
Vue 3 + Ionic ── FastAPI ───────┘
       │
       ├── Web
       ├── Tauri 2 ── bundled Nuitka Python sidecar ── Windows / macOS
       └── Capacitor ── remote HTTPS API ────────────── iOS / Android
```

All clients use the same Python business rules. The Vue frontend never reads
pickle files or imports Qt/Python objects directly. See the detailed
[architecture](docs/frontend-migration/ARCHITECTURE.md),
[migration plan](docs/frontend-migration/MIGRATION_PLAN.md), and
[live status](docs/frontend-migration/MIGRATION_STATUS.md).

## Features

- Track multiple projects, stages, states, goals, deadlines, and progress.
- Record characters, A4 pages, author's sheets, Ficbook pages, and the other
  units supported by the Python core.
- Review project statistics, productive days, and writing streaks.
- Organize project-note cards and synchronize `#карта` notes with Mind Elixir.
- Count and apply progress from Word `.docx` documents and Scrivener projects.
- Use optional game mechanics: XP, levels, coins, inspiration, health, quests,
  items, buffs, writing sessions, challenges, specializations, cabinet relics,
  custom awards, bank deposits, and streak freezes.
- Use Russian, English, Spanish, German, French, or Brazilian Portuguese.
- Select light, dark, or system theme in the new frontend.

## Target status

| Target | Current state |
| --- | --- |
| Legacy Windows and macOS | Current downloadable PySide6 fallback; preserved during migration |
| Web | Production Vue build works with a configured FastAPI deployment; HTTPS, authentication/reverse-proxy policy, and SPA route fallback belong to the deployment |
| Tauri macOS Apple Silicon | Release `.app`, fresh ARM64 Nuitka sidecar, loopback/token health check, and child cleanup verified on the current host; headless DMG styling is a separate environment limitation |
| Tauri macOS Intel | Configuration and sidecar builder exist; Intel Rust bundle and hardware/runtime verification remain pending |
| Tauri Windows | Configuration and sidecar builder exist; the MSVC sidecar and bundle must be built and tested on Windows |
| Capacitor iOS | Native project, plugins, branding, and `cap sync` are present; native compilation is blocked on this host because full Xcode and the iPhoneOS SDK are absent |
| Capacitor Android | Native project, plugins, branding, and `cap sync` are present; native compilation is blocked on this host by Java 8 and the absence of the Android SDK (`adb`/`sdkmanager`) |

The Capacitor applications do not embed CPython. Web, iOS, and Android require
a separately deployed FastAPI server. See
[MIGRATION_STATUS.md](docs/frontend-migration/MIGRATION_STATUS.md) for the
feature-level parity matrix and remaining legacy-only behavior.

## Download

Download the current PySide6 desktop build from
[GitHub Releases](https://github.com/nevskyforever/nfprogress/releases).
Project downloads are also published through
[nfproject.ru](https://nfproject.ru/).

Tauri and Capacitor artifacts are not yet the published release channel.

## Development prerequisites

- Python 3.11 (used by the official Windows build) and the dependencies in
  `requirements.txt`.
- Node.js 20.19 or newer for `frontend/`.
- Rust and Cargo for Tauri.
- Nuitka for creating the bundled desktop backend sidecar.
- Full Xcode with the iPhoneOS SDK for an iOS build.
- A supported JDK and Android SDK for an Android build.
- Windows with the MSVC toolchain for the Windows sidecar and Tauri bundle.

Clone the repository and create a Python environment:

```bash
git clone https://github.com/nevskyforever/nfprogress.git
cd nfprogress
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows, activate it with PowerShell:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Run the legacy desktop application

```bash
python main_UI.py
```

The legacy UI and the new backend still share the same pickle persistence.
Do not run both against the same data directory at the same time. Use
`--data-dir` or `NFPROGRESS_DATA_DIR` with a temporary development directory
when exercising both clients.

## Run FastAPI and the Vue frontend

Start the API from the repository root:

```bash
python -m backend.app --host 127.0.0.1 --port 8000 --platform web
```

`/health` reports readiness and `/docs` exposes OpenAPI. To isolate development
data, append `--data-dir /absolute/path/to/test-data`.

In a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

Vite listens on `127.0.0.1:5173` and proxies `/api` and `/health` to the local
backend. For a remote Web or Capacitor build, set the public API origin before
building:

```bash
cd frontend
VITE_API_BASE_URL=https://api.example.com npm run build
```

`VITE_API_BASE_URL` is public bundle configuration, not a place for secrets.
Configure `NFPROGRESS_ALLOWED_ORIGINS` on the server for the deployed client.
A non-loopback backend bind additionally requires `--allow-remote`; that mode
is intentionally unauthenticated and must sit behind an external HTTPS and
authentication layer. A Web host must route unknown application paths to
`index.html` so direct Vue Router URLs work.

Useful frontend commands:

```bash
cd frontend
npm run typecheck
npm run lint
npm run test
npm run build
npm run preview
```

## Export localization and help content

Russian strings and `HELP_SECTIONS` remain canonical in Python. Regenerate the
deterministic frontend artifacts from the repository root:

```bash
python scripts/export_frontend_content.py
python scripts/export_frontend_content.py --check
```

When canonical source strings change, follow the localization workflow in
`AGENTS.md` and regenerate `translations_catalog.py` first.

## Tauri desktop

The packaged desktop app launches a Nuitka sidecar on an ephemeral
`127.0.0.1` port. Tauri creates a per-run token, waits for `/health`, and stops
the child during normal exit. The sidecar also watches the Tauri process and
exits after a native crash. End users do not need a separate Python install.

For development, install Nuitka in the active Python environment and build the
sidecar matching the Rust host target:

```bash
python -m pip install nuitka
python scripts/build-backend-sidecar.py
cd frontend
npm ci
npm run tauri:dev
```

Checks and a production bundle:

```bash
cd frontend/src-tauri
cargo check
cd ..
npm run tauri:build
```

`npm run tauri:build` also creates a Finder-styled DMG. In a headless macOS
environment, use `npx tauri build --bundles app` to verify the production app
bundle without requiring Finder AppleScript automation.

To target macOS Intel on a macOS builder, build a matching sidecar with
`python scripts/build-backend-sidecar.py --target x86_64-apple-darwin` and use
the same Rust target for Tauri. The Windows target
`x86_64-pc-windows-msvc` must be built on Windows; the sidecar script rejects
cross-host Windows output by design.

## Capacitor iOS and Android

Set `VITE_API_BASE_URL` to the remote HTTPS API and synchronize the generated
web output with both native projects:

```bash
cd frontend
npm ci
VITE_API_BASE_URL=https://api.example.com npm run cap:sync
```

Open the platform project when its SDK is installed:

```bash
npm run cap:open:ios
npm run cap:open:android
```

An Android debug build can then be run from `frontend/android` with
`./gradlew assembleDebug` (`gradlew.bat assembleDebug` on Windows). iOS builds
are run from the generated Xcode workspace. `cap sync` does not prove that a
native SDK build succeeds.

## Word and Scrivener workflows

- Tauri desktop may select local `.docx` files and Scrivener projects, inspect
  the Scrivener binder hierarchy, configure project/stage synchronization, and
  run it manually.
- When desktop background synchronization is enabled, the sidecar performs
  configured file reads outside the API event loop on enable/start and when
  the effective writing day changes. It checks the setting once per minute and
  stops the worker with the backend.
- Web, iOS, and Android cannot obtain arbitrary filesystem or background
  access. They can explicitly upload a selected `.docx`; the server counts it
  and applies the total through normal progress and reward rules.
- Scrivener project upload is not supported by remote clients. The shared
  integration accepts `.docx` only; the legacy selector may still show `.doc`
  but correctly asks the user to save that obsolete format as `.docx`.

## Data safety

- `data.pkl`, `settings.pkl`, and `gamer.pkl` remain authoritative during the
  transition and are written atomically by the repository layer.
- Tests and smoke checks use explicit temporary data directories; they must not
  migrate real user files.
- No automatic JSON/SQLite replacement or destructive pickle migration occurs.
- Keep backups before testing migration builds with valuable data, and never
  point the legacy UI and Tauri sidecar at the same directory concurrently.

## Tests

Run the Python suite from the repository root:

```bash
python -m pytest -q
```

The current `5.0` base retains `tests/test_accessibility.py` but does not
include its legacy `accessibility.py` module (it exists in an unmerged legacy
branch). Until that separate legacy feature is merged or restored, the
migration aggregate Python run is:

```bash
python -m pytest -q --ignore=tests/test_accessibility.py
```

This does not affect the FastAPI/Vue/Tauri paths; it is tracked in the
migration status rather than silently hidden.

The focused migration checks can be run independently:

```bash
python -m pytest -q \
  tests/test_core_storage.py \
  tests/test_project_service.py \
  tests/test_core_notes_service.py \
  tests/test_core_game_service.py \
  tests/test_document_integrations.py \
  tests/test_api.py \
  tests/test_content_services.py \
  tests/test_frontend_content_export.py
```

Run frontend gates from `frontend/`:

```bash
npm run typecheck
npm run lint
npm run test
npm run build
```

Native checks additionally require the matching platform SDK. Current blockers
and the latest verified matrix are recorded in
[MIGRATION_STATUS.md](docs/frontend-migration/MIGRATION_STATUS.md).

## Uninstallation

### Windows

Open **Settings > Apps > Installed apps**, find **nfprogress**, and select
**Uninstall**. The legacy application is installed in
`%LOCALAPPDATA%\Programs\nfprogress`.

Uninstalling the application does not remove user data. It is stored in
`%APPDATA%\nfprogress`. Data created by older versions may also remain in
`%USERPROFILE%\Documents\nfprogress`. Delete these directories manually only
if you no longer need your projects, settings, and progress history.

### macOS

Move `nfprogress.app` from the Applications folder to the Trash. User data in
`~/Documents/nfprogress` is not removed automatically; delete that directory
manually only if you no longer need it.

## Code signing policy

Free code signing provided by
[SignPath.io](https://signpath.io/), certificate by
[SignPath Foundation](https://signpath.org/).

### Project roles

- Committer: nevskyforever
- Reviewer: nevskyforever
- Approver: nevskyforever

### Privacy policy

This program will not transfer any information to other networked systems
unless specifically requested by the user or the person installing or
operating it.

## License

nfprogress is free and open-source software licensed under the
[GNU General Public License version 3](LICENSE).
