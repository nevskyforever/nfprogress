# C21.2.08U — Legacy3 H historical continuation

## Status and independently accepted baseline

**LOCAL COMPLETE / REMOTE ACCEPTANCE PENDING.** Implementation starts from clean
branch `6.0`, exact HEAD/origin/actual remote
`a5c83fadd04be6db7b45e6e5eb5854b922a38e76`. Protected bytecode was verified before
and after the task. C21.2.08T is independently **REMOTELY ACCEPTED** on this SHA:
[Cloud39940501426](https://github.com/nevskyforever/nfprogress/actions/runs/39940501426),
SUCCESS6/6, first attempt. The original T implementation report and local evidence
remain historical and unchanged. .08S remains DESIGN COMPLETE; .08R remains
historical IMPLEMENTATION STOP.

U extends the existing dormant H owner only. No production scheduler, writer,
uploader, capability, ACK or registration activation is introduced. DB10, twelve
stores/indexes, Resolution4/Proof1/inbox10, Head2/Transition2, backend, wire,
cryptography and digest preimages are unchanged. Original submission transport
remains UNKNOWN; actual received transport and ciphertext remain exact.

## Private H composition and authentic source

`authenticateContinuationHistory` retains T's Legacy3 rejection. The H runtime's
JavaScript-private `#history` method selects a separate composition for a received3
`legacy_resolution_v2` root. Only that method can mint its frozen one-use request
in a private WeakMap. The consumer checks exact owner and current lifecycle before
consumption; cleanup also runs on failure. The request carries the owner-loaded
inventory and lease-provided key. Callers cannot supply an allow flag, inventory or
key to this entry. Forged, cross-owner and reused requests reject.

The composition first calls the existing full `authenticateResolutionHistory`,
requires exactly one accepted first-generation Resolution, and then runs the same
historical DAG/source authentication core as existing H. It authenticates the
original Legacy Resolution ciphertext, operation `resolution`, received protocol3,
null Content wrapper digest, encrypted identity/source evidence, Proof1/inbox10,
published parents, bootstrap and closure transition. Original and retained outputs
are separate identities. Current encrypted membership, project/Note source revisions,
all accepted descendants and original/retained role ancestry must agree.

This does not create another Resolution owner or another generation. Public H
`history()` returns read-only counts, never the private history or an apply/prefix
certificate. Prepare, predicted-state validation, diagnostics and reconciliation
all use the same private composition. Full account inventory CAS and existing
protected-source preparation/atomic commit remain in place.

## Supported continuations and atomic write set

All four genuine F strategies are covered: `choose_version`, `manual_merge`,
`delete`, `keep_both`. Original Note children and the distinct retained `keep_both`
Note support eligible updates, permitted deletes, later descendants, peer siblings
and exact replay. A delete root permits later deletes; upsert resurrection rejects.

| Actual ordinary transport | Accepted bounded route | Preserved identity |
|---|---|---|
| Legacy2 | Existing project/HTML Legacy source restrictions | Protocol2, original upsert/delete descriptor, Legacy proof/candidate |
| Framed Content3 | Existing portable Content source plus authentic Metadata/Stage prerequisite checks | Protocol3, event descriptor, framed payload and Content proof/candidate |
| Raw Legacy ordinary received3 | **UNSUPPORTED** | Stays received3; never cast to2 or decoded through a fallback |

Content producers explicitly emit eligible payloads (including empty portable
metadata); Legacy parent/root evidence is never normalized. Stage/Map ownership,
unknown/cold dependencies, unauthorized bootstrap/Metadata/Stage, own unpublished
authorship, incompatible pending intents, unsupported open conflicts, additional
Resolution generations and resource exhaustion reject. Mixed independent source
routes retain their separate guard; no failed mixed validation falls back to H.

| H outcome | Atomic writes | Source revision |
|---|---|---|
| Linear original/retained apply | Encrypted project, encrypted Note, candidate, Head2, exact inbox proof:5 writes | Project +1, target Note bound to that revision; other Notes unchanged |
| Supported sibling conflict | Candidate, group, Head2, exact inbox conflict proof:4 writes | Project/Notes unchanged |
| History / exact replay / lost-result reconcile | None | Unchanged |

F Resolution/transition/inbox10 and closed group remain immutable. H does not write
outbox, receipts, ACK, proven prefix, local ordinal, capability or registration
state. All thirteen selected downstream regression files retain their original
coverage; the T test that explicitly blocked H is narrowly superseded by an H
read-only success assertion while its other downstream rejections remain.

## Downstream isolation

G/Q, default and mixed K, O, mixed independent sources, private Metadata handoff
and historical prefix, terminal Metadata consumers, old proven-prefix, readiness
and production orchestration retain their existing Legacy3 barriers. Successful H
counts cannot be used as a G calculation input or H write token. A generic history
call still rejects the same Legacy3 inventory. No .11 boundary is declared closed.

## Native Chromium, real disk and previous bundles

The existing H native script is parameterized with `--legacy3`; normal H and its G
callback remain intact. It builds genuine Legacy parents, receives a real raw
Resolution on3, commits through F, then produces actual Legacy2 or framed Content3
children through sync ingestion and H. All eight strategy/child-family combinations
pass; original/retained identities, contents/tombstones and source revisions are
checked after full process/disk restarts with fresh auth/key/device runtimes.

U native evidence:8 F commits,18 H outcomes,18 linear plus16 fork fault rollbacks,
2 project-source CAS races, competing-tab rejection in every case,2 pre-commit
process stops and2 injected lost-completion reconciliations. Faults cover every
linear/fork write, native abort, key lock, logout and profile closure; complete
12-store snapshots remain equal after rejection. This is injected lost-result and
browser termination testing, **not an OS power-loss guarantee**.

The old T bundle is built from a separate `git archive` of exact accepted SHA
`a5c83fadd04be6db7b45e6e5eb5854b922a38e76`, using existing dependencies. Eight
closed-profile copies are opened by old T alone. Each rejects H history/reconcile/
apply plus G/Q/K/mixed K/O/private handoff/private prefix/old proven authorization
(11 real paths; TypeError/ReferenceError cannot count as rejection). All encrypted
and plaintext durable records remain byte-identical; no publication/ACK occurs.
The new U bundle then opens each same copy, authenticates history and replays every
accepted descendant without writes. All8 recover. There are16 historical reopens
in U mode, including the8 new-bundle returns from old-reader copies; F restart and
preparation-stop reopens are additional. No concurrent old/new profile writers.

The original old2320549-versus-T-F script is retained and rerun:4 strategies,
12 rollbacks,9 new-bundle reopens,4 actual old-reader copies,8 zero-write reconciles,
1 lost completion and1 pre-commit process stop PASS. Normal F2/Content3 H also
passes8 F commits,24 F rollbacks,18 H outcomes,18 H rollbacks and8 historical reopens.

## Local checks

Final coverage: **1,282 cases across 25 distinct spec files**, failures 0/skips 0.
Overlapping exploratory reruns are not summed. Focused tests preceded affected F/H/J/downstream regressions.

| Check | Result | Wall time |
|---|---|---|
| New isolated `legacy3Continuation` (`--maxWorkers=1`) | 96 PASS | 34.81s |
| resolutionReaders/Dag/Planner/Apply/Continuation, v10Transport, legacyV3Resolution (`--maxWorkers=2`) | 395 PASS /7 files | 21.66s |
| G/Q/K/O/mixed/private/post-F downstream regressions (`--maxWorkers=2`) | 631 PASS /13 files | 498.33s |
| localAuthority, readiness, prefix qualification and v9 migration (`--maxWorkers=2`) | 160 PASS /4 files | 202.88s |
| Native U H plus pinned old T | PASS,8 combinations/8 old copies | 19.72s |
| Native original F2/Content3 H | PASS | 14.78s |
| Native T raw3 F plus pinned old232 | PASS | 9.42s; old build0.140s |
| Native original F2/Content3 F | PASS,8 commits/24 rollbacks/4 exact F2 joins | 10.38s |
| Native original G callback (including original H) | PASS,8 prefix commits/10 rollbacks/8 restarts | 20.96s |
| Existing native persistence, including all15 v9→v10 migration cohorts | PASS, page errors0 | 204.67s |
| Typecheck and production build | PASS | Vite1.10s; typecheck wall time not separately captured |
| Production acceptance harness build | PASS | 0.166s |
| Whitespace, scope, protected hashes, workflow preservation | PASS | — |

Final 96-case run took34.81s during concurrent regression/migration validation.
No tests were skipped or weakened. Task-only bundles/profiles and the preview
were cleaned; main dependencies and pre-existing application build remain.

Development failures identified test-producer eligibility and stale references in
test fixtures, plus a browser helper lost at process restart; these were corrected.
A command accidentally run outside `frontend` used an unconfigured npx runner and
executed no tests; its task-created cache is removed. No dependency/configuration
change was accepted from that invocation. Final acceptance uses the repository's
installed Vitest4.1.10 and configured aliases.

## CI capacity and publication

Actual accepted T job durations from run39940501426:

| Existing mandatory job | Duration | Limit |
|---|---|---|
| Frontend admin | 27m59s | 40m |
| Complete-project | 18m15s | 40m |
| Foundation | 20m27s | 40m |
| Content-action | 17m40s | 40m |
| Regressions | 4m11s | 40m |
| Android | 2m10s | 40m |

Only focused U96 tests and the reused H script's U mode, including a pinned old T
build, are added to Frontend admin. Observed incremental unit+native runtime is
54.53s locally, plus the old bundle build. This is not an assumption that Cloud
runs at local speed: allocate3m increment and5m reserve, yielding35m59s <40m.
All six jobs, 40-minute limits, original tests, original F2/Content3/H/G browser
acceptance and T's pinned old232 acceptance are preserved. No skip, timeout
increase, continue-on-error or test move. Actual frontend/workflow paths select
Cloud; SQLite's enumerated filters do not match this diff.

Commit/push only after all local requirements pass. Do not poll Actions or start
V. U remote acceptance requires independent Cloud SUCCESS6/6 on the published U
SHA, separately from T's accepted result.

## Remaining gates and next narrow slice

Recommend separately authorized **C21.2.08V: bounded Legacy3 G/Q prefix contract
and acceptance audit**, beginning with the preserved barriers and account-wide
prefix semantics; do not infer K/O/private Metadata or writer readiness from H.
No V work starts here. Raw Legacy ordinary-on3 needs its own accepted transport/
owner contract. Complete-reader lifecycle, remaining prefix/recovery consumers,
all-device capability and Metadata create remain blocked.

C21/C21.2 IN PROGRESS; .08 NOT CLOSED; .08R historical IMPLEMENTATION STOP;
.08S DESIGN COMPLETE; .08T REMOTELY ACCEPTED; .11 PARTIALLY RESOLVED;
C21.1.06 NOT LOCAL COMPLETE; .18 REMOTELY ACCEPTED; .19/.21/.23 AUDIT COMPLETE;
.20/.22 historical IMPLEMENTATION STOP. Web89.36%, ready=false,
declarationAllowed=false, writerAuthorized=false, registration CLOSED,
PUBLIC RELEASE BLOCKED. VPS/landing, permanent CI/CD policy and all
C22/C23/PF6.0/RC security and release gates remain unchanged. No new percentage
or roadmap weight.
