# Frontend migration status

Updated: 2026-09-04

`[done]` means the repository implementation for that row exists and has been
checked on an available host; it does not imply that every native release is
signed or verified. `[blocked]` is reserved for a concrete external SDK/toolchain
blocker. Tauri is the supported desktop release target; PySide6 packaging is
retired.

## Subsystem matrix

| TypeScript Core phase 1 | [done] | `frontend/src/core/projects` owns verified pure unit, progress, remaining, and planning calculations. Vue uses the shared calculation layer for display/preview only; Python remains authoritative for persisted mutations, cached daily plans, streaks, rewards, PKL, and the SQLite shadow mirror |

| SQLite shadow mirror | [done] | Versioned sqlite3 schema, transactional rebuild/import, stable-ID relational rows, JSON payload for complex legacy state, best-effort repository-boundary synchronization, mirror metadata, verifier, and temporary-directory tests. SQLite is not a runtime read source and is not authoritative for TypeScript |

| Subsystem | Status | Evidence and remaining work |
| --- | --- | --- |
| Repository/dependency audit | [done] | Core, UI, game, storage, integrations, build scripts, and available native SDKs audited |
| Architecture and migration plan | [done] | Transitional boundaries, data safety, transports, platform capabilities, and debt documented |
| Legacy packaging retirement | [done] | PySide6 build/release wrappers, SSH publication helpers, and legacy manifests were removed. Actions publish only Tauri releases; historical Python UI source remains solely for data compatibility and regression reference |
| Qt-free supported runtime | [done] | Web, Tauri, sidecar, updater, and Capacitor paths have no Qt runtime requirement |
| Qt-free application services | [done] | Projects, notes/maps, game, settings/content, and integrations are service-backed. `engine.py`, `game.py`, and `game_data.py` deliberately retain pickle-compatible class paths and are proven to import without PySide6 or legacy UI dependencies |
| Storage repository/isolation | [done] | Explicit data roots, in-process and advisory locks, atomic legacy pickle writes, idempotent streak handling, temporary-directory tests, timestamped backups before destructive setting transitions, and a one-time backup before persisted notification IDs are present |
| JSON-safe exchange contract | [done] | Page-facing project/integration, content/settings, note/map, notification-history, and complete game state/catalog/command envelopes have explicit Pydantic contracts; compatibility JSON remains intentionally extensible only for Mind Elixir, history/results, and unknown legacy metadata |
| Project/stage service | [done] | CRUD, states, archive/completion, stages, all progress units, deadlines, infinite projects, structured statistics, and the all-project writing-day summary use stable IDs |
| Notes and Mind Elixir service | [done] | CRUD, ordering, normalization, aggregate maps, and bidirectional `#карта` synchronization are exposed without Qt |
| Game and writing-session service | [done] | Server-authoritative profile, buffs, freezes, sessions, challenges, shop/inventory, inspiration, specializations/mastery, creative events, skills/quests, cabinet, custom awards, bank commands, and persisted unread/read bank or streak events are exposed |
| Achievement/award mapping | [done] | Legacy has no separate `Achievement` model: quest badges remain canonical `Награды` inventory items; manuscript milestones remain cabinet state; custom awards have separate commands |
| Settings semantics | [done] | `inf_project` creates/removes canonical `Общий проект`; disabling it or a populated `global_streak` creates a timestamped data/settings backup before applying the legacy-compatible destructive transition |
| User-agreement service/gate | [done] | Versioned canonical agreement API, legacy-compatible acceptance flag, blocking Vue bootstrap gate, language switching, retry, accessible acceptance, and guarded Tauri decline/close behavior are implemented |
| Word/Scrivener service | [done] | Direct desktop `.docx`/Scrivener sync, nested binder inspection, remote `.docx` application, source mtime preservation, stale/missing/future-source protection, typed errors, and atomic detach-all are implemented. Stored legacy `synch` bindings are discovered across all project stages and run with the same grouped semantics as PySide6, without reconnecting sources; `.doc` is unsupported and asks for `.docx` rather than silently changing data |
| Desktop background sync | [done] | Desktop-only worker runs configured active sources off the event loop on enable/start and writing-day change, isolates per-source failures, and shuts down with FastAPI |
| FastAPI/OpenAPI | [done] | Health, centralized errors, loopback token, CORS, typed page-facing response contracts, and every router required by the Vue application are implemented; remote HTTPS/auth remains an operator deployment boundary, not an embedded account system |
| Vue/Ionic shell | [done] | Responsive desktop/mobile navigation, platform guards, network/startup errors, legacy-derived neutral/blue design tokens, Arial/Helvetica typography, focus support, themes, and locale store are implemented. Full/system/reduced motion is an explicit shared setting, so OS reduced-motion no longer silently suppresses requested progress feedback; Web and Tauri developer launchers use the same synchronized `test_data` semantics as `main_UI.py` |
| Projects/stages/progress frontend | [done] | Real API powers project list/search/filter/sort, project and stage editing/lifecycle, all units, deadlines, progress recording, immediate refresh, and finite project/stage 1080 × 1080 progress-card export with explicit clipboard/save-PNG choices. Circular diagrams and bars tween their value with visible colour/glow feedback; global, project, and eligible stage streaks are displayed from legacy-authoritative state. Stages are circular-progress tiles that open into their own focused workspace while retaining stable parent/stage IDs; project-local synchronization refreshes in place without replacing the workspace with a loading state. The displayed today target is the legacy cumulative plan, not the editable daily increment |
| Statistics frontend | [done] | Structured Python calculations and localized labels are displayed responsively; calculations are not duplicated in TypeScript |
| Notes/Mind Elixir frontend | [done] | Legacy pastel full-card note colors and in-card colour palette, a prominent full-width create action, autosave, and canonical Mind Elixir assets use the real notes/map API and synchronization rules; the responsive workspace keeps the recognizable legacy card concept |
| Game frontend | [done] | Seven responsive panels cover overview, sessions, challenges, items, growth, cabinet, and awards/bank; a global responsive notification center exposes persisted bank/streak history, and every command reloads authoritative backend state |
| Integrations frontend | [done] | Desktop dialogs, configured project/stage sync and detach, recursive Scrivener selection, manual/all-source runs, and remote `.docx` upload are wired to the real API. The project workspace discovers existing bindings on every stage, runs them together as legacy PySide6 does, or deep-links to setup with its project/stage selected; no client claims unsupported `.doc` access |
| Settings frontend | [done] | Language, light/dark/system theme, full/system/reduced interface motion, writing-day start, notification duration, game mode, infinite project, global streak, all-project daily total, desktop-only background sync/update check, inventory category, and frontend list preferences are platform-gated and persisted through the settings service |
| Localization pipeline | [done] | Six canonical Python catalogs, deterministic frontend export/drift check, Vue/TypeScript source extraction, HTML/placeholder validation, and the final catalog regression checks pass |
| Help frontend | [done] | Localized canonical `HELP_SECTIONS`, nested navigation, article rendering, in-window search, and keyboard search shortcut use the real content API |
| Web target | [done] | Production Vue build, remote URL configuration, manifest, responsive routes, platform guards, and backend-unavailable states are verified; deployment HTTPS/auth, SPA fallback, and offline mutation behavior remain operator concerns rather than bundled claims |
| Tauri lifecycle/security | [done] | Ephemeral loopback port, per-run token, health wait, restricted capabilities, shutdown kill, parent-PID orphan protection, and release-only Tauri updater are implemented |
| Tauri macOS Apple Silicon | [done] | Fresh matching ARM64 Nuitka sidecar, loopback/token `/health` smoke, child cleanup, `cargo check`, and release `.app` bundle were verified on the current Apple Silicon host |
| Tauri macOS plain DMG | [done] | `scripts/build-tauri-dmg.sh` builds the matching app, creates a drag-to-Applications UDZO image with `hdiutil`, and verifies it without Finder automation; a 41 MB x86_64 smoke DMG was verified on the current host |
| Tauri macOS DMG styling | [blocked] | The app bundle succeeds, but the optional Finder-styled DMG wrapper invokes `osascript`; Finder AppleScript hangs in this headless in-app environment. `npx tauri build --bundles app` is verified instead |
| Tauri macOS Intel | [done] | A fresh `x86_64-apple-darwin` Nuitka sidecar, target `cargo check`, and unsigned production `.app` bundle were built on the ARM host; Rosetta authenticated `/health` and token-bound API smoke completed within the 30-second Tauri readiness window. Physical Intel UI/signing verification remains a release-host task |
| Tauri Windows | [in progress] | Windows Actions build/smoke-test the MSVC sidecar with explicit product metadata and an uncompressed payload, build NSIS updater artifacts, generate `latest.json`, and publish GitHub Releases. A real run remains dependent only on repository updater keys |
| Capacitor shared setup | [done] | iOS and Android projects, app identifier/name, icons/splash assets, safe-area/theme behavior, keyboard/status bar/network/external-link plugins, and `cap sync` are present |
| Capacitor iOS native build | [blocked] | Host has only Xcode Command Line Tools; full Xcode and the iPhoneOS SDK are unavailable |
| Capacitor Android native build | [blocked] | Host exposes Java 8, below the current Android toolchain requirement, and has no Android SDK, `adb`, or `sdkmanager` |
| Automated quality gates | [in progress] | Focused release/updater, content, integration, localization, help, and export Python suites pass; frontend typecheck/lint/104 Vitest tests/build, ARM64 and x86_64 `cargo check`, `cap sync`, sidecar smoke, and audit pass. Playwright and managed Chromium are installed for browser journeys; the in-app Browser has no available target, so final responsive screenshot review remains an environment limitation |
| Developer documentation | [done] | README/runbook cover backend/frontend/Web/Tauri/Capacitor commands, Windows releases, updater keys, data safety, tests, and platform limitations |

## Functional parity summary

### Migrated through the shared core and API

- Projects, stages, lifecycle, deadlines, all legacy progress units, visible
  global/project/stage streak state and effects, structured statistics, and local 1080 × 1080
  progress cards for finite projects and stages. Their share menu has separate
  clipboard and PNG-save actions; the card never sends manuscript or note
  content to a server.
- Project-note cards, tags, ordering, Mind Elixir data, floating/free nodes, and
  bidirectional `#карта` synchronization.
- Game profile, XP/levels, health, coins, inspiration, buffs, items, shop,
  writing sessions, daily/weekly challenges, creative rhythm, specializations,
  mastery, skills, quests, streak freezes, cabinet/relics/sets, custom awards,
  bank operations, and persisted bank/streak notification history.
- Localized help, the six-language catalog service, and the versioned
  user-agreement/acceptance contract used by the blocking frontend gate.
- Platform-aware settings, including legacy-compatible infinite-project and
  global-streak transitions with pre-change backups, all-project daily-total
  display, notification duration, inventory category, and isolated Vue list
  preferences.
- Desktop `.docx` and Scrivener paths, manual/all-source sync, background sync,
  nested Scrivener binder selection, hardened source snapshots and timestamps,
  atomic detach-all, and explicit `.docx` upload for remote clients.

### Implemented Vue routes

```text
/projects
/projects/:projectId
/projects/:projectId/notes
/game
/integrations
/help
/settings
```

All listed pages call FastAPI through the shared API client. They do not use
mock project/game data or direct pickle access. Before these routes render, the
application bootstrap reads backend preferences and blocks first use behind
the shared versioned user agreement unless it was already accepted.

## Achievement evidence

The legacy code does not declare a separate achievement entity or persistence
collection:

- `game_data.py` creates quest badges through `quest_award()` as `Item` objects
  with `item_type='Награды'`;
- those items are registered under `ITEM_REGISTRY['Награды']`;
- ownership is stored in `Gamer.items['Награды']` and was displayed by the
  legacy inventory;
- manuscript milestone/relic progress is represented separately by cabinet
  state.

The new game state and UI expose quests, the `Награды` inventory category, and
the cabinet instead of inventing a duplicate achievements store. Custom awards
remain user data with stable IDs and dedicated CRUD/use/buy/sell commands.

## Data-safety constraint

The shared repository serializes API/sidecar access. Historical Qt code still
contains direct multi-step writes and is unsupported; do not run it against an
active FastAPI/Tauri data directory. Development and tests should pass
`--data-dir` or `NFPROGRESS_DATA_DIR` pointing to an isolated temporary
directory. No test or startup path intentionally converts or deletes the
user's `.pkl` files.

## Platform verification and blockers

### Web

- Vue production output builds independently of Tauri and Capacitor imports.
- `VITE_API_BASE_URL` selects the remote API; local Vite development uses the
  same-origin proxy.
- A production operator must provide HTTPS, an authentication/reverse-proxy
  boundary where needed, and SPA history fallback. Offline writes are not
  implemented.

### Tauri Windows/macOS

- Apple Silicon sidecar lifecycle, loopback/token smoke, child cleanup, and
  release app bundle were exercised. `scripts/build-tauri-dmg.sh` makes a
  verified plain DMG with `hdiutil`; only optional Finder styling is blocked
  by headless AppleScript.
- Intel macOS now has a fresh x86_64 sidecar, target compile and unsigned app
  bundle. Its bundled backend passed loopback and session-token smoke through
  Rosetta in 25.1 seconds, within Tauri's 30-second readiness window. A native
  Intel UI run and release signing still require the matching release host.
- Windows requires a Windows/MSVC host or CI runner. The release workflow now
  owns that build, updater metadata, and signature verification; an actual
  signed run still requires configured repository keys and certificate. The
  Nuitka helper rejects a Windows sidecar build on macOS rather than creating a
  misleading artifact.

### Capacitor iOS/Android

- `cap sync` validates the generated web assets, native projects, and plugin
  configuration for both platforms.
- iOS native compilation cannot start because `xcode-select` resolves only to
  Command Line Tools and `xcrun --sdk iphoneos` cannot locate an SDK.
- Android native compilation cannot start with the host's Java 8 installation,
  and no Android SDK tools are installed.

These SDK/toolchain limits do not block Web, Python, Tauri ARM64, or repository
implementation work.

The in-app browser-control environment was unavailable for the final working
tree. Playwright and its managed Chromium are installed for repository browser
journeys, while direct in-app responsive screenshot inspection remains a
verification task.

## Remaining platform debt

- A real Word `.doc` reader, should the obsolete format become a supported
  product workflow again (the current flow requests `.docx`).
- Full Playwright coverage for the project → stage → progress → statistics,
  note ↔ mind-map, and writing-session reward journeys.
- A Windows workflow run with repository updater keys, plus native release/UI
  verification on physical macOS Intel hardware, iOS, and Android.

## Verification evidence

Checks completed for the final aggregate migration tree include:

- focused release/updater, content, integration, localization, help, and
  frontend-export Python checks pass;
- `npm run typecheck`, `npm run lint`, `npm run test` — 104 Vitest tests, and
  `npm run build` — all pass; `npm audit --audit-level=high` reports zero
  vulnerabilities;
- `cargo fmt --check`, ARM64 and x86_64 `cargo check`, app-only Tauri bundles,
  a headless `hdiutil`-verified UDZO DMG, fresh matching Nuitka sidecars,
  loopback/token `/health` smoke, and orphan-process checks all pass. The
  Intel sidecar was exercised through Rosetta in 25.1 seconds, inside the
  30-second Tauri readiness limit;
- `npx cap sync` passes for both generated mobile targets;
- explicit SDK probes confirm the iOS/Android blockers above.

The legacy desktop accessibility layer is installed with `QApplication` and
keeps Designer forms, project cards, and game-list entries semantically named
for screen readers. Browser-driven visual and Playwright critical-flow QA also
remain pending because the in-app Browser exposes no target in this environment.

## Main migration commits so far

- `efd5376` — document the migration architecture.
- `e1b2ce9` — add the shared Python core and FastAPI backend.
- `2abcaf8` — add the cross-platform Vue project workspace.
- `21881b1` — expose streak-freeze commands.
- `a436ae7` — apply uploaded Word progress through normal rules.
- `0457d63` — localize structured statistics.
- `be42aa7` — run desktop synchronization in the backend lifecycle.
- `045aa32` — preserve the nested Scrivener binder hierarchy.
- `7a793cd` — migrate safe progress-card sharing.
- `fcf46bd` — restore legacy accessibility semantics and keyboard metadata.
- `afd1fa5` — enforce the Qt-free shared-core import boundary.
- `fa0615e` — verify the macOS Intel Tauri target and sidecar lifecycle.
- `7a4a1f4` — add verified headless Tauri DMG packaging.

The current Game, Integrations, Help, Settings, agreement gate, strict
contracts, project-parity, and integration-hardening layers follow these
commits and are ready for logical migration commits.
