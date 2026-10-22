# C21.2.19 — post-F Metadata no-head and create baseline audit

**Status: AUDIT COMPLETE — genuine Legacy-F no-head cohort demonstrated; private
create admission remains unsupported. No production implementation.**

Baseline branch `6.0`, starting HEAD and `origin/6.0`:
`3d5b5b3dc64c9fd1152530c90e09eb052960bc6b` (clean). The audit changed no
production TypeScript, Rust, Python, backend, workflow, schema, wire, or crypto
code. Its temporary probe was removed before commit.

## C21.2.18 independent acceptance recorded

C21.2.18 is **REMOTELY ACCEPTED** at implementation/CI-repair SHA
`8df51fbe37624324a5b0831daf6da2f1d0a55ecd`, Cloud Actions run `39850013638`,
**SUCCESS — all six mandatory Cloud jobs**. The repair corrected a defective
negative-test ciphertext mutation; it did not weaken production encryption or
synchronization. Current baseline `3d5b5b3dc64c9fd1152530c90e09eb052960bc6b` is
the subsequent docs-only release-policy checkpoint and does not need its own
Cloud run. Earlier failure/cancellation entries remain historical records.

This acceptance covers the bounded dormant .18 post-F Metadata update/delete and
private historical-prefix path only. It does not accept Metadata create/no-head,
close C21.2.11 or C21.2.08, or activate production scheduling, ACK, readiness,
capabilities, or publication.

## Finding: a genuine no-head Legacy-F history exists

The answer is **yes**, for a bounded imported-project cohort whose F resolution
uses Legacy protocol2. Protocol2 Resolution has no Content dependency wrapper or
`metadata_event_id`; the existing Resolution authentication verifies the
resolution, parent history, imported binding, bootstrap, and encrypted source
without requiring a Metadata owner. The probe began with an actual
`import_remote / captured / active` project binding at remote high-water 0, no
Metadata event and no Metadata owner. It produced contiguous peer Legacy Note
history through existing owners, then applied an encrypted protocol2 F event
through the actual `BrowserResolutionPlanner` / `BrowserResolutionApplyRuntime`.
The F proof and source output were produced by that owner; no applied inbox row,
F proof, root, or source snapshot was inserted by hand.

The bounded probe exercised all four accepted F strategies:
`choose_version`, `manual_merge`, `delete`, and `keep_both`. In each case the
complete ten-store inventory had no Metadata owner and the original F history
authenticated successfully. The `keep_both` case retained its original and
retained Note outcomes. This proves a real baseline can exist; it is not evidence
that the current private Metadata handoff admits a create from it.

The same imported project then received a genuine sender-encrypted, coverless
Metadata protocol3 `create` at the next sequence, with revision/generation 1 and
no parents. The existing `BrowserImportedMetadataApply` accepted it from its
actual imported binding. This family owner checks its own original wire, AEAD,
bootstrap, create shape, local Metadata outbox/receipts, and null-head transition;
it writes only the Metadata owner head and selected inbox applied proof.
`authenticatePrivateMetadataSource(..., durable)` subsequently authenticated
the preserved F source and the applied create together. A fresh private handoff
replay returned `already_applied`, and a separate private prefix pass qualified
the account through sequence 5 (three Legacy Note outcomes, one Resolution, one
Metadata genesis). The Metadata commit left `proven_prefix` at 0 until that
separate prefix transaction advanced it to 5. No ACK or readiness authority was
produced.

## Why the current private route still blocks that create

Before the create, the existing full-account private source verifier requires a
Metadata owner and authenticated genesis chain for the F project. The current
handoff returns `unsupported_create_baseline` before it obtains an imported
owner plan when that head is absent. The direct private source check also rejects
the no-head pre-state. The probe confirmed both barriers while preserving the
received encrypted create and every store. This is a deliberate missing
admission contract, not a failure to authenticate the Legacy-F event itself.

After the real imported owner applies the create, the private durable verifier
can authenticate the resulting complete F/Metadata state and replay it. That
post-state success cannot authorize the pre-state create retroactively. The full
route needs a private, independently authenticated no-head Legacy-F pre-state
branch and an exact predicted transition from null to the real imported owner's
genesis.

Content-F is different. Protocol3 Content Resolution carries an authenticated
`dependencies.metadata_event_id`. The current Resolution dependency verifier
requires that exact Metadata proof to belong to the project's active Metadata
owner and requires an authenticated, nondeleted dependency. The private
historical dependency verifier also requires `Metadata.server_sequence <
Content.server_sequence`. Therefore a legitimate Content-F history cannot start
without a Metadata genesis already applied before F. A Content-F project with a
missing head is corrupt/incomplete and must remain rejected; it is not a create
baseline.

Content ID0/ID1 history remains usable after a legitimate Legacy-F no-head
genesis only when the new Metadata create is earlier than those Content events,
their original dependencies reference that exact genesis/bootstrap, and their
own original ciphertext and outcomes authenticate. A Content event before the
candidate create that depends on it is not a valid applied history. Later received
Content may remain pending behind the earliest Metadata create, then be handled
by the existing Content owner after a fresh full-inventory reload. Existing .18
tests cover ID0/ID1 with an already-established Metadata owner; the temporary
no-head probe did not combine post-create H/O Content ID0/ID1 events with all four
F strategies. That combined matrix remains required for implementation
acceptance.

## Genuine-evidence and admission matrix

| Baseline / candidate state | Decision | Evidence and boundary |
| --- | --- | --- |
| Imported `captured/active` binding; exact bootstrap; complete contiguous account history; no project Metadata owner/event; authentic protocol2 Legacy F; one first protocol3 coverless `create` with revision/generation 1 and no parents | **Legitimate candidate cohort exists; current private handoff BLOCKS** | Four-strategy temporary probe used real imported binding, real Legacy Note applies, actual F owner commit, genuine encrypted create, and the full ten-store inventory. `.17` returns `unsupported_create_baseline`. No production route changed. |
| Same no-head cohort after the imported Metadata owner commits the actual create | **Durable history supported; separate prefix can qualify** | Probe authenticated F plus Metadata, exact replayed without another genesis, and committed prefix in a distinct transaction. This is post-state/recovery evidence only. |
| Content protocol3 F with absent Metadata genesis | **Reject; no legitimate baseline** | Content F's original authenticated dependency names Metadata; owner/prefix proof and strict `M < F` are required. Missing owner means incomplete history, not create permission. |
| Metadata genesis already applied but owner head removed, or applied proof/event remains without its owner chain | **Reject as corrupt/incomplete** | Full rows/proofs must join the actual owner chain. Missing or mismatched proof, gap, or incomplete inventory cannot be repaired by another create. |
| Existing valid Metadata owner/head for same project | **Reject second create** | Imported owner transition permits a null-head genesis only. Existing head plus another `create` returns Metadata conflict; only exact parented update/delete routes are accepted by .17/.18. |
| Missing, foreign, stale, wrong-account/device, wrong-bootstrap, or wrong-mode/phase project binding | **Reject** | Imported owner requires `import_remote / captured / active` and matching project/bootstrap/account identity. No binding is inferred from a caller DTO or F event alone. |
| Wrong create sequence, revision/generation, parent list, descriptor, ciphertext, AEAD, or event/project identity | **Reject** | Existing imported owner checks exact descriptor/event/AEAD and create transition; complete private route must additionally prove earliest eligible sequence and no sequence gaps. |
| Earlier received event, pending Metadata outbox/receipt conflict, source mutation, conflicting Note rows, or another pending Metadata | **Reject or stop at the earlier event** | The full account cannot be filtered to select create. The earliest received event rule and owner retained-history checks stay in force. |
| Cover material, Stage/StageOrder, own/self-echo, unsupported Resolution generation, or unrelated-project material outside the accepted cohort | **Reject / unsupported** | Separate existing contracts remain unchanged; they cannot be used as fallback evidence for create. |

Absence of an owner head is never sufficient by itself. A future exception must
prove the imported bootstrap and source lineage, exact original F/H wires and
proofs, the dense complete sequence range/current prefix, absence of an earlier
Metadata genesis in retained inbox/owner/outbox/receipt evidence, and the exact
candidate create. If the remote import high-water or retained history does not
prove the range from its origin, reject as incomplete; do not assume a missing
head means no genesis existed.

## Existing tests and executed evidence

The temporary no-head probe passed **4/4 cases**, one for each F resolution
strategy. It exercised the complete ten-store inventory, actual Legacy F owner
commit, actual encrypted Metadata create, private pre-state rejection, durable
post-state authentication, exact replay, and separate cursor commit. The probe
was removed and is not part of the accepted test suite.

Focused existing regression suites passed **218/218 tests across five files**:
`privateMetadataHandoff.spec.ts`, `privateMetadataAuthentication.spec.ts`,
`postFMetadataRecovery.spec.ts`, `historicalMetadataDependency.spec.ts`, and
`importedMetadataApply.spec.ts`. Coverage includes both F protocols and all four
strategies for the existing update/delete path, applicable Content ID0/ID1
history, pending-sequence/source/lineage/AEAD/proof barriers, duplicate genesis,
wrong revision/generation/parent, owner/prefix transaction separation, replay,
and the preserved no-head `unsupported_create_baseline` negative.

The following were **not run as production changes or as a complete no-head
matrix**: no-head Content-F (the accepted dependency contract makes it
inadmissible); every malformed binding/ciphertext/sequence variation combined
with the new Legacy-F baseline; post-create H/O Content ID0/ID1 for all F
strategies; and a physical browser-process crash in the create-to-prefix gap.
Existing .18 native restart/race evidence covers its accepted update/delete
cohort, not this new create case. These remain implementation acceptance work.
No full 761-case suite, typecheck, production build, or CI run was performed;
production code was unchanged.

## Minimal future private create contract

Propose **C21.2.20 — private Legacy-F no-head Metadata genesis admission and
restart qualification**. Scope only the proven Legacy-F cohort; do not extend
Content-F, transport2, cover, Stage/StageOrder, own authorship, further
Resolution generations, ACK/capability, writer/upload, or orchestration.

The implementation must preserve the accepted .17–.18 model:

1. Read and authenticate the complete ten-store account inventory plus existing
   native account/device identity and project binding. Prove the exact original
   Legacy-F protocol2 wire, all parent/publication/source evidence, bootstrap,
   Note membership/source revision, and a dense account prefix from a trustworthy
   import high-water. Require a genuine `import_remote / captured / active`
   binding. Reject Content-F, any prior Metadata genesis evidence, any gap, any
   ambiguous/truncated import history, unrelated unsupported material, or
   anything earlier than the candidate.
2. Select only the earliest eligible pending event. Authenticate its exact
   original encrypted Metadata protocol3 event and descriptor. Require coverless
   `create`, revision 1, generation 1, empty parents, same project/bootstrap,
   peer source, and no existing Metadata owner. Ask the real imported Metadata
   owner to prepare its opaque plan from null head; never synthesize an owner
   proof or applied inbox row.
3. Bind an opaque plan to its issuing private factory, real owner handle, exact
   scope, auth/key/profile/device/session/epoch, original wire and complete
   pre-state. Authenticate the predicted null-to-genesis head and selected
   inbox-applied proof while leaving durable rows in their original received
   state. Reauthenticate F/source against the predicted state; preserve all
   original and retained Note outcomes.
4. Commit through one native IndexedDB read/write transaction spanning the ten
   recovery stores, with full pre-state CAS inside that transaction. Change only
   the new Metadata owner head and selected inbox applied proof. Do not change
   `source_revision`, project membership, local Project/Note records, F/H
   history, cursors, outbox, receipts, or unrelated rows. Keep crypto and awaits
   outside IDB callbacks. Recheck identity and lifecycle throughout to block tab
   races and revocation.
5. Reload and verify actual durable state. Report explicit
   `commitMayHaveOccurred`/equivalent uncertainty after native completion; never
   claim rollback. Exact replay must authenticate the single real genesis and
   produce zero duplicate writes. A crash after owner commit but before cursor
   commit must resume from the durable owner proof.
6. Commit the historical proven prefix separately, under a newly authenticated
   complete inventory/CAS. Only the exact proven cursor may change. No ACK,
   capabilities, readiness, network publication, or production scheduler
   authority follows from either commit.

The probe shows the required state transition is representable by existing
records and owner APIs; no new schema or wire field is indicated. The full
implementation must STOP for contract review if import high-water/source
lineage cannot prove the no-genesis range, or if a new durable proof, migration,
wire format, server contract, or cryptographic assertion is found necessary.

## Status and roadmap

C21.2.19 is **AUDIT COMPLETE / NO PRODUCTION IMPLEMENTATION**. The genuine
Legacy-F no-head baseline is proven for the bounded high-water-0 imported cohort;
Content-F no-head create is incompatible and remains rejected. Current
`unsupported_create_baseline` stays intact until C21.2.20 independently proves
and implements the private admission contract.

C21.2.11 remains historically partially resolved, not CLOSED. C21.2.08 remains
NOT CLOSED; C21.1.06 remains NOT LOCAL COMPLETE. C21/C21.2 stay IN PROGRESS; Web
progress **89.36%**; `ready=false`; registration CLOSED; PUBLIC RELEASE BLOCKED.
VPS/landing summaries and the permanent CI/CD release policy are unchanged.
No stage weight or completion credit is added by this audit.

For this docs-only commit, Cloud and SQLite are **NOT EXPECTED** under current
path filters (`docs/web/**` is not selected). No workflow was triggered or
polled.
