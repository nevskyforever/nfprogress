# Frontend migration status

Updated: 2026-08-15

| Subsystem | Status | Notes |
| --- | --- | --- |
| Repository and dependency audit | [done] | Core, game, storage, integrations, build scripts and available SDKs audited |
| Architecture and migration plan | [done] | Transitional architecture and data-safety decisions documented |
| Legacy PySide6 application | [done] | Preserved as the current fallback; no legacy UI removed |
| Storage repository and isolation | [pending] | Existing atomic pickle format will remain authoritative |
| JSON-safe exchange models | [pending] | Stable project/stage identifiers already exist in legacy models |
| Project/stage application services | [pending] | CRUD, progress and statistics workflows to extract |
| Notes and Mind Elixir service | [pending] | Existing synchronization rules identified |
| Game and writing-session service | [pending] | Existing `Gamer` calculations remain authoritative |
| Word/Scrivener integration service | [pending] | Existing readers are reusable; platform selection must be separated |
| FastAPI and OpenAPI contract | [pending] | Includes loopback token mode and remote mode |
| Vue/Ionic application shell | [pending] | Responsive and accessible design system required |
| Project workspace | [pending] | Projects, stages, progress, statistics and status actions |
| Notes and mind-map frontend | [pending] | Existing Mind Elixir editor will be hosted directly |
| Game frontend | [pending] | Inventory, shop, quests, rhythm, sessions, challenges, cabinet |
| Localization export | [pending] | Python catalog remains canonical |
| Help export and frontend | [pending] | `HELP_SECTIONS` remains canonical |
| Web/PWA target | [pending] | Remote API URL via `VITE_API_BASE_URL` |
| Tauri 2 target | [pending] | Rust/Cargo is not installed; implementation can proceed but `cargo check` is currently [blocked] |
| Capacitor iOS target | [pending] | Full Xcode, iPhoneOS SDK and CocoaPods are absent; native build is [blocked] |
| Capacitor Android target | [pending] | Android SDK/Gradle and a modern JDK are absent; native build is [blocked] |
| Documentation and final parity matrix | [pending] | README and remaining legacy debt |
