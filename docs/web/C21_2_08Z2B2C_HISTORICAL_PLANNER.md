# C21.2.08Z2B2C — authenticated historical Note planner

**Stage COMPLETE; overall Z2B2 remains PARTIAL.** The owner states that Z2B2 Cloud run `40277351544` was independently accepted, 6/6 SUCCESS. No Actions result was queried in this stage.

## Extracted historical path

The existing authenticated `BrowserLegacyNoteApplyRuntime.prepareRoute()` now calls three module-private functions in `legacyNoteApply.ts`:

- `planHistoricalLegacyCandidates()` authenticates retained Candidate ciphertext and frozen local versions, reconstructs the exact initial Legacy cohort from the accepted outbound event, validates earlier applied Legacy proofs and self-echo receipts, and reconstructs missing historical peer Candidates from original wire and proven outcome. It never derives a historical Candidate from the current Note source.
- `planHistoricalContentJoin()` joins an already authenticated Content3 proof and its owner-minted Metadata/Stage prerequisite certificate to the retained Candidate and the existing transport replay hook. The owner still calls `verifyStoredContentNoteProof()` or `verifyStoredContentConflictProof()` and `prepareNotePrerequisite()` first.
- `verifyHistoricalLegacyReplay()` verifies an already proven Legacy event, including exact receipt for self-echo and the encrypted wire/proof digest, before the existing replay plan is minted.

`planCausalHead()` from Z2B2 still reconstructs Head from validated prior applied/outgoing evidence. The ordinary single-event Legacy2 and Content3 routes call this historical planner; no parallel replay algorithm was added. The functions calculate over owner-supplied, validated inventory and do no IndexedDB writes. Original encrypted wire, account/device/lease, durable reads, Content3 dependency authentication, private token creation and the single-event CAS transaction remain with the owner.

## Scope and remaining contract

For the narrow clean B contract, the shared historical calculation can account for initial backfill, proven ancestors, accepted self echoes, Content3 historical joins, replay and Head reconstruction. A future private owner must still establish full-history/registry evidence and feed an authenticated virtual inventory, then use a virtual local source, one prepared fold and one DB10 commit. No such owner, virtual source entry, batch transaction, Q handoff or sync capability exists here.

Z2A explicitly excludes unresolved forks and local-unsealed branches from the clean B cohort. A separate extraction of the conflict-preservation branch is therefore **not required** for that narrow implementation if the future owner rejects every unsupported conflict before commit. Existing conflict behavior and Resolution generations remain unchanged. Broader conflict replay would require its own contract and tests.

## Verification and CI capacity

Seven existing Vitest files passed locally (297 tests): initial capture, Legacy apply, Note history, conflict history, Content apply, transport gateway and the Z2B2 causal planner spec. They exercise genuine producers, cohort/backfill, Candidate/Head, replay, self-echo receipts, missing history, corrupted proof/wire, Content3 prerequisites, conflicts, lifecycle invalidation and atomic rollback. Typecheck, production build, changed-file ESLint and `git diff --check` passed. No test assertion or workflow was changed.

The only measured Frontend admin duration available from the preceding accepted run is **37:27 / 40:00**, leaving 2:33 in that run; current accepted run headroom was not queried. This stage adds no CI test or job. Existing mandatory six jobs, coverage, filters and timeout remain unchanged.

Web progress stays **89.36%**. `ready=false`, `declarationAllowed=false`, `writerAuthorized=false`; registration CLOSED and PUBLIC RELEASE BLOCKED. C21/C22/C23/PF6.0/RC gates remain mandatory.

**Next minimal slice:** a private virtual source/inventory seam for the clean B fold, with fail-closed conflict rejection, before any atomic B owner or commit. Recommended GPT-6 Sol / Medium because it spans authenticated inventory and causal source state without changing crypto or protocol.
