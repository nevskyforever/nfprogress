# WEB.ONLINE.02B — C21 Online-Only source/proof contract

**Status: DESIGN COMPLETE. Slice 1 implementation is recorded below; later slices remain deferred.**
Reviewed against clean `6.0` baseline
`57abb27ed712378a836ba654bc3c1c107ac804d5`, 2026-10-28. No production code,
migration, capability, writer, ACK or release change is part of this task.
The preceding implementation at `3ef704c5` was independently accepted by
owner-reported Cloud run `40578946929`, 6/6 SUCCESS. No CI was queried here.

**Implementation record, 2026-10-28:** the owner subsequently authorized slice 1
on baseline `a092ed2e84ceb18836d83dbec7118e060d8d07f4`. The new separate
`worta-web-replay` schema1 has 13 stores and permits only received inbox/technical
cursor/manifest state plus mirrored technical identity. Owner/source/outbound
stores remain empty. The explicit session receiver reads all account events in
pages, atomically stages them through `BrowserSyncDurability`, revalidates the
entire retained prefix against fresh server wire on resume, and requires final
registry/mode equality before returning a ciphertext-receipt summary. Prefix
comparison is read-only source reconciliation; it does not extend J's interval
replay or grant a certificate. No source/cohort/AEAD owner verification or project
opening is claimed. The 200-event, ciphertext and aggregate inventory limits are
enforced; rollback/lineage drift and unknown schemas reject. V12 and legacy data
are untouched. Final local prepush passed: 501 Vitest/18 files, typecheck/build,
six frontend Chromium scripts (17 new native storage scenarios), 263 backend
tests including the 10-scenario real Chromium/API/PostgreSQL receiver test, and
one encrypted-blob/PostgreSQL backup/restore. Changed ESLint and diff/static
checks passed; independent CI is pending and was not polled. The
original design sections below distinguish the future full owner composition
from this implemented receipt-only layer. Future owner records must have an
explicit schema/record compatibility decision before v1's received-only refusal
is broadened. No later slice is implicitly authorized.

## 1. Decision and authority

Use the existing encrypted account transport and C21 owners with an isolated,
durable, encrypted **replay cache**. The server remains authoritative for uploaded
user data. The cache is a reconstructible projection and transaction journal;
it cannot create a project, accept a local edit, publish an event, or authorize
an offline project opening. Loss of the cache requires server replay, never
recovery from an unrelated developer workspace.

This resolves the storage-policy question raised by WEB.ONLINE.02A: durable
owner evidence and Online-Only operation are compatible when browser storage
is derived, isolated and freshly checked against the server. Existing owners
still lack production composition and several family implementations. This
document does not remove those implementation barriers or approve full reading.
At the design baseline it proposed a storage boundary; the subsequent explicit
slice-1 task authorized its receipt-only implementation under `AGENTS.md`.
Further owner/content stores or behavior still require their own task.

Desktop keeps its SQLite source and optional sync. Existing `worta-web` v12,
local projects/stages/Notes/Documents and historical proofs remain untouched.
No implicit import, merge, promotion, cleanup or v12-to-production migration.
Reuse the existing account identity service, account binding and runtime AMK
lease for technical identity; do not create another key or copy credentials.

The contract covers synchronized history only. Unsent Desktop edits, local-only
entities and source-device private counters cannot be restored from the server.
Whole-account history means every retained sequence through a pinned cursor,
including other projects and account-scoped events. It does not mean that every
history is supported by today's owners. A limit or unsupported record blocks
opening; it cannot produce a partly restored project labelled complete.

## 2. Evidence and owner readiness matrix

Paths below are current implementations, not proposed APIs. `LOCAL` means a
bounded owner exists, not production Online-Only readiness. `NATIVE` means its
apply transaction executes in Rust/SQLite through Tauri and cannot run directly
in a normal browser. AEAD/codecs alone never establish an applied outcome.

| Owner / status | Required history and dependencies | Durable application evidence today | Reuse and missing production work |
| --- | --- | --- | --- |
| Metadata preview — implemented | `cloudRead.ts`, `canonicalReaders.ts`, `metadataImportSnapshot.ts`: complete bounded account feed, bootstrap, exact descriptor/header joins, causal Metadata history | None; returned Metadata is a read-only view, not apply proof | Reuse transport, AEAD and reducer unchanged. Keep preview distinct from all project-read results. Covers, unsupported families, conflicts and deleted head reject. |
| Imported Metadata — LOCAL | `importedMetadataApply.ts`, `metadataPrefixProof.ts`: original inbox wire, import binding, full Metadata parents/tips, bootstrap, no incompatible local publication | Metadata `ownerHeads` history plus `inbox.applied_proof`, committed together | Reuse owner and validators with an isolated transaction adapter. Ordinary coverless chain is narrower than all forms accepted by the preview reducer. Private post-F handoff has its own source/inventory checks. |
| Stage — LOCAL | `stageApply.ts`: Metadata proof/certificate, same project/bootstrap, exact parent/tip/revision and original peer wire | Stage owner head plus inbox record5 `stage_proven`, one transaction | Reuse existing create/update/read owner. Delete, self-echo and competing heads are barriers; Stage codec support does not remove these limits. Mixed v10 admission still needs complete-inventory guarding. |
| StageOrder — LOCAL | `stageOrderApply.ts`: Metadata plus all Stage heads, ancestry coverage and exact membership; unapplied Stage rows and tombstones are checked | StageOrder owner head plus inbox record6 `stage_order_proven` | Reuse existing owner. Missing/foreign Stage, changed membership, tombstone child manifest and unsupported history block. |
| Legacy ordinary Note — LOCAL | `noteTransport.ts`, `legacyNoteApply.ts`, `localAuthority.ts`: Legacy plaintext codec over original v2/v3 receive identity, initial cohort, causal candidates/head, membership, source CAS, real own receipts if needed | Encrypted project/Note source, candidate/head history, applied/conflict inbox proof and source revision in the owner's transaction | Reuse source/causal/historical kernels extracted by Z2B1/B2/B2C. Cache-only replay seeding below is not implemented; historical Z2A virtual-inventory/batch work is also unfinished. Do not call local CRUD to manufacture authority. |
| Content Note v3 — LOCAL; native reader also exists | `contentNoteApply.ts`, `noteTransportPrerequisite.ts`: canonical codec8, Metadata/Stage ancestry, route identity, causal and source rules | Candidate/transport/dependency joins, encrypted source and Content inbox proof committed by the actual owner | Reuse browser owner for its accepted cohort. `cloud/contentNoteReader.ts` defaults to native apply. Unsupported routes, conflicts and own Content evidence stay explicit barriers. |
| Note Resolution and descendants — LOCAL, bounded | `resolutionPlanner.ts` (including `BrowserResolutionApplyRuntime`), continuation, ordinary and prefix owners: all parents, conflict publications/closure, source-before/after, output identities, dependencies and immutable wire | Resolution4, GroupTransition2, encrypted output/source evidence, Head2 and inbox10 ResolutionProof1; actual F/H/O commits only | Preserve separate legacy-v2, raw Legacy-on-v3 and codec8 Resolution routes. Dedicated Legacy3 F/H/O/G/Q surfaces exist; default K still rejects relevant Legacy3 cohorts. Additional chains and broader source cohorts are not generally accepted. |
| V10 transport/recovery — dormant | `v10Transport.ts`, `v10Recovery.ts`, `v10MixedRecovery.ts`: complete local inventory, exact received interval, earliest pending event, gaps, source witnesses and supported binding | J verifies existing inbox and committed interval; K invokes atomic owners, may advance a local qualified prefix | Reuse within exact accepted cohorts. J is not an HTTP receiver, and K is not a complete production dispatcher. Never replace default binding with the most permissive dormant binding. |
| Maps — NATIVE | `cloud/mapSyncRuntime.ts`, Rust `map_sync.rs` / `map_codec.rs`: retained inbox, parents, Metadata/Stage authority, map/node/Note-link identities and conflict rules | `cloud_map_events`, `cloud_map_apply_ledger`, owner/projection state and exact received ciphertext | Shared codec can run in Web. Browser apply owner/storage adapter is absent; native `invoke()` cannot be wired into Web. Share the existing owner planning logic, then prove browser parity. |
| Documents — NATIVE | `cloud/documentSyncRuntime.ts`, Rust `document_sync.rs` / `document_codec.rs`: retained inbox, document scope/parents, Metadata/Stage proofs, valid Tiptap structure/extensions | `cloud_document_events`, `cloud_document_apply_ledger` and projection/owner state | Local v12 Tiptap documents are not server owner evidence. Need shared native owner kernel plus browser transaction/projection adapter; no plaintext document API. |
| Progress — NATIVE | `cloud/progressSyncRuntime.ts`, Rust `progress_sync.rs`: parents/facts, Metadata unit and Stage ancestry, conflicts and exact event identity | `cloud_progress_events`, `cloud_progress_apply_ledger`, derived chains/projection | Port the owner boundary through shared planning code, retaining fact/amount/causal validation. Do not derive history from current UI totals. |
| Project/Account Game — NATIVE | `cloud/gameSyncRuntime.ts`, Rust `game_sync.rs`: authenticated Progress/Metadata/Stage and project/account actions, stable reward IDs, deduplication, rules and compensation dependencies | `cloud_game_events`, `cloud_game_apply_ledger`, atomic project/account projections | Need shared owner computation and browser durable adapter. Replay must not grant rewards again or run outbound compensation/writer flows. Account Game uses account crypto, project Game uses project crypto. |
| Account catalog — NATIVE | `cloud/accountObjectReader.ts`, `accountCatalogRuntime.ts`, Rust `account_catalog.rs`: folder/order/membership/project-order ancestry, folder/project coverage and present authority | `cloud_catalog_events`, `cloud_catalog_apply_ledger`, account inbox and catalog state | A real native apply owner exists; authentication-only probe deliberately returns no apply authority. Need browser equivalent using shared owner logic, including cross-family dependencies; cannot omit account events. |
| Cover material — not composed in Web | Metadata cover reference, `projectCoverReference.ts`, `projectCoverCrypto.ts`, encrypted cover API and native cover repository | Existing native cover/reference authority; no accepted complete Web cover lifecycle | Reuse crypto/reference validation. Any referenced unavailable/unverified cover blocks the full-project claim until a browser owner is accepted. Do not drop it from Metadata. |

Native ledgers contain canonical frames/projections. Copying those plaintext SQL
layouts to IndexedDB is forbidden. Future browser adapters must retain original
AEAD wire and encrypt every content-bearing derived record using existing AMK
object/local-source encryption, with strict account/entity/revision ownership.
Each new family's local record layout needs its own reviewed schema/validator;
this document does not manufacture a generic proof version for all families.

## 3. Server-to-browser replay and states

```mermaid
flowchart TD
  A[Auth, legal gate, AMK lease, registered device] --> B[Fresh registry R0, transport epoch, target cursor T]
  B --> C[Pull complete account pages from zero]
  C --> D[Atomic original-wire inbox and receive cursor]
  D --> E[Verify complete inventory and bootstrap cohorts]
  E --> F[Existing owner prepare: AEAD, dependencies, source]
  F --> G[Single native IDB transaction: CAS, projections, proof, inbox]
  G --> F
  G --> H[Reauthenticate all outcomes and complete coverage through T]
  H --> I[Fresh registry R1, transport and applicable server gates]
  I --> J[Publish current in-memory project view at T]
  C --> K[Blocked or interrupted; no project-open result]
  E --> K
  F --> K
  H --> K
  I --> K
```

Proposed generation states are `receiving`, `received`, `applying`,
`locally_verified`, `blocked` and `interrupted`. A durable phase marker is a
resume hint. Final online validation and permission to expose plaintext are
short-lived session state, checked against auth/key/device/generation and server
evidence; never persist a trusted `ready` or `project_open` flag.

Receive cursor, owner-applied coverage and existing C21 `proven_prefix` remain
distinct. A receive cursor proves only committed staging. Coverage is a derived
summary of genuine owner outcomes; it is not an ACK token or a replacement for
C21 prefix certificates. `ack_cursor` is never advanced by this contract.

## 4. A — Complete source inventory

1. Acquire the production replay writer lease for the account/profile; capture
   the current auth context, canonical user, stable device identity, key lease
   and a new cache generation. Device registration remains explicit through the
   existing identity-only owner. Do not change device identity to evade own-echo
   rules. With missing identity/permission or a closed gate, return the real
   blocker before replay; no automatic registration, cutover or declaration.
2. Fetch and validate the current bootstrap registry R0 and transport mode/epoch.
   Pin `T=R0.current_cursor`. Current v3 mode is required; do not reinterpret v3
   responses as v2. A legacy/initializing/missing lineage is unsupported unless
   a separately accepted owner establishes it. `CloudProjectService.disable()`
   currently refuses deletion of bootstrap-managed projects; absence of a row
   is not evidence of an accepted project deletion.
3. Pull the account feed using existing authorized v3 parsers, initially
   `since=0`, with bounded pages (initial maximum 100 items). Preserve the exact
   accepted wire-item serialization, envelope, nonce, ciphertext, descriptor,
   receive protocol and sequence. Legacy events returned by v3 retain that
   receive identity. Their original submission transport may be unknown.
4. Require dense sequences `1..T`, unique event IDs and sequence keys, exact
   `next_cursor`, progress and consistent `has_more`. Never pre-filter by project,
   account family, tombstone, codec or error. An event beyond T, changed snapshot
   or unexplained terminal page invalidates this attempt; do not trim a page to
   simulate a stable snapshot. Existing API has no atomic multi-page snapshot.
5. Every received page and its receive-cursor update commit in one strict cache
   transaction. A duplicate is accepted only as an exact replay of the retained
   interval through its accepted transport owner. Same ID/sequence with changed
   wire is corruption. Do not broaden J's latest-interval replay rules to admit
   arbitrary older pages; restart the generation if no accepted join exists.
6. At T validate all account projects/bindings and the exact initial Note cohort
   against origin/count/max from the active bootstrap registry. Authenticate the
   Metadata genesis and every relevant ciphertext via the real owners. Origin
   for the initial cohort differs from later legitimate peer devices. A received
   descriptor supplies the server's source-device association; formats carrying
   an authenticated device field must match it. Legacy payloads without that
   field do not acquire an invented one. No device-list/signature API is assumed.
7. Bound network bytes, retained inventory and prepared post-state before
   allocation/commit. Initial product admission stays at the current preview's
   200 account events / 32 MiB ciphertext, further restricted by existing owner
   limits (including 16,384 rows/store and 32 MiB aggregate planner inventory).
   Ciphertext and planner/JSON sizes are different budgets; all must pass.
   Larger histories return a resource blocker with no completeness claim.

Registry and server ordering are trusted transport authority under the existing
threat model. AEAD authenticates content and its established domain, not a signed
global log. Dense sequence plus rechecks detect missing/inconsistent data against
the server's declared cursor; they do not prove absence of malicious server
rollback/equivocation on a fresh profile. Stored hashes are consistency joins,
not new cryptographic source authority. No stronger guarantee is introduced.

## 5. B — Proof lifecycle and transaction boundary

Owners alone create applied proofs. A downloaded event starts as `received`;
successful AEAD/codec parsing is not an applied outcome. An owner-bound opaque
plan pins the exact generation, scope, immutable wire, registry/bootstrap,
dependencies, source inventory/revision, auth context and AMK lease. Follow each
existing owner's private-token rules; a public diagnostic DTO, manifest bit or
caller-supplied proof never authorizes commit.

Crypto, hashing, full planning and encryption happen outside IndexedDB's live
transaction. Inside one physical strict read/write transaction, re-read identity,
generation and the complete required account inventory, perform exact CAS and
recheck owner invariants, then synchronously schedule the owner's projection,
history/head, source revision, applied proof and inbox transition together.
Mixed-source owners retain the complete account-store CAS required by their
accepted contracts. Do not replace it with a family-only filtered view. No
network, decryption or asynchronous hashing occurs inside the transaction.

Resolve success only on transaction completion, through the existing
`runBrowserTransaction()` semantics or its shared extracted helper. Request,
quota, validator, CAS and durability failures abort the whole owner transition.
Fresh encrypted values prepared with random nonces cannot be compared against a
recomputed ciphertext to infer earlier success. After a lost response, reopen
the original wire and committed source/history through the owner and return
`already_applied` only for the exact, completely joined outcome.

An event or a contract-defined bootstrap batch is atomic. The whole account is
not one huge transaction. Intermediate committed events remain hidden from the
project view until complete account coverage and final online validation pass.
No independently committed proof sidecar may claim a source write that failed.

## 6. C — Composition and source initialization

Use one orchestrator around the existing account transport and owners, with
explicit dispatch by actual receive protocol, operation, authenticated family
and codec version. It owns scheduling and lifecycle only. It must not implement
another causal engine, duplicate owner decisions, produce proofs, or call
writer/migration `begin` methods as a shortcut to initialize a read target.

Process the earliest unqualified sequence and stop on a gap or unsupported
route. Authenticate the complete inventory without making later application a
way to bypass an earlier blocker. Dependencies must be qualified by their real
owners; a read-only scan can inspect later ciphertext but cannot invent an
applied dependency or advance the coverage frontier. No generic family sorting,
speculative topological reordering or arbitrary offset retry is authorized.

Bootstrap source creation is a separate private owner seam with this bounded
contract, derived from Z1's server evidence. Admit an active bootstrap, one
supported coverless ordinary Metadata genesis with active status, its exact
initial Legacy Note cohort, and an otherwise empty cache source/history/outbound
state for that project. Verify the complete account history and Note-ID ownership
first. Legacy/initializing lineage, unsupported genesis fields, an initial fork
or additional source material outside the uploaded cohort blocks seeding.

Map genesis to the receiving source exactly as Z2A: `id=project_id`, supported
`name`, `goal`, `infinite`, `unit`, `status`; `created_at=updated_at` from the
authenticated genesis timestamp; `payload={}`. Start with empty membership and
local source revision 1. Unsupported absent fields are not inferred. This Note
source base is distinct from the current Metadata UI projection; subsequent
Metadata events remain with their own owner. A source revision is local order,
never a copied sender counter or server cursor.

The proposed private replay-seed owner authenticates registry/cohort/genesis and
prepares the encrypted empty source using the existing local-source validation
and sealing helpers. One strict transaction CASes the entire generation/input
inventory, asserts no project source/history/outbound data already exists, and
adds that source plus a technical seed reference in the replay manifest. The
reference pins bootstrap, genesis event and cohort boundary; it is rederived
from original server evidence on every reopen. A digest/reference alone grants
no source authority. This is a genuine source-initialization transaction, not
an applied Metadata/Note proof, and changes no event state or qualified cursor.
Do not invoke the public local CRUD initializer or accept a caller's seed DTO.

Then apply initial and subsequent Notes in actual account order using the real
Legacy/Content owners and shared Z2B1/B2/B2C source/causal/historical kernels.
Each event atomically commits its own source, history and inbox outcome. A crash
may retain a partly replayed source only inside the unpublished production-cache
generation; it is inaccessible as a user project or Q grant until complete
reconciliation. Generation privacy is part of the transaction adapter contract,
not a hidden UI button. A partial source can never be exposed through local CRUD.

Initial Legacy Notes may precede Metadata in real bootstrap logs. The seed may
authenticate that later genesis without applying it or manufacturing a Metadata
dependency proof. Legacy owners must accept this exact receiving-source cohort
under the new seed contract and genuine-producer tests before activation.
Content/Stage dependencies still require their real applied owner evidence;
if an earlier event needs a later applied dependency, return
`bootstrap_order_unsupported`. No family prepass bypass is authorized.

This isolated, unpublished, resumable seed contract is new design work. It does
not relax Z2A's atomic B import into the existing local workspace or grant its
Q handoff: Z2A's clean B virtual-inventory/batch owner remains unimplemented and
keeps its atomicity/eligibility requirements. Do not use this cache-specific
seed to replace it or to authorize legacy workspace source writes.

Resolution dispatch keeps raw Legacy-v2, raw Legacy-on-v3 and codec8 Resolution
distinct. An existing-device retained F2/v3 join is read-only, not fresh apply
authority. Dedicated Legacy3 owners must independently accept the actual
inventory; default K's refusal remains. Unsupported additional resolutions,
source cohorts, own authorship and self echoes without genuine receipts stop.
An empty compatibility outbox is not a fabricated receipt/source publication.

For native-only families, extract a shared storage-independent owner planning
core used by the existing Desktop path and the browser adapter. Rust-only cores
need a browser execution boundary, such as compiling that shared core to Wasm;
that build decision requires its own bounded feasibility slice. Keep crypto and
durable commit at the existing platform boundaries. Independently rewriting the
same rules in a second TS reducer is not an accepted implementation. SQL ledgers
are implementation evidence, not ready-made portable proof DTOs.

Full project exposure requires a supported owner outcome for every event through
T across the account, complete dependency/source closure and no unresolved
blocker. A preserved conflict remains evidence and a recovery barrier, never an
arbitrary winning value. Tombstones remain in history and are handled only by a
qualified deletion owner; a deleted selected project cannot open as live. All
references, account catalog and cover material needed by the view must be
verified. Only then may a future distinct full-project result be returned for T;
today's `metadata_only` result retains its restricted meaning.

## 7. D — Minimum browser durability and schema decision

Use the separate database `worta-web-replay`, initial schema version 1, scoped
by canonical account/device; slice 1 now implements the receipt subset above.
The full owner design extends a technical
`replayManifest`, keyed by local account ID/device, binds that ID to the canonical
user and records schema/reader-contract version, generation,
registry snapshot/T, mode/epoch, source seed references, phase and receive cursor. These fields bind CAS
and resumability, not authenticity or readiness. One generation is writable at
a time under the existing account/key lifecycle and a dedicated Web Lock.

Reuse existing identity/binding, inbox, owner-head, Note-history and encrypted
source record validators/keypaths through the transaction adapter. The C21
compatibility stores expected by complete inventories include `outbox`,
`receipts` and `legacyNoteIntents`, but read-only replay creates no outbound
records, receipts or user intents. Never alias any store to the developer DB.
Existing owner `account_id` keys retain their local-account meaning; never
substitute a canonical user ID into those keys. Technical identity may be
mirrored via the current identity service; copying
legacy project/content/proof rows is prohibited.

The minimum durable data is original received ciphertext, receive progress,
owner-required encrypted derived source/projections and history, genuine owner
heads/applied proofs, and the generation manifest. Original envelopes retain
their crypto/AAD domains and bytes. Derived content uses existing AMK encryption
and strict account/project/entity/revision checks. Titles, text, HTML, canonical
plaintext frames, search indexes, AMK, passwords and auth tokens cannot appear
in persistent replay storage, logs or diagnostics. Persist no new independent
key. Future native-family adapters require encrypted record schemas before use.

All cache stores and manifest live in the same DB so owner commits and generation
checks share a physical transaction. A new generation may replace only this
dedicated reconstructible cache after its schema/identity is verified, the view
is revoked and concurrent writers are excluded. Reset only the current account's
cache rows and manifest atomically; do not clear other accounts' stores or the
legacy DB, and do not alter unknown/newer schemas. Rebuild
has no unsent user changes to lose because read-only cache writes cannot accept
user edits. Cache absence/eviction is a normal requirement to reconnect/replay.

| Database | Required change for this contract's implementation |
| --- | --- |
| Desktop SQLite | No migration. Native owner-core extraction must preserve current transactions and schema. |
| Existing `worta-web` IndexedDB v12 | No upgrade, record conversion, import or cleanup. Keep version12 and historical refusal checks. |
| Separate `worta-web-replay` IndexedDB | Initial receipt schema1 is now implemented under the explicit slice-1 authorization; this is a new database, not v12-to-v13. Later family schemas require explicit versioning/upgrade/refusal plans. |
| Production PostgreSQL | No migration or API/wire change required for the bounded active-bootstrap replay contract. Existing server gates stay mandatory. Unsupported legacy/lineage histories stop; broadening them may require a separate contract and cannot be assumed here. |

Schema discovery must be strict. An unknown version, partial/corrupt schema or
unsupported record stops before writes. Do not automatically downgrade/delete
an unknown cache. Initial schema tests include fresh creation, rejected malformed
schema, interrupted initialization, exact reopen and older-client refusal;
no historical upgrade test is claimed until a real prior schema exists.

## 8. E — Restart, failures and final online validation

| Condition | Required action |
| --- | --- |
| Refresh/restart | Authenticate/unlock again; fetch fresh registry/mode and gates; reauthenticate retained wire, source/proofs and coverage. No cached plaintext or phase flag alone permits opening. |
| Interrupted receive/apply | Reconcile exact committed page/owner interval and resume only from accepted durable outcomes under fresh evidence. If T/registry/epoch changed, block/rebuild a generation; never append an unverified suffix to stale authority. |
| Crash or lost result during transaction | Native atomicity leaves either the old state or complete owner outcome. Reconcile it; do not replay writes blindly, allocate replacement proof authority or double-apply rewards. |
| Missing page/parent/object, unexpected later dependency | Keep the earliest blocker. Fetch/retry only through an accepted account replay/owner recovery route; no project-filtered dependency request or synthetic record. No progress means explicit stop, not a retry loop. |
| Network error/offline | Abort online validation, revoke the project-open result and show a connection failure. Cache is not an offline fallback. No saved/synced status is implied. |
| Corrupt AEAD, wire mismatch, foreign account/project/device field, orphan proof | Reject, expose no partial view, and do not repair by deleting the offending event. Rebuild only the dedicated cache under its explicit rebuild policy; server ciphertext is unchanged. |
| Unsupported family/version/generation, legacy lineage, cover, tombstone or conflict | Preserve the specific blocker and original ciphertext. No fallback codec, transport relabel, generic proof, skip or false empty project. |
| Lock/logout/account switch/key or identity revocation | Abort HTTP and active transactions, invalidate all private plans/currentness, clear plaintext and UI handles. Return no late success even if a transaction completed just before revocation; its cache must be reconciled on reopen. |
| Quota/transaction/storage failure or eviction | Atomic rollback or cache absence; report failure. No fallback to localStorage, developer DB, memory-only applied proof or successful-save label. |
| Second tab/new schema | Web Lock plus full CAS prevents competing commits. An incompatible client refuses the replay database without altering it. |

Before exposure re-fetch registry R1 and transport epoch; require equality with
R0/T and current session/lease/generation. Recheck applicable existing read-only
gate endpoints and let actual pull enforce its recipient-device gates. Changed
evidence invalidates publication. These requests are not a distributed transaction:
the result describes verified state **at T**, not a promise the server cannot
change after the final request. Continuous changes cause bounded retry/failure.

## 9. F — Device, compression and release boundaries

Current server `SyncService.pull_encrypted()` enforces registered recipient,
transport mode, sticky compression support and applicable recipient Note/Map/
Document/Progress capability requirements over account history. Existing family
and compression GET gates report all-device readiness for their own contracts;
they are not a complete device list, user-content proof or blanket permission
for all families. Do not invent an extra pull gate for a family merely because
its GET gate exists. Check each actual server contract when adding its owner.

ID0/ID1 frames are processed only after AEAD, through existing bounded frame
normalization/owner decoders. Retain original ciphertext; decoded normalization
never relabels transport or changes persisted wire. Unknown compression, bomb,
trailing/concatenated stream and codec/version failures reject as today.

Capability declarations advertise supported reader contracts and cannot be
inferred from account replay success. Conversely, a registered/capable device
does not prove that this account was completely applied. The current negative
`BrowserNoteReaderReadiness` remains unchanged. Its production dispatch, replay,
orphan/tombstone/further-chain/own-source/all-device blockers must be closed by
genuine producer/consumer acceptance before any future declaration task. New
browsers whose retained histories require such declarations stay blocked until
that work is accepted. There is no read-only pull bypass in this contract.

No PUT capabilities/reader-ready, ACK, auto-bootstrap/cutover, push, cloud writer,
ordinary local editor write or outbound Game effect is authorized. Keep
`ready=false`, `declarationAllowed=false`, `writerAuthorized=false`, Registration
CLOSED, PUBLIC RELEASE BLOCKED; C21/C22/C23/PF6.0/RC remain mandatory.

## 10. Small implementation slices and acceptance

At the design baseline all slices below were future work. The implementation
record above now covers slice 1 only. Each requires focused LOCAL-FIRST
tests first, relevant regressions/typecheck/build/lint, real Chromium for changed
browser flows and disposable PostgreSQL16 for API integration. Keep six CI jobs
and their budgets; place bounded new tests in existing appropriate groups after
measuring duration. No capability/gate activation is implicit in these slices.

| Order / slice | Minimum change | Acceptance and stopping boundary |
| --- | --- | --- |
| 1. Isolated replay storage and receiver | New approved replay schema/transaction adapter, generation/identity binding and paged account receiver using existing API/parsers; no owner composition | Genuine producer ciphertext, two projects/account events, multiple pages, exact receive/replay, gap/duplicate/mutation/version/limit checks, real Chromium restart/abort/quota/rollback and unchanged v12 bytes. All applied proofs absent; ACK/push/capability calls absent. No project-open result. |
| 2. Metadata owner composition | Bind real imported Metadata owner to replay transactions with generation and full-inventory guard | Genuine producers, exact heads/proofs and restart reconciliation; corrupt/header/bootstrap/foreign-device mismatch, stale registry/context, conflicts/cover/delete limits reject. Remains labelled Metadata-only. |
| 3. Structural and clean source foundation | Stage/StageOrder adapters; private cache-only replay-seed owner from section 6, then real per-event Note owners | Qualify real Metadata/Stage dependencies; exact StageOrder membership and rejected deletes/forks; seed/cohort origin, mapping and revision joins; restart at each commit, initial Legacy Notes before Metadata, no partial generation exposed or Q authority. Later applied dependencies block; Z2A workspace rules remain intact. |
| 4. Mixed Note/Resolution dispatch/recovery | Compose accepted Legacy/Content/F/H/O/G/Q owners and exact transport joins; implement only one remaining documented cohort per task | Genuine v2/v3/Legacy3/codec8 producers, several projects, conflicts/parents/source witnesses, restart and no relabeling; unresolved/further/own chains block. Close each readiness blocker separately; no declaring support from a narrow passing cohort. |
| 5. Native family owner cores/adapters | One family per task: shared core extraction and browser execution/storage feasibility, then account catalog, Documents/Maps, Progress and Game in actual dependency order | Desktop behavior and real producer outputs match; owner parity/negative cases, encrypted browser records and atomic ledger/projection/reward joins. Cannot count a codec or Tauri mock as browser owner support. |
| 6. Complete read-only project publication | Coverage/closure for every encountered family and auxiliary material, stable server checks, correct UI and lifecycle | Real Chromium/FastAPI/PostgreSQL server replay, cold cache and restart, all required project data restored; mixed unsupported account history blocks; network has no plaintext/ACK/push/declaration. Full-read acceptance still does not authorize writer or release. |

After slice 1's local/independent acceptance, the next minimum implementation
is **slice 2**, the real imported Metadata owner composition and compatibility
guard. It must retain Metadata-only semantics. Recommended model:
**GPT-6 Sol / High**. Native shared-core feasibility and any positive Note
capability lifecycle are separate later tasks, never hidden inside storage work.

## 11. Contract review references and verification

- [Online-Only architecture](WEB_ONLINE_ONLY_ARCHITECTURE.md) and `AGENTS.md`
  product policy define source authority and separate approval for new stores.
- [C21 browser persistence](C21_BROWSER_PERSISTENCE.md),
  [post-F structural routing](C21_POST_F_STRUCTURAL_ROUTING_CONTRACT.md) and
  [mixed source authority](C21_MIXED_PROJECT_SOURCE_AUTHORITY_CONTRACT.md)
  retain original owner/CAS/proof rules.
- [Z1 server baseline feasibility](C21_2_08Z1_SOURCE_BASELINE_FEASIBILITY.md),
  [Z2A atomic replay](C21_2_08Z2A_ATOMIC_REPLAY_CONTRACT.md),
  [Z2B1 source kernel](C21_2_08Z2B1_LOCAL_SOURCE_KERNEL.md),
  [Z2B2 causal kernel](C21_2_08Z2B2_CAUSAL_PLANNER_KERNEL.md) and
  [Z2B2C historical planner](C21_2_08Z2B2C_HISTORICAL_PLANNER.md) distinguish
  implemented shared planning from the unimplemented virtual source/batch owner.
- [Legacy3 H](C21_2_08U_LEGACY3_H_CONTINUATION.md) and
  [Legacy3 O/Q](C21_2_08Y_LEGACY3_O_Q_IMPLEMENTATION.md) preserve explicit
  cohort admission and default-path refusals.
- Code audit includes `backend/app/cloud/services.py::pull_encrypted`,
  `pull_encrypted_v3`, `CloudProjectService.disable`, actual browser owners in
  `frontend/src/platform/web`, native runtimes in `frontend/src/cloud`, and
  Rust owner transactions/ledgers in `frontend/src-tauri/src`.

For the original 02B documentation task, design consistency review, local
Markdown link/path checks and `git diff --check` passed; runtime tests, Chromium,
PostgreSQL and migrations were NOT RUN at that design baseline. Subsequent
slice-1 runtime checks are recorded separately above/in checkpoint, without
claiming full-project implementation or remote acceptance. Official Web progress
remains **89.36%**.
