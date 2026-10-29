# WEB.ONLINE.02B.03G — bounded ciphertext delivery (design only)

Baseline: `e2060541fb15c0bf1954ba6557878f71ac459bf9`, clean `6.0`.
03E: owner-reported run **40844792258 — 6/6 SUCCESS**. 03F remains STOP.
**Decision: conditional GO for B as a separately approved API contract;
implementation/activation STOP until explicit owner approval.** No endpoint,
capability, schema or runtime change is authorized by this document alone.

## Evidence and A/B decision

[SyncService](../../backend/app/cloud/services.py) `pull_encrypted()` checks
recipient Note readiness over retained account history; `content_note_reader_ready()`
requires ordinary1 and Resolution2 together. `content_note_gate()` includes every
registered device. [Gate tests](../../tests/test_cloud_c18_content_note_gate.py)
cover incomplete-recipient refusal and registration/downgrade blocking writes.
[Readiness](../../frontend/src/platform/web/noteReaderReadiness.ts) is explicitly
negative. [Source/proof contract, section 9](WEB_ONLINE_02B_C21_SOURCE_PROOF_CONTRACT.md)
currently provides no recovery-delivery exception; B requires its explicit amendment.

| Option | Real work before use | Scope/risk |
| --- | --- | --- |
| A: full readiness | Accept production v10 dispatch and paged replay; orphan/dependency recovery; tombstone resurrection; further Resolution chains; local-author-after-Resolution; own Content/Resolution chains and receipts; multi-device orchestration and server gate verification. Then independently qualify ordinary1/Resolution2 before an explicit declaration task. | Several separately accepted C21 cohorts, not one update slice. No defensible time estimate from this bounded review. Map/document/progress/game/compression claims still need their own dependent gates; Note readiness does not qualify them. False early declarations could unblock other writers unsafely. |
| B: session-authorized opaque recovery delivery | Add a distinct delivery contract and shared materialization path; retain negative readiness and all existing sync gates. Owners still decide what can be applied. | Bounded backend plus receiver work. Main risks are accidentally enrolling a sync device, partial account history, divergence from normal pull integrity, and resource amplification. |

Prefer B to unblock independently testable read-only owner composition. It grants
an already authenticated account holder access to their ciphertext, never a
claim that any client can apply it. It does not finish A or authorize writing.

## Proposed API (not implemented)

`GET /api/v3/recovery/encrypted/history`

Query: `delivery_version=1`, `protocol_version=3`, `encrypted_sync_version=3`,
`since` (safe integer >=0), `expected_cursor=T` (safe integer >=0), `limit`
(default 100, 1..100). Unknown query keys/versions reject. No account/project
filter, capability list, sync device ID or caller-selected user ID.

Response: `{delivery_version:1, current_cursor:T, writer_transport_version:3,
cutover_epoch:E, items, next_cursor, has_more}`. `items` use exactly the existing
v3 descriptor and encrypted envelope DTO serialization, including account-scope
objects and original author device/server sequence. Delivery version is only an
outer envelope: stored events remain original v3, never relabeled Legacy.
`current_cursor` is a snapshot guard, never an ACK or application certificate.
Use `Cache-Control: no-store`; no plaintext, AMK, payload logging or public cache.

### Authorization and client identity

Use the same bearer authentication, current PostgreSQL session/user validation
and mandatory legal-acceptance checks as
[`get_current_accepted_user`](../../backend/app/dependencies.py), on every page.
All queries derive user ID from that identity; foreign events/objects cannot be
joined even by guessed IDs. No anonymous, invitation-only or legacy `/api` access.
Expired/revoked sessions, inactive users and missing mandatory acceptance reject
with existing auth/legal errors. Recheck session validity before response
publication; revocation after the final check cannot recall already sent bytes.

The auth session identifies the delivery client server-side. A browser may keep
its existing account-bound local replay UUID for leases/CAS, but that UUID is
not a verified sync device or authority to publish. **Do not call device
registration for this path.** No new server client registry or recovery token
store. Existing local encrypted replay identity remains isolated from v12.
Owner adapters must prove they need only local identity for this cohort; any
requirement for a registered/capable sync device is a STOP, not a synthetic token.

### Snapshot, pagination and integrity

1. Client obtains existing registry/mode evidence, fixing T and cutover epoch E.
   Require existing mode3 state; never initialize it or perform cutover.
2. Read existing user state using `SyncRepository.user_state()`, not
   `ensure_user_state()` (which inserts). Missing state rejects without creation.
   Compare T before and after materialization; any tail/mode/epoch change returns
   409 `recovery_snapshot_changed`, with no page published. Growing accounts may
   require bounded retry; no promise of success under continuous changes.
3. Read ALL account events strictly ascending, `since < sequence <= T`, with
   limit+1 and the existing byte-budget policy. No device/project/family filtering.
   Enforce consecutive sequences, no duplicates and `since <= T` server-side.
4. Retain descriptor/object two-phase selection, original nonce/ciphertext and
   xmin/identity/length checks. Missing object, mismatched user/event/version,
   mutation between selection/materialization, gap or unrepresentable descriptor
   fails the whole page before cursor advancement. Unknown families are never
   silently omitted: current shared v3 schema rejects unrepresentable events;
   unknown encrypted codec/frame versions remain opaque in delivery and block
   the client owner. Never fall back to another codec or compress/reseal bytes.
5. `next_cursor` is the last returned sequence, or `since` only at T;
   `has_more = next_cursor < T`. Empty progress before T is an error. Object/page
   limits may shorten a page but cannot create gaps. At since=T return empty/false
   only after the same snapshot/auth checks.
6. Receiver starts reconciliation at zero on every resume/restart, comparing all
   retained wire exactly. It verifies identity, registry and mode again at end,
   publishes nothing on mismatch, and preserves committed ciphertext/proofs.
   Registry/bootstrap change invalidates consumption even if T is unchanged.
   This is bounded state-at-T evidence, not a cryptographic append-only server log;
   AEAD and genuine owner lineage remain essential.

### Reuse and server state

Do not call current `pull_encrypted_v3()` with a skip-gates flag. Extract one
internal shared bounded materializer from `pull_encrypted()` plus its v3
representability validation, and one shared v3 item serializer from
[sync_v3_router](../../backend/app/cloud/sync_v3_router.py). Both entry points use
them; only ordinary pull performs its unchanged recipient/device/capability
policy. Preserve normal pull response and errors through parity regressions.
Reuse user-scoped descriptor/object repository queries and
`_validate_materialized_encrypted_prefix()`; add snapshot bounds in that common
path. Shared helpers cannot register, initialize state or modify capability.

Recovery database work must execute as read-only (including auth/legal checks):
no state creation, last_seen update, ACK, receipt, bootstrap, event, writer flag or
capability write. No migration is needed. SQL write detection and full relevant
row snapshots are required tests. Operational transient throttling counters are
not sync state and are the only explicit non-durable accounting exception below.
If auth/session plumbing cannot uphold this read-only boundary, stop that slice.

### Resource policy

Reuse constants: object ciphertext <=8,388,624 bytes; page ciphertext <=16,777,216
bytes, bounded serialization and the existing API response-size guard. No blob
body expansion or full-history response. Web keeps existing replay budgets
(200 events, 32 MiB aggregate ciphertext/inventory, page100); exceeding them is
an honest `history_limit`, not partial project success.

No per-pull request-rate limiter was found in the inspected router/service; do
not claim C5 project-slot limits provide one. Implementation must add bounded
volatile request accounting: account AND auth-session token buckets, 30 pages/min,
burst2, one materialization/account/worker; 429 with Retry-After, cancellation,
10-second DB/query deadline, no unbounded identity-key cache. These are per-worker
limits: total load is multiplied by the configured worker/replica count. A fixed
reviewed worker count and aggregate concurrency/response-memory budget are an
implementation acceptance prerequisite; multi-replica/global limiting requires
an explicit shared-ingress design before deployment. No PostgreSQL limiter
writes, VPS changes or imaginary global-limit guarantee are approved here.

## Device impact and client composition

A new recovery-only browser creates **no SyncDevice row**, so it neither counts
as an incomplete reader nor authorizes any writer. Existing registered browsers
are never removed, excluded or promoted: an incomplete row still blocks existing
all-device writer gates exactly as before. Recovery does not cure that block.
A user must not be told that viewing ciphertext restores other devices' writes.
No automatic enrollment, cleanup or device-role migration is included.

Adapt the existing [receiver](../../frontend/src/platform/web/replayReceiver.ts)
with a typed delivery transport boundary (including its final tail check), not a
second sync engine. Keep original descriptors in replay storage; verify the
outer delivery envelope separately. No capability declaration, ACK or push can
be reached through this adapter. The bounded Content owner still needs exact
Metadata/Stage certificates, AEAD, source revision, candidate/head, transport and
inbox proof, atomic CAS/coverage and restart reauthentication. Unsupported
Resolution/family/version/conflict blocks application; receipt never means
`projectOpened=true`. No offline opening or registration-dependent fake owner
proof. Replay v4 compatibility must be established in its separate owner slice.

## Acceptance and implementation order

| Slice | Minimum acceptance |
| --- | --- |
| G1 backend delivery only | Real PG16: auth/legal/foreign account/revocation; no-device recipient with genuine producer ciphertext; mixed projects/account scopes and multiple pages; exact parity with normal pull after legitimate readiness; ordinary unready pull still409; gaps, missing/mutated objects, oversize/budget, cursor/tail/mode changes; unknown descriptor refusal; 429/deadline/cancel; zero domain writes. Show new recovery does not add a device or alter other-device push gates; existing incomplete device still blocks. No Web owner activation. |
| G2 receiver integration only | Real Chromium restart: full zero-origin wire reconciliation, no enrollment, duplicate/gap/truncation, changed registry, session/logout/AMK/network/abort, bounded retry/quota rollback and v12 preservation; ciphertext-only storage and zero ACK/push/capability requests. No owner outcome from receipt. |
| F resumed: one Content update | Genuine Legacy create -> one Content update through existing Content owner; full proof/source/candidate/coverage join and recovery, negative dependency/parent/version/fork/tombstone cases. Full required Local-First acceptance; all readiness flags remain false. |

**Owner approval needed:** explicitly approve this new session-authorized recovery
endpoint and its non-enrolled client identity, shared materializer refactor,
resource-accounting policy, and narrow amendment to section9 of 02B. This approves
delivery only; no weakening of ordinary pull, all-device writers or reader claims.
Until then: implementation STOP. A remains the fallback if that new contract is
not approved. No migration or runtime change occurred in 03G.

`ready=false`, `declarationAllowed=false`, `writerAuthorized=false`,
`projectOpened=false`; Registration CLOSED; PUBLIC RELEASE BLOCKED.
C21/C22/C23/PF6.0/RC remain mandatory. Official progress **89,36%**.
