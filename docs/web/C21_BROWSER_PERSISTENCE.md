# C21.1.02–C21.1.12 — Browser durable persistence / E2EE adapter contract

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
