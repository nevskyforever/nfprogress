# C21.1.06 — protected apply family matrix and prerequisite stop

## C21.2.05 — Content outbound authority design cross-reference

**DESIGN LOCAL COMPLETE / REMOTE CI PENDING — NOT POLLED.** Docs only.
C21.2.04 REMOTELY ACCEPTED — AUDIT ONLY: SHA `13b9ff7b5ef6bfed97f40b563f426aea07f440d1`,
Cloud `39066576774` SUCCESS, all six required jobs SUCCESS (owner supplied).
Content self-echo IMPLEMENTATION BLOCKED; accepted audit is not implementation.
[Browser Content outbound design](../web/C21_BROWSER_CONTENT_OUTBOUND_DESIGN.md)
proposes intent2, own candidate3, authenticated receipt2 and separate self-echo proof2
(inbox9), future v9 format gate with unchanged12 stores/indexes. No format/migration
or implementation is delivered here. Existing peer candidate2/proof1/conflict1/2,
Legacy writer/self-echo, group1 and ACK transport remain frozen. Content writer,
Content self-echo and Resolution remain blocked; current v8 and ready=false unchanged.
Official84.0%; C21/C21.2 IN PROGRESS; C21.1.06 NOT LOCAL COMPLETE.

## C21.2.04 — Content self-echo authority audit

**REMOTELY ACCEPTED — AUDIT ONLY / IMPLEMENTATION BLOCKED — B AUTHORITY ABSENT.**
Exact blocker: **Browser Web has no legitimate current local codec8 writer/outbox/receipt authority from which to prove own Content self-echo.**
C21.2.03A REMOTELY ACCEPTED: SHA `d3a3c1b600eec63851a4a5a1200200d6b6dd9012`,
Cloud39063756905 SUCCESS, all six required jobs SUCCESS (owner supplied).

| Family / evidence | Browser state |
|---|---|
| Peer Content codec8 ordinary-v1 ID0/ID1 | Protected apply YES on admitted routes; original-wire candidate2 + proof1 |
| Peer Content conflicts / mixed Content-Legacy | Preservation YES, unchanged winner and historical proof semantics |
| Own Legacy | Self-echo YES, exact local candidate1 + accepted outbox + receipt |
| Own Content codec8 | Self-echo NO; no production local Content author/seal/candidate/outbox authority |
| Generic protocol3 outbox + receipt | Structurally codec8-compatible; not independent authorship evidence |
| Native/Tauri Content writer/receipts | Separate SQLite runtime; no supported migration into Browser IndexedDB |
| Same account, different source device | Peer; never self-echo based on user identity alone |
| Own Content prefix/ACK | Unqualified event caps prefix/ACK before sequence; later peer apply remains possible |
| Content writer / Resolution / ready | BLOCKED / BLOCKED / false |

Detailed audit of all 18 questions and exact production creators/absence:
`docs/web/C21_BROWSER_PERSISTENCE.md`, C21.2.04 section. Content proof1 and candidate2
retain peer-only invariants. No new self-echo format; functional work stopped.
IndexedDB v8 unchanged; no migration/stores/indexes/backend/native/dependencies.
Official84.0%, C21/C21.2 IN PROGRESS, C21.1 final canonical slice .30,
C21.1.06 NOT LOCAL COMPLETE. No new functional progress or roadmap points.

### Простыми словами

Content от других устройств читается, смешанные конфликты сохраняются. Legacy
self-echo подтверждается собственной историей отправки браузера и receipt сервера.
Content writer в браузере пока не активирован, такой истории для Content нет.
Поэтому свой device id в Content нельзя честно признать доказательством собственной
отправки. Подделывать историю нельзя: Content self-echo заблокирован до настоящей
локальной Content writer/outbox authority. Native/Tauri хранит её отдельно.
Это не ломает peer Content и mixed conflicts. Полная Web-синхронизация ещё не готова;
следующий шаг — отдельный дизайн browser Content outbound authority и proof-контракта.


**C21.2.03A historical normalization:** REMOTELY ACCEPTED; docs only, no functional progress.
Canonical C21.2.03 REMOTELY ACCEPTED, SHA `582c671eed7227250bd7c06b3c34e2f9b379a104`,
Cloud `38852780341` SUCCESS, all six required jobs SUCCESS (owner supplied).
Official84.0%, C21 and C21.2 IN PROGRESS, C21.1.06 NOT LOCAL COMPLETE, ready=false.
The numbering note below is authoritative; technical sections retain their accepted scope.

C21.2.04 local validation (2026-10-18): focused authority boundary10 PASS; peer266 PASS;
Legacy31 PASS; mixed283 PASS; prefix/ACK97 PASS. Mandatory Cloud C21 selection
**1661 PASS / 57 files**, zero skips. Chromium **221 groups PASS**, native IndexedDB
and Web Locks; renderer/full-profile disk reopen retains own Content62 received,
no own outbox/receipt/candidate and no projection writes; peer67 applies/replays;
prefix61/ACK61 cannot cross62. Existing Legacy own60/70 and mixed groups remain valid.
Isolated auth/HTTP fixtures, real storage/crypto, no production Content writer fabricated.
Chromium API134: registration22/capability11/mode42/registry26/bootstrap16/ACK17;
push/pull/Resolution/unrelated0; pageErrors0. Typecheck, production build, modified
browser-script syntax, workflow YAML/mandatory coverage/path filters and
`git diff --check` PASS. Existing bundle-size/dynamic-import warnings only.
Production/backend/native/dependencies unchanged; IndexedDB v8→v8.
Cloud39066576774 SUCCESS, all six required jobs SUCCESS (owner supplied);
REMOTELY ACCEPTED — AUDIT ONLY. Protected engine/game_data bytecode unchanged.

## C21.2.03A — numbering normalization / C21.1 boundary repair

**C21.2.03A NUMBERING NORMALIZATION — REMOTELY ACCEPTED**
(2026-10-17). Docs only; no new functional progress or roadmap increment.

**Authoritative numbering boundary:** C21.1 is capped at 30 slices. C21.1.30 is the
final canonical slice of C21.1. Subsequent work belongs to C21.2.
C21.1.30 remains **REMOTELY ACCEPTED**; C21 and C21.2 remain **IN PROGRESS**.
Official progress remains **84.0%**; C21.1.06 remains **NOT LOCAL COMPLETE**;
`ready=false`.

One-time historical alias map (old execution labels are provenance only):

| Historical execution label (alias only) | Canonical stage | Unchanged SHA | Unchanged Cloud run | Status |
|---|---|---|---|---|
| C21.1.31 | C21.2.01 | `0e9adfb75d47c3f6d094d29d502dc729d11a60bc` | `38787355382` | REMOTELY ACCEPTED |
| C21.1.32 | C21.2.02 | `4302477aa756ab7ee83ff4e3ee63b8030e158b4d` | `38793623485` | REMOTELY ACCEPTED |
| C21.1.33 | C21.2.03 | `582c671eed7227250bd7c06b3c34e2f9b379a104` | `38852780341` | REMOTELY ACCEPTED |

Original commits remain authoritative: `feat(c21): stabilize content conflict lifecycle`,
`feat(c21): accept content siblings after local seal`, and
`test(c21): accept mixed legacy self echo`, respectively.
This is numbering normalization only. No code, implementation, test semantics or
technical work was redone. SHAs and CI runs remain unchanged; Git history is
intentionally not rewritten. No amend, rebase, force push, commit recreation or tag change.

Canonical **C21.2.03** is **LOCAL COMPLETE / REMOTELY ACCEPTED**:
SHA `582c671eed7227250bd7c06b3c34e2f9b379a104`, Cloud **38852780341 SUCCESS**,
all six required jobs SUCCESS (independent owner acceptance): Frontend admin;
Android compression packaging; PostgreSQL cloud and legacy regressions;
PostgreSQL mandatory (foundation); PostgreSQL mandatory (content-action);
PostgreSQL mandatory (complete-project). Production code change: **NONE**; mixed Legacy
self-echo acceptance is test/docs coverage over existing production behavior.

This docs-only repair changes stage labels/provenance/current acceptance status only.
Code, tests, browser scripts, workflow behavior, dependencies and support matrices are
unchanged. Validation: targeted repository searches, exact SHA/Cloud/status mapping,
manual documentation diff review and `git diff --check`; no test suite, Chromium,
backend/native suite, typecheck or build rerun. Expected Actions after push: Cloud
backend tests **YES**, SQLite sync substrate **NO**. Repair Cloud39063756905 SUCCESS, all six required jobs SUCCESS (owner supplied).

C21.2.04 follows this accepted normalization as a bounded authority audit.
No Content self-echo, Resolution, writer, prefix, ACK or conflict implementation is
continued by C21.2.03A.


**Current C21.1.23 update:** Stage reader-ready YES / accepted peer create-update and
ACK-safe subset unchanged; Stage-order reader-ready YES / bounded clean create-update,
complete membership and exact/ancestor head coverage LOCAL COMPLETE. Conflicts/self-
echo/delete remain blocked. v8 unchanged; readyfalse, official84.0%, .06 NOT LOCAL
COMPLETE. See final C21.1.23 audit/result sections; earlier matrices are dated history.


2026-10-12. **C21.1.06 BLOCKED BEFORE IMPLEMENTATION / NOT LOCAL COMPLETE**.
This is an audit, not a new authority/proof protocol or implemented v4 schema.
C21.1.05 / .05A independently accepted by owner/GPT at repair
`af407f751cbda2898eb881f90fdd08177e2b28d3`, implementation
`eed5ed298838c32ddc8f526b4ad2992b4fecd6c4`, Cloud **38165641607 SUCCESS**,
all six required jobs SUCCESS. Official84.0%, C21 IN PROGRESS.

## C21.1.07 prerequisite implementation update

Owner/GPT accepted this audit at `cbd7a294e0e7c7dbbe4f99c0dbfdec5d67b341fc`,
Cloud **38258729038 SUCCESS**, all six required jobs SUCCESS. C21.1.06 remains
BLOCKED BEFORE IMPLEMENTATION / NOT LOCAL COMPLETE; acceptance covers audit accuracy.
C21.1.07 now implements schema4 projectBindings record1 and dormant explicit
preparation/import/registration CAS/read operations. The first durable-lineage
storage prerequisite is implemented; the schema3 absence below is historical.
See [current browser contract](../web/C21_BROWSER_PERSISTENCE.md).

Prepared/registered upload lineage is NOT an admitted native project binding:
atomic complete Note capture/cohort proof is still absent, so capture/completing
are unavailable. Explicit import follows native captured/active/zero-cohort lineage;
future authenticated coordinator owns registry provenance. No caller ready flag,
markReady or pause/resume until durable apply/ACK readiness proofs exist. The store
is not account-wide registry reconciliation or entity authority. Cover material,
protected apply/heads/applied proofs and conflict/orphan remain separate. No family
is implemented by treating mere projectBindings existence as success. C21.1.07
REMOTELY ACCEPTED; official84.0%, C21 IN PROGRESS.

## C21.1.13 registry / positive ACK stop update

**REMOTELY ACCEPTED PARTIAL at f99bbb6beb6e2da84c84ee4ebadafc273e04dd28, Cloud38392639737 SUCCESS, all six jobs; positive ACK correctly BLOCKED.**
C21.1.12 completed Legacy Note bootstrap independently accepted at
cc9bfb567afdbccdc77ce4a8aab84cc204757930, Cloud38386112458, all six jobs SUCCESS.
Explicit current-auth/key-bound full account registry GET reconciliation now validates
ALL descriptors and full expected-old local binding set before ONE atomic state/high-water
commit. Only known bindings update; unknown remote projects block, no auto-import/source.
Bound absence fails whole response; prepared absent remains unregistered. Upload origin
local, imported origin may be peer; per-project frozen count/HI/max preserved, shared
account cursor observation never copied into ACK. Schema6/ten stores unchanged.

Only per-binding remote evidence persists. No backend registry generation/ETag exists;
full-account proof is private/current runtime token and must be refetched after reload.
No durable complete-account proof fabricated from high-water. Readonly ACK prerequisite
inventory validates current inbox/Metadata head/proof joins and diagnoses received-only,
Metadata-authority-only, missing sequence1 and unsupported families, without positive
proven candidate or invented conflict classification. Metadata joins are structural,
not fresh crypto reauthentication or native projection/apply ledger equivalence.

Native contiguous_applied_ack_prefix requires exact family applied/outcome or durable
safe conflict proof for EVERY next sequence through pull. Receipts/active/registry/pull
alone prove none of this. Browser lacks complete Legacy Note protected apply/self-echo/
conflict/native-decision ledger and other-family ledger coverage. Thus no browser positive
ACK/proven write or ACK network operation, even for contiguous Metadata applied rows.
ACK/proven0, always ready:false, no ready phase. Row-only active status requires registry;
current registry diagnosis reports pull/apply/unsupported/ACK-proof prerequisites.
Imported Metadata semantics unchanged. Upload_existing Metadata/Stage/Document/Map/
Content/Progress/Catalog/Game protected apply/capture not added. Cover material and exact
self-echo candidate/conflict/orphan/resolution gaps unchanged; complete-project capture
still absent. C21.1.06 NOT LOCAL COMPLETE, official84.0%, C21 IN PROGRESS, no points.

Local checks: registry29/ACK18/completion49/affected156 =252 PASS; Chromium128 with
registry16/completion15/ACK0/unrelatedAPI0/page errors0; typecheck/build/workflow/syntax/
diff/pyc PASS. Cloud explicit mandatory specs and Chromium; SQLite NOT EXPECTED. No new
backend/PG/native/frozen protocol/crypto contract/dependency. No CI polling. Next proposed
bounded slice: exact Legacy Note retained-inbound protected apply/self-echo/conflict proof
representation before positive contiguous ACK or any separately authorized ready work.

## C21.1.12 exact completing / remote completion update

C21.1.11 REMOTELY ACCEPTED: c1edcbb7befaab1bfff995ae6ef7f61b53e7348b,
Cloud **38380013246 SUCCESS**, all six required jobs SUCCESS, owner supplied.
C21.1.12 REMOTELY ACCEPTED: cc9bfb567afdbccdc77ce4a8aab84cc204757930,
Cloud38386112458 SUCCESS, all six required jobs SUCCESS (owner supplied). Schema6 unchanged.
Exact complete Legacy cohort + immutable receipts produce captured→completing and
frozen max (empty0) in one strict source-of-proof transaction. Full expected-old CAS,
strict phase/counter invariants, exact replay; stale/partial/corrupt/abort fail closed.
Post-capture events never alter frozen count/HI/max. Generic registration cannot
fabricate completing/remote active evidence.

Exactly one bounded isolated production completion POST per explicit pending invocation,
using existing backend endpoint/client/auth and durable completing proof outside IDB.
Backend idempotent active replay verified in actual contracts/tests. Exact matching
active descriptor/count/max/origin/project/bootstrap and safe monotone account cursor
allow a separate strict expected-old commit of remote_state/high-water, phase still
completing. Failure/timeout/lost response/local commit failure retains proof for exact
retry after crash/reopen. Proven active replay requires current exact row, no HTTP.
No new phase/store/schema/backend/frozen contract/dependency. No general coordinator.

This is NOT complete-project sync or upload_existing protected apply. ACK/proven0;
ready always false (active→ack_proof_unavailable). Metadata, other families, Cover/
self-echo/native candidate/reconciliation prerequisites remain unchanged/absent.
Completing22/remote27, affected105/capture31; Chromium119, completion requests15,
unrelatedAPI0/page errors0; typecheck/build/workflow/syntax/diff/pyc PASS. Cloud mandatory
coverage explicit; SQLite NOT EXPECTED. Official84.0%, C21 IN PROGRESS, C21.1.06 NOT
LOCAL COMPLETE. Next: account reconciliation/retained inbound/ACK proof before ready.

## C21.1.11 Legacy Note-only initial cohort update

C21.1.10 REMOTELY ACCEPTED: ffc018af7abeb7a5a696af26db0621640e6f0a5a,
Cloud **38317517321 SUCCESS**, all six required jobs SUCCESS, owner/GPT supplied.
C21.1.09 accepted historical audit remains NOT implemented capture; its main source
blocker is removed. C21.1.06 broader NOT LOCAL COMPLETE; official84.0%, C21 IN PROGRESS.

C21.1.11 REMOTELY ACCEPTED (Cloud38380013246 all six jobs SUCCESS); the following records its bounded implemented capture. Dormant schema6 runtime
captures ONLY canonical eligible live Legacy Notes from verified source snapshot R,
seals normal frozen Note events outside IDB, then source-token/full-binding CAS and
all sealed outbox rows/contiguous ordinals/captured counters commit in one strict
transaction. Only registered/upload_existing/initializing; empty count0/HI0; historical
local tombstones do not invent initial cloud delete. Successful replay freezes original
membership/bytes and excludes later source mutations. No new store/manifest/record
shape: count+HI encode EXACT reserved interval [HI−count+1,HI], not prefix<=HI;
existing monotonic allocator/unique ordinal/immutable body producers prove membership.
Read-only exact receipt join provides counts/complete/max accepted sequence, ignores
unrelated receipts and fails corrupt halves; initial max remainsNULL.

This does NOT close complete-project capture or enable upload_existing Metadata
protected apply. Cover material, native captured candidate/self-echo reconciliation,
other local families, completing/registry completion, ACK/proven/ready remain absent.
Production editor/HTTP/network composition unchanged; no full-project claim or points.
Native unsealed coalescing is not activated: this browser cohort is already sealed.
Focused capture25/status6, affected C21170, Legacy68; Chromium111/API0/page errors0;
typecheck/build/workflow/syntax/diff/protected pyc PASS. Cloud mandatory explicit capture/
status and source/lineage regressions plus browser harness; SQLite NOT EXPECTED.
Next bounded slice: captured→completing/remote bootstrap completion with exact receipt
proof, keeping ACK/ready/full-family capture separate.
See [current capture contract](../web/C21_BROWSER_PERSISTENCE.md#c21111--atomic-initial-legacy-note-cohort--local-complete).

## C21.1.10 canonical local Project/Legacy Note substrate update

C21.1.09 blocker/audit independently accepted at
`be235b79e977f9f14aa573e9a606499f6aa687de`, Cloud **38310226431 SUCCESS**,
all six required jobs SUCCESS. Audit REMOTELY ACCEPTED; capture remains BLOCKED /
NOT LOCAL COMPLETE. Official84.0%, C21 IN PROGRESS. The older source-absence statements
below describe that accepted audit baseline.

C21.1.10 REMOTELY ACCEPTED (Cloud38317517321 all six jobs SUCCESS); the following describes its bounded implemented source. Schema6 adds localProjects/
localNotes record1 in the same database, encrypted complete native Project + eligible
project-owned HTML Legacy Note payloads, stable identity/deletion membership and
safe project-wide source revision. Existing authenticated account AMK leases/object
helpers protect payloads; no new crypto/frame/AAD/dependency. A single readonly
transaction produces complete ordered source snapshot; opaque token revalidates
revision AND all encrypted membership rows inside the same future cohort transaction.
Every local mutation atomically advances source revision with its writes; stale CAS,
abort/quota/revocation fail closed. Native Note revision remains separately preserved.
Native initial capture selects live Notes; local minimal tombstones provide membership
and ID non-reuse evidence, never an invented cloud-delete event for a historic
never-cloud-visible deletion. Deleted projects cannot supply capture source.

This closes ONLY the eligible local source storage/snapshot prerequisite. Repository
remains dormant; production HTTP/editor stores are NOT redirected or imported.
Stage/non-html/map-derived Notes and populated other-family payloads reject. No
cohort capture/outbox/binding phase, cloud-visible delete obligation, native captured
candidate/self-echo reconciliation, Cover material, full-family apply, transport or
ACK/proven readiness proof is implemented. Imported Metadata protection is unchanged.
C21.1.06 broader remains NOT LOCAL COMPLETE, C21.1.09 capture remains blocked.

Local authority34 + migration14 + affected C21122 tests, real Chromium98 cases,
typecheck/build PASS; no plaintext durable, application API0/page errors0; old v5
applied Metadata proof/head/receipts and all eight stores exactly preserved. New specs
explicitly in Cloud workflow and real browser acceptance mandatory. SQLite not expected;
no backend/native/frozen contract changes. Next bounded slice: review explicit Legacy
source consumption and same-transaction initial capture; no complete-project claim.
See [current local authority contract](../web/C21_BROWSER_PERSISTENCE.md#c21110-implemented-local-source--local-complete).

## C21.1.09 complete local initial capture audit / prerequisite stop

2026-10-13. Owner/GPT independently accepted C21.1.08 at
`720aea2d8857de572a706e6332180a08e8d79727`, Cloud **38293629801 SUCCESS**,
all six required jobs SUCCESS. Imported coverless Metadata apply and C21.1.07
lineage prerequisite REMOTELY ACCEPTED. Official84.0%, C21 IN PROGRESS.

**C21.1.09 BLOCKED BEFORE IMPLEMENTATION / NOT LOCAL COMPLETE** under its
explicit source-authority STOP rule. Web Project/Metadata/Progress repositories
select API adapters; Legacy/Content Notes and Maps use project/stage scoped HTTP;
Documents and Game use compatibility HTTP. Pinia/editor refs and browser storage
preferences are not a durable exhaustive source. Run Web.sh's host Python backend
may retain data, but no complete source revision/CAS is atomically shared with
browser IDB. Existing v5 transport/proof stores cannot enumerate never-sealed
objects, unpublished local changes, all family dependencies or pre-existing deletions.
Imported Metadata proof is remote-history proof, not upload-existing local authority.

Exact native Note capture uses IMMEDIATE transaction over canonical SQLite Notes,
new project binding, unsealed intents/outbox ordinals and captured boundary.
Count=Notes rows at capture; HI=max(initial allocated ordinals); cohort requires
account/device/project + note kind + positive ordinal<=HI. Preflight rejects
Stage/map-derived/non-html Notes; other C18 families have separate capture semantics.
Native unsealed edits may coalesce in the same initial membership; sealed follow-ups
get new ordinals. Tombstones cannot be reconstructed from missing UI rows.
Max accepted sequence is persisted at completing only after full scoped cohort
receipt proof; global cursor is insufficient. Detailed family/source matrix,
actual SQL invariants and read-only inspected crash/retry/delete tests are in
[the browser contract's C21.1.09 section](../web/C21_BROWSER_PERSISTENCE.md#c21109--complete-local-capture-prerequisite-audit--stop).

Docs/checkpoint ONLY. v5/eight stores and projectBinding record1 unchanged;
upload_existing remains prepared/registered with 0/0/NULL, no capture/cohort-status/
completing/ready API or fake source/count. Metadata ownerHeads/applied proof unchanged.
No Cover/blob store, native self-echo candidate proof, network, ACK/proven advance
or upload-existing protected apply. Broader C21.1.06 NOT LOCAL COMPLETE persists.

Next independently authorize canonical encrypted browser project/Legacy Note local
source with durable deletion/dependency membership and source snapshot/CAS; document
other-family eligibility before claiming complete-project capture. No substrate
implementation hidden in this audit. Local documentation/source/status/diff/pyc
checks only; runtime suites/Chromium/build NOT RUN. Cloud audit CI expected after
push, SQLite not expected, no Actions polling. Audit publication is not capture
LOCAL COMPLETE and awards no roadmap points.

## C21.1.08 bounded imported Metadata implementation update

Owner/GPT independently accepted C21.1.07 at
`83d6f40c971163d07e1077049df225f4c9fe8964`, Cloud **38285007363 SUCCESS**,
all six required jobs SUCCESS. Durable imported-lineage prerequisite accepted.
C21.1.08 **REMOTELY ACCEPTED** (720aea2d8857de572a706e6332180a08e8d79727, Cloud38293629801 SUCCESS, all six required jobs): schema5 ownerHeads record1,
Metadata project owner, complete ordered causal tips/history metadata, inbox record2
with exact applied proof and unchanged wire. Current normal-user/binding/draining
key lease + frozen Metadata authentication/codec runs before IDB; private opaque
plan and one strict transaction recheck full scope/lineage/bootstrap/expected head,
all retained ancestry and immutable wire/receipt sources, then CLEAN only writes
head+proof+inbox state atomically. Genesis create1/1/no parents, exact causal tips,
native revision/generation; replay never rolls back descendant authority.
No plaintext projection/reconciliation or native active-authority/readiness claim.

Eligible ONLY explicit import_remote/captured/active, Metadata codec1/2 without a non-null Cover reference.
Upload-existing complete capture remains unavailable. Non-null Cover explicitly blocked; codec2 null/removal follows native no-material
semantics and is eligible without adding a blob store.
Self-echo remains received because native captured candidate/pending decision proof
is absent, even with exact accepted upload evidence. Conflict/orphan/rejected/local
incompatibility retain encrypted history without ordinary applied proof or blockers.
No separate apply store, upload-receipt overload, other family, network, ACK/proven
advancement or ready transition. All prior v4 rows preserved and ownerHeads empty
on upgrade. Future schema/corrupt rows fail closed, no fabricated lineage/authority.

Local focused41/migration8/affectedC2173/existing Metadata35 PASS; actual Chromium80
PASS, API0/pageerrors0, auth/key/session/write abort/quota rollback, reload/profile
and isolation/lock transfer. Typecheck/build/workflow/diff PASS. Cloud explicit hard
coverage; SQLite not expected. **C21.1.06 remains BLOCKED BEFORE IMPLEMENTATION /
NOT LOCAL COMPLETE**, Cover material/upload capture and other protected families
remain future prerequisites. Official84.0%, C21 IN PROGRESS, no points.

The following first-prerequisite stop records the C21.1.06 schema3 preflight;
C21.1.07/.08 updates above supersede its browser storage absence.

## First blocking prerequisite: durable project binding and bootstrap lineage

Native Metadata apply checks the installation's existing project binding and
bootstrap record INSIDE its apply transaction, before any apply ledger/head write:
`frontend/src-tauri/src/project_metadata_sync.rs:399` joins
`cloud_sync_project_bindings`, `cloud_account_bindings` and
`cloud_sync_project_bootstraps`, matching local account/project/bootstrap and the
canonical user from the authenticated frame. A valid decrypted event is not enough.
The same module's test
`project_metadata_legacy_binding_without_bootstrap_is_preserved_but_not_publishable`
removes the bootstrap row and proves missing lineage stays blocked; no implicit
binding/bootstrap reconstruction from an event is allowed.

Further production evidence:

- Legacy Note apply in `note_sync.rs:10057` requires project existence plus its
  account binding; missing project becomes orphan. Resolution peer apply and
  own-resolution reconciliation also require that binding (`:9022`, `:9525`).
- Stage `dependency()` (`stage_sync.rs:309`) checks canonical user AND exact
  bootstrap ID, then a proven live Metadata reference and active current authority.
- `account_catalog.rs:839` checks project binding/bootstrap, Metadata event and its
  exact applied ledger. Historic Metadata proof alone is insufficient: current
  authority must be active and its retained ancestry must cover the reference.
- Document/Map `dependencies_ready()`, Content Note `ready()`, Progress/Game
  `dependencies()` call that project-reference boundary; Stage references add
  their own live complete-authority requirements.
- Production `noteSyncRuntime.runGatedWithOptions()` (`:489`) reconciles the
  account-wide project registry before the normal cycle. A dormant repository must
  not pretend that possession of transport ciphertext supplies that gate.

Browser IDB3 has ONLY identities/accountBindings/outbox/inbox/cursors/receipts.
Its account binding is local-account↔canonical-user, not project membership,
installation lineage, bootstrap readiness or account-wide registry readiness.
Its receipts prove upload event/sequence acceptance; its cursor proves transport
position. Neither establishes project binding/bootstrap. Inbox/body event IDs and
AAD project scope likewise cannot prove this installation's admitted lineage.

The frozen browser design already reserves **projectBindings** separately from
ownerHeads. The native DTO `CloudProjectBootstrapRecord` retains project/account/
device/bootstrap IDs, upload_existing versus import_remote mode, closed-enum phase,
remote state/high-water and initial cohort count/ordinal/max sequence. Its admitted
relationship must survive reopen and be compared in the protected transaction.
This is a required prerequisite, not a new browser authority model. No DTO is
implemented or automatically populated in this slice; no source names/paths belong
in such a browser proof.

Putting installation binding into a synthetic owner-head genesis, trusting a
caller-supplied ready boolean, or treating an authenticated Metadata event as an
implicit import would weaken the frozen distinction between installation lineage
and entity authority. Creating projectBindings here would cross the task's explicit
STOP boundary for an additional structurally necessary store. Therefore STOP before
schema migration, crypto-plan builder, owner-head write or applied-proof API.

## Family identity, causality and retained-history matrix

A = local account bound to canonical user U; P = project; S = nullable Stage.
Project families use existing project crypto/AAD1; Catalog/Account Game use existing
account scope crypto/AAD2. Source device differs from pulling device. Transport
sequence, time and maximum revision never select a winner.

| Family | Exact native owner/entity distinction | Complete tips, dependencies and retained history |
| --- | --- | --- |
| Legacy Note | Project crypto; `(A,P,note entity ID)` | V1 primary parent/revision and immutable causal versions/tombstones; complete conflict event/version membership plus group generation when present. Project binding and eligible Note route required. |
| Note Resolution v2 | Same Note owner; optional retained clone is a second Note entity | Sorted complete resolved_event_ids equals primary+additional parent set; conflict-group/generation and exact scoped parent/version/applied-resolution proofs. Keep-both cannot partially advance original/clone. |
| Content Note codec8 | Same Note authority; authenticated project/Stage/source/content format | Existing Note/Resolution history plus codec8 frame receipt; bootstrap/Metadata/Stage references. Map-derived Note has no independent Content Note authority. |
| Metadata, without cover | `(A,P)`; transport entity_id = P | Complete sorted parent_event_ids, revision AND generation, exact bootstrap; all canonical encrypted Metadata ancestors retained. Local source/reconciliation/decision proof affects clean classification. |
| Metadata v2 with Cover | Same Metadata owner; cover blob ID is a dependency, not a separate Metadata tip | Same Metadata tips plus exact cover reference, nonce/ciphertext/envelope hash/size and verified blob material. Reference-only apply is forbidden. |
| Stage | `(A,P,stage entity ID)` | Complete parent_event_ids/revision/generation; exact bootstrap and live Metadata proof. All structural ancestors and relational dependency evidence retained. |
| Stage order | `(A,P,stage_order)`; not one owner per position | Complete causal parent set and exact live Stage membership/head permutation; removals require Stage tombstone proof. Not a timestamp-derived order. |
| Document codec10 | `(A,P,stable document ID)`; Stage relation belongs to history and can move | Sorted complete parents, revision/generation; bootstrap/Metadata/live Stage proofs including prior dependency branches. Stable document ID must not be replaced by `(P,S)` when moving scope. |
| Map codec9 | `(A,P,project-map)` or exact `stage-map-<sha256>` ID | Sorted complete parents/tips, revision/generation; bootstrap/Metadata/live Stage references. Map and its derived Notes form one semantic apply unit. |
| Progress codec11 | `(A,P,scope_id(S))`, where native scope_id is project or stage:S | Complete causal tips and retained entry/chain history; revision/generation, bootstrap/Metadata/Stage and unit proofs. Progress order is a derived relation, not a separate authority. |
| Catalog codecs4–7 | Account crypto; `(A,entity_type,entity_id)` for folder/order/membership/project_order | Complete parent_event_ids/tips, revision AND generation; exact folder/membership dependency maps and project bootstrap+Metadata proof tuples. Incompatible live dependency sets are conflicts, never silently dropped. |
| Project Game codec12 | Project crypto; owner `(A,canonical [P,S])`; per-action entity ID is NOT the owner | Complete parent/action chain and retained snapshots/proofs, bootstrap/Metadata/Stage plus matching Progress/reward dependencies and stable action identity. |
| Account Game codec13 | Account crypto; native owner account; game:<event ID> identifies an action | Complete action parents/tips, project-action/reward/streak/compensation dependency proofs and exact native rule checks. Not a Catalog folder variant. |

## Outcome and proof matrix (existing production semantics, not Web implementation)

All rows first require exact authenticated frame/envelope/descriptor/scope and
retained dependency proof. Crypto/decompression/semantic decode belongs to the
current draining auth/key lease outside IDB, with temporary byte buffers cleared.
An exported structural DTO or a caller's outcome='clean' cannot manufacture that
verification. No concrete browser apply-plan/proof record is designed past STOP.

| Family | Clean/replay/self-echo rule | Non-clean and future ACK evidence |
| --- | --- | --- |
| Legacy Note | Clean causal parent/head and compatible current Note/local intent; already_applied requires exact causal history match. Own echo checks outbox+receipt identity/sequence and current head, not source-device equality alone. | Missing project/parent → orphan; competing proven versions require conflict preservation; incompatible format/identity → rejected/error. Future ACK needs exact inbox/object/history or preserved-version proof, not the TS result conflict alone. |
| Resolution | Peer apply validates full tips/generation/parents and all original/clone mutations atomically. Exact applied-resolution replay uses its immutable proof. Own resolutions route ONLY through resolution reconciliation with canonical outbox/decision/continuation/receipt evidence. | Missing parents → orphan; self_echo_pending is not applied. Future ACK needs complete applied-resolution parent/result proof; upload receipt alone is insufficient. |
| Content Note | Existing Note/Resolution outcome plus exact authenticated codec8 frame/envelope/dependency receipt in the SAME transaction. | Unsupported frame/source/format/dependency remains blocked/orphan/rejected. Future ACK joins exact content receipt with underlying Note/resolution history. |
| Metadata / Cover | Exact bootstrap, complete parent/generation transition and compatible local/reconciled source. Own echo needs exact immutable event/envelope/receipt semantics and must preserve newer visible local state. Replay matches retained canonical payload/object/ledger. | Missing binding/lineage/material cannot apply; concurrent/local disagreement remains conflict-preserved/blocked. Future ACK requires exact Metadata ledger plus required Cover material proof. |
| Stage / Stage order | Metadata dependency active; exact complete parents/generation and compatible local structural state/membership. Self-echo uses exact sealed native evidence; replay matches canonical frame and ledger. | Missing Metadata/Stage proof → waiting/orphan; changed membership/local branch → conflict. Future ACK requires exact structural frame/envelope/ledger and relational dependency proof. |
| Document / Map | Compare complete old tips against parents AND current local/retained projection or explicit decision; verify dependencies for ancestors as required. Own native sealed/accepted event must match exact frame/envelope/sequence and decision/local rules. Exact applied ledger replay does not move heads again. | Incompatible tips/local edits → conflict_preserved; missing parents/deps/unsupported projection → waiting. Native apply commits complete tips, history, ledger and inbox classification together; future ACK cross-checks all immutable pieces. |
| Progress | Verified dependency units and rebuilt causal chain, complete tips plus compatible local source/decision. Own source alone is not proof; replay is exact retained event/ledger evidence. | Missing parent/unit/chain proof blocks; incompatible competing chains remain conflicts. Future ACK needs exact frame/envelope/ledger and chain proof. |
| Catalog | Recompute parent revisions AND generations; validate dependency coverage and compatible local catalog source/explicit decision. Replay matches exact frame/nonce/ciphertext ledger; pre-existing own receipt sequence must agree. | Missing/unproven references → blocker; incompatible live sets/local state → conflict_preserved. Native account inbox may REMAIN received even after ledger apply: future ACK uses the exact Catalog ledger/history, not that state. |
| Project / Account Game | Rebuild owner action chain; verify stable identities and reward/dependency rules; compatible local source or explicit decision. Own classification checks prior sealed material/local matching; no one-size self-echo shortcut. Replay uses exact frame/envelope/sequence/ledger. | Missing dependency/parent → waiting; noncommutative/local conflict retained. Future ACK requires matching event/ledger/snapshot and applicable blocker classification. One accepted genesis cannot imply multi-owner migration complete. |

For requested C21.1.06 clean-only semantics, EVERY orphan/conflict/rejected/unknown
outcome would leave browser inbox received and heads unchanged. Native preservation
outcomes above are documented for fidelity; implementing their blocker/conflict
engine or marking them applied is NOT authorized as a shortcut in this slice.

## Further scoped boundaries found; no extra stores created

Cover `project_cover_sync.rs:95` require_material loads the exact reference and
remote_verified material before Metadata apply (`project_metadata_sync.rs:404`).
Browser wire_item contains Metadata's encrypted event/reference, not the separately
transferred cover blob. Correct no-plaintext Web rebuild requires retained encrypted
blob material and authenticated reference proof; the planned encryptedBlobs boundary
needs its own reviewed implementation. No plaintext JPEG/projection can be copied
from native storage into browser IDB. Cover-bearing events cannot be downgraded to
cover-less success. This is an additional family blocker, not the first stop reason.

Account-only Catalog/Account Game events without project references do not
necessarily need projectBindings individually. They were NOT declared impossible
or implemented after the global prerequisite STOP. Their native clean classification
also compares retained/local source/decision and migration state; a narrower
account-only implementation requires its own explicitly bounded scope and proof
review. No unsupported claim that one generic ownerHeads record covers every family.

The protected-apply proof could potentially evolve versioned inbox records while
keeping wire_item immutable, as the task permits. No separate proof store has been
proven necessary at this stop point, and no proof format/store/digest/boolean is
invented here. ownerHeads remains planned; upload receipts stay upload-only.

## Audit result and next bounded prerequisite

Production browser/native/backend/crypto/protocol files are unchanged. IDB remains3,
all six stores/record versions unchanged, inbox received, ACK/proven prefix0.
No protected apply, network, projection mutation, editor/bootstrap/reconciliation
runtime or conflict/orphan engine is activated. No v4 migration or test/CI contract
for protected apply is claimed. No new dependency.

Read actual reader/apply modules, relevant tests and frozen designs, including
native missing-bootstrap, exact replay, self-echo, dependency and rollback cases.
No runtime tests/builds run for this documentation-only stop. Verify documentation
references, status consistency, diff scope and protected pyc hashes instead.
Cloud workflow already watches docs/cloud/**; this audit publication triggers
Cloud but cannot make unimplemented C21.1.06 locally complete. SQLite not expected.
Codex does not poll Actions or remotely accept the implementation.

Historical C21.1.06 next bounded proposal (subsequently implemented/accepted in C21.1.07):
projectBindings/bootstrap-lineage persistence and readiness-proof lifetime/CAS,
using the existing native DTO/registry rules, with no network/bootstrap activation.
After that foundation is accepted, resume family-specific protected apply; separately
bound Cover encrypted-material prerequisites and conflict/orphan/resolution handling.
Do not auto-create binding from a downloaded frame or trust caller-supplied readiness.

## C21.1.14 native outcome audit (before implementation)

C21.1.13 REMOTELY ACCEPTED PARTIAL: f99bbb6beb6e2da84c84ee4ebadafc273e04dd28,
Cloud38392639737 SUCCESS, all six required jobs SUCCESS (owner supplied).
Sources: note_sync.rs apply_received_note_with_content (9889+), read_entity_sync_head
(5515+), causal history/replay (7703+), conflict preservation (7744+), contiguous ACK
(6693+); tests peer create/update/delete/replay (1126–1256), own echo after newer local
mutation (1310–1338), timestamp/exact replay, preserved conflicts/restart (1574–1703),
resolution head/dependencies and same-project/device isolation. TS remote apply and
Note codec/protocol inspected. No schema or production implementation preceded audit.

| Native outcome | Local authority mutation | Durable material | ACK-safe | Replay |
| --- | --- | --- | --- | --- |
| applied | Peer insert/update/delete; exact causal head/revision | Causal history + entity head + applied inbox | Yes for ordinary Note | Exact history/envelope match → already_applied |
| already_applied | None | Existing exact history/outcome | Same proof as original applied | No new revision/writes |
| self_echo_applied | No Note reapply, even after later local change | Exact own accepted event/receipt/sequence; causal history, monotone head, applied inbox | Yes | Already applied; newer current Note preserved |
| conflict | None | Plain marker is insufficient | No | Remains blocking |
| conflict_preserved (reported conflict) | None | Independent immutable local+remote versions, group/common parent/generation, >=2 full tips and retained parent/history | Only after native joins verify preservation | Exact remote version/group replay |
| rejected | None | Final diagnostic state, no safe outcome | No (ACK CASE excludes it) | Blocking rejected |
| orphan | None | Missing project/parent/dependency; retryable | No | Retry once prerequisites available |

Native local Note payload revision is reset to0 by note_payload_from_record; cloud
semantic revision is separate head/causal-history revision, never project source_revision.
Create requires no head AND no existing live Note. Update/delete require exact preceding
head revision and parent; unresolved competing head or local unsealed mutation blocks.
Native apply checks admitted local project/account binding, not a fresh registry token.
Browser eligible imported captured/active and upload completing/active with exact cohort
proof can admit retained-only apply without a new GET. No ready or counters change.

Conflict STOP: current local encrypted Note can later change and does not preserve its
old branch; retained remote ciphertext alone lacks immutable local candidate versions,
conflict group/generation/full tip set and resolution decision proofs. No conflict_proven
marker or new store/schema. Rejected/orphan remain received/unproven. Resolution and
unsupported routes remain unproven. Clean peer apply/self-echo require exact causal
history and local source CAS; otherwise stop that event. Positive ACK/proven forbidden.

### C21.1.14 implemented boundary after the native audit

REMOTELY ACCEPTED PARTIAL:65e4fe4cc712162e1436970f9f6a62afbe9416d8,
Cloud38402330568 SUCCESS, all six required jobs (owner supplied). Schema6/ten stores unchanged. Explicit retained
Legacy Note reader uses normal auth/account/key/session, frozen codec/object crypto,
opaque plans and same-transaction private source mutation. Active imported captured and
upload completing with full complete receipt proof admitted; fresh registry not required
by native retained apply. No network or automatic local source creation.

Clean peer create/update/delete and causal head/parent/revision, current encrypted source
matching prior peer proof, atomic encrypted membership+Note+inbox outcome and source CAS
implemented. Native local payload revision0 is separate from cloud revision/source version.
Same/fresh exact replay does not rewrite source/proof/counters; old proof does not certify
current modified source as clean. Exact initial self-echo requires immutable accepted
outbox/receipt/protocol/sequence/device/wire; no Note/source mutation, even after newer
local edit. Receipt cannot be synthesized; source-device equality alone is insufficient.
Note inbox record3 outcome applied/self_echo_applied keeps exact original wire, strict
reference/header/SHA256 and peer encrypted projection digest/source version; accepted
received1/Metadata-applied2 unchanged, no inferred old-row upgrade or new store/index.

Native conflict independent immutable local/remote version/group/generation/full tips/
resolution substrate is still absent; no safe conflict proof. Dirty local source or
sibling head stays received/unproven. Own-head peer-child needs captured source and
native unsealed-generation history; current authority/outbox alone cannot certify it.
Rejected and orphan remain blocking; parent-dependency orphan can retry. No Resolution,
Metadata upload_existing, Stage/Document/Map/Content/Progress/Catalog/Game/Cover apply
added. Cover/material/conflict/decision/orphan-resolution/full-project capture gaps
unchanged. Readonly inventory recognizes Note applied and self-echo structurally, but
ACK/proven0 and eligible:false/ready:false remain mandatory; no positive aggregation.

Note31 incl self-echo8, record19, ACK18, affected278 =346 unique tests PASS; Chromium135,
apply-network0, prior registry16/completion15/ACK0/unrelatedAPI0/page errors0. Typecheck/
build/workflow/syntax/diff/protected pyc PASS, existing warnings only. Cloud explicit
mandatory coverage; SQLite NOT EXPECTED, no skips or CI polling. C21.1.06 NOT LOCAL
COMPLETE, official84.0%, C21 IN PROGRESS. Next proposed bounded substrate: encrypted
immutable local candidates/conflict versions with full causal tips/generation/decision
and own-head clean-source history, before any ACK aggregation or ready transition.

## C21.1.15 native mapping before implementation

C21.1.14 accepted partial:65e4fe4cc712162e1436970f9f6a62afbe9416d8,
Cloud38402330568 SUCCESS, all six required jobs SUCCESS, owner supplied.
Audit sources: note_sync.rs prepare_legacy_note_intent_with_id(5769+), initial capture
(5236+), sealed generation CAS(6370+), read_entity_sync_head(5515+), visible snapshot
comparison(4997+), preserved conflict(7744+), ACK(6693+), Resolution validation(8040+).
Tests inspected: initial capture/retry/source mutation; sealed-next-parent(12539+),
coalescing update/delete generation; conflict preservation/restart/later coalescing
(1614+), deletion/tombstone conflicts, multi-tip historical generations, stale decisions,
self-echo/Resolution and rollback. No production edits preceded this table.

| Native durable structure | Bounded Web equivalent | Creation/immutability/ACK |
| --- | --- | --- |
| Sealed initial outbox + intent snapshot generation1 | Immutable candidate in one new Legacy-only history store; frozen encrypted C15 item/header, local source anchor for NEW capture | Same source-CAS/outbox/counter TX; no receipt required to preserve history; historical event immutable |
| Applied causal history snapshot(local payload revision0) | Authenticated encrypted retained event candidate, peer projection anchor | Same peer authority+inbox TX; old explicit first use can reconstruct event from exact outcome/wire, never current content |
| cloud_sync_entities current head + sealed own head | Compact head record with linear head and complete sorted causal frontier; every tip backed by candidate | Expected-old whole Note history CAS; no latest-sequence/LWW; unresolved branches retained |
| conflict groups/versions/tips | Tagged group record in SAME store, references independent immutable candidates; random persisted UUID, common parent, tip revision, per-member introduction generation/source/sequence, complete tips | Atomic inbox+candidate+group+head; starts1, +1 for distinct compatible sibling; exact replay no generation change |
| local_unsealed intent + snapshot + mutation_generation + ordinal | NOT approximated: current Web has no unsealed outbox/intents/ordinal producer | Starts1 per newly allocated event; coalescing same event increments generation independent of cloud/local revisions; blocked portion until exact writer/allocator bridge |
| user decision/pending Resolution v2 | Existing open group identity, exact common parent/tips/generation/source/sequence retained; no decision or Resolution generated | Future frozen Resolution needs complete tip equality, current conflict generation, max revision+1 and local publication/generation proof |

Native conflict_preserved is individually ACK-safe ONLY with exact same-account/Note
remote version, group, preserved marker and >=2 complete tips. Both immutable branches
survive later mutable edits; ordinary conflict/rejected/orphan remain blocking. Native
retains canonical local branch on conflict. Local-unsealed preservation cannot be
claimed by assigning source_revision or native Note payload revision to generation.
Sealed ordinary Legacy outbox is not automatically a local_unsealed conflict version;
only applied causal history or a real unsealed intent qualifies. No Content writer reuse.

Plan structural necessity: v7 adds ONE tagged legacyNoteHistory store (candidate/head/
group), no generic family store or new dependencies. v6 ten stores preserved exactly;
no migration inference. New initial capture adds immutable source-at-capture anchor;
old cohort backfill decrypts exact initial outbox/cohort proof only, anchor unavailable
if it was not durably retained. Never synthesize historical local anchor from current
Note. Clean own continuation needs exact anchor/receipt; absent historical anchor or
post-seal local mutation stays explicitly unproven. Peer-applied sibling conflicts can
be represented with independently recoverable encrypted versions and exact native
open-group tips; local unsealed/delete-edit cases without Native intent material STOP.
No positive prefix, ACK, ready, other-family apply/capture or Resolution activation.

### C21.1.15 implemented coverage and precise remaining stop

PARTIAL LOCAL COMPLETE / local-unsealed writer/generation/allocator and missing old
capture anchors BLOCKED; remote CI PENDING — NOT POLLED. v7 ONE new tagged
legacyNoteHistory store with immutable candidate, expected-old compact head and open
group records. Ten v6 stores preserved exactly; structurally validated, no inference,
no crypto across versionchange. Candidate history wire + optional exact encrypted
source anchor is independently authenticated with existing AMK/Note tuple/codec; data
survives later local edits. New initial capture commits history/head with sealed outbox,
source CAS and counters. Generation1 from native initial intent, peer null; never reuse
local/source/cloud revision as generation. Old explicit cohort backfill from exact
immutable event/cohort evidence succeeds, missing local anchor stays unavailable.

Clean new own-head continuation with exact anchor/receipt implemented; dirty current
source stops without destroying old parent. Peer clean apply and native-qualified
remote-applied sibling conflict retain exact independent versions. Random persisted
group UUID, common parent/tip revision, complete deterministic tips, member source/
sequence/introduction generation and current conflict generation; canonical local Note
unchanged. New compatible sibling increments generation once; replay stable. Later
local edit cannot destroy old versions. Applied update vs peer delete, applied delete
vs peer update and concurrent deletes retained. Active linear descendant frontier and
frozen group Resolution tips separate; unresolved branches never discarded. Different
fork while native first group remains open stays unproven, no second safe group.

Strict inbox4 conflict-preserved proof ties exact retained event to current complete
candidate/group/version/sequence/outcome joins. Individually native ACK-safe for this
qualified preserved subset, not a generic conflict marker. old1/2/3 byte-compatible.
No positive prefix/ACK/cursor/ready/Resolution operation. Resolution group/tips/generation/
source/material data retained; future decision/local publication proofs not invented.

Local-unsealed conflict STOP remains exact: Native unsealed outbox + intent snapshot,
reserved ordinal and same-event generation/coalescing producer are not represented by
current Web localNotes mutations or sealed-only transport outbox. Creating those requires
a separately bounded native-equivalent writer/allocator bridge; no guessed generation,
fake candidate from current state or unreviewed outbox lifecycle redesign. Old initial
source-at-capture anchor absent also remains unavailable. Genesis/rejected/orphan and
unsupported resolution remain blocking. Other families/Cover unchanged, full-project
capture/apply absent. .06 NOT LOCAL COMPLETE, official84.0%, C21 IN PROGRESS; no points.

Local evidence: history20/conflict+own21/migration13/Legacy31+proof19/ACK18/affected278
=400 unique tests PASS; Chromium145, existing registry16/completion16, new candidate/
conflict/apply0, ACK0/unrelatedAPI0/page errors0; typecheck/build/workflow/syntax/diff/pyc
PASS, existing warnings only. Mandatory Cloud specs and Chromium; SQLite NOT EXPECTED.
No skips, dependencies or frozen backend/PG/native/protocol/crypto changes, no CI polling.

## C21.1.16 native producer state table BEFORE implementation

C21.1.15 owner acceptance: a386161d07b2918a30af4c2dae7328068adad914,
Cloud38426555539 SUCCESS, all six jobs SUCCESS, REMOTELY ACCEPTED PARTIAL.
Audited lib.rs direct create/update/delete interception (2926–3290), note_sync.rs
resolve_project_cloud_binding4841, allocator5497, combined head5515, producer5769,
list5909, failure6287, seal6366 and direct/coalescing/delete/restart/rollback tests
11026+,12542+,12762+,12857+, conflict later-coalescing1614+.

| Previous | Source mutation | Event/ordinal | Cloud revision/parent | Mutation generation | History effect |
|---|---|---|---|---|---|
| none | create | new UUIDv4/new account-device ordinal | 1/null | 1 pending | none before seal |
| unsealed create | update | same/same | same/same | +1 pending/reset failure | none |
| unsealed create | delete | same/same, operation delete | 1/null retained | +1 pending | tombstone, NOT removal |
| sealed create | update | new/new | sealed head+1/head ID | 1 pending | old candidate immutable |
| unsealed update | update | same/same | same/same | +1 pending | none |
| unsealed update | delete | same/same, delete | same/same | +1 pending | none |
| sealed update | update | new/new | combined head+1/head ID | 1 pending | old candidate immutable |
| sealed + peer head | update | new/new | higher exact combined head; equal different IDs error | 1 pending | no arbitrary tip |
| unresolved group | update/delete | coalesce existing or new/new | native linear combined head, unrelated tips retained | +1 or1 pending | group versions stay frozen |

Native unsealed is excluded from read_entity_sync_head; sealing removes intent and
stores immutable envelope+sealed outbox atomically. CAS compares expected generation;
exact sealed-envelope replay returns already_sealed, changed envelope errors.
Native failure key/size/dependency/unsupported = blocked; runtime = retryable_error;
invalid payload/context/metadata/envelope = invariant_error. Explicit dormant Web
invocation needs no native round-robin cursor/backoff scheduler; next_attempt_at null.
Native binding helper does not check bootstrap; Web bridge additionally requires actual
active import/captured or upload/completing with complete exact initial cohort, because
no ready/ACK is enabled. Missing/initializing/prepared/registered/captured-upload blocked.

Storage decision: v8 ONE dedicated legacyNoteIntents store. Accepted v7 history API is
an immutable cloud-visible inventory; mutable unsealed snapshots and failure lifecycle
must remain separately typed and excluded from its frontier and candidate event index.
All eleven old stores unchanged and structurally validated, zero synthesized intents.


### C21.1.16 implemented producer coverage

LOCAL COMPLETE for explicit dormant Legacy-only canonical create/update/delete producer
and immutable seal bridge. v8 ONE legacyNoteIntents store, unique Note/event/ordinal
constraints; exact v7 eleven-store structural validation and zero inferred intents.
Original encrypted canonical source and AEAD intent identity bind scope/bootstrap/event/
parent/cloud revision/ordinal/mutation generation. Atomic canonical mutation + intent/
allocator, native coalescing and exact create→delete tombstone retained. Unsealed excluded
from cloud head; next parent joins actual applied/outbox head, not arbitrary preserved tip.

Current-generation frozen Note sealing atomically removes intent and stores normal
immutable outbox + local_sealed candidate with source-at-seal anchor/generation + full
causal frontier. Exact same-envelope replay stable; changed envelope/stale lineage/
revoked auth/key/abort fail closed; stale generation leaves newer intent untouched.
Native bounded blocked/retryable/invariant codes, explicit retries only, no loop/backoff.
Open conflict permits native linear local branch update/delete while frozen groups and
unrelated complete tips remain unchanged. New own receipt/self-echo/peer-child compatible.

Historical source-at-seal now available for NEW writer events. Old missing capture
anchors remain unrecoverable; no current mutable Note inference. Local-unsealed inbound
conflict/version proof is next bounded protected-apply work; not inferred from intent
presence. Resolution publication/decision/runtime and cross-family positive ACK proofs
remain absent. No other-family/Cover/ready changes. ACK/proven0, eligible:false/ready:false.

Local new63 + prior affected400 =463 unique tests PASS, Chromium157 PASS including real
v7 corruption/quota/abort upgrade exact11, encrypted pending/sealed restarts, coalescing/
create-delete/ordinal/source-CAS/seal rollback, stale crypto/key/logout, exact anchors,
self-echo/peer-child and open-group branch/full frontier. Existing registry16/completion16
fixture requests only; producer/new sync/apply/ACK0/unrelatedAPI0/page errors0.
Typecheck/build/workflow/syntax/diff/protected pyc PASS; mandatory five new Cloud specs.
No dependencies/backend/PG/native/frozen contracts/skips; SQLite NOT EXPECTED. Remote CI
PENDING — NOT POLLED; official84.0%, C21 IN PROGRESS, .06 NOT LOCAL COMPLETE.

Native lib.rs require_note_writable1022 additionally forbids completed project status
`завершен`; dormant writer enforces it before source mutation/intent reservation.

## C21.1.17 native transition table BEFORE production

C21.1.16 accepted92a66776c0b5d30295a9533ad561e89f6a5e5193, Cloud38440249775
SUCCESS/all6 jobs SUCCESS; REMOTELY ACCEPTED. Audited note_sync.rs7744–7939
preserve_causal_note_conflict, inbound10161+, causal_edit_conflict1614+ and restart1693+,
delete/update1724+, revision1 collision3142+, ACK6693+ and Resolution8040+/9360+.

| State/incoming | Native outcome | Frozen version / live intent |
|---|---|---|
| unsealed sibling, same known non-null parent, same revision>=2, different event, visible matches exact snapshot/local revision (delete means absent) | new random UUIDv4 group/gen1, two tips, inbox conflict_preserved | local:account:event:mutation_generation, independent snapshot; live intent unchanged |
| compatible open group / distinct sibling | reuse group, generation+1, append only remote version | original local generation frozen; later mutable intent not substituted |
| changed local source before first preservation | ordinary unproven conflict | no synthetic branch |
| genesis/null parent/wrong revision/parent | ordinary unproven conflict | no group |
| incoming child of unsealed event | unproven local_unsealed_change, not clean apply | unsealed excluded from combined head |
| incompatible open group | ordinary unproven conflict | no second group/merge |
| exact replay | original preserved outcome | no generation/version changes |
| later local mutation | same unsealed event/ordinal/revision/parent, generation+1; operation may change | frozen original local version stays independent |
| later seal | ordinary generation-CAS sealing allowed | no reparent/freeze/delete because of conflict; group/tips/version unchanged |

Native initial local version source=local_unsealed, server_sequence=NULL,
local_mutation_generation=N, local_outbox_lifecycle=unsealed; version identity includes N.
Canonical Note/source unchanged. Remote version binds actual sequence/event/snapshot.
ACK SQL individually permits conflict_preserved only with exact group/remote member and
>=2 full tips; aggregate prefix not authorized. Resolution requires frozen local generation,
snapshot, exact tips/group/current generation plus later publication/receipt/decision proof;
coalesced live generation cannot impersonate original frozen publication material.
Storage: v8 unchanged. New strict local_version tag in legacyNoteHistory has NO top-level
event_id, avoiding accepted unique candidate event index and permitting later same-event
sealed candidate independently. Group local member references generation-specific version;
cloud-visible candidate frontier excludes local_version; group tips include its event.


### C21.1.17 implemented coverage / remaining aggregate prerequisites

LOCAL COMPLETE for native-qualified retained peer vs exact current unsealed intent. v8
unchanged, no stores/index/migration. Strict local_version stores independent encrypted
snapshot and authenticated intent identity, native local:account:event:generation version
ID, header/ordinal/parent/revision/frozen generation and digest/lifecycle; no event index
entry or fake sealed candidate. Group local_unsealed member has null sequence and exact
local generation. Crypto outside TX; all retained/local intent/source/history/head/group/
lineage expected-old evidence rechecked in ONE conflict outcome write TX.

Canonical local Note/source revision/live intent unchanged. Known-parent same-revision>=2
sibling and exact visible snapshot required initially. Existing compatible group appends
remote only/gen+1; original frozen local branch remains independent of later coalescing,
delete and ordinary sealing. Complete group tips include pending local event; cloud-visible
candidate frontier excludes it until actual seal. Later same-event sealed generationN+1
coexists separately, never masquerades as original conflict generationN publication.
Group and unrelated tips persist; no resolve/reparent/automatic seal/deletion/decision.
All local update/delete/remote update/delete combinations preserve tombstones and known
parent content; exact replay after edits/seal stable, changed/corrupt evidence fails.

Inbox4 strict proof2 binds frozen ID/local generation/digest; old proof1/Note3/Metadata2/
received1 unchanged. Native ACK safety established from exact remote-member/group/full tips
SQL; readonly inventory additionally authenticates frozen encrypted evidence and rechecks
its snapshot before joins. Incomplete/received/rejected/orphan/unqualified cases blocking;
proven_prefix0/ack_cursor0/eligible:false/ready:false. No aggregate proof/cursor write/network.
Qualified Legacy individual coverage is sufficient to begin NEXT bounded ACK aggregation
AUDIT. Remaining cross-family/Metadata/Cover gaps unchanged; no whole-project/ready claim.
Resolution publication/receipt/exact original generation/snapshot and user decision proofs
still separate; current live/sealed generation cannot replace frozen snapshot silently.

58 new focused +463 affected =521 unique PASS; curated28 files512 PASS before nine added
negatives, final three suites58 PASS. Chromium165 PASS: real generation race/rollback/
key/logout, independent encrypted versions/canonical preserved, coalescing/delete/append/
later seal/full tips, three delete combinations and renderer/disk-profile reopen.
Existing registry16/completion16 fixtures only; new conflict/apply/ACK0/unrelatedAPI0/
page errors0. Typecheck/build/workflow/syntax/diff/pyc PASS; three mandatory Cloud specs;
SQLite NOT EXPECTED. No skips/dependencies/backend/PG/native/frozen contracts/other-family
changes. Cloud PENDING — NOT POLLED; official84.0%, C21 IN PROGRESS, .06 NOT LOCAL COMPLETE.

## C21.1.18 ACK audit BEFORE production

Owner accepted75599e9809a7d3be5facc0e5abc46e845e5c51cd, Cloud38451825537 SUCCESS/all6.
Audited native note_sync.rs6693–6839 contiguous/prepare/commit; SQLite ACK repository,
NoteSyncDeviceAckAdapter and retry/auth tests; backend sync_router173+, encrypted V2/V3
ACK routes, services.py344 registration/990 ACK/449 compression-reader gate; native
V2/V3 cycles mode/capability prerequisites; Web durable identity/auth and dormant factories.

| Account sequence outcome | Individually safe | Prefix |
|---|---|---|
| Note3 applied / exact already-applied replay | exact authenticated original proof + durable candidate/lineage | yes |
| Note3 self echo | exact immutable outbox/receipt/wire/history | yes |
| inbox4 proof1 preserved applied/sealed conflict | complete group/member/candidate/tips/proof | yes |
| inbox4 proof2 preserved local-unsealed conflict | above + independent frozen generation/AEAD/digest | yes |
| received Note, orphan, rejected, ordinary unproven conflict | no safe persisted proof | stop |
| Metadata2 authority-only | not Native general ACK ledger | stop |
| Stage/Document/Map/ContentNote/Progress/Catalog/Game/Cover/other | missing Web ACK-safe apply proof | stop |
| missing expected sequence <=pull | absent | stop, never jump |

Native walks ACCOUNT-WIDE from ack+1 until first unsafe/missing event; duplicate IDs/
sequences corrupt. Web will authenticate whole historical proven range too, retain durable
separate prefix and never infer from max Note/pull. Native commit monotonic/expected-old,
recomputes safety, already_acknowledged/already_advanced/stale; server success/lost response
or local failure leaves safe retry. Server ACK is max(last_ack,cursor), bounded by current
account sequence, requires authenticated registered user/device, transport-mode equality
and compression_id1 reader declaration where required. last_ack_cursor metadata never
copies into local cursor.

ACK NETWORK STOP: durable Web UUID and normal auth are valid and PUT registration exists,
but current Web has NO authenticated current writer-transport/cutover/compression-reader
prerequisite flow. Native adapter default protocol1 is incompatible with encrypted account
mode2/3; choosing V2/V3 from retained row protocol or declaring Native compression support
would invent authority. Registration alone does not establish these prerequisites.
Current dormant Legacy reader does not supply full C15 compression reader registration.
Implement prefix-only; no registration/capability/cutover/ACK requests or new backend.
Diagnostic ack_transport_unavailable after explicit fresh registry token where applicable;
no durable registry proof. v8 cursor shape unchanged; no synth positive values on open.


### C21.1.18 implemented aggregation / precise transport stop

PARTIAL LOCAL COMPLETE: explicit authenticated account-wide contiguous prefix/persistence
complete; ACK HTTP/local ACK writer not implemented. Exact safe classes: Note3 applied/
original replay/self echo (receipt/outbox join), inbox4 conflict proof1 complete applied
versions/group/tips, conflict proof2 exact independently encrypted unsealed generation.
Current keys verify candidate/projection/frozen intent/retained wire/outcome before private
plan; ONE strict expected-old whole proof/cursor transaction recomputes and writes only
proven_prefix. Reopen bounds0<=ack<=proven<=pull, no open/migration synthesis. v8 unchanged;
old1–7 zero-only migration contract retained. Source/phase/ordinal/ACK immutable here.

Cross-family matrix remains exact audited table: received/orphan/rejected/unproven Notes,
missing expected sequence, Metadata authority-only, Stage/Document/Map/ContentNote/Progress/
Catalog/ProjectGame/AccountGame/Cover/unsupported all STOP. Never max Note sequence or skip;
subsequent safe events retained. All old proven history revalidated explicitly; corrupted
historical cursor/proof rejects whole operation, no weaker replacement prefix.

ACK prerequisite missing in current Web: safe authenticated current writer-mode/cutover/
registered-device/required compression-reader flow. Durable UUID and normal auth valid;
PUT registration exists but alone insufficient; default Native protocol1 ACK incompatible
with encrypted mode2/3. No guessing V2/V3 from event protocol or claiming reader capability.
No server last_ack_cursor copying/network; fresh runtime registry token remains explicit
non-durable prerequisite. Diagnostic ack_transport_unavailable; no ready. Frozen Native/
backend ACK monotonic/idempotent/lost response and local-failure semantics audited; actual
transport disabled. Next bounded prerequisite bridge then explicit bounded ACK/commit,
without other-family proof invention. Cross-family protected apply remains separate.

41 new +521 affected =562 PASS/31 files; Chromium171 PASS with prefix3→5→7, received/missing/
Document barriers, legitimate original Note apply, abort/key/logout, account isolation and
renderer/disk-profile reopen. Final prefix7/ACK0/pull9/readyfalse. Existing registry16/
completion16 fixtures only; new ACK/registration/sync0/page errors0. Typecheck/build/workflow/
syntax/diff/protected pyc PASS, three explicit mandatory Cloud specs, SQLite NOT EXPECTED.
No skips/dependencies/backend/PG/native/frozen contracts. Remote PENDING — NOT POLLED;
official84.0%, C21 IN PROGRESS, .06 NOT LOCAL COMPLETE. Checkpoint includes mandatory
Russian plain-language subsection while retaining full technical evidence.

## C21.1.19 — current contract matrix (before production edits)

Accepted .18: `6de5183e1fddcac4e4e4d1f8c70d4b3f47799bce`, Cloud
`38568720231` SUCCESS / all six jobs SUCCESS / REMOTELY ACCEPTED PARTIAL.

| Web capability | Actual implementation / durable evidence | Frozen server field/value | Safe declaration |
|---|---|---|---|
| Device identity | v8 identities + accountBindings, exact user/account/device validation | PUT v1 devices UUID; authenticated user owns composite key | Yes: identity only, empty body |
| V1/C9 | Shared HTTP registration; no browser V1 production sync cycle | Response protocol_version=1 is registration envelope, not account mode | Registration only; no V1 writer claim |
| Encrypted V2 | Exact Note transport retention/upload bodies and Legacy Note protected apply | writer_transport_version=2 via account capabilities | No cutover or writer declaration |
| Encrypted V3 | Mixed encrypted retention; Legacy Note and Metadata authority subset | reader_transport_version=3 via reader-ready | No complete V3 reader-ready declaration |
| Compression ID0 | Legacy Note JSON v1/v2; Metadata codec1/coverless2 protected authority | per-family compression_zero only; defaults false/0 | No family capability: legacy Note is not framed Content Note8 |
| Compression ID1 reader | Shared bounded pako decoder exists/tested in Chromium; Web lacks canonical family apply for codecs1–13 | compression_id1=true means ALL canonical codecs1–13 alongside ID0 | NO; cannot turn shared decompression into family reader evidence |
| Compression ID1 writer | Shared frame selector exists; no complete browser writer flow | compression-writer admission sets sticky account read barrier | NO request |
| Legacy Note codecs | noteSyncCodec canonical JSON v1 ordinary only; no Resolution apply; ordinary protected apply, durable candidate/conflict evidence | note_codec_version=1 denotes framed Content Note8, not JSON version | No Content Note capability |
| Metadata reader | durable imported authority only; not general native ACK equivalence/cover blob apply | reader-ready and cover capability are separate | No reader-ready / cover declaration |
| Writer mode | Account authority only, not per-device/all-family attestation | GET /api/v2/sync/encrypted/capabilities: writer_transport_version + cutover_epoch | Read-only authoritative source for future ACK; never infer from inbox |
| ACK | proven prefix durable; ACK adapter absent | mode-specific v1/v2/v3 ACK + registered device + sticky ID1 check | BLOCKED; no compression barrier/device capability query in registration reply |

Current source audit: sync_router PUT devices is the ONLY device registration route;
SyncService.register_device has no mode check and Native noteSyncV3Cycle uses the
same syncApi.registerDevice through NoteSyncDeviceAckAdapter. Historical C9 is
**A: still authoritative**, also valid in mode2/3, not legacy-only. Reply exact keys
protocol_version/device_id/last_ack_cursor; no capability or mode fields.
Repository INSERT ON CONFLICT DO NOTHING preserves ACK and existing capabilities;
only last_seen_at changes. New SyncDevice defaults reader_transport_version=2
(the pre-V3 baseline), every family reader=0 and compression_id1=false. These
defaults are not a Web publication of a family reader; repeat does not downgrade
an upgraded device. Model closed CHECKs prohibit generic new reader values.

Native registration uses current auth/binding and durable device; modes come from
parseV2Capabilities, cutover uses expected epoch/account lock; v3 requires all
registered reader_transport_version=3. Writer mode routes account writes/ACK and
does not assert every device implements every family. Native Metadata runtime
separately advertises compression, reader-ready and cover support; family runtimes
separately declare Note8/Map9/Document10/Progress11/Game12/13. Those runtimes are
not wired into Web persistence. C18.7 explicitly defines compression_id1 as ALL
canonical codecs1–13; compression_zero never implies ID1.

ACK endpoints: /api/v1/sync/ack, /api/v2/sync/encrypted/ack,
/api/v3/sync/encrypted/ack (204); exact account mode required. Service locks
account then device, requires registration and applicable ID1 support, rejects
cursor beyond current_sequence, monotonically accepts duplicates/lower retries.
Native commits local ACK only after confirmed HTTP success; lost response and
server-success/local-failure permit exact retry. Registration last_ack_cursor
never authorizes local advancement. Existing GET compression aggregate ready
does not expose sticky compression_id1_required or this device's capability.
Identity-only registration is safe, but it cannot prove the ACK activation gate
for an existing compressed account. STOP before ACK/capability/cutover; no backend
change, v9, store or dependency. Existing .18 barriers/ready=false unchanged.

Chosen bounded implementation: explicit authenticated identity-only registerOnce;
read-only durable scope checks before and after response, strict response allowlist,
no local registration cache/authority write. Registration remains server-authoritative
and each explicit call retries the same UUID. No mode selection is needed for this
mode-independent operation. No downgrade PUT or unsupported capability declaration.

### C21.1.19 implementation evidence

Registration-only PARTIAL LOCAL COMPLETE. `deviceRegistration.ts` implements one explicit
PUT using current NormalUserAuthRuntime, AuthoritativeAccountBinding and the SAME durable
v8 identity, read-only scope checks on both sides of HTTP. Exact three-key reply; no mode/
capability inferred or persisted, no additional capability API called. Server ACK metadata
never writes local cursor. Registration repeat preserves existing server capabilities and ACK;
no second identity/no local cache. `cloudSession.ts` retains its Tauri-only runtime gate;
Native NoteSyncTransportRouter selects fresh authenticated capabilities and is not composed
into this Web persistence factory. Registration factory is dormant, no app startup hook.

C18.7 sticky barrier checked by backend ACK and actual PostgreSQL gate tests; new legacy
registration in a compressed account remains correctly blocked until exact reader upgrade.
ACK implementation STOP for unproven ALL-codec ID1 reader contract, not because C9 route
is obsolete or because mode is guessed. No generic capability invented or cap downgraded.
Mode endpoints remain valid/audited for a future explicit bounded ACK. No ready or Metadata
ACK equivalence, no other-family apply/Resolution. All .18 barriers unchanged.

106 tests/10 focused files PASS, registration28; real Chromium177 cases PASS. Registration11,
ACK/push/pull/Resolution0; prior bootstrap completion16 + registry16 only; page errors0.
Profile/reload identity and prefix7/ACK0/pull9/barrier8 unchanged, full12-store snapshot exact.
Real browser HTTP uses isolated fixtures; no new live PostgreSQL/backend run required for
unchanged frozen implementation. Typecheck/build/YAML/syntax/diff PASS, existing warnings.
v8 unchanged/no stores/migration/dependency/backend/Native changes. Cloud mandatory contract
job includes new spec and existing Chromium job includes helper; CI PENDING — NOT POLLED.

## C21.1.20 — reader contract audit BEFORE production edits

C21.1.19 `deda194d8bbb7c5409964971cf2d868fb0c985dd`, Cloud38577509647/all6
SUCCESS REMOTELY ACCEPTED PARTIAL. Exact interrupted nine-line block removed with
owner authorization; clean HEAD/origin verified before new checkpoint edits.

Frozen C18.7 compression_id1 means bounded authenticated ID1 reading on canonical
codecs1–13 alongside ID0. Service.declare_compression_reader only changes that bool;
compression-reader PUT returns204. ACK requires that bool only after sticky account
admission, plus registered device/exact account mode/cursor<=server sequence. It does
NOT require family apply ledgers, writer admission or reader-ready. Separate device
family fields and reader-ready cover family/transport activation; Native Metadata
runtime advertises compression separately BEFORE protected apply. Reader contract is
authenticate→bounded normalize→strict owning canonical decoder→context validation,
not local authority mutation. Previous .19 conservative blocker can be resolved by
proving this entire shared read surface, without advertising family apply support.

|ID|Family|Frame codec versions|Existing canonical decoder|Browser safe/native required|Canonical validation|ID0 / ID1 vectors|Malformed rejection|Reader-ready before registry|Blocker before registry|
|---|---|---|---|---|---|---|---|---|---|
|1|Project Metadata/cover reference|1,2|unframeProjectMetadata|Yes / No|exact fields, version, canonical bytes|MetadataV2 + shared frame vectors|Yes|NO integrated surface; pure reader YES|Missing authenticated registry/matrix evidence|
|2|Stage|1,2|unframeStructuralEvent|Yes / No|causal/full tips, exact schema/canonical|stageCodecV1 + v2 tests/shared compression|Yes|NO integrated surface; pure reader YES|Missing authenticated registry/matrix evidence|
|3|Stage order|1,2|unframeStructuralEvent|Yes / No|ID/body family, exact order/heads|stage order golden-derived tests/shared compression|Yes|NO integrated surface; pure reader YES|Missing authenticated registry/matrix evidence|
|4|Folder|1|unframeCatalogEvent|Yes / No|exact catalog dependency/schema/canonical|accountCatalogV1/shared compression|Yes|NO integrated surface; pure reader YES|Missing authenticated registry/matrix evidence|
|5|Folder order|1|unframeCatalogEvent|Yes / No|exact order/dependencies|owning catalog tests/shared compression|Yes|NO integrated surface; pure reader YES|Missing authenticated registry/matrix evidence|
|6|Folder membership|1|unframeCatalogEvent|Yes / No|exact project/folder dependency proof|owning catalog tests/shared compression|Yes|NO integrated surface; pure reader YES|Missing authenticated registry/matrix evidence|
|7|Project order|1|unframeCatalogEvent|Yes / No|exact membership/project dependencies|owning catalog tests/shared compression|Yes|NO integrated surface; pure reader YES|Missing authenticated registry/matrix evidence|
|8|Content Note (embedded ordinary1/Resolution2)|1|unframeContentNote|Yes / No|owning C15/C17 serializers + portable Note|contentNoteCodecV1/shared compression|Yes|NO integrated surface; pure reader YES|Missing authenticated registry/matrix evidence|
|9|Map|1|unframeMapEvent|Yes / No|graph/domain IDs/canonical + WebCrypto SHA|mapCodecV1/shared compression|Yes|NO integrated surface; pure reader YES|Missing authenticated registry/matrix evidence|
|10|Document|1|unframeDocumentEvent|Yes / No|bounded Tiptap/domain/canonical|documentCodecV1/shared compression|Yes|NO integrated surface; pure reader YES|Missing authenticated registry/matrix evidence|
|11|Progress|1|unframeProgressEvent|Yes / No|integer micros/facts/domain/canonical|progressCodecV1/shared compression|Yes|NO integrated surface; pure reader YES|Missing authenticated registry/matrix evidence|
|12|Project Game|1|unframeGameEvent(project)|Yes / No|scope/domain/action/canonical|gameCodecV1/shared compression|Yes|NO integrated surface; pure reader YES|Missing authenticated registry/matrix evidence|
|13|Account Game|1|unframeGameEvent(account)|Yes / No|scope/domain/action/canonical|gameCodecV1/shared compression|Yes|NO integrated surface; pure reader YES|Missing authenticated registry/matrix evidence|

No Tauri/SQLite imports in owning decoders; Map uses browser WebCrypto only.
Generic compressed vectors prove framing, not canonical entities: integrated tests
must authenticate actual owning fixtures for every ID/version, force ID1 (small
fixtures need not pass writer policy), then compare exact validated canonical data.
IDs6/7 use existing owning-test examples where no standalone golden exists. No new
wire truth. Explicit registry rejects unknown ID/version and wrong crypto context;
project v1 AEAD / account v2 AEAD remain unchanged. Decompression after AEAD only.

Registration/capability operations separate; runtime opaque evidence tied to owner
auth epoch/session/scope, no store. Capability exact PUT{device_id,compression_id1:true},
empty204 required; no writer/family/reader-ready request. Mode from authenticated
V2 capabilities, never inbox. ACK fresh mode chooses v1/v2/v3 exact existing endpoints;
204 required, monotonic server duplicates/lower retries safe (SyncService.ack).
Local target exclusively committed prefix, original crypto/CAS inventory and fresh
registry revalidated; strict cursor-only commit after server success. Missing/apply
barriers unchanged even if a canonical object becomes readable. No ready/schema change.

### C21.1.20 bounded result

**LOCAL COMPLETE / REMOTE CI PENDING — NOT POLLED**, bounded canonical-reader/capability/
ACK surface only. Official84.0%, C21 IN PROGRESS, C21.1.06 NOT LOCAL COMPLETE; no roadmap points.
Owner-approved cleanup removed only exact interrupted mode-2 preflight block; clean accepted
HEAD/origin verified before new edits. .19 `deda194d8bbb7c5409964971cf2d868fb0c985dd`, Cloud
`38577509647` SUCCESS / all six jobs SUCCESS / REMOTELY ACCEPTED PARTIAL recorded.

Exact contract/matrix BEFORE production in family audit. Reader means authenticated bounded
ID0/ID1 normalization followed by owning canonical/domain validation, not protected apply.
All13 pure TS decoders already existed; integrated Web registry/authenticated proof was missing.
Matrix: ID1 Metadata versions1/2; ID2 Stage and ID3 Stage order versions1/2; IDs4 Folder,
5 Folder order,6 Folder membership,7 Project order,8 Content Note,9 Map,10 Document,
11 Progress,12 Project Game,13 Account Game version1. Content Note embeds ordinary1/Resolution2.
All owning canonical/schema/domain validators reused; no duplicate format or apply extraction.
`openBrowserCanonicalObject` authenticates project-v1/account-v2 AEAD BEFORE dispatch or
normalization, exact family/version/reference binding; unknown/malformed/future data fail
closed. Shared C18 limits/checksum/single-stream/length/ratio rejection unchanged. No storage,
network, apply, writer or readiness side effect. Frozen owning/golden and TS/Rust compression
vectors remain regression inputs; matrix uses canonical fixtures/owning test examples for6/7.

Separate explicit dormant operations: `session.device.bind(auth,binding).registerVerified(scope)`
issues ONE identity PUT and mints opaque runtime evidence; old registerOnce result unchanged.
`session.readers.bind(auth,binding).declare(scope,deviceToken)` reads authoritative authenticated
V2 capabilities then exact existing PUT compression-reader-capabilities{device_id,compression_id1:true}.
Empty successful response required; before/after read-only durable scope/auth/session checks.
No family declaration, reader-ready, cutover, compression-writer/admission. WeakMap evidence
binds auth instance/epoch/session/account/device and current registration; no local cache/store.
Reload uses same device and separate explicit registration/redeclaration. Existing server caps
are never downgraded by these calls. Server registration last_ack_cursor remains metadata only.

`proven.prepareAck(scope,readerToken,registryToken)` authenticates original prefix inventory,
requires current registration/reader evidence, current registry/exact bindings and existing
pull-caught-up prerequisite. Target ONLY DURABLE proven_prefix, never calculated-but-uncommitted
prefix/pull/high-water/server ACK. Opaque prepared token; no registration/capability/discovery
inside ACK. Fresh authoritative mode/epoch in prepare AND before send; changed mode rejects
without fallback. Exact existing mode1/2/3 endpoints, maxONE ACK HTTP per invocation; empty
success required. Conservative legacy ackStatus receives no reader token/mode proof and remains
fail-closed; activation uses the explicit gated API. No broad orchestration/background loop.

After confirmed success private strict transaction rechecks current auth/key/session/reader/
registration, entire authenticated inventory CAS and registry, recomputes structural prefix,
checks expected-old ACK and cursor bounds, writes ONLY ack_cursor. Auth invalidation abort
listener and session close abort pending transactions; native IDB completion precedes success.
ACK-only concurrent progress/replay is safe; changed prefix/pull/history/lineage requires new
explicit preparation. Lost HTTP response or local commit abort leaves local ACK old; exact
retry server duplicate monotonically accepted. Lower stale target never decreases state.
Readable-but-not-applied Document/Stage/Map remain unsupported-family barriers; Metadata
received/authority-only remains proof gap. C21.1.18 aggregation unchanged. ready=false always.
Schema8→8, no stores/index/migration/dependency/backend/Native/frozen-contract changes.

Checks: **381 unique tests /19 focused files PASS** (initial376 + five additional race/evidence
cases; final reader/ACK file44 PASS). Canonical matrix152 includes all16 ID/version pairs,
ID0/ID1 equivalence, eight malformed categories each, authentication/context and frozen bomb/
limits/concatenation rejection. Reader/ACK44 includes modes1/2/3, response/capability/registry/
identity evidence failures, stale source before and after HTTP, logout/key/close, lost response/
local abort/retry, replay/lower target, four readable-family barriers. Existing owning codec,
compression-vector, prefix/identity/open/migration regressions PASS; no skip/xfail.

Real Chromium **181 groups PASS**: all13 IDs/all16 versions, ID0/ID1 equivalence +128 malformed
matrix checks, all12 stores unchanged by reading; real registration/ID1-only capability/current
mode3/registry gates; failure→lost response→registration metadata7/localACK0→server success/local abort→exact retry ACK7; only
cursor changes; replay no HTTP; reload/disk reopen device unchanged/proven7/ACK7/pull9, Document8
barrier and Note9 retained; stale auth revokes runtime evidence, readyfalse/page errors0.
TotalAPI67: identity registration15 (prior11 + new4), capability4, modeGET9, ACK4, bootstrap
completion16 (prior unchanged), registry19 (prior16 + new3), push/pull/Resolution/unrelated0.
HTTP responses are isolated fixtures faithful to frozen backend semantics, not live production
server verification. Modes1/2 verified in focused tests; Chromium bounded ACK uses mode3.

Typecheck/production build/YAML/JS syntax/diff/protected pyc PASS; existing Vite warnings only.
Mandatory Cloud contract job includes canonicalReaders.spec.ts and readerAck.spec.ts; existing
mandatory Chromium gate invokes reader/ACK helper. Cloud EXPECTED, SQLite NOT EXPECTED; no
Actions polling. Early invalid test fixtures/canonical comparison corrected, no remaining failure.

## C21.1.21 — Native Metadata audit BEFORE production edits

Accepted .20 SHA5214e2941b7b6fbbcce7f74d297f5be7859ef5d9 / Cloud38587064713 /
all6 SUCCESS / REMOTELY ACCEPTED. Clean fetched6.0 verified before checkpoint.

Exact Rust project_metadata_sync::preserve_authenticated_event_checked validates
canonical bytes, bound account/bootstrap, exact retained object/reference, cover
material before ledger replay. Apply ledger canonical_payload/outcome joins event
project/server sequence/state in note_sync::contiguous_applied_ack_prefix(6737+).
Individual applied and exact applied replay ACK-safe YES; inbox flag alone NO.
Conflict-preserved is safe ONLY through matching completed native metadata event/
apply ledger outcome and durable full causal branch history/tips; Web lacks this
class and will NOT promote conflicts. Orphan/missing parent and received-only NO.
Self echo needs exact local candidate/decision/event state/header/canonical payload,
outbox/object/receipt; sealed lost-response path recovers a matching receipt in the
same transaction (native test project_metadata_lost_upload_response_self_echo_is_durable_and_ack_safe).
Device equality alone NO; Web local Metadata producer/decision representation absent.
Cover reference invokes project_cover_sync::require_material before successful
apply; absent/null cover needs no blob. Web cover-bearing NO. Reconciliation is
local visible project projection safety, distinct from applied cloud authority;
ACK ledger does not require a reconciliation row. No local UI projection added.

Native causal rules: retained applied/conflict parents must exist, revision max
parent+1, generation above parents; exact current full tips permit clean applied,
other branches preserved without LWW. Web captured imported active lineage only,
matching bootstrap, peer event, coverless, no local Metadata outbox. ownerHeads
proof/history + immutable inbox2/applied are sufficient durable evidence for this
bounded class ONLY after canonical cryptographic proof reproduction. No new store.
Web ordinary clean create/update/delete linear history is the promoted subset;
Resolution/self echo/conflict/orphan/upload-existing remain excluded.

Plan: opaque runtime Metadata certificate binds scope/current auth/key/session and
exact retained rows/head/history/lineage/outbox/receipts anchors. Crypto outside IDB
using accepted canonical reader and the SAME Metadata proof/digest constructor.
New Metadata crossing authenticates complete relevant causal history; existing
proven historical Metadata may retain prefix using durable scalar + strict complete
structural/digest joins without redundant decryption merely to retain it. No scalar
imports or reconstruction of a missing applied proof. Whole prefix/ACK transaction
CAS rechecks exact original inventory and current certificate; any concurrent
head/lineage/row/cursor/auth change aborts all. Metadata without current certificate
remains barrier. Generic structural diagnostics alone do not authorize Metadata.

One necessary correction: old Metadata apply commit still required ACK/proven=0.
Use existing shared cursor validator 0<=ACK<=proven<=pull instead, preserving values
unchanged; otherwise already-proven Note1 would prevent supported Metadata2 apply.
This changes no Metadata eligibility/source transition. Legacy Note/ACK transport
semantics and every other family barrier unchanged. v8/no store/index/migration.

### C21.1.21 bounded result

**LOCAL COMPLETE / REMOTE CI PENDING — NOT POLLED**. Accepted .20 SHA
`5214e2941b7b6fbbcce7f74d297f5be7859ef5d9`, Cloud `38587064713` SUCCESS,
all six required jobs SUCCESS / REMOTELY ACCEPTED. Official84.0%, C21 IN PROGRESS,
C21.1.06 NOT LOCAL COMPLETE; no roadmap points. Native outcome/ledger audit and
eligibility table BEFORE production in protected family audit.

Project Metadata reader-ready YES; protected apply remains PARTIAL. Only clean
import_remote/captured/active, exact bootstrap, peer, coverless create/update/delete
successful inbox2/applied now ACK-safe after current cryptographic proof. Complete
ownerHeads history must be one exact ordinary causal chain with correct revision/
generation/parents/server order/tip, every proof joined to original applied inbox.
No local Metadata outbox/candidate/decision compatibility inferred. Self echo,
conflict, orphan/received-only, Resolution, cover-bearing/material and upload_existing
remain barriers/unsupported; no new source/project projection/reconciliation/writer.

`metadataPrefixProof.ts` opaque WeakMap certificate contains current scope/non-secret
immutable anchors and safe sequences only, no plaintext/key. New Metadata crossing
revalidates full relevant retained causal history through accepted authenticated
canonical reader, then reproduces exact existing `metadataProofFor` fields/digest.
AEAD→authenticated ID0/ID1→owning canonical decoder→cover absence→proof match, all
OUTSIDE IDB. Wrong/corrupt/unavailable new proof cannot qualify; structurally invalid
inventory fails closed. Already-proven historical Metadata may retain durable prefix
using strict complete joins/causal checks/exact wire digest without redundant Metadata
decryption merely to retain existing prefix. This does not infer new applied outcomes.

Prefix plan includes certificate; strict same transaction rechecks whole original
inventory (binding/head/history/inbox/outbox/receipts/cursors) and certificate anchors/
current auth/key/session before recalculation and cursor-only commit. Concurrent
mutation/revocation/abort rolls back all. Structural calculator WITHOUT current
certificate still treats Metadata as barrier. ACK inventory distinguishes certified
Metadata from authority-only when certificate supplied; generic diagnostics remain
conservative. Legacy Note classes and account-wide no-skip order unchanged; only
recognized safe outcome set broadened. No other-family barrier removal.

Necessary supported-flow fix: Metadata apply's obsolete ACK/proven==0 check replaced
by exported SAME shared cursor validator 0<=ACK<=proven<=pull, preserving all cursors
unchanged. Thus Note1 already proven/ACK1 does not prevent valid Metadata2 apply.
Record2/applied, head/proof history and v8 remain unchanged; no new durable marker,
store/index/migration. Exact replay cannot roll back descendant authority.

Existing bounded ACK implementation/network payloads/endpoints untouched; only shared
prefix evidence gains Metadata. Note1/Metadata2/Note3→prefix3→explicit ACK3; received
Metadata2→prefix1/ACKmax1. ACK still targets committed prefix only; no server cursor
import, registration/capability/registry discovery hidden in apply/proof. readyfalse.

Checks: **381 unique tests /12 focused files PASS** (initial380 + final ordinary-delete
case; Metadata proof38 and Metadata ACK4 PASS), covering ID0/ID1, exact replay, positive
cursor-preserving apply, complete joins/hash/scope/header/causal tampering, certificate
forgery, missing evidence, stale prepared head/row/lineage/cursor, auth/key/close/abort,
self echo/conflict/missing-parent/cover/upload-existing exclusions, historical no-decrypt,
Metadata-only and mixed prefix, missing/Document barriers, ACK lost-response/local-abort/
replay. Existing Metadata apply/migration, Legacy Note/prefix/ACK, canonical reader and
persistence migration regressions PASS. No skip/xfail/continue-on-error.

Real Chromium **184 groups PASS** (prior181 + three Metadata groups): isolated two-account
Note1/proven1→ID1 Metadata2 applied→Note3/prefix3/ACK3 and ID1 received2→Note3/prefix1/ACK1;
real prefix abort/key lock/logout/isolation safe, current separate gates; reload/disk
reopen prefix3/ACK3, exact authority/history/bytes and applied replay preserved. Proof/
prefix operations HTTP0; new explicitly invoked gates only: registration2/capability2/
modeGET6/registry2/ACK2. Total harness API81: registration17/capability6/modeGET15/registry21/
ACK6/bootstrap completion16, push/pull/Resolution/unrelated0, page errors0. Isolated HTTP
fixtures model frozen server semantics; not live production backend verification.

Typecheck/build/workflow YAML/JS syntax/diff/protected pyc PASS; existing Vite warnings.
Two new specs mandatory in Cloud contract job, Metadata helper in mandatory Chromium
runner. Cloud EXPECTED, SQLite NOT EXPECTED. No backend/PG/Alembic/Native/Rust/SQLite,
dependencies/frozen contracts; no Actions polling. Initial oversized/missing-source
fixtures corrected; no remaining failures. Internal dormant infrastructure only, no
public UI/help/localization behavior change. Next bounded family apply remains future.

## C21.1.22 — Native Stage outcome matrix BEFORE implementation

Accepted .21 5d6d4e2293cacf6b17cbea3a05ec305f6f41f27f / Cloud38595238961/all6
SUCCESS REMOTELY ACCEPTED. Clean fetched6.0 before checkpoint edits.

Audit stageCodec/stageStructuralRuntime/SQLiteStageStructuralRepository and Rust
stage_sync::dependency/apply/write_stage, native structural ACK SQL in note_sync.
Clean peer Stage create without authenticated Stage-order YES; clean update without
order mutation YES. Native write_stage creates a compatibility placement only for
new Stage, explicitly NOT order authority; no Web ordering/projection is synthesized.
Native ACK joins completed structural ledger/event/server sequence/outcome/exact
nonce/ciphertext, not plaintext stages or compatibility ordering/projection. Thus
encrypted Stage authority/history plus verified ledger-equivalent proof is sufficient.

|Native outcome|Required exact evidence|Web bounded result|
|---|---|---|
|applied create|no parents, revision1/generation1, valid dependency, no competing local/genesis|Supported|
|applied update|exact current tips, known parents same project/type/entity, max revision+1 AND max generation+1|One-tip create/update chain only; v1/v2|
|exact replay|same canonical frame/object and completed ledger; no descendant rollback|Supported|
|conflict_preserved|durable event/full causal tips + matching structural apply ledger/object|Not implemented; received barrier|
|orphan|missing Metadata/parent/dependency, no completed safe ledger|Unsafe|
|tombstone_blocked|delete has no complete child manifest; orphan inbox, no safe apply ledger|Unsafe; delete excluded|
|self echo|own sealed/accepted outbox exact scope/object and local candidate/publication/receipt recovery|No Web producer; excluded|

Metadata dependency native requires exact known non-delete applied/conflict-preserved
Metadata event with same account/project/bootstrap and matching apply ledger, plus
CURRENT Metadata authority state active. It need not be the latest tip: a known
non-delete ancestor is acceptable while current authority remains active. Web supports
only accepted clean imported coverless applied Metadata; reauthenticate full relevant
Metadata history before Stage apply/new prefix proof. Never satisfy by arbitrary head.

No v9/store/index change needed: ownerHeads existing [account,kind,owner_id] can use
kind=stage, owner_id=canonical JSON [project_id,stage_id], with explicit validated
project/stage fields; reversible/collision-free for arbitrary valid IDs. Do not assume
global Stage IDs. Strict new Stage proof/head allowlists only non-secret IDs/causal
fields/hash/reference; actual portable value remains encrypted original inbox.
Inbox standalone Stage proven discriminator/record5 avoids overloading Metadata
record2 or changing old1–4 schemas; same stores/indexes, no migration. Historical
pre-v8 validators remain Metadata-only and reject impossible Stage state.

Apply crypto outside IDB; private plan binds whole original project/head/inbox/Meta
dependency/cursor/outbox/receipt inventory and current auth/key/session. Strict same
transaction rechecks anchors then atomically writes Stage head + Stage proven inbox.
No cursor mutation, plaintext store, order/delete/conflict/self-echo/local writer or
upload-existing scope. Opaque prefix certificate gates individually safe Stage rows;
Stage-order and other families remain barriers. Stage historical proven prefix may
retain structurally/digest validated old authority without redundant Stage decrypt.
Rehydration decrypts winning retained event after unlock; no editor/UI wiring.

## C21.1.22 — bounded encrypted Stage entity authority and ACK proof

Accepted .21 `5d6d4e2293cacf6b17cbea3a05ec305f6f41f27f`, Cloud38595238961 SUCCESS,
all six required jobs SUCCESS / REMOTELY ACCEPTED. .22 LOCAL COMPLETE, remote CI
PENDING — NOT POLLED. Official84.0%, C21 IN PROGRESS, .06 NOT LOCAL COMPLETE, readyfalse.

Stage reader-ready YES; protected apply PARTIAL. Peer clean v1 create/v1-v2 one-tip
update ID0/ID1, import_remote/captured/active only. Authenticated same-project/bootstrap
known nondelete Metadata dependency (ancestor permitted) and current active authority;
exact tip parents and parent revision/generation+1. Full wire/header/digest comparison.
Delete/order/conflict/orphan/self-echo/upload-existing/local writer stay excluded.

v8 unchanged,12 stores, no migration/index/dependency/backend/native edits. New strict
ownerHeads kind=stage uses canonical JSON tuple[project,stage], validates explicit scope,
keeps nonsecret full proof history and winner tip; inbox5/stage_proven retains original
ciphertext, strict proof discriminator/allowlist, old1–4 preserved. Same-stage IDs in
two projects have independent durable heads and decrypted winners. Historical older
migration validators reject impossible Stage outcomes without mutating their input.

stageApply prepare crypto outside IDB; opaque nonsecret plans bind full original
inventory including Meta head/history/binding, Stage head/history, inbox/outbox/receipt,
cursors and current auth/key/session. Strict same readwrite transaction rechecks ALL
anchors before atomic head+inbox writes; no cursor change. Stale/corrupt/revoked/aborted
plans fail closed with no partial authority. Reload read reauthenticates histories and
returns winner plaintext in memory only; no durable Stage payload/projection/order.

stage prefix opaque certificate reauthenticates unproven Stage and Metadata dependency;
structural proof alone never promotes. Historical already-proven Stage retains prefix
with exact full joins/digest/causal evidence and no unnecessary decrypt solely for
retention. Certificate/current scope/anchors recalculated in prefix+ACK transactions.
Note/Metadata safe classes and other barriers/account-wide no-skip walk unchanged.
Note1+Metadata2+Stage3+Note4→4; received/conflict Stage3 blocks at2; order5 blocks Note6
at4; Document after safe Stage still barrier. Existing ACK transport/gates unchanged,
one explicit request max/attempt, lost-response/local-abort retry and no-progress safe.

Validation:491 unique/18 relevant files,73 Stage tests; Chromium189 groups, native IDB/
Web Locks/reload/disk reopen, Stage abort/key/logout/isolation PASS; page errors0.
Total explicit API95: registration19/capability8/mode21/registry23/ACK8/bootstrap16;
new slice delta14 includes2 explicit ACK, Stage apply/proof/prefix0, pull/push/Resolution/
unrelated0. Typecheck, production build, workflow syntax and diff checks PASS.
Stage specs mandatory Cloud; Cloud EXPECTED, SQLite NOT EXPECTED, CI not polled.
Next bounded slice: native Stage-order dependency/authority/proof audit and clean apply,
without Stage delete/conflict/local producer or readiness expansion.

Stage history uses the existing Metadata proof budget of200 retained proofs per head.
Exceeding it rejects continuation without truncating or discarding any history.

## C21.1.23 — native Stage-order audit BEFORE production edits

Accepted .22 SHA24b6e90456e20aa73e1f735f573aed74e27cc5dc, Cloud38606705365
SUCCESS / all six required jobs SUCCESS / REMOTELY ACCEPTED. Clean fetched6.0.
Inspected stageCodec/stageStructuralRuntime/SQLiteStageStructuralRepository;
stage_sync dependency307–330/reference_coverage589–640/order_dependency696–752/
apply818–1038/known_local_in_lineage662–695; native tests2068/2109/2186/2234/2931;
structural ACK joins note_sync6728; accepted Browser Stage/Metadata/prefix/ACK.

|Audit question|Exact native semantics / bounded Web decision|
|---|---|
|1 create independently ACK-safe?|YES: clean applied + exact structural ledger/object; empty project order permitted|
|2 update independently ACK-safe?|YES: complete dependency proof, exact old tips/parents, revision AND generation maxparent+1|
|3 complete membership?|Sorted stage_ids must equal ALL local stages for this project, independent of permutation|
|4 older Stage head?|Receiver allows references covered by current Stage history; writer requires exact current heads|
|5 ancestry bound?|256 distinct non-reference events cached across current tips per Stage; reference matches stop traversal; each current tip matched AND each reference covered|
|6 missing Stage?|stage_dependency_missing; no safe applied ledger|
|7 deleted Stage?|Any current delete tip blocks stage_tombstone_child_manifest_incomplete; retained legacy row cannot authorize order|
|8 foreign Stage?|stage_order_foreign_stage; no cross-project ownership|
|9 clean applied safe?|YES; projection permutation is derived, ledger/event/sequence/outcome/exact ciphertext prove ACK|
|10 exact applied replay safe?|YES: exact wire/frame/ledger return before new dependencies, never roll back descendant|
|11 conflict preserved?|Only with complete durable conflicting causal histories and matching apply ledger; Web excluded|
|12 Metadata?|Exact same account/project/bootstrap known nondelete applied/conflict-preserved event+ledger AND current active authority; known ancestor allowed|
|13 v8 enough?|YES for accepted clean imported authority: enumerate and validate all project-scoped Stage heads; no local Stage source/writer, retained parent links and proof joins; no new store/schema|

Frozen codec3 uses entity stage_order/fixed entity_id stage_order/stage=null/deleted=null,
unique ordered IDs<=4096, exact same head keys, sorted nonempty heads<=64. v1 genesis
or single-parent update; v2 never genesis, sorted full-tip parents<=64. Bounded v2
one-tip continuation has prior winning encrypted order in its parent lineage (native
known-local check bound256), with no independent local order cache/writer/candidate.
Multi-tip resolution excluded. Native order projection DELETE/INSERT is derivable
from encrypted winner, not needed as separate ACK authority in Web.

Web membership source: all validated Stage ownerHeads in exact account/project/bootstrap;
strict Stage proof type admits only live clean create/update. Account-wide owner keys
remain collision-safe JSON[project,stage]. Pending/unproven Stage evidence at or before
new order's dependency point blocks completeness; retained delete evidence blocks new
proof with explicit tombstone reason. Unknown/missing/foreign heads never inferred.
Historic persisted order proof keeps its frozen dependency set, permits legitimate
Stage descendants via actual links and never rolls back prefix after field updates.

Order owner key[account,stage_order,project] is unambiguous fixed entity. Strict inbox6/
stage_order_proven and nonsecret head/history keep existing1–5 byte schemas. Dependency
references sorted by Stage ID in proof are evidence, NOT ordered plaintext projection;
actual permutation remains only encrypted wire. v8 unchanged/no migration. History
budget200 (stricter accepted Web shape); native coverage256 still explicitly enforced.
Opaque plan crypto outside IDB then same-transaction full inventory CAS includes
complete membership/all Stage histories/Metadata/order/inbox/cursors/outbox/receipts.
No native/backend/codec/crypto/transport changes, no readiness expansion.

## C21.1.23 — exact Stage-order protected apply and ACK proof

C21.1.22 REMOTELY ACCEPTED: SHA24b6e90456e20aa73e1f735f573aed74e27cc5dc,
Cloud38606705365 SUCCESS / all six required jobs SUCCESS. .23 LOCAL COMPLETE /
REMOTE CI PENDING — NOT POLLED. Official84.0%, C21 IN PROGRESS, .06 NOT LOCAL COMPLETE,
readyfalse. Stage reader-ready YES/peer create-update YES/ACK-safe subset unchanged.
Stage-order reader-ready YES; protected apply bounded clean peer create/update COMPLETE.

Eligibility: import_remote/captured/active, exact canonical account/device/project/
bootstrap, v1 genesis and v1/v2 ONE-tip continuation only, codec3 ID0/ID1. Frozen codec
unchanged; no conflict/full-tip resolution/self-echo/local writer/upload-existing/UI.
Same accepted Metadata dependency machinery (known nondelete exact event/retained
crypto history/current active authority; ancestor allowed), no duplicate verifier.

Membership enumerates ALL validated Stage ownerHeads in project/bootstrap, preserves
accepted collision-safe Stage tuple[project,stage]. Every referenced Stage has complete
retained crypto-proven clean live history and actual tip; unknown/foreign/missing/
deleted/unproven evidence blocks. New order's sorted members must exactly equal full
current membership; pending Stage evidence at/before dependency point blocks omission.
Exact-current heads pass; older refs pass only native receiver reference_coverage:
every current tip and every reference covered, stop at matches, cycle-safe actual
parents, per-Stage cache<=256 non-reference expansions. Web retained history budget200
is stricter than native traversal availability; over-budget fails, no truncation.

Order owner[account,stage_order,project], entity fixed stage_order. Nonsecret strict
head/history + inbox6/stage_order_proven, old1–5 unchanged. Stored dependency refs sorted
by Stage ID prove membership/causality; they are NOT an ordered stage_ids projection.
Winning canonical permutation remains encrypted original wire. v8 unchanged,12 stores,
no new index/migration/dependency/backend/native/codec/crypto changes.

Opaque private plan binds exact wire/digest, frozen ordered IDs/head refs and all
original durable inventory. Crypto outside IDB, strict same transaction CAS before
atomic head+inbox only. Auth/key/session invalidation, Stage edit/new membership,
Metadata/binding/cursor change and transaction abort fail closed. No partial order or
cursor writes. Reload reads authenticate retained dependencies/history and decrypt
winning permutation in memory; no plaintext durable authoritative cache or UI wiring.

Current cryptographic certificate qualifies clean order create/update/replay in shared
contiguous prefix and existing bounded ACK. Structural marker alone cannot qualify.
Historical proven prefix retains full exact joins/digest without redundant order
crypto merely to retain prefix. Normal Stage descendant edits preserve old reference
coverage and monotonic prefix. Exact applied replay keeps frozen membership and cannot
roll back descendant even after membership expansion; NEW proof requires full current
membership. Stage-order conflicts/deletes/self-echo and other families remain barriers;
Note/Metadata/Stage rules, account-wide ordering and ACK transport/gates unchanged.

Examples:Metadata1/Stages2-3/Order4[B,A]/Note5→5/ACK5. Normal StageA6 descendant/Note7
retains order coverage/prefix7; clean v2 Order8[A,B] with older Stage refs/Note9→9/ACK9.
Bad/missing membership or sibling reference Order4 blocks Note5 at3/ACK3. Document
following safe Order still blocks. Max1 ACK per explicit attempt; retries/no-progress
unchanged. No hidden apply/proof/coverage/prefix HTTP; no automatic registration,
capability, bootstrap, registry, pull, push, Resolution or ACK loop.

Checks:573 tests/20 focused files,82 order tests, accepted Stage/Metadata/Note/reader/
ACK/migration-open regressions PASS. Chromium195 groups, four mandatory scenarios,
real IDB/Web Locks/atomic abort/key/logout/account isolation/reload/profile reopen,
page errors0. Typecheck/production build/workflow mandatory order specs/syntax/diff
PASS. Total119 explicit APIs:registration22/capability11/mode32/registry26/ACK12/
bootstrap16. Slice delta24:registration3/capability3/mode11/registry3/ACK4.
Stage-order apply/proof/coverage/prefix0, pull/push/Resolution/unrelated0.
Cloud EXPECTED, SQLite NOT EXPECTED, remote CI NOT POLLED. Next bounded slice:
Stage durable conflict history/preservation/ACK proof, without delete/self-echo/writer.

## C21.1.24 — native Content Note audit BEFORE production edits

Accepted .23 SHA27e249c140d7b25afd1bf339cfe2cbc055c5c2a9, Cloud38623967292 SUCCESS,
all six required jobs SUCCESS / REMOTELY ACCEPTED. Native contentNoteCodec/Reader/
Runtime, content_note_sync receipt214/ready256/complete338/ack_proven355, ordinary
note_sync apply_received_note_with_content and dispatch9819, account_catalog
project_coverage832, Stage content_reference_ready643/reference_coverage594 audited.
Native tests variants541, restart/rename576, ordinary/conflict/resolution749,
Metadata ancestor873, Stage tombstone886 and retained route942 inspected.

|Question|Native answer / current browser prerequisite|
|---|---|
|1 underlying identity/history?|Same existing ordinary Note header/event ID/causal history, not a second authority|
|2 receipt identity?|EXACT embedded header event_id, source/device/project/entity/sequence/revision/time and original codec8 nonce/ciphertext/frame|
|3 ACK requires both?|YES: wrapper receipt joined inbox/object + underlying causal snapshot or conflict version; reader success insufficient|
|4 create/update/delete?|Clean ordinary operations individually safe after dependencies and shared Note apply succeed|
|5 replay?|Safe only with exact existing wrapper/object receipt AND underlying replay proof; no descendant rollback|
|6 Metadata?|Known NONDELETE APPLIED event+ledger, same bootstrap/project/account, current active authority, actual ancestry coverage from current head (catalog budget65536); not just existence|
|7 Stage?|Exactly one current live Stage tip, compatible authenticated projection, complete retained proof and exact/ancestor refs|
|8 Stage ancestor?|YES: native reference_coverage, every current tip and reference covered, cache256 non-reference expansions per Stage|
|9 missing/conflict/tombstone?|Blocks dependency; tombstone_child_manifest_incomplete for current delete, not safe projection|
|10 sources/formats?|project/null map/null node, html/plain. Mindmap, route moves, metadata keys and unsupported formats blocked|
|11 Resolution separable?|YES: native dispatch ordinary vs resolution before common transaction hooks; this slice does not enable v2|
|12 v8 storage?|Physical stores can hold a typed wrapper proof without DB migration. Current accepted Legacy Note history/proof/apply APIs have no codec8-aware atomic adapter|

Native limits remain exact owning codec: frame8MiB, content7MiB, title512KiB,
color512bytes, tags4096/16384bytes, checklist16384/id512/text65536bytes,
JSON depth12/nodecount131072, Stage refs64. Browser local authority is currently
stricter: project HTML only, title500/content300000 codepoints; plain and Stage
are explicitly rejected by noteSyncEligibility. No loosening of accepted Legacy rules.

Critical current adapter gap: Legacy load rejects operation=event; retained Note and
candidate reopen decode legacy plaintext ONLY; candidate1 strict wire demands upsert/
delete and matching ordinary header; proof1 also equates server descriptor operation/
deleted_at to underlying header. Content delete instead has OUTER operation=event,
deleted_at=null and INNER delete/tombstone. Native solves this through explicit content
parameter in the SAME shared Note transaction, receipt/ready/complete hooks. Web has
no corresponding route-aware verified history/receipt hook. Rewriting outer descriptor,
stripping frame or separately committing receipt would falsify immutable identity or
permit partial success. Do not infer that successful reader decode admits this route.

## C21.1.24 — Content Note ordinary adapter prerequisite / STOP

C21.1.23 REMOTELY ACCEPTED: SHA27e249c140d7b25afd1bf339cfe2cbc055c5c2a9,
Cloud38623967292 SUCCESS / all six jobs SUCCESS. .24 BLOCKED BEFORE IMPLEMENTATION /
NOT LOCAL COMPLETE / AUDIT REMOTELY ACCEPTED (Cloud38633076568). Official84.0%, C21 IN PROGRESS,
.06 NOT LOCAL COMPLETE, readyfalse. Content reader-ready YES; ordinary protected apply
NO, Resolution2 NO, conflicts/self-echo NO, ACK-safe Content subset NONE implemented.

Native ordinary v1 shares the existing Note event ID/causal authority. ACK requires
BOTH exact original codec8/frame/nonce/ciphertext receipt and matching underlying
successful Note causal snapshot/conflict version; wrapper-only/read-only never safe.
Native create/update/delete/replay individually safe when both are proven. Explicit
content argument in shared transaction creates receipt, validates ready, performs Note
apply, completes receipt atomically; Resolution2 is separate dispatch. Metadata:
APPLIED nondelete same project/account/bootstrap + active current authority + actual
ancestry with catalog65536 budget. Stage: one live compatible current Stage tip,
actual exact/ancestor coverage256; missing/conflicted/tombstoned/foreign blocks.
Native project/null map/node html/plain; owner/source/format continuity checked after
tombstone too. Native frame/content/title/tag/checklist/depth/count limits unchanged.

STOP1/3: Web Legacy load rejects note/operation=event. Proof and candidate record1
require ordinary upsert/delete descriptor; Content outer delete descriptor still has
operation=event/deleted_at=null. Encrypted causal history reopening only uses the
legacy plaintext decoder. Existing opaque protected Note plan has no authenticated
codec8/dependency/receipt hook, and its commit does not join ownerHeads dependency
inventory/wrapper outcome. An inbox-only new discriminator cannot make this safe.
Relabelling descriptor, stripping frame or fabricating encrypted legacy identity is
not an exact receipt; separate wrapper commit violates atomicity. Local admission also
rejects plain/Stage and has stricter existing limits (title500/content300000 codepoints).
No accepted Legacy rules broadened, no fake second Note authority/projection introduced.

Physical v8 storage can carry future typed proofs; no intrinsic schema/store blocker
claimed. Needed bounded prerequisite: explicit original-wire route-aware Note history
and shared verified apply transaction hook, current Metadata/Stage CAS and atomic
wrapper receipt; separately audited source-aware admission preserving old schemas and
rules. Current wrapper proof/ordinary apply/rehydration not implemented. Existing
Stage/Order/Metadata/Note proofs/ACK/other-family barriers unchanged, readyfalse.

485 tests/15 relevant files PASS,11 new mandatory contentNoteBoundary cases. Actual
ID0/ID1 ordinary create/update/delete read but cannot enter Legacy history/proof;
disguised original ciphertext cannot decode as legacy; wrapper-only state rejected.
Metadata1/Stage2/Order3/Content4/Note5 prefix3, no partial Note/history writes; readable
Resolution2 prefix0; native-valid Stage/plain/title501 stop existing local admission.
Chromium197 groups PASS including actual codec8 ID1 project HTML, valid Stage ancestor
and Resolution2 reader success/rejected apply, later Note13 blocked behind Content10,
no-progress ACK9, exact ciphertext/state surviving renderer/disk reopen. Page errors0.
Cumulative119 explicit APIs unchanged:registration22/capability11/mode32/registry26/
ACK12/bootstrap16. New Content apply/proof/dependency/prefix/ACK0, pull/push/Resolution/
unrelated0. Typecheck/build/workflow/syntax/diff PASS; protected pyc unchanged.
Positive Content path tests NOT RUN after STOP. Cloud EXPECTED, SQLite NOT EXPECTED;
remote CI not polled. No production backend/native/schema/dependency/frozen edits.

## C21.1.25 — shared route-aware Note prerequisite

**REMOTELY ACCEPTED** for the bounded prerequisite. Cloud `38641352769` SUCCESS; all six required jobs SUCCESS; accepted SHA `2c80641c76b81cc02731e30b9beece14b605d0c3`.
C21.1.24 accepted SHA `30b7c36ab685172a1ed584cc528e0837d621e7eb`, Cloud `38633076568` SUCCESS, all six required jobs SUCCESS; blocker/audit REMOTELY ACCEPTED. Implementation remains BLOCKED BEFORE IMPLEMENTATION / NOT LOCAL COMPLETE.
Official 84.0%, C21 IN PROGRESS, C21.1.06 NOT LOCAL COMPLETE, ready=false; no points.

`openNoteTransport` separates the exact transport from authenticated ordinary Note
material. Legacy still uses its existing decoder and exact operation/timestamp/source
eligibility. Dormant codec8 uses the existing canonical reader (AEAD before ID0/ID1
frame handling); outer note/event/null remains original, while inner create/update/
delete supplies logical causality. Embedded Resolution2 is explicitly rejected. No
codec/parser/AAD/wire/compression change and no fabricated Legacy ciphertext.

One private causal planner and one existing legacyNoteHistory/head serve both routes.
Normal prepare/apply still selects Legacy only; prepareDormantOrdinary is an internal
acceptance entry, absent from application Content dispatch. Shared plan capability is
private WeakMap state; no arbitrary DTO can authorize local source writes. Dormant
outcomes are explicitly distinguished from Legacy durable proofs and never become a
note_proven inbox row. Real Content remains received, including after dormant evidence.

Candidate record1 construction/digests remain unchanged and old records reopen without
rewrite. Strict discriminated candidate2 stores transport_kind=content_note_v1, original
full retained wire (including source device/server sequence), authenticated logical
header, original encrypted projection and narrowly typed transport prerequisite proof.
Logical digest covers the entire authenticated ordinary Note; wire digest covers exact
original transport/object; dependency digest binds exact scope/bootstrap/project/Note/
event/wire and verified owner/binding inventory. Immutable record/proof digests are
checked on reopen before reauthentication of the original codec8 object; encrypted
projection is checked against the decoded Note. No plaintext durable payload duplicate.
Physical DB remains v8, twelve stores; no store/index/migration changes, no old rewrites.

Opaque dependency certificate is minted only after original Content AEAD and forced
crypto verification of applied Metadata history. It requires same active imported
project/bootstrap, nondelete referenced Metadata and one active authenticated current
tip in the accepted clean chain. This dormant adapter admits project HTML/stage=null
only; plain/Stage and Content conflicts/self-echo/replay remain future admission work,
not production success claims. Certificate binds current auth/key/session via its lease
closure and snapshots non-secret exact inventory; no key/token/plaintext inside it.

The transport commit capability defers only its exact prepared candidate from ordinary
history puts. The same actual Note readwrite transaction schedules head/history, source
CAS/encrypted project and Note writes, then ownerHeads/all-bindings dependency CAS and
immutable candidate+wrapper evidence add. Request error, validation failure, key/auth
invalidation or transaction abort rolls back every side. Result resolves on actual
transaction completion, not a later Promise or second transaction. Existing Legacy
inbox/proof/intents/outbox/receipts/binding/cursor/history/source CAS are retained.

Cross-transport same event is fail-closed even for proven semantic equivalence: no
second candidate and no overwrite of either original wire. Altered payload/header also
hard conflicts. Native content_note_sync receipt214 binds event/source/sequence/nonce/
ciphertext and refuses differing canonical frame; note_sync ordinary dispatch9832 and
apply_received_note_with_content9895 share the Note transaction. Server sync_events has
a globally unique event_id primary key (backend/app/cloud/models.py247); browser inbox
also has unique account/event identity. A same-event dual-provenance authority is not
invented here; strict rejection avoids ambiguous authority. Tests compare equal logical
material from both independently encrypted routes and distinct transport evidence.

Production Content protected apply NO, wrapper ACK proof NO, prefix contribution NO,
ACK contribution NO, Resolution2 NO. provenPrefix, ACK gates and syncDurability inbox
classification are unchanged. Metadata1/Stage2/Order3/Content4/Legacy5 still prefix3,
ACK capped3; existing Chromium production barrier Content10/Legacy13 keeps prefix/ACK9.
Dormant Chromium Content2/update3/delete4/Resolution5/Legacy6 keeps prefix1/ACK0.

Validation: 1,038 tests in the exact mandatory Cloud 42-file C21 set passed before
adding ten further gateway cases; final gateway54 and 317 affected tests/14 files PASS.
Chromium201 groups/native IDB+Web Locks PASS: Legacy baseline regression/reopen,
codec8 ID0 create and ID1 update/delete original-wire reopen, actual hook/write/source/
abort rollback, stale dependency, auth invalidation, key revocation, account isolation,
renderer and disk-profile reopen, production barrier and Resolution rejection.
Zero page errors. Cumulative explicit HTTP remains119: registration22/capability11/
mode32/registry26/ACK12/bootstrap16. Added gateway/history/dependency/hook/Content apply/
ACK requests0; push/pull/Resolution/unrelated0. Typecheck/production build/mandatory
workflow/syntax/diff PASS; no skipped tests. Existing build chunk/import warnings only.
New gateway spec and browser helper are mandatory Cloud coverage, no skip/xfail/
continue-on-error. Cloud EXPECTED; SQLite substrate NOT EXPECTED. CI NOT POLLED.

No backend/PostgreSQL/Alembic/native/Rust/SQLite/dependency/frozen-contract changes.
Protected pyc hashes unchanged. Next bounded slice: ordinary Content Note v1 production
protected apply/inbox-wrapper proof on this gateway, with explicit scope/dependency/
replay/conflict/self-echo admission audit; Resolution remains separate.

### Простыми словами

- Проблема была не в базе браузера: старый механизм считал транспортный формат и саму историю заметки одним и тем же.
- Теперь исходная зашифрованная обёртка отделена от события, которое меняет заметку.
- История заметки остаётся общей и единственной: новый формат не получает отдельную копию авторитетной истории.
- Codec8 можно подключать к ней с его настоящим шифротекстом, не притворяясь старым форматом; обычный и сжатый варианты проверены.
- Подготовлен и проверен атомарный механизм: доказательство обёртки, история и применение заметки сохраняются вместе либо полностью откатываются. Пока он используется только внутренним тестовым путём для HTML-заметок без стадии.
- Сам Content Note в обычном приложении специально остаётся барьером. Чтение и тестовый переход не дают ему права увеличивать подтверждение серверу.
- Следующий шаг — вернуться к ordinary Content Note v1 и включить его production protected apply с настоящим доказательством inbox, отдельно проверив необходимые зависимости и исходы.
- Полная Web-синхронизация ещё не готова: ready=false, официальный прогресс 84.0%, C21 IN PROGRESS.

## C21.1.26 — production Content Note ordinary v1 / project HTML

**REMOTELY ACCEPTED** for the bounded subset. SHA `d1323fddb3187f60bf53bd3cf5c09f5d23fb5172`, Cloud `38649425407` SUCCESS, all six required jobs SUCCESS.
C21.1.25 SHA `2c80641c76b81cc02731e30b9beece14b605d0c3`, Cloud `38641352769` SUCCESS, all six required jobs SUCCESS; REMOTELY ACCEPTED.
Official84.0%, C21 IN PROGRESS, C21.1.06 NOT LOCAL COMPLETE; ready=false; no points.

`session.contentNotes` is a dedicated production runtime wrapping the accepted shared
Note planner/commit. Legacy `session.notes` retains its legacy route and proof semantics.
Production admission: protocol3, exact outer note/event/deleted_at=null; canonical
codec8 frame1/codec_version1; inner ordinary Note1; peer source; project/null map/node;
HTML/stage=null/stage_event_ids=[]; import_remote/captured/active binding, exact bootstrap
and authenticated qualifying Metadata. No upload_existing Content capture, local Content
writer, self-echo, conflicts, plain, Stage, Resolution2 or other-family expansion.

Clean create/update/delete PASS in ID0 and ID1. Delete uses existing local encrypted Note
tombstone and causal rules, no Content-specific tombstone. Competing genesis, orphan,
stale/sibling parent, unresolved frontier/group and local-unsealed intent block rather
than LWW. Content continuation from a valid Legacy parent and clean Legacy descendant
from Content are verified in one graph. Same-event cross-transport collision rejects
without replacing either immutable wire. Legacy local producer admission is not expanded
to create pending intents from a Content-only head; no local Content writer added.

Existing candidate2/transport_kind=content_note_v1 is retained without evolution or
rewrite. Dedicated inbox7/content_note_proven has strict exact-key Content proof1:
account/bootstrap/protocol, original full reference/server sequence, codec8/frame1/
codec_version1, logical header/mutation/history_event_id, original wire and logical
material digests, dependency/candidate/transport-proof digests, protected source revision,
encrypted local projection digest and outcome digest. Qualifying underlying outcome
is applied only. No plaintext Note body is persisted. Candidate2 alone and inbox proof
alone cannot qualify. Legacy inbox3/note_proven remains distinct and unchanged.

Actual common readwrite transaction schedules history/head and protected source CAS,
encrypted project/Note writes, dedicated inbox proof, accepted ownerHeads/all-bindings
CAS and immutable candidate2/transport-hook evidence. No asynchronous crypto inside IDB
transaction, no second transaction/post-commit receipt. Inbox/candidate/source failures,
auth/key/session invalidation, stale Metadata inventory and explicit abort roll back
all sides. Expected original inbox/history/intents/outbox/receipts/binding/cursor/source
inventories remain checked. Current Metadata certificate remains the accepted forced
crypto clean-chain prerequisite, nondelete referenced event plus active authenticated
current tip in the same project/bootstrap; plain/Stage refs are never silently admitted.

Exact applied replay verifies original row/candidate/header/projection/outcome digests
and original codec8 AEAD/canonical payload, plus current historical Metadata coverage.
It retains immutable original dependency digest and uses a fresh certificate for current
inventory CAS: compatible Metadata descendants do not require rewriting historical proof.
Replay observes the candidate on the shared linear-head ancestry, snapshots current local
source for CAS, never rewrites Note/head/projection and never rolls back newer descendants.
A missing/corrupt candidate/head/proof cannot be repaired from current plaintext state.
The existing transport hook checks current dependencies in the same replay transaction.

Prefix adds Content only through an opaque crypto certificate bound to exact whole
inventory, validated dedicated inbox proof, candidate2/full original wire join, protected
causal outcome/head ancestry, encrypted projection and current Metadata coverage.
Legacy stripped-wire record1 checks stay unchanged. Prefix/ACK example results:
Metadata1/Content2/Legacy3 →3; bad dependency/Resolution/plain Content2 →1;
Metadata1/Stage2/Stage-scoped Content3/Legacy4 →2. Pure structural caller without the
crypto certificate cannot qualify Content. Candidate2-only dormant acceptance remains
received and a barrier, even though its source/history are internally testable.

ACK transport/gates/retries remain unchanged; target=committed proven_prefix, at most
one ACK HTTP per explicit invocation, server success before ack_cursor commit. No loop.
Supported Content can now enlarge the target. Lost response and server-success/local-
commit-failure retries are exact; stale Content proof/candidate/wire/owner before send
blocks HTTP, changed proof after server success blocks local commit. ready=false.

Physical IndexedDB remains v8/twelve stores, no migration/new store/index. No bulk old
inbox/history rewrites; only normal authorized apply/source/head writes. v5 structural
migration validation explicitly rejects impossible Content outcome rows, preserving
its old boundary; current schema migration behavior is unchanged.

Validation: exact mandatory Cloud C21 suite1123 tests/44 files PASS, followed by nine
additional production cases; final Content apply71 + ACK13 =84 tests/2 files PASS.
Legacy/shared causal/history/unsealed/Metadata/boundary/prefix/ACK/migration/open all PASS.
Chromium203 groups PASS with native IDB/Web Locks: six production Content outcomes10–15
(ID0 and ID1 create/update/delete), correct live updates then tombstones, exact old replay,
original candidate2/inbox7 wire, one head/Note, actual rollback of wrapper/candidate/source,
post-candidate abort/auth/key/session, stale owner CAS, renderer and disk-profile reopen
with all six proofs reauthenticated and no duplicate authority/rollback/plaintext.
Readable bad dependency16/Resolution17/plain18/Stage19/self20, causal sibling21 and
session-aborted23 remain received; later Legacy22 cannot leapfrog. Prefix15/ACK15 survives.
Page errors0. Typecheck, production build, workflow/YAML/JS syntax and diff PASS; existing
chunk/dynamic-import build warnings only. Mandatory Cloud apply/ACK specs and acceptance;
no skip/xfail/continue-on-error. Protected pyc unchanged; harness output removed after stop.

HTTP added only by explicit ACK acceptance: +1 ACK and +2 existing fresh mode checks.
Cumulative122 = registration22/capability11/mode34/registry26/ACK13/bootstrap16.
New registration/capability/registry/bootstrap/pull/push/Resolution/unrelated requests0;
Content apply/proof/dependency/prefix HTTP0. Existing gates reused for ACK across Content.
Cloud EXPECTED; SQLite substrate NOT EXPECTED. Remote CI NOT POLLED.

No backend/PostgreSQL/Alembic/native/Rust/SQLite/new dependencies/frozen contract changes.
Other families and cover-bearing Metadata retain their accepted boundaries. Recommended
next bounded slice: Stage-scoped Content local-authority/admission and dependency audit,
then explicitly bounded protected apply; keep Resolution/local writer/self-echo separate.

### Простыми словами

- Предыдущий этап подготовил общий механизм для разных транспортных форматов заметки.
- Теперь обычная HTML-заметка codec8 реально применяется в Web: проверены создание, обновление и удаление, в обычном и сжатом вариантах.
- Она использует ту же единственную историю заметки, что и старый формат.
- Браузер сохраняет доказательство именно исходной codec8-обёртки, без подмены старым форматом.
- Применение заметки, её история и доказательство сохраняются атомарно: при ошибке не остаётся половины результата.
- После проверки обоих доказательств безопасная Content Note может входить в непрерывную подтверждаемую серверу последовательность; явное подтверждение серверу проверено.
- Resolution, plain, заметки внутри Stage, конфликты и self-echo пока специально не включены. Поздние безопасные события не обходят эти барьеры.
- Web-синхронизация ещё не полностью готова: ready=false, C21 IN PROGRESS, официальный прогресс 84.0%. Следующий ограниченный шаг — аудит и подготовка Stage-scoped Content admission и точного Stage dependency.

## C21.1.27 — Stage-scoped HTML Content / Content-only local admission

**LOCAL COMPLETE / REMOTE CI PENDING — NOT POLLED** for ordinary peer project HTML
Content, stage=null OR one concrete authenticated Stage; create/update/delete/replay.
C21.1.26 SHA `d1323fddb3187f60bf53bd3cf5c09f5d23fb5172`, Cloud `38649425407` SUCCESS, all six required jobs SUCCESS; REMOTELY ACCEPTED.
Official84.0%, C21 IN PROGRESS, C21.1.06 NOT LOCAL COMPLETE; ready=false; no points.

Current-code/native audit: frozen noteSyncEligibility rejects stage_id and remains
byte-for-byte unchanged. Previously openNoteTransport applied that Legacy gate to both
routes; prerequisite rejected all Stage refs; local source/projection validation also
used the Legacy gate. Content now has explicit project/null map/node/HTML route
admission; a concrete Stage ID must pass existing ID validation AND authenticated
Stage dependency. Legacy JSON reader/writer/capture/backfill/conflict admission stays
unchanged. No codecs/crypto/AAD/compression/backend/native changes or new dependencies.

Local admission uses preferred option A: split persisted-source and Content validation
from Legacy writer eligibility. Existing encrypted local_format1 already stores stage_id
in both live Note and tombstone; no new discriminator/version needed. Protected source
writer selects Content validation only through the private verified causal-plan route,
not a caller DTO. Persisted Stage HTML decrypt/reopen uses Content validation; project
stage=null continues its old read path. Public initialize/create/update/tombstone and
Legacy intent/capture still use the original Legacy validator. Old project Notes,
local payloads, envelopes and serialization are unchanged; no bulk rewrite. Title500/
content300000/codepoint/source/envelope limits stay unchanged; live Content metadata
must be empty as required by its owning codec. No plaintext durable Note data.

One existing Note causal graph/head remains authoritative. Source route is immutable
across protected continuation, including after tombstone: id/project/stage/source/map/
node/format must match authenticated prior material. Legacy cannot strip a Stage route
from a Content parent. Clean Stage delete uses the existing tombstone and retains Stage
identity; no Content-specific tombstone. Conflicts/self-echo/local Content writer remain
blocked, plain and Resolution remain reader-only barriers. Project stage=null regression
and its valid mixed Legacy/Content ancestry remain accepted.

Native stage_sync::content_reference_ready643 consumes one live compatible projected
tip. reference_coverage594 traverses actual parent_event_ids from current tips to refs,
stops at refs, requires every tip to reach a ref and all refs to be covered, with cached
non-reference expansion budget256. Equality-only is wrong: current B may be a safe
linear descendant of referenced A. Web Stage head/history has complete parents and
existing clean accepted history limit200 (stricter; unchanged). The same existing
proveStageReferenceCoverage helper implements native256 semantics; no parser duplication.

Content Stage dependency reuses force prepareStagePrefix + stageSequences after the
unchanged force Metadata prerequisite. Exact Stage owner/project/bootstrap/history/tip
must validate and all its rows must be cryptographically qualified. Web Stage projection
is derived from the authenticated single tip by existing Stage read machinery; no
separate mutable Stage plaintext projection can diverge. Unknown/foreign refs, foreign
parents, missing/corrupt histories, multiple/unresolved tips, nonlive/tombstone state,
uncovered or redundant refs and ancestry overflow fail closed. Earlier retained
unqualified Stage events cannot authorize a newer Content event; a received preceding
Stage delete reports stage_tombstone_child_manifest_incomplete. Later received Stage
rows remain their own barriers; safely applied advancement is reauthenticated and
covered, preserving historical Content proof. Stage-order is not required.

Existing opaque prerequisite binds original authenticated route/refs and the exact
owners/bindings snapshot, including Stage history/current tip, plus auth/key/session
currentness. Existing dependency_digest already includes original wire and full owner
inventory, so inbox7/content_note_proven proof1 and candidate2/content_note_v1 stay
unchanged. Historical digests remain immutable while fresh reauthentication proves
current native-compatible coverage; original Content proof/candidate are not rewritten
when Stage advances. The accepted same Note readwrite transaction performs Stage/Meta
owner CAS together with inbox/history/head/intents/source/outbox/receipts/cursor CAS
and atomic candidate/wrapper/source writes. Stage drift without cursor change aborts
inside the actual hook, not merely a preflight/cursor failure; explicit reprepare against
an authenticated covered descendant can succeed. No second receipt transaction.

Prefix certificate/reopen automatically uses the extended prerequisite for Stage-scoped
Content. Both final inbox7/candidate2/projection/causal outcome AND Metadata/Stage crypto
coverage are mandatory; candidate-only/wrapper-only never qualifies. Examples:
Metadata1/Stage2/Content3/Legacy4→prefix4;
Meta1/StageA2/Content3/StageB4/Content-update5→prefix5;
unknown Stage ref/plain/Resolution Content3 after Meta1/Stage2→prefix2.
ACK transport/gates/target=committed proven_prefix/retry remain unchanged, at most one
ACK HTTP per explicit call and server success before local ack_cursor. No background ACK.

Schema remains IndexedDB v8/twelve stores; migration/store/index changes NONE; local
payload evolution NONE; old records rewritten by migration NONE. No change to other
family statuses, Stage causal/apply/deletion/conflict/self-echo contracts or Metadata.

Validation: mandatory Cloud C21 suite1171 tests/46 files PASS; final focused Stage
Content36 + ACK5 =41 tests/2 files PASS, including two added owner/foreign-Stage cases.
Local persisted/Legacy admission, ID0/ID1 create/update/delete/replay, exact and ancestor
refs, safe A→B historical revalidation, unchanged-cursor Stage CAS, missing/foreign/
wrong-scope/bootstrap/proof/wire/parent/uncovered/unresolved/tombstone dependencies,
256 expansion boundary/overflow, route immutability after tombstone, Legacy writer/
capture barriers, atomic rollback, project Content/Legacy/Stage/prefix/ACK/migration/open
regressions PASS. Typecheck/production build/workflow/YAML/JS syntax/diff PASS; existing
build chunk/dynamic-import warnings only; protected bytecodes unchanged.

Chromium205 groups PASS/native IDB+Web Locks: project outcomes10–15 unchanged; Stage
Content ID0 create16/update17/delete18 and ID1 create19/update21/delete22; Stage advances
at20 to a safe descendant, prior Content16 remains byte-identical/valid with ancestor
refs. Legacy23 yields prefix23/ACK23. Actual Stage wrapper/candidate/source/abort/auth/
key rollback, Stage-owner CAS without cursor drift, encrypted local route/tombstone,
Legacy write refusal, renderer and disk-profile reopen with twelve Content proofs,
original codec8 wires, single Note heads and protected local_format1 all reauthenticate.
Readable unknown Stage24/Resolution25/Stage plain26/foreign Stage27/self28, conflict29
and session-aborted31 remain barriers; later Legacy30 cannot leapfrog. Page errors0.
The first browser attempt found a fixture tombstone losing stage_id; test data corrected
and final full Chromium acceptance PASS; production deletion was already passing.

HTTP counters unchanged from accepted .26: cumulative122 = registration22/capability11/
mode34/registry26/ACK13/bootstrap16. Stage dependency/Content apply/proof/prefix HTTP0;
new registration/capability/registry/bootstrap/pull/push/Resolution/unrelated0. Existing
explicit ACK now crosses safe Stage Content with no additional API calls. Mandatory
Cloud Stage specs and Chromium acceptance, no skip/xfail/continue-on-error. Cloud EXPECTED;
SQLite substrate NOT EXPECTED; remote CI NOT POLLED. Task harness removed after stop.

Recommended next bounded slice: Content-only plain admission/reopen audit while keeping
Legacy eligibility frozen; Resolution/conflicts/self-echo/local writer remain separate.

### Простыми словами

- Web уже умел применять обычные HTML-заметки проекта нового формата, включая сжатые события.
- Теперь поддержаны HTML-заметки, привязанные к конкретному этапу: создание, обновление, удаление и точный повтор.
- Браузер не просто верит идентификатору этапа, а проверяет его защищённую историю, принадлежность проекту и связи между событиями.
- Если событие этапа A сменилось нормальным потомком B, ранее принятая заметка остаётся действительной: её исходное доказательство не переписывается.
- Legacy-механизм не расширен. Его writer и capture по-прежнему не могут создавать или отправлять Stage-заметки через новое разрешение.
- Plain, Resolution, конфликты, собственные отправленные Content Note и локальный Content writer остаются отдельными задачами.
- Полная Web-синхронизация ещё не готова: ready=false, официальный прогресс 84.0%, C21 IN PROGRESS. Следующий ограниченный шаг — аудит Content-only plain admission и безопасного reopen.

## C21.1.28 — plain Content / Content-only format admission

**LOCAL COMPLETE / REMOTE CI PENDING — NOT POLLED** (2026-10-15).
C21.1.27 accepted SHA `e540f56af505ba232a1f16b2abb70f91a2417cb1`,
Cloud `38657482380` SUCCESS, all six required jobs SUCCESS; **REMOTELY ACCEPTED**
(independent owner acceptance). Official **84.0%**, C21 **IN PROGRESS**,
C21.1.06 **NOT LOCAL COMPLETE**, `ready=false`; no roadmap increment.

### Audit and durable admission decision

Audited exact current noteTransport, localAuthorityRecords/localAuthority, shared
legacyNoteApply planner, contentNoteApply/proof/records/prefix, transport prerequisite,
Stage prerequisite, frozen noteSyncCodec/contentNoteCodec, ProjectNote and native
content_note_sync.rs before production edits (checkpoint preflight records findings).
Native portable accepts html/plain; Web ProjectNote already supports both.
Native `same_scope` compares id/project/stage/source/map/node/**content_format**
against current source and parent history, including after tombstone. Therefore
**HTML→plain and plain→HTML causal updates remain BLOCKED**; each entity retains
one shared Note authority. Legacy HTML cannot strip a previously applied plain route.
This adds a guard only for the newly admissible Content-only source; all previously
admissible Legacy HTML behavior, global eligibility, codec/writer/capture are unchanged.

Content-specific assertContentNoteRoute now permits project-owned HTML or plain,
map/node null and valid Stage or null. openNoteTransport owns this admission;
prepareNotePrerequisite removes its redundant HTML-only gate. Metadata and Stage
prerequisites, Stage ancestry, owner/binding CAS and ACK machinery are unchanged.
No domain/UI changes, conversion, escaping, trimming or text normalization.
Existing local limits remain title500/content300000 codepoints/envelope8MiB.

**No encrypted payload discriminator/version is necessary.** local_format1 already
contains content_format in live Notes AND tombstones. Reopen selects Content validator
on plain or nonnull Stage; project HTML still uses existing Legacy validator.
Producer provenance: initialize/create/update/tombstone call validateLocalNote;
Legacy capture uses frozen eligibility; writer/unsealed source uses Legacy validation.
Private noteRow/seal/write/mutate offer no public raw DTO write. Protected local writes
need a current owner/scope WeakMap Note plan whose private route is Content, followed
by same-transaction source CAS. Low-level IDB is untrusted storage, not an admission API.
AEAD/canonical payload/identity/revision validation runs on every reopen, followed by
strict source-route validation; mindmap/map/node/future formats and extra fields fail.
No v9/new store/migration, no existing records or HTML payload rewrites.

**Proof1/candidate2/inbox7 remain unchanged.** Logical digest covers full inner
plaintext, including content_format; original codec8 wire digest, encrypted projection
and transport/outcome digests bind the result. History reopen compares authenticated
original Note with encrypted projection. Tests change format in an authenticated
projection and recompute public candidate digests: original-wire comparison still fails.
Changing format after prerequisite mint fails the logical-material digest check.
Prefix reauthenticates original wire/projection and current Metadata/Stage coverage.

### Supported production subset

| Content codec8 ordinary v1 route | Protected apply / replay / reopen / prefix / explicit ACK |
| --- | --- |
| project HTML | YES, existing semantics retained |
| Stage HTML | YES, existing ancestry semantics retained |
| project plain | YES, ID0/ID1 create/update/delete/replay |
| Stage plain | YES, ID0/ID1 create/update/delete/replay + authenticated Stage coverage |
| mindmap/map/node-owned plain | NO |
| future format / nonempty Content metadata | NO |
| Resolution v2 (including plain result) | NO; canonical reader-only barrier |
| Content conflict / self-echo / local writer | NO |
| Legacy plain | NO; eligibility/capture/writer/reader/apply unchanged |

Exact content, format, title/checklist/tags/color and route are retained. Plain
tombstones keep project/stage/source/map/node/format/deleted_at. HTML and plain do not
create separate graphs. Project plain requires exact Metadata and no Stage refs;
Stage plain additionally requires accepted authenticated live single Stage tip,
native-compatible bounded ancestry coverage, matching bootstrap and same owner CAS.
Safe later Stage advancement preserves prior plain proof and original bytes.
Missing/uncovered/unresolved/tombstoned Stage and dependency drift remain barriers.

### Verification and network

- New admission/source tests: initial **37 PASS**; final contentPlain **45 PASS**
  includes Legacy stripping rejection, both logical format substitutions, bad-source prefix.
- Shared project + Stage apply regression specs execute for **HTML AND plain**:
  **212 PASS /2files**, including ID0/ID1 create/update/delete/replay, metadata/Stage
  negative references, ancestry, original-wire/proof/candidate/source tampering,
  owner CAS and actual source/wrapper/candidate/auth/key/abort rollback.
- Shared project/Stage ACK specs execute for both formats: **32 PASS /2files**;
  one explicit request, unchanged retry/lost-success/no-progress/stale proof semantics.
- Mandatory Cloud C21 persistence/Legacy/unsealed/capture/history/prefix/ACK/migration
  suite: **1328 PASS /47files**. After the final newly admissible plain-route guard and
  extra tests, focused Content/Legacy/gateway suite: **269 PASS /4files**. No remaining
  failed/skipped checks. Initial test-wrapper import syntax error corrected before testing;
  production path unchanged by that correction. No repeated broad loops.
- Real Chromium: **206 groups PASS**, native IDB/Web Locks, **page errors0**.
  Existing HTML10–22 tests preserved; plain project23–28 and Stage29–35 cover ID0/ID1
  create/update/delete/replay, exact whitespace/literal markup, original candidate2/inbox7
  and local encrypted format1. Actual native source/wrapper/candidate/abort/auth/key
  injections run for project23 and Stage29. Session46 invalidation leaves no partial writes.
  Stage33 descendant preserves original plain29 proof; ancestor-ref update34/delete35
  works. Project36/Stage37 remain live and preserve exact plain strings on renderer and
  full disk-profile reopen. All26 Content histories reauthenticate without proof rewrite.
  Prefix/ACK38, pull46 survive profile restart; unresolved Stage39, Resolution40 plain,
  invalid mindmap41, missing Stage42, self43 and sibling44 remain received; safe Legacy45
  cannot leapfrog39. No plaintext content stored in durable records or logs.
- **Scenario-C clarification:** frozen/native owning Content codec rejects mindmap-owned
  payload (`content_note_map_owned`) before reader acceptance. Making that fixture
  readable would violate frozen contracts. Chromium verifies AEAD-authenticated codec
  rejection, no production writes and prefix barrier instead. Map/node admission likewise
  remains forbidden. This does not block the requested project/Stage plain subset.
- Prefix examples: Metadata1/projectPlain2/Legacy3→**3**;
  Metadata1/Stage2/StagePlain3/Legacy4→**4**;
  bad projectPlain2→**1**; bad StagePlain3→**2**. No unsupported event qualifies.
- Existing explicit ACK crosses project+Stage plain; max1 HTTP per invocation,
  server success before local cursor, retry behavior unchanged; no background ACK.
- Network **UNCHANGED vs accepted C21.1.27**: API122, registration22, capability11,
  mode34, registry26, bootstrap16, ACK13. Apply/proof/Metadata/Stage/prefix addedHTTP0;
  push/pull/Resolution/unrelated0. Only existing explicit ACK uses its existing network gates.
- Typecheck, production build, browser-script syntax, workflow YAML/mandatory spec
  inclusion and git diff --check PASS. Existing bundle-size/dynamic-import warnings only.
- Production backend/PostgreSQL/Alembic/native/SQLite/Rust/new dependencies: **NONE**.
  Legacy codec/global eligibility, codec8/crypto/AAD/compression/backend/Metadata/Stage/
  ACK contracts: **UNCHANGED**. Protected .pyc hashes unchanged.
- Expected Cloud backend tests; SQLite sync substrate NOT EXPECTED. Remote CI PENDING,
  **NOT POLLED / NOT WAITED**. Commit/push are authorized by the attached task.

### Простыми словами

- Новый Content-механизм уже безопасно принимал HTML.
- Теперь браузер принимает и обычный текстовый формат plain: заметки проекта и этапа.
- Текст сохраняется именно как plain, без преобразования в HTML, с точными пробелами
  и переносами строк. После закрытия и повторного открытия браузера он остаётся прежним.
- Безопасно принятые заметки учитываются в подтверждении серверу. Сломанные зависимости
  продолжают останавливать подтверждение; готовность синхронизации остаётся false.
- Старый Legacy-механизм не расширен: plain через него не принимается и не отправляется.
- Заметки карты, Resolution, конфликты, self-echo и локальная отправка Content остаются
  отдельными задачами. Формат существующей заметки нельзя менять между HTML и plain.
- Полная Web-синхронизация ещё не готова. Следующий ограниченный шаг — аудит и реализация
  сохранение конфликтующих peer Content-версий в общей истории Note; Resolution
  и локальную отправку не включать без отдельного задания.

## C21.1.29 — peer Content conflict preservation / shared Note group

**LOCAL COMPLETE / REMOTE CI PENDING — NOT POLLED** (2026-10-15).
C21.1.28 `f2c9a0ac2593c7c088f767f93c051492816be7b9`, Cloud `38662032578`
SUCCESS, all six required jobs SUCCESS; **REMOTELY ACCEPTED** by independent owner
acceptance. Official **84.0%**; C21 **IN PROGRESS**, C21.1.06 **NOT LOCAL COMPLETE**,
`ready=false`; no roadmap increment.

### Audit / exact decisions

Before implementation the checkpoint recorded the current-code audit and owner acceptance.
1. Content stopped at existing group/multiple tips and again after sibling detection.
   Additional Legacy-only applied/conflict evidence checks rejected actual codec8 members.
2. Reuse the existing group1 in legacyNoteHistory: common_parent_event_id, tip_revision,
   sorted members/tips, one remote_applied, remote siblings, conflict_generation. No second
   head, graph or store. Native note_sync.rs preserve_causal_note_conflict uses the same
   parent/revision checks and generation.checked_add(1); delete siblings are valid.
3. remote_applied must have actual retained applied evidence and candidate matching its
   transport. New peer Content groups require origin=peer, source device different from
   this device, exact header/wire/bootstrap, authenticated original plaintext/projection,
   and the existing winning local Note digest. Legacy-only own receipt/self-echo and
   local_unsealed paths retain their accepted validation and semantics.
4. remote must have actual Legacy conflict1 or new Content conflict proof, exact sequence,
   member generation and candidate. A group with Content cannot contain local_unsealed.
5. Existing content_note_proven/inbox7/proof1 describes an incoming local projection:
   it cannot truthfully describe a losing branch. Preserve it unchanged for clean apply.
6. Candidate2 as-is required an applied projection. Its transport_proof is now an exact
   backward-compatible discriminated union: applied (old fields/types unchanged) OR
   conflict_preserved (projection=null, projection_digest=null, source_revision=null,
   local_note_digest=null). Original wire/logical/dependency/proof digests remain mandatory.
   No fake LocalNoteRecord, losing seal or temporary incoming projection is created.
7. New inbox **record_version8 / content_note_conflict_preserved**, dedicated conflict
   proof1. DB schema version remains **v8**; these version numbers describe different things.
8. Third+ peer Content sibling extends the same group with generation+1 exactly once;
   old member proof/generation remains immutable. Exact replay returns already_applied.
9. Native Content feeds ordinary events into shared Note causality. Both mixed directions
   are valid within frozen Legacy-compatible project HTML: Legacy applied→Content sibling,
   Content applied→Legacy sibling. Stage/plain through Legacy still fails eligibility.
10. Native content_note_sync.rs same_scope compares full route, including format, against
    existing source and parents. Conflicts do not permit HTML/plain or Stage/source changes.
11. After reload, original codec8 AEAD/frame, candidate2 proof, exact group/member,
    common parent/revision/generation, peer evidence and current dependencies are checked.
12. Prefix uses the existing opaque Content certificate, now covering both applied and
    conflict states. Pure callers cannot manufacture qualification; counts.conflict
    increases for a preserved Content branch, not counts.applied.
13. IDBv8 is sufficient: no store/index/migration, existing records or payload rewrites.
    The v5 structural migration validator explicitly rejects the new impossible-in-v5 state.

### Implementation / supported subset

| Route or outcome | Status |
| --- | --- |
| clean project HTML / Stage HTML / project plain / Stage plain | YES, unchanged |
| peer Content update sibling, all four routes, ID0/ID1 | YES |
| peer Content delete sibling, all four routes, ID0/ID1 | YES; winner untouched |
| Content↔Content peer conflict | YES |
| Legacy applied + incoming Content sibling | YES, project HTML |
| Content applied + incoming Legacy sibling | YES, project HTML |
| third+ peer Content sibling / same group generation2+ | YES |
| conflicting create / route mutation | NO |
| local-unsealed + incoming Content / Content join to local-unsealed group | NO |
| self-echo Content / Resolution v2 / local Content writer / mindmap | NO |

The opaque prepareNoteTransportConflictCommit consumes the original authenticated
prerequisite, binds exact logical material and original codec8 wire, and schedules a
null-projection candidate through the existing deferred transport hook. Candidate,
group, head/frontier and inbox8 commit in ONE shared transaction. Local Note/project
shell/source revision and ACK cursor are unchanged. Source/history/inbox/bindings/
owner CAS and auth/key guards abort the whole transaction on drift or failure.

Current Metadata prerequisite is mandatory for each Content branch; Stage routes also
use the accepted Stage proof/ancestry check. When Legacy ingress uses Content history,
its plan retains an opaque Content replay hook so owner/dependency CAS still occurs in
that SAME final transaction. Opaque prerequisite snapshots from all Content branches
must have identical owners/bindings; mixed snapshots fail before commit, and the shared
snapshot is checked again in the final transaction. Legacy-only history remains on its
original path.

Shared peer-group verification reads each actual transport, authenticates each event,
compares routes with the common parent, binds the one linear winner and all exact
member sequence/generation facts. Applied Content remains usable as remote_applied.
The losing update/delete is only a history candidate. Open groups cannot authorize an
ordinary Content child or a Legacy child to silently choose a winner; Resolution stays
blocked. A different/uncovered fork remains a barrier rather than a new conflict graph.

### Verification / browser / network

- Baseline before implementation: **184 PASS /3files**, including reproduced Content
  sibling hard-stop, Legacy peer conflict and Legacy local-unsealed behavior.
- New Content conflict spec: **82 PASS**; project/Stage × HTML/plain × ID0/ID1 ×
  update/delete; original winner evidence/local envelopes unchanged; candidate null
  projection; group extension/replay; current Stage ancestry; valid second-Stage route
  mutation refusal; local-unsealed intent/open group barriers; proof/group/member/
  generation/dependency/wire tampering; candidate/group/inbox/auth/key/abort failures;
  Metadata/Stage/history/source CAS; Legacy ingress Content-owner CAS; incompatible
  opaque branch snapshots are rejected even when cursor stays unchanged.
- New Content conflict ACK spec: **9 PASS**, all four routes, bad dependencies,
  explicit max1/no-progress, HTTP/commit retry, prepared ACK invalidated by group tamper.
- Clean Content / Legacy conflict / local-unsealed / migration/open regression phase:
  **369 PASS /10files**. Mandatory Cloud C21 suite: **1421 PASS /49files**.
  After the last mixed-group guard and restoration of the original Legacy-only
  self-echo allowance, final focused Content conflict/ACK + Legacy apply/conflict/
  local-unsealed check: **166 PASS /5files**. No repeated broad unit loops.
- Initial new test injection targeted group.add, whereas accepted shared history uses
  group.put; the fixture was corrected. Initial fixture TypeScript shape errors were
  corrected. No remaining failed/skipped tests; no skip/xfail/continue-on-error.
- **Chromium208 groups PASS, page errors0**, native IDB/Web Locks, renderer and complete
  disk-profile reopen. Existing clean HTML/plain cases retained. Project plain winner38,
  sibling update39 and losing delete40 form a generation2 group without local writes.
  Stage plain winner41/sibling42/losing delete43 likewise; Stage44 safe advancement
  preserves original conflict42 proof and ancestry. HTML parent45/winner46/losing
  delete47 also preserves winner. Prefix/ACK cross all five conflicts to **48**.
- Actual native candidate/group/inbox/abort/auth/key failure injections at39 and42
  preserve every store. Tampered group/common parent, member sequence and wrapper cannot
  prepare ACK; isolated fixtures are restored byte-for-byte. Legacy root49 + pending
  unsealed edit + incoming Content50 remains barrier with zero writes. Safe Legacy51/58
  cannot leapfrog50. Legacy ordinary child59 cannot choose the unresolved HTML winner.
  Session60 invalidation has no partial writes. After disk reopen, **35 Content histories**
  including inbox7/inbox8 and candidate2 reauthenticate; shared groups and exact plain
  winner text persist. Durable proven48/ACK48/pull60; reconstructed candidate prefix49.
- Prefix examples: Metadata1/parent2/A3/conflict4/Note5→**5**;
  Metadata1/Stage2/parent3/A4/conflict5/Note6→**6**;
  bad dependency4→**3**. Local-unsealed open-group Content4→**3**;
  Chromium Content50→**49**, no leapfrog. Unsupported Resolution/self-echo still barriers.
- Network **UNCHANGED** vs C21.1.28: API122, registration22, capability11, mode34,
  registry26, bootstrap16, ACK13. Conflict apply/proof/dependencies/prefix addedHTTP0;
  push/pull/Resolution/unrelated0. Existing explicit ACK retains server-success-before-
  cursor, one request max per invocation, unchanged retry/no-progress; no background ACK.
- Typecheck, production build, workflow YAML/mandatory new spec inclusion, browser-script
  syntax and git diff --check PASS. Existing build size/dynamic-import warnings only.
- Production backend/PostgreSQL/Alembic/native/Rust/SQLite/new dependencies: NONE.
  Frozen Note/codec8/crypto/AAD/compression/backend/Metadata/Stage/route/Legacy-unsealed/
  ACK contracts unchanged. Protected .pyc hashes unchanged. Task preview/output cleaned.
- Expected Cloud backend tests; SQLite sync substrate NOT EXPECTED. Remote CI PENDING,
  NOT POLLED / NOT WAITED. Commit/push authorized by the attached C21.1.29 task.

### Простыми словами

- Раньше браузер принимал Content-заметки только с линейной историей.
- Теперь две конфликтующие версии от разных устройств можно безопасно сохранить,
  не выбирая автоматически окончательного победителя.
- Конфликтующая версия хранится в общей истории Note вместе с исходной зашифрованной
  codec8-обёрткой. Текущая локальная заметка остаётся прежней; даже конфликтующее удаление
  её не стирает.
- После перезапуска браузер заново криптографически проверяет версию, зависимости и
  принадлежность общей группе конфликта.
- Безопасно сохранённый конфликт учитывается в prefix и подтверждении серверу ACK.
- Конфликт с локальной ещё не отправленной версией, self-echo, Resolution и локальная
  отправка Content остаются отдельными задачами.
- Полная Web-синхронизация ещё не готова: ready=false, прогресс остаётся 84.0%.
- Следующий ограниченный шаг — аудит local-unsealed + incoming Content, начиная с
  project HTML и существующего Legacy pending intent; writer/Resolution не включать.

## C21.1.30 — Content + local-unsealed Legacy conflict / project HTML

**REMOTELY ACCEPTED**: `2b832a7d5b064a1ef313983b85f939d09e3ae128`, Cloud **38717317755 SUCCESS**, all six required jobs SUCCESS (owner supplied).
C21.1.29 `074b9d3d9e633e14c4f510050cc963750040bd79`, Cloud `38703171604` SUCCESS,
all six required jobs SUCCESS; **REMOTELY ACCEPTED** (independent owner acceptance).
Official **84.0%**; C21 **IN PROGRESS**, C21.1.06 **NOT LOCAL COMPLETE**;
`ready=false`, no roadmap increment.

### Audit / boundary / representation

The checkpoint records the audit BEFORE production edits. The accepted Content guards
rejected any localIntent or local_unsealed group and verifyPeerNoteGroup rejected
local members. Legacy already authenticates pending intent and encrypted snapshot,
freezes local_version1 through freezeLocalVersion, and uses Legacy conflict proof2
with local_version_id/local_mutation_generation/local_version_digest.

Reuse that exact local_version1, group1 and candidate2 conflict representation.
No Content-local version, fake remote projection or second Note authority is created.
Content conflict proof is now an exact backward-compatible union: **proof1** for
accepted peer-only groups (unchanged); **proof2** for local-unsealed groups, adding only
those three exact frozen-version fields. Inbox remains **record8 /
content_note_conflict_preserved**. Candidate2 still has conflict_preserved transport
proof, original codec8 wire/logical/dependency digests, null projection/digest/source
revision/local Note digest. **No candidate evolution, inbox9 or DB schema change.**

| Content outcome/route | Status |
| --- | --- |
| accepted clean + peer conflict project/Stage HTML/plain | YES, unchanged |
| incoming peer ordinary Content + current Legacy local-unsealed project HTML, stage=null, map/node=null | YES |
| incoming update/delete, ID0/ID1 | YES |
| second+ remote Content sibling, same frozen local group | YES, generation+1 |
| Legacy remote sibling extending that same group | YES, accepted Legacy proof2 retained |
| incoming plain / Stage HTML / Stage plain against this local Legacy route | NO |
| mindmap / wrong route / create / wrong parent/revision / same local event id | NO |
| Content self-echo / Resolution / local Content writer | NO |

Native/shared Legacy conflict semantics already support update/delete and generation
extension. Local producer remains the frozen Legacy writer: its project HTML/null Stage
eligibility is not broadened. The remote Content wrapper independently requires exact
current authenticated Metadata. Stage refs cannot authorize a mismatching local route.

### Verification / currentness / atomicity

verifyPeerNoteGroup remains strict. A separate narrow verifyLocalContentGroup handles
local mode: exactly one authenticated frozen local member and remote members. It checks
local version identity/digest/mutation generation, opens the frozen intent/snapshot,
compares parent/revision/bootstrap and complete route with the parent and each remote,
and checks actual Legacy2 or Content2 conflict proof/candidate/wire/member generation.
Current live intent must equal the frozen intent exactly; exactly one actual current
local Note record must equal its encrypted snapshot. This also applies on replay/reload.

New conflict creation reuses the accepted sibling planner and freezeLocalVersion.
Open-group extension reuses its immutable frozen local record and increments group
generation once. Exact replay returns already_applied without refreezing, duplicate
members, source writes or intent changes. Local working Note, project shell/source
revision, intent lifecycle, outbox and receipts remain unchanged by conflict preservation.

Frozen version, candidate2, group, head/frontier and inbox8/proof2 commit in the SAME
existing Note transaction. It already CASes inbox, binding, current intent inventory,
history, source snapshot and cursor; opaque transport hook CASes Metadata owners and
bindings, with auth/key/session guards. A source snapshot captured for local-mode
verification is reused for final source CAS, rather than silently replacing it later.

Prefix/ACK read the EXISTING legacyNoteIntents/localNotes stores along with their old
inventory, bind those exact snapshots to the opaque Content certificate, and compare
them again in the final prefix/ACK transaction. No stores/indexes were added. Stage
apply/prerequisite code and Legacy frozen-version verification remain unchanged.
New Content proof2 increments **unsealed_conflict**, not conflict/applied.

**Historical C21.1.30 limitation (superseded by C21.2.01 below):** changing, removing or sealing the current intent,
or changing its snapshot/generation, invalidates new Content proof2 qualification.
Historical Legacy conflict proofs keep their accepted behavior. This slice does not
invent requalification after later local edits/sealing, resolve a conflict, convert the
intent to codec8 or activate Content writer/upload. Frozen historical evidence is retained.

### Validation / browser / network

- Before implementation: **244 PASS /3files**, reproducing the old Content+intent
  barrier and checking Legacy local-unsealed, peer Content and clean Content baselines.
- New focused local-unsealed Content spec: **60 PASS**. Both ID0/ID1 update/delete,
  local update/tombstone, exact frozen version/intent/source retention, group extension,
  compatible Legacy extension, replay, currentness, route negatives, proof2/frozen/
  envelope/group/wire tampering, intent edit/removal/seal/generation/snapshot drift,
  source/history/Metadata CAS, auth/key/session, frozen/candidate/group/inbox/abort rollback.
- New ACK spec: **8 PASS**: explicit ACK4, max1/no-progress, plain barrier→ACK2,
  frozen/intent/source drift before send, HTTP/commit retry, intent drift after server
  success prevents stale local ACK cursor commit.
- Focused local + peer + Legacy unsealed/race/proof phase: **200 PASS /5files**.
  Updated clean Content/local/ACK phase: **206 PASS /3files**.
- Final exact mandatory Cloud C21 command: **1493 PASS /51files**, including peer
  project/Stage HTML/plain, mixed transport, Legacy unsealed/self-echo/backfill, clean
  apply, prefix/ACK and migration/open. First broad run found one obsolete assertion
  expecting HTML local-unsealed rejection; updated to the requested successful outcome,
  retaining plain rejection, then reran successfully. No remaining failures/skips.
- **Chromium210 groups PASS, page errors0**, native IDB/Web Locks. Legacy root49 has a
  current unsealed local update; incoming Content ID1 update50 and ID0 losing delete51
  produce inbox8/proof2 and one frozen local_version, group generation2. Local Note,
  project, intent, outbox and receipts stay byte-identical. Candidate2 has null projection.
  Actual native frozen/group/candidate/inbox/abort/auth/key injections roll back all stores.
- Local CAS scenario: Legacy root53, generation1 pending intent, prepare Content54;
  local edit coalesces generation2 before commit. Old plan aborts with zero conflict
  writes. Fresh explicit preparation safely binds generation2 and preserves Content54.
  Safe Legacy55 gives **prefix55 / ACK55**, with **unsealed_conflict3 / peer conflict5**.
- Frozen version/proof2/group tamper prevents ACK; isolated fixture rows restored exactly.
  Readable plain56, valid Stage HTML57/Stage plain58 against local Legacy HTML remain
  barriers without writes. Resolution59/self60 remain blocked; later Legacy61 cannot
  leapfrog56. Legacy unresolved-child62 and session-invalidation63 stay blocked.
- After renderer AND full disk-profile reopen: **38 Content histories**, proof1/proof2,
  original codec8 candidates, groups and intents survive; frozen local versions decrypt,
  exact pending local text remains, Metadata/current intent snapshot reauthenticate.
  Proven55/ACK55/pull63 survive and prefix reconstructs to55. No plaintext durable copy/log.
- Unit prefix example Metadata1/parent2/local pending/incoming3/Note4→**4**.
  Invalid/stale local proof does not qualify or advance the already safe **prefix2**;
  corrupt evidence fails closed. Plain/Stage mismatch at3→**2**.
- Conflict apply/frozen-local verification/Content proof/dependencies/prefix: **0 HTTP**.
  Harness API125, registration22, capability11, mode36, registry26, bootstrap16, ACK14.
  Compared with C21.1.29, +3 are ONE additional explicit ACK55 plus its TWO existing mode
  checks. No registration/capability/registry/bootstrap additions, no new endpoint.
  Push/pull/writer upload/Resolution/unrelated0. ACK protocol, max1, retries/no-progress,
  server-success-before-cursor and no-background-ACK behavior are unchanged.
- Typecheck, production build, workflow syntax/mandatory new specs, browser script syntax,
  git diff --check PASS. Existing build size/dynamic-import warnings only.
- IndexedDB **v8→v8**, twelve stores, no migration/new store/index/row rewrite.
  Existing Content peer proof1/inbox8, applied proof1/inbox7, candidate2 and Legacy conflict2
  remain valid. Backend/PostgreSQL/Alembic/native/Rust/SQLite/new dependencies: NONE.
  Frozen codec/writer eligibility/crypto/AAD/compression/Metadata/Stage/ACK/intent lifecycle
  contracts unchanged. Protected .pyc SHA256 unchanged; task preview/output cleaned.
- Cloud backend tests EXPECTED; SQLite sync substrate NOT EXPECTED. Remote CI PENDING,
  NOT POLLED / NOT WAITED. Commit/push authorized by the attached C21.1.30 task.

### Простыми словами

- Браузер уже умел сохранять конфликт двух удалённых Content-версий.
- Теперь можно безопасно сохранить и конфликт пришедшей из облака версии с локальной
  правкой, которая ещё не отправлена. Локальная правка не теряется и не заменяется удалённой.
- Локальная версия замораживается в защищённой истории как доказательство конфликта;
  сама pending-правка остаётся прежней и не превращается в Content-отправку.
- После перезапуска браузер заново проверяет замороженную локальную версию, текущий
  intent и исходную зашифрованную codec8-версию из облака.
- Безопасно сохранённый конфликт может учитываться в prefix и ACK. Если локальная
  правка затем изменится или будет запечатана, текущий proof2 перестаёт квалифицироваться;
  отдельная поддержка такого продолжения жизненного цикла ещё нужна.
- Это пока только совместимый маршрут заметки проекта в HTML, без этапа.
- Stage/plain local-unsealed, self-echo, Resolution и локальная отправка Content остаются
  отдельными задачами. Полная Web-синхронизация ещё не готова, ready=false, прогресс84.0%.
- Следующий ограниченный шаг — аудит безопасной повторной квалификации proof2 после
  Legacy coalescing/sealing, с сохранением frozen history и без Content writer/Resolution.

## C21.2.01 — durable Content local-conflict lifecycle

Historical execution label: C21.1.31; canonicalized by C21.2.03A. No implementation or CI identity changed.

C21.1.30 **REMOTELY ACCEPTED**: `2b832a7d5b064a1ef313983b85f939d09e3ae128`,
Cloud `38717317755` **SUCCESS**, all six required jobs SUCCESS (owner supplied).
C21.2.01 **REMOTELY ACCEPTED** (`0e9adfb75d47c3f6d094d29d502dc729d11a60bc`, Cloud **38787355382 SUCCESS**, all six required jobs SUCCESS, owner supplied); official **84.0%**, C21 **IN PROGRESS**,
C21.1.06 **NOT LOCAL COMPLETE**, `ready=false`.

### Creation and stored history have different lifetimes

Initial creation still authenticates the current Legacy intent and exact local encrypted
snapshot, generation, route, bootstrap, common parent/revision and current Metadata.
The commit retains same-transaction intent inventory, source, history, Metadata,
auth/key/session CAS. A later edit/removal/seal between prepare and commit aborts.
Adding a new sibling to a local group still checks the current authenticated branch and
exact current source; historical replay does not create or refresh a conflict.

Stored proof2 means: incoming Content was safely preserved against this exact frozen
local version. It does not assert that the frozen version remains the current pending
intent. The authenticated immutable local_version1, its digest and generation, group1,
Content candidate2, original codec8 wire and current Metadata dependency qualify the
historical server sequence. Group `local_unsealed` denotes origin at conflict time.
Current intent/localNotes/head may evolve without rewriting that evidence.

Coalescing preserves event_id, revision, parent_event_id and local_ordinal. Generation,
encrypted snapshot, operation, timestamps and seal state may advance. Frozen generation1
remains generation1. Update→update and update→delete are supported by the existing
Legacy producer; tombstone→update is not supported and remains rejected.
Transient retryable/blocked sealing failures and counters do not affect the proof.

Legacy prepareSeal/commitSeal atomically retain frozen/group, add a separate candidate1
local_sealed and sealed outbox, delete intent and advance head. Existing history
validation permits local_version + candidate with the same event identity. The later
candidate is authenticated, must retain account/project/Note/bootstrap/event/parent/
sibling revision and project HTML/null Stage route, and must match its exact outbox
item and original local ordinal. Its generation may be newer and its payload may differ
legally from frozen generation1. Acceptance requires the existing validated accepted
outbox/receipt pair; no remote proof rewrite. A new local revision after seal also
leaves the historical proof valid. No resolution or automatic group closure is added.

Prefix/ACK remain monotonic through coalescing, failures, seal and receipt acceptance.
Mutable intent/localNotes stores remain in inventory and certificate anchors. Prepared
operations become stale on lifecycle changes; fresh preparation succeeds. Already
ACKed history needs no duplicate ACK. Existing explicit ACK has at most one request
per advancing call, no-progress zero HTTP, `ready=false`.

Proof2, local_version1, candidate2, inbox8, group1 and DB **v8** remain unchanged.
No migration, stores, indexes or existing evidence rewrites. Immutable frozen/proof/
group/wire/dependency tampering and contradictory sealed/outbox evidence fail closed.
No backend/native/SQLite/PostgreSQL change, dependency, codec/crypto/AAD/compression,
Metadata/Stage or ACK transport change. Historical verification, coalescing, sealing
proof verification and prefix add **0 HTTP**. Legacy acceptance uses its existing path.

| Content Note boundary | Result |
|---|---|
| project HTML local-unsealed conflict, ID0/ID1 update/delete | YES |
| historical qualification after coalescing, seal errors, successful seal | YES |
| historical qualification after upload receipt acceptance | YES |
| prefix/ACK monotonicity; stale prepared operations require reprepare | YES |
| Stage/plain local-unsealed conflict | NO |
| Content writer / self-echo / Resolution | NO |
| full Web synchronization / ready | NO / false |

### Validation and release status

**Historical local execution status: LOCAL COMPLETE / REMOTE CI PENDING — NOT POLLED** (2026-10-15).
- Mandatory Cloud persistence command: **1526 PASS / 52 files**, including the new
  **36 lifecycle tests**, 57 Content-local creation/tamper regressions and 8 ACK tests.
- Focused local lifecycle/ACK phase: 100 PASS before the final additional source-boundary
  regression. Peer/Content/Legacy lifecycle regression phase: **312 PASS / 8 files**.
  Final creation/Legacy guard check: **116 PASS / 3 files**; the added source-boundary
  case then passed in the final mandatory 1526-test run.
- Real installed Chromium: **213 scenario groups PASS**, native IndexedDB/Web Locks,
  renderer reopen plus separate full disk/profile reopen with coalesced pending,
  sealed-only and accepted branches. Frozen generation1, proof2, group and codec8
  remain exact; prefix55/ACK55 remain valid. Initial creation race still fully rolls
  back; frozen and sealed causal tampering prevent ACK. Auth/key cases still pass.
- Chromium page errors **0**. Existing network totals unchanged: API125, registration22,
  capability11, mode36, registry26, bootstrap16, ACK14; Content push/pull/Resolution/
  unrelated API/protected apply/candidate-conflict requests **0**. Lifecycle verification
  and no-progress ACK add zero requests. Acceptance uses the real durable commit path
  with an isolated valid server-response fixture; no live Content upload is claimed.
- Typecheck PASS; production Vite build PASS (existing chunk-size warning); browser
  helper syntax PASS; workflow YAML PASS. New lifecycle spec is mandatory in Cloud,
  with no skip/xfail/continue-on-error. Migration/open tests pass in mandatory suite.
- Protected engine/game_data `.pyc` SHA256 unchanged; no backend/native/dependency edits.
- Final required checks pass; expected Cloud backend tests, SQLite sync substrate
  NOT EXPECTED. Original execution report: remote CI was PENDING — NOT POLLED / NOT WAITED. No roadmap increment.

### Простыми словами

В прошлом slice Web научился сохранять конфликт входящей Content-версии с ещё не
отправленной локальной правкой. Раньше доказательство зависело от того, что локальная
pending-запись навсегда остаётся неизменной. Теперь зафиксированная конфликтная версия
служит историческим доказательством: последующие обычные правки, попытки sealing,
успешный seal и подтверждённая отправка Legacy-ветки его не отменяют.

При создании конфликта текущая локальная версия по-прежнему проверяется строго.
После сохранения проверяется неизменяемая frozen history. Уже доказанный prefix/ACK
не становится недействительным задним числом. Content writer, self-echo, Resolution
и Stage/plain local-conflicts остаются отдельными задачами; полная Web-синхронизация
ещё не готова. Следующий ограниченный шаг — аудит сохранения новых входящих siblings
после sealing локальной ветки, без включения writer или Resolution.

## C21.2.02 — new Content sibling after local Legacy seal

Historical execution label: C21.1.32; canonicalized by C21.2.03A. No implementation or CI identity changed.

C21.2.01 **REMOTELY ACCEPTED**: `0e9adfb75d47c3f6d094d29d502dc729d11a60bc`,
Cloud **38787355382 SUCCESS**, all six required jobs SUCCESS (owner supplied).
C21.2.02 **REMOTELY ACCEPTED** (`4302477aa756ab7ee83ff4e3ee63b8030e158b4d`, Cloud **38793623485 SUCCESS**, all six required jobs SUCCESS, owner supplied). Official **84.0%**, C21 **IN PROGRESS**,
C21.1.06 **NOT LOCAL COMPLETE**, `ready=false`; no roadmap increment.

### Audit and admission authority

The former production conditions required localPlain and exact current intent/source
for every open group containing local_unsealed. Legitimate Legacy seal removes that
intent but retains the open group, frozen local_version1 and historical member source.
Its authenticated candidate1 local_sealed and exact outbox prove same-event continuity.
Neither a perpetual pending intent nor an unchanged current working Note is required
by that historical branch. Native conflict-version origin is a reference, unchanged.

Shared openContentLocalBranch verifies immutable frozen/header/digest/route/common
parent and any later sealed candidate/outbox pair. Existing historical group verification
uses it without changing stored-proof semantics. Separate verifyContentLocalAdmission
adds the NEW-sibling authority requirement. verifyCurrentContentLocalVersion retains
strict initial conflict-creation behavior and never silently accepts sealed state.

Only two admission modes exist:

| Mode | Required authority |
|---|---|
| Current-unsealed | original same-event authenticated intent, exact current snapshot/source, same bootstrap/parent/revision/ordinal, non-regressing generation, no same-event outbox/receipt |
| Historical-sealed | frozen version plus authenticated same-event candidate1 local_sealed and exact validated outbox; original same-event intent absent |

Accepted is the historical-sealed mode with an accepted outbox and mandatory valid
receipt. Receipt identity/protocol/positive sequence must match the local event; it
proves upload acceptance and never becomes a group-member identity. Candidate wire,
account/device/project/Note/bootstrap/event/parent/revision/ordinal and mutation
generation continuity are verified. Payload may have legally coalesced before seal.

A newer distinct local revision/intent may exist: it neither replaces nor authorizes
the original historical branch. Its current working projection is not overwritten.
Same-event pending plus sealed evidence fails closed. Intent absence alone is never
an admission fallback. If sealed continuation is missing, new R2 blocks while old R1
can remain independently qualified by frozen history. Contradictory/tampered sealed
candidate/outbox/receipt still fails historical verification as required by C21.2.01;
this is distinct from merely lacking continuation evidence for a NEW admission.

Incoming Content independently authenticates protocol3/codec8 ordinary-v1, peer device,
Metadata dependency/bootstrap and project HTML/null Stage/map/node route. Same common
parent and sibling revision are required; duplicate IDs, create, self-echo, Resolution,
plain, Stage and mindmap local-origin routes remain blocked. ID0/ID1 update/delete
siblings retain candidate2 conflict evidence with projection/source revision null.

Group1 stays open with the same ID, parent, tip revision and historical local member.
Each unique incoming sibling increments top-level generation once and adds a remote
member at that generation; old member generations/proofs/frozen bytes remain exact.
Sorted tips and existing head/frontier machinery are reused. New inbox8/proof2 binds
the original frozen version ID/digest/generation and the new remote member generation.
Replay returns already_applied without duplicates, generation or lifecycle writes.

No local Note/project source write, source revision increment, frozen/sealed candidate
rewrite, outbox rewrite or receipt rewrite occurs during sibling preservation. The
same transaction atomically writes new candidate2, group/head and inbox8. Existing
CAS snapshots history/group/frozen/intents/outbox/receipts, source, Metadata and auth/
key/session. Unsealed→sealed, sealed→accepted and concurrent group extension invalidate
old tokens; reprepare verifies the new state without optimistic generation merging.

Proof2 diagnostics remain **unsealed_conflict**, denoting historical origin. Safe R2/R3
qualify contiguous prefix and existing explicit ACK. An unadmitted R2 cannot itself
retroactively invalidate R1. ACK transport/retry/server-success-before-cursor ordering
are unchanged: at most one HTTP per advancing explicit invocation, no-progress zero.

DB **v8**, group1/local_version1/proof2/candidate2/inbox8 unchanged. No migration,
new store/index, format rewrite, new dependency, backend/PostgreSQL/Alembic/native/
SQLite/Rust change. Codec, crypto/AAD/compression, Legacy writer/seal, Metadata/Stage
and ACK contracts remain frozen. Apply/history/conflict/Metadata/prefix add **0 HTTP**.

| Content Note boundary | Result |
|---|---|
| Current local-unsealed project HTML conflict | YES, retained |
| Old historical proof after coalescing/seal/acceptance | YES, retained |
| New Content update/delete sibling after local seal | YES |
| New Content sibling after valid acceptance/receipt | YES |
| Multiple remote siblings and exact replay | YES |
| Newer working local projection preserved | YES |
| Local-origin plain / Stage / mindmap conflicts | NO |
| Content self-echo / Resolution / writer | NO |
| ready / full Web synchronization | false / NOT COMPLETE |

### Validation and release status

**Historical local execution status: LOCAL COMPLETE / REMOTE CI PENDING — NOT POLLED** (2026-10-15).
- New focused post-seal/ACK specs: **67 PASS / 2 files** (61 authority/route/proof/race/
  atomicity/replay cases + 6 ACK cases). Final focused recheck after type corrections
  also **67 PASS**. Lifecycle/peer/Legacy regression phase: **217 PASS / 7 files**.
- Mandatory Cloud C21 persistence command: **1593 PASS / 54 files**, including existing
  C21.2.01, C21.1.30 and C21.1.29, Legacy coalescing/sealing/self-echo/upload and migration/open tests.
- Installed real Chromium: **216 scenario groups PASS**, native IndexedDB/Web Locks,
  **0 page errors**. New ID1 update56 after seal extends historical group to generation3;
  ID0 delete57 and ID1 update58 after accepted receipt extend generations4/5. Earlier
  members retain generations1/2. Original proof50/51 and frozen generation1 stay exact;
  working Note unchanged. Prefix59/ACK59, unsealed_conflict6; barrier60 caps later safe65.
- Chromium unsealed→sealed race56 and sealed→accepted race57 abort old tokens with
  no partial writes, then fresh admission succeeds. Missing original intent without
  sealed continuation blocks new56 while old proofs/prefix55/ACK55 remain valid.
  Candidate/group/inbox/native abort/auth/key faults roll back every new sibling write.
  Frozen/sealed causal tampering blocks ACK. Renderer and full disk/profile reopens
  reauthenticate original and new proofs; sealed-only and accepted lifecycle restarts
  remain covered. Accepted response is an isolated valid fixture through the real
  durable acceptance commit, not a live Content upload.
- Chromium network: API131, registration22, capability11, mode40, registry26,
  bootstrap16, ACK16. Relative to C21.2.01: only two additional explicit ACK calls and
  their four existing mode GETs; no new registration/capability/registry mechanism.
  Apply/lifecycle/conflict/Metadata/prefix HTTP **0**. Content push/pull/Resolution/
  protected apply/candidate-conflict/unrelated API requests **0**. No-progress zero HTTP.
- Typecheck PASS; production Vite build PASS (existing dynamic-import/chunk warnings);
  both browser helpers syntax PASS; workflow YAML PASS, both new specs mandatory,
  no skip/xfail/continue-on-error; final diff check PASS.
- Schema v8 and all persistent formats unchanged; no migration or format-driven row
  rewrites. Normal new-sibling commit updates group/head and inserts candidate/inbox;
  old proofs/local member/frozen/candidate/outbox/receipt are never rewritten.
- Protected engine/game_data `.pyc` SHA256 unchanged. No backend/native/dependency edit.
  Cloud backend tests EXPECTED; SQLite sync substrate NOT EXPECTED.
  Original execution report: remote CI was PENDING — NOT POLLED / NOT WAITED. Official progress remains84.0%.

### Простыми словами

Ранее Web уже умел сохранить конфликт локальной правки и облачной Content-версии.
Затем мы сделали это доказательство устойчивым после отправки локальной ветки. Теперь
новая облачная конфликтующая версия может прийти и после того, как исходная локальная
ветка была sealed или принята сервером. Web проверяет её связь с той же исторической
веткой по frozen version, локальному sealed-кандидату и outbox/receipt. Старый pending
intent больше не требуется.

Конфликт остаётся одной общей историей Note, локальная заметка не заменяется.
Гонки sealing/acceptance с новым входящим событием требуют безопасной повторной
подготовки, без смешивания состояний. Stage/plain local-conflicts, Content self-echo,
Resolution и Content writer остаются отдельными задачами. Полная Web-синхронизация
ещё не готова. Следующий ограниченный шаг — аудит Legacy self-echo локальной ветки
в смешанной Content/Legacy группе, без выбора победителя и включения Content writer.

## C21.2.03 — Legacy self-echo in a mixed Content conflict group

Historical execution label: C21.1.33; canonicalized by C21.2.03A. No implementation or CI identity changed.

C21.2.02 **REMOTELY ACCEPTED**: `4302477aa756ab7ee83ff4e3ee63b8030e158b4d`,
Cloud **38793623485 SUCCESS**, all six required jobs SUCCESS (owner supplied).
C21.2.03 **LOCAL COMPLETE / REMOTELY ACCEPTED** (`582c671eed7227250bd7c06b3c34e2f9b379a104`, Cloud **38852780341 SUCCESS**, all six required jobs SUCCESS (owner supplied)). Official **84.0%**, C21 **IN PROGRESS**,
C21.1.06 **NOT LOCAL COMPLETE**, `ready=false`, no roadmap increment.

### Audit result: existing production behavior, explicit acceptance tests

No production edit is required by the observed behavior. Existing Legacy self-echo
admission already validates the entire mixed group before retaining an own-event proof.
requireOwnReceipt requires the local device, accepted outbox and durable receipt via
validateBrowserUploadPair, matching protocol and exact receipt server_sequence, plus
exact event descriptor/encrypted object after removing the server wrapper's device/
sequence fields. It never infers upload acceptance from pull and never creates a receipt.

The local candidate1 local_sealed already exists from Legacy seal. Mixed-group history
verification authenticates that candidate, exact causal identity, original frozen local
version and candidate/outbox continuity; source_device, bootstrap, project/Note/event/
parent/revision and crypto remain strict. The group is open and the historical local
member remains source=local_unsealed. Head is L after seal, or a legitimate later local
head; echo never selects a winner or rolls the head backward.

The existing own path skips peer conflict extension and protected local projection
writes. It emits existing NoteProof1 outcome=self_echo_applied in inbox3/note_proven,
source_revision/local_note_digest=null. group1, head, frozen local_version1, candidate1,
Content candidate2/proof2/inbox8, outbox and receipt remain byte-identical. No current
intent or old frozen/current-source equality is required. A newer working Note and
subsequent local Legacy mutations remain usable without applying old cloud text back.

commitHistoryChange receives identical retained history and takes its exact no-op
branch. The mixed Content dependency replay hook rechecks current Metadata owner/
binding inventory and finds its original candidate already present; it performs no
history write. Tests explicitly reject any write outside inbox during self-echo and
observe exactly inbox:put; exact replay observes zero writes.

verifyLocalContentGroup already accepts valid accepted lifecycle. The own proven inbox
row is extra corroboration, not a conflict member and not a requirement for old R1.
The full Legacy planner validates existing own proofs through verifyStoredNoteProof
and requireOwnReceipt, including before new Content sibling admission. Full prefix
verification authenticates the own proof and exact candidate/outbox/receipt join
independently of Content prefix. Corrupt proven echo blocks replay/new Content/prefix;
absence of echo leaves historical Content qualification unchanged. No extra group-level
state, circular proof dependency or persistent record is necessary.

Prefix counts own Legacy echo as **self_echo**, Content proof2 as **unsealed_conflict**.
Before receipt, own received row is a barrier and R1 remains qualified. Once exact
acceptance is durable, fresh prepare produces self_echo_applied and prefix/ACK may cross.
Explicit ACK remains at most one request per advancing call, no-progress zero HTTP,
server-success-before-cursor and retry semantics unchanged. No background mechanism.

Existing inventory CAS covers history/group/frozen, accepted outbox/receipt, binding,
cursor, current source where already anchored, Metadata and auth/key/session. Changed
inventory aborts stale self-echo plans atomically; fresh prepare validates current
accepted evidence. Legitimate unrelated upload acceptance is also covered as a stale-
inventory race. Prepare without receipt yields no proven token or partial proof.

Both R1→echo→R2 and R1→R2→echo preserve equivalent unresolved group semantics modulo
IDs/server sequence ordering. Additional Content siblings after echo use C21.2.02
historical-accepted authority; only that new sibling advances group generation. Receipt
and own echo prove cloud durability of L, never conflict resolution or a winning branch.

| Boundary | Result |
|---|---|
| Standalone Legacy own self-echo | YES, retained |
| Legacy own self-echo in mixed Content group | YES, explicitly tested |
| Multiple Content members / subsequent sibling after echo | YES |
| Group/frozen/Content proof/local projection rewritten by echo | NO |
| Local-origin project HTML Content conflicts | YES, retained |
| Local-origin plain / Stage expansion | NO |
| Content self-echo / Content writer / Resolution | NO |
| ready / full Web synchronization | false / NOT COMPLETE |

DB **v8** and all existing persistent formats remain unchanged. No migration, new store,
index, dependency, backend/PostgreSQL/Alembic/native/SQLite/Rust or protocol change.
The only self-echo write is the normal received→note_proven inbox transition.
Self-echo apply, receipt/group verification and prefix add **0 HTTP**. Existing explicit
ACK and authenticated reader/registry gates are reused.

### Validation and release status

**Historical local execution status: LOCAL COMPLETE / REMOTE CI PENDING — NOT POLLED** (2026-10-16).
**Production code changed: NO.** This slice accepts the existing path through mandatory
regression tests, Chromium scenarios, workflow coverage and documentation.

- New mixed-self-echo tests: **56 PASS** (47 core cases + 9 ACK cases) in the final
  mandatory run. Initial focused phase **55 PASS / 2 files**; final added case explicitly
  verifies subsequent Legacy mutation/seal after self-echo without resolving the group.
- Relevant C21.2.02 / C21.2.01 / Legacy self-echo/upload regression phase: **147 PASS / 6 files**.
- Final mandatory Cloud C21 persistence suite: **1649 PASS / 56 files**, no skipped tests;
  includes C21.1.30/.29, standalone self-echo, clean HTML/plain/Stage, lifecycle,
  upload acceptance and migration/open baselines.
- Real installed Chromium: **219 scenario groups PASS**, native IndexedDB/Web Locks,
  **0 page errors**. Own Legacy echo60 is proven after valid receipt in a group already
  containing multiple ID1/ID0 Content siblings. Only inbox:put is observed; group/head/
  frozen/candidates/Content proofs/local source/outbox/receipt remain exact. Auth/key/
  inbox/native-abort injections roll back every write. Exact replay performs no writes.
- Current working Note is edited after seal; echo60 does not overwrite it. New ID1
  Content sibling61 remains admissible after echo, advances only its own group generation.
  Prefix61/ACK61 counts **self_echo1 / unsealed_conflict7**; route barrier62 still caps
  later safe67. Receipt/outbox/own proof/group/candidate tampering prevents ACK.
- Own Legacy echo70 arrives before receipt on another mixed group, stays received over
  a full disk/profile restart, then exact durable acceptance enables fresh self-echo
  proof without group/source changes. Another disk/profile reopen validates replay.
  Main echo60 and all old/new Content proofs also reauthenticate after renderer/profile
  reopen. Acceptance uses isolated valid response fixtures through the real durable
  commit, not a live server upload or a new pull mechanism.
- Chromium network: API134, registration22, capability11, mode42, registry26,
  bootstrap16, ACK17. Relative to C21.2.02, one added explicit ACK scenario and its two
  existing mode GETs. Self-echo apply/receipt/group verification/prefix HTTP **0**;
  push/pull/Content writer/Resolution/protected apply/candidate-conflict/unrelated API
  requests **0**. No new registration/capability mechanism; no-progress zero HTTP.
- Typecheck PASS after correcting test-helper inventory types; production Vite build
  PASS (existing dynamic-import/chunk warnings); both browser helpers syntax PASS;
  workflow YAML PASS, both specs mandatory with no skip/xfail/continue-on-error;
  final diff check PASS. No production TypeScript file was edited.
- DBv8, proof/history/group formats unchanged; only normal received→note_proven own
  inbox transition. Protected engine/game_data `.pyc` SHA256 unchanged. No backend,
  PostgreSQL/Alembic, native/SQLite/Rust, dependency or frozen-contract changes.
- Cloud backend tests EXPECTED; SQLite sync substrate NOT EXPECTED.
  Original execution report: remote CI was PENDING — NOT POLLED / NOT WAITED. Official progress remains84.0%.

### Простыми словами

Локальная Legacy-версия может быть отправлена на сервер, даже когда вокруг неё уже
есть конфликт с Content-версиями. Когда сервер возвращает ту же версию обратно, Web
распознаёт self-echo, а не новую конфликтную ветку. Подтверждение сервера не означает,
что локальная версия победила: группа конфликта и Content-версии остаются неизменными.

Локальная заметка не перезаписывается старой отправленной версией. Точность self-echo
подтверждается accepted outbox и receipt. После проверки событие входит в prefix и
может быть подтверждено через ACK. До receipt оно остаётся барьером; после receipt
проверку можно безопасно подготовить заново.

Этот путь уже существовал в production; slice закрепляет его обязательными тестами
и браузерной приёмкой. Content self-echo, Resolution и Content writer остаются отдельными
задачами, полная Web-синхронизация ещё не готова. Следующий ограниченный шаг — аудит
Content self-echo и необходимой own-wire/receipt authority без включения writer/Resolution.
