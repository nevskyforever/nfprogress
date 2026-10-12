# C21.1.02–C21.1.06 — Browser durable persistence / E2EE adapter contract

Contract revision5, 2026-10-12. C21.1.05 remains dormant; IDB schema stays3.
C21.1.06 stopped at prerequisite audit; no protected apply implemented.
Starting local/fetched `6.0`: `0ad27ac4c5ccf09de99c2a8c3d29759003a39ee8`.
C21.1.01 independently accepted by owner/GPT: Cloud `38127992242` SUCCESS,
all required Cloud jobs SUCCESS; SQLite not triggered/not expected. C21 stays
IN PROGRESS, official WORTA ROADMAP SCORING v1.0 **84.0%**.

## Decision and limits

Use one origin/profile-scoped IndexedDB database `worta-web`, with Web Locks
exclusive writer ownership of `worta-web:writer`. Storage schema version **3**
implements `identities`, `accountBindings`, `outbox`, `inbox`, `cursors`, and
upload-acceptance `receipts`. Protected-apply receipts remain unimplemented.
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
| `projectBindings` | `[account_id, project_id]`; `[account_id, bootstrap_id]` | Planned: exact device/lineage/mode/phase, remote state/high-water, cohort IDs/count/ordinal, pause/blocker code. No title/path/source binding. |
| `outbox` | `[account_id,event_id]`; unique `ordinal` on `[account_id,device_id,local_ordinal]`, nonunique `state` on `[account_id,state,local_ordinal]` | Implemented schema2 / record1: account/device/event/ordinal, protocol2 or3, state `sealed` or `accepted` (schema3), exact `raw_body` from an existing singleton encrypted push. Accepted requires its immutable upload receipt; no unsealed plaintext. Causal parent/base-tip proofs remain inside existing sealed frames; authority capture is deferred. |
| `inbox` | `[account_id,server_sequence]`; unique `event` on `[account_id,event_id]`, nonunique `state` on `[account_id,state,server_sequence]` | Implemented schema2 / record1: receiving account/device, event/sequence, protocol2 or3, state `received`, exact metadata/encrypted envelope in `wire_item`. Wire validation is not crypto authentication or apply. Applied/orphan/blocked states and proofs deferred. |
| `cursors` | `[account_id,device_id]`, no indexes | Implemented schema2 / record1: pull cursor, `next_local_ordinal` starting1; `ack_cursor` and `proven_prefix` reserved at0, with no advancement API. Pull expected-old CAS is inseparable from inbox commit. Never infer ACK from ciphertext receipt. |
| `receipts` | `[account_id,event_id]`; unique `server_sequence` on `[account_id,server_sequence]` | Implemented schema3 / record1: exactly account/device/event IDs, protocol2 or3, server_sequence and first response duplicate diagnostic. Upload acceptance only. No protected-apply receipt, causal continuation, key/content/timestamp or arbitrary backend body. |
| `ownerHeads` | `[account_id,owner_kind,owner_id]` | Planned: complete tip IDs/revisions/dependency/history pointers, not decrypted projections. Owner identity retains exact existing project/account crypto scope. |
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
Current v3 supports a new empty DB, an exact v3, or forward versionchange
upgrades from exact v1 or v2. It validates every v1 identity/binding pair and their
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
