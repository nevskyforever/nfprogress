# C21.2.08Z2B1 — shared local Note source transition

**Local implementation slice only.** The accepted Z2A atomic second-project
replay contract remains the authority for a future batch owner. This stage does
not import B or qualify its history in Q.

`BrowserLocalAuthorityRuntime.preparePeerSource()` now calls the private pure
`planPeerSourceTransition()` in `localAuthority.ts`. Given a validated opened
local source, its source revision and an owner-authenticated Note plaintext, the
function checks account/device/project identity, the prior source revision and
membership, validates the Legacy2 or Content3 local Note route, and computes
the next project payload and Note source. A peer Note retains local mutation
revision 0; the project source revision advances once. Existing 4000-member
and safe-integer limits remain. The unchanged local canonical encoder enforces
the 8 MiB source limit before either encrypted record is written.

The three existing owner paths use this function through `preparePeerSource()`:
Legacy/Content ordinary Note apply, Resolution continuation Note apply, and
V10 ordinary Note apply. The function has no exported entry point and cannot
mint a source token or durable write. `preparePeerSource()` still requires the
genuine `LocalSourceToken` and authenticated Note owner token, opens the exact
durable encrypted source, checks auth/key lifecycle, seals the original record
formats, and mints the old `ProtectedNoteSourcePlan`. Its commit still performs
the original source CAS and paired project/Note/inbox/history transaction.
No virtual source path is exposed in this slice.

Focused Vitest covered Legacy2 create/update/delete, Content3 and the existing
single-event rollback paths, plus deterministic reopened source projections,
the 8 MiB boundary, lock/logout during preparation and rejection of an opaque
unverified caller. TypeScript typecheck, production build and ESLint on the two
changed frontend files passed locally. No Chromium batch replay is claimed.

**Next minimum stage: C21.2.08Z2B2.** Extract the Note causal/candidate/proof
planning from `BrowserLegacyNoteApplyRuntime.prepareRoute()` so its existing
single-event path and a future private virtual B inventory can share it.
`prepareRoute()` still reads durable per-Note history and calls the protected
source owner; it cannot yet plan a complete B replay in memory. The future B
owner must separately establish authenticated registry/full-history evidence,
private virtual-source admission, full-inventory CAS and one DB10 commit before
any Q source capability is possible. `ready=false`, `declarationAllowed=false`,
`writerAuthorized=false`, registration CLOSED, PUBLIC RELEASE BLOCKED and all
C21/C22/C23/PF6.0/RC gates remain in force. Official Web progress: 89.36%.
