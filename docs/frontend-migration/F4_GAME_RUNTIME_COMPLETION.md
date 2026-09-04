# NFProgress — F4 Game runtime completion

Status: complete for the normal development desktop path, 2026-09-04.
Starting HEAD: `aad08cdd34cd5bc9a10c28e862c2f8aa6860da7c`.

## Baseline and scope

Git history confirms that F2 `9af7b0597d3f3a54adce23766057546e1c122d68` is an
ancestor of the F4 starting HEAD. HEAD is F3 `aad08cdd34cd5bc9a10c28e862c2f8aa6860da7c`.
No cherry-pick or history rewrite was needed. F4 addresses the F3 blocker: the
normal desktop Game commands were still routed through the Python compatibility
service. Mind Elixir, XMind, Documents, Word, Scrivener, file watchers and
full sidecar removal remain out of scope.

## Runtime path audit

| User action | Vue caller / TS adapter | Tauri command | Rust service / persistence | State / side effect | Python? |
| --- | --- | --- | --- | --- | --- |
| Read Game, catalog, notifications | `gameApi.state/catalog/notifications` | `game_state`, `game_catalog`, `game_notifications` | service projection → SQLite | no mutation | No |
| Mark notifications | notification store | `mark_game_notification_read`, `mark_all_game_notifications_read` | atomic Game transaction | unread → read | No |
| Sessions | `GamePage`, `WritingSessionPanel` | `game_start/finish/cancel_writing_session` | wall-clock state/history | XP, coins, streak, inspiration | No |
| Challenges and creative rhythm | Game growth panels | `game_select_daily_challenge`, `game_start_weekly_challenge`, `game_resolve_creative_event` | counters/reward transition | challenge/event state and rewards | No |
| Inspiration/specialization/skills | growth panels | `game_activate_inspiration_ability`, `game_select_specialization`, `game_activate_specialization_ability`, `game_increase_skill` | validated transition | costs, pending effects, mastery/points | No |
| Quests and streak freeze | growth/overview panels | `game_start_quest`, `game_abandon_quest`, `game_apply_streak_freeze` | Gamer aggregate | status or freeze inventory | No |
| Shop/inventory/lottery | inventory/shop panels | `game_buy_item`, `game_sell_item`, `game_use_item`, `game_run_lottery` | catalog, RNG, inventory/coins | item effects, lottery history | No |
| Custom awards | awards panel | `game_create/update/delete/buy/sell/use_custom_award` | tagged objects/inventory | coins and custom count | No |
| Bank | bank panel | `game_preview/open/process/pay/repay/top_up/withdraw_*` | tagged bank aggregate/transaction | balance and product state | No |
| F2 domain events | Game startup/read/mutation | native service processes pending events | Rust consumer → SQLite | rewards and processed marker | No |

The Web adapter retains the existing `/api/game` Python implementation. It is
selected only when the runtime platform is not Tauri. The desktop Game path has
zero localhost Game HTTP calls, zero Python Game calls and zero pickle access.

## Rust application layer

Every stateful command follows:

```text
typed Tauri DTO (deny_unknown_fields)
  → GameApplicationService
  → validation and pure transition/RNG/clock ports
  → one SQLite transaction
  → GameCommandResponse with projected state
```

The error model distinguishes insufficient funds, invalid quantity, duplicate
or already claimed state, missing prerequisite, not found, cooldown, invalid
state, validation and database failures. Counts, money, dates and session
parameters are bounded; non-finite values and negative quantities are rejected.
Unknown Gamer extension fields and tagged legacy objects are not reconstructed
or discarded by unrelated mutations.

Ported rules include economy and 75% selling, level thresholds and multi-level
XP transitions, health/inspiration caps, skill points, consumable and custom
inventory, time-limited buffs, session grades/streak shields/quality medals,
daily and weekly challenge selection/progress, creative event resolution,
specialization selection/mastery-effect storage/cooldowns, bank balance guards,
and reward application from F2 progress/completion events. Manuscript/cabinet
data remains preserved in the Game aggregate; document-derived updates remain
an explicit future integration boundary.

Lottery uses an injectable `GameRng`: production uses the OS provider and tests
use a fixed provider. It draws two unique 5-of-30 sets, applies the legacy
2/3/4/5-match multipliers, consumes one ticket, credits the prize in the same
transaction and stores a bounded draw history.

## Event, persistence and recovery guarantees

Rust processes pending Game events before reads and writes. The event ID,
processed/failed marker and Game state transition share one SQLite transaction;
duplicate claims and duplicate clicks therefore cannot double-spend or
double-reward. Retry/poison handling from F3 is retained. A committed SQLite
backup can be reopened with Game state and pending events intact. Rust never
decodes pickle; the migration-only Python helper and future isolated Legacy
Migration Service remain outside normal runtime.

The weekly date boundary now stores the Monday of the effective UTC week in
native challenge state. The pre-existing Python fixture failure
`test_week_symbol_quest_counts_last_seven_days` is not silently reclassified:
it comes from the legacy test creating midnight notes while the Python oracle
normalizes writing-day timestamps. No user-facing writing-day rule was changed
without a parity decision; this remains a tracked oracle/test-fixture blocker.

## Verification

Added checks cover the native adapter/no-HTTP path, strict command boundary,
catalog parity, deterministic lottery, unknown-field preservation, event
idempotency and Rust compilation/unit tests. Python Web service and API
contracts remain unchanged. The complete baseline still has the three known
failures: legacy accessibility tab order, the developer OpenAPI response-model
expectation, and the writing-day week-symbol fixture boundary.

Production Python bridge updates remain monotonic and independent of F4
development readiness. The next milestone is F5 Mind Elixir/XMind only; no
integration work is started by this commit.
