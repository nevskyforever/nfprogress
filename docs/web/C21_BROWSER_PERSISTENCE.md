# C21.1.02 — Browser durable persistence / E2EE adapter contract

Contract v1, 2026-10-11, frozen for the next bounded implementation slice.
Starting local/fetched `6.0`: `0ad27ac4c5ccf09de99c2a8c3d29759003a39ee8`.
C21.1.01 independently accepted by owner/GPT: Cloud `38127992242` SUCCESS,
all required Cloud jobs SUCCESS; SQLite not triggered/not expected. C21 stays
IN PROGRESS, official WORTA ROADMAP SCORING v1.0 **84.0%**.

## Decision and limits

Use one origin/profile-scoped IndexedDB database `worta-web`, with Web Locks
exclusive writer ownership of `worta-web:writer`. Storage schema version **1**
implements only `identities` and `accountBindings`. Other stores below are a
**frozen semantic design**, not implemented stores or enabled Web sync.
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
| `outbox` | `[account_id,event_id]`; unique `[account_id,device_id,local_ordinal]`, `[account_id,state,local_ordinal]` | Planned: frozen envelope/AAD metadata, exact immutable sealed transport bytes, parents/base tips, state and bounded retry code; receipts linked atomically. No unsealed plaintext. |
| `inbox` | `[account_id,server_sequence]`; unique `[account_id,event_id]`, `[account_id,state,server_sequence]` | Planned: verified encrypted transport row; received/applied/orphan/blocked state + typed code/dependencies. Exact replay comparison. |
| `cursors` | `[account_id,device_id]` | Planned: pull cursor, committed ACK, contiguous proved prefix, next local ordinal and expected-old CAS. Never infer ACK from max sequence alone. |
| `receipts` | `[account_id,event_id]`; `[account_id,server_sequence]` | Planned: immutable upload acceptance/protected-apply receipts and causal continuation proofs, frozen canonical references. |
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
v1 only supports a new empty DB or exact existing v1. Unknown future IDB version
raises a typed version blocker with no downgrade/delete. Known future upgrades
must be incremental, versionchange-atomic, preserve immutable ciphertext and identity,
validate old records before transforming, and abort on any unsupported record.
Older connections close on versionchange; blocked upgrades reject and require
explicit reopen after other tabs close. No copy into plaintext legacy API storage.
Rollback to an older app requires a compatible reader, not destructive migration.

## Multi-tab ownership

Conservative v1 policy: **one writer session per origin/database across all accounts**.
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
Inbox/outbox/ACK/protected apply/bootstrap/authority repositories require independent
IDB implementations and corresponding invariant tests, not SQL translation.
No C18 entities or Class C device-local bindings are redefined.

Next **C21.1.03**: implement bounded encrypted outbox/inbox/cursor persistence with
exact retry, atomic rollback and restart proofs, still dormant. No UI/full Web sync
activation before protected apply/ACK/account-wide reconciliation and retained
conflict/authority proofs have their own accepted implementations.

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
- versionchange closes old handle, v2 refuses unsafe v1 open, records retained.

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
npm run dev -- --host 127.0.0.1 --port 5174
# Repository root, another terminal:
node frontend/scripts/browser-persistence-acceptance.mjs http://127.0.0.1:5174
npm --prefix frontend test -- --run src/platform/web/persistence.spec.ts \
  src/platform/runtime.spec.ts src/auth/userAuth.spec.ts src/auth/accountBinding.spec.ts \
  src/auth/keyContext.spec.ts src/cloud/noteSyncRuntime.spec.ts src/stores/cloudSession.spec.ts
npm --prefix frontend run build
```

The harness supplies only a blank HTML page on an isolated loopback route and
loads the actual source module through Vite; it does not mount the HTTP compatibility
application, mock its success, or touch user application data. Production application
smoke from C21.1.01 is retained, not repeated: its runtime paths are unchanged.
Full native/SQLite/Rust/PostgreSQL/Android/Windows/Nuitka suites and deployment
**not run**. Browser power-loss, public retention UX, encrypted repository/apply/ACK
acceptance and full Web cloud sync remain later gates. No full sync activation.

Expected publication CI: Cloud backend tests (frontend/src path filter); SQLite
sync substrate tests not expected. Existing curated remote selection does not run
this new persistence spec or real-browser harness automatically; the local results
above must not be presented as remote browser acceptance. No CI/dependency/install
changes made for this slice. Published SHA is REMOTE CI PENDING, not polled.
