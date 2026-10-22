# C21.2.16 — post-F Metadata private handoff contract audit

**DESIGN AUDIT COMPLETE / CONTRACT STOP FOR DIRECT ROUTING. No adapter implemented.**
Audited branch `6.0`, baseline `472d950b95c1fad829c5a1c1f62a0ff208614be3`.
C21.2.15 is **REMOTELY ACCEPTED**, diagnostic scope only: [Cloud39768042164](https://github.com/nevskyforever/nfprogress/actions/runs/39768042164),
completed SUCCESS at that exact SHA, all six mandatory jobs SUCCESS, independently
read once. Earlier pending checkpoint entries remain historical records.

This document refines the [.10 structural contract](C21_POST_F_STRUCTURAL_ROUTING_CONTRACT.md),
[.12–15 historical contract](C21_HISTORICAL_METADATA_DEPENDENCY_CONTRACT.md),
[mixed source contract](C21_MIXED_PROJECT_SOURCE_AUTHORITY_CONTRACT.md) and
[accepted mixed K](C21_V10_MIXED_RECOVERY_ROUTING.md). It does not supersede their
accepted behavior or the C21.2.11 IMPLEMENTATION STOP.

## 1. Findings and implementation boundary

The IDB10 infrastructure **can** schedule one strict native transaction over the
ten recovery stores and compare their complete bound-account snapshot before
writes. Existing Metadata owner APIs **cannot yet compose** their opaque plan
into that transaction. An outside full-inventory comparison followed by the
existing owner commit leaves a race and is forbidden. See `BrowserSyncTransaction`
in [syncDurability.ts][sync], `runBrowserTransaction` / `BrowserPersistence.syncTransaction`
in [persistence.ts][db], and `BrowserImportedMetadataApply.commitVerifiedImportedMetadataApply`
in [owner]. F's `BrowserResolutionApplyRuntime.commit` in [resolutionPlanner.ts][inventory]
and G's `BrowserResolutionPrefixRuntime.commit` in [prefix] already demonstrate
synchronous complete-inventory CAS followed by writes in the same transaction.
These precedents establish storage feasibility, not a working Metadata handoff.

There is a second, independent **CONTRACT STOP**: accepted .13–15 cannot directly
authenticate a transition containing pending Metadata. In [historicalMetadataDependency.ts][dependency],
private `verify` requires every retained Metadata row to be in its actual owner's
applied history, with no extra pending Metadata row, and requires the root
project's terminal delete. `.14 authenticateTerminalMetadataSourceState` and
`.15 inspectTerminalMetadataHistoricalPrefix` in [mixedSourceValidation.ts][mixed]
do not add a pending Metadata admission mode. Active pre-state, a pending delete,
and a terminal-delete post-state are different cohorts. Public reader success,
exception handling, or a synthetic already-applied post-state is not permission
to bridge them. A later pending Metadata row can block this whole-account check
before K reaches the earliest event.

**Decision:** no schema migration, new store/index, persisted proof format, wire,
crypto or backend change is required for the specified coverless owner delta.
Existing proof/head/inbox formats represent it. What remains unimplemented and
unaccepted is private in-memory composition and complete pre/post authentication
with explicitly classified pending Metadata. Do not claim universal history
support or functional acceptance from this audit. If that verifier cannot prove
a genuine cohort using existing evidence, retain STOP; do not add evidence fields
or reinterpret historical digests to force support.

## 2. Actual call-site and authority map

Paths below refer to the audited baseline; names are actual functions/types.
“Reusable” means semantics/code, not permission to consume a diagnostic as a token.

| Boundary | Current owner and evidence | Required fresh check / private authority | Current status and failure |
|---|---|---|---|
| Durable inventory → identity | [inventory] `resolutionInventoryStores`, `scheduleResolutionInventory`; [db] `syncTransaction` | All ten stores, bounded rows/bytes, durable identity/binding, session/account/device/key/profile/epoch | Reusable; malformed/over-limit/missing cursor aborts, no filtered snapshot |
| Inventory → original F/H | [resolutionAuthentication.ts][f-auth] `authenticateResolutionHistory`; [resolutionHistorical.ts][h-auth] `authenticateContinuationHistory` | Original AEAD, parents/publications, closure, Head2 roles and causal DAG; live dependencies in current path | Implemented for accepted live cohort; terminal Metadata delete breaks Content live prerequisites |
| Terminal delete → retained Content/F | [dependency] `authenticateTerminalMetadataInventory`; [f-auth] `authenticateTerminalMetadataResolutions`; [h-auth] `authenticateTerminalMetadataContinuations` | Fresh internal sequence-bounded dependency reproduction plus unchanged F/H proof authentication | Isolated reusable read-only semantics; pending Metadata/Stage/own/additional generations fail closed |
| Historical history → exact current source | [mixed] private `authenticateTerminalMetadataSourceState`, `validateAuthenticatedInventory`, `verifyContinuationSources` in [h-auth] | Every actual revision, baseline/member projection and current encrypted source; evidence-selected mixed vs historical ordering | Implemented privately for .14/.15, no source grant; valid-AEAD unexplained drift rejects |
| Source/history → earliest received event | [v10MixedRecovery.ts][k] `bindMixedV10Recovery`; [v10Transport.ts][transport] `listReceived` | Dense sequence1..pull, already-proven interval, earlier unqualified outcomes, actual earliest row | K currently authenticates H and Q before routing, then returns `post_F_structural_route`; no Metadata handle |
| Earliest Metadata → owner prepare | [owner] `prepareVerified`, `metadataProofFor`, private `transition`, private `plans` WeakMap | Actual imported/captured/active lineage, all retained AEAD/references, clean parent/tip/revision/generation, coverless peer event | Family prepare reusable; no complete-account or earliest-event capability; genesis-resolution/reactivation not admitted by this audit |
| Owner plan → atomic write | [owner] `commitVerifiedImportedMetadataApply` | Same-tx full ten-store pre-state CAS, owner checks, predicted delta and complete lifecycle guard | Missing private composition: current commit owns a separate six-store transaction; cannot unwrap/export/copy plan |
| Committed result → fresh history | [dependency], [mixed], [historicalContentAuthentication.ts][reader14], [historicalPrefixQualification.ts][reader15] | Reload actual durable outcome, independent source and per-family evidence; no cached diagnostic | Read-only terminal cohort implemented; generalized pending/active orchestration unavailable |
| Fresh history → local cursor | [prefix] `prepare` / `calculate` / `prepareCommit` / `commit` | Genuine private G certificate and separate full-inventory CAS; each sequence's own proof | Current G/Q use live admission and remain negative after Content/Metadata delete; .15 has no commit surface |
| K / cursor → network ACK or declaration | [deviceRegistration.ts][device] `currentBrowserDevice`; [ackPrerequisites.ts][ack] and [provenPrefix.ts][reader-ack] | Separate accepted transport/mode/capability/proof gates, never reader/owner output | No new authority in .16; registration token is identity/lifecycle only; no HTTP required by this handoff |

Default `BrowserV10Recovery.bind` in [v10Recovery.ts][default-k] has Metadata calls
only on its older permitted route; `bindMixedSources` delegates to [k]. Copying
that older prepare→outside-load→commit pattern is not a post-F solution. The
13 existing [postFMetadataBoundary.spec.ts][stop-tests] cases, including the
wholly Legacy control, remain unchanged. The 12 genuine Content deletion cases
prove the real owner commits a tombstone while Q/K then reject authentication.
The control does not authorize structural mixed-K dispatch.

## 3. Historical versus live authorization

| Operation/evidence | Accepted guarantee | Cannot authorize |
|---|---|---|
| .13 `BrowserHistoricalMetadataDependency.inspect` | Dependency component and exact `M < E < D` for genuine retained outcomes; explicitly `fullHistoryAuthenticated=false` | Full source, first apply, owner commit, prefix or ACK |
| .14 `BrowserHistoricalContentAuthentication.inspect` | Fresh retained F/H/Content plus independently verified current source in its accepted terminal cohort | A new Content event, Metadata write, source handoff or writer token |
| .15 `BrowserHistoricalPrefixQualification.inspect` | Frozen candidate and first barrier; own-family evidence including old proven interval; no cursor writes | `VerifiedResolutionPrefix`, Metadata plan, Q commit, readiness or ACK |
| Live `prepareNotePrerequisite` in [noteTransportPrerequisite.ts][live] and F `dependencies` in [f-auth] | Actual current nondeleted Metadata and covered exact reference, plus Stage dependencies when applicable | New Content after current delete, or reconstruction of an exact old owner snapshot from a digest |
| Genuine owner `VerifiedImportedMetadataPlan` in [owner] | Owner-instance/scope-bound private retained AEAD/proof, expected head/binding | Complete v10 source, earliest-event order or full ten-store atomic handoff |
| Note source owners F/H/O | Own source/project/Note transitions, causal roles and exact CAS | Metadata delta does not inherit or mint their authority |
| Q/G certificate and commit plan in [prefix] | Family-qualified contiguous local prefix under its actual accepted admission | Owner apply, account-wide Note declaration, network ACK or readiness |

For each already applied Content event E, authenticate the actual nondelete
Metadata dependency M, original references/bootstrap/AEAD, actual owner history
and outcome proof, and the terminal delete D with `q(M) < q(E) < q(D)`. Check every
retained Content outcome, not just the selected target. F retains its original
proof/evidence, group closure and output identities; H roles and O source
transitions still need complete source validation. A preserved losing conflict
remains its real preserved outcome, never a manufactured applied projection.
These are [dependency] `verify` and [mixed] private source-state semantics.

Sequence-bounded admissibility does **not** prove local wall-clock apply time or
an exact old owner inventory. `dependency_digest` remains its original immutable
commitment, not a recipe for a guessed snapshot. New first apply continues to
use current live prerequisites even for `E < D`: a received row is not an old
applied outcome. Legacy cannot bypass deleted Metadata to make new source changes.
No live owner is routed through terminal historical exceptions.

## 4. Earliest-event decision matrix

These are future prerequisites, **not currently enabled routes**. Missing/invalid
later material can prevent complete validation even when the earliest row looks
valid. Always retain and authenticate it; never drop it to obtain a permit.

| Material | Decision / exact boundary |
|---|---|
| First Metadata create after F | Conditional only: genuine imported binding, no existing owner, create rev1/gen1/no parents, and F/history/source remain provable without invented earlier Metadata. A Content F already requiring that project's genesis cannot be satisfied by a late create. Same-project second create rejects; no fallback to another project. Legacy-only no-head cohort needs genuine acceptance before admission |
| Metadata update, active parent | Existing owner must reproduce full clean history and exact current tip; predicted source unchanged. Current .11 test proves genuine update can remain Q-readable; that alone does not cover pending full-v10 handoff |
| Terminal delete after F | Prove active pre-state and owner-prepared predicted terminal state with every retained Content interval `M<E<D`; exact peer clean chain only. Commit head/history+inbox, no canonical project tombstone |
| Applied Content before D | Historical validation/replay only; preserve original bytes, outcome and revision, no duplicate source write |
| Received Content before a still-received D | Consider Content first through its actual live owner; no skipping it to commit D. Missing prerequisites block the pass |
| Received Content before an already applied D | Keep received; even `E<D` cannot grant first apply under current delete. It remains a contiguous-prefix barrier |
| Received Content after D | Authenticate ciphertext where supported, keep received; no new apply, source mutation or historical promotion |
| Missing/late/duplicate/competing Metadata dependency, invalid AEAD/bootstrap/proof | STOP; no interval, repair, guessed parent, success fallback or cursor crossing |
| Extra later pending Metadata | Current .13–15 reject it. Future private verifier must classify its original wire and uncommitted status in the complete snapshot without adding it to owner history. If unsupported, STOP whole preparation; never pretend an already applied suffix |
| Interleaved genuine ordinary O/H history | Reproduce complete membership/revisions/projections and original/retained roles; Metadata never advances source_revision. Accepted F/H-only cross-role commit ordering remains evidence-selected, not forced into O ordering |
| Another project's Metadata | Existing historical checker opens each real owner's chain; no borrowed proof. Future routing initially restricted to the accepted F project; unrelated-project first apply is deferred, not inferred from read-only readability |
| Unrelated Note writer, own/local publication, unsupported generation/fork/family | Explicit barrier in the complete inventory, even after an earlier pending row; no foreign authority or filtering |
| Stage/StageOrder, Stage-scoped Content, covers | Block future initial adapter. .13 rejects Stage rows/owners and Stage dependencies. Existing Stage/StageOrder live contracts cannot supply the missing historical coverage |
| Already applied Metadata replay | Fresh complete history and matching own persisted proof; no transition or history append, and no source/cursor write. Must not prepare a stale pre-delete plan to roll a descendant back |

A saved proven cursor is not evidence. Validate1..pull and recheck its entire
proven interval using each event's own genuine outcome, as .15 does. If an earlier
non-received unqualified fork/outcome precedes the earliest received row, stop
there. No later owner apply or delete can fill that gap.

## 5. Ten-store atomicity and permitted write set

[resolutionPlanner.ts][inventory] names exactly:
`inbox`, `outbox`, `receipts`, `projectBindings`, `ownerHeads`,
`legacyNoteHistory`, `legacyNoteIntents`, `localProjects`, `localNotes`, `cursors`.
`MAX_PLANNER_ROWS=16384` per store and aggregate `MAX_PLANNER_INVENTORY_BYTES=32MiB`
remain enforced by `scheduleResolutionInventory`.

The range is **all records for the bound account**, including unrelated projects,
Notes, owners, upload material and cursors; it is not a selected-project subset
or a scan of every other user's account. `BrowserPersistence.syncTransaction`
adds `identities` and `accountBindings`, validates their canonical/local/device
mapping in the same native transaction, then calls the scheduler. Thus there
are ten recovery stores plus two identity stores in the native scope, with no
schema extension. No permission to change another account's records follows.
A requirement for cross-account database-wide CAS would need a separate contract;
this audit does not claim the account-range loader implements it.

`BrowserSyncTransaction` accepts a synchronous `Schedule<T>` callback.
`runBrowserTransaction` demands strict durability for writes, rejects a returned
Promise, aborts on request failure and resolves only on native `oncomplete`.
AEAD, hashing, dependency and predicted-history validation therefore happen
**before** the write transaction. Inside it, schedule cursor reads, compare exact
pre-state and already authenticated dependencies, then schedule the owner's
existing writes synchronously in IDB callbacks. No awaits, crypto, HTTP, nested
owner transaction or transaction keep-alive trick is permitted.

| Store | Permitted future delta |
|---|---|
| `ownerHeads` | Exactly the selected Metadata owner head, from owner-verified `transition`; append its own proof/history and new tip, preserving all prior entries |
| `inbox` | Exactly selected received row → existing record_version2 applied outcome with that owner's genuine proof; original wire/identity/sequence unchanged |
| Other eight recovery stores | Byte-identical, including all source/member/revision data, candidate/head history, intents, outbox/receipts, bindings and every cursor field |
| Other records in `ownerHeads` / `inbox` and identity stores | Byte-identical; no unrelated record deletion, revision, fixup or cursor advancement |

Exact full snapshot equality immediately before these writes makes the
outside-transaction authentication current. Owner lineage/head/retained-row/local
outbox/receipt/cursor checks must still run, or be factored into the same private
scheduler with demonstrably equivalent checks. Abort if the predicted allowed
delta differs from what the scheduler is about to write. Transaction completion
is the commit point; reporting `result('applied')` before `oncomplete` is not one.

## 6. Smallest future private API refactor

Current [owner] `plans` is module-private and bound to its owner instance;
`transition` is private. Its six-store commit rereads family records, handles
exact replay without rolling back descendants and subscribes to auth invalidation.
It does not accept an existing IDB transaction/full snapshot, capture profile or
verified device, or subscribe directly to key invalidation. Its transition checks
alone are not the narrower terminal-chain contract: an adapter must explicitly
exclude genesis resolution, reactivation and unsupported cohorts. Preserve the
old API's accepted behavior; do not globally tighten it as an incidental refactor.

The future private composition must have **one owner of preparation and commit**:

1. A private factory captures transaction/session/profile, auth/bindings, keys and
   genuine verified device. External inputs are scope and earliest sequence only;
   caller-provided snapshots, diagnostics or predicted records are not grants.
2. Load complete snapshot A. Freshly authenticate F/H/Content, source and all
   pending wire; classify active vs terminal cohort from actual owner evidence.
   Establish earliest-event/barrier order, not a caller's claimed sequence.
3. Ask the actual Metadata owner to privately prepare proof/transition from its
   retained AEAD. Refactor its family validation into a module-private preparation
   and synchronous scheduling seam; keep owner checks shared, not copied into K.
   Re-read A after asynchronous preparation; any drift invalidates the plan.
4. Privately construct predicted B from **that owner's** transition: only the two
   allowed records differ. Authenticate complete B, current source and all
   retained intervals, explicitly distinguishing hypothetical owner result from
   genuinely durable applied evidence. Never persist or return this prediction,
   feed it to public .13–15 as a certified past, or fake a positive fixture proof.
5. Retain A, predicted delta, original opaque owner identity and lifecycle guards
   only in the private closure/WeakMap. No public `fromDiagnostic`, transferable
   callback, sidecar authorization token or arbitrary transaction write callback.
6. Consume the new handoff once (including abort). Open one ten-store readwrite
   transaction; compare full A; recheck lifecycle and family dependencies; schedule
   exactly the owner delta; recheck guards on requests. Auth **and key** invalidation
   abort active transaction; profile/session/device checks must remain current.
7. Reload actual durable state; authenticate it freshly, compare to predicted B
   or reject stale concurrent changes. Return only a bounded outcome diagnostic.
   A new attempt/restart prepares again. Do not persist or resurrect the plan.

This is an illustrative contract, **not an existing API**. No new public source
or commit authority is proposed. Storage scheduling precedent is [inventory]
`BrowserResolutionApplyRuntime.commit`; lifecycle/identity precedent is
[prefix] `guard`/`commit` and [db] `syncTransaction`/`close`. The accepted .13–15
public `inspect` surfaces must remain read-only and independently rechecking.

**Unaccepted prerequisite:** an internal verifier must handle complete actual
active/pending Metadata state and owner-derived hypothetical post-state without
weakening .13–15's terminal-only public semantics. It must distinguish pending
rows from genuine applied evidence; test their references/AEAD and barriers,
not temporarily relabel/drop them. For the active pre-state, independently establish `q(M) < q(E)` and the
nondeleted interval for retained Content too: today's live tip check alone does
not establish that sequence fence. For predicted deletion, use the genuine
owner-prepared D and require every applied Content E before D. Do not claim to
recover its wall-clock apply time. After a terminal commit, pending Content may
remain readable but never first-applied; later pending Metadata remains a barrier
until its separate full-account admission is proved. No generic "historical=true"
flag or catch-live-failure→try-historical fallback is acceptable.

## 7. Commit, restart and rollback state machine

`received → authenticated A → private owner preparation → authenticated predicted B
→ same-transaction CAS(A)+owner writes → native complete → fresh durable verification`.
Prefix qualification/commit is a **later separate state**, not part of Metadata
owner commit and not supplied by .15 diagnostics.

| Event or failure point | Exact outcome |
|---|---|
| Competing browser tab | [db] `openBrowserPersistence` exclusive Web Lock normally yields `writer_busy`; independent handles/queued writers still need exact full-inventory CAS, no last-writer overwrite |
| Source, binding, Metadata head, cursor or unrelated account-range record changes after prepare | CAS mismatch aborts both owner writes; discard handoff, manual fresh preparation only |
| Device token changes or becomes invalid | [device] `currentBrowserDevice` fails; no new registration/HTTP or reuse of stale plan. Unobserved remote server revocation is not detectable by this local token; server gates remain independent |
| Key lock, logout, profile/session/epoch change before native complete | Active transaction abort via lifecycle subscriptions/checks; no successful owner result. [db] `close` drains/aborts pending transactions before releasing lock |
| Request error, explicit abort, crash before commit | No partial owner head/proof or inbox state; original received row remains, no source/cursor change |
| Crash after native commit before post-check/prefix | Durable head+applied proof survive together; reopen fresh session and reconstruct exact result without duplicate append/apply |
| Actual state fails post-commit authentication or differs from prediction | Report committed outcome with verification failure/uncertainty, halt further applies/prefix/ACK. Preserve evidence. Never report rolled back, erase committed proof or silently retry |
| Later Q/G cursor transaction abort/failure | Earlier genuine owner commits remain. No pass-wide rollback; fresh accepted prefix preparation may retry only where its own contract supports the actual history |
| Replayed already applied Metadata, including old ancestor | Authenticate real durable evidence and current complete source; return already_applied without history append or descendant rollback. Fresh complete snapshot, no stale-plan replay shortcut |
| Existing proven cursor plus new received events | Reauthenticate old proven interval and new complete inventory; cursor cannot qualify received rows or authorize a later event |
| Missing sequence, unsupported earliest row or earlier unresolved fork | Stop at earliest barrier, no automatic retry or later apply. Corrupt/unsupported later inventory may reject entire pass with no candidate |

The present G/Q cannot commit a terminal-delete historical candidate. A future
owner success therefore must not imply that the pass or prefix succeeded. K will
need separately accepted control flow that can load terminal history before its
current live H/Q calls and preserve committed results when fresh verification
fails. No such change is implemented or implicitly authorized here.

## 8. Security invariants and STOP conditions

- Full account history and independent source validation on A and B; no filtered
  v9 inventory, fabricated Head1, borrowed unrelated proof, source revision or
  membership repair. F/H-only historical ordering remains evidence-selected.
- Metadata changes only its two allowed records. Retained wire/AEAD, original
  dependency digests, tombstones, source identity and proofs remain immutable.
- Read-only .13/.14/.15 results are never accepted as owner/source/prefix/ACK
  tokens. A predicted owner state is not proof that a transaction occurred.
- One accepted F, received peer clean coverless Metadata only; no new Resolution
  generation, local authorship, resurrection, cover or structural child inference.
- STOP if pending/active/terminal full-account admission cannot be proved, the
  private owner cannot schedule in the caller-owned native transaction, exact
  delta/CAS/lifecycle cannot be preserved, or fresh post-state fails validation.
- STOP for missing ancestors, forged/repeated event or sequence, foreign binding,
  stale source/tip, unresolved fork, unsupported family/Stage dependency or
  ambiguous cohort. Never switch verifier after a failed check.
- STOP before any new schema/proof/wire/backend requirement. Current IDB10 old
  client/migration barriers stay fixed. This audit resolves storage feasibility,
  not all unsupported history/evidence questions.

## 9. Genuine acceptance and CI capacity

No tests/builds were run for this docs-only audit. Evidence is source inspection
and retained genuine .11–15 tests; [stop-tests] remains byte-identical. A future
implementation must use actual F/H/O/Metadata owner operations and real encrypted
records, never fabricated positive inbox proofs/heads.

| Bounded future test cohort | Required acceptance |
|---|---|
| F protocols2/3, four strategies, Content ID0/ID1; Metadata protocols2/3 | Actual F/H/O with coverless Metadata update/delete; exact own proof, immutable history and unchanged source; keep_both outputs/roles retained |
| Conditional create and ordinary variants | Genuine no-head Legacy-F control if reconstructible; Content-F missing/late genesis rejected; same-project second genesis, unrelated project and post-delete update rejected |
| Pre-state and predicted/durable post-state | Active/pending/terminal evidence-selected modes; later pending Metadata never dropped; pending Content both sides of D remains a barrier; authentic M<E<D for every actual Content outcome |
| Forgery and conflicts | Missing/wrong proof/bootstrap/ancestor, sequence gaps/duplicates, tombstone reactivation, cover, own/local, Stage/StageOrder, unsupported generation and open fork all reject without delta |
| CAS races | Change each ten-store inventory component after preparation, including unrelated project/source/cursor, with genuine actors where possible; exact stale rejection and zero partial writes |
| Revocation | Auth/key/profile/epoch/device invalidation before/during prepare and actual IDB writes; abort, no plan reuse or unauthorized HTTP |
| Native crash/restart | Real disk-backed Chromium, crash before native complete vs after commit before post-check/prefix; head+proof atomicity, preserved received/applied state, exact replay after full process reopen |
| Native competing tabs and rollback | Exclusive lock plus stale-prestate race; real request/transaction abort after first scheduled owner write; both writes roll back, all other stores byte-identical |
| Authority isolation | Public .13–15 unchanged; old .11 STOP unchanged; diagnostic/foreign-owner/old plan misuse rejects; writes allowed exactly2 records, source/cursor/HTTP/nonce allocations0 in commit |

Use separate meaningful fixture hooks and assertion phases, **each ≤5000ms**;
no timing exemption, retry, skip or timeout increase. Fixture encryption may
allocate its real nonces; a Metadata apply/replay must not re-encrypt original
wire or invent source nonces. Test current owners unchanged alongside private
composition; retain N/O/P/Q/K and historical regression assertions.

Independently accepted .15 run39768042164 measured Frontend admin **35m49s/40**
and complete-project **26m13s/40**. Existing [Cloud workflow][workflow] places the
241-case isolated historical command plus native historical acceptance in
complete-project with `--maxWorkers=1`; Frontend has its own mandatory suites and
O/P/Q/K native acceptance. Do not duplicate new long fixtures into both jobs.
For planning only, reserve **2–4 runner minutes** for a bounded private primitive
suite and **1–2 minutes** for 4–8 reused disk profiles; these are estimates, not
measurements or proof a future job fits. Prefer complete-project only for new
isolated checks, keep Frontend coverage intact, and measure actual fixture/body/
step timings before broadening. If measured headroom is inadequate, move complete
indivisible suites with path/coverage accounting between existing mandatory shards;
retain six job names/all checks and ≤40-minute budgets, or STOP with a reviewed
partition proposal. Do not append workloads blindly to Frontend's4m11s margin.

## 10. Recommended numeric next step and remaining blockers

**Propose C21.2.17 — private Metadata atomic-handoff prerequisite repair**, narrower
than mixed-K routing. First implement/test the internal pending/active versus
terminal validation boundary and private owner preparation/synchronous scheduling
seam with a dormant isolated full-ten-store commit. Limit to genuine imported,
coverless same-F-project Metadata create/update/delete where the complete cohort
can actually be proved; record unsupported create baselines as explicit blockers.
Initially admit at most one pending Metadata event (the selected earliest row);
additional pending Metadata is an explicit whole-preparation barrier, never
filtered out. General multi-pending admission requires later review. Preserve
public historical reader semantics and old Metadata API behavior. No K,
G/Q, production scheduling or prefix integration in this prerequisite slice.

This recommendation follows the two concrete CONTRACT STOPs above: direct reuse
of terminal readers and family-scoped commit is insufficient today. Review and
independently accept the private primitive before proposing a later numeric
mixed-K routing/cursor integration; do not silently implement that here or rename
historical stages. If genuine pending/pre/post evidence is still insufficient,
C21.2.17 must STOP before writing an owner result.

Stage needs its own historical Metadata coverage, complete Stage tip/history,
tombstone/dependency contract and private handoff; StageOrder additionally needs
exact authenticated membership/Stage reference coverage, including unsupported
child/deletion semantics. [stageApply.ts][stage] `prepareStagePrefix` and
[stageOrderApply.ts][order] `prepareStageOrderPrefix` / `dependencies` are live
family owners, not accepted historical substitutes. No Stage routing is enabled.

C21 closure/full production sync still needs reviewed K and G/Q terminal-history
composition, all required family/dependency routes, Content writer/sealing/upload,
immutable receipts/self-echo/own authorship where required, independent transport/
capability/ACK gates and real multi-device failure/lifecycle acceptance. VPS
hardening, independent security audit, closed registration, owner reminders,
PUBLIC RELEASE BLOCKED and all release gates remain mandatory. Web **89.36%**,
C21 IN PROGRESS, C21.2.08 NOT CLOSED, C21.2.11 IMPLEMENTATION STOP, `ready=false`.

This docs-only change matches neither [Cloud][workflow] nor [SQLite][sqlite]
push path filters: both **NOT EXPECTED**. No workflow edits, CI polling or waiting.

### Простыми словами

Сохранённую историю после удаления Metadata браузер уже умеет отдельно проверять.
Но безопасная запись — другой шаг: нужно одновременно проверить всю историю и
записать только настоящее изменение Metadata, не затрагивая заметки и курсоры.
Существующая база позволяет такую атомарную операцию, а интерфейс владельца
Metadata пока требует внутренней доработки. Проверка также пока не принимает
неприменённые Metadata-события в историческом режиме. Поэтому следующий
предлагаемый шаг — изолированно доказать эти две границы. Маршрутизация, ACK и
полная Web-синхронизация этим аудитом не включены.

[sync]: ../../frontend/src/platform/web/syncDurability.ts
[db]: ../../frontend/src/platform/web/persistence.ts
[owner]: ../../frontend/src/platform/web/importedMetadataApply.ts
[inventory]: ../../frontend/src/platform/web/resolutionPlanner.ts
[prefix]: ../../frontend/src/platform/web/resolutionPrefix.ts
[dependency]: ../../frontend/src/platform/web/historicalMetadataDependency.ts
[mixed]: ../../frontend/src/platform/web/mixedSourceValidation.ts
[f-auth]: ../../frontend/src/platform/web/resolutionAuthentication.ts
[h-auth]: ../../frontend/src/platform/web/resolutionHistorical.ts
[k]: ../../frontend/src/platform/web/v10MixedRecovery.ts
[transport]: ../../frontend/src/platform/web/v10Transport.ts
[reader14]: ../../frontend/src/platform/web/historicalContentAuthentication.ts
[reader15]: ../../frontend/src/platform/web/historicalPrefixQualification.ts
[device]: ../../frontend/src/platform/web/deviceRegistration.ts
[ack]: ../../frontend/src/platform/web/ackPrerequisites.ts
[reader-ack]: ../../frontend/src/platform/web/provenPrefix.ts
[default-k]: ../../frontend/src/platform/web/v10Recovery.ts
[stop-tests]: ../../frontend/src/platform/web/postFMetadataBoundary.spec.ts
[live]: ../../frontend/src/platform/web/noteTransportPrerequisite.ts
[workflow]: ../../.github/workflows/cloud-backend-tests.yml
[sqlite]: ../../.github/workflows/sqlite-sync-tests.yml
[stage]: ../../frontend/src/platform/web/stageApply.ts
[order]: ../../frontend/src/platform/web/stageOrderApply.ts
