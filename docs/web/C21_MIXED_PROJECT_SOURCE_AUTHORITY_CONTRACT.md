# C21.2.08M — Mixed project source authority contract

**DESIGN ONLY / PROPOSED CONTRACT / NOT IMPLEMENTED** (2026-10-20).
Baseline branch `6.0`: local HEAD, origin/6.0 and independent remote ref
`301377f45bc307cf07bf068c7d85789000584eed`; worktree initially clean.
L: **AUDIT REMOTELY ACCEPTED / IMPLEMENTATION STOP**, Cloud `39458702360`
SUCCESS, **6/6 required jobs SUCCESS**, result supplied by the owner; Actions not
polled. This accepts L's audit, NOT L routing or a new authority model.

This proposal requires independent contract review and later implementation
acceptance. M creates no runtime, record, migration, authority token or permission.
F/H/G/K behavior and every L STOP probe remain unchanged. C21.2.08 is NOT CLOSED.

## 1. Audited evidence and the precise boundary

Paths below are relative to `frontend/src/platform/web/`.

| Existing owner / record | Evidence actually present | Constraint on the design |
| --- | --- | --- |
| `resolutionPlanner.ts`, F prepare/commit | Resolution4 AEAD evidence, exact before/after project rows, original Note before, one/two output Notes after; GroupTransition2, Head2, Inbox10 committed atomically | F changes the project counter once, including keep_both; no second Resolution activation |
| `resolutionAuthentication.ts`, `authenticateResolutionHistory` | Opens original wire and evidence, authenticates parents, local publications/receipts when applicable, group closure, dependencies, before/after project membership and output projections | Historical authentication is required first and is distinct from current-source authority |
| `resolutionHistorical.ts`, `verifyContinuationSources` | Project fields AND member_ids equal F source-after; suffix counters explained only by original/retained H projections; exact last output records | This accepted function must not simply drop membership equality or add an unexplained revision allowance |
| `resolutionPrefix.ts`, G prepare/commit | Calls H historical/current-source verification; other members pinned to a candidate projection or existing Legacy intent snapshot; family certificates and exact inventory CAS | Mixed source verification must precede any future G qualification; no ACK follows from a source witness |
| `localAuthority.ts`, `preparePeerSource` | One encrypted Note and encrypted project per applied peer event; project counter +1; sorted membership; local Note mutation revision 0 | A tombstone stays a member; the counter is local commit order, not sync revision or server sequence |
| `localAuthority.ts`, source-only write | Global old Note-history validation; exact project + complete Note-set CAS; identity index check | Source-only mutations cannot bypass the future-history/Content ownership checks |
| `legacyNoteApply.ts` / `contentNoteApply.ts` | Full old inbox/history readers; causal engine; atomic source/candidate/head/inbox proof; Content additionally dependency/transport evidence | Reusing business rules needs explicit full-v10 dispatch; a filtered v9 account view is forbidden |
| `noteHistoryRecords.ts`, `noteHistory.ts` | Immutable candidate1/2 with original encrypted wire, record/wire digests, optional encrypted projection and projection_digest; authenticated plaintext/projection equality | A digest without its projection is not a reconstructible source snapshot |
| `noteApplyRecords.ts`, `contentNoteRecords.ts` | Legacy/Content applied proofs bind event identity, wire, source_revision and local_note_digest; Content joins candidate/transport/dependency digests | An ordinary proof stays an ordinary proof; no relabeling as a Resolution or whole-project grant |
| `resolutionContinuation.ts`, H | Original/retained reachability, no resurrection, exact source CAS, one clean projection or a preserved conflict with no projection | H keeps ownership of these descendants and their conflicts; ordinary routing cannot take them over |
| `v10Recovery.ts`, K / `v10Transport.ts`, J | Manual first-pending ordering, complete bounded inventories, exact replay, gaps/forks/generations barriers | No offset, scheduler or retry may hide an earlier unqualified event |
| Metadata / Stage / StageOrder owners | Atomic ownerHeads + inbox changes; no localProjects/localNotes writes | These are dependency-owner transitions, not project source revisions; Stage readers still encounter the global old inbox parser |

**F does not contain a full snapshot of every member Note.** Its encrypted project
payload commits the entire sorted member set, but `source_after.notes` contains
only the original output and, for keep_both, the retained output. Other initial
members need separate genuine baseline evidence. This is a necessary eligibility
check, not a reason to reconstruct them from today's mutable source.

L evidence retained without rerunning: `v10OrdinaryBoundary.spec.ts` (22 PASS),
`browser-v10-ordinary-boundary-acceptance.mjs` (8 profiles, 24 disk restarts,
16 Metadata applies + 16 rollbacks). Valid-AEAD membership/revision drift passes
historical authentication but fails H/G/K current-source checks. These are negative
fixtures, never positive ordinary apply authority. L also proves the separate
Metadata exception and the unrelated-project old source-writer/parser boundary.

## 2. Proposed authority and eligibility

The minimal proposal is a **derived, read-only ordered project-source witness**,
recomputed from existing immutable authenticated evidence on every prepare/reopen.
It is neither a new persisted proof nor a caller-supplied authorization token.
Only the existing apply owners may produce new durable outcomes in a later,
explicitly accepted implementation. AEAD proves the encrypted content/identity;
unkeyed digests only join records. Neither successful decryption nor a claimed
counter by itself proves that an apply transaction happened.

Scope: peer, supported ordinary Legacy or Content-v1 events, active genuine
binding/bootstrap, one already accepted F anchor and its accepted H branches.
Existing route/format/dependency limits remain necessary. No own author, self-echo,
local unsealed/Content writer transition, project-field mutation, project deletion,
Note move, resurrection, new fork activation or additional Resolution is admitted.
Existing historical reads and accepted H conflict preservation are not removed.
An authentic preserved open conflict remains an explicit recovery/prefix barrier.

All account records are loaded through the existing bounded complete inventory,
validated by exact record version and authenticated by their actual owners.
Unknown versions, malformed identities, orphan proofs and inconsistent publications
are not ignored merely because their project differs from the target. Pending
rows retain original wire and their received status; readable payload authentication
does not invent an apply outcome. Unsupported pending families remain barriers.
Family dependency views may contain only their own authenticated families, as today,
but are never substitutes for complete account Note/history/source validation.

## 3. Root and complete ordered witness

The following is a specification, not an API or new record layout.

### A. Authenticate the root and every initial member

For a Resolution project P, authenticate F exactly as today, including its original
encrypted evidence, wire, parents, before/after project transition, output proofs
and closure. Let R0 be its source-after source_revision, S0 its server sequence,
P0 its canonical project fields and M0 its sorted member_ids. F itself explains
the transition R0-1 → R0; keep_both adds one member in that SINGLE transition.

Construct a baseline map B0 with exactly the IDs in M0:

1. Original and retained outputs use the exact LocalNoteRecords from authenticated
   F source-after evidence. Never replace them with a current Note or an old Head1.
2. For each other member, require a unique reconstructible accepted projection at
   the F boundary: an authenticated peer candidate1/2, its genuine applied inbox
   proof, matching bootstrap/project/Note/device and AEAD projection. Its source
   revision is below R0 and its server sequence below S0. Reconstruct the unique
   applied causal path up to the anchor and select its last applied projection;
   all earlier claimed applied outcomes on that path must join correctly. The
   current head alone is not a historical head at F. Conflict-only candidates,
   later candidates and an unrelated Note's publication cannot supply this root.
3. Require every pre-anchor applied projection for P to be consistent with this
   boundary: no pre-anchor event may claim a post-anchor source revision, and no
   post-anchor event may claim a pre-anchor revision. Enforce account-wide identity
   uniqueness, including retained IDs and the localNotes identity index.

If ANY M0 member lacks this baseline, mixed-project mutation is unsupported. A
Legacy pending intent snapshot accepted by existing G for an unchanged member
does not silently become a mixed-write anchor. Old backfill with a digest but no
projection, local-only initialization with no accepted publication, I2/C3 ownership
or a disputed pre-anchor path similarly cannot bootstrap this received-only design.
Keep existing read-only behavior; do not repair, backfill authority or rewrite F.

The witness covers the entire suffix AFTER the authenticated F boundary, not every
local mutation since project creation. Earlier state is anchored by F plus B0's
real per-member evidence; no claim of universal local-history recovery is made.

### B. Enumerate every suffix source transition

After complete historical authentication, derive the suffix from ALL P outcomes:

- Include every genuine peer applied candidate whose projection source_revision
  exceeds R0, whether it is an H descendant or an independent ordinary candidate.
  Legacy requires the exact applied proof/projection/digest join; Content requires
  candidate2 + applied transport proof + Content inbox proof + dependencies. The
  encrypted projection must agree with authenticated wire plaintext and local
  mutation revision 0. A claimed applied outcome with missing/null projection or
  missing matching inbox proof is a blocker, not an omitted step.
- Classify by authenticated DAG reachability and role, not merely record version:
  original/retained descendants belong to H; independent Notes must have a genuine
  Head1 causal chain outside both Resolution output identities. Candidate1/2
  layouts can be used by BOTH owners; a projected old-format candidate is never
  itself a whole-project witness or v10 permission.
- Conflict-preserved events have no source projection and consume no revision.
  Authenticate them and retain their explicit unresolved barrier. Receipts,
  received rows, replay, Metadata, Stage and StageOrder also consume no source
  revision. No source-only/local writer outcome may be counted as a peer apply.

Sort actual transition revisions, never fabricate a value from array order. For
N transitions the revisions MUST be exactly R0+1, …, R0+N, unique and safe integers.
The matching server sequences must be unique, strictly increasing and above S0;
each causal parent/dependency must precede its child under its accepted contract.
Server sequences need not be consecutive for P: other projects/families may occur
between them. Account sequence continuity is checked separately across ALL rows.
Source counters of different projects and local publication ordinals are never
merged, compared as one counter or used to fill a missing source revision.

This ordering is admission to the proposed manual mixed route, not a retroactive
change to historical proof validity. An existing accepted state outside that
ordered cohort stays readable under its existing contract and is unsupported for
mixed mutation; do not rewrite its history or silently reorder committed outcomes.
All digest domains and existing Legacy-versus-Content wire joins stay unchanged;
never reframe, recompress, re-encrypt or normalize original events to fit the fold.

### C. Fold membership, complete Note state and causal ownership

Start with (R0, P0, M0, B0). At transition Ri = R0+i:

| Transition | Required pre-state and evidence | Exact post-state |
| --- | --- | --- |
| Independent create | Genuine absent Note; revision1/parent null/upsert; no member, head, history, intent, retained-ID reservation or cross-project identity collision | Add its ID once; store exact authenticated projection at Ri; no other member changes |
| Independent update | Existing live member, exact unique applied parent/head and prior projection; sync revision parent+1; same route; peer outcome and dependencies verified | Replace that Note with its exact projection at Ri; membership unchanged |
| Independent delete | Existing member and exact applied parent; authenticated tombstone and route; no physical removal | Replace with tombstone at Ri; ID remains in membership; child delete only if the accepted owner permits it |
| H original/retained projection | Exact role-bound reachability to F, accepted H parent/tip/revision/dependency checks, no resurrection | Replace only the H-owned Note; membership unchanged; retained genesis was already included by F |
| F itself | Full accepted before/after evidence and all four strategy rules | Single root transition; original replacement and optional retained addition; not counted again in suffix |

Every non-target Note record stays byte-for-byte the same as the preceding map.
No upsert of a tombstone, recreation of a deleted ID, absent-member delete, Note
move, retargeting of a parent or route/format change can be inferred from this fold.
New member creation is not inferred from a higher revision or a missing local row.
Every suffix projection must be consumed exactly once; none may be attributed to
another project, bootstrap, Note or Resolution role.

At the end require ALL of the following, not just a final counter check:

- Current project source_revision = R0+N in both outer row and decrypted payload;
  project is live, scope is exact, canonical fields equal P0.
- Current decrypted member_ids equal the fold's sorted member set, and the complete
  localNotes key set equals that set, including tombstones. No omitted/extra member.
- Each current LocalNoteRecord exactly equals its expected final projection/B0
  record, including encrypted envelope and source revision; decrypt/validate all
  records and compare plaintext with their genuine event/output evidence.
- Independent heads reflect the unique accepted ordinary path; H Head2 role,
  reachable linear head, tips and head_revision count still obey H. Source revisions
  count projections; head revisions may also count conflict preservation. They
  must not be substituted for each other.

Project intermediate envelopes need not be persisted: their canonical payload is
deterministically (P0, derived membership, Ri). Fresh encryption uses fresh nonces;
do NOT compare a re-encrypted project envelope to a guessed historical ciphertext.
Current actual project ciphertext and the complete Note rows remain pinned by the
exact source CAS. A checksum cache or a caller's claimed fold is never authority.

### D. Atomic apply, concurrency, restart and manual retry

A later v10-aware owner must authenticate the full pre-inventory, derive the current
witness and prepare source/candidate/proof changes OUTSIDE a live IDB transaction.
It must validate the complete predicted post-inventory, including this same witness,
before committing. A pending decrypted event is only proposed input until this
real owner has checked its causal/dependency/source preconditions.

The short readwrite transaction pins the complete account inventory used for routing
and proof preparation, not only the target Note. Re-read all ten inventory stores,
exact project row AND entire project Note set, binding/bootstrap, heads/history,
intents, inbox/outbox/receipts and cursors. Check identity-index absence/ownership and
live account/auth/key/profile/device epochs, then write the source project + changed
Note + immutable candidate + appropriate head + genuine inbox proof atomically.
Reuse accepted source CAS and scheduling primitives; do not await crypto/network
inside the transaction. New private owner handoffs, if later necessary, require
explicit implementation review and cannot consume public read-only diagnostics.

Another tab/owner changing any pinned value makes the prepared plan stale. Abort;
discard it; fully reload/authenticate and require manual retry at the earliest
pending sequence. Independent Notes in one project still serialize on its project
counter. Full-account pinning may conservatively reject unrelated-project races;
there is no merge of stale plans and no allocation before a successful commit.

An abort/quota error/request failure, lifecycle revocation or crash before completion
leaves the old source/history/inbox/cursors intact. A crash after completion leaves
the whole real outcome, recoverable by recomputing from immutable records. Exact J
replay is a no-op for source revisions and proofs. No durable witness cache, recovery
marker or repair write is required. A complete valid disk snapshot rollback cannot
be detected by a purely local derived witness without an external monotonic anchor;
this proposal does not claim that guarantee or full multi-device disaster recovery.

## 4. Ownership and separate routing decisions

| Component / route | Proposed bounded responsibility after separate acceptance | Still forbidden / deferred |
| --- | --- | --- |
| Ordinary apply | Full-v10 inventory dispatch; own causal/AEAD/format/dependency checks; exact-source peer transaction on independent Notes; existing candidate/proof formats | Taking an H output, using a filtered old account inventory, writing through a public diagnostic |
| F | Original accepted one-Resolution boundary and atomic evidence root | Another Resolution anywhere K currently blocks it; rewriting F evidence to include new ordinary Notes |
| H | Exclusive original/retained descendants and accepted conflict preservation; same semantic checks; eventual explicitly reviewed mixed witness prerequisite | Routing independent Notes through H or dropping role/reachability/no-resurrection checks |
| G | Eventually consume the independently accepted complete mixed witness BEFORE its existing family/contiguous-prefix calculation and exact CAS | Treating witness success as an ACK, Note capability or positive readiness |
| Future v10-aware source owner | Only source preparation/scheduling for a real ordinary/H owner after full pre/post verification; all mutations explained | Source-only init/edit/delete, local intent or Content writer activation in an R project under this received-only contract |
| K / J | K keeps earliest pending, gaps/forks, budgets, manual retry and role-aware dispatch; J exact immutable replay remains transport-only | Scheduler, pull/push, skip-ahead, second F generation or a new authorization from mode/registration |

Current H/G functions remain unchanged in M. A later read-only candidate verifier
must be isolated. Substitution into H/G/ordinary prepare and commit is a distinct
reviewed integration change: no fallback such as "H failed, try a looser count".

Same-project independent routes need the COMPLETE witness above. For an unrelated
already-bound project with no Resolution, retain its existing genuine canonical
source + ordinary causal/CAS rules; fully authenticate the Resolution project too,
but do not borrow its root or counter. Its source change must leave the R project's
rows/proofs unchanged. New post-v10 project initialization remains a separate blocked
source-writer concern, not permission inferred from another project's binding.

Metadata is the L-proven exception: its unchanged exact-reference owner can apply
after F/H/G, changes only owner head/inbox and consumes no source revision. A future
K route still needs full-account pre/post pinning and first-pending/dependency checks.
It does not update P0's canonical project fields. Materializing Metadata into
localProjects would be a new source transition outside this contract.

Stage/StageOrder also change ownerHeads/inbox only. Their old global inbox parsing
must be replaced by explicit full-v10 dispatch before routing, preserving original
AEAD, bootstrap, complete parent tips, Metadata/Stage dependencies, exact Stage-head
coverage and owner CAS. StageOrder must not infer missing stages or use a later
unproven head. Revalidate Content dependencies against the real resulting owner
history; an owner-head advance cannot silently authorize a Note. These routes are
separately testable, not evidence that ordinary source authority is solved.

## 5. Fail-closed decisions

| Condition | Required result |
| --- | --- |
| Missing/duplicate revision, counter-only drift, unexplained source write | Reject witness; no G qualification, source write, repair or counter renumbering |
| Forged member set, omitted tombstone, swapped projection, added/missing Note | Reject exact expected source comparison even when all envelopes decrypt |
| Duplicate event with different wire/identity/proof, duplicate projection revision | Reject; exact known replay alone is idempotent and allocates nothing |
| Stale source/head/bootstrap/cursor, competing tab or dependency owner | Atomic abort; full fresh prepare on manual retry; no stale plan reuse |
| Missing inbox sequence, orphan parent or proof, unavailable dependency | Earliest explicit barrier; no later apply/prefix bypass; do not invent applied evidence |
| New fork/open group | Retain accepted authenticated history; no new ordinary fork activation, no qualification across it; H's existing preservation stays owned by H |
| New Resolution/unknown generation, own event, resurrection, local unsealed/I2/C3 source | Unsupported barrier; never an implicit downgrade or fallback route |
| Missing baseline or old applied proof without a reconstructible projection | Unsupported baseline barrier; a proof digest/current source is insufficient |
| Corrupt AEAD, wrong AAD, scope/project/bootstrap/role mismatch, unknown version | Fail authentication; retain bytes; no partial acceptance of the rest of the account |
| Resource bounds exceeded | Explicit resource-limit stop before writes; no hidden rows, truncation or relaxed size limits |
| Rollback/restart/revocation | No partial transaction; recompute at reopen and recheck epochs; no public diagnostic reused as a commit grant |

## 6. Representation and migration decision

**Migration requirement: NO for the proposed bounded received-only contract.**
This is a representability conclusion, not a claim that the current owners can
already route it or that all existing databases are eligible. L implementation
remains STOP until the new semantics and its owner integration are accepted.

| Required material | Existing durable representation | Remaining admission check |
| --- | --- | --- |
| Root project fields, membership and revision | F Resolution4 evidence source-before/source-after project1 AEAD | Full F authentication, same scope/bootstrap; not a complete Note snapshot |
| Root output Notes | F encrypted source-after original/retained LocalNoteRecord1 | Exact F outputs/proofs |
| Other initial member sources | Retained candidate1/2 encrypted projection, genuine applied inbox proof and original wire | Unique pre-anchor applied path; missing projection makes project ineligible |
| Every suffix applied transition | Candidate1/2 projection source_revision, wire AEAD, Legacy or Content proof; Content transport/dependency joins | Exactly one real outcome per revision; correct ordinary/H ownership and causal order |
| Current complete source and membership | LocalProjectRecord1 + payload member_ids, LocalNoteRecord1 set | Derived full-state equality and exact source CAS |
| Restart/replay/atomicity | Existing history/inbox/source/cursors in one IDB10 database | Real owner transaction; derived witness rebuilt, never persisted |

No fields, discriminants, record versions, stores, indexes, IDB database version,
wire/crypto formats or migration are proposed to change. It is unnecessary to store
the reconstructed intermediate project envelopes or duplicate proof hashes. Existing
read-only v10 dispatch and frozen v9 validators remain distinct; this is semantic
acceptance work, not permission to feed v10 records to v9 validators.

If future scope MUST include members whose historical projections were never
retained, arbitrary local/project-field writes, physical removal, additional F
chains or new writers, this NO does not cover it. Missing historical bytes cannot
be recreated by migration. Supporting such scope would require a separately
accepted authenticated complete baseline/source-transition record produced by its
real source owner with exact before/after scope, revision, membership and changed
Note evidence, atomically with that mutation; its versioning/old-client barrier
and any database upgrade would need their own design. Do not assign a speculative
record version or implement/backfill that record here. **STOP before such expansion.**

## 7. Concrete next implementation plan

Recommended next bounded slice: **isolated read-only mixed project witness verifier**,
after independent review of this proposal; no new C-stage number assigned here.

1. Add only a private pure derivation/read-only diagnostic over the existing complete
   authenticated inventory; implement baseline admission, revision fold, exact current
   comparison and sanitized blocker reasons. No commit/ACK/capability authority in its
   public output. No substitution for existing H/G checks yet.
2. Prove it accepts genuine unchanged F/H states and reconstructible pre-anchor
   independent members, and rejects all L negative evidence, missing baseline and
   malformed outcome joins. Retain L assertions against unchanged production owners.
   A preview based on real pending wire may calculate a proposed transition, but is
   explicitly not a persisted applied outcome or a positive mixed-history acceptance.
3. Independently accept that verifier. In a following explicitly authorized slice,
   introduce a dormant v10-aware ordinary owner handoff and reviewed H/G integration,
   using existing record shapes and source transaction semantics. Both full pre-state
   and predicted post-state must pass before any genuine new outcome is committed.
   Default old production owners and scheduler remain strict/inactive.
4. Generate positive post-F independent histories ONLY through that real accepted
   atomic owner, not database puts, manufactured proofs or relabeled read-only tokens.
   Then run the end-to-end acceptance matrix below. If the old owner cannot expose a
   safe private handoff without another contract change, STOP and review it first.
5. Only after those components are independently accepted, extend manual K dispatch
   for independent Notes and separately accepted Metadata/Stage/StageOrder paths.
   Preserve H precedence, original F generation limit, full-account barriers and
   manual retries. No scheduler, writer, readiness, Note declaration or ACK activation.

### Acceptance matrix for implementation (PLANNED, not run or claimed PASS by M)

| Cases | Required evidence / outcome |
| --- | --- |
| Protocol2 Legacy + protocol3 Content-v1, Content ID0/ID1; each of four F strategies | Genuine original wire/AEAD; actual F/H and later accepted ordinary owners; same invariant for choose_version/manual_merge/delete/keep_both |
| Existing independently proven member before F: update/delete; new absent member after F: create→update→delete | Exact B0; contiguous project revisions; tombstones retained; every outcome/projection joined; no unrelated Note changes |
| Interleave independent changes with original AND retained H descendants; include repeated permitted tombstone delete | Owner roles remain exact, no double revision for keep_both; final witness/current source equal; all existing H checks preserved |
| Other-project events before/between/after P events, including repeated source revision numbers in different projects | Full account auth, no cross-project root reuse; P unchanged by Q; global sequence continuity retained |
| Missing B0 projection, digest-only backfill, local-only member, pending Legacy/I2/C3 | Explicit admission barrier, no current-source inference or generated authority |
| Revision/member drift from unchanged L negatives, changed P0 fields, omitted tombstone, cross-Note projection | All reject even with valid AEAD; original proofs/wire retained; no repair or positive G result |
| Gaps/duplicates/orphans, wrong parent order, conflicting wire, scope/bootstrap/identity collision | Explicit earliest blocker or corruption; no skip, source allocation or proof rewrite |
| New ordinary fork, accepted H preserved fork, second Resolution, resurrection, own author/self-echo | Preserve accepted H behavior and explicit prefix hole; no new activation or ownership fallback |
| Metadata exception after R, Stage genesis/update/delete, StageOrder exact coverage; Content before/after dependencies | Actual dependency owners, ID0/ID1; no source counter consumed; missing/stale/deleted dependencies fail closed |
| Same-project and cross-project competing tabs; changed source/head/intent/dependency/cursor between prepare/commit | One exact transaction wins, stale one aborts; retry recomputes full account, does not reuse witness or nonce plan |
| Native fault after each source/history/head/inbox write, auth/key/profile/device revocation | Entire transaction rolls back; no partial candidate/proof/source or unauthorized network operation |
| Full Chromium disk close/relaunch before/after apply, crash simulation, exact J replay, bounded K retry | Rebuilt witness equals committed state; replay allocates nothing; original encrypted events/immutable proofs byte-for-byte unchanged |
| Prefix across Metadata/Stage/StageOrder/Legacy/Content/R and unsupported other families | Existing contiguous account barrier preserved; local prefix only; Resolution ACK0, Note PUT0, Content push0, ready=false |
| Compatibility and existing regressions | Frozen IDB10/12 stores/indexes, no conversion; F/H/G/I/J/K and L STOP default paths preserved; protected files unchanged |

Future validation: focused unit tests, affected owner/prefix/replay regressions,
real Chromium persistent profiles for the matrix, typecheck/build and mandatory
workflow/path checks. Resource/time limits must remain explicit; no redundant
full backend/native suite solely for a docs or isolated read-only change.

## 8. M validation and unchanged release state

M validation is documentation consistency, source-contract inspection, existing L
evidence review, exact historical-text preservation, local workflow path analysis,
protected-file hashes and `git diff --check`. No runtime test/build rerun or new
test infrastructure is needed for this docs-only commit. No Actions polling/wait.
Because the companion audit updates `docs/cloud/**`, Cloud is EXPECTED with all six
mandatory jobs, including Frontend admin and Android compression packaging; SQLite
is NOT EXPECTED for these documentation paths. This is an expectation, not a run result.

Official Web progress **89.36% (84/94×100)** unchanged; C21/C21.2 IN PROGRESS,
C21.1.06 NOT LOCAL COMPLETE, C21.2.08 NOT CLOSED / FUNCTIONALLY BLOCKED;
L AUDIT REMOTELY ACCEPTED / IMPLEMENTATION STOP. No roadmap points or numbering
changes. Production scheduler, Resolution ACK, account-wide Note declaration,
Content writer/sealing/upload and own authorship remain OFF; ready=false.
VPS Security Hardening & Security Audit, PUBLIC RELEASE BLOCKED, owner reminders,
registration/policy/license/stabilization gates and all historical records remain.

### Простыми словами

Предлагается проверять общий счётчик проекта по полной последовательности реальных
применений: каждое изменение должно объяснять ровно один шаг и точное состояние
затронутой заметки. Новая заметка добавляется в состав проекта, удалённая остаётся
в нём как запись об удалении. Исходная и сохранённая ветки Resolution по-прежнему
принадлежат H; Metadata и Stage имеют свои проверки и не меняют этот счётчик.

Для этого ограниченного варианта существующих форматов базы достаточно. Но если
исходный снимок какой-либо старой заметки не сохранён с настоящим доказательством,
её нельзя считать подтверждённой по сегодняшнему содержимому: проект останется
заблокированным для нового смешанного маршрута. Сейчас утверждён только результат
аудита L. M описывает предлагаемый контракт; маршруты и синхронизация не включены,
ready=false, прогресс 89,36%. Следующий шаг — отдельный проверяющий модуль только
для чтения и его независимая приёмка.

## C21.2.08N — Bounded read-only verifier implementation

**LOCAL COMPLETE — ISOLATED READ-ONLY / REMOTE CI PENDING** (2026-10-20).
Starting clean branch6.0 local/origin/remote ref:
`bc7eddc4095ba6c321298e76a7e54711bf5e74c2`.
M **REMOTELY ACCEPTED**, Cloud `39470290591`, required six-job SUCCESS accepted
from the owner's «тесты прошли» follow-up to the pending independent acceptance
question. No Actions API query/poll/wait. Earlier gate-blocked preflights changed
nothing. The original M proposal above is retained verbatim as design history.

### Implemented surface and derivation

`frontend/src/platform/web/mixedSourceWitness.ts` is imported only by its spec and
the isolated acceptance harness. `BrowserMixedSourceWitness(...).bind(...).inspect`
has no source owner, apply/commit/replay/ACK method, public authorization token or
persisted witness. Normal persistence/editor/startup and F/H/G/K do not import it.
Public results contain frozen counts and literal readOnly=true, commitAuthorized=false,
ackAuthorized=false, ready=false. Errors expose sanitized blocker codes, not Note
content, IDs or key material. A result is not authority for any later operation.

Every inspection authenticates the full bounded account inventory through accepted
historical F/H crypto and exact version dispatch. Metadata/Stage/StageOrder receive
only their existing family dependency view AFTER full future Note/history validation;
their history is freshly authenticated. Inbox gaps, identity collisions, wrong
publication/proof joins, scope and resource violations fail closed. All encrypted
current project/Note rows are opened and validated; only the single F project gets
the derived project witness. Other projects never borrow its root or counter.

Supported pending Note/Metadata/Stage/StageOrder frames are also freshly AEAD/
canonically decoded and bound to their actual reference. They remain received,
consume no source revision and obtain no apply/dependency grant from that read.
Corrupt pending wire rejects; another received Resolution or unsupported pending
family is an explicit barrier. A genuine encrypted Map is tested as canonically
readable yet unsupported here: reader support is not protected-apply permission.

The baseline uses F's exact original/retained output snapshots and reconstructs
other members from their unique real pre-F peer applied paths/projections. No
current-source snapshot, old Head1 reinterpretation or digest-only substitute.
Active local intent/C3 ownership in the witnessed project is unsupported. A missing
root remains missing; there is no backfill, rewrite or migration.

All genuine applied suffix candidates join their existing owner proofs/projections;
source revisions are unique/contiguous and sequence order strictly increases.
Independent Note create/update/delete, unchanged other members, tombstone retention
and H role-specific descendant/head/causal/no-resurrection checks are separate from
this project fold. The complete expected final Note map must equal current encrypted
records exactly. Project fields/membership/revision must equal the derived canonical
state; the actual project envelope and whole account snapshot are pinned by a fresh
final read. No looser retry after failed H checks or relaxed source predicate is
installed in any accepted owner. Open conflicts remain explicit barriers.

### Evidence, limits and non-claims

Focused N51 PASS; affected C21/auth-key run2401 PASS /75 files. Genuine pre-F ordinary
create/update/delete outcomes, F and original/retained H descendants are all made
by unchanged actual owners. Test scheduling now reproduces native localNotes compound
key order rather than insertion/locale order; real disk acceptance uses native IDB.
The full bounded run includes50 N cases; final focused N51 additionally proves that
invalid authenticated current-source JSON cannot escape as a parser error containing
plaintext. Known sanitized owner/blocker errors remain explicit; unknown decoder
errors become corrupt_record. This adds no new persisted/error record format.

The digest-only negative removes an encrypted historical projection and recomputes
only the unkeyed candidate checksum; original Legacy applied proof and wire are
untouched. Existing historical read still succeeds while N rejects missing_baseline.
It is NOT a manufactured positive source witness. L's valid-AEAD source drift,
canonical project-field drift, exact Note re-encryption mismatch, proof/identity/
membership corruption and full-inventory races reject without writes. A genuine
local-only member before F is rejected, as by existing G. A genuine H-preserved
fork blocks N. Genuine out-of-server-order H cross-role applies remain readable by
H and are rejected ONLY as admission to the stricter mixed cohort, without repair.

Native mode `browser-v10-ordinary-boundary-acceptance.mjs --mixed-source-witness`
reuses ALL L native assertions and adds real pre-F ordinary live/tombstone baselines.
8 disk profiles cover both protocols/all4 strategies and Content ID0/ID1;24 full
disk restarts;48 inspections under write/nonce traps;8 races caused by REAL H apply
between N's reads;8 lifecycle revocations;8 competing tabs;16 source-drift refusals
before/after restart. N writes0, nonce allocation0, HTTP0, page errors0. Existing
Metadata owner16 applies/16 rollbacks and all L ordinary/Stage/source refusals PASS.

**No positive independent ordinary-after-F applied history is claimed.** L still
blocks its accepted producer. N implements the read-only suffix rules, but neither
fixtures nor database puts synthesize a positive ordinary apply proof to test new
post-F routing. That end-to-end acceptance belongs to the separately authorized
real owner integration slice. No preview/result is relabeled as an applied event.

Typecheck/build PASS (existing Vite import/chunk warnings); mandatory workflow/path
and diff checks PASS. No skipped/failing cases in final checks. Unrelated backend/
native suites and unchanged heavy physical migration runner not repeated; unit
migration/format regressions PASS. Existing L default native command/mandatory
steps retained; new awaited N mode and N spec added to Cloud. Cloud all6 EXPECTED,
including Frontend admin and Android compression packaging; SQLite NOT EXPECTED.
No Actions polling. Protected .pyc hashes unchanged; schema/migration/IDB10 untouched.
An earlier local run overlapped crypto tests/build/browser work and hit8 test timeouts.
The final complete run limits local concurrency to maxWorkers4; assertions and
existing timeout limits are unchanged. This is a local command option, not a CI
skip, workflow timeout change or suppression of a failed assertion.

Next requires independent N acceptance, then a separate dormant v10-aware ordinary
owner handoff and independently reviewed source prerequisites before generating
real post-F ordinary outcomes and integrating H/G/K. None of that is enabled by N.
L IMPLEMENTATION STOP, C21/C21.2 IN PROGRESS, C21.2.08 NOT CLOSED, Web89.36%,
ready=false; scheduler/Resolution ACK/Note declaration/Content writer-sealing-upload
OFF. All security/public-release/owner gates and prior records preserved.

### Простыми словами

Добавлена проверка только для чтения: она сверяет источник проекта с настоящей
историей, не создаёт proofs и не меняет данные. Полученные, но ещё не применённые
события проверяются как зашифрованные данные; это не делает их применёнными.
Отсутствующие исходные снимки и неподдержанные случаи остаются барьерами.
Независимые правки после F потребуют реального owner и следующей отдельной приёмки.


## C21.2.08O — Dormant ordinary owner implementation / no H-G-K integration

**LOCAL COMPLETE — BOUNDED ISOLATED OWNER / REMOTE CI PENDING** (2026-10-21).
Clean branch6.0 HEAD/origin/remote `11d18a19e4cae18df60f918f852281b563654f12`.
N **REMOTELY ACCEPTED**, SHA `11d18a19e4cae18df60f918f852281b563654f12`,
Cloud `39479808344` SUCCESS, all six required jobs SUCCESS, independently accepted
as explicitly supplied by the owner in O. No Actions query/poll/wait. M's original
proposed contract and all historical N/L records above are preserved verbatim.

### Exact admitted cohort and authority boundary

`BrowserV10OrdinaryApply` is explicitly constructed only in tests/the isolated
harness. It is absent from normal persistence composition, editor, H/G/K dispatch
and schedulers. Scope is the one F project, received peer ordinary Notes, active
import_remote/captured binding. It supports new independent Notes and genuine
pre-F reconstructed independent members. Legacy protocol2 retains stage-null/html
admission; Content protocol3 retains v1/html-or-plain/project-or-stage admission and
actual Metadata/Stage dependency prerequisites, ID0/ID1. No new own/local admission.

The original F Note and optional retained Note are rejected by O regardless of
incoming protocol or payload: H keeps their role-aware Head2/Resolution ancestry.
Unrelated-project ordinary routing is intentionally outside O; full account crypto
and source decoding still include those projects. The first received account event
of any family must be processed first. Gaps, forks, orphan parents, missing
baselines/dependencies and new Resolution generations never get skipped or repaired.
Existing conflicting/local histories reject, not silently resolved by this owner.

The N fold has moved unchanged into internal pure `mixedSourceValidation.ts`.
`BrowserMixedSourceWitness.inspect` remains a frozen counts-only diagnostic with
false commit/ACK/ready flags, no writer/owner/plan/cache. O never calls inspect or
consumes its result. Instead O authenticates its own complete bounded pre-inventory,
checks root, binding, peer identity, exact source, ordinary Head1/parent/revision/
route/no-resurrection, and then validates the entire predicted post-inventory using
the same pure derivation. This internal pure function returns counts, never a grant.
The complete account is not downgraded or filtered into an old Note owner.
Metadata/Stage receive only their existing dependency view after full v10 validation.

A private WeakMap plan is bound to O runtime + local runtime + exact scope + live
registered device/auth/key/profile epochs. Only its one-use handoff may call
`prepareProtectedV10OrdinaryApply`, which reuses the existing private peer source
preparation. Neither a plaintext DTO nor N counts nor foreign/replayed plans pass
the handoff. No authority token is persisted, exposed as a diagnostic or fabricated.

### Real post-state and atomic source handoff

- Every actual commit increments the project source revision once and changes one
  Note. Create adds exactly one member; delete keeps a tombstone/member; unrelated
  Notes and original F/H encrypted evidence stay byte-for-byte unchanged.
- Legacy uses genuine candidate1/proof1/inbox3; Content uses genuine candidate2,
  existing transport/dependency certificate+commit hook and inbox7. Ordinary Head1
  stays Head1 for independent Notes; no substitute for H's Head2 is created.
- Newly encrypted project and Note plus candidate/head/proof are validated as one
  complete predicted state BEFORE any write. This includes all original AEAD,
  genuine applied projection joins, exact F baseline and contiguous revision fold.
- All ten account inventory stores, exact source/project/whole Note set, cursors,
  dependency owners and global identity-index state are pinned in the short final
  readwrite transaction. Source/candidate/head/inbox proof are atomic. No async
  crypto/network work occurs inside IDB. Drift invalidates the plan; it is consumed
  on a commit attempt and cannot be reused. Fresh manual prepare is required.
- Lifecycle listeners abort active transactions. Every scheduled write checks
  currentness. Crash before commit leaves only the original received ciphertext;
  crash after commit preserves the entire real outcome for fresh read-only replay.
- Reconcile authenticates full mixed history/current source and real applied joins;
  it preserves superseded original proofs without nonce allocation/source mutation.
  Exact J replay also reads the genuine outcomes under its unchanged cursor contract.

No new persisted fields, stores, indexes, record versions, schema, wire, crypto or
migration. **Migration requirement: NO for O's bounded received-only cohort.**

### Acceptance and remaining blockers

O46 focused and N51 PASS; affected1198 regressions/23 files PASS, including old
F/H/G/I/J/K/L ordinary/dependency/migration barriers. Every positive post-F projection
and inbox proof is generated by actual O prepare/commit after real F/H; there are
no fabricated positive applied rows. Tests cover both protocols × four F strategies,
Content ID0/ID1, independent create/update/delete, pre-F live/deleted members, stage/
plain, concurrent Notes/owners, exact source revisions and replay. Predicted-state
corruption, N-as-authority, forged device/caller grants, missing dependency/parent,
resurrection, F/H role/unrelated-project requests, stale full-inventory CAS, rollback,
revocation and unauthorized HTTP all reject without partial writes.

Native O PASS:8 disk profiles,32 full process restarts,64 actual applications,
16 read-only replays,8 injected native transaction aborts,16 genuine races,
8 lifecycle revocations,8 competing tabs,96 barrier assertions, page errors0.
Original F/H/baseline ciphertext, immutable candidates/evidence and inbox proofs,
unchanged source Notes, outbox/receipts/dependency owners/intents/bindings preserved.
Native N/L PASS:8 profiles/24 restarts,48 read-only inspections under write/nonce
traps,8 H races,8 revocations,8 tabs,16 source refusals; all old L assertions remain,
including Metadata16 genuine applies/16 rollbacks and ordinary32/structural16 rejects.
N diagnostic writes/nonces0. No unauthorized HTTP, Content push, ACK or Note PUT.
Typecheck/build/workflow/path/diff/history checks PASS; protected .pyc unchanged.
Existing Vite warnings remain. No unrelated backend/native heavy suite repeated.
A native delete-strategy boundary probe initially tried to encode a live payload
from a tombstone; only that sender-negative fixture was corrected to send delete.
Final native acceptance passes all strategies; production resurrection stays blocked.

Old H/G/K are deliberately untouched and tested to reject a genuine mixed O source.
This is NOT H/G source handoff, G prefix proof, ACK eligibility, K integration or
full multi-device recovery acceptance. A subsequent reviewed slice must integrate
mixed source validation into H/G without turning diagnostic counts into grants,
then separately review K routing. Additional Resolution chains, resurrection,
local/own authorship, unrelated-project routing and unsupported families remain
explicit blockers. L's old-route implementation STOP is not renamed as complete.
Production scheduler/public writer/Content sealing-upload/Note capability/Resolution
ACK OFF; ready=false. Web89.36%, C21/C21.2 IN PROGRESS, C21.1.06 NOT LOCAL COMPLETE,
C21.2.08 NOT CLOSED; security/public-release/owner gates preserved. Cloud all six
mandatory jobs EXPECTED (Frontend admin + Android compression packaging included),
SQLite NOT EXPECTED; O remote CI pending, no polling/waiting.

### Простыми словами

После решения конфликта отдельный модуль может безопасно сохранить независимые
заметки и доказать, почему изменился состав проекта и его общий счётчик. Он не
подменяет проверку только для чтения разрешением на запись. Перезапуск и повтор
события проверены на настоящей браузерной базе. Обычная синхронизация новый модуль
пока не вызывает; для H/G/K потребуется отдельная согласованная приёмка. Готовность
и публичный доступ не включены, прогресс89,36% без новых начислений.


## C21.2.08P — H-only mixed source integration / explicit historical compatibility

**LOCAL COMPLETE — DORMANT H ONLY / REMOTE CI PENDING** (2026-10-21).
Clean branch6.0 HEAD/origin/remote `a20a676312b164bf952366672d2ab903d1ffb200`.
O **REMOTELY ACCEPTED**, same SHA, Cloud `39581100692` SUCCESS, all6 mandatory
jobs SUCCESS, independently accepted as explicitly supplied by owner. Actions not
queried/polled/waited. Prior O/N/M/L contracts and acceptance records stay verbatim.

### Evidence-selected source contract

`resolutionContinuation.ts` retains its private H plan/source authorization and
all existing role/causal/Head2/dependency/no-resurrection/atomic CAS checks. After
complete original-wire/history crypto, its private source selector examines
independent Note candidates in the Resolution project. A server sequence above
F, or an authenticated projected source revision above F, selects mixed admission.
This includes unsupported ordinary conflicts/ownership; they cannot select a looser
historical route. It is not inferred from a mutable counter or claimed diagnostic.

Before selecting, require every retained account sequence AFTER F through pull_cursor
exactly once. Deleting O's candidate/head/inbox evidence and restoring actual old
encrypted source is still a post-F gap, not a new historical-only authority. This
check preserves the old pre-F admission boundary; it does not reclassify old source
projections or create missing events. Full mixed admission additionally retains the
N/M complete account sequence, current source and dependency validations.

| Authenticated evidence | H source prerequisite | Permitted behavior |
| --- | --- | --- |
| No independent post-F outcome | Existing verifyContinuationSources, unchanged, plus post-F continuity | Accepted F/H-only reads/apply/replay/preservation, including genuine historical cross-role source order outside M's mixed cohort |
| Genuine independent post-F O outcome, no open groups | Complete mixed fold plus unchanged H role/causal checks | Original/retained H apply after full pre/post verification; independent Notes stay O-owned |
| Mixed history with authenticated H-only open fork(s) | Exact mixed source fold AND full H group/member/tip/outcome crypto and role-rooted ancestry | Read/replay and conflict-only preservation; NULL projection, unchanged source_revision/source/prefix |
| Mixed open group while requesting a source-changing H apply | Explicit barrier | Reject even when targeting another H role; never mint an applied projection across a fork |
| Independent/unowned open conflict, missing baseline, invalid proof/source, unsupported generation/ownership | Reject | No retry through historical verifier, filtering, repair, source guess or qualification |

Source mode is bound across complete pre- and predicted post-inventory. Every apply
also re-reads all ten stores before commit and pins them in the atomic transaction.
No failure handler downgrades a mixed error to legacy checks. Authenticating the
complete inventory still precedes any Metadata/Stage dependency-only view.

### Preserving H conflicts without granting source/prefix authority

`mixedSourceValidation.ts` keeps N/O's strict `validateMixedSourceInventory` entry.
It always rejects unresolved forks. P adds a separate internal
`validateMixedContinuationInventory` entry for H. It uses the SAME full baseline,
revision/membership/final Note fold and authentication, then admits only an open
group whose Note is an original/retained F output, whose common parent reaches that
exact Resolution in that role, and whose members/outcomes/head/tips have already
passed genuine H historical authentication. Local-unsealed/independent ownership
is not admitted. It returns counts only, never an authorization/certificate.

All conflict members retain the accepted null-projection/inbox-conflict proof
contract. The current source must still equal the real last applied projection;
Head2 revisions count preserved candidates, source revisions count applies only.
H prepare determines its actual action separately: an open group permits only
accepted conflict preservation; any source-changing mixed apply is blocked. H's
private WeakMap plan, authentic plaintext and original local runtime/scope/lifecycle
remain the only source handoff. N diagnostics and raw DTOs cannot be substituted.
Existing H reconcile's already_applied result means immutable replay recognition;
it does NOT relabel a conflict row/projection or authorize prefix/ACK/capability.

The same source route must validate the predicted outcome. New source ciphertext,
changed Note, immutable candidate, Head2 and genuine inbox proof are atomic under
existing exact inventory/project/whole Note set/identity/dependency CAS. Preserved
conflicts use exact source CAS without source writes. Revocation/request abort/
stale source/crash leave no partial records; restart reconstructs from real bytes.
No new persisted format/token/witness, schema, migration, crypto or wire contract.
This is the explicitly authorized H integration of M/O and existing H preservation;
no separate authority model or source-writer migration was necessary.

### Compatibility and remaining owners

The historical-only path is chosen BEFORE verification, not after N/mixed failure.
Real retained/original H commits made out of server order remain readable with the
accepted old H source predicate. Strict N/O still reject that cohort for mixed
mutation. Legacy open forks, including retained-role apply alongside an original
fork where old H permits it, keep their old behavior. There is no historical rewrite,
new Head1 stand-in or forced conversion to M's stricter ordered source witness.

O ordinary semantics, formats and source CAS are unchanged. Accepted O unit/native
H-history assertions now expect P's new read-only H success; all G/K rejection,
original O applies and immutable/protected/source assertions remain. N/O continue
to reject open forks. Existing G source validation has NOT changed: it requires
F membership and enumerates H-only source transitions, so genuine O changes still
block it. K still requires G before dispatch and cannot inherit H's new admission.
No G mixed-prefix qualification, K routing, Resolution ACK or Note declaration.

### Evidence and validation

P47 and O46 PASS, both isolated maxWorkers1 with fresh genuine setup bounded5000ms.
Affected F/H/G/I/J/K/N/L470 tests across10 files PASS; final failed/skipped0.
Both protocols (Legacy2; Content3 ID0/ID1), four F strategies, actual interleaved
F/H/O owners, original/retained branches, membership/tombstones, Stage/StageOrder
and Content plain prerequisites are covered. Every positive apply/proof comes
from an actual owner. No fabricated applied inbox records or synthetic Head1.
Real valid-AEAD counter/member drift, erased O evidence plus old-ciphertext rollback,
missing proof/sequence, corrupt predicted source, resurrection and grant/lifecycle/
CAS/rollback failures reject without a fallback or partial write. Two protocols
exercise genuine historical out-of-order H compatibility; old H conflict and
all N/L negatives remain. No increased timeout, retry, skip or assertion weakening.

Native O/P superset PASS:8 disk profiles,56 full restarts;64 existing O acceptance
applies plus24 new O interleaves;50 genuine H applies,16 preserved siblings,
32 H replays,8 H native rollbacks,16 H races,8 H revocations,8 H competing tabs,
106 H barriers. Includes close/reopen before/after commit and persisted open forks.
Original wire/F evidence/proofs/untouched tombstones preserved. N write/nonce traps
PASS on new mixed H history; no fork source/cursor/prefix writes, page errors0,
unauthorized HTTP0.80 device PUTs are setup/rebind, not H network behavior.
Typecheck/build PASS with existing Vite warnings; workflow/path/history/diff checks
and protected .pyc hashes PASS. O's5000ms setup/body repair and mandatory isolated
step are retained; P gets an isolated mandatory step. The native O step becomes an
awaited O+P superset to avoid duplicate heavy profiles. No unrelated backend/native
suite or unchanged physical migration rerun. Cloud all6 EXPECTED including Frontend
admin and Android compression packaging; SQLite NOT EXPECTED. P CI pending, not polled.

C21/C21.2 IN PROGRESS, C21.1.06 NOT LOCAL COMPLETE, C21.2.08 NOT CLOSED,
Web89.36%, ready=false. Additional Resolution chains, resurrection, local/own writers,
unrelated-project routing and full production recovery remain blocked. Scheduler,
Content writer/sealing/upload, Note capability and Resolution ACK remain OFF.
All VPS/security/public-release/owner gates preserved. Next requires independent P
acceptance, then a separately reviewed G mixed-prefix slice with explicit fork
barriers; K remains later, not activated transitively through H.

### Простыми словами

H теперь продолжает ветви Resolution после настоящих независимых изменений заметок.
Он проверяет всю цепочку и сохраняет прежние допустимые истории. Конкурирующий
вариант хранится как конфликт и не подменяет текущую заметку. Это не даёт подтверждения
серверу: G/K ещё заблокированы, автоматическая синхронизация и ready не включены.
