# C21.2.21 — trusted import-origin evidence contract audit

Starting branch `6.0`, clean local HEAD, fetched `origin/6.0`, and remote
`refs/heads/6.0` matched `37ae64429eae378f65f80413d6c2a0dabaffa10f`.
C21.2.18 remains **REMOTELY ACCEPTED**, Cloud `39850013638`, SUCCESS6/6;
C21.2.19 remains **AUDIT COMPLETE**; C21.2.20 remains **IMPLEMENTATION STOP /
NOT LOCAL COMPLETE**. This audit changes documentation only and does not
reinterpret .20 as implementation success.

## Decision

**AUDIT COMPLETE — original per-device import provenance is not retained.** The
current binding and registry response do not prove the original import cursor.
However, the current server implementation provides a stronger way to prove the
fact needed for a no-genesis decision: freshly authenticate and replay the
complete account event log from sequence1 through the current server cursor,
then authenticate the target project's actual Metadata/F history. This proves
whether a Metadata genesis existed before F without relying on the import-time
cursor or a local empty owner head.

Recommend **Option A with complete server-history replay** as the single
candidate contract. This is supported by the current code, not by the binding's
`remote_high_water`. It remains fail-closed if the server log is incomplete,
the account inventory exceeds existing limits, any row/proof is invalid, or the
fresh cursor cannot be matched. The backend currently has no history-compaction
path; preserving the sequence log is an explicit acceptance requirement for
this proof. If the server owner cannot guarantee that behavior, the cohort stays
unsupported pending a server-verifiable history/retention contract.

This audit authorizes no implementation. `unsupported_create_baseline` remains
unchanged until a separately tasked implementation proves this admission path
and its full acceptance matrix.

## Actual authority and data flow

| Source | What it proves | What it does not prove |
| --- | --- | --- |
| `frontend/src/platform/web/projectBindings.ts`, `BrowserProjectBindings.importRemote()` | Exact-shape `project_id`, `bootstrap_id`, active state and nonnegative high-water are stored in an account/device-scoped row. | It explicitly accepts a supplied DTO; it has no authenticated-registry capability or retained original response. A local binding is not import authority. |
| `frontend/src/platform/web/accountRegistry.ts`, `reconcile()` / `targets()` | The authenticated current registry response is bound to the active account/session; bootstrap identity and state are checked; local bindings are CAS-updated. | `targets()` writes the current account cursor into `remote_high_water`. The WeakMap registry capability is runtime-only. Neither records the original per-device import cursor. |
| `frontend/src/cloud/projectBootstrap.ts`, `importRemoteProjectOnce()` | A real current import fetches the authenticated bootstrap list, selects the active project descriptor and passes its bootstrap ID plus current cursor into the repository. | The original response is not retained as durable authenticated provenance. A crash can occur between GET and local import persistence. |
| `backend/app/cloud/models.py`, `CloudProject`; `backend/app/cloud/services.py`, `list_bootstrap()` and `complete_bootstrap()`; `backend/app/cloud/projects_router.py`, `/bootstrap` | The server stores the project bootstrap ID, origin device, state and immutable initial-upload count/max sequence. Registry GET returns these plus the current account cursor. | Initial-upload counters describe the original upload cohort, not this device's import time or whether the account event log contained project Metadata at that time. |
| `backend/app/cloud/repositories.py`, `SyncRepository.pull()` / `pull_encrypted_descriptors()`; `backend/app/cloud/services.py`, encrypted pull | Authenticated sync pull can read events after any account sequence; rows retain globally unique account sequence numbers. Current code inserts accepted events and has no sync-history compaction/deletion path. A missing sequence is observable as a gap. | The registry endpoint alone does not return event history or a signed history receipt. Current code is implementation evidence, not a promise that future server versions may compact history. |
| `frontend/src/platform/web/resolutionPlanner.ts` / `resolutionAuthentication.ts` | F has actual encrypted wire, AEAD, source/history outcomes and a `dependency_digest` committing its then-observed local owners and bindings. | The digest does not retain an import receipt or recover a guessed historical snapshot. It cannot replace server-history replay. |
| `frontend/src/platform/web/persistence.ts` | IndexedDB schema10 contains the existing `projectBindings`, `inbox`, `cursors`, owner/source/history stores and native identity/account-binding transaction checks. | A durable local cursor/inbox/head can be edited, incomplete, stale or forged. Without fresh server replay it is not independent proof of original import or no genesis. |

The server is the authority for account identity, bootstrap lineage, event
sequence assignment and the current high-water. The device records when it
imports only indirectly through its local cursor/binding. The current API does
not preserve that per-device historical fact. A fresh authenticated bootstrap
GET establishes current server state only. A fresh authenticated full sync pull
can establish the needed history because the current server exposes the
sequence log from its beginning and current code has no compaction operation.

Browser restart, device migration and import interruption are handled by
reconstructing evidence from the server, not by trusting a local import receipt:
after restart or on a second device, authenticate the same account and device,
verify the active project/bootstrap descriptor, pull the account sequence from
1 through the server's current cursor, validate every row and the target
project's original ciphertext/history, then prepare a fresh private proof. Do
not accept a locally stored `remote_high_water` as the replay start or as the
proof. If the current cursor advances during preparation, repeat/revalidate or
block. A crash before durable local inbox commit leaves a gap/short cursor and
blocks; restart pulls the missing range. Existing account inventory limits
(16,384 rows per store and 32 MiB aggregate) still apply; limit overflow blocks
this route.

## Options A–D

| Option | Finding | Decision |
| --- | --- | --- |
| **A — existing evidence only** | Current binding + current registry + a complete-looking persisted inbox are insufficient. The actual authenticated server event log replayed from sequence1 through the current cursor is sufficient under the current append-only server behavior: it exposes any earlier Metadata genesis, including a genesis whose current owner head is missing or deleted. If any sequence is absent, history is compacted, or authenticated replay cannot complete, no permission is derived. | **Recommend**, with server-log retention pinned as an acceptance invariant. No import receipt is required for the no-genesis fact. |
| **B — durable import-origin receipt** | A valid receipt would bind canonical account/user, local account, registered device, project/bootstrap IDs, exact registry descriptor, original cursor, auth epoch and import lifecycle. Only the coordinator that received the real `authorized()` response could mint it; the current registry WeakMap token is not passed to import and cannot be restored after restart. A same-database hash is forgeable. A keyed MAC/AEAD needs a reviewed key and local-tamper threat model and still proves only that the trusted app sealed a response it received; it is device-local and cannot independently attest server history. Reconciliation must leave the receipt immutable. Receipt and binding need one native transaction, exact retry after commit, and no receipt after a crash before commit. Adding fields to strict record1 requires a versioned binding/schema migration (or new store); legacy rows cannot be backfilled truthfully. | Not needed by the recommended replay. If later required for import-time audit provenance, contract-review the authority, cryptographic key, device-migration semantics and versioned storage before implementation; never backfill old receipts. |
| **C — server-verifiable origin** | Existing bootstrap row is immutable for upload lineage and initial-upload counters, but does not record an importing device/cursor. No endpoint returns a per-device import checkpoint or signed historical proof. The server cannot infer which account cursor a device actually imported. A future server attestation would need an authenticated device/project/bootstrap checkpoint request and immutable per-device state or a signed response; that is a new API and likely database contract, not an existing response. | Not needed when full append-only log replay is available. If retention changes or a durable import-time audit becomes a requirement, new backend contract/schema review is required. |
| **D — unsupported create cohort** | Post-F Legacy no-head is a representable genuine cohort (.19), while Content-F needs its Metadata dependency before F. Current contracts explicitly leave no-head create blocked. They do not explicitly classify this one Legacy-F cohort as mandatory or optional for release. | Keep the route unsupported until complete-history replay is independently accepted and the owner confirms this cohort's release classification. Do not remove mandatory Metadata behavior or infer a release waiver. |

## Required decision matrix

“Permit” means only that the no-genesis prerequisite can pass; all existing F,
source, owner, ten-store CAS, lifecycle and independent create acceptance checks
remain mandatory.

| Case | Result | Reason |
| --- | --- | --- |
| Fresh authenticated import, original cursor0 | **Provably permitted**, after full replay and other gates | Fresh replay independently checks the actual sequence history; the stored zero is not used as authority. |
| Fresh import with nonzero history | **Provably permitted** only if replay proves no prior target-project Metadata genesis and all history validates; otherwise **rejected** | Nonzero account history alone is not a target Metadata head. |
| Registry reconciliation increases high-water | **Temporarily blocked pending revalidation** | Re-fetch/replay through the new current cursor; reconciliation's overwritten field does not preserve origin. |
| Browser crash during initial import | **Temporarily blocked pending revalidation** | Resume with authenticated replay; gaps/short pull cursor block until filled. |
| Browser restart after successful import | **Temporarily blocked pending revalidation**, then **provably permitted** if replay succeeds | Recreate the private proof from current server history; do not restore runtime tokens. |
| Second device imports the same account | **Temporarily blocked pending revalidation**, then evaluate from its own authenticated full replay | It must verify account, registered device, project and bootstrap identity independently. |
| Previously imported project without provenance receipt | **Provably permitted** only after full server replay; otherwise **unsupported** | No fabricated receipt is needed; local history alone is not enough. |
| Local database migration from an older version | **Temporarily blocked pending revalidation** | Existing rows remain. Replay from sequence1 after migration; no receipt is backfilled. |
| Corrupted or forged local import evidence | **Rejected** or **temporarily blocked pending revalidation** | Caller DTO, altered binding/high-water or malformed local rows cannot pass authenticated replay and exact identity/history checks. |
| Missing historical Metadata head | **Rejected** if replay retains a genesis; **temporarily blocked** if the history has a gap | A missing head does not erase an earlier event. |
| Original Metadata genesis retained elsewhere in account log | **Rejected** | Authenticated project history reveals that the target project already had a genesis. |
| Conflicting bootstrap/project identity | **Rejected** | Exact current account registry and event/bootstrap lineage must agree. |
| Registry response after server-side history compaction | **Temporarily blocked / unsupported until recovery contract exists** | Current cursor without a complete sequence from1 cannot prove absence. Never bridge the gap. |
| Offline device without current registry access | **Temporarily blocked pending revalidation** | No current authenticated high-water or registry identity is available. |

## Migration, release classification and next stage

The recommended replay uses existing IndexedDB stores and the existing
authenticated registry and sync APIs. **No schema migration, backend endpoint,
new cryptographic proof or dependency is needed** while the server retains the
complete sequence log. Older bindings are preserved and revalidated; they are
never silently deleted/re-imported, and encrypted data is never discarded.
There is no safe receipt backfill for legacy bindings. If replay cannot cover
sequence1 through the current cursor, explicit recovery or a separately reviewed
server history contract is required.

The server history retention rule is the remaining contract boundary: current
repository/service code demonstrates append-only event insertion and full
sequence pulls, but no explicit frozen policy against future compaction was
found in the inspected contracts. Independent acceptance must pin that rule or
verify a server-provided earliest-retained sequence and reject any incomplete
range. The current frontend's 16,384-row/32-MiB bound may leave unusually large
accounts unsupported; increasing it is a separate capacity decision.

The frozen routing contract calls coverless Metadata create a candidate future
route and explicitly blocks create without a legitimate no-head baseline. The
checkpoint makes this specific Legacy-F cohort release-blocking for C21
completion, but no inspected owner statement classifies it as an unconditional
WORTA6.0 user-facing release requirement. Preserve both facts: do not drop
frozen Metadata guarantees, and do not claim this cohort is release-optional
without owner decision. If unsupported status is retained, users on the cohort
remain unable to apply this post-F Metadata create and need explicit recovery or
an owner-approved release boundary.

Propose **C21.2.22 — private Legacy-F no-head create using authenticated complete
history replay**. It should integrate only the replay proof into the dormant
private create path, then independently accept fresh/restarted/second-device
zero and nonzero histories, registry advancement, missing/forged/corrupt rows,
retained earlier genesis, conflicts, cursor races, import crashes and native
atomicity. Keep all Content-F, covers, Stage/StageOrder, ACK, transport2 and
startup/default-route exclusions. Do not begin .22 automatically.

Preserve C21/C21.2 IN PROGRESS; C21.2.20 NOT LOCAL COMPLETE; C21.2.19 AUDIT
COMPLETE; C21.2.18 REMOTELY ACCEPTED; C21.2.11 historically PARTIALLY RESOLVED;
C21.2.08 NOT CLOSED; C21.1.06 NOT LOCAL COMPLETE. Web89.36%, `ready=false`,
registration CLOSED, PUBLIC RELEASE BLOCKED. VPS, landing, permanent CI/CD
release policy, existing stage weights and release gates remain unchanged.

## Checks

Focused read-only source and contract inspection only; no probes or test suites
were run. No frontend/backend/Rust/Python/schema/workflow/wire/cryptography files
changed. The decision rests on current code paths named above; server log
retention beyond current implementation remains an explicit acceptance item.
