# C21.2.12 — Historical Metadata tombstone and Content dependencies

**DESIGN ONLY / PROPOSED CONTRACT — no runtime authorization or routing.**
Baseline `65cd497542f51b7b6263e34ed2da77b4c1d895d5`, branch `6.0`.
C21.2.11 remains **IMPLEMENTATION STOP**, not functionally complete. Cloud run
`39672625896` has no independently supplied all-six-success confirmation in this
task. It is not recorded as remotely accepted; Actions are not queried or awaited.

## Audited cause and evidence

Paths below resolve against the actual baseline source, not future pseudocode.

| Source | Existing contract / evidence |
|---|---|
| [resolutionAuthentication.ts](../../frontend/src/platform/web/resolutionAuthentication.ts), `dependencies` | Retained Content F checks its original Metadata reference and the CURRENT qualified nondelete tip. The Resolution identity, including dependency digest, is bound into its existing AEAD evidence; original owner snapshots are not stored by that digest. |
| [resolutionHistorical.ts](../../frontend/src/platform/web/resolutionHistorical.ts), `authenticateContinuationHistory` | Reopens retained candidates and calls fresh `prepareNotePrerequisite` for peer Content candidates, including already applied outcomes. |
| [noteTransportPrerequisite.ts](../../frontend/src/platform/web/noteTransportPrerequisite.ts), `prepareNotePrerequisite` | Opens original Content, joins bootstrap/Metadata and Stage proofs, requires a current nondelete Metadata tip, and mints a private live certificate. The dependency digest includes the then-current owners/bindings; it is not their recoverable snapshot. |
| [metadataPrefixProof.ts](../../frontend/src/platform/web/metadataPrefixProof.ts) | Reproduces each Metadata proof from retained wire, descriptor digest and AEAD; qualifies a peer clean create/update/delete chain with increasing server sequence, revision and generation. Delete is itself qualifying Metadata evidence. |
| [importedMetadataApply.ts](../../frontend/src/platform/web/importedMetadataApply.ts), `transition` / commit | Real imported owner enforces exact reference, bootstrap, parent/tip, revision, generation and atomic head/inbox writes. It does not modify Note source. It does not itself impose a general terminal-delete/no-reactivation rule. |
| [contentNoteProof.ts](../../frontend/src/platform/web/contentNoteProof.ts), [noteHistory.ts](../../frontend/src/platform/web/noteHistory.ts), [resolutionRecords.ts](../../frontend/src/platform/web/resolutionRecords.ts) | Existing candidate/transport/outcome, original wire, projection and Resolution evidence joins must remain; a matching digest or `applied` flag alone is insufficient. |
| [resolutionPrefix.ts](../../frontend/src/platform/web/resolutionPrefix.ts), [v10MixedRecovery.ts](../../frontend/src/platform/web/v10MixedRecovery.ts) | Full v10 historical/source verification precedes family qualification or routing. Q local-prefix certificates and diagnostics never grant owner/ACK/readiness authority. |
| [postFMetadataBoundary.spec.ts](../../frontend/src/platform/web/postFMetadataBoundary.spec.ts) | Genuine F/H/O followed by a real Metadata ID1 update remains valid; a real owner tombstone makes Q/K reject. A wholly Legacy control still qualifies deletion. No positive applied proofs are manufactured. |

The .11 counterexamples distinguish a valid Metadata outcome from the ability to
authenticate the complete account after that outcome. Full-account CAS cannot
fix the reuse of a live-operation prerequisite as a historical reader check.

## Three separate decisions

1. **Historical authentication:** reproduce a durable accepted outcome from its
   own original wire, exact persisted proofs and dependency history. It may remain
   valid after a later Metadata tombstone. It never changes source or creates an
   applied outcome for a received event.
2. **Current-source authority:** independently verify the complete F/H or mixed
   source witness, exact Note projections, membership, source revisions and causal
   DAG. Historical dependency success alone cannot establish this authority.
3. **New apply authorization:** the real accepted owner must check current active
   dependencies, lifecycle and full pre/post source/owner evidence, then commit
   under its private authorization and exact transaction CAS. A historical result
   cannot be consumed as that authorization.

This separation is a proposed semantic contract. Runtime live checks stay intact
until independently reviewed implementation; no generic `historical=true` switch
may turn a live owner certificate into a less restrictive commit token.

## Bounded historical rule

Let `q(E)` be the genuine retained server sequence of a Content event, `M` its
exact `metadata_event_id`, and `D` a later Metadata delete in the same project and
bootstrap. Sequence comes from the existing exact inbox key/descriptor/proof and
retained transport joins. It orders server publication, not client creation or
local application time, and is not a newly introduced server signature.

For a **previously persisted accepted outcome** to pass the proposed historical
Metadata check after deletion, require all of the following:

- Original Content AEAD/frame/codec, inner/outer event identity, account, project,
  bootstrap, device, operation, revision, timestamp binding and existing immutable
  outcome joins authenticate normally. Codec8 ordinary and Content Resolution
  remain distinct. Reopen every relevant Metadata AEAD and reproduce exact
  Metadata proofs; hashes or owner-head shape alone do not qualify.
- Metadata has one complete retained peer coverless chain from genuine create:
  initial revision/generation1, no parents; each subsequent parent is the previous
  tip, revision is parent+1, generation is strictly greater (not necessarily +1),
  and server sequence strictly increases. Every proof joins its own applied inbox
  row and original wire. The current head must describe exactly that chain.
- `q(M) < q(E) < q(D)`. `M` is nondelete and lies on that same chain. The last
  Metadata ancestor published before `q(E)` is also nondelete and descends from
  `M` (or is `M`). Thus the exact reference can be older than that historical tip;
  it cannot belong to a foreign branch/bootstrap or jump over a prior deletion.
- Enumerate every retained same-project Metadata descriptor through `q(E)`.
  Received/unqualified events, missing ancestors, an ignored competing branch or
  an earlier unproven delete prevent claiming a complete active interval. Do not
  select just the clean owner-head subset and discard that contrary evidence.
  Later pending rows stay visible as their own full-account/prefix barriers;
  their existence does not erase an otherwise proved earlier outcome.
- `D` is a genuine coverless delete with the exact retained parent, revision,
  generation, descriptor and tombstone. This first bounded cohort has a terminal
  delete: later reactivation, a second distinct delete, new genesis or Metadata
  resolution is deferred. Exact replay of the same `D` is allowed. This terminal
  rule is a design fence, not a claim that today's owner already enforces it.
- The original owner-specific Content/F proof, parents, conflict closure or
  preservation, source outcome and projection remain authentic. An accepted
  conflict-only candidate stays conflict-only with NULL projection; historical
  Metadata coverage cannot manufacture an applied Note or close a fork.
- The complete bounded account inventory is retained and authenticated. Missing
  sequences/proofs, duplicates, unknown generations, broken source history and
  foreign/local unsupported material remain explicit barriers. Computing a
  historical chain fold is not permission to filter the account into v9 data.

This proves **sequence-bounded historical admissibility**, not the exact active
owner snapshot or wall-clock time at the original local commit. The immutable
dependency digest stays unchanged and is checked in its existing proof/AEAD joins;
do not pretend hashing today's owners reproduces it or guess a past snapshot from
it. A design that requires proving the original full commit-time owner inventory
or local apply-before-delete timing has insufficient evidence and must STOP.

## Metadata deletion and live operations

A Metadata owner delete is structurally valid only through its real imported,
captured, active binding, original encrypted payload, exact references, clean
current parent/tip, revision/generation and no incompatible local Metadata outbox
or own-event shortcut. A non-null cover dependency remains unsupported. Metadata
tombstone, remote bootstrap state and canonical local project deletion are
different facts: do not alter binding, `localProjects`, Notes, membership or
`source_revision` to simulate project deletion.

A future mixed router may commit `D` only if its complete pre-state and predicted
post-state satisfy the separately accepted historical and source rules, with the
same full-ten-store atomic owner guard required by the [.10 contract](C21_POST_F_STRUCTURAL_ROUTING_CONTRACT.md).
A valid individual delete is not sufficient when other account evidence prevents
that post-state from being proved. Pending events and unresolved barriers remain
visible, not converted or removed to let the delete through.

For a **new first apply**, current Metadata must still be authenticated, active,
single-tipped, nondelete and compatible with the exact dependency, binding and
owner snapshot. The proposed bounded future path must also establish `q(M) < q(E)`
and its nondeleted historical interval; today's live checks alone do not prove
that cross-family fence. Old covered ancestors can remain legitimate under the accepted
live contract; an old reference is not inherently stale. A changed prepared
snapshot/tip, foreign or missing ancestor, delete, never-proven event, unresolved
fork or unsupported lifecycle is stale/ineligible. After a current tombstone,
no older reference can authorize a new Content create/update/delete or Content
Resolution, even if its server sequence precedes `D`. Retained bytes may be
decoded for diagnosis without granting first apply.

Do not use Legacy transport as a bypass for the project's deleted Metadata.
Pure Legacy historical outcomes retain their actual contracts and acquire no
invented Content dependencies; any future routing permission for new Legacy
source changes in a tombstoned project must be separately specified and stays
blocked in this slice. Local authorship/own echo and new Resolution generations
remain unsupported regardless of Metadata status.

## Decision matrix

“Historical valid” below means the Metadata component passes the above proposed
rule, conditional on all other original family/source checks. It is not a current
runtime result and never alone qualifies an inbox sequence or grants new apply.

| Case | Historical / retained evidence | New first apply / routing |
|---|---|---|
| Genuine applied Content `M < E < D`, current terminal tombstone | Historical valid after full proof reproduction; keep actual projection/outcome | No duplicate source write; exact replay validates existing outcome only |
| Content received with `E < D`, still received when `D` is already applied | Authenticated ciphertext/reference may be readable; no accepted outcome to grandfather | Block first apply under current delete; keep received barrier. No timestamp or claimed earlier receipt promotes it |
| Earlier `E` received and later `D` only received, current Metadata still active | Evaluate earliest `E` through normal live owner; missing dependencies remain barriers | Apply eligible `E` before `D`, reload, then consider `D`; never skip earlier `E` to apply delete |
| Claimed created-after-delete Content referring to old `M`, or `E >= D` | Creation time is unproven; an applied out-of-order outcome is retained but outside the historical cohort | Block under delete. Already applied evidence at/after `D` does not earn historical qualification merely from its digest |
| Genuine Metadata update then delete | Retain all versions, references, revisions/generations and exact tombstone; older same-chain reference may still cover earlier Content | Delete requires full account post-state/CAS; update-after-delete/reactivation is deferred |
| Content F before `D` and its earlier accepted parents | Preserve Resolution AEAD, group closure, parent publications, Head2 and original/retained roles; historical Metadata rule applies to each actual Content dependency | No new F generation or permission to author/apply a new Resolution |
| Legacy F with earlier Content O/H outcomes | Legacy F keeps Legacy semantics; each retained Content O/H outcome independently proves `M < E < D` | O/H fresh source changes still need live prerequisites; no Head1/Head2 substitution |
| Existing resolved or unresolved Note forks | Reproduce genuine closure/preservation; NULL projections stay NULL; unsupported groups remain barriers | No new conflict resolution. G/Q cannot cross an unresolved incoming fork |
| Deleted Metadata with pending Stage/StageOrder | Keep ciphertext, dependency references and all prior heads/history; no cascade or synthetic tombstones | Block first apply; Stage/StageOrder routes and their delete operations stay OFF |
| Missing/corrupt Metadata wire, proof, ancestor, sequence or bootstrap | Cannot establish historical admissibility; preserve data and fail closed | No owner, prefix, ACK or repair grant |
| Restart / exact replay after valid `D` | Reopen original evidence and reconstruct the same historical result without writes; existing outcome stays immutable | New transaction/session must prepare again; no persisted historical permit or automatic retry |

## Timing, evidence sufficiency and unresolved cases

Existing IDB10 evidence is sufficient to implement a **bounded read-only**
resolver for the clean `M < E < D` cohort: original Content/Metadata ciphertext,
explicit dependency IDs, immutable references/server sequences, complete Metadata
history and genuine persisted outcomes are available. No store, migration,
crypto/wire field or new durable witness is justified for that resolver. This is
an evidence audit, not implementation or functional acceptance.

The following are explicitly unresolved/deferred; preserve their existing bytes
and stop qualification without inventing a permissive default:

- Metadata dependency published after Content (`q(M) >= q(E)`), missing intervals,
  or already applied Content published after a delete. Current live checks do not
  establish the proposed strict cross-family sequence fence. Existing proofs do
  not make every such history admissible; do not silently reinterpret it.
- Whether a received event was created or locally applied before deletion in
  wall-clock time; sequence, Note `source_revision`, timestamps and an applied flag
  do not establish that fact. Support needing this fact requires a separately
  reviewed evidence contract; no migration or proof is fabricated here.
- A Metadata reactivation/resolution, multiple branches/generations, local/own
  Metadata history, cold missing history, unsupported cover material or source
  authorship. Current head alone cannot prove a prior active interval.
- Stage-scoped Content/F and already retained Stage/StageOrder after deletion,
  until their own complete historical dependency coverage is reviewed below.

Compatibility must be explicit. This narrow rule does not change H's accepted
F/H-only cross-role source commit ordering, nor impose server order on unrelated
Note source revisions. Metadata sequence ancestry is a separate proposed fence.
If a genuine formerly accepted history is outside it, retain and report that
cohort as unresolved; never rewrite old proofs, downgrade to v9, silently fall
back after failure, or claim universal backward compatibility.

## Stage, StageOrder, full account and transaction consequences

[stageApply.ts](../../frontend/src/platform/web/stageApply.ts) already distinguishes
an `active` Metadata check, but forced Stage history verification passes active
requirements again. [stageOrderApply.ts](../../frontend/src/platform/web/stageOrderApply.ts)
uses `fresh`/`replayHistory` and cursor position to choose dependency checks. Those
booleans are not an accepted historical tombstone proof. Do not force them false
or move `proven_prefix` to bypass verification.

An eventual historical Stage reader must authenticate its own exact Metadata
ancestor/active interval at the Stage event sequence, complete Stage history/tips
and tombstones. Historical StageOrder additionally needs each original Stage
reference and causal reachability/exact membership coverage at its own event,
not today's head set alone. Review whether its existing retained evidence proves
that set; mark unresolved when it cannot. Stage/StageOrder deletion and missing
child-manifest semantics remain unsupported. Until separate acceptance, Stage
dependencies can still block full-account qualification; a project-scoped
Metadata/Content success is not whole-account success in such an inventory.

Future F/H/O integration must separate retained-history readers from current
apply prerequisites at every call site. Q may use the historical component to
authenticate genuine existing outcomes, then still verify complete source and
each family's own qualification. It advances only the contiguous fully proven
prefix. Received, fork-only, unsupported or incomplete sequences remain barriers;
the cursor itself is not an exemption from historical validation. No ACK follows.
The delete sequence may qualify only from its own genuine Metadata proof, after
every preceding sequence qualifies; it contributes no Note-source authority.

K must always authenticate all ten stores, select from evidence, and process the
earliest pending event. Invalid later material may block the entire pass; it
cannot be hidden. A later well-formed but live-ineligible received event remains
received, not historical applied evidence. Applying Metadata must use the real
owner's private plan and exact complete pre/post CAS in one transaction. Earlier
committed genuine events survive a later pass failure; no pass-wide repair occurs.
Concurrent tabs/source/dependency/cursor changes require fresh preparation;
auth/key/profile/device revocation aborts; rollback retains the original state.
After restart or a prefix-commit abort, reauthenticate actual durable outcomes
before a fresh local prefix commit. No diagnostic becomes write permission.

## Proposed acceptance and numerical implementation sequence

Use genuine F/H/O and Metadata owners, original encrypted events, both F protocols,
all four strategies and ID0/ID1 where applicable. Keep .11 counterexamples as
current-runtime negative evidence until explicitly reviewed historical integration;
do not simply flip them to success or weaken their source/immutability assertions.

| Future evidence | Required assertion |
|---|---|
| Real accepted project-scoped Content/F then update and terminal delete | Read-only resolver proves exact `M < E < D`; accepted tombstone, original wire/outcomes and source remain byte-identical; no commit certificate |
| Legacy F plus genuine earlier Content O/original/retained H | Each Content dependency independently qualifies; Legacy semantics and role/Head2 ownership unchanged |
| Genuine pending Content on either side of delete; false client timestamps | No first apply after current delete; earlier pending event is never skipped; creation-time claims confer nothing |
| Missing/forged/digest-only Metadata proof, foreign bootstrap, duplicate sequence, dependency at/after `E`, delete before `E` | Explicit barrier, no manufactured historical grant, no deletion of retained evidence |
| Real forks, unknown generations, local/own outbox, Stage/StageOrder/cover dependencies | Existing barriers remain; historical success never creates a source projection, child manifest or capability |
| Exact replay, disk reopen, competing tabs, stale pre-state, revocation and write/prefix abort | Fresh authentication/CAS and real native rollback; no duplicated source revision, repair, ACK or readiness |

Proposed **C21.2.13 — isolated read-only historical Metadata dependency verifier**:
clean received-peer coverless chain and project-scoped retained Content/F wire,
sequence-bounded terminal-delete cohort only. Authenticate the actual Metadata
chain and Content dependency binding; report only that component's result, not
full Resolution/source acceptance. No owner/H/O/G/K integration, public token,
persisted witness, migration or runtime live-check changes. Missing evidence or
an unprovable lifecycle must STOP. Independent contract review precedes coding.

After independent acceptance, propose separate numeric slices for historical
F/Content reader integration with unchanged fresh live checks and full source
guards, then the ten-store Metadata owner adapter and K routing. Stage/StageOrder
historical contracts must be reviewed independently before claiming their coverage.
No slice is silently implemented or renumbered by this document.

C21/C21.2 remain IN PROGRESS; C21.2.08 NOT CLOSED; Web89.36%, ready=false.
Complete family readers, own/local authority, further Resolution lifecycle,
orphan/cold recovery, Content sealing/upload/receipt/self echo, account/server
declaration and ACK gates, production composition and multi-device acceptance
remain prerequisites. VPS hardening/security audit, owner stabilization, closed
registration and PUBLIC RELEASE BLOCKED remain mandatory; this contract opens none.

## C21.2.13 — isolated component verifier / local implementation

Baseline `b084b590e4a5a3fe7c5465b161b8b0da57d232a8`. C21.2.12 is DESIGN COMPLETE,
docs-only; its paths did not call for Cloud/SQLite. C21.2.11 stays IMPLEMENTATION
STOP. The last supplied .11 status is 5/6 Cloud jobs SUCCESS and Frontend running;
there is no new independent all-six confirmation, and Actions were not queried.

[historicalMetadataDependency.ts](../../frontend/src/platform/web/historicalMetadataDependency.ts)
adds a frozen inspect-only binding, imported by the focused tests and isolated
acceptance harness. Normal persistence, F/H/O/G/Q/K, current-tip prerequisites,
writers and startup do not import or call it. No plan/certificate is stored, no
writer hook is added, and no schema/wire/crypto/proof format changes.

### Implemented evidence and conservative limits

The reader loads the complete original ten-store v10 inventory with the accepted
16384 rows/store and 32 MiB aggregate limits. It checks scope, sequence continuity,
event collisions, known full DAG formats, one F root, publication/outcome joins,
canonical current source envelopes and member identities. Candidate AEAD and
projection verification use the accepted pure reader; existing immutable Content
outcome/transport and Legacy proof helpers reproduce their actual persisted joins.
Its module-private F evidence reader opens the original wire and Resolution AEAD
evidence, checks identity/payload/frame/group/parent/transition/output proof joins
and historical source snapshots. This is not a replacement for accepted full
F/H historical/current-source admission or a new Resolution apply owner.

Every Metadata head's original records are independently reopened; proofs are
reproduced from actual wire, not minted from a matching digest. Exact peer imported
lineage, create/update/delete chain, parent/tip, revision+1, increasing generation
and sequence are checked. All same-project Metadata rows must belong to that
authenticated chain; contrary received/unqualified events cannot be hidden. The
root project must have a terminal delete and each retained Content outcome must
prove its exact nondelete dependency and `M < E < D`. Decrypted retained candidate
material and individual historical JSON are additionally bounded at 16 MiB;
ordinary canonical decoder/frame limits remain intact. Buffers are cleared; JavaScript
plaintext/string erasure is not claimed.

The scope is deliberately conservative: one peer F project and project-scoped
Content, import_remote/captured/active lineage, no local intents/outbox/receipts,
own authorship, further Resolution generations or open groups. Any Stage/StageOrder
rows/heads, including unrelated account structural material, reject this bounded
inspection. All Metadata owners are checked; reactivation/repeated delete or an
unproven head elsewhere cannot be filtered out for a positive result. Unsupported
families, missing/corrupt proof or interval, foreign scope, failed AEAD and unknown
formats fail closed with fixed sanitized reasons. This is a narrower cohort than
all accepted F/H/G histories; it changes none of their existing behavior.

The result explicitly reports `fullHistoryAuthenticated:false`,
`sourceAuthorized:false`, `firstApplyAllowed:false`, `commitAuthorized:false`,
`ackAuthorized:false`, `ready:false`. Only `historicalMetadataAdmissible` describes
the authenticated dependency component for a genuinely retained Content outcome.
Legacy F has `not_content` rather than an invented Content dependency. A received
Content target, whether before or after the tombstone sequence, has `not_applied`;
it never becomes an applied outcome. Sequence does not prove client creation or
local commit time, nor reproduce a former complete owner snapshot.

Before returning either result, the reader rechecks the complete native snapshot
and real auth/key/profile/device context. Concurrent owner/source/cursor changes
throw stale_source; revocation rejects. A diagnostic cannot be reused as an O/H/Q
commit token. The only transactions scheduled by the verifier are readonly; no
nonce, HTTP, durable witness, inbox/source/head/cursor mutation is performed.

### Genuine validation and CI partition

The focused suite uses actual accepted F/H/O and Metadata owners: both F protocols,
four strategies, Content F ID0/ID1, independent Content ID1 and original/retained H
ID0/ID1. Positive dependency components coexist with unchanged .11 Q/K rejection.
Negative evidence includes pending Content on either side of deletion, genuine
late Metadata accepted by the live owner, actual unresolved H fork, Stage cohort,
real repeated delete/reactivation, contrary received Metadata, corruption,
collisions, missing/digest-only evidence, foreign scope, lifecycle revocation and
a real Metadata owner racing the final reload. Final counts are in the checkpoint.

The new `--historical-metadata` acceptance mode reuses the existing genuine native
F seed in eight disposable profiles. It is separate from unchanged L/N/O/P/Q/K
acceptance commands. Original O/H outcomes, Metadata update and delete are created
by the actual owners, then inspection is repeated with readwrite transactions,
getRandomValues and fetch trapped. Across disk reopen, all twelve stores remain
byte-identical and diagnostics replay exactly. Four Legacy F checks report no
Content dependency; 22 positive Content target checks per phase cover O/H/F roles.
Eight competing tabs are excluded; eight key revocations reject; eight actual
external Metadata-owner races invalidate the final snapshot. Those known fixture
actor writes are separate from the verifier's zero writes. Page errors and
unauthorized HTTP are zero. No J transport replay support after deletion is claimed.

Capacity review uses the already recorded accepted .09 complete-project job
(18m45.28s of 40 minutes); the pending .11 run is not polled. New isolated tests
and the separate native mode run once in that existing mandatory job, after npm
installation, with conditional pinned Chromium/harness/preview setup. All old
test commands and six mandatory jobs remain, Frontend admin gains no workload and
keeps 40 minutes. Existing per-test 5000ms limits, no retries/skips remain. Remote
CI is pending; local measurements do not guarantee future runner duration.

### C21.2.14 proposal and remaining boundary

Only after independent .13 acceptance, propose **C21.2.14 — read-only historical
Content/F dependency integration**. Review private sharing of the authenticated
dependency semantics, while every original payload/proof/source/causal check stays
independent. Do not consume inspect diagnostics as authority or relax fresh live
owner prerequisites. This proposal does not authorize applying Metadata, integrating
K dispatch, Stage/StageOrder, or changing ACK/readiness. Unsupported cohorts must
retain evidence and explicit barriers. No .14 implementation is included.

C21.2.13 is LOCAL COMPLETE / REMOTE CI PENDING for this read-only component only;
.11 stays IMPLEMENTATION STOP and .08 NOT CLOSED. Web89.36%, ready=false,
closed registration and every VPS/security/public-release gate remain unchanged.

## C21.2.14 — isolated historical Content/F authentication

**LOCAL IMPLEMENTATION / REMOTE CI PENDING.** This appendix supersedes only the
proposal/status for the new slice, not the historical .12/.13 records above.
C21.2.13 implementation04f4cf6 plus timeout repair/baseline
`a67d104f3aa1462c75d9f07669b307186bf4ed84` are independently **REMOTELY ACCEPTED**:
Cloud39747671030 SUCCESS, all6 mandatory jobs; completed run identity/jobs verified.

### Explicit reader, unchanged authorization

`BrowserHistoricalContentAuthentication.bind(...).inspect(scope,eventId)` is a
separate dormant read-only entrypoint. It loads all ten bounded durable account
stores (original32MiB/16384-row limits), reacquires real account/device/key/profile/
epoch context and compares the complete inventory again before returning. It
exposes a frozen inspect-only handle and frozen counts/diagnostics, never decrypted
material, an owner plan, prerequisite, source grant, prefix certificate or ACK grant.
`historicalAuthenticated/fullHistoryAuthenticated/currentSourceVerified` describe
this bounded historical cohort for an eligible retained target. All
sourceAuthorized/firstApplyAllowed/commitAuthorized/ackAuthorized/ready flags
remain false. Missing/received targets get no positive historical result; the
earliest received sequence stays visible and no event is applied or skipped.

The internal `authenticateTerminalMetadataInventory` returns **void**, not the
public .13 inspect result or a detached Boolean/certificate. It invokes the actual
unchanged module-private .13 verifier over the complete original snapshot. This
freshly authenticates every candidate, original F evidence and Metadata ancestor,
including exact AEAD/wire/proofs/bootstrap and `M < E < D`. An actual retained
Content outcome is required even for a Legacy F target; no Content dependency is
invented for Legacy F. Terminal delete, peer/imported/captured lineage, project
scope, coverless material, one F, no local/own material or unresolved fork and no
Stage/StageOrder remain the accepted bounded fences. The public .13 API/result
and all51 previous cases retain their semantics.

| Layer | Historical-only composition | Default callers remain |
|---|---|---|
| `resolutionAuthentication.ts` | `authenticateTerminalMetadataResolutions` uses the internal complete .13 validation for dependency admission; the original F authentication core independently checks original AEAD/frame/codec, payload/identity, parent/group/transition, source snapshots and immutable output proofs | `authenticateResolutionHistory` uses its unchanged live `dependencies`, including active Metadata tip and Stage checks |
| `resolutionHistorical.ts` | `authenticateTerminalMetadataContinuations` shares the original continuation core after that F pass; only genuine peer persisted Content applied/conflict outcomes are accepted, without minting a live prerequisite | `authenticateContinuationHistory` still calls the same live `prepareNotePrerequisite` for Content candidates |
| `mixedSourceValidation.ts` | `inspectTerminalMetadataSourceHistory` independently validates the current source after historical authentication. The same complete mixed revision/member/projection fold is used only when genuine independent post-F evidence selects it | N/O/P/Q source owners still call their original default entrypoints with original live F/H authentication |
| F/H-only source history | Evidence selects original `verifyContinuationSources` plus non-output projection checks; genuine historical cross-role source order is retained | No failed mixed verification can fall back to this route |
| `noteTransportPrerequisite.ts`, F planner, O/H writers, J replay, G/Q and K | **No integration** | Live prerequisites, private WeakMap grants, first apply/replay/publication, prefix commit and mixed dispatch remain unchanged |

Private shared cores accept no public historical flag or caller-provided exemption.
Only named read-only composition selects the bounded alternative internally. Their
historical maps are ordinary internal validation material, never owner certificates;
source checking is not skipped and is never inferred from Metadata success.
Complete current Note/project AEAD alone is insufficient: exact source revisions,
F-boundary membership, reconstructible prior applied baselines, genuine O/H
projections, Head2/role reachability, causal chains, retained tombstones and final
records must independently match. Tests deliberately change current source under
valid AEAD: .13 dependency admissibility still succeeds, .14 authentication rejects.
No past complete owner inventory or application timestamp is synthesized.

### Call-site audit and remaining barriers

Two live-prerequisite reuse points are relevant: F `dependencies` requires today's
qualified nondeleted Metadata tip; H `authenticateContinuationHistory` calls fresh
`prepareNotePrerequisite` for retained Content candidates. The latter mints live
prerequisite certificates and therefore is not weakened. O/H prepare/reconcile,
F planner predicted-state/replay, mixed source validation, J retained replay,
G/Q prefix and mixed K all retain those default readers. Ordinary Content prefix
and intent-rebase checks also keep their existing live prerequisite. No entrypoint
is substituted in those callers, and original .11 Q/K rejection stays negative.

The alternative supports Content F3 ID0/ID1 and Legacy F2 followed by genuine
Content O/H, all four F strategies, independent peer Content and original/retained
H descendants, clean Metadata update then terminal delete and exact read-only
replay. A genuine F/H-only cross-role apply order outside the mixed cohort is
separately tested. This is not general reader readiness or universal historical
compatibility. Active-tip histories continue through existing default readers;
unsupported additional generations, resurrection, local/own material, unrelated
source writers, Stage/StageOrder/cover material, missing ancestors/sequences,
digest-only evidence, altered ciphertext/proofs/source, repeated delete,
reactivation, competing Metadata and open forks reject without repair/fallback.

Received Content on either side of deletion stays received. Fresh O/H/F operations,
self-echo and new Resolution retain strict current dependencies. Historical
success cannot advance a cursor, authorize a writer, ACK, Note declaration or
registration, publish Content or activate a scheduler. All diagnostics are
sanitized; concurrent inventory/source/Metadata changes reject stale_source and
lifecycle revocation rejects. Retry requires an entirely fresh read. Existing
IDB10 stores/formats/migration, original wire, crypto and proofs are unchanged;
no migration or new durable evidence is needed for this bounded cohort.

### Validation, workload and next numeric slice

Use actual F/H/O/Metadata owners only. The new suite splits baseline and post-F
construction into separate meaningful5000ms hooks; each test body also retains
5000ms. It covers both protocols, all four strategies, ID0/ID1, historical replay,
pending-before/after deletion, forks, Stage, corrupted/foreign/missing evidence,
valid-AEAD source drift, Head2, competing Metadata/account snapshots, lifecycle
revocation, zero writes/nonces/HTTP and refusal to consume diagnostics as O/H/Q
commit authority, live transport/source prerequisite or ACK reader/ACK token. Public .13 inspect is trapped in a positive test to prove that
its diagnostic is never used as authentication. Original .11/.13 negatives remain.

Final focused verification:51 new cases plus108 original F-reader/N-witness cases
PASS; unchanged .13/.11 and F/H/G/K/L regressions348 PASS. Total507/10files, final
failed/skipped0. Typecheck/build PASS (existing Vite warnings); detailed timings
and protected/history/workflow checks are recorded in checkpoint.

Native `--historical-metadata --historical-content` extends the existing eight real
persistent F profiles instead of duplicating setup. All previous .13 assertions
remain; additional .14 F/Content targets and exact replay are checked under
readwrite/getRandomValues/fetch traps, before/after full process reopen. All12
stores remain byte-identical. Competing tabs are excluded. Two simultaneous
readers are invalidated by one genuine external Metadata-owner commit between
both first and second snapshots; key revocation rejects both readers. Known actor
writes are distinct from zero historical-reader writes. No J replay-after-delete
or G/Q prefix advancement is claimed. Counts/results are recorded in checkpoint.

Capacity was reviewed BEFORE extending CI: accepted complete-project job
39747671030 took27m32s/40; isolated135 tests took6m53s and native .13 took38s.
Frontend admin took21m40s/40 and receives no new workload. New unit cases run once
in the existing complete-project isolated command; one native mode adds checks to
the same profiles. All six job names, mandatory checks and time budgets remain;
no retries/skips or increased per-test/hook timeout. Runner capacity still needs
fresh independent all-six acceptance; Actions are not polled after publication.

Proposed **C21.2.15 — read-only historical prefix qualification**: separately review
and bound whole-account family/earliest-event qualification using this authenticated
historical reader plus independent source checks. No prefix commit certificate,
network ACK, Metadata owner adapter or K dispatch activation is implied; original
.11 STOP remains until its eventual atomic adapter is independently accepted.
Do not implement .15 here. Further Stage/cover/local/own/additional-generation
readers, full recovery, writer/upload/self-echo, production orchestration and all
security/release acceptance remain prerequisites for C21 closure.

C21.2.14 LOCAL COMPLETE is limited to the isolated read-only composition and requires
new independent Cloud6/6 success for REMOTELY ACCEPTED. C21.2.11 IMPLEMENTATION STOP,
C21.2.08 NOT CLOSED, C21/C21.2 IN PROGRESS, Web89.36%, ready=false, closed registration
and all VPS hardening/security/public-release gates remain unchanged.

## C21.2.15 — isolated read-only historical prefix qualification

**ISOLATED READ-ONLY PATH — no G/Q certificate, cursor commit or Metadata route.**
Baseline `4ef43f266e7edfb83939f5033880e273c0501889`, branch6.0. C21.2.14 is
independently **REMOTELY ACCEPTED** for its bounded reader only: Cloud39755485254
SUCCESS, all6 mandatory jobs, accepted run SHA independently matched. This appendix
supersedes that slice's pending status without rewriting any historical entries.

### Private evidence and supported family scope

`BrowserHistoricalPrefixQualification.bind(...).inspect(scope)` loads all ten real
bounded recovery stores under the accepted account/device/auth/key/profile/epoch
guards. It uses fresh internal F/H/Metadata and current-source authentication,
never the public .13/.14 inspect results, a detached Boolean, or Q prepare/calculate.
The .14 source composition is factored into a module-private function returning
its authenticated maps only inside `mixedSourceValidation.ts`; its existing
public diagnostic keeps the same counts and semantics. Default N/O/P/G/Q/K and
live first-apply paths remain unchanged.

The qualifier explicitly requires exactly one authenticated F. An ordinary-only
history, even with genuine Content and Metadata deletion, is outside this path.
No callback simply failing to encounter F, nor a successful diagnostic, can admit
that history. The complete terminal-delete scope from .13–14 stays: received-peer
project-scoped Content, actual imported/captured bootstrap, complete `M < E < D`
ancestry, coverless Metadata and authentic retained outcomes. Additional generations,
local/own source, outbox/receipt dependencies, unsupported families and open forks
are rejected, never filtered into an old-format account view.

| Counted family | Independent authenticated evidence required |
|---|---|
| `legacy` | Original peer candidate/wire and genuine `note_proven` applied proof/source projection; a preserved losing candidate needs its own conflict proof and actual resolved F group |
| `content` | Original Content AEAD/frame/codec, candidate, transport/outcome/dependency proofs and independent source checks, including the accepted historical Metadata interval; only the accepted peer C1 format |
| `resolution` | Original accepted F row/proof, encrypted payload/evidence, parents/group/transition, historical source snapshots, output identities and current role/Head2 checks; keep_both contributes **one** server sequence |
| `metadata` | Each sequence's genuine applied inbox proof equals its own complete authenticated owner-history entry, reproduced from original Metadata AEAD/wire; a terminal delete qualifies only itself |

Legacy/Content Note qualification is confined to the accepted F project. An
unrelated Note/source writer has no borrowed F authority and is rejected. Other
same-account Metadata can qualify only through its independently authenticated
existing owner/binding history; Metadata grants no Note membership/source change.
No Stage/StageOrder count or historical coverage is invented. Preserved conflict
material is not converted into an applied projection: only an actually resolved
F group permits its own retained sequence to count; an unresolved fork rejects.

Current-source verification remains independent and exact. Genuine mixed histories
use the complete accepted baseline/revision/member/projection fold. F/H-only
histories preserve their original role-specific source ordering, including genuine
cross-role commit order outside the mixed cohort. Selection is by authenticated
evidence, never fallback after a failed check. Source revision/membership/Head2
mismatch or valid-AEAD current source drift rejects despite valid Metadata ancestry.

### Contiguity, errors and immutable diagnostics

The durable cursor is reread/validated and must equal the actual checkpoint record.
Duplicate/gapped sequences reject before a candidate can be claimed. Every stored
sequence **from1**, including all of `proven_prefix`, is independently qualified;
the old cursor value is not proof. Counts cover1..candidate, not merely the delta
beyond the current prefix. Each sequence counts at most once.

For a fully authenticated supported account, the first received/unqualified row
stops the candidate immediately. A pending event before D prevents the prefix
from reaching D even though D has its own valid Metadata proof. A pending event
after D leaves the candidate at D and remains pending after restart. If an already
proven sequence is unqualified, reject rather than trust, reduce or repair the
stored cursor. Later unsupported material cannot be hidden just because an earlier
pending event would have stopped a partial traversal.

Returned values are deeply frozen for the exposed structure: current_proven_prefix,
candidate_historical_prefix, pull_cursor, first_blocking_sequence, blocker,
sourceCohort and frozen family counts. Only these diagnostic scalars escape.
All cursorCommitAuthorized/sourceAuthorized/firstApplyAllowed/commitAuthorized/
ackAuthorized/declarationAllowed/ready flags remain false. There are no prepare,
calculate, commit, registration or capability methods and no reusable grants,
certificates, decrypted events or persisted witness.

| Actual evidence | Result |
|---|---|
| Genuine fixture with no pending event | Candidate14, or16 for keep_both; first blocker NULL; source/proofs/cursor unchanged |
| keep_both pending before terminal deletion | Candidate15, first blocker16/received; deletion17 is retained but not counted; Metadata count2 |
| keep_both pending after terminal deletion | Candidate16, first blocker17/received; Metadata count3 |
| Gap, including a foreign-account key removing a required row | Rejected `missing_sequence` with first gap position; no candidate |
| Duplicate server sequence | Rejected `duplicate_sequence`; no candidate |
| Unsupported Stage/StageOrder or unrelated Note | Rejected `unsupported_family` at the offending sequence; no candidate |
| Received sequence already inside durable proven_prefix | Rejected `unqualified_proven_sequence`; no cursor repair |
| Corrupt/foreign/missing proof, unknown generation, unresolved fork, invalid source or unsupported authoring | Rejected sanitized `invalid_history`; no candidate or partial-authentication claim |
| Owner/cursor/full inventory changed during inspection | Rejected stale_source after the fresh complete snapshot comparison |
| Account/device/key/profile/epoch revocation | Rejected by genuine lifecycle guards; no stale diagnostic accepted as authority |

`HistoricalPrefixQualificationError.sequence` identifies rejected material/gaps;
it is not an authenticated candidate or a claim about a partially verified prefix.
Only successful full-history authentication may produce the first-blocker result
for a pending/unqualified row. A fatal account-cohort failure returns no result;
this conservative behavior preserves .13–14's complete-inventory fences. Decoder
or source exceptions never become success/fallback or expose plaintext details.

Before either a calculated result or a qualification error escapes, the complete
account is reread and compared and the actual session guards are rechecked. Failed
initial readonly transactions return no result; a later inspect starts fresh.
No write transaction, nonce, HTTP, source revision, owner head, inbox outcome or
cursor mutation is performed. Original bytes and pending data remain intact.

### Genuine acceptance, CI capacity and remaining work

New tests use actual F/H/O/Metadata commits, both F protocols, all four strategies
and ID0/ID1, with baseline/post-F setup in separate5000ms hooks and test bodies
bounded at5000ms. They cover real existing prefixes, exact counts, closed losing
branches, pending-before/after D, already-proven corruption, gaps/duplicates,
foreign scope, malformed proof/source, valid-AEAD drift, actual Metadata races,
stale cursors, unsupported later material, F/H-only ordering and no-F rejection.
Spies forbid public .13/.14 diagnostics and Q bindings in a positive reader test.
Results cannot be consumed as O/H/Metadata, Q, live transport or ACK authorization.
Old .11 STOP/.13/.14 and affected F/H/O/G/Q/K tests are retained; totals are in checkpoint.

Native `--historical-prefix` extends the same eight .13/.14 persistent profiles
and preserves all old assertions. It verifies an initial candidate through D,
then receives a genuine pending Content after D and repeats qualification/replay
before and after full process disk reopen. Exact family counts, immutable proofs,
all12 stores and unchanged durable cursors are checked. Traps enforce zero
readwrite/nonces/HTTP. Eight actual native readonly IDB aborts leave storage intact
and fresh qualification succeeds; competing tabs are excluded. One genuine
Metadata-owner actor invalidates all three simultaneous readers' complete snapshots;
revocation rejects all three. The test-only race gate has a bounded5000ms deadline,
not a retry. No transaction abort manufactures a cursor/source commit.

Accepted run39755485254 complete-project took21m01s/40; the isolated186-case step
7m55s and native .13/.14 step37s. Frontend admin took32m14s/40. New cases run once
only in complete-project, and existing native profiles gain checks rather than
being duplicated. Frontend gets no new suites; all six mandatory job names and
checks, original5000ms limits and Frontend40-minute budget remain unchanged.
Workflow/path coverage and capacity are checked; local timing cannot substitute
for fresh independent all-six acceptance. Actions are not polled after publication.

No schema, migration, durable format, original wire/proof, crypto, backend or
protocol changes are needed for this calculation. Existing BrowserResolutionPrefix,
bindMixedSources/Q prepare/calculate/commit, K routing, F/H/O/Metadata writers and
live prerequisites remain untouched. C21.2.11 remains IMPLEMENTATION STOP.

Proposed **C21.2.16 — post-F Metadata private handoff contract audit**: specify
private active pre-state versus terminal-delete historical post-state admission,
the actual Metadata owner's plan ownership, predicted structural-only changes and
exact ten-store atomic CAS/lifecycle/replay boundaries. Public prefix/reader
results cannot be reused as that authorization. Review any additional private
contract before implementing a dormant Metadata adapter or cursor commit; do not
activate either in .15. Stage/cover/local/own/additional-generation histories,
full recovery, outbound lifecycle, ACK/readiness and production synchronization
remain separate unaccepted dependencies.

C21.2.15 may be LOCAL COMPLETE only after bounded local validation; REMOTELY ACCEPTED
requires a subsequent independent Cloud6/6 success. C21.2.08 NOT CLOSED,
C21/C21.2 IN PROGRESS, Web89.36%, ready=false, closed registration and every
VPS/security/public-release gate remain unchanged.

## C21.2.18 — independent private historical cursor authority

[The later .18 implementation](C21_POST_F_METADATA_ROUTING.md) uses fresh complete
original-wire/proof/source authentication to mint a new closure-bound private
cursor certificate, with full-inventory CAS in the native cursor transaction.
It does not consume a .15 diagnostic, turn historical decoding into first apply,
or change the public .13/.14/.15 contracts. A real Metadata owner outcome and its
later cursor update are separate durable operations; failure of the latter retains
the earlier applied evidence and reports a blocker. The original .11 negative tests
remain historical/default-path evidence. Received Content before/after terminal D
never gains historical qualification or live permission. New .18 remote acceptance
is pending; all unimplemented source/family/outbound/readiness/release requirements
remain in the checkpoint's C21 REMAINING ACCEPTANCE GATES inventory.
