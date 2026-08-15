# Frontend migration status

Updated: 2026-08-15

| Subsystem | Status | Notes |
| --- | --- | --- |
| Repository and dependency audit | [done] | Core, game, storage, integrations, build scripts and available SDKs audited |
| Architecture and migration plan | [done] | Transitional architecture and data-safety decisions documented |
| Legacy PySide6 application | [done] | Preserved as the current fallback; no legacy UI removed |
| Storage repository and isolation | [done] | Thread-safe explicit data roots retain atomic legacy pickle files; backup and isolation tests added |
| JSON-safe exchange models | [in progress] | Projects, stages, progress, notes, maps, settings, game, content and integration results covered |
| Project/stage application services | [done] | CRUD, lifecycle, stages, progress and statistics use stable IDs through shared services |
| Notes and Mind Elixir service | [done] | Qt-free CRUD, ordering, aggregate maps and bidirectional synchronization are exposed through the API |
| Game and writing-session service | [in progress] | Authoritative game/session/challenge/shop commands added; remaining legacy cabinet workflows are being audited |
| Word/Scrivener integration service | [in progress] | Desktop paths and explicit Word uploads run through the shared project service |
| FastAPI and OpenAPI contract | [in progress] | App factory, errors, loopback token, CORS, health and initial complete router set implemented |
| Vue/Ionic application shell | [done] | Typed API client, responsive navigation, design tokens, themes, locale loading and network state build successfully |
| Project workspace | [done] | Search, filters, CRUD, lifecycle, stages, all progress units and thirteen statistics metrics use the real API |
| Notes and mind-map frontend | [done] | Notes CRUD/autosave and the canonical Mind Elixir assets use the real synchronization API |
| Game frontend | [pending] | Inventory, shop, quests, rhythm, sessions, challenges, cabinet |
| Localization export | [in progress] | Deterministic Python-catalog-to-JSON exporter and drift test implemented |
| Help export and frontend | [in progress] | Localized `HELP_SECTIONS` export and API implemented; Vue help surface pending |
| Web/PWA target | [in progress] | Production build, remote API config, manifest, branding and responsive project/notes workflows pass |
| Tauri 2 target | [in progress] | `cargo check`, release macOS ARM app bundle, loopback token and crash-safe Nuitka sidecar lifecycle pass; Intel/Windows builds remain |
| Capacitor iOS target | [in progress] | Native target, branding, plugins and `cap sync` pass; full Xcode/iPhoneOS SDK are absent, so native build is [blocked] |
| Capacitor Android target | [in progress] | Native target, branding, plugins and `cap sync` pass; build is [blocked] by host Java 8 (AGP requires JVM 11+) and missing Android SDK |
| Documentation and final parity matrix | [pending] | README and remaining legacy debt |
