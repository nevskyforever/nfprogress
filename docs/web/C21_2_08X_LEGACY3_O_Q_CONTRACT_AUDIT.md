# C21.2.08X — Legacy3 independent-source O owner and Q prefix contract audit

**AUDIT COMPLETE — documentation only.** Baseline `dc5cad87e9bf07b6d529e702ecdeaad988d3a5cf`, branch `6.0`; local and origin matched and the worktree was clean. Protected Python bytecode matched the CI1 baseline. No production code, test, workflow, database, wire, or cryptographic behavior changed in X.

## Independent W-CI1 acceptance

GitHub run [40116362152, attempt 1](https://github.com/nevskyforever/nfprogress/actions/runs/40116362152) is for exactly the baseline SHA and completed successfully. The six jobs were Android compression packaging, Frontend admin, complete-project, cloud and legacy regressions, foundation, and content-action; all six concluded `success`. This independently accepts bounded Legacy3 G from W-CI1. W remains PARTIAL because Legacy3 Q and its independent-source owner have not been implemented or accepted.

The original W run `40079162004` remains recorded in history as five of six successful jobs with Frontend admin failing one randomized ciphertext-rejection assertion. CI1 changed only the test mutation: both evidence-envelope and original-wire ciphertext are now guaranteed to differ, and the real authentication rejection and unchanged-persisted-state assertions remain. No production authenticator repair was needed.

## Existing source and write contracts

The genuine F root is one accepted first-generation Legacy3 `Resolution4` with its original encrypted `legacy_resolution_v2`, authenticated parents and dependencies, `Proof1`, inbox10 closure, and encrypted source-before/source-after evidence. T accepted F, U accepted H original/retained continuations, and W-CI1 independently accepted G contiguous prefix qualification. `keep_both` is one Resolution sequence with two distinct output Note identities and two H Head2 chains.

O is already a dormant `BrowserV10OrdinaryApplyRuntime` with a narrow supported shape: one received, remote-authored ordinary Note event in the F root's project, under the active `import_remote/captured` project/bootstrap binding. It accepts Legacy2 upsert/delete with the existing project/HTML source restrictions and framed Content3 v1 events after their Metadata/Stage prerequisites authenticate. It rejects own-device and raw Legacy ordinary received3 events, unrelated projects, the F original/retained identities, unsupported bindings, and later or non-earliest received events.

O's existing mutation checks already distinguish create from update/delete:

- A create is a genuine event with `parent_event_id = null`, revision 1, no Head1, no prior candidate for that identity, and no current local Note identity anywhere in the account.
- An update or delete must name the currently authenticated peer Candidate at the single-tip Head1, advance its Note revision by one, preserve the exact route, and follow an earlier server sequence. A tombstoned Note cannot be resurrected; another delete may follow its authenticated tombstone parent.
- Both paths use the exact root project and bootstrap. The current encrypted local source snapshot must match the captured inventory before a new project `source_revision` is prepared.

The existing mixed-source fold anchors the root project at F's authenticated `source_after` snapshot and source revision R0. It reconstructs each existing member's latest pre-F applied peer projection, then requires each post-F applied H/O transition to have exactly the next source revision, a prior server sequence, valid parent/revision lineage, and the expected Note projection. It checks encrypted project and Note records, member identity, cross-project Note identity collisions, complete account sequence density, and real Metadata/Stage/StageOrder owner proofs. H output identities are handled separately as original/retained Head2 chains; O cannot take either role. An unresolved H conflict can be retained by the prefix validator only for those two F output identities, with no local-unsealed member or source projection. O apply itself rejects an open conflict.

The existing evidence was reviewed in `v10OrdinaryApply.spec.ts` (real Legacy2/Content3 create, update, delete, rollback, CAS and lifecycle cases), `resolutionMixedPrefix.spec.ts` (real O/H interleavings, mixed family counts, blockers and cursor-only commit), `resolutionMixedContinuation.spec.ts` and `v10MixedRecovery.spec.ts` (recovery order and no fallback), and `legacy3Continuation.spec.ts` / `legacy3Prefix.spec.ts` (current Legacy3 O/Q rejection). The browser prefix harness already covers real F/H production, native full-inventory CAS, disk restart, uncertain completion and a pinned older bundle; Y must extend its old-bundle mode from old U to exact W-CI1 and add genuine O/Q durable history.

An O prepare is read-only. Its commit transaction snapshots and compares the full ten-store resolution inventory, checks lifecycle and local-source CAS, then atomically writes exactly:

1. `localProjects`: encrypted project source revision and membership;
2. `localNotes`: the encrypted Note/tombstone projection;
3. `legacyNoteHistory`: the ordinary Candidate and its Head1;
4. `inbox`: the existing Legacy2 `note_proven` proof or Content3 `content_note_proven` proof.

For Content3, the existing opaque transport commit writes the Candidate in the same transaction after rechecking Metadata owner/binding dependencies. Neither form writes cursors, receipts, outbox, ACK, capabilities, project bindings, owner heads, or any server state. Auth, key, device, profile, inventory, and native transaction checks already exist in the dormant O owner; the Legacy3 O path must use and re-test those same checks.

## Exact blocker and smallest O extension

`v10OrdinaryApply.ts` currently runs `validateMixedSourceInventory()` and `authenticateContinuationHistory()` before it can examine a received O event. Both deliberately enter `rejectLegacy3ResolutionRoots`; the first F prerequisite therefore stops O before the existing create/update/delete checks. H does not repair this: H owns only the F original/retained Head2 outputs. G's prefix grant cannot be supplied to O, and the generic root guard cannot be weakened.

The smallest proposed O change is an owner-specific **O history composition** that authenticates the same complete captured inventory through the strict Resolution4/Proof1/inbox10 verifier and strict continuation core, then runs the existing mixed-source historical fold over that authenticated history. It admits exactly one Legacy3 F root and its accepted H history. It does not admit a second Resolution, alter transport routing, or convert a public diagnostic to authority. O then proceeds through its existing exact event eligibility, source snapshot, predicted post-state validation, and atomic commit path. The existing generic `authenticateContinuationHistory`, default K/readers, private Metadata routes, recovery defaults, and G's guard remain rejecting outside their separately authorized owners.

The explicit `bindMixedV10Recovery()` path also begins with the generic rejecting history call before it can use its mixed prefix owner. Y must route this dormant composition through the new Q-owned verifier, use authenticated role identity to select H versus O, and retain the independent prefix commit. `BrowserV10Recovery.bind()` and default production recovery keep their current generic Legacy3 rejection. No O/Q owner is added to production sync composition.

Mint an O-specific opaque one-use history request from O's own runtime only. Bind it to the exact O runtime, scope/account, device and profile, active auth epoch and key lease, complete loaded inventory, and live `current()` predicate. Store the request in a private WeakMap; consume and delete it on success or failure. No allow flag, caller-provided history, G/H token, diagnostic DTO, public result, or fallback after an authentication error may enter this path. O must require exactly the accepted first-generation F root before using the O-specific composition.

The existing `validateMixedSourceInventory()` is safe for current owners because it obtains its own generic authenticated history. The implementation should factor its strict fold so O/Q can pass only the history produced inside their owner-specific composition. That fold result is validation data, never an O write token or Q prefix certificate. Keep the owner-private O plan and Q certificate as separate WeakMap capabilities. Do not make a generic `allowLegacy3` export or accept an arbitrary caller-supplied history object.

## Q composition and prefix behavior

After genuine O commits, Q must authenticate the complete account history afresh from the same inventory snapshot. A successful O apply is evidence for one ordinary Note transition; it is not a Q certificate. Q composes:

1. The exact F Legacy3 Resolution root and its original proof/closure.
2. Complete H original and (if present) retained output histories.
3. Each eligible O Candidate, Head1, inbox proof, encrypted before/after projection, and source-revision transition.
4. The cross-role order between H and O, including the account server sequence and root project's R0+n source revision.
5. Project membership and the final local Note projections.
6. Metadata, Stage, and StageOrder dependencies through their existing owners.
7. Every account server sequence through `pull_cursor`, including independently owned events from other projects.
8. The existing H-only conflict-preservation boundary; an open independent conflict or unqualified incoming event stops the prefix.
9. Exact `ack_cursor <= proven_prefix <= pull_cursor` state and the complete captured inventory.
10. Current account, auth/key lease, device, profile, and native transaction lifecycle.

Q gets its own one-use private request and its own certificate/commit ownership. It cannot consume H or G requests, and G cannot consume Q authority. Route selection comes from the authenticated F root and actual independent applied history, never a caller flag. If mixed validation or source authentication fails, Q rejects; it never retries through G. If authentication succeeds but a present sequence is not qualified, the existing earliest `unproven_family` blocker is retained; a missing sequence yields `missing_sequence`. Corruption in an already claimed prefix rejects instead of lowering it. The existing native cursor-only commit and `advanced` / `already_proven` / `no_progress` semantics can be reused; only `cursors.proven_prefix` changes. G continues to reject the same-root post-F independent Note cohort requiring Q.

There is one explicit boundary for unrelated projects. Their Metadata, Stage, and StageOrder rows can be interleaved and qualified by their existing authenticated owners. Current mixed source reconstruction is anchored by F's `source_after` for the F project; it does not independently replay a second project's entire Note `source_revision` chain from an authenticated baseline. Therefore an unrelated project's ordinary Note history must not be counted as a Q-qualified Note family under this Legacy3 cohort until that project has an authenticated source-history anchor/fold. This is not needed for the bounded O target, which is restricted to the F project. If X is intended to include arbitrary second-project Note mutations, STOP for a separate source-witness contract before implementation.

## Compatibility and durable-record decision

For the bounded same-F-project O/Q cohort, existing Candidate v2, Head1, inbox `note_proven` or `content_note_proven`, encrypted `localProjects`/`localNotes`, F Resolution4/Proof1/inbox10, H Head2 records, and current family proofs carry the needed evidence. The F `source_after` envelope supplies the historical R0 baseline; the applied O Candidate and proof identify the event, parent, operation, sequence and encrypted projection; the mixed fold joins those to the next source revision and final membership. Q's certificate remains ephemeral in memory.

Accordingly, DB10 and its twelve existing stores are sufficient for this bounded contract. The ten stores in `resolutionInventoryStores` are the complete history/source/cursor comparison set; `BrowserPersistence.syncTransaction()` adds `identities` and `accountBindings` to each scoped native transaction and checks them against the bound scope. Existing prefix certificate and cursor formats are sufficient. No new durable proof version, migration, backend, PostgreSQL, wire field, or cryptographic change is required for same-project O and Q. No silent record reinterpretation is authorized. If implementation cannot establish the exact F R0 and O before/after relationship using the existing encrypted records, stop rather than invent a positive witness.

The older W-CI1 bundle at `dc5cad87e9bf07b6d529e702ecdeaad988d3a5cf` still has the generic Legacy3 root guards in O and Q. With unchanged DB10 formats it is expected to reject a later F→O/Q inventory without writing or deleting its encrypted records. This is a compatibility expectation, not yet native acceptance for O/Q data. Y must build that exact old bundle, open copies containing genuine newly applied O/Q records, assert O/Q/history/recovery attempts reject with the full twelve-store snapshot unchanged, then reopen the same copies with the new bundle and verify durable reauthentication and Q replay. Never run old and new writers concurrently.

## Decision matrix

Labels describe evidence at the end of X. “Proposed supported” is a future Y contract, not current Legacy3 O/Q acceptance.

| Case | Expected decision | Conditions / boundary |
|---|---|---|
| All four F strategies | **Accepted existing prerequisite** | Genuine accepted F; `keep_both` remains one Resolution sequence with separate original/retained identities. |
| Independent Legacy2 Note create | **Proposed supported case** | Received2, remote peer, same F project/bootstrap, new global Note identity, null parent/revision1, existing Legacy2 HTML/project restrictions. |
| Independent framed Content3 Note create | **Proposed supported case** | Genuine framed v1 event, new identity and valid exact Metadata/Stage dependencies through existing owners. |
| Independent update | **Proposed supported case** | Parent is the authenticated single-tip peer Head1 for that identity; exact route and next Note/source revisions. |
| Independent delete | **Proposed supported case** | Same authenticated parent rules. No resurrection; repeated delete only from a proved tombstone chain. |
| H original changes interleaved with O | **Proposed supported case** | H uses original Head2 only; applied server order and project source revisions are contiguous. |
| H retained changes interleaved with O | **Proposed supported case** | Only after `keep_both`; retained identity keeps its distinct Head2 and source chain. |
| Metadata/Stage/StageOrder dependencies | **Accepted existing prerequisite** | Authenticated by the existing family owners over the complete account inventory; Content3 prerequisites name the exact accepted dependency. |
| Another project: Metadata/Stage/StageOrder interleaved | **Accepted existing prerequisite** | Real unrelated project rows remain in account sequence and are qualified by their own owners. |
| Another project: ordinary Note events | **Requires new contract** | No complete independent source-revision anchor/fold exists for a non-F project. Do not qualify these Note rows in Legacy3 Q yet. |
| Independent source revision gap | **Explicitly blocked case** | `revision_order`; no skip. A server-sequence hole is instead the earliest `missing_sequence`. |
| Project membership mismatch | **Explicitly blocked case** | Encrypted project membership must equal the reconstructed Note identities. |
| Missing parent or unpublished parent event | **Explicitly blocked case** | The selected remote O event may be received, but any parent must be an earlier authenticated applied peer Candidate. Own-device, local-unsealed, or unreceipted local source cannot serve as its parent. |
| Head1 versus Head2 role mismatch | **Explicitly blocked case** | Independent O Notes use single-tip Head1. F original/retained outputs use their respective Head2 chains; no role conversion. |
| Unresolved independent Note conflict | **Explicitly blocked case** | O does not commit while the mixed source validator reports it; Q cannot qualify its sequence. |
| Cross-project Note identity collision | **Explicitly blocked case** | Identity is account-wide; one Note ID cannot be owned by two projects. |
| Raw Legacy ordinary received3 | **Explicitly blocked case** | No protocol cast, decode fallback, or ordinary Legacy admission on protocol3. |
| Second Resolution generation | **Explicitly blocked case** | This contract is one first-generation F root only. |
| Implicit tombstone resurrection | **Explicitly blocked case** | A tombstoned identity can only continue through the allowed delete chain. |
| Auth/key/device/profile invalidation | **Explicitly blocked case** | Request, prepared plan, certificate and transaction abort when the bound lifecycle is no longer current. |
| Full process/disk restart | **Proposed supported case** | Reauthenticate durable F/H/O evidence after reopen; ephemeral O/Q tokens and prefix certificates never survive restart. |
| Old W-CI1 bundle sees new O/Q data | **Proposed supported case** | Exact old bundle rejects without writes and preserves all twelve stores; same-copy recovery with Y bundle must pass. |

## Required Y acceptance

Use real producer paths only. The next implementation acceptance should include:

- Genuine F Legacy3 commit for all four strategies, then actual H original/retained applies.
- Actual encrypted O Legacy2 and Content3 creates, updates and deletes; exact F-project identity, bootstrap and route checks; create versus already-authenticated parent cases.
- Reconstruct F R0 and every O/H source revision in server order. Include Metadata/Stage dependencies and unrelated-project Metadata/Stage/StageOrder interleavings; assert unrelated-project Note rows remain unqualified under this contract.
- A separate Q prepare, calculate, prepareCommit and native commit. Assert exact family counts, contiguous prefix, earliest blocker, `keep_both` one-sequence accounting, and cursor-only writes.
- Negative O/Q cases for membership, full source revisions, missing parent, unproved publication, Head1/Head2 substitution, independent conflict, identity collision, raw3, second Resolution, tombstone resurrection, dependency corruption, sequence gap, forged/reused/cross-owner token, H/G/Q token substitution, and no-fallback behavior.
- Inject O abort at each source/history/inbox write boundary and assert exact full-store rollback. Race O/Q against inventory mutation and competing tabs; stale plan/certificate must not commit.
- Inject successful native commit followed by lost completion and reconcile from durable state. Close/reopen the complete Chromium process and disk profile with fresh auth/key/device runtimes; reauthenticate F/H/O, recalculate and replay Q.
- Build the exact old W-CI1 bundle from the pinned SHA. On disposable copies with genuine O/Q records, verify rejection and zero writes, then verify the same copies recover under Y. Do not claim OS power-loss guarantees and do not run old/new writers concurrently.
- Preserve all current F2/Content3 O/H/G/Q tests, generic Legacy3 reader rejections, K/mixed-K/private Metadata/readiness/ACK negatives, all four F strategies, and all unrelated CI suites.

No hand-built applied proof is a positive fixture. New unit and Chromium assertions remain blocking. A test-only producer may corrupt disposable data for negative cases.

## CI capacity recommendation

Run40116362152 measured these actual successful job durations (all jobs retain their existing 40-minute limit):

| Job | Actual CI1 runtime | Placement |
|---|---:|---|
| Foundation | 20m07s | New isolated O/Q unit tests only |
| Content-action | 22m35s | New native O/Q Chromium/restart/old-W acceptance |
| Complete-project | 30m31s | No additional O/Q suite |
| Frontend admin | 36m33s | No additional O/Q suite |
| Cloud and legacy regressions | 3m56s | Existing suite unchanged |
| Android compression packaging | 1m54s | Existing suite unchanged |

The Foundation and Content-action shards are the only safe destinations in the current six-job matrix. Plan no more than eight additional minutes of O/Q unit work in Foundation and eight minutes of O/Q native work in Content-action, with at least five minutes left as reserve. Against the accepted CI1 measurements this yields 20m07s + 8m + 5m = 33m07s for Foundation, and 22m35s + 8m + 5m = 35m35s for Content-action. Both fit below 40 minutes. These are planning envelopes, not measured Y runtimes; locally time exact commands before editing workflow placement and compare actual Cloud step timings after independent acceptance. If either cohort exceeds its eight-minute envelope or external setup variability erodes the five-minute reserve, stop for a separately authorized capacity design. Do not add a seventh job, change timeout, move tests onto Frontend admin/complete-project, or weaken/skip existing coverage.

## Status and next stage

The bounded same-F-project O/Q contract is implementable by reusing the accepted F/H evidence, existing O write owner, existing mixed-source fold, existing family owners, and existing prefix certificate/cursor. It needs distinct private O and Q history requests and a Q-owned mixed certificate path; it does not need a new durable proof. Cross-project ordinary Note source reconstruction is outside this bounded contract and requires a separate witness contract before that behavior is admitted.

Recommend separately authorized **C21.2.08Y — bounded Legacy3 O admission and Q composition**, scoped to one genuine F root, same-F-project independent Notes, existing account-family owners, the current ten-store inventory CAS, and the CI budgets above. Y must keep O/Q dormant from production sync and leave readiness/ACK/capability gates false. X itself authorizes no implementation or activation.

C21/C21.2 remain IN PROGRESS; C21.2.08 remains NOT CLOSED; W remains PARTIAL; bounded G is REMOTELY ACCEPTED; Q remains IMPLEMENTATION STOP; T/U remain REMOTELY ACCEPTED; V is AUDIT COMPLETE; C21.2.11 remains PARTIALLY RESOLVED; C21.1.06 is NOT LOCAL COMPLETE. Web remains 89.36%, `ready=false`, `declarationAllowed=false`, `writerAuthorized=false`, registration CLOSED, PUBLIC RELEASE BLOCKED. C22/C23/PF6.0/RC, VPS, landing, mandatory CI, security, and owner release gates are unchanged.
