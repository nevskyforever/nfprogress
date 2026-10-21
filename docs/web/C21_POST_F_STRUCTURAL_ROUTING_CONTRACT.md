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
