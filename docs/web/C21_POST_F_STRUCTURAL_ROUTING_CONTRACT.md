# C21 post-F structural routing contract

**Status: architecture audit only — no structural route is enabled in mixed K.**
This document defines a possible bounded implementation contract for post-F
project Metadata, Stage and StageOrder inbox events. It does not grant Note source
authority, ACK authority, reader readiness or production synchronization.

## Audit result

The existing Web v10 records can represent the evidence needed for these routes;
the audit found no need for an IndexedDB migration, new store, or new persisted
proof format. Metadata uses `ownerHeads` plus the existing applied inbox proof
(record version 2). Stage and StageOrder use their existing owner-head histories
and inbox proofs (versions 5 and 6). The schema is fixed at IDB10 and the complete
recovery inventory already names ten existing stores: `inbox`, `outbox`,
`receipts`, `projectBindings`, `ownerHeads`, `legacyNoteHistory`,
`legacyNoteIntents`, `localProjects`, `localNotes`, and `cursors`.

That does not mean the existing owners accept the mixed K handoff. Their opaque
plans and atomic commits are family-scoped. Metadata commit rereads lineage,
Metadata head, retained rows, local Metadata outbox/receipts and cursor. Stage and
StageOrder commit reread `PREFIX_STORES` (inbox/outbox/receipts/cursors/bindings/
ownerHeads/history). Neither commit compares the entire ten-store v10 inventory
inside its write transaction. K's current mixed entry point instead stops at
`project_metadata`, `stage`, and `stage_order` before calling any structural
owner. The default recovery entry point has structural routes only before an
accepted Resolution; it is not a post-F adapter.

Therefore **no migration or persistent-record change is required**, but a
separately reviewed private owner adapter is required before post-F dispatch.
Without a full-account transaction guard and explicit dependency admission, this
route must remain STOP/BLOCKED. The read-only Q prefix result cannot authorize an
owner commit.

## Routing matrix

| Event / state | Accepted owner evidence | Post-F mixed K decision |
|---|---|---|
| Coverless project Metadata create/update | Authenticated original ciphertext; exact descriptor/reference; imported Metadata proof and linear `project_metadata` owner history; `import_remote/captured/active` binding | Candidate for a future private adapter after full-inventory guard and lineage/dependency checks |
| Coverless project Metadata delete | Same evidence; exact delete tombstone (`deleted_at == updated_at`); no non-null cover material | Candidate for the same adapter; retain tombstone in owner history. Any non-null `cover_reference` remains blocked until its material contract exists |
| Metadata fork, second genesis, missing parent, stale binding, local Metadata outbox, or self echo | Existing Metadata owner rejects or cannot prove it | Stop at that sequence; preserve received bytes and existing heads |
| Stage create/update | Protocol 3 canonical AEAD event; matching descriptor; Metadata proof for the referenced active nondeleted head; exact Stage parent/tip and full retained Stage history | Candidate only after Metadata is applied and verified and the private full-v10 handoff is implemented |
| Stage delete / Stage tombstone | Browser proof builder accepts only `create`/`update` with an upsert descriptor; deletion is not representable as an accepted Stage proof | Unsupported; do not infer deletion or remove a Stage head |
| StageOrder create/update | Protocol 3 AEAD event; Metadata dependency; every referenced Stage head and complete event coverage; membership equals all authenticated current Stage heads | Candidate only after all earlier Metadata/Stage dependencies and a full inventory guard |
| StageOrder delete, missing ancestor, open/conflicting head, incomplete child/tombstone manifest, foreign Stage, or membership mismatch | Existing owner rejects or cannot prove complete current membership | Stop at exact sequence; no order projection or prefix advancement across it |
| Any structural event from this device, unsupported protocol/family/generation, or event for another project | No accepted post-F mixed authority | Explicit barrier; never route through H/O or treat it as Note source evidence |

Metadata, Stage, and StageOrder have separate owner heads and proofs. Their
successful application may advance only those structures and the matching inbox
state/proof. It must not edit `localProjects`, `localNotes`, project membership,
or `source_revision`. The existing Metadata owner has this shape today; the
contract for future adapters must retain it.

## Authentication, ordering, and dependency boundary

The router must read and authenticate the complete account inventory, not a
family-filtered v9 view. This includes every inbox row and sequence through
`pull_cursor`, retained history, owner heads, upload/receipt evidence, project
bindings, local project and Note ciphertext, local intents, and cursor fields.
Authenticate the original wire with its existing AEAD/AAD and codec. Bind the
descriptor to account, project, entity, event, device, protocol, operation,
revision, timestamp, deletion marker and server sequence. Retain exact ciphertext;
do not rewrite, normalize or reconstruct wire events.

Admission is by the earliest received server sequence. Authenticate later rows
as part of the complete inventory, but never apply them ahead of an earlier
received event or use them to hide a gap. For a Stage event, its exact Metadata
event must already have an accepted proof and be present in the authenticated
Metadata chain. For StageOrder, every Stage named by the order must have an
authenticated current head, all referenced Stage events must be covered by that
head's complete history, and the order membership must equal the complete
current Stage-head set for the same project/bootstrap. Re-evaluate these
dependencies after each commit from a fresh inventory.

Current Q/G mixed prefix validation authenticates the complete v10 inventory and
opens received structural ciphertext, then asks the existing family prefix
verifiers to qualify only persisted applied evidence. It does not apply those
received events. A later structural event can be authenticated while an earlier
independent Note is considered; the router still must stop at whichever event is
the earliest pending sequence. If a received Metadata event is the dependency
for a received Stage event, apply Metadata, reload and revalidate, then consider
Stage. If an earlier unsupported family, missing sequence, invalid history,
unresolved fork, or unsupported generation prevents complete witness creation,
the pass stops without applying a later event or minting a Q prefix certificate.
No filtered retry, legacy fallback, or bypass of an earlier event is allowed.

## Private handoff and atomicity requirements

A future adapter must keep owner handles, plans, and commit authority in a private
closure. A read-only witness or diagnostic value is never accepted as commit
authorization. For each structural event:

1. Authenticate a complete pre-state inventory and establish the exact earliest
   event, route, binding, family history and dependency set.
2. Ask the existing family owner to prepare its normal opaque plan. Verify the
   predicted structural post-state and prove that the Note-source stores and all
   unrelated account records are unchanged.
3. Immediately before commit, compare the complete inventory again. Then commit
   under one IndexedDB read/write transaction spanning the ten existing stores:
   reread and compare the exact pre-state in that transaction, recheck lifecycle
   and dependencies, and atomically write only the owner's existing head/proof
   plus the inbox's existing applied transition. Abort on any mismatch.
4. Reload and authenticate the complete inventory after the commit. Exact replay
   returns the existing accepted result and does not append history or alter
   source data. A crash before commit leaves the event received; a crash after
   commit leaves the durable owner proof for restart validation.

The accepted family owner must continue checking its own immutable wire digest,
retained history, current tip, lineage and family invariants. The new guard
supplements those checks; it cannot replace them. A stale source, altered
inventory, competing tab, changed binding, auth/key/profile/device revocation or
transaction abort rejects atomically. Do not retry automatically. A user may
manually retry only after the missing dependency or stale condition is repaired
through an already accepted owner flow.

## Explicit barriers and STOP conditions

Stop without writes or prefix advancement for missing sequence/history, invalid
AEAD or descriptor, duplicate event/sequence, missing Metadata ancestor,
unsupported cover material, Stage deletion, unresolved or competing heads,
incomplete StageOrder coverage, foreign project/bootstrap, stale owner tip,
local structural outbox, self echo, unknown family/generation, unsupported
structural payload, an earlier unqualified event, or any failed full-inventory
CAS. Preserve ciphertext, proofs and heads for diagnosis/retry. Never convert a
structural result into a Note projection, a source revision, ACK, capability,
`ready`, or positive registration status.

**Implementation STOP:** if the existing browser transaction abstraction cannot
open a single read/write transaction over all ten IDB10 stores and compare the
complete pre-state before the family's existing writes, do not weaken the check
or add a sidecar token. Return to contract review. If future implementation
requires a new durable proof, migration, wire field, codec or server contract,
stop and obtain a separate reviewed contract before implementation.

## Bounded acceptance matrix for a future implementation

Use real accepted F/H/O histories and actual Metadata/Stage/StageOrder owners;
do not fabricate applied inbox rows or owner heads. Run both supported transport
protocols where the family accepts them (Metadata 2/3; Stage and StageOrder 3),
both F root protocols, all four F strategies, and ID0/ID1 for applicable encrypted
events. Exercise:

- Metadata create/update/delete, exact reference binding, tombstone retention,
  non-null cover blocker, missing parent, conflict, local-outbox and self-echo
  barriers;
- Stage create/update after Metadata, exact parent/tip, full history, missing or
  deleted Metadata, unsupported delete, conflict, self-echo and restart;
- StageOrder after multiple genuine Stage heads, exact coverage and membership,
  changed/missing/foreign Stage, incomplete history and tombstone child-manifest
  barriers;
- interleaved ordinary Note and H descendants, ensuring structural apply leaves
  project/Note ciphertext, membership and `source_revision` byte-identical;
- complete inventory mutation between prepare and commit, actual two-tab race,
  stale owner/source, auth/key/profile/device revocation, injected transaction
  abort, restart after each owner commit, exact replay and cursor/prefix abort;
- missing sequence, earlier unsupported family, later unsupported family,
  unresolved fork and unsupported Resolution generation, proving no event is
  skipped and no prefix crosses the first unqualified sequence;
- zero ACK, capability PUT, Content publication, scheduler activation and
  `ready=true`.

Use disposable real IndexedDB files in Chromium and reopen the same database.
Acceptance must report route outcomes, preserved wire/proofs, exact before/after
inventory comparisons, cursor/prefix, restart, rollback, race and revocation
results. Existing 5-second per-test budgets and accepted Frontend 40-minute job
budget remain unchanged; partition work only if measured job time requires it.

## Numeric implementation sequence and closure boundary

Proposed **C21.2.11 — private post-F Metadata adapter and ordering gate**: first
implement only coverless Metadata create/update/delete after one accepted F,
using existing owner formats and the full-ten-store atomic guard. Prove interleaved
Note/H state unchanged, dependency retry, exact replay, restart, rollback, race
and revocation. Keep Stage and StageOrder blocked. Proceed to a later numeric
slice for Stage apply and another for StageOrder only after each prior slice is
independently accepted. Do not add lettered stages or renumber earlier records.

These slices would still not close C21 or C21.2.08. Closure requires the accepted
reader/capability contract, complete browser family readers and ordinary writers,
original/retained Resolution and mixed source history, structural routes where
required, exact ACK-safe contiguous-prefix evidence, production composition and
multi-device lifecycle/restart acceptance. Content sealing, upload, immutable
receipt, self echo, server declaration/ACK gates, own authorship and the VPS
security/public-release gates remain separate prerequisites. Keep `ready=false`,
do not activate synchronization or public registration, and preserve Web progress
89.36% until its separately defined acceptance criteria are met.

## C21.2.11 — implementation STOP: historical Metadata tombstone semantics

The C21.2.10 commit `25df7f98beb6ede03d4bc082c0a949a9777d83f3` is **DOCS-ONLY
AUDIT COMPLETE**, not functional acceptance. Its two documentation paths did not
trigger Cloud/SQLite workflows. The preceding matrix records possible routes;
the following genuine counterexample blocks the proposed combined create/update/
delete implementation before any production change.

**Exact blocker:** accepted historical Content authentication requires a CURRENT
nondeleted Metadata tip, even when the Content event names a genuine nondeleted
Metadata ancestor. A valid Metadata delete changes only the Metadata head and
inbox proof, but makes the complete F/H/O account history fail authentication:

- `resolutionAuthentication.ts`, private `dependencies`: a Content F requires
  the referenced Metadata proof AND the current tip to be qualified and nondelete;
  a delete tip calls `bad()` (`corrupt_record`).
- `resolutionHistorical.ts`, `authenticateContinuationHistory`: every retained
  peer Content candidate calls `prepareNotePrerequisite`, including already
  applied candidates, before source/prefix verification.
- `noteTransportPrerequisite.ts`, `prepareNotePrerequisite`: requires a qualified
  nondelete dependency AND a qualified current nondelete Metadata tip; a delete
  tip rejects with `stale_authority`.
- Q invokes that full historical authentication before its source/family
  certificate; mixed K also authenticates history before routing. O/H rely on
  the same historical and dependency checks. Neither a full-account CAS nor
  immutable Metadata proof can repair this semantic incompatibility.

The counterexample is specifically a retained Content dependency, not a claim
that every Metadata tombstone is corrupt. A wholly Legacy F/H/O control still
qualifies its genuine Metadata deletion through Q. A Legacy F followed by a
genuine applied Content O event already exhibits the blocker; Content F exhibits
it directly. Both are required mixed-reader cohorts in the requested scope.
Applying only create/update, filtering old Content, replaying a pre-delete
inventory, changing a tombstone back to an active tip, or ignoring a failed Q
verification would substitute a weaker or different scope and is not enabled.

### Genuine evidence and unchanged boundaries

`postFMetadataBoundary.spec.ts` creates genuine accepted F/H baselines, then uses
the actual O owner for an independent Content ID1 event. The actual imported
Metadata owner applies a compressed coverless update (positive Q control), then
in a disposable counterexample applies a valid coverless delete. All four F
strategies and Legacy/Content F roots are covered, with Content F ID0/ID1. The
small deletion fixture remains ID0; no padding or fabricated proof forces ID1.
The wholly Legacy control distinguishes historical Content dependency failure
from Metadata owner/proof-format failure.

Before the counterexample, the unchanged manual K refuses the received structural
event with `post_F_structural_route` and leaves the full database identical. The
direct Metadata owner is used only to construct negative evidence in disposable
tests; it is not new routing or production authorization. The resulting tombstone
is genuinely applied and replayable, source/Note history is unchanged, and Q/K
reject the complete resulting account. Failed verification does not repair or
rewrite any retained record.

A bounded native Chromium probe reuses the unchanged acceptance harness and real
F/H/O setup: 8 disk profiles (both F protocols × four strategies), 8 full process
reopens, 16 transaction abort/rollback checks (each Metadata write boundary),
8 competing-tab writer exclusions, and exact Metadata replay. Each real ID1
update qualified through Q before deletion. Every valid Metadata tombstone caused
the same Q/K rejection after disk reopen while original wire, Note source and
history remained identical. Page errors and unauthorized HTTP were zero; the
16 device PUTs were disposable setup/rebind only. The temporary probe and build
bundle are local audit artifacts, not added product/test-fixture infrastructure.

### Storage decision and next numeric slice

The ten-store compare is feasible: `runBrowserTransaction` opens a strict native
transaction over the supplied store list; `syncTransaction` adds identity/account
binding checks; `scheduleResolutionInventory` reads all ten existing recovery
stores. No schema, migration, wire, crypto or proof-format deficiency is evidenced
by this blocker, and none is changed. The Metadata owner itself remains reusable;
the issue is the accepted full-history lifecycle contract after a tombstone.

**STOP under C21.2.11's mandatory invariants condition.** No adapter, handoff,
Metadata route or activation was implemented. Do not mark C21.2.11 functionally
complete or remotely accepted because its negative evidence passes.

Proposed **C21.2.12 — historical Metadata tombstone / Content dependency contract
audit (DESIGN ONLY)**. Define independently authenticated historical dependencies
for already accepted Content F/candidates separately from active prerequisites for
new applies. Specify deletion timing, ancestor/sequence coverage, fresh versus
replay checks, imported lineage, Stage/StageOrder consequences, new pending events,
forks, restart, prefix and current-source behavior without weakening any owner.
Determine whether existing immutable evidence suffices before proposing runtime
changes. Do not silently implement that contract or renumber prior stages.

Stage/StageOrder and Metadata routing stay blocked in mixed K. All prior F/H/O/Q/K
behavior and negative tests, Note-source authority, historical evidence, IDB10,
ready=false, C21.2.08 NOT CLOSED, Web89.36% and security/public-release gates remain.

## C21.2.18 — bounded alternative to the historical .11 STOP

[The explicit .18 Metadata path](C21_POST_F_METADATA_ROUTING.md) selects the accepted
private handoff before original K's live H/Q preflight and independently authenticates
the actual post-delete history for a separate local cursor commit. The old .11
counterexample and default K/G/Q assertions remain unchanged. The bounded new path
supports only genuine peer coverless Metadata3 update/delete, one F and one earliest
pending Metadata, with complete original source/history/CAS checks. No Stage/
StageOrder/create/cover/own/local/further-generation routing is inferred. This local
repair needs independent .18 acceptance and cannot close the original full .11
scope or authorize ACK, Note capability, a writer or production scheduling.
