# C21.2.18 — dormant post-F Metadata routing and private historical cursor

Baseline `4934cc12c8593e3fe5633b33f1a68e731c982ea0`, branch `6.0`.
C21.2.17 is independently REMOTELY ACCEPTED at that SHA: Cloud run
`39819436126`, all six mandatory jobs SUCCESS. Its CI native bridge repair and
private Metadata owner implementation are retained. The original .11 STOP tests
and historical failed/cancelled CI records remain evidence of the old path.

## Explicit entry and supported account cohort

`BrowserV10Recovery.bindPostFMetadata(...)` returns a separate dormant run-only
object. Neither `bind()` nor `bindMixedSources()` changes behavior. The new entry
is absent from `BrowserPersistenceSession`, editor/startup/network orchestration
and readiness. Its component owners, private prefix tokens and busy state remain
inside the factory closure.

The supported cohort is the accepted .17 complete-account cohort: exactly one
genuine F, both F protocols and all four strategies, coverless imported/captured/
active peer Metadata3, same F project, linear Metadata update or terminal delete,
Content ID0/ID1 and accepted retained F/H/O history. At most one Metadata outcome
can commit in one manual pass. The existing default event budget 8, allowed 1–32,
source/resource bounds, identity stores and lifecycle barriers are retained.

Create without a legitimate no-head baseline, Metadata2, Stage/StageOrder, covers,
own/local authorship, extra pending Metadata, additional Resolution generations,
unrelated-project Note routing and unsupported source/history remain rejected.
The complete retained inventory is never filtered to turn one of those cases into
a successful smaller account. In particular, a pending Note before Metadata stops
admission; it cannot be hidden to select the later Metadata row.

## Authentication and owner selection

The new entry loads all ten account recovery stores, then uses
`authenticatePrivateMetadataPrefixInventory` before any dispatch. This new internal
composition calls the accepted `.17 authenticateMetadataHandoffContinuations` and
the same complete source-state verifier used by the private handoff. It reproduces
original F/H/Content/Metadata wire, AEAD and stored proof relationships, source
membership/projection/revision/Head2, dense unique sequence ordering and the
complete previously proven prefix. Pending Metadata uses the explicit pending mode;
otherwise actual durable active/terminal history uses the durable mode. No failed
live H/Q call selects a replacement verifier.

Only the authenticated original F output identity selects H versus O for an
ordinary event. The actual live H/O owner prepares and commits independently,
including its original live dependencies and source grant. Metadata dispatch calls
the genuine `.17 bindPrivateMetadataHandoff`, never the old family-only commit.
K pins the full routing inventory before that private owner commit. The accepted
handoff rechecks complete A and its exact owner delta in the native transaction
and independently verifies actual durable B after native completion.

Every subsequent iteration reloads and reauthenticates the actual complete
inventory, including before idle/budget decisions. A terminal Metadata head permits
retained applied Content evidence only where the original authenticated dependency
has `M<E<D`. It grants no first apply: received Content before or after D stays
received, and both Content and Legacy new source changes in that deleted project
are blocked. Old F/H/O live ownership is not replaced with historical admission.

## Separate private cursor authority

`privateMetadataPrefix.ts::bindPrivateMetadataPrefix` is an internal owner with
closure-local WeakMaps. Its `prepare()` always obtains fresh actual auth, binding,
AMK lease, verified device/profile/session, complete inventory and original-wire/
source authentication. It derives private qualified-family maps from actual owner
outcomes. No `.15 inspect()` diagnostic, count, public result, old G/Q token,
caller snapshot or Metadata-owner token can be supplied to mint a certificate.

Applied Metadata joins its exact original owner proof. F joins its real inbox10
and Resolution4 digest; `keep_both` is one server sequence. Ordinary sequences join
real candidate/plaintext/proof outcomes; conflicts qualify only under their genuine
accepted closure. Received rows never qualify. All rows, including sequences1
through the existing proven prefix, are independently authenticated; gaps,
duplicates, corrupted proof/AEAD/source, unqualified old prefix and unsupported
retained families reject. Calculation stops at the earliest received/unqualified
sequence and reports exact counts only through that boundary.

Certificates bind to their issuing closure, actual scope and lifecycle, and pin
the complete inventory. `prepareCommit` consumes a certificate before its first
await. Commit plans are separately opaque and consumed before any transaction,
including stale, revoked, failed or aborted attempts. Foreign/reused tokens reject;
fresh replay requires fresh authentication. Returned calculation results have no
authority and are recomputed internally when preparing a commit.

Cursor commit is a second durable operation after Metadata apply. One native
readwrite transaction includes all ten recovery stores plus the existing two
identity stores. It rechecks the entire authenticated inventory and calculation,
then can put only `cursors.proven_prefix`; ACK, pull cursor and local ordinal stay
unchanged. No crypto, network or await runs inside an IndexedDB callback. Native
abort/request failure and lifecycle invalidation roll back that cursor operation.
After native completion, actual durable inventory and every original authenticated
family/source are verified again, with a final full snapshot/lifecycle check.

The original public G/Q implementation remains unchanged for its accepted histories.
The public .15 reader remains read-only and explicitly grants no cursor, source,
first-apply, ACK, capability or readiness authority. This private cursor route grants
only its exact local prefix update; it authorizes no server request or declaration.

## Interruption, replay and reporting

| Durable point / failure | Result and recovery |
|---|---|
| Metadata owner preparation or native owner abort | No applied outcome or cursor crossing; original owner rollback and errors remain. |
| Native Metadata completion followed by failed owner verification | `ownerCommitMayHaveOccurred=true`, explicit blocker, no invented verified outcome or false rollback; persisted evidence is retained for a fresh pass. |
| Verified Metadata commit followed by failed history/prefix preparation or cursor abort | The returned `applied` Metadata result remains; the prefix/history blocker is explicit. The earlier owner commit is never undone or discarded. |
| Cursor completion followed by failed post-check | `prefixCommitMayHaveOccurred=true`, explicit prefix blocker; no claimed rollback. A new runtime authenticates actual disk state. |
| Restart after owner commit and before cursor commit | Fresh private authentication recognizes the real applied Metadata outcome and can advance only the independently proven prefix, without repeating owner/source mutations. |
| Repeated applied update/delete or already-current prefix | Fresh read/verification; zero duplicate owner/source/cursor mutations. |

An unverified post-commit failure reports `more=true` as a conservative request for
fresh manual recovery. The outcome flags and blocker describe which durable stage
needs verification; no failed stage triggers an automatic retry or compensating write.

Private page replay retains J's exact current-interval rule: the page must end at
the current pull cursor, contain the same immutable encrypted events and protocol,
and match native inbox sequence keys and event-index joins. A full authenticated
inventory CAS pins the readonly native replay transaction. Older arbitrary pages,
changed ciphertext or uncommitted intervals reject. Replay never puts a cursor.

## Acceptance and CI placement

Positive fixtures use actual accepted F/H/O/Metadata owners and original encrypted
sender events. `postFMetadataRecovery.spec.ts` covers update/delete across F2/F3,
four strategies and ID0/ID1, exact counts, M/E/D ordering, live H/O, received Note
barriers, budgets, interruption between the two durable operations and replay.
`privateMetadataPrefix.spec.ts` covers independent old-prefix authentication,
diagnostic/foreign-token rejection, all-ten-store CAS, rollback, stale plans,
concurrent certificate consumption, auth/key/epoch/profile/device checks and exact
native page replay. Original .11–17 assertions are retained verbatim.

The native `--post-f-metadata` mode reuses the existing harness/install/preview and
eight persistent Chromium profiles. It checks real Metadata and cursor commits,
request-error/native abort rollback, local auth/key/epoch/profile revocation,
competing-tab writer exclusion, genuine transport races, renderer crashes before
apply/after owner/after cursor, full disk reopens and no duplicate mutation.
Metadata/cursor/replay operations trap nonce allocation and HTTP. A genuine O
source operation retains its own encryption/nonces and is checked separately.

Final local evidence: **761 distinct cases /17 files PASS** across focused complete
commands; final exact new CI command **74/74 PASS in72.54s**. The rebuilt native mode
passed in **46.246s**:8 profiles,16 Metadata owner commits,24 cursor commits,56 native
rollback checks,40 process/disk reopens,24 renderer crashes,16 inventory races,
16 replay checks,8 competing-tab exclusions and8 deliberate post-cursor failures.
Unexpected HTTP/page errors and Metadata source changes0; ACK/capability0, ready=false.
Typecheck/production/harness builds and workflow/source/history preservation checks
PASS. Existing Vite warnings remain. New-SHA remote acceptance is pending.

New unit checks run in existing `foundation`; only the new native mode is added
to `complete-project`. One-time reads of completed accepted jobs establish:
foundation `119966480895` 16m17s, complete-project `119966480407` 31m32s and
content-action `119966480628` 37m43s. No new suite is placed in the already tight
content-action job. In the current local regression run the unchanged .17 two
private suites (82 cases) consumed 76.948s; the intermediate new 73-case workload
consumed 115.277s. The final 74-case CI command took 72.54s; planning conservatively
uses the larger observed workload. The accepted CI .17 step took 173s, giving an
observed ratio about 2.25 and an estimate 4m19s for the new unit step. Foundation
would total about 20m36s/40. The accepted .17 native mode took 90s versus 32.264s local;
planning uses the larger new-mode measurement 57.516s (final rebuilt run 46.246s),
giving an estimate 2m40s. Complete-project would total about 34m12s/40, retaining
about 5m48s reserve. These are capacity estimates, not a guarantee
of future runner speed; fresh CI must confirm. Existing suites do not move, old
commands/build preparation are retained, Frontend gets no extra suite/Rust build,
all six checks and40-minute limits remain. Changed paths trigger Cloud; SQLite
is not expected by its actual filters. No new-SHA Actions polling is needed.

This bounded local route does not close the original .11 create claim, C21.2.08,
C21, reader capability, Content outbound, ACK, orchestration or release gates.
Current status and final local evidence belong to the checkpoint's .18 and
**C21 REMAINING ACCEPTANCE GATES** sections. Web89.36%, ready=false, registration
CLOSED, VPS hardening/security audit, C22/C23/PF6.0+RC and owner release gates remain.
