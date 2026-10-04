# C18.5.06 mutation inventory (before implementation)

Baseline: `302a5fe1f7cda77bcc248994bf0b40cc1dcc6ad0`, branch `6.0`.
This is an implementation audit, not a claim of activated Game synchronization.

## Current ownership and mutation boundaries

Native Vue commands use `frontend/src/api/game.ts` → `GameApplication` in
`frontend/src-tauri/src/game.rs`. Ordinary native mutations share `mutate`, which
consumes pending domain events before updating SQLite `game_state` in a transaction.
Native `process_pending_events` updates the projection and processing marker in
one transaction. Domain rows include stable event/project/stage/progress IDs, but
the current native consumer SELECT omits stage/progress/day; ledger capture must
read those columns rather than infer ownership from names.

Python compatibility uses `nfprogress/core/services/game.py`, its `_command`
transaction and `SQLiteGameRepository`. `_prepare_gamer`, `get_state`, bank
processing and legacy streak refresh can mutate state during reads/preparation.
Guarding only frontend button commands would leave competing writers. Both the
native and Python persistence boundaries require capture or an explicit blocker
after activation; raw SQLite compatibility writes cannot become cloud authority.

`nfprogress/core/game_state.py` preserves unknown fields and tagged legacy objects.
Its encoder includes Python callable descriptors in quest/template objects; these
are recovery evidence only and must never be portable executable authority.
`engine.Project`/`Stage` and the Game overlay both contain streak state.
The cloud authority must be one ledger, with those fields as compatibility views.

## Classification of every current API family

The A/B entries below identify the required ownership, not implementation status.
An unadmitted A/B state is F until its typed codec, writer and reader are complete.

| Current operation/state family | Class | Mutation/dependency and admission rule |
| --- | --- | --- |
| ProgressAdded local domain consumer | A → B | Exact authenticated Progress event, entry, owner, unit, writing day and delta; project transition plus uniquely sourced account reward. Freeze native/Python rule inputs/results separately. |
| ProgressDeleted | A evidence; C local journal | No automatic reward clawback. Remote Progress import creates no local domain reward. |
| ProjectCompleted / StageCompleted | A → B | Stable owner/completion identity, metadata/Stage authority, total input, rule version, existing claimed markers; rename cannot reopen a reward. |
| ProjectStatusChanged / ProjectDeleted | A lifecycle authority elsewhere; C Game journal | Existing metadata authority remains canonical; local consumer journal is not a portable snapshot. |
| Project/Stage streak transitions | A | Authenticated owner and contributing Progress/day facts; finite historical dates and freeze facts. Counters are D. |
| Global streak transitions/rewards | B | Account scope, contributing authenticated project facts or audited legacy base; markers/health effects require typed admission. |
| applyStreakFreeze(global) | B, otherwise F | Noncommutative item consumption plus global transition; exact prior head and eligible day. |
| applyStreakFreeze(project) | A + B, otherwise F | Account item consumption coupled to project/Stage transition. Never publish only one side. Native currently consumes inventory without modifying streak history; Python calls engine freeze/group functions. This discrepancy cannot be hidden by a snapshot codec. |
| startWritingSession / cancelWritingSession | C | Wall-clock timer, intention and transient execution stay local. |
| finishWritingSession | B result, otherwise F | Coins/XP/inspiration, session series/history, shield/grade-boost consumption, specialization effects and bonuses must be accounted for. Transient session is not uploaded. |
| selectDailyChallenge | B, otherwise F | Selection, options/date, inspiration spend; exact prior account head. |
| startWeeklyChallenge | B, otherwise F | Challenge identity/period and state; exact prior head. |
| automatic daily/weekly advancement | B, otherwise F | Local Progress consumer also changes challenge progress, completion and rewards. A reward-only capture must not omit these effects. |
| activateInspirationAbility | B, otherwise F | Inspiration spend and pending bonus, consume exactly at matching reward. |
| resolveCreativeEvent | B, otherwise F | Selected choice and frozen RNG outcome, bonuses/history/productive counter. Never reroll on replay. |
| selectSpecialization / activateSpecializationAbility | B, otherwise F | Selection/change day, mastery, cooldown and pending effect; noncommutative. |
| increaseSkill | B, otherwise F | Point spend, skill increment, coefficient/max-health consequences; causal account base. |
| startQuest / abandonQuest / automatic quest settlement | B, otherwise F | Stable quest ID, status, reward claim and frozen rule; callable/template display objects are excluded. |
| buyItem / sellItem | B, otherwise F | Exact category/key/count, frozen unit price/inflation, balance and inventory base; no balance LWW. |
| useItem | B, otherwise F | Every current effect needs admission: health, inspiration, timed buffs, pending session bonuses, challenges, skills, freezes, RNG lottery. Merely decrementing count is insufficient. |
| native lottery dialog/result | B, otherwise F | Ticket consumption and frozen selected outcome, reward/buff effects; replay never invokes RNG. |
| create/update/deleteCustomAward | B, otherwise F | Definition and stable ID, bounded user text and inflation policy; retain references of deleted definitions. Current native count-derived IDs are not a cross-device stable creation contract. |
| buy/sell/useCustomAward | B, otherwise F | Definition dependency, inventory quantity, frozen price and balance; causal account head. |
| openBankCredit / openBankDeposit | B, otherwise F | Balance, product, terms, opening date and history; no raw BankAccount dump. |
| processBankEvents | B, otherwise F | Interest, overdue/payment/penalty and notification-related settlement; command and preparation may mutate. |
| makeBankLoanPayment / partiallyRepayBankCredit / repayBankCredit | B, otherwise F | Exact prior product and account base, balance spend, history and credit score. |
| topUpBankDeposit / withdrawBankDeposit / withdrawBankDepositInterest | B, otherwise F | Product base, accrued interest, maturity/early policy, balance and history. |
| previewBankProduct / catalog / ordinary DTO views | D read | Preview is not a portable action; audit preparation for hidden mutations. |
| developerProfile / developerInventory / developerRestoreStreak / developerCreateStreakSeries | C + explicit F restriction | Never normal portable authority; durable dev-state restriction must survive toggling developer mode off. |
| test-date controls / profile transfer execution/results | C + F if portable base contaminated | No debug/test provenance in genesis; explicit restriction needed for affected ordinary state. |
| notifications / markNotificationRead / markAllNotificationsRead | C | No cloud read/unread state, text or notification IDs. |
| domain_events attempts/status/errors, diagnostics | C | Processing/retry evidence remains local; no raw row upload. |
| gamer balance/XP/level/skills/inventory, project_game_state, global counters | D after admission | Rebuilt from typed genesis plus admitted actions; never mutable independent cloud winners. |
| buffs/debuffs, bank, custom awards, quests, challenges, specialization, cabinet/manuscript, completion/reward markers | B ownership; F until admitted | Nonempty unsupported fields retained losslessly; explicit safe blocker. Known default template objects need exact normalization, not an unchecked whitelist. |
| unknown root/gamer/project/global extensions | F | Immutable local recovery evidence, bounded durable blocker, no false complete claim. |

## Rule differences requiring explicit versioning

Native ProgressAdded uses base coins=10, XP=500, coefficient, inspiration and
writing bonus. `add_experience` advances levels/skill points. It also advances
active session/challenges and productive-event counters. Python's deterministic
consumer currently adds raw XP without that native level advancement. Completion
uses native float round-away-from-zero versus Python round-to-even at half ties.
Existing outcomes must not be silently normalized or recalculated on import.
Native freeze lacks the engine eligibility/group/streak transition implemented
by Python. Any admitted freeze writer must prove the complete transition.

## Codec allocation audit

Current WORTA-C1: metadata=1, Stage/order=2/3, catalog=4/5/6/7,
Note=8, Map=9, Document=10, Progress=11. TS framing and Rust counterparts agree.
No existing framing assignment uses 12 or 13. Expected project Game=12 and
account Game=13 are available; no existing codec is renumbered.
`accountCatalogCodec.ts` currently uses `4 + ACCOUNT_ENTITY_TYPES.indexOf`.
Before adding account Game, freeze a separate four-entry catalog list/mapping;
Game must have explicit 13 rather than the fifth catalog ordinal 8.

## Required activation boundary

One atomic local mutation must contain action(s), stable reward identity,
projection, outbox and local consumer marker. Remote readers authenticate exact
source dependencies and preserve conflicts before shared ACK. Migration is an
explicit UI action only. Existing local-only projects remain unbound. Unsupported
local data and commands keep recovery evidence and durable typed blockers.
Game is not locally complete until both production writers/readers, capability
gate, shared ACK proof, UI and real PostgreSQL/two-file-SQLite acceptance pass.

## Integration finding: complete native reward effects

The unpublished codec13 legacy base initially omitted health/max-health,
coefficient/pending-writing inputs and the productive-action/creative-event marker.
Native `add_experience` and `ProgressAdded` prove these omissions would produce
an incomplete second-device projection even with the correct coin/XP reward.
The draft base now admits these bounded typed fields; IDs12/13, frame/version,
compression and both crypto domains remain unchanged. Active challenges,
bank/quest/custom-award effects still require their existing explicit F classification.
The creative marker distinguishes an absent legacy field from present null, because
native historical execution distinguishes those states. No historical behavior is corrected implicitly.

The production skill keys are `productivity`, `profitability`, `endurance` in both
`Gamer.get_default_skills` and native `skills_projection`. The draft's invented
`discipline`/`creativity` fields were corrected before activation, preserving the
actual save identities. A native/Python event-consumer savepoint now rolls back
Game state and future ledger intents if the processed marker fails; retry evidence
is written after that rollback. This closes an existing partial-transaction hazard.

Completion integration also exposed a missing authenticated total dependency in the
unpublished draft: a declared `total_symbols` alone cannot prove historical reward
input after later Progress correction/deletion. Codec12 completion now references
an exact Progress event/owner; apply must reconstruct that authenticated historical
chain and verify the frozen total. The stable completion identity remains the
Project/Stage owner, so later Progress edits or renames cannot reopen the claim.
Health-recovery coefficient is also captured with the other real `cf` inputs,
preserving the existing endurance-skill projection. Frozen local default templates
are compared exactly; modified/deferred templates remain lossless F evidence.

The ordinary native domain consumer now admits writing only when its exact local
Progress append is retained, both Game owners are active, and the full post-rule
portable account projection equals deterministic ledger interpretation. The stable
source/reward relation prevents reprocessing from applying the historical reward
again. Deferred side effects retain the existing local product behavior and block
complete Game authority with recovery evidence. Completion claims keep the actual
legacy compatibility keys (`project:<id>` / `stage:<project>:<stage>`); the canonical
completion/action identity is independently derived from the unambiguous owner tuple.
No completion history is regenerated because a project or Stage is renamed.
Legacy numeric values that cannot round-trip through the frozen six-decimal
contract remain F; migration must not silently round a reward coefficient or
balance. A second local processing record for the same scoped Progress entry
reuses its existing canonical writing/reward relation without applying legacy
reward logic again. Processing records themselves remain local evidence.

## Final production admission boundary (C18.5.06)

Admitted ordinary writers are native and Python local ProgressAdded and
ProjectCompleted/StageCompleted, plus native catalog buyItem/sellItem. The latter
freeze actual category/key/count/price and verify the complete portable result in
one transaction. A historical base preserves existing balances, inventory, series,
claimed completions and prior aggregate rewards without executing them again.
Explicit adoption, full-tip resolution and separately confirmed compensation are
closed control operations, not generic setters. Progress source deletion retains
its authenticated history and reward; it does not imply automatic clawback.

Other A/B families in the ownership matrix remain F until their exact transitions
have a production writer AND authenticated interpreter. This includes live
project/global streak changes/rewards and freezes (the two existing runtimes have
different freeze semantics), sessions with portable effects, challenge/quest/skill/
specialization transitions, custom awards, item use/lottery/buffs and bank effects.
Their existing local behavior is preserved with immutable OLD/NEW recovery evidence
and a complete-sync blocker; no arbitrary account snapshot escapes this boundary.
The codec reserves closed variants for these families but a structurally valid
reserved variant is not sufficient admission: the current interpreter rejects it
and retains ciphertext without apply/ACK evidence. Freeze concurrency is therefore
not claimed as an admitted writer acceptance.

Every admitted account action is causal. Distinct independently sourced rewards
retain separate unique facts; a divergent earn/spend or compensation/spend requires
full-tip resolution just like spend/spend. There is no implicit commutative merge,
clock/server-order winner, final-balance overwrite or duplicate reward identity.
