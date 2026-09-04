# NFProgress — F11 release gate checklist

Private qualification only. Production manifests remain untouched and no
public release is authorized.

## Distribution policy

- [x] Unsigned/ad-hoc/self-signed distribution is explicitly accepted by the owner.
- [x] Gatekeeper and SmartScreen warnings are documented as known `P1` limitations.
- [x] Developer ID, notarization, and Authenticode remain optional future hardening.
- [x] OS signing is not conflated with Tauri updater cryptographic signing.
- [x] No credentials or private keys were committed.

## Functional gates

| Gate | Result | Evidence/remaining requirement |
| --- | --- | --- |
| ARM Tauri build/package/provenance | PASS | real arm64 ZIP, DMG verification, source revision check |
| ARM helper build and smoke | PASS | real arm64 helper; detect/preview/prepare/verify |
| ARM Tauri first launch/restart | NOT TESTED | active installed single-instance process prevented isolated launch |
| ARM full transition | BLOCKED | install/launch/restart leg remains |
| Intel app/helper/runtime | DEFERRED | macOS Intel is not in initial rollout scope; support remains retained |
| Windows app/helper/NSIS/runtime | NOT TESTED | Windows x64 runner required |
| transition handoff release | BLOCKED | minimal transitional Python release not implemented/qualified |
| transition metadata | PASS (fixture) | F10 documentation fixture validates target/platform shape; production values remain unassigned |
| Tauri updater valid/invalid crypto | PASS (ephemeral test key) | matching `.sig` accepted and tampered payload rejected by `minisign-verify`; production key continuity not proven |
| interrupted transition/recovery | NOT TESTED on packaged installers | helper/recovery unit coverage exists |

## Regression gates

- Python focused profile: **68 passed, 2 subtests passed**.
- Full Python suite: **578 passed, 8 failed, 15 skipped, 2 subtests passed**;
  completed in 32.68s, no hang reproduced.
- Rust: `cargo fmt --check`, `cargo check`, `cargo test`: **32 passed**.
- Frontend: typecheck passed; **261 tests passed**; production build passed.
- F9/F8 helper/recovery tests: included in focused profile and passed.

The eight full-suite failures are exact nodes:

1. `tests/test_accessibility.py::test_ui_templates_expose_names_labels_and_tab_order`
   — legacy PySide template.
2. `tests/test_api_game_contracts.py::test_openapi_exposes_game_state_catalog_and_command_models`
   — Web OpenAPI response contract.
3. `tests/test_api_game_contracts.py::test_representative_full_game_state_and_commands_validate`
   — Web API Game contract fixture.
4. `tests/test_core_game_service.py::test_progress_streak_events_are_idempotent_per_server_day`
   — legacy Python date-boundary mismatch.
5. `tests/test_core_game_service.py::test_streak_recovery_repairs_project_marker_without_duplicate_reward`
   — legacy Python date-boundary mismatch.
6. `tests/test_project_service.py::test_project_stage_progress_and_statistics_round_trip`
   — legacy Python date-boundary mismatch.
7. `tests/test_project_service.py::test_project_reads_refresh_automatic_local_and_global_streaks`
   — legacy Python date-boundary mismatch.
8. `tests/test_quests_catalog.py::test_week_symbol_quest_counts_last_seven_days`
   — legacy weekly quest boundary.

The historical baseline has three failure categories: legacy accessibility,
Web OpenAPI/Game contract, and weekly-symbol/date-boundary behavior. The
current wall-clock run exposes eight nodes across those categories plus the
four date-sensitive service assertions. They are not Tauri desktop runtime
tests, but should be triaged before claiming the entire Python product suite
green. No test was excluded to manufacture a pass.

## Revised P0/P1 and final status

Initial rollout scope: **macOS ARM64 and Windows x64**. macOS Intel remains
supported by the build but is **DEFERRED / NOT IN INITIAL RELEASE SCOPE** and
is a P1 backlog item, not a current release gate.

Current P0:

- full ARM helper → installer → Tauri launch → restart transition;
- real Windows x64 build, packaged helper, NSIS install, launch, restart, and
  `%APPDATA%\\nfprogress`/historical fallback verification;
- minimal transitional Python delivery/handoff and no-update-loop proof;
- production Tauri updater key embedded in the release configuration plus
  valid/invalid signature verification on the actual updater path;
- interrupted transition, recovery, and first-launch failure evidence.

Current P1:

- Developer ID and notarization for macOS;
- Authenticode for Windows;
- Intel helper/runtime/migration qualification and a later macOS Intel rollout;
- release-note/support UX for Gatekeeper and SmartScreen;
- resolution of legacy-only Python suite failures before broad legacy support.

Final F11 status: **BLOCKED**. This status is caused by unqualified
functional/runtime transition gates, not by absent OS signing credentials.

Intended initial platform set: macOS ARM64 and Windows x64. Intel is explicitly
excluded from this initial wave, so its missing runtime evidence does not make
the initial release `BLOCKED`.
