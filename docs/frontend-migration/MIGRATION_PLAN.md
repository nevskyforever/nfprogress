# Frontend migration plan

Migration is delivered as verified vertical slices. Legacy packaging is
retired; each slice must preserve existing user data and must not touch real
user files in tests.

## Persistence preparation: PKL-authoritative shadow mirror

This stage deliberately does not migrate runtime reads or business logic:

```text
Vue / TypeScript -> FastAPI -> Python Core -> PickleRepository -> PKL (authoritative)
                                                               \-> SQLite (shadow)
```

The versioned `nfprogress.db` schema stores relational project, stage, progress,
note, and settings rows. Complex legacy state, including the game state and
extensible Mind Elixir data, remains standard UTF-8 JSON payload text. SQLite
can be deleted and rebuilt from PKL. The intended future sequence is:

1. Phase 1: Python writes PKL and mirrors successful writes to SQLite.
2. Phase 2: Python remains authoritative while mirror health is monitored.
3. Phase 3: selected subsystems may write SQLite from TypeScript.
4. Phase 4: TypeScript uses SQLite; Python is a compatibility layer.
5. Phase 5: PKL is retained only as legacy import/backup format.

Phases 3–5 are not implemented here; SQLite is not yet the TypeScript
authoritative database.

### Stage 3: read-only SQLite project repository

The first SQLite-to-TypeScript path is limited to project, stage, and progress
reads. Tauri's Rust bridge uses `rusqlite` in `SQLITE_OPEN_READ_ONLY` mode and
exposes fixed queries only. The API remains the fallback and the only command
source; no TypeScript SQLite writes or migrations are allowed. Manual list
ordering is intentionally API-owned until `project_order` is represented safely
in the mirror.

## TS Core migration phase 1: pure project calculations

The first TypeScript Core slice contains only verified, side-effect-free unit
conversion, percentage, remaining-work, and project-form planning calculations.
Python remains authoritative for persisted mutations and all model-derived
plans. The TypeScript functions receive dates explicitly, preserve the legacy
rounding rules, and use `null` with an explicit `infinite` flag for unbounded
goals. This phase does not change the API, PKL, SQLite shadow mirror, or Python
runtime calls.

## TS Core migration phase 2: read-only statistics

`frontend/src/core/statistics` calculates the verified pure subset from JSON-safe
project/stage data: entry counts, totals, averages, best day/weekday, project
age, active-day percentage, and timeline. Stage projects aggregate stage entries
as `get_notes_with_stage_names()` does; a selected stage uses only its entries.
Dates come from serialized effective writing-day dates and the explicit planning
date, so the core never reads the browser clock. The adapter merges these
results with Python-owned `freezes_used`, `current_streak`, and `max_streak`.
`/statistics`, PKL, and the SQLite shadow mirror remain unchanged.

## 1. Shared Python application layer

1. Add a context-local data directory override and repository lock.
2. Add JSON-safe serializers for projects, stages, progress, statistics,
   settings, notes, mind maps, game state, inventory, challenges, sessions,
   achievements, localization, and help.
3. Implement project/stage CRUD, progress, statistics, notes/mind-map,
   settings, game, and file-integration services.
4. Cover storage isolation and service commands with focused tests.

## 2. FastAPI contract

1. Add an application factory with dependency injection, centralized domain
   errors, CORS, optional desktop session token, `/health`, and OpenAPI.
2. Add thin routers for projects/stages/progress/statistics, notes/maps,
   settings/content, game/session commands, and desktop file integrations.
3. Add API tests for the critical workflows and malformed input.

## 3. Vue/Ionic application

1. Create Vue 3 + TypeScript + Vite + Ionic Vue, Router, and Pinia setup.
2. Add design tokens, responsive shell, theme selection, accessible focus and
   reduced-motion behavior.
3. Implement project workspace, stages, progress history, statistics, notes,
   mind maps, game/rhythm/session surfaces, settings, and help against the real
   API client.
4. Add typecheck, Vitest/Vue Test Utils tests, production build, and focused
   Playwright coverage when the browser environment supports it.

## 4. Runtime targets

1. Add Web/PWA manifest, direct-route fallback documentation, network/error
   state, and environment-based remote API configuration. Do not claim an
   offline shell or offline mutation queue until one is implemented.
2. Add Capacitor iOS/Android targets, safe-area/platform styling, status bar,
   external links, explicit file selection, icons/splash, and `cap sync` checks.
3. Add Tauri 2 shell, minimal capabilities, dynamic loopback port/token,
   Nuitka sidecar build scripts, health wait, startup errors, and reliable child
   termination. Run `cargo check` and platform builds where SDKs exist.

## 5. Parity and handoff

1. Run focused Python compatibility and service tests, frontend tests/typecheck/build,
   Capacitor sync, and Tauri checks.
2. Exercise critical end-to-end flows with a temporary data directory.
3. Update README, architecture, platform limitations, and migration status.
4. Keep compatibility code only where existing data or regression evidence
   still requires it; do not publish PySide6 packages.

## Definition of a migrated subsystem

A subsystem is marked done only when its real persistent data is read and
mutated through the shared service/API, the frontend exposes its supported
workflow without mock data, and relevant automated checks pass. A generated
screen without backend integration remains in progress.
