# C21.2.08Z2B2 — shared Note causal planner slice

Status: **PARTIAL**. The prior Z2B1 Cloud run `40242607000` was independently accepted by the owner (6/6 SUCCESS). This slice changes no public Note capability or release gate.

## Extracted from the existing one-event owner

`BrowserLegacyNoteApplyRuntime.prepareRoute()` now calls private functions in `legacyNoteApply.ts` after account/key lease, durable inventory, wire decryption, history authentication and Content3 prerequisites:

- `planCausalHead()` reconstructs the current head from authenticated applied/outgoing evidence when a retained head is absent.
- `verifyOwnCausalAdmission()` retains the exact self-echo receipt, candidate and same-revision checks.
- `verifyCleanPeerCausality()` checks initial create isolation, exact parent/revision, projection digest and accepted non-peer ancestor evidence over the owner-supplied Note source image. It has no IndexedDB reads or writes and can consume a future private virtual image.
- `planCleanCandidateProof()` builds the existing Legacy2 or Content3 Candidate/Head transition and outcome proof after the genuine protected local source projection is prepared. Content3 still uses `prepareNoteTransportCommit()` and its opaque `ownerHeads` hook; Legacy2 still uses `makeHistoryCandidate()`. Existing validators and digest helpers remain authoritative.

The ordinary Legacy2 and Content3 create/update/delete paths use these functions through the same `prepareRoute()` and `commit()`. The existing `planPeerSourceTransition()` remains the only local source transition calculator. The new helpers are module-private and cannot mint or commit a capability. Authentication, account/device/key lifecycle, Metadata/Stage proof, original wire, conflict proof, private plan tokens, source CAS, history CAS and the single IndexedDB transaction remain with their existing owners. A caller-supplied virtual inventory grants no durable write.

## Checks and CI capacity

The focused Legacy2/Content3/history/transport Vitest selection passed: 5 files, 263 tests. The new planner spec passed: 3 tests covering genuine-producer create/update/delete Candidate/Head evolution, exact replay, orphan rollback and refusal of a fabricated virtual inventory as commit capability. Typecheck, production build, changed-file ESLint and `git diff --check` passed. Existing suites additionally cover self-echo, conflict preservation, malformed ciphertext/proof, account/key invalidation, bootstrap/project mismatch and transaction rollback; they were run without changing their assertions.

The last accepted Cloud run's six jobs completed successfully. Their observed durations were 2:15 (Android), 20:58 (foundation), 14:58 (content-action), 22:57 (complete-project), 37:27 (Frontend admin), and 3:14 (cloud/legacy). Frontend admin had 2:33 before its 40-minute limit. Only the new short Vitest spec was added to its existing contract-test command. Mandatory jobs, filters and coverage remain unchanged. No Chromium batch replay was added.

## Remaining work before atomic B replay

The conflict-preservation branch still constructs group members, frozen local versions, Content3 conflict candidates/proofs and head transitions inside `prepareRoute()`. Historical applied/replay joins and the first-use backfill loop also remain owner-local. They must be made compatible with an owner-authenticated virtual inventory before the future B owner can fold multiple Notes. The Z2A decision also requires one private virtual source and one batch IndexedDB commit with CAS, rollback and Q handoff; none exist here. Therefore **Z2B3 is not yet ready**. The next minimum slice is completion of Z2B2's conflict/historical planner extraction, recommended model GPT-6 Sol / Medium because it affects causal conflict proofs.

Web progress remains **89.36%**. `ready=false`, `declarationAllowed=false`, `writerAuthorized=false`; registration CLOSED and PUBLIC RELEASE BLOCKED. C21/C22/C23/PF6.0/RC and reader/writer gates are unchanged.
