# NFProgress — migration status

Updated for F3 against implementation HEAD
`29e064dceeb2fc4dae9f1eba88bdc34cc7ac6969` on 2026-09-04.

This status distinguishes implemented features from authoritative storage.
F1/F2 storage foundations and the F3 Game owner switch are implemented. The
Python sidecar remains a transitional compatibility transport until F6.

## Current ownership

```text
projects/stages/progress = SQLite authoritative
settings                 = SQLite authoritative
notes                    = SQLite authoritative
game                     = SQLite authoritative
```

| Domain | Current desktop path | Status |
| --- | --- | --- |
| Projects/stages/progress | Typed Vue/Tauri commands → Rust → SQLite, with durable Game outbox events | SQLite-authoritative; Python remains the web/compatibility adapter |
| Settings | Typed Rust SQLite commands for ordinary settings; coupled project transitions still call Python/API | SQLite-authoritative, coupled behavior remains Python |
| Notes | Typed Rust SQLite CRUD/order; map normalization, reconciliation and XMind still use Python/API | SQLite-authoritative notes; map document path remains transitional |
| Game | SQLite `game_state` DTO, deterministic event consumer, compatibility HTTP façade | SQLite-authoritative; PKL recovery-only |
| Documents | Vue/Tiptap plus Python `documents.json` service | Separate JSON store; not in SQLite |
| Word/Scrivener/sync | Python sidecar parser and minute background task | Python-dependent |

## Completed foundations

- versioned SQLite schema through v5, ownership table, mirror health and
  semantic verifier;
- explicit data roots, process/advisory locking and atomic PKL writes;
- SQLite Settings and Notes controlled cutovers;
- complete ordered Projects/Stages/Progress read projection;
- P2 typed metadata/order boundary;
- P3 typed manual progress add/delete boundary and parity-tested TS
  conversion/normalization/statistics helpers;
- typed Tauri DTOs and fixed SQL for current direct Settings/Notes/read paths;
- shared Python/Rust migration files, canonical Projects migration DTO,
  transactional/idempotent import, typed Rust Projects repository primitives,
  folders/bindings/extensions and Notes-safe FK policy.

F3 adds GameMigrationBundle v1, owner verification/guard, SQLite Gamer
encoding with unknown-field preservation, Game-owned notifications and
global/project streak materialization, plus atomic retryable outbox consumers
in Python compatibility and trusted Rust boundaries.

These foundations are retained. Documents and external-file manifests remain
F5 concerns; the SQLite backup now contains authoritative Game state.

## Audit conclusions

- `projects`, `stages`, `progress_entries`, `project_order`, Settings, Notes
  and broad Game JSON are present in SQLite under the conditions described in
  [`FAST_TRACK_AUDIT.md`](FAST_TRACK_AUDIT.md).
- Project folders, actual `synch`/`last_synch` bindings, unknown
  Project/Stage fields and stable progress order are now represented in v4.
- Notifications/global streak are now Game-owned in SQLite; `documents.json`
  and external files remain F5 concerns.
- A migration-only Python helper is selected for legacy PKL parsing. Rust does
  not execute arbitrary pickle object behavior and now runs the shared schema
  migrations at DB open.
- No additional user-facing bridge release is recommended if the final
  distribution provides a separately tested one-shot legacy importer. Without
  that helper, a bridge release is mandatory.

## Known baseline Python failures

The suite at the F3 baseline HEAD reports `530 passed, 3 failed, 15 skipped,
2 subtests passed`.

| Test | Classification | Migration impact |
| --- | --- | --- |
| `tests/test_accessibility.py::test_ui_templates_expose_names_labels_and_tab_order` | Legacy PySide6 UI template: `lottery_ticket.ui` has focusable controls but no `<tabstops>` | Obsolete for Vue/Tauri; does not block desktop migration, but must be retired or fixed before claiming the full legacy suite is green. |
| `tests/test_api_game_contracts.py::test_openapi_exposes_game_state_catalog_and_command_models` | Game API schema contract: developer endpoint returns `DeveloperModeResponse`, while the test assumes all non-read paths are `GameCommandResponse` | Relevant to the Python oracle/API contract; resolve or explicitly narrow the test before F3 parity sign-off. |
| `tests/test_quests_catalog.py::test_week_symbol_quest_counts_last_seven_days` | Week quest boundary/date behavior does not match the test fixture | Relevant to F3 only; not a storage blocker, but must be fixed or retired before quest parity. |

The accessibility failure is legacy UI-only. The OpenAPI failure is a contract
test mismatch, not evidence of SQLite storage loss. The week quest failure is
the remaining relevant legacy-oracle issue and is recorded for parity follow-up.

## New roadmap status

| Milestone | Status | Risk / Codex recommendation |
| --- | --- | --- |
| F1 storage contract, Rust migrations and one-shot legacy importer | Complete (storage foundation) | Very High / Luna High; importer packaging/source matrix remains an F2 blocker |
| F2 Projects/Stages/Progress SQLite-authoritative cutover | Complete | Very High / Luna High; regression and baseline classification in `F2_PROJECTS_SQLITE_CUTOVER.md` |
| F3 Game SQLite/event cutover | Complete (development authority) | Very High / Luna High; seamless production upgrade remains an F7 gate |
| F4 Mind Elixir/XMind | Not started | High / Luna Medium–High |
| F5 Documents/Word/Scrivener/background sync | Not started | High / Luna Medium–High |
| F6 Python-free Tauri packaging/runtime | Not started | High / Luna Medium–High |
| F7 migration, backup/restore and release qualification | Not started | Very High / Luna High; Sol for cross-platform release/integrity issues |

P1–P3 are complete foundations and are absorbed into F1/F2. P4 is absorbed
into F2 with a durable Game event contract. P5 is split into F4 and F5. P6/P7
are combined into F3. P8 is F6. P9 is split between F1 and F7.

## F1 boundary

F1 does not switch ownership, stop PKL writes, delete Python/sidecar/PKL, or
begin Projects/Game/Integration runtime cutover. The next milestone is F2 and
requires a separate explicit task.

## F2 boundary

F2 switches the local Tauri desktop Projects owner to SQLite only after
MigrationBundle verification. Normal desktop Projects reads/writes use typed
TS → Tauri → Rust → SQLite commands; PKL project access is guarded. Web remains
the independent FastAPI/Python adapter, Game is SQLite-owned, and document,
filesystem and Game-rule migrations remain future work. The durable outbox is
an explicit retry boundary, not distributed Game/Projects transactionality.

## F3 boundary

Game ownership is SQLite-authoritative. A failed verifier leaves the owner as
pickle; a second startup does not reimport PKL; and Game state plus event
processed marker commit together. The current sidecar still exposes the
existing Python service API for the Vue Game page, but that façade uses the
SQLite Game repository and cannot write Game PKL. Direct typed Tauri Game
command coverage belongs to F6's final sidecar removal.

## Production Bridge Release Strategy

Production Python continues receiving maintenance and bugfix releases during
F3–F7. Additional bridge releases may monotonically normalize Game state,
materialize stable IDs or export a canonical MigrationBundle. Development
authority readiness does not imply production upgrade readiness: F7 names the
minimum seamless-upgrade version. Older profiles use the migration-only helper
or the sandboxed Legacy Migration Service, in the order prepared SQLite,
bridge-updated Python, temporary helper, then isolated web conversion.
