# C21.2.08Y — Legacy3 independent O owner and Q mixed prefix

## Status and baseline

**LOCAL COMPLETE / REMOTE ACCEPTANCE PENDING.** Y starts from exact clean branch
`6.0` baseline `9ca8ba10838ebf891531d72da51308f35fc28c31`. W-CI1 bounded G is independently
**REMOTELY ACCEPTED** at `dc5cad87e9bf07b6d529e702ecdeaad988d3a5cf`, Cloud
`40116362152`, SUCCESS 6/6 on the first attempt. The original W randomized
ciphertext-test failure remains historical. X remains **AUDIT COMPLETE**.

Y implements only genuine remote-authored independent ordinary Notes in the same
project and bootstrap as one accepted first-generation Legacy3 F Resolution. It
does not add a production scheduler or sync composition. DB10, all twelve stores,
Resolution4/Proof1/inbox10, Candidate2/Head1, Head2, backend, API, wire, AEAD,
digest and proof formats are unchanged.

## Private O and Q authority

O now owns a distinct one-use `OHistoryToken`. The request is stored in a private
`WeakMap`, bound to the exact runtime, scope, complete captured inventory, AMK
lease and live auth/key/device/profile predicate, and deleted on consumption or
failure. Its consumer runs the existing strict Resolution authentication and
continuation core, then the existing complete mixed-source fold. O repeats that
composition over its predicted post-state before it returns a write plan.

Q separately owns a one-use `QHistoryToken` and private request map. Only
`bindMixedSources()` inserts a runtime into the module-private Q `WeakSet`; no
constructor flag, mutable property or public `allowLegacy3` discriminator exists.
Q independently authenticates F, H and every O record, reconstructs F's encrypted
R0 baseline and each H/O source revision, validates membership/current encrypted
projections and authenticates Metadata/Stage/StageOrder through their existing
owners. O success does not mint Q authority. H and G tokens cannot enter O or Q,
Q cannot enter O, and a failed Q path has no G fallback.

The public `authenticateContinuationHistory()`, public mixed validators, default
G, default K, private Metadata owners, readers, ACK and readiness gates retain
their original Legacy3 guards. The explicitly dormant mixed-recovery composition
uses Q first, pins the same full inventory, and only then selects H versus O from
the authenticated root identity. Default K remains unchanged.

## Supported O history and atomic writes

O accepts Legacy2 ordinary Notes and framed Content3 ordinary Notes with genuine
Metadata/Stage prerequisites. Both Content compression IDs are covered. Supported
same-F-project operations are independent create, linear update, delete, later
delete from an authenticated tombstone, and later accepted linear descendants.
A create requires null parent, revision 1, no Head1/candidate/local identity and a
genuine received remote event. Update/delete requires the exact single-tip Head1,
published parent Candidate, next Note revision, preserved route and next project
source revision. Original and retained H identities remain Head2-only.

O continues rejecting own-device/local authorship, raw Legacy received3, another
project's ordinary Note, a second Resolution, non-earliest received work, missing
or future parents/dependencies, wrong route/bootstrap/membership/revision, Head
substitution, independent conflicts, cross-project identity collisions and
tombstone resurrection. Source snapshot comparison is order-independent by Note
ID; the encrypted records and membership still have to match exactly.

The accepted O transaction writes only the encrypted local project, encrypted
local Note/tombstone, genuine ordinary Candidate, Head1 and existing Legacy2 or
Content3 inbox proof. It retains the complete ten-store inventory CAS, identity
and binding checks, local-source CAS and native IndexedDB atomicity. It never
changes F/Head2 authority, cursors, ACK, ordinal, outbox, receipts, bindings,
capabilities or server state.

## Q prefix and cross-project boundary

Q preserves dense sequence scanning, exact family counts, `keep_both` as one F
sequence, earliest `missing_sequence`/`unproven_family`, and cryptographic failure
as terminal rejection. Preparation and calculation are read-only. Commit changes
only `cursors.proven_prefix`, after a full ten-store CAS and lifecycle recheck,
with `advanced`, `already_proven` and `no_progress` reconciliation. It exposes
`ackAuthorized=false` and performs no HTTP or ACK.

Authenticated Metadata, Stage and StageOrder events from another project may
qualify through their existing owners. Another project's ordinary Note remains
unqualified because Y has no independently authenticated source baseline for that
project. Its row stays in account order and blocks the prefix. Y never reuses the
F project's R0 for another project.

## Native acceptance and compatibility

The final Y browser mode uses genuine F and H producers, then real O
create/update/delete transactions and a separate Q prepare/calculate/commit. Eight
persistent profiles cover all four F strategies and both ordinary protocols; the
Content cases exercise both compression IDs. Results: 24 O commits, 48 protected
O rollback injections, 40 Q rollback/lifecycle injections, 8 Q cursor advances,
8 Y process/disk restarts, 8 old-W reader copies and 8 same-copy Y recoveries.
Injected successful Q commit followed by lost completion is reconciled from the
durable cursor. These checks simulate transaction/process interruption, not OS
power loss.

The exact W-CI1 bundle at `dc5cad87e9bf07b6d529e702ecdeaad988d3a5cf` is built
from `git archive`. On closed disposable copies containing genuine new O/Q data,
old O, G, Q and mixed-recovery paths reject semantically, without TypeError or
missing-method acceptance, and all twelve stores remain byte-identical. The new Y
bundle reopens each same copy, reauthenticates O/Q and returns Q `no_progress`.
Old and new bundles never open the same profile concurrently.

Preserved native regressions pass: bounded Legacy3 G plus exact old-U rejection,
and original F2/Content3 F/H/G/Q. The full persistence suite, including all 15
v9-to-v10 cohorts, passes with zero page errors.

## Validation and CI capacity

| Final check | Result | Wall time |
|---|---:|---:|
| Mandatory Foundation command | 81 PASS / 2 files | 8.64s process; 8.40s Vitest |
| Affected F/H/G/Q/K/O/private/readiness/migration specs | 1,201 PASS / 25 files | 234.12s |
| Y O/Q Chromium plus exact old W | PASS / 8 profiles | 37.17s |
| Preserved Legacy3 G plus exact old U | PASS / 8 profiles | 27.14s |
| Original F2/Content3 G/H/Q | PASS / 8 profiles | 18.36s |
| Native persistence and all 15 v9-to-v10 cohorts | PASS / page errors 0 | 159.44s |
| Typecheck and production build | PASS | Vite 0.824s |
| Acceptance harness build | PASS | Vite 0.090s |

Foundation receives only `legacy3Prefix.spec.ts` and the new
`legacy3OrdinaryPrefix.spec.ts`. Against the accepted 20m07s CI1 runtime, the
authorized 8-minute increment and 5-minute reserve total 33m07s, below the 40
minute limit. Content-action receives the reused Y Chromium mode and pinned old-W
build. Against 22m35s, the 8-minute increment and 5-minute reserve total 35m35s.
The measured local Y command is 37.17s plus the 0.084s old-bundle build. Frontend
admin and complete-project receive no Y suite. All six jobs and 40-minute limits,
original tests and blocking behavior remain.

The changed workflow, source, test and script paths select Cloud. The actual
SQLite path filters do not select this diff. Independent Cloud SUCCESS 6/6 on the
published Y SHA is required before Y can be remotely accepted. No Actions polling
or next-slice work follows publication.

## Remaining gates and next slice

Y does not support ordinary Note qualification from a second project. A separate
authenticated source baseline and complete fold is required. After independent Y
remote acceptance, the recommended next narrow slice is **C21.2.08Z — cross-project
ordinary Note source-witness contract audit**. It must begin as an audit and cannot
infer a second-project baseline from the accepted F project.

C21/C21.2 remain **IN PROGRESS**; C21.2.08 **NOT CLOSED**; W remains **PARTIAL**
with bounded G remotely accepted and its old Q STOP retained as history; T/U are
**REMOTELY ACCEPTED**; V/X are **AUDIT COMPLETE**; C21.2.11 is **PARTIALLY
RESOLVED**; C21.1.06 is **NOT LOCAL COMPLETE**. Official Web progress remains
**89.36%**, `ready=false`, `declarationAllowed=false`, `writerAuthorized=false`,
registration **CLOSED**, and **PUBLIC RELEASE BLOCKED**. C22/C23/PF6.0/RC,
VPS/landing, permanent CI/CD policy and every security/release gate are unchanged.
