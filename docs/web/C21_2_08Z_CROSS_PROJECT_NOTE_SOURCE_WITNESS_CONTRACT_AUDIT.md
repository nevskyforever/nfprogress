# C21.2.08Z — Cross-project Note source-witness contract audit

**AUDIT COMPLETE — documentation only.** Baseline `e8d20b9fb463f6f4daadfcc3cfdc5a41e57a961e`, branch `6.0`; preflight found a clean worktree and `HEAD == origin/6.0`. No production code, tests, CI, database, wire format, cryptographic behavior, or readiness gate changed.

## Independent acceptance and scope

The owner independently accepted C21.2.08Y implementation SHA
`59352b36c5d923031f9191d073e1d9a39b07a8c1`; Cloud run `40122788774` completed
6/6 SUCCESS. This accepts Y's bounded same-F-project O/Q implementation, not
cross-project Note history. MVP6.0.12 Cloud run `40236767686` remains pending
independent owner acceptance and is not marked accepted here. No Actions were
queried.

This audit asks whether an ordinary Note history in project B can be authenticated
and folded while project A contains the accepted Legacy3 F/H/O history. It does
not enable synchronization or broaden Y's accepted cohort.

## Existing evidence and exact gap

| Existing owner / durable data | What it establishes | What it does not establish for project B |
| --- | --- | --- |
| `projectBindings.ts::importRemote` | Account scope, project ID, bootstrap ID, active registry state and remote high-water, assuming the descriptor came from the authenticated registry owner | A source revision at import/bootstrap, the initial Note membership/projections, or a complete historical Note event interval. The imported binding starts with zero initial events and no initial maximum server sequence. |
| `initialNoteCapture.ts` and `bootstrapCompletion.ts` | For `upload_existing`, the source device's captured initial Note cohort, local ordinal range, accepted receipts/count and maximum accepted server sequence | A canonical, independently downloadable source snapshot for a different device/project. Capture is an outbound source-device cohort, not the imported project's source-revision anchor. |
| `inbox` received wire rows | Original encrypted event wire, authenticated event identity and account server sequence; the account prefix can check sequence continuity | A Note's project `source_revision`, proof that the device has every event since the project's source genesis, or the project state before the first received event. Server sequence is account-wide, not a project source counter. |
| `legacyNoteHistory` Candidate/Head1 and Note apply proofs | On the browser that applied an event: authenticated wire/candidate, Note causal parent/revision, and where applied, local encrypted projection and source-revision join | A portable source-device baseline or a canonical complete history on another device. These browser records are device-local evidence; a projection digest alone cannot reconstruct the projection. |
| Content3 proof / transport records | On the applying browser, joins event, dependencies, outcome and local source revision | A server-authenticated project source revision or completeness proof for a second device. Existing transport event wire does not carry the local project counter. |
| Current encrypted `localProjects` / `localNotes` | Current local projection, membership and local source counter under the current device's encrypted local authority | Historical baseline: these are mutable present-state records and cannot independently prove which initial state or transitions produced them. |
| F Resolution4 `source_after` and Y mixed fold | Exact project A source-after payload and R0; Y then folds eligible A transitions in server order | Any revision, membership, Note projection or source history for project B. Borrowing A's R0 would assert false authority. |

The available history cannot, by itself, reconstruct B from a separately
authenticated starting source. Account sequence ordering detects a missing
account sequence but does not prove that a downloaded project's Note history is
complete from its bootstrap. Per-Note event revisions and parent links prove
Note lineage, not the project-wide source counter or whole-project membership.
Same-browser persistence survives that browser's restart, but it does not make
its local source witness available to a newly imported device. Thus existing
DB10, its twelve stores, and current proof versions are **not sufficient** for
cross-project Note qualification under Y's Q contract.

Account-wide Note identity uniqueness remains a required fold invariant: an ID
must have one project owner across the complete account inventory. Existing
server sequence order must remain global and exact, while source revisions must
be contiguous only within the independently witnessed project. Neither counter
can substitute for the other.

## Minimal viable contract choices

| Approach | Authenticated source and producer | Durable/restart behavior | Compatibility and unsupported-history behavior | Decision |
| --- | --- | --- | --- | --- |
| Complete historical replay from project bootstrap | A trusted producer must expose an authenticated project bootstrap/source snapshot and the complete ordered Note history from that exact anchor. The replay consumer verifies account/project/bootstrap, membership, initial projections, every applied source transition, dependencies and global sequence joins. Existing event inbox is usable only if the producer can prove no interval is omitted and bind the anchor to it. | Anchor and replayable events must be durably available to a fresh device after restart; the consumer recomputes the fold rather than trusting today's local projection. | Old clients lacking the anchor or complete history reject without writes. This is smallest only if an existing owner/API already supplies that complete proof; the audited current records do not. | Viable contract shape, but **not currently implementable with existing records**. |
| New authenticated project source-witness record/chain | A narrowly scoped trusted source/apply owner produces a project bootstrap anchor and authenticated per-transition before/after source revision, membership and Note projection joins. Q consumes it only after authenticating the ordinary event and existing Metadata/Stage dependencies. The witness is bound to account, project, bootstrap and source device; signatures/MACs or existing authenticated encryption must be specified by the owner contract, not inferred from unkeyed digests. | Durable records must travel with or be retrievable for the complete history; a new device can verify and recompute the fold. Browser-local copies alone do not satisfy cross-device replay. | Older builds treat unknown/missing witness data as a blocker and preserve every record. Corrupt, partial, stale or mismatched witness never lowers a proven prefix. | Required if no existing authoritative full-replay source can be provided. Requires a separately reviewed and approved protocol/schema or frozen-semantic extension before implementation. |
| Trust current local project rows or reuse F's R0 | No independent producer; mutable local source or project A is substituted. | May survive one browser restart only. | Cannot distinguish a genuine complete history from a forged, stale or incomplete source and can mis-qualify B. | Rejected. |

### Contract decision

**Cross-project ordinary Note qualification remains blocked.** No positive witness
is minted from current `localProjects`, `localNotes`, imported project binding,
global sequence, Note-local revisions, or project A's F evidence. A future
implementation must first name the authenticated producer and provide either
the missing complete bootstrap-to-current history from an existing authoritative
owner, or a separately approved durable witness contract. If the latter needs a
wire/proof version, store, migration, server endpoint, or change to frozen C21
semantics, mark **IMPLEMENTATION STOP** until that separate contract is approved.

The consumer remains Q's private prefix owner. It independently authenticates
project B's source witness, replays B's Notes in global server-sequence order,
checks contiguous project-local source revisions and account-wide Note identity
uniqueness, then joins the result with existing Metadata/Stage/StageOrder owners
and project A's accepted F/H/O fold. Q may only advance the proven cursor; it
does not ACK. Missing, corrupt, forged, incomplete or unsupported evidence is
an earliest prefix blocker/rejection and causes no durable mutation.

## Future implementation acceptance matrix

| Scenario | Required result |
| --- | --- |
| Two genuine isolated projects; genuine Legacy3 F/H/O in A; independent Legacy2 and Content3 create/update/delete in B | Positive qualification only when B has the complete independently authenticated source anchor and all exact Note/apply/dependency joins. Otherwise block B's Note sequence; do not borrow A's R0. |
| Accepted Metadata/Stage/StageOrder interleaved across projects | Qualify only through their existing owners; keep each event in complete account sequence. |
| Full B source revisions plus global server order; restart and fresh-device replay | Recompute identical fold from durable authenticated anchor/history. Preserve ciphertext and exact cursor semantics. |
| Missing event, missing/corrupt history or retained ciphertext, stale auth/key/device, cross-tab race | Reject/block without deleting, rewriting or partially committing durable evidence. |
| Wrong project/bootstrap, forged source, cross-project Note ID collision | Reject; no Note ID may be attributed to two projects in one account. |
| Q qualification | Cursor-only `proven_prefix` commit; no ACK, upload, writer activation or reader declaration. |
| Older browser build encounters witness records | Reject without modifying any durable record; newer build may reopen and authenticate the same copy. |

Positive cases must use genuine production-shaped producer paths. Fabricated
authenticated proofs, caller-provided fold DTOs, present-state-only source,
weakened sequence checks, and fallback after authentication failure are not
acceptable test substitutes.

## Boundaries and next stage

C21 truthful reader gate remains intact: `ready=false`,
`declarationAllowed=false`, `writerAuthorized=false`; cloud Note upload/writer/ACK
remain disabled. Registration stays CLOSED; PUBLIC RELEASE BLOCKED. C22/C23,
PF6.0 and RC remain mandatory. Official Web progress stays 89.36%.

The next bounded stage should be **C21.2.08Z1 — authenticated second-project
source-baseline owner and replay contract/producer feasibility** — GPT-6 Luna /
High. It should first determine whether an existing authoritative bootstrap and
full-history source can satisfy this contract without a new format. If not, stop
implementation and submit the smallest new durable witness protocol/schema for
separate approval. Escalate to Sol / Medium only if that contract design exposes
an unresolved architectural ambiguity. Do not start a Q admission implementation
before the source authority is accepted.

MVP6.0.12's recorded localization test debt remains 27 historical untranslated
catalog keys per target language (47 at its baseline); its original test result
is preserved and this audit does not treat the debt as resolved. The independent
acceptance state for MVP6.0.12 Cloud `40236767686` remains pending owner
confirmation.
