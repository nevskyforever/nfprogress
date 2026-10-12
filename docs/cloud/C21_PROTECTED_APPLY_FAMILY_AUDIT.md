# C21.1.06 — protected apply family matrix and prerequisite stop

2026-10-12. **C21.1.06 BLOCKED BEFORE IMPLEMENTATION / NOT LOCAL COMPLETE**.
This is an audit, not a new authority/proof protocol or implemented v4 schema.
C21.1.05 / .05A independently accepted by owner/GPT at repair
`af407f751cbda2898eb881f90fdd08177e2b28d3`, implementation
`eed5ed298838c32ddc8f526b4ad2992b4fecd6c4`, Cloud **38165641607 SUCCESS**,
all six required jobs SUCCESS. Official84.0%, C21 IN PROGRESS.

## First blocking prerequisite: durable project binding and bootstrap lineage

Native Metadata apply checks the installation's existing project binding and
bootstrap record INSIDE its apply transaction, before any apply ledger/head write:
`frontend/src-tauri/src/project_metadata_sync.rs:399` joins
`cloud_sync_project_bindings`, `cloud_account_bindings` and
`cloud_sync_project_bootstraps`, matching local account/project/bootstrap and the
canonical user from the authenticated frame. A valid decrypted event is not enough.
The same module's test
`project_metadata_legacy_binding_without_bootstrap_is_preserved_but_not_publishable`
removes the bootstrap row and proves missing lineage stays blocked; no implicit
binding/bootstrap reconstruction from an event is allowed.

Further production evidence:

- Legacy Note apply in `note_sync.rs:10057` requires project existence plus its
  account binding; missing project becomes orphan. Resolution peer apply and
  own-resolution reconciliation also require that binding (`:9022`, `:9525`).
- Stage `dependency()` (`stage_sync.rs:309`) checks canonical user AND exact
  bootstrap ID, then a proven live Metadata reference and active current authority.
- `account_catalog.rs:839` checks project binding/bootstrap, Metadata event and its
  exact applied ledger. Historic Metadata proof alone is insufficient: current
  authority must be active and its retained ancestry must cover the reference.
- Document/Map `dependencies_ready()`, Content Note `ready()`, Progress/Game
  `dependencies()` call that project-reference boundary; Stage references add
  their own live complete-authority requirements.
- Production `noteSyncRuntime.runGatedWithOptions()` (`:489`) reconciles the
  account-wide project registry before the normal cycle. A dormant repository must
  not pretend that possession of transport ciphertext supplies that gate.

Browser IDB3 has ONLY identities/accountBindings/outbox/inbox/cursors/receipts.
Its account binding is local-account↔canonical-user, not project membership,
installation lineage, bootstrap readiness or account-wide registry readiness.
Its receipts prove upload event/sequence acceptance; its cursor proves transport
position. Neither establishes project binding/bootstrap. Inbox/body event IDs and
AAD project scope likewise cannot prove this installation's admitted lineage.

The frozen browser design already reserves **projectBindings** separately from
ownerHeads. The native DTO `CloudProjectBootstrapRecord` retains project/account/
device/bootstrap IDs, upload_existing versus import_remote mode, closed-enum phase,
remote state/high-water and initial cohort count/ordinal/max sequence. Its admitted
relationship must survive reopen and be compared in the protected transaction.
This is a required prerequisite, not a new browser authority model. No DTO is
implemented or automatically populated in this slice; no source names/paths belong
in such a browser proof.

Putting installation binding into a synthetic owner-head genesis, trusting a
caller-supplied ready boolean, or treating an authenticated Metadata event as an
implicit import would weaken the frozen distinction between installation lineage
and entity authority. Creating projectBindings here would cross the task's explicit
STOP boundary for an additional structurally necessary store. Therefore STOP before
schema migration, crypto-plan builder, owner-head write or applied-proof API.

## Family identity, causality and retained-history matrix

A = local account bound to canonical user U; P = project; S = nullable Stage.
Project families use existing project crypto/AAD1; Catalog/Account Game use existing
account scope crypto/AAD2. Source device differs from pulling device. Transport
sequence, time and maximum revision never select a winner.

| Family | Exact native owner/entity distinction | Complete tips, dependencies and retained history |
| --- | --- | --- |
| Legacy Note | Project crypto; `(A,P,note entity ID)` | V1 primary parent/revision and immutable causal versions/tombstones; complete conflict event/version membership plus group generation when present. Project binding and eligible Note route required. |
| Note Resolution v2 | Same Note owner; optional retained clone is a second Note entity | Sorted complete resolved_event_ids equals primary+additional parent set; conflict-group/generation and exact scoped parent/version/applied-resolution proofs. Keep-both cannot partially advance original/clone. |
| Content Note codec8 | Same Note authority; authenticated project/Stage/source/content format | Existing Note/Resolution history plus codec8 frame receipt; bootstrap/Metadata/Stage references. Map-derived Note has no independent Content Note authority. |
| Metadata, without cover | `(A,P)`; transport entity_id = P | Complete sorted parent_event_ids, revision AND generation, exact bootstrap; all canonical encrypted Metadata ancestors retained. Local source/reconciliation/decision proof affects clean classification. |
| Metadata v2 with Cover | Same Metadata owner; cover blob ID is a dependency, not a separate Metadata tip | Same Metadata tips plus exact cover reference, nonce/ciphertext/envelope hash/size and verified blob material. Reference-only apply is forbidden. |
| Stage | `(A,P,stage entity ID)` | Complete parent_event_ids/revision/generation; exact bootstrap and live Metadata proof. All structural ancestors and relational dependency evidence retained. |
| Stage order | `(A,P,stage_order)`; not one owner per position | Complete causal parent set and exact live Stage membership/head permutation; removals require Stage tombstone proof. Not a timestamp-derived order. |
| Document codec10 | `(A,P,stable document ID)`; Stage relation belongs to history and can move | Sorted complete parents, revision/generation; bootstrap/Metadata/live Stage proofs including prior dependency branches. Stable document ID must not be replaced by `(P,S)` when moving scope. |
| Map codec9 | `(A,P,project-map)` or exact `stage-map-<sha256>` ID | Sorted complete parents/tips, revision/generation; bootstrap/Metadata/live Stage references. Map and its derived Notes form one semantic apply unit. |
| Progress codec11 | `(A,P,scope_id(S))`, where native scope_id is project or stage:S | Complete causal tips and retained entry/chain history; revision/generation, bootstrap/Metadata/Stage and unit proofs. Progress order is a derived relation, not a separate authority. |
| Catalog codecs4–7 | Account crypto; `(A,entity_type,entity_id)` for folder/order/membership/project_order | Complete parent_event_ids/tips, revision AND generation; exact folder/membership dependency maps and project bootstrap+Metadata proof tuples. Incompatible live dependency sets are conflicts, never silently dropped. |
| Project Game codec12 | Project crypto; owner `(A,canonical [P,S])`; per-action entity ID is NOT the owner | Complete parent/action chain and retained snapshots/proofs, bootstrap/Metadata/Stage plus matching Progress/reward dependencies and stable action identity. |
| Account Game codec13 | Account crypto; native owner account; game:<event ID> identifies an action | Complete action parents/tips, project-action/reward/streak/compensation dependency proofs and exact native rule checks. Not a Catalog folder variant. |

## Outcome and proof matrix (existing production semantics, not Web implementation)

All rows first require exact authenticated frame/envelope/descriptor/scope and
retained dependency proof. Crypto/decompression/semantic decode belongs to the
current draining auth/key lease outside IDB, with temporary byte buffers cleared.
An exported structural DTO or a caller's outcome='clean' cannot manufacture that
verification. No concrete browser apply-plan/proof record is designed past STOP.

| Family | Clean/replay/self-echo rule | Non-clean and future ACK evidence |
| --- | --- | --- |
| Legacy Note | Clean causal parent/head and compatible current Note/local intent; already_applied requires exact causal history match. Own echo checks outbox+receipt identity/sequence and current head, not source-device equality alone. | Missing project/parent → orphan; competing proven versions require conflict preservation; incompatible format/identity → rejected/error. Future ACK needs exact inbox/object/history or preserved-version proof, not the TS result conflict alone. |
| Resolution | Peer apply validates full tips/generation/parents and all original/clone mutations atomically. Exact applied-resolution replay uses its immutable proof. Own resolutions route ONLY through resolution reconciliation with canonical outbox/decision/continuation/receipt evidence. | Missing parents → orphan; self_echo_pending is not applied. Future ACK needs complete applied-resolution parent/result proof; upload receipt alone is insufficient. |
| Content Note | Existing Note/Resolution outcome plus exact authenticated codec8 frame/envelope/dependency receipt in the SAME transaction. | Unsupported frame/source/format/dependency remains blocked/orphan/rejected. Future ACK joins exact content receipt with underlying Note/resolution history. |
| Metadata / Cover | Exact bootstrap, complete parent/generation transition and compatible local/reconciled source. Own echo needs exact immutable event/envelope/receipt semantics and must preserve newer visible local state. Replay matches retained canonical payload/object/ledger. | Missing binding/lineage/material cannot apply; concurrent/local disagreement remains conflict-preserved/blocked. Future ACK requires exact Metadata ledger plus required Cover material proof. |
| Stage / Stage order | Metadata dependency active; exact complete parents/generation and compatible local structural state/membership. Self-echo uses exact sealed native evidence; replay matches canonical frame and ledger. | Missing Metadata/Stage proof → waiting/orphan; changed membership/local branch → conflict. Future ACK requires exact structural frame/envelope/ledger and relational dependency proof. |
| Document / Map | Compare complete old tips against parents AND current local/retained projection or explicit decision; verify dependencies for ancestors as required. Own native sealed/accepted event must match exact frame/envelope/sequence and decision/local rules. Exact applied ledger replay does not move heads again. | Incompatible tips/local edits → conflict_preserved; missing parents/deps/unsupported projection → waiting. Native apply commits complete tips, history, ledger and inbox classification together; future ACK cross-checks all immutable pieces. |
| Progress | Verified dependency units and rebuilt causal chain, complete tips plus compatible local source/decision. Own source alone is not proof; replay is exact retained event/ledger evidence. | Missing parent/unit/chain proof blocks; incompatible competing chains remain conflicts. Future ACK needs exact frame/envelope/ledger and chain proof. |
| Catalog | Recompute parent revisions AND generations; validate dependency coverage and compatible local catalog source/explicit decision. Replay matches exact frame/nonce/ciphertext ledger; pre-existing own receipt sequence must agree. | Missing/unproven references → blocker; incompatible live sets/local state → conflict_preserved. Native account inbox may REMAIN received even after ledger apply: future ACK uses the exact Catalog ledger/history, not that state. |
| Project / Account Game | Rebuild owner action chain; verify stable identities and reward/dependency rules; compatible local source or explicit decision. Own classification checks prior sealed material/local matching; no one-size self-echo shortcut. Replay uses exact frame/envelope/sequence/ledger. | Missing dependency/parent → waiting; noncommutative/local conflict retained. Future ACK requires matching event/ledger/snapshot and applicable blocker classification. One accepted genesis cannot imply multi-owner migration complete. |

For requested C21.1.06 clean-only semantics, EVERY orphan/conflict/rejected/unknown
outcome would leave browser inbox received and heads unchanged. Native preservation
outcomes above are documented for fidelity; implementing their blocker/conflict
engine or marking them applied is NOT authorized as a shortcut in this slice.

## Further scoped boundaries found; no extra stores created

Cover `project_cover_sync.rs:95` require_material loads the exact reference and
remote_verified material before Metadata apply (`project_metadata_sync.rs:404`).
Browser wire_item contains Metadata's encrypted event/reference, not the separately
transferred cover blob. Correct no-plaintext Web rebuild requires retained encrypted
blob material and authenticated reference proof; the planned encryptedBlobs boundary
needs its own reviewed implementation. No plaintext JPEG/projection can be copied
from native storage into browser IDB. Cover-bearing events cannot be downgraded to
cover-less success. This is an additional family blocker, not the first stop reason.

Account-only Catalog/Account Game events without project references do not
necessarily need projectBindings individually. They were NOT declared impossible
or implemented after the global prerequisite STOP. Their native clean classification
also compares retained/local source/decision and migration state; a narrower
account-only implementation requires its own explicitly bounded scope and proof
review. No unsupported claim that one generic ownerHeads record covers every family.

The protected-apply proof could potentially evolve versioned inbox records while
keeping wire_item immutable, as the task permits. No separate proof store has been
proven necessary at this stop point, and no proof format/store/digest/boolean is
invented here. ownerHeads remains planned; upload receipts stay upload-only.

## Audit result and next bounded prerequisite

Production browser/native/backend/crypto/protocol files are unchanged. IDB remains3,
all six stores/record versions unchanged, inbox received, ACK/proven prefix0.
No protected apply, network, projection mutation, editor/bootstrap/reconciliation
runtime or conflict/orphan engine is activated. No v4 migration or test/CI contract
for protected apply is claimed. No new dependency.

Read actual reader/apply modules, relevant tests and frozen designs, including
native missing-bootstrap, exact replay, self-echo, dependency and rollback cases.
No runtime tests/builds run for this documentation-only stop. Verify documentation
references, status consistency, diff scope and protected pyc hashes instead.
Cloud workflow already watches docs/cloud/**; this audit publication triggers
Cloud but cannot make unimplemented C21.1.06 locally complete. SQLite not expected.
Codex does not poll Actions or remotely accept the implementation.

Next bounded proposal: independently review/authorize dormant browser
projectBindings/bootstrap-lineage persistence and readiness-proof lifetime/CAS,
using the existing native DTO/registry rules, with no network/bootstrap activation.
After that foundation is accepted, resume family-specific protected apply; separately
bound Cover encrypted-material prerequisites and conflict/orphan/resolution handling.
Do not auto-create binding from a downloaded frame or trust caller-supplied readiness.
