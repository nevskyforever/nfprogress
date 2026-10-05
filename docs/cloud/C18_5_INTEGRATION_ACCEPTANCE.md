# C18.5.07 — content/action integration acceptance

Date: 2026-10-05. Branch: `6.0`. Starting HEAD and local `origin/6.0`:
`d34254fef37501e95d7b435f35e3106e6d8eda95`; initial worktree clean.

This is a bounded integration audit of accepted authority families. C18.6 is not
implemented. Official progress remains 77.0%. Local completion and independent
remote acceptance are separate gates; this document cannot independently close C18.5.

## Independent acceptance carried forward

| Slice | Accepted implementation/correction | SQLite / Cloud successful runs |
|---|---|---|
| .01 Note reader/substrate | `c01ed8cd965a0e48fefb4f5b147ff3a99eccca31` | 37014080772 / 37014080630 |
| .02 Note migration/writers | `33f0e1cdd0be7f8f3a216fc7635005160562f26d` | 37057286547 / 37057286590 |
| .03 Map authority | `6b3b19f860a87b9ecf2f4e3ecd835adbb3587833`, correction `6f5ed95f1fb479cce3b3d246179068b918a525f0` | 37107105194 / 37111787798 |
| .04 Document authority | `cb120044763ba4e57094d561ebbbac86b83cc418`, published checkpoint `ef89ff728b1daf179037d61f35042f8c59cc0c2f` | 37124209205 / 37124209225 |
| .05 Progress authority | final `302a5fe1f7cda77bcc248994bf0b40cc1dcc6ad0` | 37144592269 / 37144592250 |
| .06 Game authority | `d34254fef37501e95d7b435f35e3106e6d8eda95` | 37212649560 / 37212649515 |

These are owner/GPT supplied independent results, preserved in
`docs/WORTA_CHECKPOINT.md`; Codex has not polled Actions.

## Registry and crypto domains

| Actual production framing allocation | Codec IDs | Encryption / AAD |
|---|---|---|
| Project metadata, Stage, Stage order | 1, 2, 3 | project C11, 1 / 1 |
| Folder, folder order, membership, project order | explicit closed 4–7 | account, 2 / 2 |
| Content Note | 8 | project C11, 1 / 1 |
| Map | 9 | project C11, 1 / 1 |
| Document | 10 | project C11, 1 / 1 |
| Progress | 11 | project C11, 1 / 1 |
| Project Game | 12 | project C11, 1 / 1 |
| Account Game | 13 | account, 2 / 2 |

`contentActionIntegration.spec.ts` calls every production framer and checks the
actual header slot, then submits all frames to every other reader family. Catalog
mapping is explicit, independent of registry ordering. All accepted content/action
golden vectors remain byte-identical. Native workflow codec filters exercise the
same frozen vectors, and historical Note ordinary v1/resolution v2 tests remain in
both workflows. No ciphertext or historical genesis is rewritten.

Production crypto negatives cover adjacent Note/Map/Document/Progress/Project Game
contexts, another project, user and entity; project/account envelope-domain swaps;
Catalog/Account Game; and hashed Stage map identities S1/S2. No crypto change.

## Dependency DAG and explicit consent

```text
account/device/project binding
  -> authenticated metadata
     -> authenticated live Stage (for Stage owners)
        -> Note / Map / Document / Progress
           Progress/source completion -> Project Game -> Account Game reward
Map -> atomic derived mindmap Note projection
Document -> canonical content; external binding/path remains local
Progress -> local entries, totals and statistics
Game ledgers -> local game_state/read models
```

Production dependency checks use authenticated retained events, owner identity,
causal ancestry and active authority. Multi-tip conflicts preserve all branches;
full-tip decisions use CAS. Timestamp, sequence proximity and projected display
rows are not authority. Existing bounded graph/resource rejection tests are retained.
Stage tombstones retain child histories and block unsafe continuation.

| Family | Reader evidence | Explicit migration / ordinary writes |
|---|---|---|
| Legacy Project HTML Note | established accepted contract | established v1/v2 writer/history retained |
| New Note forms | codec8 declaration on every registered device | explicit begin; ordinary plain/Stage HTML writes afterward |
| Map | codec9 declaration | explicit begin; map editor and derived Note edits share Map authority |
| Document | codec10 declaration | explicit begin; normal save/rename/move/delete uses Document authority |
| Progress | codec11 declaration | explicit begin; normal actual progress uses immutable Progress actions |
| Project/Account Game | independent 12/13 declarations plus Progress prerequisites | explicit begin; admitted source actions form one G/R pair |

Reader advertising, login, inspection, settings opening and background cycling
are not migration consent. Pre-consent ordinary content saves create no migration
outbox. `noteSyncV3Cycle.spec.ts` exercises every family across simultaneous
Note/Document/Progress/Game blockers and proves no begin calls on repeated cycles.

## Mixed acceptance and shared ACK

`test_cloud_c18_content_action_integration.py` uses a real migrated PostgreSQL,
production TS encryption and three separate file-backed native SQLite databases.
Every bridge call reopens its database; no in-memory substitute applier is used.

A contains Metadata, Stage/order, Project/Stage plain Notes, Project/Stage maps and
derived Notes, Project/Stage documents, Progress and Project/Account Game history.
Explicit migration is followed by actual ordinary writes. Lost upload responses
retry exactly the durable sealed candidate, retaining event IDs and ciphertext.

C first advertises only mode3. Ordinary Note8, Map9, Document10, Progress11 and
G12/R13 publication is explicitly rejected as C lacks each respective reader.
Each capability upgrade permits the unchanged sealed candidate. C then imports
all families from retained authenticated mixed history.

B deliberately withholds one Progress proof. A later safe Stage Note is applied
and retained while G/R wait, and the ONE shared ACK cannot cross the hole. Reopen
without network applies the original retained Progress/G/R and fills the prefix.
Remote Progress neither emits another local ProgressAdded nor independently pays
a reward. Reprocessing and self-echo leave one reward. Existing Game native/PG
acceptance additionally covers source commit, partial sealing, lost account reward
response, compensation and exact replay boundaries.

With ordinary Note8 authority active, editing and deleting a derived map Note
emit Map9 only; no Note8 event/tombstone is created. Map application updates the
derived Note rows on all three devices.

B continues Note/Map/Document histories back to A. Semantic comparison excludes
only the established device-local Note revision counter and normalizes the frozen
timestamp equivalence; portable content, canonical documents, Progress projection,
Game tips/reward proofs/projections and maps compare strictly.

Concurrent ordinary Stage Note and Stage Map branches create independent conflicts.
Resolving Map with full tips preserves Note conflict versions exactly. A subsequent
Stage tombstone with all five child families retains rows/history and prevents new
unsafe Progress production. Shared ACK before tombstone is exact; tombstone blocks
its prefix instead of removing child data.

The mixed test checks server routing columns and all emitted entity types. PostgreSQL
holds opaque encrypted objects and frozen routing descriptors, with no content,
map text, document title/path, Progress total or Game balance/reward semantics.
Existing family-specific blindness assertions run in the mandatory Cloud selection.

## Local-only and external boundary

The extended real-PG catalog integration has C1/C2 connected and L1 local in the
same profile. Account order/discovery does not bind L1. Actual local Note save,
Document save, document progress and local Game processing remain local; account
Game migration creates no L1 Project Game owner/events. No L1 project outbox or
server event appears. Cloud project order contains only admitted bound projects.

Document/Progress composition uses separate Doc10/Progress11 events and replay
produces no duplicate progress. The existing mandatory Document acceptance exercises
an explicit Word proposal, source-hash recheck, local external binding, restart and
remote path exclusion. External paths do not become portable document content.

## Deferred/F inventory and coverage guard

| Retained unsupported source | Durable rejection/evidence | Regression evidence |
|---|---|---|
| Note metadata/source/format/resource variants | source rows, encrypted receipt and typed blocker; no ACK | content_note_sync unknown-format/source/resource and migration tests |
| Map unknown data/annotations/extensions | raw candidates and original map/Note projection retained | map_sync unsupported-annotation/local-only tests |
| Document extensions or migration orphans | documents/extensions/orphan rows retained; blocked begin/edit | document_sync extensions/orphans/reopen tests |
| Inconsistent legacy Progress/order/extension | raw entity plus ordered rows retained in candidate; explicit blocker | progress authority source/migration/projection tests |
| Unsupported Game bases/actions/extensions | immutable candidates or OLD/NEW local mutations and blocker; no fabricated reward | game legacy admission, transport and SQLite guard tests |

See `C18_GAME_MUTATION_AUDIT.md` for the frozen ownership/admission classification.
Admitted Game actions remain Progress/completion, native buy/sell and explicit
adopt/full-tip resolution/rebuild/compensation. Streak/freeze, bank, quests/challenges,
specialization/skills, custom awards and item effects remain F where not admitted.
This audit does not add their product semantics.

`test_c18_content_action_integration.py` derives command names from BOTH production
nativeCommand and direct nativeGame<GameCommandResponse> routing. It follows Rust
wrapper/service calls to ledger processing or the guarded SQLite mutation boundary,
and rejects a new direct game_state persistence sink outside the two classified
sinks. Preview is separately proved non-mutating. Thirteen representative existing
and future portable state changes retain exact OLD/NEW evidence, durable blockers,
local state and zero reward/outbox after file reopen. Notification read state and
explicit developer controls retain their accepted local classification.

Game status refresh now observes local changes and inspected idle sync cycles;
a retained deferred action cannot leave an open panel showing stale success.
Chromium verifies refresh without publication and existing consent/conflict/reversal
flows in six locales. Native readers also reuse the existing schema37 visit table
for content Note8/Map/Document/Progress scheduling. Historical Note v1/v2
reader paging retains its stable accepted behavior. Every listed row is rotated durably,
even if decrypt/dependency checks fail, while returned pages remain sequence-sorted.
A native file-reopen test seeds40 retained events in each family: after four pages
of8, the next background cycle receives33–40 instead of repeating1–32. All40
orphan rows remain, ACK stays0, and no outbox/apply proof is fabricated. The existing
Project/Account Game rotation test remains unchanged and passes against the shared
visit records. Visits are local scheduling metadata, not an additional sync cursor.
Existing help already describes this retained blocked state;
no labels, localization keys or help behavior changed.

## Diagnostics and migrations

Native diagnostics test asserts exact TS/Rust allowlist equality. Production
family diagnostics emit admitted codes/counts/subsystems, not content, totals,
paths, Game balances/items, key material or encrypted envelopes. The integrated
acceptance does not add telemetry or diagnostic payload fields.

SQLite latest remains37, no duplicate migration/version. Workflow tests upgrade
all supported prefixes, verify populated36->37 preservation and reopen. Alembic
has one `c18_game_readers` head; real-PG fresh/prior-head/repeated upgrade tests
remain mandatory. No codec14/schema38/crypto version/AAD/cursor is introduced.

## Findings and bounded corrections

| Severity | Finding | Correction / evidence |
|---|---|---|
| P1, resolved | New remote Stage lacked an empty local Progress read model, causing imported genesis to conflict with absent total | Initialize total0/empty entries only on first Stage creation; preserve existing history. Native fresh Stage source assertion and mixed PG convergence. |
| P1, resolved | Open Game panel could retain stale success after a durable deferred mutation until manual inspection | Data-change refresh with unsubscribe and inspected idle-cycle refresh; unit test and Chromium, no automatic migration. |
| P1, resolved | More than one bounded cycle of blocked content events repeatedly hid later owners | Reuse durable schema37 reader visits across Note/Map/Document/Progress; sequence-sort output and retain exact evidence/ACK. Native40-event/family reopen test. |
| P2 | No open task-specific findings | Existing frontend bundle/dynamic-import warnings remain outside this bounded slice. |

No P0 was found. Closure requires P0 remaining0 / P1 remaining0 and ALL mandatory
local checks below passing, followed by independent remote acceptance.

## Exact local verification

Local workflow selections run on macOS with Python3.12 and Node26.4.0
(`--no-experimental-webstorage`, to avoid the existing Node26/jsdom global storage
collision). CI pins Python3.13 / Node20.19.0 and Windows native Rust; independent
remote validation of those environments remains pending. No dependency change.

| Final local check | Result |
|---|---|
| Python SQLite workflow selection | 442 PASS, zero skips; final routing/deferred guard separately rechecked14 PASS |
| Native SQLite workflow selection | 358 PASS in17 filters, zero failures/ignored tests |
| Native content/Game reader rotation | 2 PASS; 40 events/family plus existing mixed Game35-event reopen |
| Cloud mandatory PG/native/crypto selection | 52 PASS, zero skips |
| Cloud focused backend/API selection | 194 PASS, zero skips |
| Final mixed acceptance including derived Note deletion | 1 PASS, zero skips;163.33s |
| Extended local-only catalog acceptance | 1 PASS, zero skips; exact JSON owner key checked |
| Frontend workflow selection | 381 PASS in60 files |
| TypeScript typecheck / production frontend build | PASS / PASS |
| Final cargo check | PASS; existing19 warnings |
| Chromium | PASS: live blocker refresh without publication, consent, conflict/reversal flows, six locales |
| AST/imports, workflow YAML, contiguous migration graph, Alembic single head | PASS |
| Diagnostics equality/privacy | PASS native allowlist test; no family console/println diagnostics |
| Final diff whitespace / protected pyc | PASS / untouched original mtimes and sizes |

Logs from this local run are `/tmp/c18507-{sqlite-ci,rust-ci,cloud-ci,frontend-ci,
mixed-final,local-only,reader-rotation,guard-audit,final-cargo-check,browser}.log`.
The first aggregate Cloud invocation omitted the test database URL and skipped
PostgreSQL tests; it was rejected as evidence and rerun with an explicit isolated
PostgreSQL URL and zero-skip check. The system Node26 WebStorage collision was
likewise resolved by the runtime flag above, without changing application code.

P0 remaining0; P1 remaining0; no open task-specific P2. C18.5.07 is LOCAL COMPLETE /
REMOTE CI PENDING. C18.5 is CLOSURE CANDIDATE / REMOTE CI PENDING, not independently
CLOSED. C18 remains IN PROGRESS, progress77.0%, C18.6 NOT STARTED. Next recommendation
only after independent remote acceptance: C18.6.01 COVER BLOB / REFERENCE /
MISSING-BLOB ACCEPTANCE. Release/registration decision and C21 local-Web-first
sequence remain unchanged. After the authorized push, Codex stops without polling
Actions; expected workflows are Cloud backend tests and SQLite sync substrate tests.


## C18.5.07 Cloud CI runtime correction

Correction baseline: `9b2c7594589b7dfa58b5b7fe83905f0336a7c710`, branch `6.0`,
HEAD = origin/6.0 and worktree clean before this correction. Production files,
protocols, assertions and the three integration fixes above remain unchanged.

### Completed remote run inspection (no rerun or polling)

Owner/GPT independent result: SQLite **37288645324 SUCCESS**; Cloud
**37288645301 CANCELLED**. Frontend admin succeeded (381 + 199 + 48 tests,
typecheck and build). PostgreSQL mandatory acceptance succeeded: **52 passed,
zero skips**, pytest 2026.05 seconds. C18.5 remains a closure candidate.

Stored Cloud run timestamps (UTC): created 2026-10-05 09:13:44, updated 09:54:07.
PostgreSQL job started 09:13:47, completed 09:54:06 (40:19 including cleanup).
The cancellation error was emitted at 09:54:03; configured job timeout was 40
minutes. The stored check-run annotation explicitly confirms:
`The job has exceeded the maximum execution time of 40m0s`.
Setup/container/toolchains/dependencies to first native check:
09:13:47–09:15:12 (1:25). Native checks: 09:15:12–09:18:50 (3:38).
Mandatory step: 09:18:50–09:52:39 (33:49). Focused regression step:
09:52:39–09:54:03 (1:24 before cancellation).

The quiet pytest log confirms at least **72 focused tests passed** at 09:53:20
(37% of 194); buffering prevents an exact final completed count. It does not
record the active node ID when cancelled. The last identifiable test activity is
`test_cloud_encrypted_blobs.py::test_c14_postgresql_constraints_and_c13_roundtrip`:
its nine deliberately invalid blob inserts emitted PostgreSQL constraint errors
at 09:54:01.999–09:54:02.007. These match its `pytest.raises(IntegrityError)`
assertions; they are expected negative-test output, not pytest failures. It is
node 129 of the baseline focused collection; serial ordering suggests 128 prior
nodes completed, but only the 72-dot progress line is an explicit passed-count
record. The exact count at cancellation cannot be recovered from this quiet log.
No pytest assertion/error/failure summary preceded cancellation. Classification:
**CI runtime / 40-minute job timeout**, not a product correctness failure.

### Deterministic coverage manifest

The explicit file lists in `cloud-backend-tests.yml` are the executable manifest;
there is no collection-order or random balancing. All jobs run independently.

| Selection | Old intended files / collected tests | New assignment |
|---|---|---|
| Mandatory ACK / multi-device | 26 / 52 | foundation: 15 / 30; content-action: 11 / 22 |
| Focused cloud / legacy | 14 / 194 | regressions: identical 14 / 194 |
| Native Rust checks | note_sync, account_catalog, account_sync, document_codec, document_sync, progress_ | unchanged commands, once in foundation |
| Frontend admin | three curated groups, typecheck, build | entire job unchanged |

Foundation contains sync, two-device, C15/C17 historical Note (including
three-device conflict), project/C16 bootstrap, C18 metadata/account, structural,
catalog, authority and edge families. Content-action contains Note/Map/Document/
Progress/Game gates and acceptance plus mixed C18.5 integration. Both retain
`Run mandatory sync ACK and multi-device backend acceptance without skips`, with
pytest/tee failure checks and the same zero-skip guard.

Collection comparison uses complete pytest node-ID sets, not only counts:
old mandatory = foundation union content-action; old focused = regressions.
The sets are disjoint: **246 unique Python tests**, no exact duplicates removed,
no unique tests/families lost, no skip/xfail/assertion changes. Native and frontend
selections are unchanged. Server-blindness, all entity families, shared ACK,
two-/three-device, mixed integration and Alembic upgrade/head/round-trip checks
remain selected.

Each matrix expansion and the regression job provisions its own PostgreSQL 16
service and fresh `nfprogress_c1_test` database on its own runner. No shared DB,
cache of mutable DB state, cross-job ordering or dependencies. Existing fixture
Alembic setup and cleanup remain unchanged. Both mandatory shards need Python,
Node/npm production crypto and Rust/headless native dependencies. Regression
files and imported backend/SQLite helpers use Python only; they install no Node,
Rust, native GTK dependencies or frontend npm packages.

Every PostgreSQL job retains **timeout-minutes: 40**; frontend retains 15. Splitting
the former 33:49 mandatory workload itself, rather than merely moving regressions,
provides variance margin. Runtime estimates remain estimates until independent
remote acceptance confirms actual runner timings.

Both push/PR filters retain all previous paths and additionally cover all native
sources/toolchain files, C9 SQLite tests, legacy engine and core dependencies.
Workflow self and cloud docs continue triggering all Cloud jobs. SQLite workflow
filters do not match these Cloud-workflow/docs-only edits; no production edit is
manufactured to trigger it. Accepted implementation SQLite run 37288645324
remains carried forward.

### Correction validation and status

YAML parsing, matrix/service/timeout/trigger checks, pinned-action checks and
`bash -n` for every run command pass. Frontend job, native commands and regression
selection compare equal to the baseline. Collect-only proof: 30 + 22 + 194 = 246.
Single local separated-group execution (sequential pytest sessions, one isolated
PostgreSQL database with existing fixture reset/cleanup, temporary legacy profile;
no production data):

| Group | Collected / passed | Skipped / failed | Wall time |
|---|---|---|---|
| foundation | 30 / 30 | 0 / 0 | 462.82s (7:43) |
| content-action | 22 / 22 | 0 / 0 | 740.64s (12:21) |
| regressions | 194 / 194 | 0 / 0 | 106.10s (1:46) |

Mixed C18.5 and Progress acceptance passed. No frontend/native unit rerun was
needed: their commands are unchanged and passed in the inspected baseline run;
both mandatory groups execute the real native bridge and production crypto.
The local mandatory split is approximately 38% / 62% of test time. Applying that
ratio to the observed remote 33:49 workload, plus the old setup/native overhead,
gives planning estimates near 18 / 26 minutes per mandatory job (not a remote
result or guarantee); the regression job has its own full 40-minute budget.
`git diff --check` passed; protected engine/game_data Python 3.12 bytecode size
and modification timestamps remain identical to preflight. Only the workflow
and these two documents changed.

C18.5.07: **CI CORRECTION LOCAL COMPLETE / REMOTE CI PENDING** after validation.
C18.5: **CLOSURE CANDIDATE / REMOTE CI PENDING**. C18: **IN PROGRESS**. Progress:
**77.0%**. P0 remaining 0, P1 remaining 0. Only independent GPT/owner full-green
acceptance may close C18.5; the correction push does not close it or begin C18.6.
