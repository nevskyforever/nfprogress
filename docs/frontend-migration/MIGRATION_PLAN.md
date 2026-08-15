# Frontend migration plan

Migration is delivered as verified vertical slices. Each slice must leave the
legacy desktop application runnable and must not touch real user files in
tests.

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

1. Add Web/PWA manifest, direct-route fallback documentation, offline shell,
   network/error state, and environment-based remote API configuration.
2. Add Capacitor iOS/Android targets, safe-area/platform styling, status bar,
   external links, explicit file selection, icons/splash, and `cap sync` checks.
3. Add Tauri 2 shell, minimal capabilities, dynamic loopback port/token,
   Nuitka sidecar build scripts, health wait, startup errors, and reliable child
   termination. Run `cargo check` and platform builds where SDKs exist.

## 5. Parity and handoff

1. Run focused legacy and new Python tests, frontend tests/typecheck/build,
   Capacitor sync, and Tauri checks.
2. Exercise critical end-to-end flows with a temporary data directory.
3. Update README, architecture, platform limitations, and migration status.
4. Keep unmatched PySide6 workflows documented as fallback debt; remove no
   legacy code without proof of replacement.

## Definition of a migrated subsystem

A subsystem is marked done only when its real persistent data is read and
mutated through the shared service/API, the frontend exposes its supported
workflow without mock data, and relevant automated checks pass. A generated
screen without backend integration remains in progress.
