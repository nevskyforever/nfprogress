# C21.2.08T — Legacy3 durable owner and retained-F2 exact join

**LOCAL COMPLETE / REMOTE ACCEPTANCE PENDING.** Starting branch6.0, HEAD, origin/6.0 and actual remote ref all
matched `2320549e1c2e4ef3cc87bd91ee109c8e9bb7ebc6`; worktree was clean and protected
bytecode matched the established SHA-256 values. The owner explicitly authorized
Option A from [S](C21_2_08S_LEGACY_V3_DURABLE_CONTRACT.md) for this bounded stage.
S remains DESIGN COMPLETE and [R's STOP](C21_2_08R_LEGACY_V3_DURABLE_CONTRACT_STOP.md)
remains valid historical evidence. No additional durable variant is admitted.

## Implemented identity and private authority

| Received protocol | Authenticated codec | Original operation | Content wrapper digest |
|---|---|---|---|
| 2 | legacy_resolution_v2 | resolution | null |
| 3 | content_note_resolution_v2 | event | authenticated wrapper digest |
| 3 | legacy_resolution_v2 | resolution | null |

`resolutionTransportKind` admits exactly these descriptor routes. F first opens
the original AEAD under current canonical-user/project/note context and then runs
the one selected strict decoder. Decoder failure never invokes another codec.
Only the validated result enters the private WeakMap plan; the protected local
source hook obtains `transportKind` from that plan, not from a caller flag or
read-only diagnostic. It no longer assumes received3 implies Content.

Raw Legacy retains project routing, HTML, stage_id=null, source_type=project,
source_map_id=null and source_node_id=null, including tombstones/retained output.
Full real parent/publication/group/bootstrap/source checks remain. Mixed genuine
Legacy/Content parents retain their own codec and dependency authentication.
Pending raw3 keep_both events participate in clone reservation and collision
checks. The account-wide first-F constraint is unchanged: further Resolution
generations remain unsupported.

The original submitting transport remains **UNKNOWN**. Neither raw codec nor a
retained F2 receive proves the original submission endpoint. Original wire and
received protocol are retained verbatim. Resolution4, Proof1, inbox10, Head2,
Transition2, DB10/twelve stores/indexes and crypto/AAD versions are unchanged.

All ten identity distinctions and exact hash preimages in S remain authoritative.
In particular, wire_digest hashes `{protocol_version: actualReceive, item: parsedOriginal}`;
payload_digest hashes the strict Resolution v2 payload; dependency_digest uses
the original received1 row, captured owners/bindings and null dependencies for
raw Legacy. Encrypted evidence binds exact public Resolution identity and original
decrypted bytes, with a literal null wrapper digest for raw3. Record, transition,
encrypted output and proof outcome digest algorithms are unchanged. Existing
F2/Content3 records are never converted, re-signed or rewritten.

Historical authentication additionally requires Resolution and inbox protocols
to agree. This must be explicit now that the same raw descriptor may be received
on2 or3; the previous operation-to-protocol implication no longer suffices.
Exact inbox/proof/reference/header/sequence/source equality and encrypted evidence
identity remain mandatory. Rehashed public data cannot replace encrypted evidence.

## Atomic owner and exact write set

F preparation reopens original payload and actual published parents, captures the
complete ten-store bounded inventory, prepares the protected encrypted source,
and authenticates the predicted full state before any write. Commit repeats CAS
against the whole captured inventory and current key/auth/device/profile context.
Its single native readwrite transaction changes only:

- `localProjects`: one encrypted project/source revision update.
- `localNotes`: original encrypted output and, for keep_both, one retained output.
- `legacyNoteHistory`: append Resolution4 and GroupTransition2, replace original
  Head2, and append retained Head2 for keep_both. Preserve candidates, original
  group and frozen local versions byte-for-byte.
- `inbox`: replace the exact received1 row with inbox10/Proof1, preserving original
  protocol, descriptor/ciphertext string, event and sequence.

Ordinary strategies perform six puts/adds; keep_both performs eight. The other
transaction stores (`outbox`, `receipts`, `projectBindings`, `ownerHeads`,
`legacyNoteIntents`, `cursors`) are CAS witnesses, not write targets. F does not
advance pull/proven/ACK cursors, allocate outbound ordinals, send HTTP or alter
capabilities. Initial authorized receive separately retains its page/pull cursor.

Native request failure, transaction abort and in-flight key/logout/profile
invalidation roll back the complete write set. A lost completion signal after
native commit leaves a complete result; fresh disk reconciliation authenticates
that result without allocating another clone/revision/proof. Reconciliation is
read-only and still requires exact current F output; broader historical source
continuation remains a separate H route.

The factory remains absent from normal persistence composition. The new producer
is invoked only through the existing dormant factory and acceptance harness;
K/default routing does not dispatch raw3 into it.

## Separate retained-F2 join

`BrowserV10TransportRuntime.joinRetainedF2(scope, since, rawPage, eventId)` is a
separate read-only entry. It validates a v3 page and target note/resolution item,
loads the complete bounded inventory, requires dense retained server sequences,
and matches a genuine retained protocol2 inbox10/Proof1 and Resolution4.
It compares the exact parsed original descriptor and every encrypted-object field,
including device, event, project/note, sequence, revision/timestamp, nonce and
ciphertext. A valid different re-encryption rejects.

It reauthenticates original F2 AEAD/evidence, parents/publications/bootstrap,
accepted historical descendants and current encrypted sources using the existing
H historical/source verifier. A second readonly snapshot must equal the first
before returning; current account/session/key/registered device/profile guards
remain active throughout. Missing/corrupt evidence or a changed inventory rejects.
No cache/private in-memory join token is needed after a full restart.

The frozen diagnostic reports matched event/sequence, receivedProtocol3,
retainedProtocol2, commitAuthorized=false and ackAuthorized=false. It is not an
apply token or prefix certificate. There are no writes to source/history/inbox,
bindings/owners, receipts/outbox or any cursor. Original F2 digest domains stay2.
A fresh device or raw3 applied row cannot substitute for retained F2 application.
J's ordinary interval replay still requires retained protocol=page protocol;
F2→page3 remains a conflicting_record there. The join can inspect an older exact
item after later pull advancement without claiming to replay that interval.
No endpoint, fetch, transport activation or server reader-gate bypass is added.

## Actual consumer matrix

All production paths below are under frontend/src/platform/web.

| Consumer | Implemented handling / barrier |
|---|---|
| resolutionRecords.ts | Strict three-tuple validation and exact Proof1 reference routing; no permissive protocol3 decoder fallback. Shared explicit new-root rejection helper. |
| resolutionPlanner.ts / actual apply runtime | Authenticated codec in private plan, strict Legacy source admission, raw3 clone reservations, unchanged hash preimages/atomic CAS, real raw3 outcome and read-only reconcile. No production resolutionApply.ts exists. |
| localAuthority.ts protected F hook | Validator chosen from private authenticated codec; no caller-created source authority. Other local writer restrictions remain. |
| resolutionAuthentication.ts core | Raw3 original AEAD/Legacy decode, null wrapper and Legacy source_after authentication; explicit Resolution/inbox protocol equality. Full parent/dependency/evidence checks remain. |
| resolutionDag.ts | Unchanged algorithm; strict leaves admit new tuple. Event/revision/bootstrap/role/clone uniqueness remains structural only. |
| syncDurability.ts | Unchanged actual raw3 receive preserves protocol/bytes. Old generic applied readers stay strict. |
| v10Transport.ts J | New exact F2 join with full historical/current-source auth and final snapshot CAS; raw3 same-protocol replay uses accepted original interval/index checks. No writes or certificates. |
| resolutionHistorical.ts | Root decoding follows authenticated codec. Explicit Legacy3-root guard at authenticateContinuationHistory keeps H/G/Q/O/mixed consumers bounded. Existing F2 historical descendants remain join-readable. |
| resolutionContinuation.ts H | Shared guarded historical entry rejects new roots before preparation, source write or successful history result; existing F2/Content3 paths unchanged. |
| resolutionPrefix.ts G / Q | Same guard before certificate/commit; raw3 gains no proven-prefix authority. |
| v10Recovery.ts K | Explicit root guard before prefix/owner routing. Fresh raw3 still classifies unsupported; dormant F is not automatically selected. |
| v10MixedRecovery.ts / post-F routing | Guarded full historical entry rejects raw3 before owner/routing/prefix mutation; preserved .11 negative boundary. |
| v10OrdinaryApply.ts O, mixedSourceValidation.ts | Shared guard rejects new root before ordinary/mixed source authority. Additional/pending Resolution remains unsupported. |
| Specialized terminal/handoff Resolution authentication | Explicit guard in both wrappers, independently of whether Content dependencies are present. |
| historicalMetadataDependency.ts | Guard in common complete-inventory verifier covers direct diagnostic, terminal and private handoff entry points. |
| historicalContentAuthentication.ts / privateMetadataPrefix.ts | Their existing guarded historical/Metadata composition rejects raw3; no new private/create authority inherited. There is no production privateMetadataAuthentication.ts. |
| provenPrefix.ts / ACK / upload | Unchanged old validators and gates reject future Resolution leaves; neither new result is an ACK or outbound authorization. |
| noteReaderReadiness.ts | Unchanged ready=false/declarationAllowed=false/writerAuthorized=false. |
| persistence.ts / indexedDbV9Migration.ts | Unchanged physical DB10 and keyless strict migration. Opening10 grants no record/owner authority; invalid future leaves in9 still reject atomically. |
| Restart / old reader | Fresh auth/key/profile/device and complete disk reauthentication. Pinned old v10 rejects semantically despite opening DB10; no false VersionError claim. |

The main shared barriers were added before extending the dormant F producer.
No additional H/G/Q/K/O/private route is accepted for the new root. Partial
upgrade retains encrypted data and fails before protected consumption; rollback
requires restoring a compatible bundle, never deleting data or relabeling as2.

## Local acceptance and actual old bundle

All selected local requirements passed. Current coverage spans **1,186 cases
across24 distinct spec files**, accepted through the runs below; overlapping
focused reruns are not added together:

| Actual command group | Result | Wall time |
|---|---|---|
| resolutionPlanner, resolutionReaders, resolutionApply, resolutionDag, v10Transport, legacyV3Resolution, localAuthority (`--maxWorkers=2`) | 356 PASS /7 files at that revision | 47.07s |
| H/G/Q/K/O/mixed/private and post-F regressions: resolutionContinuation, resolutionPrefix, resolutionMixedContinuation, resolutionMixedPrefix, v10Recovery, v10MixedRecovery, v10OrdinaryApply, historicalMetadataDependency, historicalContentAuthentication, privateMetadataAuthentication, privateMetadataHandoff, privateMetadataPrefix, postFMetadataBoundary, postFMetadataRecovery (`--maxWorkers=2`) | 699 PASS /14 files | 696.73s |
| legacyV3Resolution + noteReaderReadiness + indexedDbV9Migration + historicalPrefixQualification (`--maxWorkers=2`) | 194 PASS /4 files at that revision | 155.48s |
| Final v10Transport including genuine post-H F2 join (`--maxWorkers=1`) | 63 PASS /1 file | 35.04s |
| Final legacyV3Resolution including non-null wrapper/public rehash and actual additional receive (`--maxWorkers=1`) | 70 PASS /1 file | 8.62s |
| Native raw3 apply script, final old-reader/source-edit/J boundaries | 4 strategies;4 commits,12 fault rollbacks,9 new-bundle full process reopens,4 old-profile copies ×12 rejected paths,8 zero-write F reconciles plus J replay,1 lost completion,1 pre-commit process stop | 7.33s |
| Native normal F2/Content3 script | 8 commits,24 fault rollbacks,8 process reopens,16 zero-write F reconciles;4 independent F2 joins | 8.95s |
| Existing browser-persistence acceptance | PASS, including all15 native v9→v10 migration cohorts and schema10 reopen; page errors0 | 204.75s |
| CI-style pinned-baseline archive/build + raw3 script | PASS, original old bundle built from pinned source | old build0.258s, browser14.00s |
| Typecheck, production Vite build, production acceptance harness build | PASS | production Vite2.73s; no separate typecheck wall time captured |

All reported Vitest runs have failures0/skips0. Earlier focused runs of174/52/66
cases also passed during development; they are superseded by the current coverage
above. Initial typecheck errors in test annotations and the join descriptor's
broad TypeScript API type were corrected; final checks pass. No existing test was
removed, skipped, weakened or assigned a larger timeout.
Acceptance uses actual encrypted producers and real owners, not hand-built
positive applied proofs. The focused Legacy3 file covers all four strategies,
mixed Legacy/Content parents, original wire/codec separation, private source
restrictions, pending raw3 clone reservations, exact F2 join and missing-proof/
fresh-device rejection, source/bootstrap/publication corruption, rehashed evidence,
duplicates, lifecycle/CAS and all deferred consumer barriers. Existing F2/Content3
tests retain their original behavior. A separate J regression joins F2 after
genuine H source evolution/pull advancement and rejects corrupt descendants.

The existing browser-resolution-apply-acceptance script is parameterized with
`--legacy-v3`; its normal mode retains F2/Content3 coverage and adds F2 joins.
Both modes use real persistent Chromium directories/native IndexedDB. They close
the entire browser process, reopen the same profile, establish fresh real
auth/binding/key/device runtimes and require byte-identical complete twelve-store
snapshots. Native reconcile/J replay/F2 joins install a write trap and perform
zero writes. Concurrent tabs remain writer_busy. Current identity mutation
invalidates prepared raw3 and Content3 tokens before any commit.

For raw3 keep_both, twelve native fault paths cover all eight write positions,
transaction abort and in-flight key/logout/profile invalidation. Losing a
prepared token by closing the process before commit preserves the pre-commit
snapshot. A harness-only wrapper rejects the completion result **after native
commit**; fresh reconcile finds exactly one complete result. This is an injected
lost signal and native transaction abort, not a claim of testing OS power loss.

Old-reader acceptance pins baseline
`2320549e1c2e4ef3cc87bd91ee109c8e9bb7ebc6`. Its unmodified source is archived into
a disposable directory, built against unchanged installed dependencies, and
served at the same origin into a **copy of a closed new-data profile**. The
script verifies the baseline marker and absence of the new join method. Old and
new bundles never write the same open profile concurrently.

All four raw3 strategies exercise twelve old paths: F reconcile/prepare, J scan,
H history, G/Q prepare, K/mixed K, O apply, old proven-prefix, direct local source
edit, and J replay. Runtime TypeError/ReferenceError cannot count as rejection.
The complete database must remain byte-identical. Reopening each old-tested copy
with the new bundle authenticates/reconciles successfully without reset,
downgrade, proof rewrite or data deletion. Old v10 opens physical10 and rejects
the semantic tuple; existing old-physical-version barriers remain unchanged.

Existing native persistence acceptance additionally verifies genuine v9→v10
cohorts, failed/aborted upgrade preservation and schema10 disk reopen. Its prior
fixture-only API checks remain separate from the new Resolution harness, whose
only API activity is disposable device registration; no live backend or user
data is used by either run.

## CI budget, publication and next slice

Measured accepted Cloud run39850013638: Frontend admin **22m59s**,
complete-project **39m00s**. The old Frontend atomic-apply step was12s and harness
build1s. The connector's compact job summary omitted timestamps; exact historical
job/step timestamps were read through the GitHub API. This is a historical
capacity review, not polling the implementation's Actions.

Keep complete-project unchanged. Frontend admin receives two narrow steps:
build the pinned old bundle and run the existing apply script's raw3 mode; run
the isolated Legacy3 spec with maxWorkers1. Its existing F/J script/spec coverage
is extended in place; no original step/test is disabled or moved. The new CI
baseline builder was reproduced locally using git archive, a temporary source
directory and the same Vite command; cleanup never follows the node_modules
symlink. All six mandatory jobs and 40-minute limits remain.

Observed local new browser time is at most14s in the recorded runs; focused
incremental spec time is recorded below. Allow a conservative **two-minute CI
increment plus five-minute reserve**: 22m59s+2m+5m=29m59s <40m. This is an estimate
based on measured historical job headroom and local incremental work, not a
measurement of the future implementation run. Independent CI must confirm it;
any future budget failure requires an explicit partition, not coverage removal.

Actual changed paths select Cloud, hence expected six mandatory jobs on the
published SHA. They do not match SQLite's enumerated paths. No Cloud/SQLite
equivalence is claimed from local tests and Actions will not be polled/waited.
Remote acceptance requires independent Cloud SUCCESS6/6 on the implementation SHA.

Next proposed slice, after independent T acceptance and separate authorization:
**C21.2.08U — bounded Legacy3 H historical source and continuation acceptance**.
Accept original/retained peer ordinary child2/child3 history and restart/source
checks; retain explicit G/Q/K/O/private barriers at their own entry points before
widening H's shared reader. Later prefix/recovery/mixed acceptance remains
separate. Full Note reader/capability and complete account replay remain open;
Metadata no-head create is still blocked and is not U.

Final publication checks: whitespace validation, exact18-file scope, preserved
prior checkpoint text outside the three current gate rows, unchanged original
workflow steps/job coverage/timeouts, workflow/embedded Python syntax and actual
Cloud/SQLite path selection. Protected engine/game_data bytecode SHA-256 values
remain those in S. All disposable Chromium profiles and old/new acceptance
bundles are removed after use; the task preview is stopped and main node_modules
is preserved. No backend, physical migration, crypto implementation, dependency,
Rust/Python production, readiness predicate, VPS or landing change is included.
The docs and checkpoint state LOCAL COMPLETE only; publication/remote SHA is
reported in the task result and independent CI is still required.

C21/C21.2 IN PROGRESS; .08 NOT CLOSED; .08R IMPLEMENTATION STOP (historical);
.08S DESIGN COMPLETE; .11 PARTIALLY RESOLVED; C21.1.06 NOT LOCAL COMPLETE;
.18 REMOTELY ACCEPTED, Cloud39850013638 SUCCESS6/6;
.19/.21/.23 AUDIT COMPLETE; .20/.22 IMPLEMENTATION STOP.
Web89.36%, ready=false, declarationAllowed=false, writerAuthorized=false,
registration CLOSED, PUBLIC RELEASE BLOCKED. VPS/landing, mandatory CI/CD policy,
C22/C23/PF6.0/RC and security/release gates remain mandatory.
