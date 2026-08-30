# nfprogress

nfprogress is a progress tracker for writers. It organizes writing projects,
stages, deadlines, notes, statistics, and optional game mechanics that turn
regular writing into challenges and rewards.

The current application uses Vue 3, TypeScript, Ionic, FastAPI, Tauri 2, and
Capacitor. PySide6 source remains in the repository only as a compatibility
reference for existing data and behavior; legacy packages are no longer built,
published, or supported.

## Architecture

```text
Vue 3 + Ionic ── FastAPI ── shared Python Core
                                │
                                ├── repositories ── atomic legacy pickle files
       │
       ├── Web
       ├── Tauri 2 ── bundled Nuitka Python sidecar ── Windows / macOS
       └── Capacitor ── remote HTTPS API ────────────── iOS / Android
```

All clients use the same Python business rules. `Project`, `Stage`, `Gamer`,
and `Buff` retain their legacy module paths so existing pickle data stays
loadable, while the shared core and services import without Qt. The Vue
frontend never reads pickle files or imports Qt/Python objects directly. See the detailed
[architecture](docs/frontend-migration/ARCHITECTURE.md),
[migration plan](docs/frontend-migration/MIGRATION_PLAN.md), and
[live status](docs/frontend-migration/MIGRATION_STATUS.md).

## Features

- Track multiple projects, stages, states, goals, deadlines, and progress.
- Record characters, A4 pages, author's sheets, Ficbook pages, and the other
  units supported by the Python core.
- Review project statistics, productive days, and writing streaks.
- Create a 1080 × 1080 progress card for a finite project or stage; its share
  menu has separate Copy-to-clipboard and Save-PNG actions.
- Organize project-note cards and synchronize `#карта` notes with Mind Elixir.
- Count and apply progress from Word `.docx` documents and Scrivener projects.
- Use optional game mechanics: XP, levels, coins, inspiration, health, quests,
  items, buffs, writing sessions, challenges, specializations, cabinet relics,
  custom awards, bank deposits, and streak freezes.
- Use Russian, English, Spanish, German, French, or Brazilian Portuguese.
- Select light, dark, or system theme in the new frontend.
- Configure the writing-day boundary, notification duration, and optional
  all-project daily total; Vue remembers its own project-list and inventory
  views without changing historical desktop preference keys.
- Review persistent bank and streak events in the cross-platform notification
  center and mark them read without losing the legacy event history.

## Target status

| Target | Current state |
| --- | --- |
| Web | Production Vue build works with a configured FastAPI deployment; HTTPS, authentication/reverse-proxy policy, and SPA route fallback belong to the deployment |
| Tauri macOS Apple Silicon | Release `.app`, fresh ARM64 Nuitka sidecar, loopback/token health check, and child cleanup verified on the current host; a plain headless DMG is available, while Finder styling remains cosmetic-only |
| Tauri macOS Intel | Fresh x86_64 sidecar, target `cargo check`, and unsigned production `.app` bundle were built on the ARM host; authenticated sidecar startup was exercised through Rosetta within Tauri's 30-second readiness window. Physical Intel UI/signing verification remains a release-host task |
| Tauri Windows | The workflow builds the MSVC Nuitka sidecar and Tauri NSIS installer, checks runtime health, creates the updater artifact, and publishes `latest.json` with the GitHub Release |
| Capacitor iOS | Native project, plugins, branding, and `cap sync` are present; native compilation is blocked on this host because full Xcode and the iPhoneOS SDK are absent |
| Capacitor Android | Native project, plugins, branding, and `cap sync` are present; native compilation is blocked on this host by Java 8 and the absence of the Android SDK (`adb`/`sdkmanager`) |

The Capacitor applications do not embed CPython. Web, iOS, and Android require
a separately deployed FastAPI server. See
[MIGRATION_STATUS.md](docs/frontend-migration/MIGRATION_STATUS.md) for the
feature-level parity matrix and remaining platform-specific behavior.

## Download

Tauri desktop builds are published through
[GitHub Releases](https://github.com/nevskyforever/nfprogress/releases).
Windows releases use the bundled NSIS installer; automatic updates are delivered
from the same GitHub release channel.

## Development prerequisites

- Python 3.13 (used by the official Windows build) and the dependencies in
  `requirements-backend.txt` for the new desktop/backend targets.
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
python -m pip install -r requirements-backend.txt
```

On Windows, activate it with PowerShell:

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-backend.txt
```

## Historical PySide6 source

`main_UI.py` and the old updater remain for regression comparison and pickle
compatibility only. They are not part of the release workflow and are not a
supported application target. Use Web or Tauri for development and releases.

## Run FastAPI and the Vue frontend

Start the API from the repository root:

```bash
python -m backend.app --host 127.0.0.1 --port 8000 --platform web --dev-data
```

`/health` reports readiness and `/docs` exposes OpenAPI. The `--dev-data` flag
uses the same synchronized test-data behavior as the historical Python UI. To
isolate a test completely, replace it with `--data-dir
/absolute/path/to/test-data`.

In a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

For a one-command local Web run from the repository root, use:

```bash
bash "Run Web.sh"
```

It starts the Python backend with `--dev-data`, waits for `/health`, and then
starts Vite. Stopping Vite also stops that backend.

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

For a local desktop test without a production package, run from the repository
root:

```bash
bash "Run Tauri.sh"
```

It selects the host target, rebuilds its matching sidecar when that ignored
local binary is absent or stale, and uses the Python-compatible synchronized
`test_data` directory in Tauri debug mode. Use
bash "Run Tauri.sh" --check to validate prerequisites without opening a window.
Stop a separately running npm run dev first, because Tauri dev uses port 5173.

Checks and a production bundle:

```bash
cd frontend/src-tauri
cargo check
cd ..
npm run tauri:build
```

`Build Tauri ARM.sh`, `Build Tauri Intel.sh`, and `Build Tauri All.sh`
provide matching macOS build entry points. They build the target-matched Nuitka
sidecar, Tauri app, verified plain DMG, and a local ZIP containing the DMG,
license, and source-code notice:

```bash
bash "Build Tauri ARM.sh"
bash "Build Tauri Intel.sh"
bash "Build Tauri All.sh"
```

`Build Tauri All.sh` and `Release Tauri All.sh` run ARM and Intel work in
parallel in the current terminal. PyCharm users can run the shared `Tauri Build
All` or `Tauri Release All` compound configuration: it starts both jobs in the
IDE's Terminal tool window. The release workflow serializes only the shared
update-manifest step to preserve both architecture entries.

All Tauri build entry points synchronize the normalized three-component version
from `engine.py` into the Tauri and Cargo metadata before building.

The artifacts are written to `build-tauri-arm/` and `build-tauri-intel/`.
On Apple Silicon, the Intel scripts automatically create and maintain the local
Rosetta x86_64 environment `.venv-tauri-intel` with backend dependencies and
Nuitka. To use a different environment, set `NFPROGRESS_TAURI_PYTHON` (and, if
needed, `NFPROGRESS_TAURI_PYTHON_ARCH=x86_64`) before launch. The matching `Release Tauri
*.sh` wrappers upload the macOS archives to the release hosting; the protected CI
workflow downloads them, adds the Windows artifacts, and publishes the combined
GitHub Release. Set `NFPROGRESS_TAURI_RELEASE_UPLOAD=0` to build without uploading.

### Windows release and automatic updates

`.github/workflows/build.yml` is the supported Windows release path. It builds
the x86_64 MSVC sidecar and NSIS installer, runs Python/frontend/Rust checks,
smoke-tests the sidecar, creates the Tauri updater artifact and `latest.json`,
then publishes one GitHub Release. The Windows Nuitka sidecar carries stable
version/product metadata and avoids payload compression.

Configure these GitHub Actions secrets before the first release:

- `TAURI_SIGNING_PRIVATE_KEY`: the private updater key generated once with
  `npm run tauri signer generate -- -w
  "$env:USERPROFILE\\.tauri\\nfprogress-updater.key"` from PowerShell;
- `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`: updater-key password, when set.

Set `TAURI_UPDATER_PUBLIC_KEY` as a repository variable (a secret with the same
name is also accepted). This is a free Tauri update key, not an Authenticode
publisher certificate. Keep its private half backed up securely: installed
clients cannot trust releases signed by a replacement key.

Official release builds check GitHub Releases after startup and once per hour.
When a version is available, the app shows its release notes and installs it
through Tauri after cryptographic verification. Local `tauri:dev` and ordinary
unsigned local bundles do not enable this channel.

`npm run tauri:build` also creates a Finder-styled DMG. In a headless macOS
environment, use `npx tauri build --bundles app` to verify the production app
bundle without requiring Finder AppleScript automation. To produce a normal
drag-to-Applications DMG without Finder styling, use:

```bash
scripts/build-tauri-dmg.sh aarch64-apple-darwin
scripts/build-tauri-dmg.sh x86_64-apple-darwin
```

After the matching Python sidecar has been built, the script builds the matching
`.app`, then creates and verifies a UDZO DMG with `hdiutil`; it never invokes
`osascript`.

To target macOS Intel on a macOS builder, build a matching sidecar with
`python scripts/build-backend-sidecar.py --target x86_64-apple-darwin` and use
the same Rust target for Tauri. On Apple Silicon, invoke that command from an
`x86_64` execution of a universal Python virtual environment with matching
x86_64 backend dependencies; an arm64 Python cannot package arm64 extension
modules such as `pydantic_core` into an Intel sidecar. The Windows target
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
  integration accepts `.docx` only and asks the user to save the obsolete
  `.doc` format as `.docx`.

## Data safety

- `data.pkl`, `settings.pkl`, and `gamer.pkl` remain authoritative during the
  transition and are written atomically by the repository layer.
- Tests and smoke checks use explicit temporary data directories; they must not
  migrate real user files.
- No automatic JSON/SQLite replacement or destructive pickle migration occurs.
- Keep backups before testing migration builds with valuable data.

## Tests

Run the Python suite from the repository root:

```bash
python -m pytest -q
```

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
**Uninstall**. The Tauri NSIS application is installed for the current user.

Uninstalling the application does not remove user data. It is stored in
`%APPDATA%\nfprogress`. Data created by older versions may also remain in
`%USERPROFILE%\Documents\nfprogress`. Delete these directories manually only
if you no longer need your projects, settings, and progress history.

### macOS

Move `nfprogress.app` from the Applications folder to the Trash. User data in
`~/Documents/nfprogress` is not removed automatically; delete that directory
manually only if you no longer need it.

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
