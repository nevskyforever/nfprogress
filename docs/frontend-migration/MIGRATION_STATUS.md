# Frontend migration status

Updated: 2026-08-23

`[done]` means the repository implementation for that row exists and has been
checked on an available host; it does not imply that every native release is
signed or verified. `[blocked]` is reserved for a concrete external SDK/toolchain
blocker. The PySide6 application remains the release fallback.

## Subsystem matrix

| Subsystem | Status | Evidence and remaining work |
| --- | --- | --- |
| Repository/dependency audit | [done] | Core, UI, game, storage, integrations, build scripts, and available native SDKs audited |
| Architecture and migration plan | [done] | Transitional boundaries, data safety, transports, platform capabilities, and debt documented |
| Legacy PySide6 preservation | [done] | Existing desktop UI and build files remain; no legacy workflow was deleted for the migration |
| Complete Qt retirement | [pending] | Legacy remains required for the updater, progress-share clipboard image, and native macOS Help search |
| Qt-free application services | [in progress] | Projects, notes/maps, game, settings/content, and integrations are service-backed; proven domain classes still physically live in `engine.py`, `game.py`, and `game_data.py` behind compatibility imports |
| Storage repository/isolation | [done] | Explicit data roots, in-process and advisory locks, atomic legacy pickle writes, idempotent streak handling, temporary-directory tests, timestamped backups before destructive setting transitions, and a one-time backup before persisted notification IDs are present |
| JSON-safe exchange contract | [done] | Page-facing project/integration, content/settings, note/map, notification-history, and complete game state/catalog/command envelopes have explicit Pydantic contracts; compatibility JSON remains intentionally extensible only for Mind Elixir, history/results, and unknown legacy metadata |
| Project/stage service | [done] | CRUD, states, archive/completion, stages, all progress units, deadlines, infinite projects, structured statistics, and the all-project writing-day summary use stable IDs |
| Notes and Mind Elixir service | [done] | CRUD, ordering, normalization, aggregate maps, and bidirectional `#карта` synchronization are exposed without Qt |
| Game and writing-session service | [done] | Server-authoritative profile, buffs, freezes, sessions, challenges, shop/inventory, inspiration, specializations/mastery, creative events, skills/quests, cabinet, custom awards, bank commands, and persisted unread/read bank or streak events are exposed |
| Achievement/award mapping | [done] | Legacy has no separate `Achievement` model: quest badges remain canonical `Награды` inventory items; manuscript milestones remain cabinet state; custom awards have separate commands |
| Settings semantics | [done] | `inf_project` creates/removes canonical `Общий проект`; disabling it or a populated `global_streak` creates a timestamped data/settings backup before applying the legacy-compatible destructive transition |
| User-agreement service/gate | [done] | Versioned canonical agreement API, legacy-compatible acceptance flag, blocking Vue bootstrap gate, language switching, retry, accessible acceptance, and guarded Tauri decline/close behavior are implemented |
| Word/Scrivener service | [done] | Direct desktop `.docx`/Scrivener sync, nested binder inspection, remote `.docx` application, source mtime preservation, stale/missing/future-source protection, typed errors, and atomic detach-all are implemented; `.doc` is unsupported and asks for `.docx` rather than silently changing data |
| Desktop background sync | [done] | Desktop-only worker runs configured active sources off the event loop on enable/start and writing-day change, isolates per-source failures, and shuts down with FastAPI |
| FastAPI/OpenAPI | [done] | Health, centralized errors, loopback token, CORS, typed page-facing response contracts, and every router required by the Vue application are implemented; remote HTTPS/auth remains an operator deployment boundary, not an embedded account system |
| Vue/Ionic shell | [done] | Responsive desktop/mobile navigation, platform guards, network/startup errors, design tokens, focus/reduced-motion support, themes, and locale store are implemented |
| Projects/stages/progress frontend | [done] | Real API powers project list/search/filter/sort, project and stage editing/lifecycle, all units, deadlines, progress recording, and immediate refresh |
| Statistics frontend | [done] | Structured Python calculations and localized labels are displayed responsively; calculations are not duplicated in TypeScript |
| Notes/Mind Elixir frontend | [done] | Note cards/autosave and canonical Mind Elixir assets use the real notes/map API and synchronization rules |
| Game frontend | [done] | Seven responsive panels cover overview, sessions, challenges, items, growth, cabinet, and awards/bank; a global responsive notification center exposes persisted bank/streak history, and every command reloads authoritative backend state |
| Integrations frontend | [done] | Desktop dialogs, configured project/stage sync and detach, recursive Scrivener selection, manual/all-source runs, and remote `.docx` upload are wired to the real API; no client claims unsupported `.doc` access |
| Settings frontend | [done] | Language, light/dark/system theme, writing-day start, notification duration, game mode, infinite project, global streak, all-project daily total, desktop-only background sync, inventory category, and frontend list preferences are platform-gated and persisted through the settings service |
| Localization pipeline | [done] | Six canonical Python catalogs, deterministic frontend export/drift check, Vue/TypeScript source extraction, HTML/placeholder validation, and the final catalog regression checks pass |
| Help frontend | [done] | Localized canonical `HELP_SECTIONS`, nested navigation, article rendering, in-window search, and keyboard search shortcut use the real content API |
| Web target | [done] | Production Vue build, remote URL configuration, manifest, responsive routes, platform guards, and backend-unavailable states are verified; deployment HTTPS/auth, SPA fallback, and offline mutation behavior remain operator concerns rather than bundled claims |
| Tauri lifecycle/security | [done] | Ephemeral loopback port, per-run token, health wait, restricted capabilities, shutdown kill, and parent-PID orphan protection are implemented |
| Tauri macOS Apple Silicon | [done] | Fresh matching ARM64 Nuitka sidecar, loopback/token `/health` smoke, child cleanup, `cargo check`, and release `.app` bundle were verified on the current Apple Silicon host |
| Tauri macOS DMG styling | [blocked] | The app bundle succeeds, but the optional Finder-styled DMG wrapper invokes `osascript`; Finder AppleScript hangs in this headless in-app environment. `npx tauri build --bundles app` is verified instead |
| Tauri macOS Intel | [pending] | Intel sidecar target is supported, but the matching Rust/Tauri bundle and runtime verification were not performed on the ARM host |
| Tauri Windows | [pending] | Windows MSVC target is configured; sidecar builder deliberately requires a Windows host/runner, so bundle/runtime verification remains |
| Capacitor shared setup | [done] | iOS and Android projects, app identifier/name, icons/splash assets, safe-area/theme behavior, keyboard/status bar/network/external-link plugins, and `cap sync` are present |
| Capacitor iOS native build | [blocked] | Host has only Xcode Command Line Tools; full Xcode and the iPhoneOS SDK are unavailable |
| Capacitor Android native build | [blocked] | Host exposes Java 8, below the current Android toolchain requirement, and has no Android SDK, `adb`, or `sdkmanager` |
| Automated quality gates | [in progress] | Aggregate migration Python suite: 411 passed, 15 skipped, 2 subtests passed; frontend typecheck/lint/70 Vitest tests/build, `cargo fmt --check`/`cargo check`, `cap sync`, sidecar smoke, and audit pass. The retained legacy accessibility test cannot collect because this base branch lacks `accessibility.py`; in-app Browser has no available target, so visual/Playwright journeys remain unverified |
| Developer documentation | [done] | README covers legacy/backend/frontend/Web/Tauri/Capacitor commands, data safety, platform limitations, tests, and current target status |

## Functional parity summary

### Migrated through the shared core and API

- Projects, stages, lifecycle, deadlines, all legacy progress units, global and
  project streak effects, and structured statistics.
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

The shared repository serializes API/sidecar access, but the legacy Qt code
still contains direct multi-step writes. Do not run `main_UI.py` and the new
FastAPI/Tauri backend against the same data directory concurrently. Development
and tests should pass `--data-dir` or `NFPROGRESS_DATA_DIR` pointing to an
isolated temporary directory. No test or startup path intentionally converts or
deletes the user's `.pkl` files.

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
  release app bundle were exercised. The optional Finder-styled DMG is blocked
  only by headless AppleScript; an app-only production bundle succeeds.
- Intel macOS remains a cross-target build/runtime verification task. The
  sidecar builder can emit `x86_64-apple-darwin` on macOS, but a matching Rust
  target and Intel validation are still required.
- Windows requires a Windows/MSVC host or CI runner. The Nuitka helper rejects
  a Windows sidecar build on macOS rather than creating a misleading artifact.

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
tree, so responsive screenshot inspection and browser-driven critical journeys
remain a verification task even where component tests and production builds
have passed in earlier slices.

## Remaining legacy debt

- Qt updater/installer and release signing/update metadata.
- A real Word `.doc` reader, should the obsolete format become a supported
  product workflow again (the current legacy and new flows request `.docx`).
- Progress-share image rendering and clipboard copy.
- Native macOS Help-menu search bridge (`NSUserInterfaceItemSearching`).
- Full Playwright coverage for the project → stage → progress → statistics,
  note ↔ mind-map, and writing-session reward journeys.
- Native release/signing/runtime verification on Windows, macOS Intel, iOS,
  and Android.

## Verification evidence

Checks completed for the final aggregate migration tree include:

- `python3 -m pytest -q --ignore=tests/test_accessibility.py` — 411 passed,
  15 skipped, 2 subtests passed; focused localization/help/export checks add
  44 passing tests;
- `npm run typecheck`, `npm run lint`, `npm run test` — 70 Vitest tests, and
  `npm run build` — all pass; `npm audit --audit-level=high` reports zero
  vulnerabilities;
- `cargo fmt --check`, `cargo check`, `npx tauri build --bundles app`, a fresh
  Nuitka ARM64 sidecar, loopback/token `/health` smoke, and orphan-process
  check all pass;
- `npx cap sync` passes for both generated mobile targets;
- explicit SDK probes confirm the iOS/Android blockers above.

`tests/test_accessibility.py` is retained from the base project but imports an
`accessibility.py` module absent from this branch (it exists in an unmerged
legacy branch), so an unfiltered `pytest -q` stops at collection. This is a
pre-existing legacy test/module mismatch, not a migration service/API/frontend
failure. Browser-driven visual and Playwright critical-flow QA also remain
pending because the in-app Browser exposes no target in this environment.

## Main migration commits so far

- `efd5376` — document the migration architecture.
- `e1b2ce9` — add the shared Python core and FastAPI backend.
- `2abcaf8` — add the cross-platform Vue project workspace.
- `21881b1` — expose streak-freeze commands.
- `a436ae7` — apply uploaded Word progress through normal rules.
- `0457d63` — localize structured statistics.
- `be42aa7` — run desktop synchronization in the backend lifecycle.
- `045aa32` — preserve the nested Scrivener binder hierarchy.

The current Game, Integrations, Help, Settings, agreement gate, strict
contracts, project-parity, and integration-hardening layers follow these
commits and are ready for logical migration commits.
