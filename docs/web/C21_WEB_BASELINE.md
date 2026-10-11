# C21.1.01 — Local production Web baseline and browser boundary

Date: 2026-10-11. Branch `6.0`; starting HEAD and fetched `origin/6.0`:
`8d8675ed00d0ed3b5a8dfa99cf502350f7c3c958`. Initial worktree clean.
C18.8/C18 CLOSED on the independent owner/GPT acceptance supplied in the task:
Cloud `38123427926` SUCCESS, SQLite `38123427916` SUCCESS. Official progress
**84.0%**, C21 **IN PROGRESS**. This slice earns no roadmap points.

## What this baseline proves

The existing Vite production output runs in plain Chromium without
`window.__TAURI_INTERNALS__`, native Capacitor, native SQLite IPC, or a Tauri
command/plugin host. Runtime initialization itself is browser-safe. The existing
application is **an HTTP-backed browser client**, not an offline encrypted Web
client. It requires `/api/settings`, `/api/content/*` and the existing project,
notes, documents and game APIs. `Run Web.sh` is a development launcher: it starts
the Python-compatible API and Vite development server; it is not a deployment
or production persistence architecture.

A built client with no API renders its existing bootstrap error/retry gate.
It must not invent settings, accept the agreement automatically, claim writes
succeeded, or route plaintext into cloud encrypted-sync endpoints to make boot
look successful. Successful local smoke uses the real existing Python Web API
with an isolated **synthetic** profile; no production Tauri or API mocks.
The API may itself use its existing server-side SQLite/settings implementation;
there is **no native frontend SQLite command host** in the browser.

This local API has plaintext application endpoints. It is not the future public
Web E2EE storage boundary and must not be deployed as a substitute. No deployment,
backend semantics, SQLite/PostgreSQL schemas, authority/AAD, AMK/password/recovery,
codec/compression/ID0/ID1, history/ACK/cursor or project-bootstrap changes occur.

## Browser-platform contract

- `src/platform/runtime.ts` initializes before mounting Vue and selects `web`,
  `tauri`, `ios` or `android`. No global Tauri mock or platform spoofing is allowed.
- Browser adapters use existing HTTP repositories, DOM/File/Blob downloads,
  clipboard APIs and browser windows. HTTP failures propagate; they are not writes.
- `requireDesktopRuntime()` is the centralized fail-closed guard for newly repaired
  desktop-only public entry points. It rejects **before** importing native plugins.
  Existing gated callers stay intact; this slice does not rewrite every repository.
- Native repositories/runtimes below are internal desktop implementations, not
  browser adapters. Do not instantiate/call them from a Web feature. Future Web
  persistence must implement the repository contracts with real durable,
  transactional storage, not fake SQLite or localStorage success results.
- Desktop file paths/bindings, native journal, updates and desktop encrypted-sync
  UI remain unavailable in Web. Backend capabilities describe HTTP service abilities;
  they never authorize native IPC in a browser. Web bootstrap does not start cloud
  session/native document/update timers. Capacitor initialization and listeners
  continue behind `isNativePlatform()` / `isNativeMobile()`.
- Explicit Word upload in the legacy local API is a local-development flow. The
  public E2EE Web design must not upload manuscript plaintext to that service.
  Client-side `.docx` conversion/download already exists in document services.

## Production dependency inventory

Audit scope: all `frontend/src/**` production TS/Vue (excluding specs/generated
locale text), `vite.config.ts`, `capacitor.config.ts`, `package.json`, runtime
bootstrap/router, and imported mind-map browser assets. Static imports of Tauri
modules are inert until their functions run; they are not themselves proof of a
native command on the Web path. All matching files are listed below.

Classes: **1** existing browser-safe/runtime-gated; **2** browser adapter needed
for the future encrypted/offline client; **3** explicitly desktop/mobile-only;
**4** immediate native-entry defect repaired here. Multiple classes describe a
mixed module without claiming its native internals are browser implementations.

| Production paths (relative to `frontend/`) | Class and boundary decision |
| --- | --- |
| `src/main.ts`, `src/App.vue`, `src/router/index.ts` | **1** runtime precedes mount; desktop cloud initialization and update scheduling gated. Non-admin bootstrap needs real settings API. Admin routes use independent memory session. No native call at module load. |
| `src/platform/runtime.ts` | **1/3** dynamic core/window/opener; runtime info and native document timer only Tauri; App/Keyboard/StatusBar and back/minimize only native Capacitor. Web links use `window.open`; close returns false; system bars no-op. Adds central rejection guard. |
| `src/platform/files.ts` | **1/3** dialog import guarded; Word open/save and Scrivener absolute path selection reject in Web. |
| `src/platform/workspaceWindows.ts` | **1** Tauri WebviewWindow only desktop; Web opens browser popup with workspace query marker. Popup availability still depends on browser policy. |
| `src/platform/progressShare.ts` | **1** clipboard-manager only initialized Tauri platform; Web uses canvas/Blob/ClipboardItem with explicit PNG download fallback. |
| `src/composables/useNetworkStatus.ts` | **1/3** Web uses navigator online/offline; Capacitor Network dynamically imported only native mobile. |
| `src/stores/updater.ts`, `src/components/ui/UpdatePrompt.vue` | **1/3** updater/app/core/event/process imports only after native update capability or macOS Tauri check; pending install/relaunch requires a native check result. Web does not schedule updates. |
| `src/api/projects.ts` | **1/4→3** desktop CRUD/summary/folders gated by Tauri global; Web uses HTTP. `reorderFolders` previously unconditionally invoked IPC; now rejects Web before native IPC. Only current UI caller is desktop catalog authority panel. No HTTP folder-order writer invented. |
| `src/stores/projects.ts` | **1** raw Tauri check gates desktop reload behavior; normal browser store uses HTTP project adapters. |
| `src/api/settings.ts`, `src/api/game.ts` | **1/2** SQLite/settings or game invoke only Tauri; Web HTTP including explicit agreement persistence. Public encrypted browser persistence still needs an adapter. |
| `src/api/documents.ts`, `src/api/integrations.ts` | **1/3** native helpers private behind Tauri branches; browser uses HTTP. `confirmSync` explicitly rejects non-desktop. Local API capabilities disable background paths. |
| `src/components/documents/DocumentEditorView.vue` | **1/3** native Word export gated; close/destroy listener only Tauri. Web import uses File + client conversion, export Blob download. Desktop local binding panel hidden (`canLinkWord`). External polling is existing HTTP behavior in Web. |
| `src/composables/useDocumentSync.ts`, `src/services/documentDocx.ts` | **1/2** browser docx codec and HTTP document persistence; native authority/linked-Word branches gated. Public E2EE durable document implementation not present. |
| `src/pages/IntegrationsPage.vue`, `src/components/integrations/WordUploadCard.vue` | **1/3** explicit file upload supported by local API; background paths and Scrivener unavailable when Web capabilities false, with existing localized explanation. Tauri picker separately gated. |
| `src/pages/SettingsPage.vue`, `src/components/developer/DeveloperModeDialog.vue` | **1/3** desktop cloud and diagnostics cards require desktop response; updates also require runtime support. Developer test-data controls require Tauri; other developer actions use HTTP in Web. This smoke uses API `platform=web`. |
| `src/diagnostics/service.ts` | **4→3** record already disabled outside Tauri, but stats/copy/export/clear called native plugins directly. Every desktop adapter operation now uses central guard. Unsupported reads/writes reject, never report success. |
| `src/components/settings/DiagnosticsCard.vue` | **1/3** hidden on Web settings; native journal has no browser persistence/export adapter. |
| `src/infrastructure/projects/projectReadRepository.ts`, `projectMetadataRepository.ts`, `progressRepository.ts` | **1** raw Tauri check selects native vs HTTP implementations. No new environment checks introduced here. |
| `src/infrastructure/notes/notesRepository.ts` | **1** currentPlatform selects API vs SQLite notes; `useProjectNotes` stays browser-capable through that factory. |
| `src/infrastructure/tauri/projectMetadataRepository.ts`, `progressRepository.ts` | **3** static core imports; internal native writers reachable only through gated platform factories. |
| `src/infrastructure/sqlite/settingsRepository.ts`, `projectReadRepository.ts`, `notesRepository.ts` | **2/3** native SQLite implementations with core IPC (project reads dynamic); factories above select HTTP in Web. Cannot be reused as browser durable repositories. |
| `src/infrastructure/sqlite/cloudAccountBindingRepository.ts`, `cloudIdentityRepository.ts`, `cloudProjectBootstrapRepository.ts` | **2/3** static core imports; native account/device binding and durable bootstrap. Created by desktop runtime factory only after cloud-session guard. Browser identity/bootstrap adapter is missing. |
| `src/infrastructure/sqlite/noteSyncIntentRepository.ts`, `noteSyncOutboxRepository.ts`, `noteSyncInboxRepository.ts`, `noteSyncRemoteApplyRepository.ts`, `noteSyncAckRepository.ts` | **2/3** native durable transactional capture/seal/upload/pull/protected apply/ACK. Browser equivalents are blocking design work, not localStorage shims. |
| `src/infrastructure/sqlite/noteSyncResolutionRepository.ts`, `noteSyncResolutionUploadRepository.ts` | **2/3** native durable conflict/resolution state/receipts; desktop runtime only. |
| `src/infrastructure/sqlite/projectMetadataMigrationRepository.ts`, `projectCoverRepository.ts`, `stageStructuralRepository.ts`, `accountCatalogRepository.ts` | **2/3** native metadata/cover/structural/catalog authorities. Gated desktop cloud workflows; no browser transactional adapter. |
| `src/cloud/noteSyncRuntime.ts`, `src/stores/cloudSession.ts` | **2/3** desktop factory constructs native repositories; session.initialize refuses non-Tauri, login/actions require initialized runtime; main/App do not initialize it in Web. No browser scheduler enabled. |
| `src/cloud/accountObjectReader.ts`, `contentNoteReader.ts`, `contentNoteRuntime.ts`, `mapSyncRuntime.ts`, `documentSyncRuntime.ts`, `progressSyncRuntime.ts`, `gameSyncRuntime.ts` | **2/3** static core imports/native commands; reached through desktop runtime and authority actions. Pure codecs remain browser-capable; these durable/native orchestration implementations are not. |
| `src/components/settings/CloudSyncSettingsCard.vue`, `ProjectMetadataAuthorityPanel.vue`, `ProjectCoverAuthorityPanel.vue`, `StageStructuralAuthorityPanel.vue`, `ContentNoteAuthorityPanel.vue`, `MapAuthorityPanel.vue`, `DocumentAuthorityPanel.vue`, `ProgressAuthorityPanel.vue`, `GameAuthorityPanel.vue`, `AccountCatalogAuthorityPanel.vue` | **3** descendants of desktop-only cloud card. Must not be mounted/activated as Web sync without durable adapter. Catalog folder reorder now explicitly rejects an accidental Web call. |
| `src/auth/keyContext.ts`, `src/cloud/accountCryptoProvisioning.ts`, `noteSyncInboxDecrypt.ts`, `src/crypto/**`, `src/api/accountCrypto.ts`, `encryptedSync*.ts`, `encryptedCovers.ts` | **1/2** client WebCrypto, key leases, bounded encrypted HTTP; no key/plaintext authority moved server-side. Browser primitives exist, but durable sync composition is desktop-only. No contract change. |
| `src/api/client.ts`, `content.ts`, `notes.ts`, `userAuth.ts`, `admin.ts`, `cloudProjects.ts`, `sync.ts`, `src/infrastructure/api/**` | **1/2** fetch with relative default or explicit `VITE_API_BASE_URL`; no implicit native service address. HTTP application persistence is local-development baseline only; cloud encrypted APIs remain separate. `sync.ts` dormant C9 client not wired by UI. |
| `src/components/projects/projectCoverPreparation.ts` | **1** browser fetch/File/image conversion; no native IPC. Existing imported-cover preparation not changed. |
| `src/components/notes/MindMapEditor.vue`, `src/components/notes/mindMapBridge.ts`, `src/core/mindmap/normalization.ts`, `../mindmap_assets/{index.html,app.js,i18n.js,MindElixir.js,MindElixir.css}` | **1** local browser iframe/bridge and DOM code; no Tauri/Qt dependency on production browser bridge. Persist through notes repository. |
| `vite.config.ts`, `src/env.d.ts`, `capacitor.config.ts`, `package.json` | **1/3** Vite `/api` and `/health` local proxy points to `127.0.0.1:8000` for local testing (also used by preview); deployment must explicitly decide service routing. Capacitor packages installed but gated at runtime; type-only imports/native build configuration do not activate a native host. No new packages/config changes. |

## Repairs and retained restrictions

Only two native-entry defects repaired: full-folder-order write and explicit
native diagnostic journal operations. Shared guard uses existing Russian text
`Доступно только в desktop-приложении.` already present in all five non-Russian
catalogs; no generated catalogs or new UI labels edited. Existing local-file
limitation explains browser restrictions. Related help topics (file integrations,
Word, cloud sync, diagnostics) reviewed: no new feature or workflow is introduced;
existing desktop/local-file advice remains applicable, no help rewrite required.

Static-only/offline initialization, browser durable E2EE project/notes/content/
catalog/game state, account identity, transactional outbox/inbox/conflict/ACK,
recoverable migration and restart proofs remain **blocked on a separately scoped
browser adapter design**. Current HTTP settings/CRUD must not become the public
plaintext authority. Stop that persistence work here. Do not claim C21 acceptance
from the local API smoke. Popup/clipboard permissions and large existing bundle
warnings also remain; no broad bundle refactor belongs in this slice.

## Reproduction and verification

Use installed frontend dependencies and Chromium; no install was required.
`bash 'Run Web.sh' --check` confirms the launcher prerequisites. To avoid copying
real writer data, the production smoke uses the launcher's existing API entry
point with a different, empty test profile; intentionally does not run `--dev-data`:

```sh
# Repository root; unique fresh task-only directory, not a production profile.
PYTHONDONTWRITEBYTECODE=1 NFPROGRESS_TEST_DATA_DIR=/tmp/c21-web-profile \
  NFPROGRESS_DEVELOPER_MODE=1 python3 -m backend.app \
  --host 127.0.0.1 --port 8000 --platform web --data-dir /tmp/c21-web-profile
# Separate terminal, frontend/:
npm run build
npm run preview -- --host 127.0.0.1 --port 4173
# Repository root, only against that synthetic profile:
node frontend/scripts/web-baseline-smoke.mjs http://127.0.0.1:4173 --synthetic-profile
```

The script accepts the synthetic agreement through the UI, creates one
synthetic project (discard the task-only profile after stopping the API) through the real API, exercises browser routes, verifies absent
native globals, confirms hidden native diagnostics and visible local-file
restriction, and checks the existing API-failure bootstrap gate (failure request
aborted only in a separate context). Successful API responses are never mocked.

### Actual local results

- Focused boundary/catalog/native diagnostics: 26 tests across 4 files passed
  (runtime 3, catalog 3, desktop diagnostics 3, generic diagnostics 17).
  Initial catalog mock lacked `currentPlatform`; repaired only that harness and
  its affected 3 tests passed. Native operation guards and no-import assertions
  are exercised, not merely static import scans.
- One final CI-equivalent frontend union: all three curated `Frontend admin`
  selections from `.github/workflows/cloud-backend-tests.yml`, plus runtime,
  workspace windows, progress share, agreement, integrations/documents API,
  project-read factory and integrations-page coverage: **112 files / 695 tests**.
  **694 passed / 1 failed** initially on installed Node 26: the existing admin
  spec resolved Node's experimental global `localStorage` instead of jsdom.
  Only affected `src/api/admin.spec.ts` rerun with
  `NODE_OPTIONS=--no-experimental-webstorage npm test -- --run src/api/admin.spec.ts`:
  **5/5 PASS**, including the original failure. No test/production change to
  accommodate Node 26. Combined selection has no unresolved failed case or skip.
- Explicit typecheck (via `npm run build`) and final production build PASS.
  Existing large-chunk and mixed static/dynamic documentDocx-import warnings
  remain. Existing Ionic sourcemap warnings remain in Vitest.
- Production Playwright/installed Chromium smoke PASS: `/projects`, synthetic
  project detail, `/texts`, `/maps`, `/notes`, synthetic project notes/map,
  `/game`, `/integrations`, `/help`, `/settings`, plus `/admin/login`.
  Native state: `platform=web`, Tauri global absent, Capacitor native false;
  JS page errors 0, unhandled rejections 0. Agreement UI, native diagnostics
  hidden, visible file-sync restriction and API-failure gate verified.
- Rapid repeated hard reloads in the first smoke attempts overloaded the local
  Python API: page shells rendered, but integrations remained loading and
  synthetic cleanup requests timed out. Stack-only diagnosis on a separate
  synthetic profile showed repository-lock waits under project/streak reads,
  with active SQLite mirror ownership/application-metadata configuration.
  Sequential navigation with `networkidle` gates passed all checks. This is
  **retained local API latency/rapid-reload sensitivity**, not evidence of a
  browser Tauri call or a proven deadlock. No backend/SQLite production repair
  attempted; that work requires a separate bounded scope. Fast reload/load
  stress acceptance is not claimed. The smoke now waits for API completion.
- `node --check frontend/scripts/web-baseline-smoke.mjs`, all five existing
  desktop-only message translations, `Run Web.sh --check`, protected bytecode
  SHA-256 comparison and `git diff --check`: PASS.
- Python/Rust/PostgreSQL/native SQLite/Android/Windows suites, full Nuitka builds,
  deployment and remote CI inspection: **not run**, production unchanged.

The new runtime spec is included in the local union above, but not automatically
in the existing curated remote workflow. Existing modified catalog and native
diagnostics specs are already curated. Workflow/config changes are excluded from
this frontend/docs slice. Expected publication workflow: Cloud backend tests;
SQLite sync substrate tests not expected. Published slice remains REMOTE CI
PENDING; Codex must not poll Actions. C21 remains IN PROGRESS at **84.0%**.

Next: **C21.1.02**, local browser durable persistence/E2EE adapter design with
transaction/restart/fail-closed acceptance contracts. Include the local API latency
observation in the decision; do not deploy the plaintext compatibility API.
