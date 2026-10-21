# C21.2.09 — Dormant manual v10 mixed-source recovery routing

Baseline `71effc2cd4cdadc336a14b63d0079da1d7db1b98`, branch6.0. Q independently accepted
Cloud39651959872 SUCCESS, all6 required jobs. This bounded slice does not close .08.
Local validation/status/totals are recorded in the .09 checkpoint; remote CI pending.

## Later C21.2.11 contract-boundary audit

C21.2.09 is independently accepted (Cloud39664022870 SUCCESS, all6 jobs). Its
runtime remains unchanged. The attempted post-F Metadata slice stopped BEFORE
production edits: a genuine Metadata tombstone invalidates retained Content
authentication because accepted F/candidate dependency checks require a current
nondeleted Metadata tip. A genuine compressed update is a positive control;
Legacy-only deletion remains readable, but the required mixed cohorts do not.
See [the exact C21.2.11 blocker](C21_POST_F_STRUCTURAL_ROUTING_CONTRACT.md#c21211--implementation-stop-historical-metadata-tombstone-semantics).
Metadata/Stage/StageOrder remain explicit barriers. No fallback or partial
create/update route was activated. Proposed next numeric .12 is a DESIGN-ONLY
historical Metadata tombstone/dependency contract audit, not synchronization.

## Numbering and unchanged lifecycle requirements

The historical Content Outbound Design §17 uses Planning identifiers only, including
.09 upload/acceptance, while its technical lifecycle is authoritative. The owner
explicitly resolved this conflict in this chat: the NEW task replaces the planned
.09 assignment with mixed-source K routing. This record has precedence for the
current .09 label. The earlier table, .08 records, accepted scope and requirements
remain verbatim history. No claim of sealer/upload/self-echo completion, roadmap
points or public activation follows. Proposed next .10 is a separately reviewed
post-F structural routing audit; further outbound numbering awaits owner planning.

## Entry and evidence ownership

The existing `BrowserV10Recovery.bind` and historical run body remain byte-identical.
`bindMixedSources` delegates to the module-internal `bindMixedV10Recovery` factory,
which returns a frozen run-only object. J, H, O, Q, busy state, leases and tokens are
lexically private. No persistent selector, public certificate/source token, network
adapter, timer, UI composition or production persistence surface is added.

The new mode requires one accepted F in complete account history; preparing/applying
F remains the existing accepted owner's responsibility. J validates actual IDB keys,
indices, retained evidence and immutable replay. Every scan begins at0, loads all
bounded stores and compares earliest pending identity. A missing sequence prevents
mixed admission; a gap inside an existing proven prefix is corruption. No offsets,
filtered v9 history, fake Head1 or hidden later candidate inventory is accepted.

K authenticates original F/closure/history and uses explicit Q full source/family
verification. Q keeps its accepted evidence-selected historical versus mixed source
contract, with no error fallback. Pure F/H-only histories retain historical source
ordering even when N/O cannot admit that history to the stricter mixed cohort.
An independent mutation must still pass O's COMPLETE mixed pre-state and predicted
post-state contract; historical admission is not independent-writer authority. A valid
historical F/H cross-role commit order can still fail O's strict revision_order:
this is an unaccepted mixed cohort, not permission to rewrite that valid history.
The original error remains explicit and no apply/prefix token is borrowed.

Only authenticated F project/output identity selects H versus O, never an inferred
head version or an unsuccessful owner attempt. Each owner independently opens the
actual event, validates bootstrap/membership/dependencies/causal ancestry, prepares
its private source grant and validates the predicted complete post-state. K pins
the complete routing inventory before the existing owner commit; native CAS and
lifecycle enforce atomicity. After every commit the loop reloads the complete
inventory, including when the next decision is budget exhaustion or idle state.

## Supported and blocked route matrix

| Pending route | .09 owner/result | Prerequisite for a future route |
|---|---|---|
| Peer independent Note in the F project | O, Legacy2/Content3 ID0/ID1 create/update/delete; original O import_remote/captured, accepted project/Stage HTML/plain only | Current O pre/post witness, actual Head1 or genuine create, no open conflict/local/own source |
| F original or retained Note | H only; accepted continuation, role-specific Head2/reachability, immutable causal/source checks | No resurrection, new generation or O fallback |
| Authentic H-owned fork | H conflict preservation, NULL projection/revision; Q stops at incoming sequence; later queue untouched | A separately accepted resolution/closure mechanism before crossing the fork |
| Post-F Metadata | Explicit unsupported_route/post_F_structural_route | Full-v10 owner adapter, complete pre/post inventory pinning, exact-reference/owner CAS; never materialize canonical P0 without a new source contract |
| Post-F Stage/StageOrder | Same explicit structural barrier | Full-v10 dispatch, real Metadata/Stage dependencies/tips and StageOrder exact coverage; no filtered old account view |
| Unrelated project Note | Explicit unrelated_project_writer | Separate authenticated project/source transition model and actual ordinary owner; no borrowing the F project's root/revision |
| New Resolution | unsupported_generation; full witness can block before applying earlier queued work | Accepted additional-generation F/H/G evidence/source/closure contracts |
| Tombstone resurrection | Existing owner rejection becomes unsupported_route | Separate reviewed resurrection semantics and proof/source transition contract |
| Own event/self-echo | Explicit own/source-cohort barrier | Actual producer C3/R2/P2 or own Resolution chain and full consumer acceptance, no device-id inference |
| Local source writer/intent | Existing mixed-source owner barrier | Independently accepted v10-aware local ownership model and durable producer evidence |
| Missing dependency/baseline | dependency_unavailable/manual retry, or explicit unsupported source cohort | Genuine accepted retained evidence/owner result; current exact J replay is not a cold-history reconstruction/repair mechanism |
| Unsupported pending family or generation later in the full account | Earliest pending apply blocked by explicit full-witness cohort reason; no G token | Do not hide the later record or downgrade the inventory to process around it |
| Corrupt/unknown evidence, revision drift, stale snapshot or revoked lifecycle | Reject; retain bytes and last completed owner transaction | Fresh valid state and separately accepted repair/recovery, never a flag or manufactured proof |

## Prefix, restart and diagnostics

Every event commits in its actual O/H atomic transaction. K is not one transaction
for the entire pass: a later barrier/error preserves earlier genuine commits.
Q certificates/calculations never authorize O/H writes, ACK or readiness. Local
prefix is prepared fresh and committed only via Q's native full-inventory CAS;
an H conflict incoming sequence is never qualified. If this cursor transaction
aborts after real O/H success, the immutable applied evidence remains and a fresh
manual pass can advance prefix with zero duplicate apply. Auth/key/profile/device
invalidation, source races and stale dependencies never become success or fallback.

J replay remains the exact current committed server interval before/after local
apply; no arbitrary older-page replay, encoding, re-encryption, pull or upload.
Fresh runtime/process restarts reacquire genuine registration/key bindings and
reconstruct from durable records; private plans are not persisted or resurrected.
Concurrent passes on one binding are excluded; independent bindings still require
exact owner/source CAS. Native competing tabs retain the exclusive writer Web Lock.

Result flags remain ready=false, declarationAllowed=false, ackAuthorized=false.
Readiness is NULL, not a synthesized I diagnostic: the existing I preflight uses
default historical G and remains negative-only/unchanged. .09 does not silently
replace it with Q or clear any audited reader blockers. No returned result is a
capability or commit token; public diagnostics cannot be consumed by owner/ACK APIs.

## Validation and CI workload

All positive histories use actual accepted F/H/O commits. Tests cover protocols2/3,
ID0/ID1, all4 F strategies, independent/project/Stage/plain Notes, original/retained
branches, tombstones, immutable proof/wire, budget/manual resume, fork barriers,
corruption/gaps, actual source races, per-event rollback, prefix recovery after a
real apply, auth/key/profile/device revocation and historical cross-role ordering.
Fresh genuine fixtures, individual test bodies and hooks retain5000ms limits.
Long multi-pass acceptance is split into meaningful fixture/event/cursor checks;
no retries, skips, fabricated applied rows, timeout growth or security reduction.

Native .09 extends the same8 O/P/Q disk profiles: bounded O→H resume over a full
restart, actual Legacy/Content updates/deletes, retained tombstone, native event
abort, applied-event/prefix-abort/restart recovery, revocation/rebind, competing tabs,
exact replay and H-preserved fork barriers before/after reopen. All old negative
assertions remain; default K is still tested to reject mixed histories.

Completed accepted Q Frontend measured30m43s of40, complete-project9m18s of40.
New isolated .09 Vitest tests run ONLY in the already mandatory complete-project
shard after its existing npm ci and Node20.19.0 setup, maxWorkers1, no new dependency
or job. Frontend retains all prior suites and adds .09 to its single awaited native
O/P/Q superset. No mandatory step is dropped, renamed, made optional or hidden behind
continue-on-error; six required job names and40-minute budgets are unchanged.
Final local validation: .09 K71, O46, P47, Q71 and original F/H/G/K/N/L/J/I412
regressions PASS (647 tests /12 files, failed/skipped0). Native O/P/Q/.09 PASS:
8 profiles,80 full restarts,58 actual new K owner outcomes plus8 H-preserved K forks,
8 event rollbacks,8 applied-event/prefix-abort recoveries,8 lifecycle revocations,
8 competing tabs,16 exact replays; page errors/unauthorized HTTP0. Registration120
PUTs are disposable fixture setup/rebind only. Unit .09 took66.08s, combined native
199.46s locally. Typecheck/build, strict workflow/coverage/history/path/diff and
protected hashes PASS. No unrelated heavy backend/native suite repeated. See the
.09 checkpoint for full evidence, including original O/P/Q counters. LOCAL COMPLETE
/ REMOTE CI PENDING; resulting Actions are not polled or awaited.

## Remaining .08 and production gates

.08 is NOT CLOSED: actual Content sealing/gate, raw upload/receipt, own Content
P2/self-echo and own Resolution authorship are still absent/unaccepted. Full Note
reader readiness also requires complete structural/unrelated-project routing,
missing/cold dependency recovery beyond J's exact replay, all supported Resolution
generations and resurrection, local/own source history, and genuine multi-device
restart/revocation/recovery acceptance. Existing I blocker list is not rewritten.
Before a Note capability declaration the exact current server mode/device/account
reader gate must be verified and ALL claimed reader prerequisites independently
accepted. No stale Note gate/compression capability or registration implies this.

Production composition, scheduling, Content writer/sealing/publication/upload and
Resolution network ACK require separate explicit authorization after those gates.
All formats, crypto/AAD/wire, IDB10 migration/12 stores and old-client barriers remain
frozen. Web89.36%, C21/C21.2 IN PROGRESS, C21.1.06 NOT LOCAL COMPLETE; VPS hardening,
security audit, closed public registration and all owner/public-release gates remain.

### Простыми словами

Ручной обработчик выбирает правильный проверенный модуль для очередного события и
останавливается на первой нерешённой границе. Он может восстановить локальную
отметку проверки после сбоя без повторного изменения заметки. Это отдельный dormant
путь для принятой истории, а не автоматическая полная Web-синхронизация или разрешение
отправлять данные. Следующий предлагаемый числовой этап .10 — аудит структурных
событий после Resolution; остальные reader/producer/security gates сохраняются.
