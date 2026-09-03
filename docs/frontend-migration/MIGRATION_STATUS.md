# NFProgress — migration status

Updated against baseline `04b62c3970b22c43b9f604f79ee6de17243179f2` on
2026-09-04.

This status distinguishes implemented features from authoritative storage.
No implementation milestone was started by the fast-track audit.

## Current ownership

```text
projects/stages/progress = PKL authoritative
settings                 = SQLite authoritative
notes                    = SQLite authoritative
game                     = PKL authoritative
```

| Domain | Current desktop path | Status |
| --- | --- | --- |
| Projects/stages/progress | Healthy SQLite read projection; typed metadata/order and manual progress commands call authenticated Python, which writes PKL and rebuilds the mirror | Transitional P3 boundary; not cut over |
| Settings | Typed Rust SQLite commands for ordinary settings; coupled project transitions still call Python/API | SQLite-authoritative, coupled behavior remains Python |
| Notes | Typed Rust SQLite CRUD/order; map normalization, reconciliation and XMind still use Python/API | SQLite-authoritative notes; map document path remains transitional |
| Game | Python GameService and `gamer.pkl`; broad `game_state` mirror | Not cut over |
| Documents | Vue/Tiptap plus Python `documents.json` service | Separate JSON store; not in SQLite |
| Word/Scrivener/sync | Python sidecar parser and minute background task | Python-dependent |

## Completed foundations

- versioned SQLite schema through v3, ownership table, mirror health and
  semantic verifier;
- explicit data roots, process/advisory locking and atomic PKL writes;
- SQLite Settings and Notes controlled cutovers;
- complete ordered Projects/Stages/Progress read projection;
- P2 typed metadata/order boundary;
- P3 typed manual progress add/delete boundary and parity-tested TS
  conversion/normalization/statistics helpers;
- typed Tauri DTOs and fixed SQL for current direct Settings/Notes/read paths.

These foundations are retained. They do not prove that Projects or Game are
SQLite-authoritative and do not prove that the v3 database is a lossless user
backup.

## Audit conclusions

- `projects`, `stages`, `progress_entries`, `project_order`, Settings, Notes
  and broad Game JSON are present in SQLite under the conditions described in
  [`FAST_TRACK_AUDIT.md`](FAST_TRACK_AUDIT.md).
- Project envelope fields (`project_folders`, notifications/global streak),
  actual `synch`/`last_synch` bindings, `documents.json`, unknown Project
  attributes and external files are not guaranteed in SQLite.
- The current Rust path does not run the Python schema migrations. A final
  direct upgrade therefore needs a migration-only importer and Rust/open
  migration support.
- No additional user-facing bridge release is recommended if the final
  distribution provides a separately tested one-shot legacy importer. Without
  that helper, a bridge release is mandatory.

## Known baseline Python failures

The suite at this baseline reports `517 passed, 8 failed, 15 skipped`.

| Test | Classification | Migration impact |
| --- | --- | --- |
| `tests/test_accessibility.py::test_ui_templates_expose_names_labels_and_tab_order` | Legacy PySide6 UI template: `lottery_ticket.ui` has focusable controls but no `<tabstops>` | Obsolete for Vue/Tauri; does not block desktop migration, but must be retired or fixed before claiming the full legacy suite is green. |
| `tests/test_api_game_contracts.py::test_openapi_exposes_game_state_catalog_and_command_models` | Game API schema contract: developer endpoint returns `DeveloperModeResponse`, while the test assumes all non-read paths are `GameCommandResponse` | Relevant to the Python oracle/API contract; resolve or explicitly narrow the test before F3 parity sign-off. |
| `tests/test_api_game_contracts.py::test_representative_full_game_state_and_commands_validate` | Game contract fixture observes no eligible streak-freeze project after current date/test-clock behavior | Relevant to Game/progress parity; blocks F3 until behavior is fixed, test clock is isolated, or the behavior is explicitly retired with a replacement. |
| `tests/test_core_game_service.py::test_progress_streak_events_are_idempotent_per_server_day` | Date/test-clock mismatch: saved reward marker is 2026-09-04 while the assertion expects 2026-09-03 | Relevant to progress/Game event parity; blocks F2/F3 time semantics. |
| `tests/test_core_game_service.py::test_streak_recovery_repairs_project_marker_without_duplicate_reward` | Same date/test-clock mismatch in recovery marker | Relevant to idempotent recovery; blocks F3. |
| `tests/test_project_service.py::test_project_stage_progress_and_statistics_round_trip` | Same date/test-clock mismatch in progress statistics | Relevant to F2 progress parity; blocks F2 until deterministic clock ownership is established. |
| `tests/test_project_service.py::test_project_reads_refresh_automatic_local_and_global_streaks` | Same date/test-clock mismatch in today summary | Relevant to lifecycle/streak read semantics; blocks F2 if today summaries remain supported. |
| `tests/test_quests_catalog.py::test_week_symbol_quest_counts_last_seven_days` | Week quest boundary/date behavior does not match the test fixture | Relevant to F3 only; not a storage blocker, but must be fixed or retired before quest parity. |

The six date/game/progress failures must not be relabeled “pre-existing” and
then carried through the port without a decision. The accessibility failure is
legacy UI-only. The OpenAPI failure is a contract-test mismatch, not evidence
of storage loss.

## New roadmap status

| Milestone | Status | Risk / Codex recommendation |
| --- | --- | --- |
| F1 storage contract, Rust migrations and one-shot legacy importer | Not started | Very High / Luna High; Sol only for pickle/parser or integrity design |
| F2 Projects/Stages/Progress SQLite-authoritative cutover | Not started | Very High / Luna High |
| F3 Game SQLite/event cutover | Not started | Very High / Luna High |
| F4 Mind Elixir/XMind | Not started | High / Luna Medium–High |
| F5 Documents/Word/Scrivener/background sync | Not started | High / Luna Medium–High |
| F6 Python-free Tauri packaging/runtime | Not started | High / Luna Medium–High |
| F7 migration, backup/restore and release qualification | Not started | Very High / Luna High; Sol for cross-platform release/integrity issues |

P1–P3 are complete foundations and are absorbed into F1/F2. P4 is absorbed
into F2 with a durable Game event contract. P5 is split into F4 and F5. P6/P7
are combined into F3. P8 is F6. P9 is split between F1 and F7.

## Do not start automatically

The next action after this documentation commit requires explicit approval to
start F1. This replan does not switch ownership, change the schema, delete
Python, delete sidecar/PKL, or begin Projects/Game/Integration implementation.
