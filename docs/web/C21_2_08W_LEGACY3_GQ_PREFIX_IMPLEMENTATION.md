# C21.2.08W — Legacy3 G/Q prefix implementation and CI capacity gate

## Preflight and capacity decision

**PARTIAL — bounded G locally accepted; Q IMPLEMENTATION STOP. W is NOT LOCAL COMPLETE; independent remote acceptance of the bounded G implementation remains pending.** Clean branch `6.0`, HEAD,
`origin/6.0` and actual remote matched `9000a96fbd905a58d3971f7ab9f2e81c5e9eb24f`.
Protected engine/game_data Python 3.12 bytecode hashes match the U/V baseline.
V is AUDIT COMPLETE; it is not implementation acceptance. T remains REMOTELY
ACCEPTED (Cloud39940501426 SUCCESS6/6). U is REMOTELY ACCEPTED on
`22b68493daf304c219bed14f0d8598d65fcc1ee8`, Cloud40015205669 attempt2 SUCCESS6/6.

Before production changes, the accepted U job/step timestamps and Frontend admin
logs were inspected through the GitHub API. Final accepted job durations:

| Mandatory job | U runtime | Proposed new ownership |
|---|---:|---|
| Foundation | 16m28s | Isolated new Legacy3 G/Q unit/security tests only |
| Content-action | 14m49s | New native Legacy3 G/Q Chromium/restart/old-U acceptance |
| Complete-project | 31m29s | Existing coverage unchanged; no W additions |
| Frontend admin | 35m38s | Existing coverage unchanged; no W additions |
| Regressions | 2m49s | Unchanged |
| Android | 2m20s | Unchanged |

The successful foundation/content-action results were carried forward from the
first attempt; complete-project reran successfully in attempt2. The earlier
complete-project timeout remains historical evidence and required no code repair.
Attempt1 job120625387541 spent26m21s installing native system dependencies; the
same step took26s in the successful retry. The cancelled job lasted40m19s including
termination overhead at its40m limit.
The six mandatory jobs and each 40-minute limit remain fixed.

Measured Linux representative incremental work, from accepted U job120798752365:
Legacy3 H96 unit step27s, mixed-prefix71 unit step187s, native Legacy3 H including
pinned old bundle43s, original G native38s, full O/H/Q/K native511s. Chromium
installation22s, harness build1s and preview1s. These are real Ubuntu runner
measurements, not an extrapolation solely from Mac timings.

**Selected partition:** foundation gets isolated new tests with an 8-minute
increment envelope (twice the measured 214s representative unit workload fits
within480s). Content-action gets the isolated native W mode, Chromium/harness/
preview and pinned old-U build with a 12-minute increment envelope (measured
representative native/setup total616s, including the substantially broader
O/H/Q/K runner; allocate720s). Actual new workload must be reviewed against these
envelopes after implementation; overruns require STOP/repartition, not acceptance
removal or timeout increases.

Planning equations with at least5m reserve: foundation16m28s +8m +5m =29m28s;
content-action14m49s +12m +5m =31m49s, both below40m. No existing acceptance is
relocated or duplicated. Both receiving shards already have Node20.19, `npm ci`,
Rust/native bridge, Linux system libraries and the same repository sources.
Content-action additionally needs the exact existing pinned Playwright install,
Vite harness/preview and disposable archived old-U bundle steps. Browser tests use
isolated persistent profiles and do not use the backend database. All additions
remain blocking and selected by stable shard conditions; no optional/skip flags.
Original Cloud path filters and six-job coverage remain unchanged.

This decision completes W's first mandatory gate before production changes.

## Bounded G implementation

G now independently authenticates one genuine first-generation received3 /
`legacy_resolution_v2` F root using the actual original encrypted Resolution and
Resolution4/Proof1/inbox10, published parents, source-before/source-after and F
closure. All four strategies qualify. Original H descendants and the distinct
retained `keep_both` identity support accepted Legacy2 and framed Content3 ordinary
children (ID0/ID1), subsequent permitted deletes and later descendants. Unstaged
Legacy HTML source restrictions are preserved. Real pre-F Metadata/Stage/StageOrder
family owners and an unrelated project's Metadata event participate in the full
account prefix; family evidence is not fabricated or inferred from encrypted
source alone. This does not add post-F structural source routing.

`resolutionHistorical.ts` factors its existing strict authenticated-history work
into a private shared helper. H and G each have their own owner-bound, one-use
WeakMap requests. Only the matching JavaScript-private runtime method can mint a
request from its loaded complete inventory and active key lease. H grants cannot
enter G, G grants cannot enter H or Q, and wrong/reused/expired requests reject.
Both successful and failed requests are deleted. The Q/default entry discriminator
is now a JavaScript-private readonly field; assigning caller-visible `mixedSources`
or `allowLegacy3` properties cannot change entry authority. Generic historical
readers retain `rejectLegacy3ResolutionRoots` unchanged.

G source selection detects post-F independent Note history before qualifying it;
a Legacy3 history needing Q is rejected under G. Default F2/Content3 G and explicit
Q retain their existing authentication and mixed-source semantics. No H diagnostic
or caller-readable result becomes a prefix/commit capability.

## Prefix calculation and exact write set

Every retained sequence1..pull_cursor must independently qualify. Result fields
remain `current_proven_prefix`, `candidate_proven_prefix`, `pull_cursor`,
`first_blocking_sequence`, `blocker`, exact family `counts`, `readOnly=true` and
`ackAuthorized=false`. F `keep_both` counts as one Resolution sequence. Original
and retained descendants have their own event sequences. G stops at the earliest
missing row (`missing_sequence`) or present but unqualified row (`unproven_family`),
including an authentic unresolved H sibling. It never jumps over an unrelated
project, unsupported transport/family or missing dependency. Failed cryptographic
preparation returns no invented blocker; corruption inside an already claimed
proven prefix rejects without reset.

The existing native commit algorithm is preserved: fresh calculation/certificate,
exact complete ten-store inventory comparison inside IndexedDB, current auth/key/
device/profile checks and cursor relations. The sole write is replacement of
`cursors.proven_prefix`. Pull/ACK/local ordinal, encrypted projects/Notes, F/H
history, inbox, owners, outbox, receipts, registration and capabilities stay exact.
`advanced`, exact same-plan `already_proven`, and fresh `no_progress` retain their
meanings. Request grants are one-use; exact commit replay remains deliberately
idempotent under the existing complete-inventory comparison.

## Q source-authority STOP

**Q is not implemented or accepted for Legacy3.** It retains its generic root
barrier and receives no new private grant. The existing mixed validator can only
qualify independently owned/applied source history after complete order/membership/
revision validation. The accepted browser O producer/owner cannot produce that
history after a Legacy3 root: `v10OrdinaryApply.ts` calls
`validateMixedSourceInventory` and `authenticateContinuationHistory`, both of
which retain the Legacy3 barrier. H only changes the original/retained F outputs;
it cannot be used as an independent Note owner.

A new test supplies a genuine encrypted independent Content create, ingests it,
and invokes the actual O and Q owners. Both reject without durable changes. A
successful H/G history is not evidence that the independent source was applied.
Constructing positive applied records, rewriting an older F2 root, passing H/G
history into Q as a grant, or bypassing O's guard would invalidate acceptance.
Activating O is explicitly excluded by W. Therefore the source-owner authorization
and genuine mixed producer/consumer acceptance are a separate prerequisite, even
though no new schema/proof/crypto requirement has been established.

This is the permitted bounded-G / Q-prerequisite STOP from W sections3/6/14. No Q
success, full W LOCAL COMPLETE, complete-reader acceptance or remote acceptance is
claimed. Recommend separately authorized **C21.2.08X — Legacy3 independent-source
owner and Q composition contract audit**, after independent bounded G acceptance.
Do not start it automatically or retry Metadata create.

## Downstream and compatibility boundaries

Default K, mixed K, O, private Metadata apply/handoff/prefix and terminal Metadata
retain their strict root guards. The original C21.2.11 negative boundary passes.
No new Resolution generation, raw Legacy ordinary-on3, implicit resurrection,
unpublished own source or missing/cold dependency is authorized. The negative-only
readiness inspector can report G's authenticated bounded inventory but still
returns `ready=false`, `declarationAllowed=false`, `writerAuthorized=false`,
`serverGate=not_checked` and its existing complete-reader blockers. It has no
capability/ACK/writer action. Production orchestration remains absent.

Existing DB10/twelve stores/indexes, Resolution4/Proof1/inbox10, ordinary proofs,
Head2/Transition2, wire identity, digest preimages and AEAD remain unchanged. No
IndexedDB migration, durable proof version, backend, PostgreSQL, wire or crypto
change is required for bounded G. Old U can still authenticate its accepted H
history, rejects Legacy3 G/Q/recovery/private-prefix work, and preserves the new
cursor together with all encrypted evidence. Reopening the same closed profile
copy with W reauthenticates and safely returns no progress. There is no downgrade,
reset or simultaneous old/new writer.

## Local acceptance and CI integration

Final unit inventory is recorded below without summing overlapping reruns. Test
producers use actual F commits, H commits and genuine existing family owners;
negative-only corruption is isolated in disposable data. The U/T negative G
expectations are superseded narrowly by explicit read-only G success assertions;
all other negative downstream cases remain.

The new61-case `legacy3Prefix.spec.ts` is mandatory in foundation only. Native W
runs in content-action only, using the shared pinned Chromium/harness/preview and
a disposable `git archive`/build of exact U SHA. All old acceptance categories,
including actual old-T/old-v10, remain in their original jobs. Before/after YAML
comparison verifies the complete original step/test multiset, matrix, conditions,
Cloud filters and six expanded mandatory jobs with40m limits. Only three setup
steps additionally run in content-action; no acceptance is relocated, removed,
skipped, optional or masked by `continue-on-error`.

Observed local W native runtime remains far below the12m planning envelope; this
is corroboration alongside the measured616s Linux representative superset, not a
claim of measured W Cloud time. External dependency downloads remain variable;
the original timeout is retained and does not permit a coverage waiver. Independent
Cloud SUCCESS6/6 on the published bounded-G implementation SHA is still required.
No Actions polling or waiting follows publication. The final source/scripts/
workflow paths select Cloud; SQLite's enumerated filters do not match.

### Validation record

- New Legacy3 G tests: all strategies, Legacy2/Content3 ID0/ID1, real H descendants,
  real pre-F family owners/unrelated project, exact family counts, cursor-only
  commits, replay, earliest gaps/forks, root/proof/AEAD/role/source/member/bootstrap
  corruption, full CAS, lifecycle, private token/cross-owner/mode isolation,
  resource bounds, negative-only readiness and Q's actual O-owner prerequisite.
- Native W:8 genuine F/H profiles,8 root-only calculations,16 post-H calculations,
  8 confirmed cursor advances,6 exact same-plan idempotent retries,2 lost-completion
  reauthentications,2 prepared-process stops,10 cursor transaction rollbacks,
  8 stale full-inventory rejections,1 native identity rejection,1 competing tab,
  8 missing-sequence and2 fork barriers. Full browser/process/disk restarts use
  fresh runtimes;8 isolated actual old-U copies reject8 real unauthorized routes
  and8 same-copy W recoveries pass with complete durable snapshot preservation.
- These injected native failures and browser termination checks are not an OS
  power-loss guarantee. Successful native commit followed by lost completion is
  confirmed by durable reauthentication, never reported as rollback.

Final unit inventory: **1,016 cases across21 distinct spec files**, failures0,
skips0. Overlapping prefix reruns are not added to this count.

| Final check | Result | Wall time |
|---|---|---:|
| Exact new CI unit command, one worker | 61 PASS | 4.97s process /4.64s Vitest |
| New G plus T/U/readiness/Stage-prefix regressions | 291 PASS /6 files | 12.05s |
| Affected F/H/J/G/Q/K/O/private/.11 regressions | 725 PASS /15 files | 151.20s |
| Final G/Q prefix rerun (overlaps rows above) | 199 PASS /3 files | 66.18s |
| W G native, actual old U and recovery | PASS /8 profiles | 26.44s |
| U H native plus actual old T | PASS /8 profiles | 20.74s |
| T Legacy3 F native plus actual old v10 | PASS /4 strategies | 7.40s |
| Original F2/Content3 G/H native | PASS /8 profiles | 18.45s |
| Original F2/Content3 F native | PASS /8 profiles | 8.73s |
| Native persistence and migration, including15 v9→v10 cohorts | PASS /page errors0 | 161.54s |
| Typecheck /production build /acceptance harness | PASS | typecheck not separately timed; Vite0.906s /harness0.088s |
| Node syntax, workflow syntax/coverage/filters, diff/scope/history and bytecode | PASS | — |

Exploratory failures were confined to fixture/expectation corrections: old-v9
family owners must run before F; protocol2 cannot carry an unknown non-Note
family; a missing family owner yields its existing unproven-family blocker; CAS
test records need the correct account partition key. Final real-family producers
use the actual owners before F. No production verifier was weakened to make a
fixture pass. All disposable profiles and task-only bundles are removed after
acceptance; main dependencies, Git history and user data are retained.

## Exact changed-file inventory

- Production: `frontend/src/platform/web/resolutionPrefix.ts`,
  `frontend/src/platform/web/resolutionHistorical.ts`.
- Tests/producers: `frontend/src/platform/web/legacy3Prefix.spec.ts`,
  `frontend/src/platform/web/legacy3Continuation.spec.ts`,
  `frontend/src/platform/web/legacyV3Resolution.spec.ts`,
  `frontend/src/platform/web/resolutionContinuation.testFixture.ts`,
  `frontend/src/platform/web/resolutionPlanner.testFixture.ts`.
- Native acceptance: `frontend/scripts/browser-persistence-harness.ts`,
  `frontend/scripts/browser-resolution-continuation-acceptance.mjs`,
  `frontend/scripts/browser-resolution-prefix-acceptance.mjs`.
- CI: `.github/workflows/cloud-backend-tests.yml`.
- Documentation: this document and `docs/WORTA_CHECKPOINT.md`.

Protected Python3.12 bytecode remains exact: engine
`a256bcf08940a513a98f6551e314511cf6961bf298b88b294fd6d9c133d4bec5`,
game_data `8bd116c0b5b284f4f4b80551d10199e20d3c4546fe8caac22c07ff2973d568d2`.
All prior checkpoint headings and the complete T/V historical sections are
preserved. No UI/help/localization behavior changes in this dormant owner slice.

## Preserved project gates

C21/C21.2 IN PROGRESS; .08 NOT CLOSED; T/U REMOTELY ACCEPTED; V AUDIT COMPLETE;
R historical STOP; S DESIGN COMPLETE; .11 PARTIALLY RESOLVED; C21.1.06 NOT LOCAL
COMPLETE; .18 REMOTELY ACCEPTED; .20/.22 historical STOP. Web89.36%, ready=false,
declarationAllowed=false, writerAuthorized=false, registration CLOSED and PUBLIC
RELEASE BLOCKED. VPS/landing records, permanent CI/CD policy, C22/C23/PF6.0/RC,
security and owner release gates remain mandatory. No roadmap reweighting.
