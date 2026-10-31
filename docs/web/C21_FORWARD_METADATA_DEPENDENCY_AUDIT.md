# Forward Metadata dependency audit

Baseline: `eeeb4f276778084b40f28e417ea2b5fd03ebf9b5`, branch `6.0`.
Outcome **A: retain fail-closed refusal; do not expand replay v5**.
This is a source/history audit, not a production implementation or a capability
qualification. It concerns only Stage2 referencing Metadata3 in the same
account feed. It makes no general claim about other orphan/Resolution cohorts.

## Writer invariant and evidence

| Boundary | Audited production evidence | Consequence |
| --- | --- | --- |
| Select dependency | `frontend/src-tauri/src/stage_sync.rs::header` obtains `metadata_event_id` from `metadata::authority_view`, requires state `active`; `capture_candidate_tx` uses the same active head | No caller-selected future UUID is used by the ordinary Stage writer |
| Queue Stage | `stage_sync.rs::prepare_tx` calls `dependency` before inserting the structural event/outbox; explicit migration `begin`, decision and ordinary `prepare_local_stage_change` paths use this boundary | Queueing requires the exact nondelete Metadata event in `applied`/`conflict_preserved` state joined to `cloud_sync_metadata_apply_ledger`, plus active authority |
| Establish Metadata authority | `project_metadata_sync.rs::preserve_authenticated_event_checked` reads the original Metadata inbox event and retained ciphertext, validates identity, and commits tips/projection/ledger; own echo requires its real receipt or reconstructs it from the authenticated server echo | A prepared, sealed or merely accepted pending Metadata candidate is not the applied dependency needed to queue Stage |
| Publish | `StageStructuralRuntime.uploadOnce` uploads only native pending structural rows and commits their receipts; `NoteSyncV3Cycle` uploads Metadata before structure | The cycle order helps, but the earlier native dependency check is the decisive invariant even if these calls overlap |
| Assign sequence | `backend/app/cloud/services.py` encrypted push allocates increasing account sequences for new events; exact duplicates return the original sequence and changed duplicates reject | Metadata already present on the server cannot acquire a later sequence than a newly accepted dependent Stage |

Thus, for a supported writer and the existing server history model:

`server accepts Metadata M → authenticated Metadata apply/ledger → Stage S queued with M → server accepts S`.

Consequently `sequence(M) < sequence(S)`. Stage2 → Metadata3 contradicts this
necessary causal construction. This proof does not assume the server can inspect
the encrypted dependency; it follows the client's authority boundary. As in the
existing source/proof contract, malicious server rollback/equivocation or
tampered native storage is outside the supported-history premise.

## Offline, concurrent edits and restart

Offline Metadata edits can remain frozen pending candidates. They do not become
an active applied head simply because local saving succeeded. New Stage work
either fails the active-authority/dependency check or references an already
authenticated older head; it cannot substitute the future candidate ID.

If an unrelated Metadata edit is prepared after Stage, Stage retains its earlier
dependency rather than retroactively referencing the newer revision. Native
transactions pin candidate/head and write outbox state atomically. Sealing and
retry retain the frozen event/header; receipt confirmation and lost-response
self-echo preserve event identity and its original server sequence. Restart
does not regenerate the dependency. Multi-device reception likewise needs the
Metadata apply ledger before using that event as a Stage source dependency.

The browser's `localStages.ts` is encrypted local CRUD, not a cloud structural
writer. Browser replay owners are readers and cannot manufacture this published
history. `stageCodec.ts` can seal a caller-supplied frame, but that low-level
cryptographic helper does not grant production writer authority.

## Historical versions and migrations

The first structural substrate, `d0ba4b12`, already required the same exact
Metadata event/apply-ledger join in `dependency` and checked it before queueing.
The integrated ordinary writer at `a9f175ef` retained that gate and selected the
active head. Subsequent revisions of `stage_sync.rs` add integration, native
families and compression; the dependency boundary remains present. Before that
substrate there was no supported encrypted Stage writer producing these frames.
Legacy Notes transport does not imply an earlier Stage publisher.

SQLite migrations 025–029 define the Metadata ledger, authority, structural
and integration tables; they do not seed fabricated applied Metadata evidence
from unsent local values. The explicit Stage migration captures local stages
only against active Metadata and queues through the same check. Metadata import
history derives from the server and does not turn a local unsent candidate into
a server dependency. No audited supported older path provides an exception to
the sequence inequality above. No new schema or protocol migration is needed
to retain refusal.

## Meaning of the previous regression

`replay-structural-fixture.mjs`, variant `late_metadata_dependency`, clones an
authenticated Metadata genesis, allocates the later update ID, seals a Stage
with that future ID and calls raw push for Stage before pushing the update.
It uses real encryption/codecs and a real authorized server, but **bypasses the
production structural candidate/authority/outbox writer** by construction.
It is an artificial negative test of a semantically invalid dependency order.
AEAD validity and server transport acceptance do not prove supported client
provenance. The server's opaque-content boundary is not a reason to weaken it
by inspecting plaintext dependencies.

Distinguish three cases: a valid supported writer history obeys dependency
order; a changed/truncated/tampered history is a corruption/incompleteness
failure; this fixture has intact ciphertext and a complete feed but an invalid
semantic ordering. Reader rejection is correct in all unsupported cases, though
their diagnostics need not be identical. The previous HTTP/Chromium result
remains valid evidence of refusal, wire preservation and restart behavior, not
of a missing production recovery feature.

## Decision and remaining work

Keep `missing_history` and v5's requirement for earlier Metadata proofs. Do not
reorder owner application, invent a proof, rewrite server sequence or introduce
a v6 schema for this scenario. The prior conditional proposal for staged
forward proofs is not required for supported writers and is not an active
implementation recommendation. The regression remains a negative security
boundary check. It does not close the broader orphan-readiness checklist.

Other supported dependency/recovery scenarios need their own evidence if later
selected. No next slice is started by this audit. E2EE/zero-knowledge,
`ready=false`, `declarationAllowed=false`, `writerAuthorized=false`, Registration
CLOSED, PUBLIC RELEASE BLOCKED and official progress **89.36%** remain.

Verification: current baseline/tracking/remote branch and clean tree checked;
production call paths, earliest substrate/integration history and SQLite
migration source inspected; documentation links, diff and maintained quick
checks run. The already passed HTTP/PostgreSQL/Chromium and owner tests were not
repeated and are not reported as new runtime acceptance.
