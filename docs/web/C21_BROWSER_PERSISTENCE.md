# C21.1.02–C21.1.12 — Browser durable persistence / E2EE adapter contract

**Current C21.2.03A status (2026-10-17):** NUMBERING NORMALIZATION — LOCAL COMPLETE /
REMOTE CI PENDING — NOT POLLED; docs only, no functional progress.
Canonical C21.2.03 REMOTELY ACCEPTED, SHA `582c671eed7227250bd7c06b3c34e2f9b379a104`,
Cloud `38852780341` SUCCESS, all six required jobs SUCCESS (owner supplied).
Official84.0%, C21 and C21.2 IN PROGRESS, C21.1.06 NOT LOCAL COMPLETE, ready=false.
The numbering note below is authoritative; technical sections retain their accepted scope.

## C21.2.03A — numbering normalization / C21.1 boundary repair

**C21.2.03A NUMBERING NORMALIZATION — LOCAL COMPLETE / REMOTE CI PENDING — NOT POLLED**
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
backend tests **YES**, SQLite sync substrate **NO**. Repair CI remains PENDING — NOT POLLED.

The next functional slice is **C21.2.04**, only after this normalization is accepted.
No Content self-echo, Resolution, writer, prefix, ACK or conflict implementation is
continued by C21.2.03A.


**Current C21.1.23 update (2026-10-14):** v8 /12 stores, clean imported Stage-order
protected apply and exact membership/ancestor proof LOCAL COMPLETE; readyfalse.
C21.1.22 SHA24b6e90456e20aa73e1f735f573aed74e27cc5dc, Cloud38606705365 SUCCESS,
all six required jobs SUCCESS / REMOTELY ACCEPTED. Current details are in the final
C21.1.23 section; earlier dated schema/contract sections below remain historical.


Contract revision11, 2026-10-13. IDB schema6 implements dormant encrypted local source and atomic initial Legacy Note capture/receipt proof and exact completing/isolated remote completion; imported coverless Metadata protected apply remains unchanged.
C21.1.06 remains the broader BLOCKED / NOT LOCAL COMPLETE umbrella.
Starting local/fetched `6.0`: `0ad27ac4c5ccf09de99c2a8c3d29759003a39ee8`.
C21.1.01 independently accepted by owner/GPT: Cloud `38127992242` SUCCESS,
all required Cloud jobs SUCCESS; SQLite not triggered/not expected. C21 stays
IN PROGRESS, official WORTA ROADMAP SCORING v1.0 **84.0%**.

## Decision and limits

Use one origin/profile-scoped IndexedDB database `worta-web`, with Web Locks
exclusive writer ownership of `worta-web:writer`. Storage schema version **6**
implements `identities`, `accountBindings`, `outbox`, `inbox`, `cursors`,
upload-acceptance `receipts`, dormant `projectBindings`, Metadata-only `ownerHeads`, and canonical `localProjects`/`localNotes`.
Applied Metadata proof is part of the versioned inbox row; no separate apply-receipt store.
Other stores below remain a **frozen semantic design**, not implemented stores.
No full Web sync is enabled. Owner/GPT independently accepted C21.1.02 + .02A
at `245938f009c1914f52ee32927efe2e722858faef`: Cloud **38137926976 SUCCESS**,
all six required jobs, real Chromium persistence acceptance and contract tests
SUCCESS; SQLite not triggered/not expected.
C21.1.03 independently accepted at `8a9034782883baa2155a4bee2b2ed5952233c845`:
Cloud **38143710650 SUCCESS**, all six jobs, persistence/syncDurability tests and
real Chromium acceptance SUCCESS; SQLite not triggered/not expected.
No dependency added. No byte/schema compatibility with native SQLite claimed.
Existing Tauri/Capacitor factories and cloud runtime remain untouched.

IndexedDB supports transactions spanning stores and versioned upgrades. Every
foundation write requests `durability: 'strict'`; success is transaction completion,
not a request's success. This remains a browser durability hint, not a guarantee
against hardware failure or clearing site data. [IndexedDB specification](https://www.w3.org/TR/IndexedDB/).

Web Locks give cooperating tabs exclusive ownership until the callback promise
settles. The foundation holds that promise for its session lifetime; an unavailable
lock rejects immediately. [Web Locks specification](https://www.w3.org/TR/web-locks/).

Storage persistence and estimates are browser-controlled. Storage-disabled or
opaque-origin environments may refuse access; persistence does not protect against
explicit user clearing. [Storage standard](https://storage.spec.whatwg.org/).

OPFS would require a separate journal/commit protocol to atomically relate files
to IDB cursors/proofs. C18 cover limits fit bounded encrypted records; keep those
in IDB when implemented. Reconsider OPFS only in a separately accepted large-blob
slice. [File System standard](https://fs.spec.whatwg.org/).

Reject localStorage/sessionStorage: no multi-store transactional commit, inappropriate
for authoritative sync state, and no plaintext/key fallback allowed. Reject
in-memory/fake SQLite: cannot prove reload durability. Reject SQLite WASM/OPFS
packages now: new dependency/worker/filesystem architecture and license burden;
physical SQLite reuse is unnecessary. Reject plaintext compatibility HTTP API as
Web persistence authority: local baseline only, not the public E2EE path.

## Durable vs runtime boundary

Persistent allowlist: canonical account/device/project/entity/event identifiers,
lineage/sequence/revision/ordinal metadata, closed-enum phase/error codes,
authenticated encrypted envelopes and exact transport bodies, immutable receipts,
complete tip/dependency/proof references and encrypted blob bytes. Metadata must
not include user names/titles, arbitrary errors/backend bodies or derived text.
Identity is public pseudonymous metadata, not an authentication credential.

Passwords, plaintext AMK/Recovery Key, tokens/Authorization, decrypted manuscript,
notes, catalog names, game/custom-award text and plaintext drafts are never stored
for sync durability. Existing auth stays memory-only, as does RuntimeKeyContext;
existing draining leases zero temporary AMK copies on lock/logout. A caller must
obtain a verified current canonical normal-user context; this module does not
turn a caller-supplied UUID into server authentication. No standalone Web login
or key-runtime activation in this slice.

Future editor/projection state is rehydrated **in memory** by verified decryption
of retained canonical encrypted histories. No plaintext materialized IDB projection.
Do not lose accepted authority by caching only the visible winning tip: retain
all required immutable encrypted versions, conflicts, dependency proofs and receipts.
Pending edit capture must assign its event/parents using the frozen authority,
seal through existing codec/frame/AAD/key lease outside IDB, and then atomically
commit ciphertext + causal proof + outbox eligibility. No saved indicator before
commit. A crash before commit loses an unconfirmed edit; after commit it retries
exact bytes. Further edits create proper continuation events after immutable seal;
never reseal an already persisted event under the same ID. Implementing browser
capture/coalescing and editor autosave requires its own acceptance slice; native
unsealed/coalescing rules are not silently ported or weakened here.

## Stores, keys and indexes

All future stores are in the **same database** for atomic cross-domain apply/ACK.
No store is created speculatively before its implementing migration.

| Store | Primary key / indexes | Status / contents |
| --- | --- | --- |
| `identities` | `canonical_user_id`; unique `local_account_id`, unique `device_id` | Implemented v1: exactly canonical UUID user/account/device + `record_version: 1`. Random account/device generated internally once per canonical user. |
| `accountBindings` | `local_account_id`; unique `canonical_user_id` | Implemented v1: immutable local-account→canonical-user mapping + record version. Created with identity in one transaction. |
| `projectBindings` | `[account_id,project_id]`; unique `bootstrap` on `[account_id,bootstrap_id]` | Implemented schema4 / record1: exact native lineage/status fields. upload_existing prepared/registered; explicit import_remote captured/active with zero local cohort. C21.1.11 adds upload_existing registered→captured/initializing with exact count/HI; C21.1.12 adds exact captured→completing and validated remote active/high-water; ready/pause/blocked producers deferred; no title/path/content or arbitrary reason. |
| `outbox` | `[account_id,event_id]`; unique `ordinal` on `[account_id,device_id,local_ordinal]`, nonunique `state` on `[account_id,state,local_ordinal]` | Implemented schema2 / record1: account/device/event/ordinal, protocol2 or3, state `sealed` or `accepted` (schema3), exact `raw_body` from an existing singleton encrypted push. Accepted requires its immutable upload receipt; no unsealed plaintext. Causal parent/base-tip proofs remain inside existing sealed frames; authority capture is deferred. |
| `inbox` | `[account_id,server_sequence]`; unique `event` on `[account_id,event_id]`, nonunique `state` on `[account_id,state,server_sequence]` | Implemented schema2 / record1: receiving account/device, event/sequence, protocol2 or3, state `received`, exact metadata/encrypted envelope in `wire_item`. Wire validation is not crypto authentication or apply. Schema5 adds record2 `applied` with exact non-plaintext Metadata proof, preserving wire_item. Orphan/conflict/blocked producers deferred. |
| `cursors` | `[account_id,device_id]`, no indexes | Implemented schema2 / record1: pull cursor, `next_local_ordinal` starting1; `ack_cursor` and `proven_prefix` reserved at0, with no advancement API. Pull expected-old CAS is inseparable from inbox commit. Never infer ACK from ciphertext receipt. |
| `receipts` | `[account_id,event_id]`; unique `server_sequence` on `[account_id,server_sequence]` | Implemented schema3 / record1: exactly account/device/event IDs, protocol2 or3, server_sequence and first response duplicate diagnostic. Upload acceptance only. No protected-apply receipt, causal continuation, key/content/timestamp or arbitrary backend body. |
| `ownerHeads` | `[account_id,owner_kind,owner_id]` | Implemented schema5 / record1, Metadata only: owner_kind project_metadata, owner_id project_id; exact bootstrap, complete sorted tips and bounded retained-history proof references with per-event revision/generation. No decrypted projection. |
| `localProjects` | `[account_id,project_id]`, no indexes | Implemented schema6 / record1: device, safe project-wide source revision, deleted classification, authenticated opaque native Project payload + complete membership manifest. |
| `localNotes` | `[account_id,project_id,note_id]`; unique `identity` on `[account_id,note_id]` | Implemented schema6 / record1: stable membership/device, last changed source revision, native Note revision, live/deleted classification, encrypted full native Note or minimal routing tombstone. Primary-key prefix provides complete project enumeration; identity index prevents moving/duplicating a Note across projects. |
| `blockers` | `[account_id,event_id,code]`; `[account_id,state,server_sequence]` | Planned: orphan/conflict/dependency blocker references, sanitized enums; conflict versions retained in encrypted history, not silent LWW. |
| `accountObjects` | `[account_id,event_id]`; `[account_id,entity_type,entity_id]` | Planned: encrypted Catalog types4–7 and Game12/13 account objects plus canonical owner/proof references; Metadata, Stage and Content variants use existing ownership/crypto rules. |
| `encryptedBlobs` | `[account_id,blob_id]` | Planned: authenticated ciphertext/nonce/hash/size for covers and immutable blob versions; no absolute Word/Scrivener paths. |

Indexes ensure uniqueness and retrieval only; they do not authenticate encrypted
records. Every future repository must validate canonical user↔account binding,
origin device, project/bootstrap lineage and key-context lease exactly as the
SQLite semantic boundary does. Do not normalize unknown owner/codec/state into
success. Unknown nonempty content stays blocked with ciphertext retained.

## Atomic transitions and crypto work

Foundation: versionchange creates both stores/indexes atomically; identity and
binding are `add`ed in one strict readwrite transaction. Reopen validates both
records, schema and their immutable relationship; missing/inconsistent records
reject instead of auto-rebinding. Unique indexes prevent cross-account identity reuse.

The transaction helper accepts synchronous scheduling and IDB event handlers only.
No async callback, fetch, crypto, timer or arbitrary await inside a live transaction.
Future adapters prepare crypto under the existing current draining key lease first,
then use a short transaction that rechecks lifecycle epoch, expected complete heads,
lineage and expected cursor. No raw DB handle is exposed by a session.

Frozen future transaction units:
1. Capture: event identity/ordinal/parents + ciphertext + outbox eligibility/proof
   + monotone local-ordinal allocator (same transaction, expected-old validation).
2. Upload receipt: exact expected event + immutable receipt + outbox acceptance.
3. Pull page: entire validated encrypted page/replay checks + expected pull cursor.
4. Protected apply: verified envelope/dependency/complete-tip comparison + encrypted
   retained history/heads + applied proof/inbox transition. Failure/orphan preserves
   ciphertext and the ACK hole; no partial success across dependent C18 entities.
5. ACK preparation reads the contiguous proven prefix across supported entity types.
   Send HTTP ACK outside IDB. After validated reply, compare-and-set local ACK and
   durable proof atomically; lost reply/reload retries the same prefix. Never advance
   through unknown/corrupt/blocked rows or merely because ciphertext downloaded.
6. Bootstrap capture/cohort/registration/ready transitions use existing immutable
   token/event cohort/receipt proof. Account-wide registry reconciliation still gates
   normal pull/upload/apply/ACK; missing local lineage is not auto-connected.
7. Resolution commits retain exact complete tip sets, prior encrypted versions,
   explicit decision and continuation proof; preserve no-LWW/conflict algorithms.

## Recovery, lifecycle and compatibility

Reopen preserves identity/binding. An interrupted IDB transaction aborts atomically;
committed records are retried using their exact event identity/ciphertext. Reload
reacquires writer ownership before access and reruns account-wide reconciliation.
No background sync starts merely because persistence exists. After unlock, rehydrate
and verify encrypted authority/proof references before runtime use; key-locked
state cannot apply/ACK new work merely because an old receipt exists.

Session close/reset-for-logout immediately revokes session access, aborts pending
transactions, closes the connection and releases ownership only after transactions
settle. It deletes **no database/store/record** and does not alter remote history.
A stale handle cannot read/write even if another account opens. New account uses
its own generated local-account/device identities; it cannot `ensure` the old binding.
An optional AbortSignal supports auth/key lifecycle invalidation, including
cancellation during open/provision. Pagehide and database `versionchange`/unexpected
close also invalidate the session.
A future auth integration must subscribe to invalidation and first stop scheduling,
close/reset this handle and call existing key lock/drain; every result must check
current auth/key epochs. This foundation never accepts or holds a key context.

If an entire profile is cleared/evicted, it is a new installation/device, not an
invented continuation of missing cursors. Reauthenticate, explicitly import/reconcile
remote encrypted histories and require the existing project-bootstrap rules.
Unsynced data cannot be restored magically; browser/profile backups and encrypted
recovery remain future product work, not automatic export/deployment in this slice.

IDB version is separate from record version and C11/C15/C17/C18 wire/codec versions.
Current v5 supports a new empty DB, an exact v5, or non-destructive forward
versionchange upgrades from exact v1/v2/v3/v4. v4→v5 validates all seven old stores
and adds only empty ownerHeads (see C21.1.08 below). Historical v3→v4 validates all six old stores
and every receipt/outbox relationship, own echo and checkpoint, then adds only
empty projectBindings; no binding is inferred from events. Earlier v1/v2 gates follow. It validates every v1 identity/binding pair and their
indexes before committing the four added stores. Unknown/corrupt old records
or any quota/request failure abort the entire migration, leaving v1 data/schema
intact; no destructive recreation or clearing is attempted. The v2→v3 upgrade
validates all five existing stores and every scope/record/envelope, contiguous
retained local ordinals, allocator/pull positions and own-echo consistency. It
adds only an empty upload-receipts store, leaves every old row/body unchanged, and
rejects structurally corrupt/unknown v2 records without clearing anything. Opaque
ciphertext authentication remains protected-reader work, not migration crypto. Unknown future IDB version
raises a typed version blocker with no downgrade/delete. Known future upgrades
must be incremental, versionchange-atomic, preserve immutable ciphertext and identity,
validate old records before transforming, and abort on any unsupported record.
Older connections close on versionchange; blocked upgrades reject and require
explicit reopen after other tabs close. No copy into plaintext legacy API storage.
Rollback to an older app requires a compatible reader, not destructive migration.

## Multi-tab ownership

Conservative v1/v2 policy: **one writer session per origin/database across all accounts**.
Same-tab duplicate opens and second-tab opens reject `writer_busy` using exclusive
Web Locks with `ifAvailable: true`; no competing device provisioning. Different
account sessions serialize too. No TTL/heartbeat/localStorage lease, lock stealing,
server locking or automatic device regeneration. Frozen/background owner remains
owner; close its tab or logout to transfer. Browser crash releases the lock through
native lifecycle; tests cover tab termination and reacquisition.

Tabs on different browser profiles/origins are separate devices/storage boundaries.
BroadcastChannel can notify UI in a later slice but is not writer authority. Web
Locks/secure context missing or ownership failure disables persistence fail-closed.
The lock protects cooperating application code; arbitrary same-origin injected JS
is outside that isolation model. IDB is not a security boundary against XSS/browser
profile compromise; runtime decrypted state remains equally sensitive.

## Quota, private mode and storage pressure

QuotaExceededError is a typed `quota_exceeded` blocker; SecurityError/NotAllowed
means unavailable; other IDB failures map to bounded `storage_failed` codes. Never
return a successful identity/write on abort, request error, missing APIs, unsupported
strict durability, corruption or ownership failure. Error objects/log output contain
codes only, not DOMException messages, records or backend bodies. No fallback store.

`navigator.storage.persisted()/estimate()` are advisory retention/quota status,
not a reservation or proof of future durability; the foundation does not prompt
for persistence automatically. A future UI may explain and explicitly request
`persist()`, preserve ciphertext on denial and show retention limitations before
allowing important unsynced editing. No automatic deletion of ciphertext/conflicts,
or ACK/cursor advancement to free space. History compaction requires its own accepted
receipt/ACK recovery contract. Reject a failed transaction, retry only after capacity
is available; server success/local receipt failure must replay exact immutable event.

Private/incognito cannot be reliably detected. Even working IDB may be ephemeral;
this foundation promises reopen within the same retained profile, never survival
when a private session ends. Disabled storage rejects, no pretend persistence.
Public Web activation must provide retention/unsynced-data UX and browser-support
acceptance (Chrome/Firefox/Safari), plus quota/crash/recovery tests. Chromium local
proof here is not cross-browser/private-session survival acceptance.

## Semantic reuse and next slice

Reuse `CloudIdentityRepository` and `CloudAccountBindingRepository` shapes/validation
semantically with browser implementations. Reuse existing TypeScript encrypted
transport, codecs, frame/compression, key leases and coordinators where their
repository boundary permits it; do not instantiate native default compositions.
Outbox/inbox/cursor now have dormant IDB implementations below. ACK/protected
apply/bootstrap/authority repositories still require independent IDB implementations
and corresponding invariant tests, not SQL translation.
No C18 entities or Class C device-local bindings are redefined.

C21.1.03 implements the dormant sealed/received transport boundary below.
Upload acceptance receipts are implemented in C21.1.04 below. Protected apply,
shared ACK and account-wide reconciliation remain separately accepted work before
runtime activation.

## Implemented C21.1.03 repository boundary

`openBrowserPersistence(user).sync` exposes `enqueue`, `listSealed`,
`commitInboundPage`, `listReceived`, and `readCheckpoint`. Every method snapshots
`{canonicalUserId, accountId, deviceId}` and validates it against identity/binding
inside the same strict IDB transaction. No raw DB handle escapes to sync code.
Returned data is a detached structured clone. Close/logout/AbortSignal/pagehide/
versionchange tracks and aborts these transactions through the existing session;
stale handles reject and existing encrypted data remains retained.

`enqueue(scope, bodies)` accepts 1–100 already sealed singleton v2/v3 push bodies
from the existing encoders, with the existing ciphertext/envelope/batch limits.
The existing v2 validator covers ordinary/resolution Notes; the existing mixed v3
parser validates project and account descriptors, crypto1/1 and account crypto2/2.
No encryption, compression, codec decoding, content parsing, fetch or key lease
is performed here. New sealed records and the monotone ordinal allocator commit
in one transaction. Failure rolls back the entire enqueue batch and allocator.
The first body is saved unchanged. A canonical metadata/encrypted-byte duplicate
returns its original saved body/ordinal; conflicting identity aborts without LWW.
Whitespace/key order do not force resealing. Raw bodies must round-trip the
existing JSON encoder (apart from outside-string whitespace); duplicate/overwritten
JSON keys and noncanonical escape spellings are rejected before persistence so
raw retry bytes cannot hide discarded fields. Singleton delivery is an existing
transport shape, not a second protocol. Request batching/HTTP is not implemented.
Legacy transport1 writers are not added; existing historical Note snapshots and
resolution payloads remain opaque and readable through current v2/v3 envelopes.

Inbox remains `received`; outbox supports `sealed` and upload-proven `accepted`
in schema3. No applied proof, retry deletion or history pruning is inferred from
transport state. The upload-only receipt transition is implemented below.
List order is local ordinal for outbox and server sequence for inbox, with bounded
limits1–200; inbox supports `afterServerSequence`. Unknown record versions/state/
envelopes reject reads while retaining all rows. Read indexes do not filter away
unknown states as success.

`commitInboundPage(scope, since, rawPage)` validates the existing wire response
with the same protocol2/3 parsers and ≤200 received records. Mixed project/account
rows share one account/device cursor, never per-project or per-entity cursors.
A transaction compares `since` with stored pull cursor, preserves all descriptors
and encrypted nonce/ciphertext, checks event and sequence uniqueness and advances
only to the validated page's last durable sequence. An empty page cannot advance.
Lost-result replay is allowed only at the already committed next cursor with the
complete original interval, matching metadata and encrypted bytes. Missing rows,
changed envelopes, sequence/event collision, incomplete replay or stale cursor
abort the whole transaction. A v2 Note page replay through mixed v3 compares the
same metadata/encrypted bytes and retains its original received record; transport
version alone is not a new event identity. An own echo must also match its sealed
outbox metadata/envelope and source device before cursor advancement. Sequence gaps permitted by existing transport parsers
do not constitute applied proof or ACK permission. Unsupported/malformed incoming
pages are refused without cursor advance; server retry remains possible. Already
persisted unsupported/corrupt records are neither deleted nor normalized.

`readCheckpoint` restores exact pull cursor and allocator. An absent cursor is a
fresh zero position only when both sync stores have no retained records for that
account. Missing cursor with retained ciphertext fails closed instead of inventing
a new history. `ack_cursor` and `proven_prefix` stay0; no ACK preparation/publication
method, decrypted apply, conflict decision or account reconciliation is implemented.
Project lineage/bootstrap/owner heads and current key/auth epochs still require
future authoritative capture/apply composition; this dormant storage API does not
claim those proofs or activate existing native coordinators on Web.


## Local evidence and reproduction

`frontend/src/platform/web/persistence.ts` is dormant production infrastructure;
only its tests/harness import it in this slice. No existing startup/store/repository
factory changes. Type-only imports reuse existing native identity/binding interface
shapes without importing native command implementations at runtime.

Focused Vitest selection: persistence/platform, user auth, authoritative account
binding, key context, sync runtime and cloud session: **7 files / 57 tests PASS**.
Only the affected new persistence spec rerun after lifecycle/test improvements:
**3/3 PASS**. Existing crypto/key/session implementations were not modified.
TypeScript typecheck and production frontend build **PASS**; existing large bundle
and mixed static/dynamic documentDocx-import warnings retained. Script syntax and
`git diff --check` PASS; protected engine/game_data bytecode hashes unchanged.

Real Chromium acceptance: **13 scenarios PASS**, native IndexedDB and Web Locks,
with a temporary disk profile cleaned after browser shutdown. Demonstrated:
- first-open identity/binding commit with exact field allowlist;
- reload and browser process restart preserve exact account/device IDs;
- different-account binding rejection, distinct IDs, retained records after logout;
- same-tab/second-tab/different-account writer exclusion and owner-tab termination;
- logout abort/drain and stale-handle rejection;
- deterministic quota failure **after identity add was queued**, no partial rows;
- real asynchronous unique-key request failure, no partial rows;
- lifecycle cancellation during provision, no partial committed identity/binding;
- unknown binding-record version rejects without rewriting/reprovisioning;
- missing Locks/storage-disabled access returns typed unavailable, no fallback;
- external lifecycle AbortSignal revokes access;
- versionchange closes old handle, a future version refuses unsafe older open, records retained.

Failure injection changes native API descriptors/prototype methods **only within
the disposable test context**, and always restores them; successful IDB operations,
transactions, Web Locks and disk reopen are real. Initial harness attempt failed
because the storage-disabled probe did not restore the Window indexedDB descriptor;
fixed the test harness, not production. Final run: API requests **0**, page errors
**0**. No tokens, passwords, plaintext keys/content or arbitrary backend/error
bodies printed. Actual browser quota exhaustion, power loss and Firefox/Safari
acceptance are **not claimed** by deterministic Chromium failure injection.

```sh
# Existing installed frontend/Chromium tooling, no install/new dependency.
# Frontend directory, one terminal:
npx vite build --config scripts/vite.persistence-acceptance.config.ts
npm run preview -- --host 127.0.0.1 --port 5174 --strictPort --outDir .c21-persistence-dist
# Repository root, another terminal:
node frontend/scripts/browser-persistence-acceptance.mjs http://127.0.0.1:5174
npm --prefix frontend test -- --run src/platform/web/persistence.spec.ts \
  src/platform/web/syncDurability.spec.ts src/platform/runtime.spec.ts src/auth/userAuth.spec.ts src/auth/accountBinding.spec.ts \
  src/auth/keyContext.spec.ts src/cloud/noteSyncRuntime.spec.ts src/stores/cloudSession.spec.ts
npm --prefix frontend run build
```

The harness serves its isolated HTML and production-built actual module through
Vite preview on loopback (C21.1.02A); it does not mount the HTTP compatibility
application, mock its success, or touch user application data. Production application
smoke from C21.1.01 is retained, not repeated: its runtime paths are unchanged.
Full native/SQLite/Rust/PostgreSQL/Android/Windows/Nuitka suites and deployment
**not run**. Browser power-loss, public retention UX, encrypted repository/apply/ACK
acceptance and full Web cloud sync remain later gates. No full sync activation.

## C21.1.03 local acceptance / remote coverage

Final focused new encrypted-boundary Vitest **13 PASS**; new + foundation focused
rerun **2 files/16 PASS**. Affected persistence/platform/auth/binding/key/runtime/
cloud-session selection **7 files/57 PASS**. Typecheck, production frontend build,
production acceptance bundle, script syntax, workflow YAML/explicit hard-failure
coverage and `git diff --check` **PASS**. Initial typecheck definite-assignment error
in the validator was corrected; final gates pass. Existing documentDocx mixed-import
and large-chunk build warnings remain. Protected pyc hashes unchanged. Real Chromium uses the existing
production-preview harness and a disposable disk profile, with native IndexedDB
and Web Locks: **24 scenarios PASS**. It verifies v1→v2 identity/binding preservation, encrypted v2/v3
outbox and mixed v3 inbox/cursor commit, original retry bytes across reload/process
reopen, account/device isolation, writer exclusion/transfer, logout cancellation,
conflicting/incomplete replay and stale cursor, cursor-quota atomic rollback,
corrupt retained rows, missing cursor failure, versionchange/future rejection,
and rollback of corrupt/quota-failed v1 upgrades with safe retry. Fixture ciphertext
is deliberately opaque; no claim of decryption/apply/crypto authentication is made.
API requests0/page errors0. No user data or existing profile is touched.

Cloud CI explicitly runs `persistence.spec.ts` and `syncDurability.spec.ts`, plus
this same real Chromium acceptance with hard failures; existing dependencies and
Chromium installation remain unchanged. C21.1.03 publication is now **REMOTELY ACCEPTED** by the owner/GPT evidence
above; the original pending status is superseded. Expected Cloud; SQLite not expected. Codex does not poll Actions.
Physical quota exhaustion, power loss, Firefox/Safari, private-session survival,
full native/backend suites and complete Web sync remain unclaimed future gates.

## Implemented C21.1.04 upload proof contract

Authoritative evidence already exists in `V2PushResponse` / `V3PushResponse`:
version headers, results `{event_id, server_sequence, duplicate}` and
`current_cursor`. `parseV2PushResponse` and the unchanged v3 parser exported as
`parseV3PushResponse` validate the exact expected event and positive safe sequence
bounded by the returned high water. Server idempotency binds that event ID to the
original metadata/encrypted bytes; a conflicting reuse is refused by the frozen
protocol. Native `commit_note_sync_upload_acceptance` uses stable server sequence
for replay, retaining the first duplicate diagnostic even if a later retry changes
false→true. The browser follows those semantics. No server protocol changed.

`commitUploadAcceptance(scope, expectedEvent, response)` is dormant infrastructure.
A future uploader must obtain this response from the authenticated existing push
for that exact stored body and current context. Persistence is not authentication;
HTTP2xx alone, missing/reordered rows or a caller's guessed sequence is not proof.
Expected event is a detached captured outbox DTO; its state is not authority.
The method snapshots it and prepares the receipt through the existing parsers
before IDB. The strict transaction revalidates binding/device, loads the saved row,
checks exact original raw_body/event/protocol/local_ordinal/account/device, validates
both durable halves, checks sequence collisions/own inbox evidence, and inserts
receipt plus sealed→accepted update together. Completion is the success boundary.
No HTTP, key/crypto work or async scheduling occurs inside the transaction.

Receipt record1 contains exactly `record_version`, `account_id`, `device_id`,
`event_id`, `protocol_version`, `server_sequence`, `duplicate`. Account/device and
record version are local contextual/schema metadata, not invented server fields.
The protocol is the validated existing header; event/sequence/duplicate come from
the authoritative result. No client-generated receipt ID, timestamp, body hash,
synthetic sequence, plaintext content, auth token, password, AMK or Recovery Key.
Transient `current_cursor` is validated but not persisted or used to advance pull,
ACK or proven prefix. Protected-apply receipts/outcomes are still planned.

First commit returns `accepted`. Replay of the same immutable event/sequence returns
`already_accepted` with no write, preserving original proof and body. Duplicate and
server high water may vary between authoritative responses; neither changes stable
identity. Conflicting sequence, wrong event/scope/device/body/ordinal/protocol,
unknown event, or event/sequence collision fails closed. An accepted row missing its
receipt, a receipt beside a sealed/missing row, unknown state/version or mismatched
proof blocks reads/acceptance after reopen. Neither half is silently repaired.

`listOutbox` retains known sealed/accepted rows in ordinal order. `listSealed`
iterates rows and validates their receipt relationship before filtering accepted
rows, rather than hiding unknown states behind a state index. `readUploadReceipt`
validates the same pair, returns null only for a coherent unaccepted/absent event,
and returns a detached immutable proof for accepted data. No delete/prune method.
Outbox state is the only changed row field; original raw_body, event ID, protocol,
ordinal and encrypted nonce/ciphertext remain unchanged. Enqueue replay of an
already accepted event retains that accepted state and never reseals it.

Server-success/local quota/abort/crash preserves sealed row and no receipt. The
next network attempt must resend the exact original body/event/ciphertext; its
authoritative duplicate result can commit normally. The new store lives in the
same database and uses the existing exclusive Web Lock/lifecycle transaction drain.
Logout/revocation denies stale access and retains valid proofs. ACK/proven prefix
stay at0; no upload scheduler, HTTP orchestration, apply, conflict handling,
reconciliation, editor/bootstrap or full Web sync is activated.

C21.1.04 local evidence: receipt focused **7 PASS**, migration focused **4 PASS**,
affected persistence/sync/v2/v3/native-adapter DTO tests **41 PASS / 5 files**.
Real Chromium production-preview acceptance **33 scenarios PASS**: old encrypted
state preserved by v2→v3; corrupt/quota upgrade rollback; atomic acceptance/replay/
conflict; local quota/abort/real constraint failure and exact retry; reload/profile
reopen; multi-tab/account isolation/logout; inconsistent halves and future schema
retain proof/body. Failure injection stays in the disposable profile; native IDB
and Web Locks are real. Server responses are fixed protocol fixtures here, not
network activation or a claim of remote server acceptance. API requests0/page
errors0. Physical power-loss/quota exhaustion and Firefox/Safari remain unclaimed.

Cloud CI explicitly runs `persistence.spec.ts`, `syncDurability.spec.ts`,
`uploadAcceptance.spec.ts`, `persistenceMigration.spec.ts`, and the same real Chromium
acceptance with hard failures. No dependency/install changes. C21.1.04 publication
is **REMOTELY ACCEPTED** by owner/GPT: `16ce1e09d0043076aa2112845b776ca6b38ee807`,
Cloud **38151133406 SUCCESS**, all six required jobs, upload acceptance/migration
contract tests and real Chromium SUCCESS; SQLite not triggered/not expected. Official
**84.0%**, C21 **IN PROGRESS**. Expected Cloud; SQLite not expected. No Actions polling.

Next bounded recommendation: dormant retained encrypted history/reader-proof
repository; protected apply/shared ACK/reconciliation stay separate before activation.

Final C21.1.04 typecheck/production build, production harness build, workflow YAML/
explicit hard-failure coverage, script syntax and diff checks PASS. Existing large
chunks/documentDocx import warnings remain. Protected pyc hashes unchanged; disposable
profiles removed and task-owned preview stopped. Heavy native/backend suites not run.


## C21.1.05 native authority audit and read-only retained-history foundation

Accepted starting local/fetched origin6.0: `16ce1e09d0043076aa2112845b776ca6b38ee807`.
C21.1.04 independent acceptance above supersedes its historical pending status.
**C21.1.05 LOCAL COMPLETE / REMOTE CI PENDING**. Official84.0%, C21 IN PROGRESS.

Inspected production `noteSyncInboxDecrypt`, `noteSyncInboxApply`,
`noteSyncResolutionInboxApply`, `accountObjectReader`, `contentNoteReader`,
Document/Map runtimes/codecs, SQLite remote-apply repository, native `note_sync.rs`,
`content_note_sync.rs`, `account_catalog.rs`, Document/Map/Progress/Game apply,
Metadata/Stage/Cover contracts, SQL017/023/024/032 and C17/C18 frozen designs.
The exact account domain is local account binding to canonical user; source device
and pulling device are distinct. Transport server_sequence/revision/time never
establish causality, a winning tip or successful protected apply.

| Existing authority family | Existing owner and complete-history semantics retained |
| --- | --- |
| Note / Resolution / Content Note | Local account, project ID, Note entity ID; immutable parent/revision history, complete conflict event/version tips, conflict-group generation. Resolution requires the complete sorted resolved_event_ids/primary+additional parents and exact parent proofs, not merely the selected Note. Content Note retains bootstrap/metadata/stage dependency references and uses the same Note history engine, with its additional frame/envelope receipt. Map-derived Notes belong to Map authority. |
| Metadata / Cover / Stage / Stage order | Existing project/bootstrap identity and entity types remain distinct; Metadata entity_id equals project_id, Stage has its own entity ID, stage_order its fixed ID. Structural parents/generation, metadata/stage-head membership and cover encrypted-blob/reference dependencies stay in their existing authenticated frames/contracts. Cover is not invented as a new transport owner. |
| Document | Local account/project/stable document entity ID; stage relation can move and belongs to authenticated history, not a new independent owner. Full parents/revision/generation plus bootstrap/metadata/stage dependency event IDs and prior dependency branches must remain retained. |
| Map | Local account/project and exact existing `project-map` or `stage-map-<sha256>` entity ID. All current sorted event tips, parent ancestry and bootstrap/metadata/stage references; map and derived Notes share one apply unit. |
| Progress | Local account/project/project-or-stage owner; complete causal parent tips and retained entry/chain facts, bootstrap/metadata/stage proofs. No inferred revision winner or independently stored progress-order authority. |
| Catalog | Local account and canonical-user account scope, exact entity_type/entity_id (folder, folder_order, folder_membership, project_order). Complete sorted parent_event_ids/current tips, revision AND generation; folder/membership dependency maps and project bootstrap+metadata proof tuples remain distinct. |
| Game | Account owner is native `account`; project owner is canonical `[project_id,stage_id]`. Per-action transport entity IDs (`game:<event>` / `game:project:<event>` / stage action IDs) are NOT authority owner keys. Retained parent/action/dependency/reward proofs and concurrent tips are essential. |

Native Note/Resolution/Content, Map/Document/Progress/Game authority mutation
rechecks scope, exact envelope/frame and dependencies, then changes retained history,
complete tips, ledger/proof and inbox classification inside the same protected
transaction (and projection if authorized). Catalog also commits full tips, retained
canonical frame/envelope, dependency classification and apply ledger together;
its account inbox can remain `received`, so that state alone is not an apply proof.
An authentication-only account probe explicitly returns
`account_entity_codec_not_activated`; Note decrypt status `validated` is likewise
transient validation, not durable apply/ACK proof. Native SQL histories may contain
plaintext under their existing storage contract; no such projection/frame is copied
into browser IDB.

**Architectural boundary:** encrypted transport descriptors do not expose these
complete authenticated parents/dependencies/owner structures. A generic browser
head derived from revision/server_sequence or Game entity_id would be lossy.
Writing an authoritative complete head without the future protected-apply unit
would split the frozen invariant. This slice therefore exposes NO head write,
CAS, persisted reader/applied proof, or fake intermediate proof state. IDB stays
**3**, exactly the six implemented stores. No v3→v4 upgrade or `ownerHeads` store
is introduced; ownerHeads remains planned for its actual atomic implementation.
No blockers/accountObjects/encryptedBlobs/projectBindings store is created.

`session.sync.readRetainedHistory(scope, references)` is a dormant read repository.
References reuse the exact existing `V3Descriptor | AccountDescriptor` transport
identity (also covering v2 Note descriptors), including event/source device,
server_sequence, exact project OR canonical-user account scope, entity type/ID,
operation, revision and timestamps. They are query metadata, not persisted records
or authenticated reader output. Strict known keys reject content/error/token fields.
No browser owner-kind enum or normalized cross-family causal model is introduced.

A bounded nonempty batch (max200 unique events) snapshots caller primitives before
IDB, orders references lexically by event ID and validates account/device/session
binding plus checkpoint inside ONE readonly transaction over existing stores.
It resolves each event through accepted outbox+immutable receipt and/or the received
inbox event index; the original raw_body/wire_item strings are returned unchanged.
Existing v2/v3 validators check descriptors/envelopes; an own echo must exactly
match source device, metadata, ciphertext and receipt sequence. A sealed event
alone is not accepted history; a matching received echo remains readable without
promoting that local sealed row. Upload-only accepted history and received-only
peer history retain their distinct evidence. Returned DTOs contain no apply status.
No copies are written to a second history store.

The pure `validateBrowserRetainedHistory` helper enforces the same retained-pair
and exact-reference boundary. Neither helper authenticates ciphertext nor proves
parents/dependencies or complete-tip membership. Every supplied branch is returned;
there is no visible-winner filtering, inferred completeness or maximum-revision
selection. Missing history throws bounded `missing_history`, never empty authority.
Duplicate event references, wrong owner/revision/sequence/device, cross-account
substitution, missing acceptance halves, unknown versions/states or conflicting
own ciphertext fail closed. A batch either returns all references after transaction
completion or rejects; it cannot return a partially verified prefix. No auto-repair,
pruning or deletion. Reload/log-out keeps all original encrypted history.

A future protected reader must decrypt/authenticate under the existing draining
lease outside IDB, retain family-specific complete tips/parents/dependencies, and
atomically recheck immutable references/current complete heads while committing
history+heads+applied proof+inbox transition. Receipt/download alone cannot authorize
that transaction or ACK. That implementation needs separate independent acceptance;
no runtime/key/HTTP/editor/reconciliation/conflict/orphan/projection activation here.
ACK and proven prefix remain0.

Local acceptance: new retained-history spec **19 PASS**; affected persistence,
syncDurability, uploadAcceptance, migration and v2/v3 contracts **49 PASS / 6 files**.
Existing migration validation remains **4 PASS** within that selection; new v3→v4
migration is not applicable. Real production-preview Chromium **40 scenarios PASS**:
all previous migration/receipt proofs plus unchanged six-store v3 reads, exact
mixed account/project references, upload-only/received-only retention, canonical
read order, missing/conflicting references, real read-transaction abort, reload and
disk-profile reopen, Web Locks ownership transfer, account isolation/revocation,
unknown/broken durable records and future-schema rejection. API requests0/page
errors0; disposable protocol/ciphertext fixtures are not crypto/apply proof.
Cloud explicitly runs retainedHistory.spec.ts alongside the existing four C21 specs
and this expanded Chromium harness with hard failures. No new dependency or native/
backend/crypto/AAD/frame/codec/compression contract change. Typecheck, production
build, production harness build, workflow YAML/coverage, script syntax and diff
checks PASS. Existing large-chunk/documentDocx import warnings remain. Protected
pyc hashes unchanged; disposable profiles removed and task preview stopped.
Physical power loss/quota exhaustion, other browsers, native/backend heavy suites,
full frontend suites and protected apply remain unclaimed/not run.


## C21.1.06 prerequisite stop — no protected apply implementation

C21.1.05/.05A independently accepted by owner/GPT at repair
`af407f751cbda2898eb881f90fdd08177e2b28d3` (implementation
`eed5ed298838c32ddc8f526b4ad2992b4fecd6c4`), Cloud38165641607 SUCCESS,
all six required jobs SUCCESS. Historical pending status above is superseded.
Official84.0%, C21 IN PROGRESS.

Actual family matrix and native prerequisite evidence:
[Protected apply family audit](../cloud/C21_PROTECTED_APPLY_FAMILY_AUDIT.md).
Metadata apply checks the installation's durable project binding/bootstrap record
inside its transaction; typed account binding and possession of an authenticated
Metadata frame are insufficient. The planned projectBindings foundation is absent
from browser v3. Per the task's explicit additional-store STOP rule, no v4,
ownerHeads, verifier/apply API or applied proof is created. Cover material is another
specific prerequisite; account-only subcases were not conflated with project ones.

C21.1.06 **BLOCKED BEFORE IMPLEMENTATION / NOT LOCAL COMPLETE**. All existing
schema/stores/raw bodies/receipts/received inbox and cursors remain unchanged.
No premature proof/head write, new store, plaintext projection, network or ACK.
No new runtime tests/builds/CI specs, since there is no production implementation.
Review/authorize a bounded dormant binding/bootstrap-lineage persistence prerequisite
before resuming family-specific atomic protected apply. No points awarded.


## Implemented C21.1.07 installation-lineage contract

Accepted audit baseline `cbd7a294e0e7c7dbbe4f99c0dbfdec5d67b341fc`:
owner/GPT Cloud **38258729038 SUCCESS**, all six required jobs SUCCESS. Audit
accepted; **C21.1.06 remains BLOCKED BEFORE IMPLEMENTATION / NOT LOCAL COMPLETE**.
C21.1.05/.05A remain REMOTELY ACCEPTED. C21.1.07 **REMOTELY ACCEPTED** (83d6f40c971163d07e1077049df225f4c9fe8964, Cloud38285007363 SUCCESS, all six required jobs),
official84.0%, C21 IN PROGRESS. Historical schema3/audit statements above are prior
slice records; schema5 and the C21.1.08 section describe current code.

`session.projects` exposes ONLY `prepare`, `importRemote`, `read`, `list`,
`confirmRegistration` and `evaluateReadiness`. Each read/write uses the existing
session-owned transaction wrapper, revalidating canonical user/account/device
identity+binding in the SAME IDB transaction. Writes request strict durability;
transaction completion is success. No raw DB/store handle, generic patch/setPhase,
delete or rebinding method. Account/project key and unique account/bootstrap index
retain immutable account_id/project_id/device_id/bootstrap_id/mode. Project IDs
retain existing opaque nonempty bounded transport identity; UUIDs are canonical,
bootstrap IDs specifically lowercase UUIDv4 with native variant bits. No title/path
is converted into an ID. Native semantic DTO reused type-only, with no native IPC.

Record1 contains exactly record_version plus the twelve native fields:
account_id, project_id, device_id, bootstrap_id, mode, phase, remote_state,
initial_event_count, initial_local_ordinal_hi, remote_high_water,
initial_max_server_sequence, blocked_reason. All counters follow nonnegative safe
integer bounds. This slice has no complete atomic editor/capture evidence: cohort
count/ordinal stay0 and initial_max_server_sequence staysnull. blocked_reason stays
null; there is no existing native blocked producer to port and arbitrary reason
strings are forbidden. No creation/update timestamps or backend bodies persisted.

| Operation | Durable effect / authority boundary |
| --- | --- |
| prepare(scope,{project_id,mode:upload_existing}) | Explicit install/preparation action generates UUIDv4 outside IDB; creates prepared/null remote state with zero cohort. Existing same scoped project/mode returns original row in any supported phase, ignoring the unused new candidate UUID. No local projection is created. Future trusted coordinator must perform actual project existence/eligibility preflight before invoking it; persistence is not that preflight proof. |
| importRemote(scope,{project_id,bootstrap_id,remote_state:active,remote_high_water}) | Exact explicit inputs from a future authenticated remote registry/coordinator; creates native import_remote/captured/active with zero local cohort. No network, project shell, name or plaintext metadata. DTO is not cryptographically authenticated by this repository. Same immutable imported lineage retries return original record, preserving its first high-water; different lineage/mode rejects. |
| confirmRegistration(scope,expected,evidence) | Exact native registration evidence fields only: remote_state initializing/active and safe remote_high_water. prepared→registered or same registered/import-captured phase; high-water uses native max(old,reply), active cannot regress. All fields of expected-old record are CAS-checked. Exact desired record already present is idempotent; another high-water/phase or lineage is stale/conflicting. No independent remote-field patch. Future authenticated coordinator is responsible for evidence provenance. |
| read/list | Detached validated exact record / complete account-scoped list in primary-key project order. No arbitrary page limit silently hides projects. Wrong scope/device, unsupported record/version/state/fields or corrupted rows fail closed, never auto-repair. |
| evaluateReadiness | Read-only `{ready:false,code,required_cursor}`; missing_lineage, registration_required, capture_proof_unavailable or ack_proof_unavailable. No persistent ready flag or account-wide readiness claim. |

Native upload capture atomically scans ALL eligible current Notes, creates their
initial intents AND project binding, then freezes cohort count/local-ordinal high.
Existing browser sealed outbox/receipts cannot prove that capture included every
Note or freeze a missing captured cohort. Thus upload_existing registered cannot
advance to captured/completing, even when remote_state=active or counters/high-water
are zero. Prepared/registered rows prove a prepared lineage, not an admitted project
binding for protected apply. Explicit import captured follows the native zero-local-
cohort subset; it proves explicit installation lineage, not entity authority/apply.
No fake empty-cohort completion inferred from pull cursor/receipt acceptance.

Native markReady requires active remote and durable ACK >= max(remote_high_water,
initial_max_server_sequence), after coordinator reconciliation/bounded sync. Browser
ACK/proven prefix are reserved0 with no applied/ACK proofs. A zero required cursor
does not manufacture verified cycle completion. **No markReady/capture/markCompleting
API exists**, and no record1 producer/reader admits an unproven ready/completing or
upload-captured record. Native pause/resume is EXACTLY ready→paused→ready, with no
previous-phase field. **No setPaused API** until readiness exists; prepared/registered
cannot pause, and no invented resume-to-registered state. Native phase enum retained
in DTO typing; unsupported later states need a separately accepted proof/record
extension, not silently normalized success. No blocked/orphan/conflict record engine.

A successful v3→v4 versionchange validates identity/binding scopes, exact body/envelope
records, checkpoint/allocator positions and all upload receipts, rejects orphan/
missing/duplicate/sequence-conflicting proof halves, and leaves all six old stores
byte-for-byte untouched. Validation may use detached sealed-state copies only to
reuse earlier invariant checks; persisted accepted rows remain accepted. Quota/corrupt/request-abort/blocked-versionchange upgrades abort entirely; no clearing. Fresh v4 has exactly7
stores; projectBindings starts EMPTY after migration despite retained project events.
Future DB version refuses downgrade. All project lifecycle operations share existing
Web Locks, session revocation/drain and typed bounded storage errors. Logout never
erases lineage. No plaintext, password, AMK/Recovery Key, tokens or arbitrary error
messages. No ownerHeads/applied proof/inbox transition, HTTP or bootstrap activation.

Local evidence: projectBindings **23 PASS**, new v3-migration **4 PASS**; affected
persistence/syncDurability/retainedHistory/uploadAcceptance/old migration plus native
bootstrap-coordinator TS contracts **58 PASS / 6 files**. Existing coordinator tests
exercise native ordering, partial cohort, import, pause and registry gate semantics;
that coordinator is NOT connected to the browser repository. Initial UUID-negative
fixture was corrected (it had accidentally supplied a valid UUIDv4). Real migration
request-abort testing exposed an opener double-abort page error; guarded upgrade
abort preserves the original bounded failure even if the transaction already ended.
Final curated C21 invocation **73 PASS / 7 files**; all final gates pass.
Real production-preview Chromium **48 scenarios PASS**: all prior encrypted durability
proofs plus actual v3 upgrade/rollback, empty binding store/no transport synthesis,
explicit create/import and UUID/project uniqueness, exact registration CAS/replay,
wrong lineage/device/stale/caller ready/cohort fields, real transaction abort, reload/
disk-profile reopen, account isolation/Web Locks transfer/logout, unknown/unproven
records and future-version retention. A final preparation replay case additionally
proves unused candidate UUID collision cannot reset/conflict existing lineage.
API requests0/page errors0. Protocol/remote evidence are disposable fixtures, not
network activation or proof that a DTO authenticated itself. No mocked IDB/Web Locks.
Typecheck and production build PASS; existing chunk/documentDocx warnings remain.
Cloud explicitly selects the new lineage and migration specs with existing C21 specs
and the expanded Chromium harness, all hard failures. No dependencies/native/backend/
frozen crypto/AAD/frame/codec/compression changes. Other browsers, physical power-loss/
quota exhaustion, full suites and heavy PostgreSQL/Rust/SQLite not run.

First durable-lineage STORE prerequisite is implemented. Remaining upload capture/
readiness evidence, account-wide authenticated registry reconciliation, Cover encrypted
blob material and protected apply remain separately bounded. C21.1.06 is NOT complete;
no points awarded. After independent C21.1.07 acceptance, review the imported-lineage
protected-apply boundary and upload capture prerequisite; ACK/ready and Cover stay
separate. Do not infer admission/authority from the existence of a prepared row.


## C21.1.08 — imported Metadata protected apply (current schema5)

C21.1.07 **REMOTELY ACCEPTED** by owner/GPT at
`83d6f40c971163d07e1077049df225f4c9fe8964`, Cloud **38285007363 SUCCESS**,
all six required jobs SUCCESS. C21.1.08 **REMOTELY ACCEPTED** at
`720aea2d8857de572a706e6332180a08e8d79727`, Cloud **38293629801 SUCCESS**,
all six required jobs SUCCESS; owner/GPT supplied independent acceptance.
C21.1.06 broader umbrella remains **BLOCKED BEFORE IMPLEMENTATION / NOT LOCAL COMPLETE**.
Official **84.0%**, C21 **IN PROGRESS**, no points. Earlier schema/slice statements
above describe their historical implementations and are superseded here.

Only Project Metadata codec1/2 without a non-null Cover reference, exact persisted installation lineage
`import_remote/captured/active`, and clean transitions are implemented. Account,
canonical user, receiving device, project and bootstrap are checked against existing
identity/account/project bindings. Upload-existing prepared/registered/active is
ineligible: no complete capture/cohort proof. Other families, full Web sync,
HTTP/coordinator activation, ACK, readiness, projection/adoption/reconciliation,
Cover material and conflict/orphan persistence are absent. This encrypted authority
proof is not native `authority_view().state == active`, which additionally requires
visible/reconciled local projection; it cannot unlock dependent families or readiness.

`session.metadata.prepareVerified` uses current NormalUserAuthRuntime,
AuthoritativeAccountBinding and real RuntimeKeyContext draining lease. It reads
exact expected-old head/lineage and retained history, then authenticates each required
encrypted ancestor/event outside IDB with the existing object AEAD/AAD, Metadata
frame/decompression/canonical codec. Descriptor/account/project/entity/event/source,
operation/tombstone/revision and bootstrap must match. Temporary nonce/ciphertext,
wire-digest input/output and lease-key copies are zeroed; existing Metadata opener
clears decrypted bytes. Decoded Metadata objects are transient only. No title,
content, plaintext hash, key, passphrase, token or error body is stored. The opaque
frozen token has no data fields; module-private WeakMap provenance binds it to the
originating repository and current auth/key context. A caller-supplied `clean` DTO
cannot enter commit. The returned plan contains only authority/proof identifiers
and encrypted snapshots, never decoded Metadata.

Owner key is native Metadata project scope: `[account_id,'project_metadata',project_id]`.
Head record1 has account/device/owner/bootstrap, complete sorted `tip_event_ids`, and
sorted `history` containing exact proof/reference metadata for EVERY retained ancestor.
Per-event revision/generation/parents are retained, rather than one highest revision,
sequence, timestamp or LWW winner. Graph validation proves parent existence, native
revision=max(parent revision)+1, generation>max(parent generation), create1/1/no parents,
genesis-resolution parents all true genesis, and exact causal maxima. Bounds are
200 history references and 64 parents/tips; over-limit data fails closed without pruning.
This clean-only producer writes one resulting causal tip; validation never collapses
an existing complete multi-tip set or authorizes an incomplete resolution.

Inbox received record1 is unchanged. Applied record2 preserves ALL original fields
and exact `wire_item`, changes state to `applied`, and adds `applied_proof` record1:
protocol2/3, Metadata codec1/2 version, native owner kind, local account/project/bootstrap/event/source device,
server sequence, operation, revision, generation, ordered parent IDs, exact transport
descriptor and SHA-256 `wire_digest` over canonical protocol+descriptor+encrypted
nonce/ciphertext envelope. Proof1 fixes verification to frozen frame1/Metadata codec1/2,
crypto1/AAD1. Hash input is ciphertext/transport only, never plaintext. This binds
replay to the exact envelope, not only an authenticated header. Upload receipt remains
separate, immutable and unchanged. Original wire is never rewritten/deleted at apply.

`commitVerifiedImportedMetadataApply` performs ONE strict readwrite transaction over
identity/account/project bindings, ownerHeads, inbox, outbox, receipts and cursors.
Current canonical scope/auth/key context is rechecked; exact imported lineage and
bootstrap, full expected-old head and registration snapshot, immutable inbox
identity/sequence/protocol/wire, every retained ancestor/source/receipt and current
local candidate incompatibility are revalidated synchronously. No crypto, timers,
fetch or await run in this transaction. CLEAN only queues head replacement and
inbox applied proof/state together; success means transaction completion. Auth
invalidation/session close abort immediately; key-current checks precede writes
and run again on write request success. Abort/quota/constraint/lifecycle failure
preserves old head, received row and encrypted history; no partial proof.

No head means ONLY native create revision1/generation1/empty parents can establish
initial authority. An imported latest update must wait for causal predecessors.
Next clean event must cover the exact COMPLETE current tips and have verified applied
parent history with native revision/generation. Missing history/orphan, conflicting
create/stale branch, invalid parent transition or incompatible local state aborts:
received remains received, no blocker/conflict engine or head mutation. Retained
conflicting ciphertext is not discarded or marked ordinary applied. Conflict-preserved
history required for future full resolutions remains a separate authorized slice.

Exact applied replay returns `already_applied`, verifies existing proof and matching
history entry, and does not rewrite the head even after descendants/deletion. Changed
ciphertext, header, descriptor, protocol, sequence, bootstrap or proof rejects.
Retained-history reads accept validated received OR applied inbox plus the existing
accepted outbox/receipt sources. `listReceived` validates primary-key cursor entries, so unknown states fail closed
and applied entries cannot consume its received page limit; inbound-page replay preserves applied
records/proofs and original wire instead of resetting state.

Self-echo is closed as `self_echo_unavailable`: native also requires exact captured
candidate or pending decision/payload/state (`project_metadata_sync.rs:462–513`),
which browser transport/lineage does not persist. Even accepted outbox+matching
receipt+identical ciphertext/source/sequence cannot invent that proof. Missing inbox
with upload proof alone is `missing_history`. Pending local Metadata transport
conservatively returns `local_incompatible`. No lost-response receipt synthesis here.
Metadata codec2 with explicit null/removal follows the native no-material rule
(`project_cover_sync.rs:102`) and is eligible. Authenticated non-null Cover returns
`cover_material_unavailable`; the reference cannot be stripped or applied without
the separately planned retained verified encrypted material.

v4→v5 validates exact physical seven-store schema and every old identity/binding,
outbox/body, inbox/wire/received state, cursor/allocator, receipt pair and project
lineage row, including unique project/bootstrap identities. Adds ONLY empty
ownerHeads. Existing rows, bytes, accepted state, proofs, lineage, cursors and ACK0
remain unchanged. No head/applied proof is inferred. Invalid old state, quota,
request abort or blocked upgrade rolls back to v4. Future schema is refused without
repair/downgrade. Earlier v1/v2/v3 upgrades add only the missing authorized stores.

Local verification: focused Metadata **41 PASS**, v4 migration **8 PASS**, affected
C21 **73 PASS** across7 files; existing Metadata codec/runtime/bootstrap/compression
**35 PASS**. Real production Chromium **80 scenarios PASS**, actual auth/binding/key
runtime with disposable synthetic transport, actual AEAD/codec and actual native
IndexedDB/Web Locks; **API requests0/page errors0**. Covers migration and failure
rollback, genesis/causal/delete/replay/stale CAS, conflicts/orphans/generation/revision,
lineage/Cover/self-echo/receipt/local incompatibility, auth/key/session revoke, retained
ciphertext/no plaintext/ACK0, reload and full disk-profile reopen/isolation/lock transfer.
Unit scheduling driver is not a storage durability claim; real rollback is Chromium.
Typecheck, production/harness build, workflow/script syntax and diff checks PASS.
Cloud explicitly selects both new specs with current C21 specs and hard-failure
Chromium. No heavy PostgreSQL/Rust/SQLite suite needed/run; no dependencies,
native/backend/crypto/AAD/frame/compression/frozen contract changes. Browser strict
is a durability hint; physical power loss and other browsers are not tested.

## C21.1.09 — complete local capture prerequisite audit / STOP

2026-10-13. **BLOCKED BEFORE IMPLEMENTATION / NOT LOCAL COMPLETE**.
Accepted C21.1.08 `720aea2d8857de572a706e6332180a08e8d79727`,
Cloud **38293629801 SUCCESS**, all six required jobs SUCCESS, independently
supplied by owner/GPT. Imported coverless Metadata protected apply is REMOTELY
ACCEPTED; C21.1.07 remains accepted. Broader C21.1.06 remains NOT LOCAL COMPLETE.
Official **84.0%**, C21 **IN PROGRESS**, no points. Clean starting local HEAD ==
fetched origin/6.0 == accepted SHA. Acceptance recorded in checkpoint first.

### Browser local authority evidence

The missing prerequisite is a **durable canonical browser project-source repository**
with exhaustive family membership/deletion/dependency coverage and an immutable
source snapshot/revision token checked atomically against capture commit. None of
that is supplied by the existing encrypted transport DB or its ordinal allocator.
There is no new capture producer, cohort-status API, record format or schema here.

| Family / dependent state | Current Web path | Durable browser authority / exhaustive capture |
| --- | --- | --- |
| Projects | PlatformProjectReadRepository → ApiProjectReadRepository → projectsApi list/get (`infrastructure/projects/projectReadRepository.ts`, `infrastructure/api/projectReadRepository.ts`, `api/projects.ts`) | Absent. HTTP results and Pinia project/currentProject refs are views; projectBindings records only explicit lineage. |
| Legacy Notes | getNotesRepository selects ApiNotesRepository on Web (`infrastructure/notes/notesRepository.ts`); api/notes.ts uses project/stage scoped GET/PATCH/DELETE | Absent. No durable browser Notes payload table or exhaustive source revision. |
| Metadata | PlatformProjectMetadataRepository → ApiProjectMetadataRepository → projectsApi.updateMetadata | Absent for local upload-existing source. Imported ownerHeads/applied inbox prove authenticated retained remote history, not every current mutable local project field or local candidate. |
| Stage / Stage order | projectsApi createStage/updateStage/deleteStage/reorderStages → compatibility HTTP | Absent. Stage list/order in project DTO is not a frozen browser source transaction. |
| Documents | api/documents.ts Web list/get/save/progress → compatibility HTTP | Absent. Browser save sends content without native expectedHeads; editor refs are transient. localStorage remembers selection/scroll/zoom/typewriter state only. |
| Maps | ApiNotesRepository mindMap/saveMindMap → api/notes.ts project/stage HTTP | Absent. Editor data and a fetched map cannot prove complete map membership, annotations, derived Notes or source CAS. |
| Content Notes | Same Web notes API, including stage scope; native ContentNote runtime/writer is separate | Absent. No browser Content Note candidates, stable document scopes or causal/local source repository. |
| Progress | PlatformProgressRepository → ApiProgressRepository → projectsApi record/deleteProgress | Absent. No browser immutable progress journal/chain or complete project/stage source snapshot. |
| Project Game | api/game.ts Web /api/game/state and command endpoints | Absent. No browser canonical Game action ledger, owner/reward/dependency/capture source. |
| Project-scoped dependencies | Stage relations/order, map-derived Notes/annotations, document scopes, completion/reward links and project/catalog relations are API/native data | Absent as one complete browser project snapshot; IDs found in envelopes do not prove local source membership. |
| Deleted objects / tombstones | HTTP delete operations; retained sync envelopes may contain individual deletes | Absent as exhaustive browser-local deletion journal. Existing transport history proves only those events already retained, not every pre-existing local deletion or future mutation boundary. |

Evidence is code inspection, not a claim that user data does not exist elsewhere.
`Run Web.sh` launches Python-compatible development FastAPI with host test_data;
backend/app/routers/{projects,notes,documents,game}.py delegate to host Services,
and backend/app/dependencies.py:get_services returns app.state.services. Durable
host-side data, if present, is NOT browser-owned IDB authority. Separate HTTP list/get
responses cannot participate in an IDB source+cohort transaction or provide a complete
cross-family immutable source token; taking another GET after async sealing is a race.
HTTP capture is also outside this slice's no-network boundary.

`stores/projects.ts` uses ordinary Vue refs; `stores/cloudSession.ts:initialize`
returns unavailable outside Tauri. Production IDB creation is exclusively in
platform/web/persistence.ts with exactly the eight accepted v5 stores. Those retain
identity/account binding, sealed/accepted outbox, received/applied encrypted inbox,
cursors, receipts, lineage and imported Metadata authority/proofs. They contain no
mutable local project/Note/Stage/Document/Map/Progress/Game source tables. Browser
storage usage elsewhere is navigation, language/theme, search/workspace preference
or editor position, not manuscript/project authority. No Pinia persistence plugin
or existing local payload/CAS repository supplies the missing capture boundary.

Therefore complete deterministic browser-local enumeration is **NOT POSSIBLE**
with current adapters. Atomic source snapshot/CAS with encrypted cohort insertion
is **NOT AVAILABLE**. Web Locks protect cooperating durability writers, not mutations
made by host Services or UI/editor buffers. A staged encrypted plan cannot revalidate
an absent durable source. Current sealed rows, receipts, highest ordinal, timestamps,
visible objects or imported Metadata proof are expressly not substitutes.

### Exact native invariant inspected

`frontend/src-tauri/src/note_sync.rs` and
`frontend/src/infrastructure/sqlite/cloudProjectBootstrapRepository.ts`:

- `CloudProjectBootstrapRecord` has project/account/device/bootstrap/mode/phase,
  remote state/high-water, initial_event_count, initial_local_ordinal_hi,
  initial_max_server_sequence and bounded reason. Preparation checks local SQLite
  project existence, current device and Notes preflight before creating upload lineage.
  Registration checks exact immutable IDs, transitions prepared→registered only,
  preserves an already active remote state and uses MAX for remote high-water.
- `capture_initial_note_sync_intents` (5236) begins SQLite IMMEDIATE, validates
  account/device/project/bootstrap and upload_existing mode, and returns the ORIGINAL
  record for captured/completing/ready/paused without recapture. First capture requires
  registered + remote_state **initializing**, complete successful Note preflight and
  no existing cloud_sync_project_bindings row. Registered/active alone is not that
  native initial-capture admission condition.
- Within that SAME transaction it inserts project binding, selects ALL current
  `notes WHERE project_id=? ORDER BY id`, creates one initial upsert intent per row,
  allocates account/device ordinals and freezes count/high-water plus captured phase.
  Any missing/unsupported intent or SQL failure aborts binding, every intent/outbox
  allocation and phase together. Empty initial Notes yields count0/high-water0.
- `initial_event_count` is **notes.len() at that capture**, not every project object,
  current outbox count, current accepted count or history count. Preflight (5040)
  rejects Stage/map-derived Notes and non-html formats. C18 family-specific Metadata,
  Stage, Document, Map, Content Note, Progress and Game capture paths remain distinct;
  do not redefine the C16 Note cohort as generic all-family project capture.
- `initial_local_ordinal_hi` is maximum ordinal returned by those initial intents,
  not a snapshot of a global highest ordinal. `next_local_ordinal` (5497) uses
  account/device MAX(non-legacy outbox ordinal)+1 inside the owning SQL transaction.
  Cohort membership additionally requires exact account/device/project, entity_type
  note, positive ordinal and ordinal<=frozen high-water; unrelated lower ordinals
  do not count. Creating later work must not alter count/boundary.
- Native intents are initially **unsealed**, with snapshot_json/mutation_generation.
  Unsealed edits can coalesce into the same event/ordinal; sealing uses expected
  mutation generation. A new mutation after sealing creates a new event/ordinal
  (delete after a sealed initial event links its parent and exceeds frozen high-water).
  Frozen cohort membership is not an immutable plaintext image while unsealed.
  Browser outbox currently begins at sealed immutable bytes and must not copy native
  plaintext intent persistence or promise identical coalescing without its source proof.
- Capture's actual SQL enumerates current Notes rows, not a tombstone table or all
  historical deletes. Delete/tombstone evidence belongs to retained mutation history
  and writer rules; absent rows cannot be inferred as captured initial Notes. Any
  future browser source must expose the applicable deletion history explicitly.
- `read_initial_note_cohort_status` (5292) counts the exact scoped Note/ordinal subset,
  accepted rows with upload receipts, and COALESCE(MAX(receipt server_sequence),0).
  Complete means event_count==frozen initial_event_count AND accepted_count==event_count.
  Neither global pull/current_cursor nor unrelated/post-boundary receipts prove it.
  `commit_note_sync_upload_acceptance` (7126) validates exact account/device/event,
  stable positive sequence, sealed-envelope consistency and accepted receipt replay;
  the first duplicate diagnostic is retained. Web additionally records protocol2/3.
- `initial_max_server_sequence` remains NULL at capture and during partial upload.
  `mark_cloud_project_bootstrap_completing` (5325) first reads a COMPLETE cohort,
  then in a separate IMMEDIATE transaction rechecks immutable scope and stores that
  cohort's max sequence with completing phase. It is not registration high-water or
  global cursor. This is an observed two-transaction native method, not an invented
  browser full-record CAS/atomicity guarantee. Repeating on unchanged membership/
  immutable receipts yields the same boundary. No markCompleting producer added.
- Ready separately requires active remote evidence and durable ACK past max(remote
  high-water, initial max sequence); no browser ready producer follows from capture.

Inspected native regressions (read, NOT run):
bootstrap_capture_is_atomic_complete_and_idempotent;
file_backed_restart_reuses_bootstrap_token_and_initial_event_ids;
bootstrap_capture_rolls_back_binding_and_every_intent_on_failure;
edits_and_deletes_during_bootstrap_preserve_ordered_durable_work;
unsupported_note_blocks_before_token_and_before_capture;
accepted_cohort_completion_ready_and_pause_resume_are_durable.
C18 native capture entry points inspected: project_metadata_sync::capture_legacy_candidate,
stage_sync::capture_candidate, document_sync::begin, map_sync::begin,
content_note_writer::begin, progress_sync::capture and game_migration::capture.
They consume SQLite local sources/dependencies, not browser local authority.

### Bounded outcome and next prerequisite

**STOP BEFORE IMPLEMENTATION.** Schema remains5, projectBinding record1 unchanged;
upload_existing stays prepared/registered, count0/ordinalHI0/maxSequenceNULL.
Imported captured/active lineage is its existing zero-cohort import contract, not
local upload capture. Metadata ownerHeads and applied inbox proof remain unchanged.
No cohort/status/completing/ready API, new store, migration, sealing, source writes,
HTTP, ACK/proven advancement or protected-apply expansion. No Cover/self-echo work.
No backend/PostgreSQL/native/frozen contract/dependency changes.

Next separately authorized bounded prerequisite: design and independently review a
canonical encrypted browser LOCAL project-source repository, starting with explicit
project + eligible Legacy Note authority and source-version/CAS/deletion coverage,
with an honest family eligibility matrix. Other syncable local families/dependencies
must be represented or explicitly unsupported before any complete-project capture
claim. Keep local source storage separate from sync plaintext; require one actual
source+encrypted-cohort commit boundary or a proven atomic revision-token protocol.
Do not add that substrate/store/dependency under this documentation-only stop.

Local checks: source/usage/native-test inspection, documentation reference/status
consistency, unchanged production/workflow scope, protected pyc hashes and
`git diff --check` PASS. Runtime focused/migration/affected adapter tests, Chromium,
typecheck and production/heavy builds NOT RUN for docs-only STOP; nothing skipped
or softened, no runtime PASS inferred from prior accepted C21.1.08. No API requests
made or browser session launched; page-error count N/A. Existing Cloud docs/cloud/**
filter matches this audit publication; SQLite filter does not. After publishing,
audit CI PENDING — NOT POLLED; audit acceptance cannot make capture LOCAL COMPLETE.

## C21.1.10 — local source design preflight

Accepted C21.1.09 audit `be235b79e977f9f14aa573e9a606499f6aa687de`, Cloud
38310226431 SUCCESS, all six required jobs SUCCESS, owner/GPT supplied. Capture
remains blocked/not implemented; official84.0%, C21 IN PROGRESS.

Canonical Legacy Note source must retain the native payload fields: id, project_id,
stage_id, source_type, source_map_id, source_node_id, content_format, title, content,
checklist(id/text/checked), color, pinned, archived, sort_order, tags, created_at,
updated_at, metadata, and native local revision. NoteSyncRecord owns every field
except native local revision; that revision must remain distinct from project-wide
source revision and future cloud event revision. Nullable routing fields are retained,
not dropped. This slice admits only project-owned HTML, null Stage/map/node routing;
Stage/plain/map-derived sources are rejected, not silently converted. Stable Note
ID must be unique per account across project membership. Display title/system tags,
owner labels and stage names are UI projections, not canonical Legacy source.
Native update allows only title/content/tags/checklist/color/pinned/archived,
increments local Note revision and timestamp; delete retains route+deleted_at in
sync intent then removes live Notes row. Native initial capture enumerates live
Notes, not historic never-cloud-visible deletes. Local minimal deletion membership
may remain as a tombstone, but future initial cohort must not invent cloud-delete
publication for a never-published Note. Deleted projects cannot be captured.

Project source preserves the native ProjectRecord identity/scalars/nullable timestamps
and its opaque JSON payload; unsupported populated other-family content is refused,
not removed. No Stage/Document/Map/Progress/Game/Cover authority is introduced.
Existing RuntimeKeyContext provides current account AMK without a cloud project
binding. Existing object helpers use crypto1/AAD1 and stable canonical-user/project/
entity tuples (project_metadata and note). Versioned local plaintext wrappers are
inside ciphertext and cannot be mistaken for cloud frames; helpers, key derivation,
AAD bytes, wire/frame/codec and key lifecycle remain unchanged. No anonymous-key or
plaintext fallback. Crypto and payload validation occur outside live IDB transactions.


### C21.1.10 implemented local source / LOCAL COMPLETE

`session.localSource.bind(auth, accountBindings, keys)` is the dormant entry point.
It uses the normal-user runtime, authoritative account binding and draining AMK lease;
no cloud project registration is needed. Schema6 adds ONLY the two local stores above.
Record1 project ciphertext contains native id/name/goal/infinite/unit/status/nullable
created_at/updated_at/payload, lifecycle and sorted complete member IDs. Record1 Note
ciphertext contains all 19 native fields listed above, or minimal route/deleted_at plus
native local revision. Existing crypto1/AAD1 object helpers and project_metadata/note
stable tuples are reused unchanged; local-format1 is an encrypted source wrapper,
not a cloud frame/event/AAD/key protocol. Random authenticated nonces, canonical
bounded JSON, fatal UTF8 decoding, exact-key/source validators; buffers/key copies zeroed.
Only IDs/device/revision/deletion/routing metadata are clear. No plaintext durable.
Current authenticated unlocked account is mandatory; anonymous editing is not enabled.

`createProject` rejects duplicates. `initializeProject` accepts a trusted explicitly
complete project+Notes snapshot, validates ALL rows before one atomic write, and is
never called by production composition. No discovery/network/automatic HTTP import.
Exact identical initialization retry at source revision1 returns1 and preserves
original ciphertext; conflicting/partial retry or retry after a later mutation rejects.
The caller must guarantee the supplied set is complete: the repository cannot prove
completeness of an external HTTP/source dataset. It makes that explicit complete set
canonical, never merges it with UI cache or a partial collection. All member IDs,
live and tombstone, are covered by the encrypted project manifest.

Narrow APIs: createNote, updateNote(native editable seven fields), tombstoneNote,
replaceProject, deleteProject, readSnapshot, withDecryptedSnapshot, assertSnapshot.
No raw put, move, restore, import merge, cloud seal/capture/readiness producer.
Creation commits source revision1. Each subsequent authoritative project/Note mutation
increments it exactly once in the SAME strict transaction as its row writes. Native
Note revision starts0/increments on update/delete separately; local source revision
is never a cloud revision, timestamp, ordinal, server sequence or cursor. Null resets
and native color normalization are preserved. Pure reads/exact init retry do not increment.
Stable Note identity is unique per account, including deleted membership. A second
project cannot claim an existing ID; rejected moves never remove the original row.
Deleted project source rejects snapshots/future capture. Bound project deletion is
unsupported (no cloud deletion semantics); unbound deletion retains encrypted evidence
and advances its source revision. No resurrection/reuse API is provided.

Native bootstrap selects live canonical Notes; physically deleted never-cloud-visible
Notes do not produce initial cloud delete events. The browser retains minimal local
routing tombstones ONLY as deletion/membership/non-reuse evidence. Snapshot includes
them; a future initial live cohort MUST filter state=live, not manufacture publication
of deleted-before-capture Notes. No current tombstone is an outbox obligation. Later
cloud-visible delete obligations require a separately implemented capture/sync boundary.

ReadSnapshot retrieves Project AND ALL project-prefix Note rows in ONE readonly
transaction, validates/decrypts outside it, authenticates full membership, and returns
one immutable encrypted snapshot ordered by stable Note ID with an opaque verified
WeakMap token. No plaintext is retained in the token. Full native payloads can be
consumed temporarily via withDecryptedSnapshot outside any IDB transaction. Bounds:
4000 members, 8MiB per encrypted source payload, JSON depth64; excess refuses a complete
snapshot/initialization, never truncates. Clear metadata cannot quietly replace missing
members or fabricate a tombstone. Pure current CAS passes; changed revision/row/membership,
foreign scope, forged token, stale auth/key/session and deleted project fail closed.

`assertLocalSourceInTransaction` synchronously schedules full Project+membership
revalidation in a caller's SAME future source+outbox+projectBindings transaction.
It compares exact revision and encrypted rows as well as current scope/lease. This is
an infrastructure assertion primitive, not a public arbitrary mutation callback.
Future flow can read R → prepare crypto outside IDB → re-enter one transaction →
assert R → write cohort. C21.1.10 does NOT write that cohort or binding phase.
Mutation prepares authenticated replacement bytes outside IDB, rechecks the full
expected-old token inside the strict transaction, then queues all writes. Success
requires transaction completion; request abort/quota/auth invalidation/key lock/close
never reports a partially committed mutation.

v5→v6 validates exact eight-store schema, immutable identity/binding, all transport/
receipt/cursor invariants, every applied inbox proof, all Metadata head ancestry and
matching imported bootstrap/proof links. Detached received views permit the old
transport validator without modifying any applied row. This is STRUCTURAL validation,
not AEAD or wire-digest recomputation during versionchange. No key or async crypto in
upgrade. All eight original rows/bodies/proofs/heads remain exactly preserved; new
locals start EMPTY, no inferred source. Corrupt structural v5, forced abort and quota
roll back the whole upgrade. Future version refuses downgrade without clear/recreate.

Validation: local authority34, local migration14, affected C21 persistence/receipts/
lineage/Metadata122 tests PASS. Production Chromium acceptance98 cases PASS, real IDB/
Web Locks and actual sodium/auth/account/key runtime, zero application API requests,
zero page errors. Includes preserved applied v5 fixture, source initialization abort,
Note/revision rollback, full membership missing-row refusal, current/stale future CAS,
reload/profile reopen/account/device/logout/multitab, no durable plaintext, no sync writes.
Harness synthetic Metadata sequences now follow prior immutable receipt sequences as
well as pull position; this corrects fixture collision without relaxing production rules.
Typecheck and production build PASS (existing chunk/dynamic-import warnings only).
Cloud workflow explicitly runs both new specs plus mandatory real Chromium entry point.
SQLite NOT EXPECTED; remote CI PENDING — NOT POLLED; no skipped/softened gates.

C21.1.10 LOCAL COMPLETE, remote acceptance pending. C21.1.09 audit REMOTELY ACCEPTED
at be235b79e977f9f14aa573e9a606499f6aa687de / Cloud38310226431 all6SUCCESS;
its capture remains NOT IMPLEMENTED / BLOCKED / NOT LOCAL COMPLETE. Local repository
is dormant, NOT wired to editor/UI. HTTP compatibility remains non-authoritative;
no transport, outbox/receipt, projectBinding, ACK/proven prefix or protected-apply
semantics changed. Other local families and Cover remain unsupported. C21.1.06 broader
NOT LOCAL COMPLETE; official84.0%, C21 IN PROGRESS, no new points. Next bounded slice:
independently review explicit eligible Legacy Note source consumption and atomic
initial capture using this snapshot/CAS, with no complete-project/multi-family claim.


## C21.1.11 — atomic initial Legacy Note cohort / LOCAL COMPLETE

C21.1.10 independently REMOTELY ACCEPTED at
`ffc018af7abeb7a5a696af26db0621640e6f0a5a`, Cloud **38317517321 SUCCESS**,
all six required jobs SUCCESS (owner/GPT supplied). The older source-absence audit
in C21.1.09 remains accurate history; its main source blocker is now resolved.
C21.1.09 itself is NOT relabelled as implemented capture. C21.1.06 broader NOT LOCAL
COMPLETE. Official84.0%, C21 IN PROGRESS; this is NOT complete-project capture.

### Native equivalence and exact proof without new persisted structure

Inspected native `capture_initial_note_sync_intents` and
`read_initial_note_cohort_status`, prepare_unsealed_note_intent, ordinal allocation,
registration/capture/rollback/restart/local-mutation tests. Native requires exact
account/device/project/bootstrap, upload_existing, registered, remote initializing;
active registration is NOT capture-eligible. Notes selected ORDER BY id; complete
live Notes only; preflight rejects Stage/map-derived/non-html. Native starts initial
HI0 and takes max allocated initial ordinal; empty initial Notes means count0/HI0,
not current pre-capture ordinal. Native Note local revision is separate from first
cloud event revision1/no parent. Native unsealed intent may coalesce until sealed;
this browser slice seals the full snapshot outside IDB and commits immutable exact
bytes, so later mutations cannot rewrite its initial cohort. Normal later-event
production/coalescing is NOT activated.

Browser capture reserves a SINGLE contiguous ordinal range for exactly N prepared
singleton events at allocator start A, then writes count=N, HI=A+N−1 atomically.
Thus the existing count/HI encode exact interval [HI−N+1,HI]. Every ordinal in that
interval MUST be a valid initial Note upsert/revision1 of this account/device/project,
with distinct event and member IDs in stable-ID order. N0 requires HI0/empty interval.
This is NOT the prefix <=HI. Earlier unrelated events, even same-project different
Notes, are outside the interval; later enqueue uses monotonically increasing allocator
and cannot join it. Outbox rows/raw bodies are immutable through existing public
producers; unique account/device/ordinal index prevents replacement/collision; no
public prune/delete/reorder producer exists. Capture is the sole producer of
upload_existing/captured; generic registration transition cannot set that phase or
counters. Immutable project/bootstrap identity permits only one such capture.
These enforced writer invariants prove exact cohort membership without a manifest,
new field/record version/store or schema migration. Status is structural receipt proof
over these committed immutable facts, not a second AEAD/source authentication pass.
Corrupt missing interval members, wrong project/type/revision/order, broken accepted
receipt halves or conflicting receipt identity/sequence fail closed, not partial proof.
A previously emitted or received cloud Note matching an initial live member rejects
capture: it cannot become a second genesis. Earlier unrelated Notes do not count.

### Runtime and atomic boundary

Dormant `session.initialNotes.bind(auth, accountBindings, keys)` exposes prepare,
commit, capture and readStatus. No production UI/editor/coordinator activation.
Prepare requires exact stored expected-old eligible lineage, current normal user,
authoritative account binding and current draining AMK lease. It reads ONLY
BrowserLocalAuthorityRuntime.readSnapshot and withDecryptedSnapshot, no arbitrary
Note array/HTTP/UI/outbox-as-source. All live eligibility validated before sealing;
local tombstones remain source evidence and NEVER create initial cloud delete events.
Unsupported non-Legacy source fails the whole project, never an easy subset.

Opaque frozen empty plan token is bound by private WeakMap to runtime/scope/lease,
original LocalSourceToken/source revision R, exact expected binding, complete ordered
member IDs, generated UUIDv4 event IDs and immutable sealed singleton raw bodies.
Caller DTO/forged/cross-runtime token cannot authorize capture. Crypto outside IDB:
existing createNoteSyncPlaintext → encodeNoteSyncPlaintext → existing validated object
crypto tuple/crypto1/AAD1 → encodeV2Push. This is the exact frozen Legacy C15 JSON
writer path/readable by openNoteSyncEvent, not a C18 Content Note frame. No invented
frame/compression selection or wire/version/key/AAD change. Canonical plaintext byte
buffers, temporary nonce/cipher buffers and leased AMK copies are cleared; JavaScript
plaintext objects/strings are temporary runtime values and are not durable/in the plan.
Each raw body is a normal immutable protocol2 sealed Note upload event; no upload.

ONE strict readwrite transaction spans identities/accountBindings (session guard),
localProjects/localNotes/projectBindings/outbox/inbox/cursors/receipts. It rechecks
scope/session/current auth/key and full expected-old binding, then calls
assertLocalSourceInTransaction with original token in that SAME transaction. Reads
and validates existing allocator/all retained outbound+receipt facts, requires safe
contiguous global existing ordinal state and exact next ordinal, rejects event ID
collisions with outbox/inbox or duplicate prepared IDs, reserves the full range,
adds every sealed row, updates allocator and registered→captured binding together.
No await/crypto/HTTP in live transaction. Request success is not mutation success;
only transaction completion succeeds. Abort/quota/async constraint/auth invalidation/
key lock/close leaves zero new cohort writes and original allocator/binding counters.
Changed Project OR Note source R rejects stale source without partial capture; caller
may restart from a fresh snapshot/plan with new uncommitted event UUIDs.

Empty capture still asserts exact source R and lineage; captured count0/HI0/maxNULL,
no outbox row or invented ordinal and allocator unchanged. All-tombstone local source
has the same live initial semantics. For successful capture, original registered
request may replay ONLY against matching immutable lineage/registration evidence;
readStatus verifies durable exact interval. Reusing the same plan also compares every
original event ID/raw body with committed cohort. Replay never reads current source,
reseals, allocates ordinals or changes counters. Later Note creation/update/deletion
belongs to a future normal writer, not bootstrap recapture.

ReadStatus reads binding/outbox/receipts in ONE readonly bound transaction and derives
{event_count, accepted_count, complete, max_server_sequence} for the exact interval.
Sealed with no receipt is not accepted; accepted requires existing immutable matching
receipt; accepted-without-receipt or sealed-with-receipt is corrupt, not success.
Unrelated receipts are ignored; complete only when all exact members accepted.
Max is the maximum exact accepted server sequence (0 if none/empty), not pull cursor,
remote high-water or an unrelated receipt. It NEVER persists initial_max_server_sequence,
changes phase or advances ACK. Captured readiness remains false with explicit
bootstrap_completion_unavailable; completing/remote completion/ready are later slices.
Schema remains6/ten stores; no migration. v4/v5 upgrade validation continues to reject
upload capture rows because those historical versions had no capture producer.

### Validation and remaining scope

Focused capture25 + cohort-status6 =31 tests PASS; affected C21 local/migration/
lineage/durability/receipts/history/Metadata170 tests PASS; Legacy Note codec/golden/
intent/authority/protocol/compression/V2 encoder68 tests PASS. Real production-preview
Chromium111 scenarios PASS (native IDB/Web Locks/actual auth/keys/crypto, API0/page
errors0), including all-field frozen reader roundtrip, source/binding CAS, contiguous
allocation, empty capture after prior outbox, exact partial/all receipts, unrelated
receipt exclusion, immutable replay after source mutations, reload/full profile reopen,
rollback after queued outbox+allocator+binding writes, async unique-ordinal failure,
auth/key/session lifecycle and future-schema preservation. Old browser baseline cases
remain mandatory; inspections compare like ordering (ordinal vs primary UUID keys).
Typecheck/build and workflow/syntax/diff/pyc checks PASS; existing build warnings only.
Cloud explicitly runs new capture/status spec and local/projectBinding regressions,
plus the expanded hard-failing Chromium entry point. No soft failures/skips.
SQLite NOT EXPECTED; remote CI PENDING — NOT POLLED.

C21.1.11 LOCAL COMPLETE for Legacy Note cohort ONLY. No Metadata/Stage/Document/Map/
Content Note/Progress/Catalog/Game/Cover capture, upload_existing protected apply,
native candidate/self-echo reconciliation, complete-project claim, HTTP fallback/
automatic import, network/registry/upload/pull/ACK, completing/ready or active synthesis.
ACK/proven stay0 and initial max staysNULL. Backend/PostgreSQL/native/frozen semantics
and dependencies unchanged. Next bounded slice: captured→completing and remote bootstrap
completion boundary using exact receipt status, without granting ACK/ready/full-family sync.


## C21.1.12 native/backend invariant preflight

Accepted C21.1.11 c1edcbb7befaab1bfff995ae6ef7f61b53e7348b / Cloud38380013246,
all six jobs SUCCESS (owner supplied). Native markCompleting freezes maximum exact
initial receipt sequence, including0 for empty; native remote completion POST then
confirms remote active/high-water while phase stays completing. Ready separately
requires ACK>=max(remote_high_water,initial_max); this slice does NOT implement it.
Backend POST /api/v1/cloud/projects/{project_id}/bootstrap/complete requires exactly
bootstrap_id/device_id/initial_event_count/initial_max_server_sequence (no ordinal HI).
Bearer user supplies account ownership. Registered device + exact bootstrap/origin
required. Initializing uses project/device event stats count>=declared and max>=declared;
our client must prove EXACT cohort locally (server aggregate does not do this).
Active exact replay is idempotent only when frozen count/max identical; changed
lineage/proof conflicts. Response {project,current_cursor} includes exact six descriptor
fields, authoritative active + frozen count/max, origin identity. Cursor is account-wide,
can exceed cohort max; require >=prior high-water and >=initial max, never equality.
No wire response version exists; do not invent one. Empty requires count0 iff max0.
Existing cloudProjectsApi.completeBootstrap can be isolated from registry/upload/pull/
ACK/coordinator. A current authenticated request outside IDB and strict expected-old
response commit can retain completing/initializing on failure/lost response/crash and
retry exact proof after reopen. Existing completing row can represent proven remote
active + monotonic high-water without new phase/store/schema. Public generic registration
must NOT promote completing from arbitrary evidence DTO; only exact completion response
may do so. Freeze this contract before production transition changes.


### C21.1.12 implementation — LOCAL COMPLETE

Schema6/ten stores/record1 unchanged, no migration/manifest/new persisted proof format.
`session.completion.bind(auth, accountBindings, keys)` is an explicit bounded runtime;
no production editor or sync coordinator is switched over. This slice is Legacy Note
ONLY, not complete-project sync. C21.1.11 REMOTELY ACCEPTED, user Cloud38380013246
all six SUCCESS; official84.0%, C21 IN PROGRESS, C21.1.06 NOT LOCAL COMPLETE.

`markCompleting(scope, expectedBinding)` requires current normal-user/account/session/
key context and exact upload_existing/captured/initializing lineage. ONE strict
readwrite transaction over session identity/binding plus projectBindings/outbox/receipts
reconstructs the exact contiguous initial interval, validates every immutable member/
receipt, requires all accepted and derives maximum sequence. Only phase completing
and initial_max_server_sequence change together. Caller complete flags/max DTOs are
not accepted. Empty count0/HI0 requires no receipt and freezes native max0; nonempty
safe max>=count. Partial/missing/conflicting receipts, stale full binding/scope or
request failure abort without a half transition. Later unrelated events/receipts cannot
change count/HI/max. Replay from captured expected-old returns original initializing
completing ONLY when every expected field + derived max matches; completing expected
replay requires full exact row. Changed count/HI/max rejects, never normalized into
success. After authoritative active/high-water changes, callers read the current
completing row for subsequent replay (old expected row is stale).

Validation deliberately admits only prepared/registered/captured/completing upload
phases, with explicit phase invariants. Captured still initializing/maxNULL. Completing
requires safe frozen max (count0 iff max0), exact counters, initializing or active;
active high-water>=frozen max. Import captured/active/zero/maxNULL unchanged. Generic
confirmRegistration/pure transition refuses completing and cannot fabricate active
from caller evidence or change frozen cohort counters. Older v4/v5 migration validators
refuse both upload captured and completing (those versions had no producer).
Cohort status now accepts completing only when all durable receipts still reproduce
the frozen max; it cannot silently recompute a different completion proof.

`completeRemote(scope, expectedCompleting)` first re-reads full exact binding and
cohort proof in one readonly scoped transaction. HTTP occurs AFTER that transaction
ends. Existing cloudProjectsApi.completeBootstrap + auth.authorized send one POST:
bootstrap_id, device_id, initial_event_count, initial_max_server_sequence, project in
encoded path. No HI/body/manuscript contents, registry/upload/pull/ACK call, automatic
retry, token refresh loop, background poll or normal cycle. Existing client gains an
optional AbortSignal and16KiB successful-response bound; endpoint/body/backend semantics
unchanged. Fixed30s AbortController timeout; auth invalidation aborts request. Key/
session revocation before request or before response commit rejects current context.
No key bytes are needed/sent during HTTP. No server error/body is logged or persisted;
failures are bounded bootstrap_completion_failed/response_rejected/closed codes.

Response must contain EXACT {project,current_cursor} and exactly six project descriptor
fields: matching project/bootstrap/origin device, active, exact frozen count/max.
No version/account field exists in this backend contract; unknown/extra fields reject.
Authenticated Bearer user + scoped durable account mapping supply ownership. Cursor
must be safe, >=prior remote_high_water AND >=initial max; can be larger, not equal.
Successful2xx alone never activates. After response validation, a separate strict
readwrite transaction rechecks full expected-old completing row/current context and
ALL durable cohort receipts, then persists ONLY remote_state=active and remote_high_water
from authoritative response. Phase stays completing; count/HI/max never change. Exact
same concurrent target may replay; different concurrent cursor/row fails stale CAS,
never LWW/max-merging a stale response. No transaction is held across fetch/await.

HTTP/network/timeout/malformed/wrong-lineage/nonmonotone response or local commit quota/
abort leaves completing/initializing and original frozen proof. Reopen retries same
bootstrap/device/count/max. Backend active replay must return matching immutable proof;
changed already-completed metadata conflicts. If remote response was lost or local
active commit failed after server success, exact endpoint replay safely finishes later.
Already durably active plus full exact current expected row returns it without HTTP.
No new completion_sent/completed_remote phase or v7 is needed. This proves remote
bootstrap active, not account reconciliation or local application/ACK of initial Notes.

Readiness stays false: captured or completing/initializing →
bootstrap_completion_unavailable; completing/active → ack_proof_unavailable, required
cursor=max(remote high-water,frozen initial max). ACK/proven remain0. No markReady,
ready event, upload_existing Metadata apply, native candidate/self-echo/Cover material,
other-family capture or complete-project claim. Production HTTP/editor routes remain
unchanged except this explicitly called isolated completion operation.

Checks: completing22 + remote27 =49 new tests PASS; affected C21/API105 plus initial
capture31 =136 regression tests PASS. Shared scheduling-contract fixture was extracted
without altering the31 capture assertions; real storage/network proved in Chromium.
Production-preview Chromium119 scenarios PASS,15 intercepted completion POST requests,
0 unrelated API/sync requests,0 page errors. Exact paths/Bearer/body validated; seven
failure-project requests use identical frozen proof. Includes incomplete/partial/
conflicting receipts, post-capture900 excluded from frozen501, empty0, request-success
abort rollback, server failure/lost response/timeout/mismatched response, local active
commit quota then reload/idempotent server replay, logout/key/close before commit,
real second-tab exclusion while HTTP waits outside IDB, full disk-profile reopen,
no plaintext or ACK/ready. Timeout fixture accelerates only the existing30s timer;
production limit remains30s. Requests intercepted locally, no backend Internet needed.
Typecheck/build/workflow/syntax/diff/protected pyc PASS, existing build warnings only.
Cloud explicitly executes completing/remote spec, capture/status/lineage regressions
and expanded hard-failing Chromium. SQLite NOT EXPECTED; remote CI PENDING — NOT POLLED.
No skipped/softened gates; full/heavy/native/PostgreSQL suites not run.

Next bounded slice: account-wide remote reconciliation, retained inbound proof and
ACK/proven-prefix prerequisites before any separately authorized ready transition.
Do not infer full project synchronization from this Legacy Note-only remote bootstrap.


## C21.1.13 registry / ACK safety preflight

Accepted C21.1.12 cc9bfb567afdbccdc77ce4a8aab84cc204757930 / Cloud38386112458
all six jobs SUCCESS (owner supplied). Existing GET /api/v1/cloud/projects/bootstrap
returns ALL current-user project rows in one ordered SELECT/all(), no pagination/token.
Response projects + account current_cursor has no snapshot generation/ETag; cursor is
an observed account high-water, NOT an atomic generation for registry membership.
Validate entire response and all identities/duplicates before one expected-old account
commit. Never infer durable complete-registry proof merely from per-binding high-water.
Known prepared absent: retain/register-required; known registered/captured/completing/
import absent: fail entire response, no inferred deletion/rebinding. Unknown remote rows
remain unbound blockers, never automatic import/local source. Imported installation
uses local device while server origin device may be peer; bootstrap must still match.
Upload-existing origin must match local device. Both projects share the account cursor;
local initial cohort count/HI/max are NEVER copied between project bindings.

Native ACK is contiguous_applied_ack_prefix from current ACK up to pull cursor, requires
each sequence's exact native family applied ledger/outcome, or properly preserved
conflict proof; gaps/unresolved/conflicts/unsupported stop. Native candidate is recomputed,
not a SQLite stored proven_prefix field. Commit rechecks scope, expected-old ACK and
prefix, requires target<=pull. Backend ACK is monotone/idempotent204 and rejects target
beyond account server cursor; cannot verify client decryption/application itself. Browser
has received ciphertext and Metadata-only authority proof/heads, no complete native
family applied/projection/conflict ledger coverage, especially Legacy Note self-echo.
Thus registry/high-water/initial receipts/pull/Metadata marker NEVER authorize positive
browser proven/ACK advancement in this slice. Keep reserved ACK/proven0, no ACK HTTP.
Read-only inventory may validate current records and diagnose missing proof, not invent
native applied outcomes. Registry full-snapshot token stays runtime-only/current-context;
per-binding state/high-water can persist in v6, but reload requires fresh reconciliation.
Ready remains false. ACK positive progression STOP: missing protected pull/apply/family
proof representation; no v7/store/marker or frozen semantic workaround.

## C21.1.13 bounded registry / ACK prerequisite result

**PARTIAL LOCAL COMPLETE / positive ACK BLOCKED; remote CI PENDING — NOT POLLED.**
C21.1.12 remotely accepted: cc9bfb567afdbccdc77ce4a8aab84cc204757930,
Cloud38386112458 SUCCESS, all six required jobs SUCCESS, owner supplied.

`session.registry.bind(auth,bindings,keys).reconcile(scope)` explicitly calls the
existing GET /api/v1/cloud/projects/bootstrap outside IndexedDB. Current normal-user
context, authoritative binding, key lease, installation device and session guard apply
before request and commit. Existing client adds optional AbortSignal, 2MiB response cap;
operation has30s timeout and logout abort. Entire exact projects/current_cursor response
is validated before TX: bounded4096 entries, safe cursor/count/max, native opaque
project IDs, canonical bootstrap/origin UUIDs, duplicate IDs/bootstrap IDs, legacy null
fields and initializing/active count/max relationships. No page loop: endpoint is
unpaginated; extra pagination fields fail closed. Bounds reject rather than truncate.
Source: backend/app/cloud/projects_router.py, services.py list_bootstrap, repositories.py
CloudProjectRepository.list. One ordered SELECT produces all current-user projects;
account cursor is observed separately, without atomic registry generation or ETag.

One strict transaction uses full expected-old known account binding set, identity/device
scope and current lifecycle; completing rows rejoin exact cohort/outbox/receipt proof.
A local binding inserted while HTTP awaits invalidates the whole response commit.
Only projectBindings state/high-water changes; no inbox/cursor/receipt/source rewrite.
Remote active may confirm exact completing count/max; retained frozen count/HI/max
are immutable. Prepared matching initializing may recover registered evidence only.
Captured/registered upload active cannot synthesize missing local completion proof.
Remote bootstrap/origin/state regression or prior high-water regression rejects ALL.
Known bound absence rejects without deletion; absent prepared remains unregistered.
Unknown valid remote/legacy projects are explicit whole-account blockers, never imported.
Upload origin must equal local device; imported origin may be another device, preserving
local installation device and bootstrap. Both known projects receive account cursor,
without copying another project's initial count/HI/max or altering shared cursor.

Persisted registry evidence is ONLY existing per-binding remote_state/high-water in
schema6. No durable complete-account registry snapshot proof is claimed. Private weak
runtime token binds exact complete local set/current auth/key/session; unknown/unregistered
rows block its use. Forged/cross-runtime/stale token cannot authorize prerequisites.
Profile reopen retains binding projection but expires token; explicit refetch required.
No new schema/store/generation marker. Account membership snapshot is never inferred
from a row's high-water, and remote cursor is never advertised as registry generation.

`registry.ackPrerequisites(scope,projectId,token?)` takes one readonly scoped inventory
of bindings/cursor/inbox/Metadata heads. It validates immutable wire record structure,
sequence/event uniqueness, pull bounds, and exact Metadata proof/head/imported bootstrap
joins; detects received-only, Metadata-authority-only, missing sequence1 and unsupported
families. This is structural inventory, NOT fresh AEAD verification, a generic conflict
classifier or native protected-apply/projection ledger. Encrypted resolution cannot be
silently classified as conflict-safe. Missing/unsupported proof keeps candidate0 even
with contiguous received rows or Metadata-only applied rows. Corrupt retained joins
fail closed. No positive candidate and no invented applied/conflict status.

Native `note_sync.rs` contiguous_applied_ack_prefix requires each next sequence through
pull to have exact family-specific safe apply/outcome or preserved conflict proof;
commit rechecks expected-old ACK and recomputed prefix. Native has no separate stored
proven_prefix column. Browser reserved `0<=ack<=proven<=pull` holds with ACK/proven0.
Backend ACK (/api/v1/sync/ack and existing encrypted V2/V3 routes) is monotone/idempotent
204, target bounded by server account sequence; it cannot prove local client apply.
No browser ACK target/request/response/retry implementation is safe yet. Initial own
receipts, remote active, registry and pull cursor cannot substitute for missing exact
Legacy Note self-echo/native decision/conflict and all-family ledger coverage.

Row-only readiness now registry_reconciliation_required for active import/completing.
Current exact account token yields bootstrap_completion_unavailable, pull_required,
protected_apply_required, unsupported_family_proof or ack_proof_unavailable as supported.
Always ready:false/ack_eligible:false; no markReady/phase ready or normal loop. Inventory
cannot claim all events cryptographically verified/applied or complete-project sync.

Tests: registry29, ACK prerequisites18, completion49, affected C21/API156 incl capture31:
252 tests/15 files PASS. Chromium128 PASS: registry GET16, preceding completion POST15,
ACK0, unrelatedAPI0, page errors0. Actual installed Chromium+production preview uses
isolated intercepted HTTP, normal auth/key/Sodium, native strict IDB/Web Locks and disk
profile. Covers two projects/peer origin, exact retry, whole-vector malformed/duplicate/
absence/bootstrap/cursor rollback, local-set CAS race, request-success abort/quota,
key/logout/close, competing writer and retained projection/refetch after profile reopen.
Typecheck/build/workflow/syntax/diff/pyc PASS; existing build warnings only. Cloud runs
new specs explicitly plus existing completion/cursor/inbox and hard-failing Chromium.
SQLite NOT EXPECTED; no skips; heavy/native/backend suites and remote CI not run.
Official84.0%, C21 IN PROGRESS, .06 NOT LOCAL COMPLETE; Cover/self-echo/full-project
capture/apply remain bounded future prerequisites. No production UI/help changes.

## C21.1.14 retained Legacy Note proof substrate

**PARTIAL LOCAL COMPLETE / conflict preservation BLOCKED; remote CI PENDING — NOT POLLED.**
C21.1.13 REMOTELY ACCEPTED PARTIAL at f99bbb6beb6e2da84c84ee4ebadafc273e04dd28,
Cloud38392639737 SUCCESS, all six required jobs SUCCESS (owner supplied). Registry
accepted, positive ACK correctly blocked. Native outcome table and precise stops:
[family audit](../cloud/C21_PROTECTED_APPLY_FAMILY_AUDIT.md).

Dormant `session.notes.bind(auth,bindings,keys).prepare(scope,serverSequence)` reads
exact retained inbox, same-account bindings/outbox/receipts/cursor. Target must already
be retained with sequence<=pull. No caller plaintext/DTO/proof constructor, network or
new registry request. Active import captured and upload completing/active are eligible;
upload complete frozen cohort receipts rechecked at prepare AND commit. Native admitted
project/account is necessary; fresh registry token is not a native apply prerequisite.
Canonical encrypted local Project must already exist, never auto-created from ciphertext.
Only ordinary Note upsert/delete, frozen Legacy codec1, project-owned HTML with null
Stage/map/node are supported. Other families/Content/Resolution/unsupported variants
remain received/unproven; malformed crypto/metadata fail closed with bounded codes.

Decrypt/decode/semantic transition and encryption occur outside live IDB. Existing
object crypto1/AAD1 and frozen Note canonical codec; SHA256 follows Metadata's existing
immutable protocol+descriptor+object identity pattern. Temporary plaintext byte buffers,
nonce/cipher/key lease copies are cleared. JSON strings cannot be wiped in JS; decrypted
DTO is temporary, removed from private plan after protected source preparation and
never persisted or returned as an apply input. No changes to frozen crypto/frame/codec.

New inbox record3/state note_proven with note_proof (separate from applied_proof) has
strict exact fields: owner_kind legacy_note; outcome applied/self_echo_applied; account,
bootstrap, protocol, exact reference/header/mutation, immutable wire_digest/outcome_digest, peer resulting
source_revision/local_note_digest or self-echo nulls. outcome_digest is SHA256 of the
complete strict proof body excluding that digest field; detects record corruption, not
an independent authenticity/ACK certificate. Replays also authenticate frozen plaintext
and wire identity. Original wire_item remains byte-for-
byte. Header carries cloud semantic revision/parent; digest of encrypted resulting local
Note binds clean-source continuation, not a plaintext projection. No conflict_proven,
rejected-safe or orphan-final variants. received1 and Metadata-applied2 remain unchanged.
No schema/index/store change or auto-upgrade of existing inbox. v5 migration rejects
future Note3 rows rather than synthesizing them; v6 validators/readers accept explicit
new runtime outcomes. Reopen preserves encrypted records; no repairs or fabricated proofs.

Peer head combines exact validated Note outcomes and ordinary sealed/accepted own
outbox heads; ambiguous equal-revision heads block. Create requires no cloud head and
no existing local member; update/delete requires exact head revision+1 and direct parent.
Retained Note history proofs are reauthenticated against their frozen decoded header,
mutation and immutable wire digest. Peer-child of a proven peer-applied head requires
current encrypted Note equal the parent's resulting local digest; any intervening local
Note mutation blocks. Unrelated project edits invalidate an old source plan but a fresh
snapshot may retry. Own-head peer children are deferred: Web lacks captured local-source/
unsealed mutation-generation proof, so an old self-echo cannot falsely certify current
local authority as clean. No fallback based on timestamps or cloud max revision.

Private verified capability lets localAuthority prepare only this exact remote Note;
there is no public raw putLocalNote DTO API. It reseals Project complete membership and
changed Note with source_revision+1; native local payload revision is0, matching
note_sync.rs note_payload_from_record, distinct from cloud revision and Web source token.
Native delete is logical absence; Web retains encrypted minimal routing tombstone with
local revision0 and authenticated membership. Future clean native upsert can resurrect
that same identity. Cross-project Note identity collision aborts both authority/proof.

`commit(plan)` schedules ONE strict transaction over inbox/projectBindings/outbox/
receipts/cursors/localProjects/localNotes, plus existing identity/account scope guards.
Full expected-old retained inventory/lineage/outbox/receipt/cursor CAS, exact complete
upload cohort, private source token and identity index are rechecked before writes.
Encrypted local authority and Note proof commit only on transaction complete; quota,
request-success abort, key/auth/session invalidation or source race rolls back ALL.
No cursor or bootstrap counter/phase writes. Exact same-plan committed replay returns
already_applied without source/proof rewrite. Fresh sequence replay reauthenticates proof
and returns already_applied even after later local state changes; does not roll back
newer source or increment revisions. Changed wire/header/bootstrap/receipt fails closed.

Pure self_echo_applied needs exact retained own immutable accepted outbox+receipt:
account/device/event/project/Note/protocol/sequence/descriptor/cipher identity, never just
source-device match. Receipt required, not synthesized from incoming echo. Complete
initial cohort proof is preserved. It records causal outcome, without reapplying Note or
changing source_revision, including old initial echo after a newer local mutation.
Replay still checks accepted receipt and immutable original wire. Later source change
between prepare/commit invalidates plan; fresh preparation proves echo without rewind.

Conflict STOP: native conflict_preserved uses independent immutable local+remote
versions, group/common parent/generation/full >=2 tips and retained causal/resolution
material. Mutable current canonical Note plus inbound ciphertext/outbox receipts do not
preserve an unsealed historical local candidate across later edits. No final conflict
proof/store is created. Local-dirty/head-sibling/unsupported resolution cases remain
unproven; rejected is blocking by native ACK CASE, orphan retryable after parent/dependency
arrives. Neither is an ACK-safe final outcome. Incoming ciphertext and current local
version remain retained, but are not advertised as a durable native conflict repository.

ACK inventory adds distinct note_received_only/note_applied/note_self_echo counts with exact binding/proof
structural validation; received-only and unsupported families remain blockers. Inventory
is not a fresh AEAD authentication pass or positive contiguous cross-family computation.
Even all-Note proven fixtures retain proven_prefix0/ack_cursor0/ack_eligible:false/ready:false.
No ACK network/target, ready phase, orchestrator, other-family apply/capture or UI changes.

Checks: Note31 (self-echo8 included), proof validation19, ACK18, affectedC21278:346
unique tests/17 files PASS across final focused selections. Chromium135 PASS, protected
apply requests0; existing registryGET16/completionPOST15/ACK0/unrelatedAPI0/page errors0.
Includes actual retained crypto, encrypted source, native strict IDB rollback, source
race/retry, peer causal create/update/delete/resurrection, local-dirty conflict blocker,
bad receipt/exact old self-echo after newer mutation, replay, renderer/disk-profile reopen
and received1/Metadata2/Note3 coexistence. Typecheck/build/workflow/syntax/diff/pyc PASS,
existing chunk/dynamic-import warnings only. Explicit mandatory Cloud new specs plus
localAuthority/sync/ACK/bootstrap/registry regressions and Chromium; SQLite NOT EXPECTED.
No skips, dependencies or backend/PG/native/frozen semantics changes; no remote CI polling.
Official84.0%, C21 IN PROGRESS, C21.1.06 NOT LOCAL COMPLETE; complete-project/Cover/
other families/conflict/resolution and positive cross-family ACK remain future slices.

## C21.1.15 durable candidate/conflict history

**PARTIAL LOCAL COMPLETE / local unsealed history and missing old capture anchors BLOCKED;
remote CI PENDING — NOT POLLED.** C21.1.14 accepted partial at
65e4fe4cc712162e1436970f9f6a62afbe9416d8, Cloud38402330568 SUCCESS, all six required
jobs SUCCESS (owner supplied). Accepted clean apply/self-echo and correct conflict stop.
Native structure/generation/group/ACK/Resolution mapping precedes implementation:
[family audit](../cloud/C21_PROTECTED_APPLY_FAMILY_AUDIT.md).

Structural necessity authorizes IDB7: ONE new legacyNoteHistory store, compound key
[account_id,project_id,note_id,record_kind,record_id], unique event index [account_id,event_id]
only for candidate records. Tagged exact allowlists keep immutable candidates separate
from mutable CAS heads/groups; not a generic other-family store. v6 exact ten-store
schema/data structural validation precedes upgrade; all existing bytes stay unchanged.
Includes transport/receipt/cursor invariants, scopes, lineage, exact Metadata proof/head
joins, received1/Metadata2/Note3, encrypted local record envelopes and source ownership/
revision relationships. No AMK or async crypto in versionchange; semantic AEAD checked
by current authorized runtimes. No plaintext conversion, synthetic candidate/group/head
or inferred proof. New store empty. Corrupt/quota/abort leaves v6 valid; v1–v5 direct
upgrade paths preserved, repeat v7 opens stable, future8 refuses downgrade.

Candidate record1: account/installation/project/Note/bootstrap, event/source device,
protocol, exact frozen Legacy header(parent/cloud revision/operation), origin,
mutation_generation1 for fixed initial capture or null for peer (never revision/source/
server sequence), immutable encrypted wire_item and SHA256 wire/record digests. New
capture/peer apply may retain exact encrypted local projection anchor + its digest;
old peer outcome may provide its original projection digest, without inventing an anchor.
The encrypted event independently reconstructs native cloud-visible version/local payload
revision0. Current normal auth/account/key/session leases authenticate retained ciphertext,
strict header/codec/routing, full source-anchor payload/ownership where present and exact
integrity digests; temporary byte/nonce/cipher/key buffers cleared. SHA detects corruption,
not independent author authenticity; no new crypto/AAD/frame/compression primitive.

Initial capture creates candidate + initial head in SAME strict source-CAS/outbox/
allocator/captured counters TX, so server receipt is not a candidate-creation boundary.
Source anchor is the actual verified encrypted historical source read before sealing;
never read current Note later to fabricate it. Native initial new event generation1 is
explicit constant from initial prepare intent contract; not generation=revision. Existing
accepted/sealed cohort can be explicitly backfilled from exact initial interval, immutable
body/receipt proof and frozen AEAD/codec. No current local source read in backfill.
Historical event projection reconstructs exactly; missing original local anchor stays
missing. Initial replay never reseals/rewrites candidate. Generic transport.enqueue is
not a reviewed post-capture Note writer and cannot invent generation/projection history.

Peer apply atomically stores immutable candidate, projected source anchor, compact head
and Note3 proof with local authority. Own-head continuation requires correct historical
sealed parent/project/Note/bootstrap/header, accepted receipt/wire and exact source anchor;
source change fails closed, historical parent remains recoverable. Old initial backfill
without source anchor reports candidate_history_unavailable for clean continuation.
Old explicitly used Note3 outcomes may reconstruct peer event history/known original
projection digest from their exact retained proof, never current content. Source revision
and native local Note revision remain distinct from cloud revision and mutation generation.

Head record1 has linear_head_event_id and COMPLETE sorted causal frontier tip_event_ids,
plus independent Web head_revision for expected-old CAS, not native mutation/conflict
generation. Every tip backed by immutable candidate; direct parent/revision ownership
validated, duplicates/dangling parents rejected. Consumed ancestor leaves frontier; an
unresolved unrelated branch stays. Native active linear child may advance while existing
conflict group retains its original Resolution tip set; no branch is silently dropped.
Head replacement and all candidate/group/inbox/source effects occur through ONE strict
full expected-old inventory/history/source transaction; crypto/network outside IDB.

Conflict group record1 uses native persisted random UUIDv4, exact common parent,
tip_revision, conflict_generation starting1, open lifecycle and complete sorted member/
tip set. Native remote_applied current head and incoming sibling versions are independently
recoverable encrypted candidates; member stores native version_id (applied:/remote:),
source, exact server sequence and introduction generation. Canonical local Note remains
unchanged. First group requires clean exact prior projected source and applied evidence;
existing compatible group can preserve new sibling even after later local edit because
old versions are independent. Each distinct sibling adds one immutable version/tip and
increments current group generation once; exact replay changes nothing. Native permits
ONE open group per Note: a different fork cannot become a second safe group while the
first remains unresolved. Descendant/current frontier and frozen group tips remain
separate, preserving future Resolution context. No resolved/decision shortcut.

Native-qualified applied update vs remote delete, applied delete vs remote update and
concurrent deletes preserve each encrypted tombstone/version and exact identity. Local
unsealed edit/delete is a DIFFERENT source: Native needs actual unsealed outbox event,
reserved ordinal, intent mutation_generation/coalescing and independent snapshot.
Those producers/lifecycle/allocator records are absent in current Web. Current mutable
localNotes + source_revision cannot replace them; stop that portion before fake local
candidate/generation/publication evidence. No broad outbox lifecycle redesign in this
bounded store slice. Dirty local source, genesis conflict, unsupported Resolution,
rejected and orphan remain received/unproven. Orphan can retry after exact dependency.

New inbox4/state note_conflict_preserved/note_conflict_proof is an explicit separate
variant. Strict account/bootstrap/protocol/reference/header/mutation/wire/outcome digests,
group identity and preservation generation bind exact retained event. Original wire_item
unchanged. Runtime validates current complete group/version/sequence/outcome joins;
received1, Metadata-applied2 and Note-proven3 remain byte-compatible. v6 migration never
accepts a fabricated future4 or creates it from received rows. Group proof can be
individually native ACK-safe with exact preserved versions and >=2 full tips; not aggregate
prefix or an ACK request. Readonly inventory adds note_conflict_preserved and verifies
complete joins, while ACK/proven0/ack_eligible:false/ready:false are mandatory even for
all-proven Note fixtures. No phase ready, registry request from apply, orchestrator,
Resolution send/UI, other-family capture/apply or complete-project claim.

Future frozen Resolution v2 needs exact group ID/current conflict generation/full tip IDs,
common parent, per-tip header/revision/operation/source/server sequence and material,
resolution revision=max tips+1, and current local publication/generation/decision proof.
All supported group fields/material retained; local-unsealed publication/decision and
Resolution runtime remain absent, rather than inventing consent or sealed dependencies.

Local checks: history20, conflict/own-head21, v6 migration13, Legacy Note31/proof19,
ACK18, affectedC21278 =400 unique tests across focused final selections PASS. Chromium145
PASS; v6 ten stores exact, received1/Metadata2/Note3, corrupt/quota/abort upgrade, new
store empty, old backfill/new capture anchor, immutable material, own child, independent
update/delete conflict versions, generation/full tips/replay/later local edit, auth/key
revoke and full transaction abort/reload/disk-profile reopen. Existing completion16
(one additional bounded fixture)/registry16; candidate/conflict/apply requests0, ACK0,
unrelatedAPI0/page errors0. Typecheck/build/workflow/syntax/diff/protected pyc PASS;
existing build warnings only. Cloud new history/conflict/migration specs explicitly
mandatory plus affected C21 and hard-failing Chromium. SQLite NOT EXPECTED; no skips,
new dependencies/backend/PG/native/frozen contract edits; no Actions polling.
Official84.0%, C21 IN PROGRESS, .06 NOT LOCAL COMPLETE. Next proposed bound: local
unsealed candidate generation/ordinal/writer bridge, then separately authorized
Resolution and cross-family ACK; current unsupported family/Cover gaps unchanged.


## C21.1.16 local unsealed writer and immutable seal bridge

C21.1.15 owner acceptance: a386161d07b2918a30af4c2dae7328068adad914,
Cloud38426555539 SUCCESS/all six jobs SUCCESS; REMOTELY ACCEPTED PARTIAL.
C21.1.16 LOCAL COMPLETE / REMOTE CI PENDING — NOT POLLED. Official84.0%,
C21 IN PROGRESS, .06 NOT LOCAL COMPLETE. Native state table and references live in
C21_PROTECTED_APPLY_FAMILY_AUDIT; audited before production.

Schema8 adds only legacyNoteIntents, key [account_id,event_id], unique Note index
[account_id,project_id,note_id] and ordinal index [account_id,device_id,local_ordinal].
Version7 validates all eleven exact old stores, received1/Metadata2/Note3/conflict4,
source/proof/lineage/history/frontier/group joins and immutable wire references;
no keys/decryption/repair/inference in versionchange. New store empty. Failed/quota/
corrupt upgrade retains original v7; current8 reopens; future9 refuses downgrade.

Dormant `session.noteIntents.bind(normalAuth,accountBinding,keys).local` reuses existing
canonical BrowserLocalAuthority createNote/updateNote/tombstoneNote mutation and source
CAS. It does not route editor calls or activate background syncing. Normal local-only
runtime remains available; explicit producer methods are the reviewed atomic boundary.
Eligible lineage: active import_remote/captured, or active upload_existing/completing
with exact accepted initial cohort. Native binding helper alone allows more states;
Web deliberately requires accepted bootstrap completion under existing no-ready model.
Prepared/registered/upload-captured/incomplete/missing/stale/foreign scope fail whole
producer mutation. Supported Note HTML/project/null Stage/null map/node only;
unsupported/invalid/oversized source rolls back canonical mutation and ordinal.

SAME strict transaction: encrypted canonical project/Note, source_revision+1, intent,
existing next_local_ordinal reservation. New UUIDv4/cloud revision1/null parent only
when no actual cloud head; otherwise highest native combined sealed/accepted outbox
and applied Note3 head +1/exact parent, equal different IDs fail. History candidate
AEAD verified; preserved incoming tip cannot impersonate actual applied/outbox head.
Unsealed is NOT cloud-visible frontier. Account/device ordinal spans projects and
Notes; initial specialized cohort producer now includes unsealed reservations when
validating allocator without changing count/HI/capture semantics. Aborts consume none.

Coalescing: SAME UUID, ordinal, cloud revision, parent; mutation_generation increments
for every new snapshot and resets pending/attempts/error. Create→update, update→update,
update→delete and create→delete follow native; create→delete becomes delete on same
revision1 event, not removal. Native payload revision/source revision remain distinct.
Intent retains encrypted original canonical source anchor plus encrypted identity
wrapper using existing Note object tuple/AAD. Identity authenticates complete event/
lineage/parent/cloud revision/ordinal/mutation generation and exact encrypted anchor
hash. Neither plaintext snapshot_json nor user content is persisted. No new crypto.

Explicit list/prepareSeal/commitSeal/seal methods: current account key opens/verifies
anchor and identity outside IDB, frozen createNoteSyncPlaintext/sealNoteSyncEvent and
V2 encoding produce normal immutable Note bytes. Seal generation-CAS stores outbox at
reserved ordinal, local_sealed immutable candidate/exact source-at-seal anchor/native
generation, complete frontier/head and removes intent in ONE TX. Metadata failure
updates at same generation do not invalidate valid prepared crypto. Newer generation
returns stale_generation with no changes. Same prepared encrypted bytes replay returns
already_sealed; differently encrypted same event fails after first commit. No held-open
crypto transaction, crash window or partial sealed state. Lineage/history/inbound/
outbox/receipt CAS and auth/key/session invalidation enforce fail-closed commit.

Bounded native error codes: key/size/dependency/unsupported blocked; runtime retryable;
invalid payload/context/metadata/envelope invariant_error. Absent current key records
key_unavailable for exact generation; revoked prepared key/auth cannot commit. New
mutation resets older failure; invariant cannot be retried without new generation.
Explicit blocked retry only; next_attempt_at null, no invented scheduler/backoff/loop.
Corrupt snapshots/metadata fail closed without arbitrary exception strings or repair.

Post-seal edit creates new event/ordinal/gen1 with exact combined causal parent;
previous candidate immutable. Open native conflict group allows ordinary local branch
and later coalescing, while group versions/generation/tips stay frozen and complete
frontier retains all unrelated tips. No Resolution decision/resolve/send. Accepted
receipts and retained own echo recognize new sealed events; protected peer child can
use exact source anchor through C21.1.15. New source-at-seal history available; old
unrecoverable anchors remain unavailable, never reconstructed from mutable current Note.
Local-unsealed inbound conflict capture remains a separate subsequent apply slice.

Checks: producer17/coalescing5/seal22/integration6/migration13 =63 new PASS; previous
400 affected C21 PASS =463 unique final focused selections. Chromium157 PASS: v7
migration exact11, zero inferred intents, corruption/quota/abort, dormant create/update/
delete/coalescing, encrypted identity/snapshot, generation race, source/seal rollback,
logout/key lock, before/after seal renderer and disk-profile reopen, immutable anchor,
post-seal next event, self-echo/peer child/open conflict branch. Existing acceptance
registry16/completion16, total32 fixture API requests; producer/new sync/apply/ACK0,
unrelatedAPI0/page errors0. Typecheck/build/workflow/syntax/diff/pyc PASS; existing
build warnings only. Five specs explicitly mandatory in Cloud plus all affected C21
and hard-failing Chromium; SQLite NOT EXPECTED. No skips, dependencies/backend/PG/
native/frozen wire/codec/crypto/receipt changes, ACK/proven prefix remains0,
ack_eligible:false/ready:false. No other-family/ready/complete-project claim or CI polling.


## C21.1.17 retained conflict against exact local unsealed generation

Owner accepted C21.1.16 `92a66776c0b5d30295a9533ad561e89f6a5e5193`, Cloud38440249775
SUCCESS/all six jobs SUCCESS; REMOTELY ACCEPTED. C21.1.17 LOCAL COMPLETE / REMOTE CI
PENDING — NOT POLLED. Official84.0%, C21 IN PROGRESS, .06 NOT LOCAL COMPLETE.
Native source/transition/ACK/Resolution table audited BEFORE implementation in family audit.

Schema remains8. No new store/index/migration. legacyNoteHistory gains strict local_version
record1 tag, scoped account/device/project/Note/bootstrap, version_id/record_id
local:account:event:mutation_generation, frozen header, complete original encrypted
BrowserNoteIntent and SHA integrity digest, local_outbox_lifecycle:unsealed. Original
intent AEAD binds event/parent/cloud revision/ordinal/generation/anchor. No top-level
event_id, so existing unique candidate event index remains cloud-candidate-only; later
same-event sealed candidate may coexist without rewriting the frozen local version.
Canonical encrypted Note source anchor is independently recoverable from frozen intent,
not later localNotes. No plaintext snapshot_json/content and no synthetic sealed wire.
Guarded withDecryptedLocalVersion authenticates record/intent/snapshot under current lease.

New peer preservation requires current supported local intent, same durable known non-null
parent/revision>=2, different event ID, original visible canonical source EXACT snapshot
(for local delete, accepted encrypted tombstone equivalent to native absent Note). Parent
history authenticated; no arbitrary server sequence/Note revision inference. New group
UUIDv4/gen1 with local_unsealed member source, null server_sequence, exact local generation
and generation-specific version ID; remote member/candidate has actual retained sequence/
wire/parent/operation/authenticated material. Current canonical Note and project source
revision remain unchanged; live intent retained untouched. Unsealed version never enters
cloud-visible candidate frontier; group full tips include local event plus remote siblings.
Existing linear applied/sealed head stays intact, unrelated candidate tips retained.

Compatible existing group reuses ID/common parent and frozen original local version;
adds one distinct remote tip and increments conflict generation once, independently of
live intent mutation_generation. Incompatible group cannot merge/create a second group.
Genesis/create→update revision1 collision, wrong parent/revision/lineage/scope, unsupported
variants, mismatched visible source and purported peer child of unsealed event remain
unproven. Native unsealed branch blocks clean apply until eligible preservation; no
manufactured conflict or overwrite. Existing ordinary applied/self-echo and sealed-history
conflicts retain accepted behavior.

Crypto/decode outside IDB. Private opaque prepare binds original received wire, frozen
intent event/gen/snapshot/AEAD identity, source token and full history/head/group inventory.
ONE strict TX CAS checks exact live intent inventory and lineage/source/cursor/wire/history;
atomically stores local version, peer candidate, group/tips/head and inbox4 conflict proof.
No intent/source/outbox/receipt/cursor writes. Generation N→N+1, stale head/source, logout/
key revocation and quota/abort leave no partial proof. Fresh retry freezes new generation.
Exact replay after later edits/deletes/seal retains original frozen generation and outcome,
no duplicates/group increment/current content rollback. Changed wire/digest/scope fails.

Native intent remains unsealed and sealable; no automatic seal/reparent/block/deletion.
Later mutation coalesces same event/ordinal/parent/cloud revision and increments live
mutation_generation. Frozen local version stays immutable. Later sealing current generation
uses accepted C21.1.16 path, preserving local_version/group; adding normal sealed candidate
and complete frontier independently. Different sealed generation does NOT prove publication
of original frozen conflict snapshot. Update/delete, delete/update and delete/delete retain
tombstone identities and earlier historical parent content. Renderer/disk reopen persists
all snapshots, proof, intent and tips.

Strict conflict proof2 extends only existing inbox4 proof payload: local_version_id,
local_mutation_generation and local_version_digest bind exact immutable branch plus existing
peer wire/header/reference/group/generation. Old conflict proof1 byte-compatible; no applied
projection shortcut. Runtime verifies every local/remote member/outcome/sequence/digest.
Readonly ACK inventory authenticates frozen local record/intent/snapshot outside transaction,
then compares exact verified history and complete group joins in final readonly transaction.
Missing/corrupt/changed local version or proof never yields safe count. Qualified conflicts
individually native ACK-safe; no contiguous aggregation, ACK request, cursor advance or ready.
Persisted proven_prefix0/ack_cursor0/ack_eligible:false/ready:false remain mandatory.

Resolution v2 future prerequisites retain group/current conflict generation/full tip IDs,
common parent, exact per-version event/revision/operation/source/sequence/local generation/
independent material. Local ordinal retained too. Decision and publication/receipt proof
remain separate future work; later coalesced/sealed snapshot cannot substitute older frozen
snapshot. Ordinary native-unqualified/genesis/rejected/orphan and old unavailable history
remain blockers. This fills reviewed Legacy local-unsealed qualified conflict gap and permits
NEXT bounded ACK aggregation AUDIT; other-family/Cover/Metadata authority gaps unchanged.
No Resolution UI/event/decision/network or broad editor routing.

Checks:58 new (semantics24/races12/proof22) + prior463 =521 unique PASS across final selections.
Curated28 files512 PASS followed by nine extra focused negatives; final three specs58 PASS.
Chromium165 PASS including real N3→N4 stale race/safe retry, TX abort/key/logout, independent
version reads/current canonical state, later update→delete/third sibling/generation/later
seal, pre-delete parent content and all three delete combinations, renderer and disk-profile
reopen. Existing registry16/completion16 acceptance requests only; new conflict/apply/ACK0,
unrelatedAPI0/page errors0. Typecheck/build/workflow/syntax/diff/pyc PASS; existing build
warnings only. Three new specs explicit Cloud gates plus producer/seal/history/apply/ACK/
migration regressions and hard-failing Chromium. SQLite NOT EXPECTED, no skips/dependencies/
backend/PG/native/frozen Note/crypto/receipt/Resolution/Metadata apply changes. No CI polling.


## C21.1.18 account-wide contiguous proven prefix / ACK transport STOP

Owner accepted C21.1.17 `75599e9809a7d3be5facc0e5abc46e845e5c51cd`, Cloud38451825537
SUCCESS/all six jobs SUCCESS; REMOTELY ACCEPTED. C21.1.18 PARTIAL LOCAL COMPLETE:
positive prefix complete, ACK transport blocked by current writer-mode/reader-registration
prerequisites. Official84.0%, C21 IN PROGRESS, .06 NOT LOCAL COMPLETE. Exact Native/backend
ACK/outcome audit before production in protected-family audit; no roadmap points.

Schema8 unchanged, no store/index/migration. Cursor record1 same fields; numeric bounded
0<=ack_cursor<=proven_prefix<=pull_cursor and positive safe next_local_ordinal. Current v8
reads preserve positive state, no inferred advancement/full crypto during open. Historical
v1–v7 migration validators still reject positive old counters (no repair/synthesis). Normal
pull/outbox/receipt writers preserve independent prefix/ACK fields; readCheckpoint returns
actual values. This slice writes ONLY positive proven_prefix; no ACK writer/network.

Dormant session.proven.bind(...) calculate/prepare/result/commit/advance requires normal
current auth/authoritative account binding/durable identity/device/key/session. Pure structural
calculation independently tested before commit layer. Exact account-wide inbox sequence
sort/duplicate event+sequence validation, never highest Note sequence. Note3 applied and
exact replay count through ORIGINAL durable proof; self_echo needs exact outbox/immutable
receipt/sequence/wire. Inbox4 proof1 preserved applied conflict and proof2 local-unsealed
conflict require complete group/members/versions/common parent/generation/tips and exact
frozen local ID/generation/digest. Every Note candidate/header/protocol/source/wire matches
original outcome; active bootstrap and upload/completing initial cohort joined where needed.

Current-lease authentication OUTSIDE IDB: immutable candidate/snapshot AEAD, frozen local
record/intent/generation, retained Note plaintext/header/eligibility, wire and outcome digests.
Missing/corrupt/foreign required evidence fails closed. Full historical proven range is
revalidated on explicit prepare, so old unsupported/missing/corrupt rows cannot weaken a
stored positive prefix. Crypto is never held in a write transaction. Pure calculator alone
cannot persist authority; only opaque private verified plan can enter commit.

Walk1..pull, retain previous monotonic proven prefix, stop at FIRST unqualified or absent
expected sequence; subsequent safe Notes do not jump barrier. Received-only Note including
orphan/rejected/ordinary conflict blocks; Metadata-applied/ownerHeads authority is NOT a
native general ACK ledger and blocks; Stage/Document/Map/ContentNote/Progress/Catalog/
ProjectGame/AccountGame/Cover/others block without protected apply invention. Result has
current/candidate prefix/pull/first blocking sequence/code/family/counts. Exact scalar
invariants and impossible historical prefix detect corruption. Later events never rewritten.

Strict ONE prefix write TX re-reads exact inbox/outbox/receipts/bindings/ownerHeads/history/
cursor and recomputes exact contiguous target. Expected-old whole inventory/cursor CAS:
changed proof/header/group/pull/current prefix/key/auth aborts; no blind write. Exact already
committed plan returns already_proven if original inventory except prefix unchanged; fresh
same-target no_progress. Only cursor.proven_prefix changes, ACK/source/phase/ordinal stay.
No decreases, beyond-pull target or holes. Positive prefix retained across renderer/profile
reopen; no registry/transport discovery in prefix operation.

ackStatus is READONLY diagnostic, no HTTP/ACK commit. Reports safe_note_prefix_available
when crypto-verified candidate needs explicit persistence, missing/received/Metadata/family
barriers, no_ack_progress, registry_reconciliation_required, pull_required and
ack_transport_unavailable. A fresh explicit C21.1.13 registry token, scope/current lease/
exact current bindings required to pass registry gate; token never becomes durable proof.
Normal existing registry diagnostics report actual durable positive prefix and ACK cursor;
ready:false/ack_eligible:false always. Positive prefix alone does not imply full sync ready.

NETWORK GATE STOP: durable Web UUID/normal auth are valid and frozen PUT /api/v1/sync/
devices/{id} registration exists, but registered-device authority/current account writer
mode/cutover/compression-reader capability flow is absent in this dormant Web composition.
Native NoteSyncDeviceAckAdapter default protocol1 cannot ACK encrypted mode2/3; Native
cycles verify mode and required reader support before mode-specific transport. Backend
services.ack enforces registered authenticated device, mode equality and required ID1
reader capability, bounds to current account sequence and monotonically retains max ACK.
Safe V2/V3 endpoint cannot be selected from mixed retained protocol versions. No arbitrary
reader capability/cutover declaration. Prefix-only implementation, not an improvised HTTP
adapter. Registration/ACK/capability/cutover requests0; server last_ack_cursor never copied.
Frozen idempotent/lost-response/local-failure semantics audited, actual ACK tests not run
because network disabled. Next bound: authenticated Web mode/reader/device prerequisite
bridge, then separately bounded ACK/retry/commit; other-family protected apply still missing.

Checks: aggregation16/persistence23/diagnostics2 =41 new +521 affected =562 PASS/31 curated
files; final focused checks PASS. Chromium171: three proven Notes/prefix3, abort/key/logout,
only cursor writes, reload/disk persistence, received4 stops safe5 then original protected
apply/prefix5, missing6 stops safe7 (isolated recovery fixture restores exact ORIGINAL
received bytes, no fake success), legitimate apply/prefix7, Document8 stops Note9, account
isolation, final prefix7/ACK0/pull9/phase unchanged/readyfalse. Old proof/conflict/self-echo/
initial cohort/migration/open regressions retained. Existing registry16/completion16 fixture
requests only; new registration/ACK/pull/push/registry/bootstrap/Resolution0/page errors0.
Typecheck/build/workflow/syntax/diff/pyc PASS; existing warnings only. Three explicit Cloud
specs plus accepted regressions and hard-failing Chromium; SQLite NOT EXPECTED. No skips/
dependencies/backend/PG/native/frozen protocol/crypto/receipt/conflict changes or CI polling.

## C21.1.19 — explicit device registration / ACK gate stopped

C21.1.18 REMOTELY ACCEPTED PARTIAL: SHA `6de5183e1fddcac4e4e4d1f8c70d4b3f47799bce`,
Cloud `38568720231` SUCCESS / all six required jobs SUCCESS; proven-prefix COMPLETE,
ACK transport BLOCKED. Official84.0%, C21 IN PROGRESS, .06 NOT LOCAL COMPLETE.

### C21.1.19 bounded result

**PARTIAL LOCAL COMPLETE / REGISTRATION COMPLETE / ACK BLOCKED / REMOTE CI PENDING — NOT POLLED**.
Current exact Native/backend/Web architecture and capability matrix recorded BEFORE
production edits in `docs/cloud/C21_PROTECTED_APPLY_FAMILY_AUDIT.md`. Historical C9
PUT `/api/v1/sync/devices/{device_id}` is still authoritative across account modes1/2/3;
registration protocol1 is not account writer mode. Account mode source is fresh authenticated
GET `/api/v2/sync/encrypted/capabilities`; no mode selection/cutover occurs in this slice.
Writer transport routes account publication/ACK; separate per-family reader gates exist.

Dormant `session.device.bind(normalAuth,binding).registerOnce(scope)` uses existing durable
UUID and authoritative binding, current auth/session checks plus read-only IDB identity scope
validation BEFORE and AFTER HTTP. Exact reply allowlist protocol_version/device_id/
last_ack_cursor; wrong/future device/mode/capability/cursor rejected. One explicit PUT with
no body, no unsupported capability declaration; server insert-or-reuse preserves existing
capabilities/ACK, updates last_seen only. No local registration cache or proof needed;
server authoritative, retry same identity. last_ack_cursor returned only as metadata,
never copied into local cursors. Schema8→8/no stores/index/migration. No public UI/help change.

ACK gate STOP: C18.7 compression_id1=true means bounded reading for all canonical codecs1–13,
not shared decompressor presence or compression_zero. Browser protected readers cover Legacy
Note JSON1 and limited Metadata authority; no complete family readers, framed Content Note8
or Resolution apply. No safe ID1 declaration. Registration response omits sticky account
compression_id1_required/current device capabilities; aggregate compression GET is not this
proof. Authoritative mode API exists, but registration alone cannot authorize ACK for current
compressed mode3 history. No Web ACK implemented; this is not a claim that every uncompressed
account mode can never support a later bounded ACK. Cross-family/no-skip barriers, prefix
aggregation, ACK0, ready=false unchanged. No loops/pull/push/bootstrap/registry discovery.

Checks: registration28 + prefix/barrier/ACK diagnostics59 + affected identity/open/migration/
auth19 = **106 tests /10 files PASS**. Chromium **177 cases PASS**, includes existing171 and
six registration groups: auth/exact payload/replay, all12 stores unchanged, malformed replies,
lost registration response/retry, wrong account/user/device and stale auth, reload and disk
profile reopen. Existing positive prefix7/ACK0/pull9 and Document8 barrier intact; server ACK19
not imported. API counters: registration11 (explicit, includes failure cases), ACK0, push0,
pull0, bootstrap completion16 and registry16 (unchanged fixtures), Resolution0/unrelated0/
page errors0. Harness uses isolated authenticated HTTP fixtures, not a live production account;
backend retry/default/capability semantics verified from frozen source and existing PG tests.
New ACK lost-response/local-commit-failure tests NOT APPLICABLE: gate blocked before implementation.

Typecheck/production build PASS (existing Vite chunk/import warnings only); workflow YAML,
JavaScript syntax, diff check PASS. Mandatory Cloud contract job adds registration spec,
existing mandatory Chromium gate invokes new helper. No backend/PG/Alembic/native/SQLite/Rust,
dependencies or frozen contract changes; protected pyc unchanged. Cloud EXPECTED, SQLite NOT
EXPECTED. Official84.0%, C21 IN PROGRESS, C21.1.06 NOT LOCAL COMPLETE; no roadmap points.

### Простыми словами

- Браузер умеет по явному запросу зарегистрировать на сервере своё сохранённое устройство; после повторного открытия используется тот же номер.
- Регистрация нужна серверу, чтобы связать запросы с конкретным устройством нужного аккаунта. Дополнительные возможности чтения браузер пока не объявляет.
- Подтверждение изменений серверу не включено: сервер может требовать чтения сжатых данных всех видов, а браузер пока безопасно обрабатывает только часть данных проекта.
- Полученные изменения по-прежнему проверяются по порядку; неподдерживаемое изменение останавливает проверку. Автоматический обмен данными и готовность всей синхронизации выключены.
- Следующий шаг — проверить и добавить недостающие средства чтения данных, затем отдельно подключить безопасные подтверждения серверу.

## C21.1.20 — canonical readers / explicit capability / bounded ACK

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

### Простыми словами

- Браузер проверен на чтение всех 13 форматов облачных данных, включая поддерживаемые старые и новые варианты.
- Для каждого формата проверены обычные и сжатые данные; повреждённые или неподдерживаемые данные отклоняются.
- Теперь браузер может по явному запросу честно сообщить серверу о поддержке чтения сжатых данных. Это не включает их запись или автоматический обмен.
- Подтверждение серверу заработало: браузер сообщает только номер изменения, до которого всё безопасно обработано. Потеря ответа или сбой сохранения допускают безопасный повтор.
- Прочитать данные ещё не значит применить их к проекту. Неприменённые документы, этапы, карты и другие виды данных по-прежнему останавливают подтверждение перед собой.
- Главный следующий шаг — безопасно применять остальные виды данных к проекту. Полная синхронизация в браузере пока не считается готовой.

## C21.1.21 — coverless Metadata ACK-safe proof

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

### Простыми словами

- Раньше служебное изменение проекта могло быть успешно обработано, но всё равно останавливало подтверждение серверу.
- Теперь поддерживаемые изменения проекта без обложки входят в общую непрерывную цепочку после проверки сохранённых данных и их происхождения.
- Если между двумя безопасно обработанными заметками есть такое изменение проекта, браузер может подтвердить всю цепочку до третьего изменения.
- Конфликт, неприменённые данные, неподдерживаемый вариант или обложка по-прежнему останавливают цепочку перед собой.
- Остальные виды данных ещё не все умеют безопасно применяться к проекту; полная синхронизация в браузере не готова.
- Следующий шаг — добавить безопасное применение следующего вида данных, например этапов проекта, сохранив проверки остальных ограничений.

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
