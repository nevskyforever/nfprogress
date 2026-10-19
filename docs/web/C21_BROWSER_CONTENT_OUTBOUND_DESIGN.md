# C21.2.05 — Browser Content outbound authority and self-echo contract

## C21.2.08 — pre-implementation audit / STOP (2026-10-19)

Baseline: clean branch6.0 at local/origin
`67135b15d7de2ba8f256ab13abece09393a35a1d`; the docs-only VPS release gate at this
baseline is preserved. C21.2.07 was independently accepted by the owner: SHA
`a0e248c7b22d0b707f6f2e3e488708612964a2fa`, Cloud `39167228308` SUCCESS, 6/6 jobs.

The code audit confirms the format and local cryptographic building blocks are
present: authenticated I2/source through `authenticateContentIntent2`; strict C3 v3
shape and C3 authorship AEAD through `authenticateContentCandidate3`; ordinary-v1
payload inside canonical codec8/frame1; ID0/ID1 bounded compression primitives;
crypto1/AAD1 Note object encryption; protocol3 single Note/event body validation;
immutable outbox1 raw_body; reserved dense ordinal; source-token/history/head CAS;
forced Metadata dependency authentication; and current auth/key/session checks.
Stored C3 alone remains outside receipt, self-echo, proven-prefix and ACK authority.

**STOP before functional edits:** the current browser reader declaration verifies
generic transport mode and declares only `compression_id1`. Browser Note-family
reader declaration and its all-device `noteReaderGate` are absent from browser
composition; the existing family API is used by native Tauri `ContentNoteRuntime`.
The `compressionWriter` response only authorizes compression ID1. There is no
existing browser Content writer authorization or explicit writer activation token.
Reusing either generic compression authority or the native caller would violate the
frozen gate and browser-only scope. A test boolean would manufacture positive
authority. No safe I2→C3 transition can be prepared under the current contract, so
this slice made no production, test, Chromium, workflow, or schema changes. No new
wire format or migration was introduced. No tests were run because no code changed;
CI was not polled. Official progress84.0%, C21/C21.2 IN PROGRESS, ready=false.

The next design decision must provide a genuine browser Note writer gate and a
browser-local way to prove Note reader declaration/currentness while keeping normal
application composition dormant. Until then C21.2.08 is audit-only and blocked.

**C21.2.05 REMOTELY ACCEPTED — DESIGN ONLY.**
C21.2.05 REMOTELY ACCEPTED — DESIGN ONLY: SHA `86641d80c00305f9756c1d9fce8a2f7e81977ccc`,
Cloud `39153860372` SUCCESS, all six required jobs SUCCESS (owner supplied).
Date: 2026-10-18. Branch: `6.0`. Audited baseline:
`13b9ff7b5ef6bfed97f40b563f426aea07f440d1` (`test(c21): audit content self echo authority`).
C21.2.04 is **REMOTELY ACCEPTED — AUDIT ONLY**: Cloud `39066576774`,
SUCCESS, all six required jobs SUCCESS (owner supplied). Its Content self-echo
implementation remains BLOCKED; acceptance did not activate a writer.

At the C21.2.05 baseline all contracts below were proposed; current implementation
status is recorded in the C21.2.06/C21.2.07 sections. Writer/self-echo/Resolution remain disabled, `ready=false`.
Official progress84.0%; C21/C21.2 IN PROGRESS; C21.1 ends at C21.1.30;
C21.1.06 NOT LOCAL COMPLETE. No roadmap points. No production, migration, test,
browser-script, workflow, dependency, native or backend edits in C21.2.05.

## C21.2.07 — Canonical Content source / atomic intent2 / dormant ownership

**REMOTELY ACCEPTED** (2026-10-19; owner supplied). Implementation SHA
`a0e248c7b22d0b707f6f2e3e488708612964a2fa`, Cloud `39167228308` SUCCESS, 6/6 required
jobs SUCCESS. Continuation baseline `67135b15d7de2ba8f256ab13abece09393a35a1d` is preserved.

`contentNoteIntents.ts` adds an explicitly constructed internal dormant runtime;
BrowserPersistence/user composition/startup/UI do not select or expose it. It reuses
localAuthority's writer hook and canonical encrypted localNotes/localProjects.
A single strict T_mutate includes source, membership/source_revision, authenticated
intent_format2/I2 and the shared allocation cursor. Crypto is outside IDB. Exact
source-token, full account inventory/cursor, binding/owner history, same-Note head,
prior intent/generation, inbox/outbox/receipt and auth/key/session CAS precede writes.
A failed request, abort or invalidated context preserves the old state and ordinal.

Initial support: explicit clean active import_remote/captured project HTML, stage=null,
source_type=project, no map/node fields and existing Content metadata admission.
Genuine absent Note genesis allocates UUID4/revision1/parent null/ordinal once;
existing unbound local Notes cannot be rebranded as genesis. Handover uses the exact
single authenticated linear head with matching canonical source; every earlier local
candidate must have accepted immutable outbox/receipt and proven Legacy self-echo.
Peer Content alone never chooses the writer. Pending Legacy, group1/local versions,
forks, unresolved received evidence and C3 sealed lifecycle block same-Note writing.
Other eligible Notes continue, including Legacy intent1, on the common dense ordinal.

Metadata dependencies come from prepareMetadataPrefix(force=true), original AEAD
and an exact active bootstrap/head; pinned covered ancestors remain pinned during
coalescing. Same-operation unsealed upsert I2 coalescing authenticates its prior envelope/source,
preserves event/parent/cloud revision/ordinal, increments generation and local edit/
source counters independently, and resets retry diagnostics. First deletion of an
eligible clean live head is supported. Pending create→delete/update→delete,
resurrection, cancellation, repeated delete of an existing tombstone and sealed-event
coalescing remain blocked. Authenticated historical Legacy self-echo/peer Content
replay remains read-only after I2 handover; new received mutations still cannot
overwrite an outstanding I2.

I2 is the writer claim, not a second mutable Note store. Legacy writer and raw
source-only edits cannot overwrite I2/C3-owned Notes. No ownership Boolean, validator
weakening, peer/Legacy conversion or conflict winner. No C3/outbox/R2/P2/inbox9 producer,
codec8 framing/compression selection/outbound ciphertext, upload, HTTP endpoint,
self-echo/Resolution activation or prefix/ACK change. IndexedDB remains9, same12
stores/indexes/key paths; no migration. Existing v8→v9 compatibility gate retained.
Official84.0%; C21/C21.2 IN PROGRESS; C21.1 ends .30; .06 NOT LOCAL COMPLETE; ready=false.

### Простыми словами

I2 хранит зашифрованный снимок незавершённой Content-правки и её постоянные event,
parent, cloud revision и ordinal. Заметка, состав проекта и намерение сохраняются
одной транзакцией: после сбоя остаётся либо прежний набор, либо целиком новый.
Повторная совместимая правка обновляет снимок и поколение того же намерения;
новое событие и номер очереди не создаются. После перезапуска I2 снова проверяется
текущим ключом. Обычные Legacy-заметки сохраняют свой writer, а возврат Content
к Legacy запрещён. Runtime вызывается только явно в тестовом стенде; пользовательский
Content writer и отправка ещё выключены. C21.2.08 пока остановлен на аудите:
браузеру требуется отдельное подтверждённое Content writer полномочие; этот этап
не начат функционально.

Validation: **65 focused producer/atomicity/coalescing/handover/security tests PASS**
(two new mandatory specs). Existing targeted Legacy/peer/mixed/prefix regressions:
**599 PASS / 20 files**. Mandatory affected C21 suite, including all accepted .06
format/migration coverage: **1795 PASS / 61 files**. Native Chromium: **238 case groups
PASS, page errors0**; seven .07 groups exercise genuine producer I2, every source/
intent/cursor write abort, exclusive writer lock, renderer + disk reopen, coalescing,
clean peer handover/read-only historical replay, existing mixed group blocker,
auth/key invalidation and independent Legacy/Content ordinals. New scenario HTTP0;
overall existing134 expected API requests unchanged, push/pull/Resolution0. The initial
new test's re-entrant logout wait was corrected; final full browser run PASS.
Typecheck and production Vite build PASS (existing non-blocking bundling warnings).
Workflow YAML, both new mandatory spec entries/path filters, helper syntax and
`git diff --check` PASS. No remaining failures or skipped required checks; no new
migration, dependencies, native/backend builds or CI polling. Protected .pyc unchanged.
C21.2.07 is REMOTELY ACCEPTED: SHA `a0e248c7b22d0b707f6f2e3e488708612964a2fa`, Cloud `39167228308` SUCCESS, 6/6 required jobs SUCCESS (owner supplied).
Expected Actions: Cloud backend tests YES; SQLite sync substrate NO. CI NOT POLLED.

## C21.2.07 — pre-implementation production audit (2026-10-19)

Baseline/local/origin `198f50df429bddbb398ac7572d2834a950fa7d02`, branch6.0,
clean preflight; protected bytecode hashes recorded and retained. The full accepted
.05 design and implemented .06 formats were read before production changes.

| Audit question | Actual production finding / bounded implementation decision |
|---|---|
| 1 canonical content | localNotes encrypted local_format1, localProjects encrypted membership/source_revision; keep both. |
| 2 Legacy ownership | BrowserNoteIntentRuntime binds localAuthority.withNoteWriter; no automatic Content selection. |
| 3 source transaction | localAuthority.write asserts source token/membership and identity index, writes project+Note, resolves at native strict transaction completion. |
| 4 Legacy allocation | prepareMutation/scheduleMutation reserve shared event/ordinal; same-event generation coalescing and full inventory CAS; keep identity contract. |
| 5 I2 | Separate exact validateContentIntent2 and authenticateContentIntent2 decrypt intent_format2 plus source; hashes alone are insufficient. |
| 6 existing guards | Legacy prepareMutation/prepareSeal reject I2/C3. Raw source-only mutation also needs an ownership guard to prevent overwriting an outstanding I2. |
| 7 dormant composition | A standalone Content runtime can reuse the writer hook without adding any BrowserPersistence property, UI import, startup or background producer. |
| 8 atomic commit | Narrow structural writer hook accepts source token; reuse existing source write with intent/history/cursor/binding/outbox/receipt/inbox plus ownerHeads in SAME transaction. Crypto stays outside. |
| 9 dependency authority | prepareMetadataPrefix(force=true) authenticates retained Metadata ciphertext/history; verifiedMetadataSequences plus exact active binding/head supplies a current tip or covered pinned ancestor. No supplied UUID authority. |
| 10 conflicts | Retained group1/local versions, non-linear frontier and unresolved same-Note inbound evidence block handover/mutation; no conflict conversion. Other Notes stay eligible. |
| 11 tabs | Existing exclusive session Web Lock excludes another tab; strict source/inventory/cursor CAS handles competing asynchronous plans in one session. No new lock. |
| 12 invalidation | Current normal-user context, bound account and AMK lease after awaits and write callbacks; auth invalidation aborts transaction, session close aborts tracked transactions. |

Implementation will admit only explicit clean project HTML import_remote handover
or genuinely absent Note genesis; authenticate each causal candidate and final peer/
Legacy proof, require all earlier same-Note local events accepted and self-echo proven,
compare canonical source to authenticated head, and preserve pinned I2 identity.
No C3/outbox/R2/P2/inbox9 creation, frame/compression selection, HTTP, migration,
production writer activation, Resolution or ACK change. Official84.0%, ready=false.

C21.2.06 REMOTELY ACCEPTED: SHA `198f50df429bddbb398ac7572d2834a950fa7d02`, Cloud `39162803233` SUCCESS, 6/6 required jobs SUCCESS (owner supplied).

## C21.2.06 — Browser Content durable formats / IndexedDB v9

**REMOTELY ACCEPTED** (2026-10-19).
C21.2.05 REMOTELY ACCEPTED — DESIGN ONLY: SHA `86641d80c00305f9756c1d9fce8a2f7e81977ccc`,
Cloud `39153860372` SUCCESS, all six required jobs SUCCESS (owner supplied).

Current database **v9**, migrated from v8 as a compatibility/format gate. Exactly
12 stores, unchanged key paths/indexes; no additions/deletions/recreation/downgrade.
Versionchange validates the complete old schema (including multiEntry=false), old
scope/record allowlists, source/history/receipt/ordinal/cohort joins and structural
prefix/ACK constraints, without crypto or HTTP awaits. Existing rows are not rewritten;
structural failures abort and preserve the v8 profile. Cryptographic authenticity
is separately checked after unlock, never inferred from a SHA-256 digest.

Read-only foundation: exact Content intent2, own candidate3, authenticated receipt2,
separate self-echo proof2 and inbox9. New format/authentication/inventory validators
are in contentAuthorityRecords.ts, contentAuthorityAuthentication.ts and
contentAuthorityInventory.ts; keyless old-state gate in contentAuthorityMigration.ts.
Version dispatch retains existing peer candidate2/proof1/conflict1/2 and Legacy
candidate1/intent1/head1/group1/local_version1 contracts. Shared allocation counts
both live intent versions. New evidence is authenticated before protected consumers
use it; unrelated Legacy paths retain their own source and frozen wire semantics.

No production producer creates I2/C3/R2/P2/inbox9. Legacy writer cannot take over a
Content-owned candidate/intent. P2/inbox9 is recognized but remains **unqualified**:
no new prefix certificate, no self-echo activation and no ACK crossing. Candidate3
cannot become a new group1 local member or synthetic peer candidate. Existing
Legacy mutation/seal/upload/self-echo and peer/mixed Content flows remain protected.
No Content writer/sealer/uploader, Resolution, backend/native or dependency activation.

Official84.0%; C21/C21.2 IN PROGRESS; C21.1 final canonical slice C21.1.30;
C21.1.06 NOT LOCAL COMPLETE; ready=false. No roadmap points.

### Простыми словами

Браузерное хранилище получает версию9 и строгие правила будущих записей Content.
Существующие заметки и история при миграции не переписываются. Старый v8-клиент
не может открыть v9: он не понимает новые форматы и должен безопасно отказаться.
Если старая структура или данные повреждены, upgrade прерывается, исходный v8
сохраняется. Проверка шифрования выполняется отдельно после разблокировки ключа.
Content writer, отправка Content, собственное Content self-echo и Resolution ещё
выключены; даже новый proof не даёт пройти ACK. Следующий ограниченный C21.2.07 —
канонический источник и атомарное локальное Content intent/ownership без активации
отправки. Полная Web-синхронизация ещё не готова.

Validation: pre-bump keyless v8 preflight 15 PASS; final format/migration focused
69 PASS (50 format/negative/read-only tests + 19 migration tests); affected Legacy,
peer/mixed Content and prefix/ACK regressions 640 PASS / 20 files. Native Chromium
231 case groups PASS, page errors0; nine v8/v9 variants cover populated sealed and
accepted profiles, exact ciphertext/source/history preservation, interrupted upgrade,
malformed schema/index, corrupt old record, cryptographic failure after unlock,
future-version rejection, old v8 VersionError and full profile restart. Migration
variants make zero API requests; existing overall suite has134 expected API calls,
zero push/pull/Resolution/unrelated API calls. Existing prefix61/ACK61 and own Content
barrier62 survive migration/reopen. Mandatory affected C21 suite **1730 PASS / 59 files**;
post-type-fix focused + initial capture **100 PASS / 3 files**. Typecheck and production
Vite build PASS (non-blocking existing bundling warnings); workflow YAML, mandatory
suite inclusion, helper syntax, path filters and git diff --check PASS. Initial stale
schema assertions, shared corruption-fixture mutation and two type errors were fixed;
no unresolved failures. No native/backend builds; protected .pyc hashes unchanged.
Expected Actions: Cloud backend tests YES; SQLite sync substrate NO. CI NOT POLLED.

The original numbered design below remains the authoritative lifecycle contract.
Its source inventory and "current v8" statements describe the accepted .05 baseline;
C21.2.06 now implements its read-only formats and v9 gate. Producer/activation
requirements in .07–.11 remain future work. No proposed field allowlists changed.

## 1. Existing authority inventory

Paths are relative to this document. Symbols in this table exist at the audited SHA.
This is a source audit, not evidence that proposed records already pass validators.

| Existing source | Actual contract / relevant symbols |
|---|---|
| [persistence.ts](../../frontend/src/platform/web/persistence.ts) | WEB_DATABASE_VERSION=8; SCHEMA has12 stores; openBrowserPersistence holds exclusive `worta-web:writer` Web Lock for the session; runBrowserTransaction uses strict durability and resolves only on transaction completion. |
| [localAuthority.ts](../../frontend/src/platform/web/localAuthority.ts) | BrowserLocalAuthorityRuntime.readSnapshot/withDecryptedSnapshot, withNoteWriter, prepareProtectedNoteApply; source-token CAS and one encrypted project membership/Note source. Current writer hook is typed for Legacy. |
| [localAuthorityRecords.ts](../../frontend/src/platform/web/localAuthorityRecords.ts) | LocalNoteRecord1/LocalNotePayload local_format1; validateLocalNote, validateContentLocalNote, validatePersistedLocalNote and validateLocalNoteRecord. Persisted Content reading already supports project/Stage HTML/plain; ordinary local mutations remain narrower. |
| [noteIntents.ts](../../frontend/src/platform/web/noteIntents.ts) | BrowserNoteIntentRuntime.prepareMutation/scheduleMutation/prepareSeal/commitSeal; openSnapshot and authenticateIntent. Intent1 authenticates identity using an encrypted local JSON payload; commitSeal atomically removes intent, inserts candidate1/protocol2 outbox1 and advances head. |
| [noteIntentRecords.ts](../../frontend/src/platform/web/noteIntentRecords.ts) | BrowserNoteIntent1, validateNoteIntent, sealFailureState; exactly one intent per Note via unique index; ordinal identity reserved durably. |
| [noteUnsealedVersion.ts](../../frontend/src/platform/web/noteUnsealedVersion.ts) | freezeLocalVersion/openFrozenLocalVersion preserve an immutable Legacy intent1 generation for group1; not a generic Content snapshot format. |
| [noteHistory.ts](../../frontend/src/platform/web/noteHistory.ts) | makeHistoryCandidate/openHistoryCandidate/nextNoteHead/commitHistoryChange: exact original wire, immutable candidates, parent chain, append-only retained evidence and head CAS. |
| [noteHistoryRecords.ts](../../frontend/src/platform/web/noteHistoryRecords.ts) | candidate1 Legacy; candidate2 peer Content; head1; group1; local_version1 embeds Legacy intent1. validateNoteHistoryRecord/Set enforce parent revision and frontier membership. |
| [legacyNoteApply.ts](../../frontend/src/platform/web/legacyNoteApply.ts) | BrowserLegacyNoteApplyRuntime.prepareContentOrdinary shares causal planner, but calls Content prerequisite before own logic. requireOwnReceipt is structural and is not Content authorship. |
| [noteTransportPrerequisite.ts](../../frontend/src/platform/web/noteTransportPrerequisite.ts) | prepareNotePrerequisite rejects own Content with unsupported_local_source; prepareNoteTransportCommit creates peer candidate2 only. |
| [noteTransport.ts](../../frontend/src/platform/web/noteTransport.ts) | openNoteTransport authenticates original codec8 wrapper, device/header and route; does not relabel it as Legacy. |
| [contentNoteRecords.ts](../../frontend/src/platform/web/contentNoteRecords.ts) | BrowserContentNoteProof1 is peer applied only; validateContentNoteProof rejects own device; conflict proof1/2 inherit peer constraints. |
| [contentNoteProof.ts](../../frontend/src/platform/web/contentNoteProof.ts) | contentHistoryJoin/verifyStoredContentNoteProof require peer candidate2, immutable original transport and historical ancestry. |
| [contentNoteConflictProof.ts](../../frontend/src/platform/web/contentNoteConflictProof.ts) | contentConflictHistoryJoin/verifyContentGroup/verifyContentLocalAdmission authenticate existing peer or frozen Legacy branches, including post-seal history. No Content-local writer branch exists. |
| [contentNotePrefix.ts](../../frontend/src/platform/web/contentNotePrefix.ts) | prepareContentNotePrefix binds exact inventory and rechecks Content dependencies; only existing peer outcomes qualify. |
| [syncDurability.ts](../../frontend/src/platform/web/syncDurability.ts) | BrowserOutboxRecord1 sealed/accepted, BrowserUploadReceipt1; validateBrowserSealedBody, validateBrowserUploadPair, prepareBrowserUploadAcceptance and BrowserSyncDurability.commitUploadAcceptance. Generic wire storage is not a producer. Inbox wrapper versions1–8 are occupied. |
| [projectBindings.ts](../../frontend/src/platform/web/projectBindings.ts) | validateBrowserProjectBinding fixes account/device/project/bootstrap and eligible lineage; upload_existing cohort is separately frozen. |
| [provenPrefixRecords.ts](../../frontend/src/platform/web/provenPrefixRecords.ts) | calculateBrowserPrefix authenticates via runtime certificates then walks every server sequence; unsupported or missing events remain barriers. |
| [provenPrefix.ts](../../frontend/src/platform/web/provenPrefix.ts) / [ackPrerequisites.ts](../../frontend/src/platform/web/ackPrerequisites.ts) | BrowserProvenPrefixRuntime.prepare/commit/prepareAck/ackOnce plus inspectBrowserAckInventory: full inventory CAS, registration/reader/registry/mode gates, no-progress zero HTTP; one common ACK. |
| [readerCapability.ts](../../frontend/src/platform/web/readerCapability.ts) / [deviceRegistration.ts](../../frontend/src/platform/web/deviceRegistration.ts) | BrowserReaderCapabilityRuntime.declare and BrowserDeviceRegistration bind exact current auth/device. Existing browser reader token declares compression support, not Content writer authority. |
| [contentNoteCodec.ts](../../frontend/src/cloud/contentNoteCodec.ts) | frameContentNote/unframeContentNote/validateContentNote: codec8, frame1, codec-version1; ordinary inner event1 and separately readable Resolution2. |
| [frameCompression.ts](../../frontend/src/cloud/frameCompression.ts) | selectWriterFrame/compressCanonicalFrame/normalizeAuthenticatedFrame: bounded ID0/ID1, existing selection policy and no persisted-frame fallback. |
| [canonicalReaders.ts](../../frontend/src/platform/web/canonicalReaders.ts) | openBrowserCanonicalObject decrypts before decode/decompression and checks account/project/Note/event identity. |
| [encryptedSyncProtocol.ts](../../frontend/src/cloud/encryptedSyncProtocol.ts) / [noteSyncCodec.ts](../../frontend/src/cloud/noteSyncCodec.ts) | createNoteSyncPlaintext/validateNoteSyncPlaintext distinguish ordinary mutation and causal header; Legacy eligibility remains narrower. |
| [objectCrypto.ts](../../frontend/src/crypto/objectCrypto.ts) / [encoding.ts](../../frontend/src/crypto/encoding.ts) | encryptObjectBytes/decryptObjectBytes and encodeObjectAad: frozen object crypto1/AAD1 with user/project/entity/type identity; fresh nonce for each new encryption. |
| [encryptedSyncV3.ts](../../frontend/src/api/encryptedSyncV3.ts) | parseV3Pull/parseV3PushResponse, noteReaderCapabilities/noteReaderGate and compressionWriter. encodeV3MetadataPush excludes Note; it is not a Content upload encoder. |
| [projectMetadataMigrationRuntime.ts](../../frontend/src/cloud/projectMetadataMigrationRuntime.ts) | requireMode3/compressionFrame show native runtime's authoritative mode and account compression-gate pattern; cannot instantiate it as a browser storage adapter. |
| [contentNoteRuntime.ts](../../frontend/src/cloud/contentNoteRuntime.ts) | ContentNoteRuntime.beginNotes/sealNotes/uploadNotes call native IPC/storage; no Browser IndexedDB producer. Static upload call uses pushMetadata, whose current encoder rejects note/event: do not copy this call into Web. No runtime/native repair performed here. |
| [content_note_writer.rs](../../frontend/src-tauri/src/content_note_writer.rs) | normal/begin/pending/seal/receipt use SQLite writer_events, candidates, shared outbox/event_objects and upload receipts. Compare immutable frame/generation before seal. |
| [content_note_sync.rs](../../frontend/src-tauri/src/content_note_sync.rs) | receipt/ready retain native inbound evidence; exact existing own frame/object can recover native acceptance after lost response. Browser does not inherit that recovery rule or data. |
| [schemas.py](../../backend/app/cloud/schemas.py) / [sync_v3_router.py](../../backend/app/cloud/sync_v3_router.py) | V3SyncEventEnvelope permits note/event; encrypted_push returns event_id/server_sequence/duplicate via existing protocol3. No server schema or receipt semantics change proposed. |

## 2. Missing browser authority

Missing: a browser-only producer that atomically binds a canonical local mutation,
reserved event/ordinal, authenticated intent, exact sealed codec8 candidate and
outbox before any upload; then retains authenticated acceptance and own-echo proof.
Native SQLite tables, same-account peer candidates, generic enqueue and a server echo
cannot create that origin retrospectively. No migration may manufacture such records.

There are two additional integration gaps: the browser currently has no Content
writer gate/composition, and the public metadata push encoder does not accept Note.
Neither requires changing codec8, crypto/AAD or the server protocol. A future
browser-specific adapter must validate/send the **already stored** raw protocol3
Note body. Re-encoding through metadata or Legacy is forbidden.

This design deliberately limits the first future activation to clean project HTML
ordinary-v1 Notes in an active import_remote/captured binding. The record contract
can describe existing project/Stage HTML/plain routes, but Stage/plain production
writing, initial Content capture, upload_existing handover and mixed-conflict Content
writing are not automatically authorized. No mindmap, Resolution or full-Web claim.

## 3. Proposed durable record contracts

**Four new top-level record variants**, plus the new inbox wrapper for one of them.
No separate working-source store, frozen Content version, outbound-binding store or
accepted-binding store. Version numbers below are reservations in this design only;
C21.2.06 reserves and validates these exact versions; production creation remains disabled.

Notation: S=(canonicalUserId, accountId, deviceId); H is the existing canonical
SHA-256 helper noteProofDigest, not a MAC; E is existing LocalEnvelope crypto1/AAD1.
All fields have exact allowlists, bounded canonical JSON and safe integer/UUID checks.
A new local event_id is UUID4 from crypto.randomUUID; never derived from content.
Every E uses the existing Note object context
`{userId:S.canonicalUserId, projectId, entityId:note_id, entityType:'note'}`.
New local payload discriminators are not new crypto/AAD domains or wire codecs.

### I2 — Content local intent, record_version=2

Store `legacyNoteIntents`, existing key `[account_id,event_id]` and Note/ordinal
unique indexes. Exact proposed top-level fields:

```text
record_version=2, transport_kind='content_note_v1',
account_id, device_id, project_id, note_id, bootstrap_id, event_id,
operation ('upsert'|'delete'), revision, parent_event_id, updated_at, deleted_at,
local_ordinal, mutation_generation,
dependencies {bootstrap_id,metadata_event_id,stage_event_ids},
snapshot: LocalNoteRecord1, snapshot_digest, intent_envelope: E,
seal_state, seal_attempt_count, last_error_code, next_attempt_at=null
```

I2 is a separate validator, not an accepted value of validateNoteIntent1. Its
snapshot uses the **same** local_format1 encrypted source, decoded with the existing
Content source rules rather than Legacy-only openSnapshot. Snapshot contains no
plaintext Note. Intent metadata and dependencies are authenticated inside
`{intent_format:2, identity:I2 without retry fields and intent_envelope}` under E.
Require account/device/project/Note/bootstrap identity, snapshot digest and plaintext
snapshot/header mutation agreement. Retry fields are diagnostics only; they never
supply authority. Existing sealFailureState classification may be reused unchanged.

### C3 — own Content sealed candidate, record_version=3

Store `legacyNoteHistory`, key `[account_id,project_id,note_id,'candidate',event_id]`;
existing unique event index also applies. Exact proposed fields:

```text
record_version=3, record_kind='candidate', record_id=event_id,
account_id, device_id, project_id, note_id, bootstrap_id, event_id,
source_device_id=device_id, protocol_version=3,
transport_kind='content_note_v1', origin='local_sealed',
codec_id=8, frame_version=1, codec_version=1, compression_id (0|1),
header: ordinary NoteSyncHeader,
intent: frozen I2 (including its encrypted snapshot and intent_envelope),
wire_item: exact outbound {event,object} JSON without receive-only device/sequence,
wire_digest, raw_body_digest, logical_digest, authorship_envelope:E, record_digest
```

No server sequence, peer transport_proof, current projection pointer or peer applied
outcome. `wire_digest=H({protocol_version:3,item:parsed wire_item})`;
`raw_body_digest=H(the exact raw_body string)` binds whitespace/property ordering too;
`logical_digest=H(authenticated ContentNoteEvent)`; record_digest hashes C3 excluding
itself. Let B be C3 excluding authorship_envelope and record_digest. Authorship
payload is exactly `{content_outbound_format:1, kind:'sealed_authorship',
candidate_body_digest:H(B)}`. Thus an editable SHA digest alone cannot mint C3.
Authenticate E, frozen I2, source snapshot, the exact encrypted frame and header;
validate that all describe the same mutation/generation/dependencies. Retain I2
inside C3 before deleting its mutable store entry. This supplies the frozen source
needed for provenance without defining Content local_version2 or group semantics.

### R2 — Content upload receipt binding, record_version=2

Store `receipts`, existing key `[account_id,event_id]` and unique server_sequence
index. Exact proposed fields:

```text
record_version=2, owner_kind='content_note_acceptance',
account_id, device_id, event_id, protocol_version=3, server_sequence, duplicate,
candidate_digest, wire_digest, acceptance_envelope:E, receipt_digest
```

The receipt's scalar fields retain the existing server meaning. Its E plaintext is
`{content_receipt_format:1, receipt:baseReceipt1, candidate_digest, wire_digest}`,
where baseReceipt1 is the exact existing v1 receipt shape constructed from the
validated authenticated push response. receipt_digest=H(R2 without receipt_digest).
This is a **local authenticated binding**, not a server signature or changed server
receipt. Project/Note/AAD context comes from the exact matching C3; identity must
match both decrypted payload and scope. A fake accepted outbox plus a structurally
valid receipt1 cannot qualify Content. Valid R2 must authenticate against C3.

### P2 — Content self-echo proof, record_version=2

Separate type, proposed `BrowserContentNoteSelfEchoProof2`; separate validator.
It does not extend or reinterpret BrowserContentNoteProof1.

```text
record_version=2, owner_kind='content_note_self_echo', outcome='acknowledged',
account_id, device_id, bootstrap_id, protocol_version=3,
reference: original V3Descriptor, server_sequence,
codec_id=8, frame_version=1, codec_version=1,
header: ordinary NoteSyncHeader, mutation ('create'|'update'|'delete'),
history_event_id, candidate_digest, wire_digest, receipt_digest, outcome_digest
```

Require `reference.device_id=device_id=S.deviceId`, original wrapper operation event,
exact C3/R2 and positive matching sequence. No source_revision/local_note_digest,
projection outcome, conflict group or generation. outcome_digest=H(P2 excluding
itself), a consistency checksum; full C3/R2 AEAD authentication is always required.

Proposed inbox wrapper9 has **exactly** received-row scope/event/sequence/protocol/
wire fields plus `record_version=9`, `state='content_note_self_echo_proven'` and
`content_note_self_echo_proof:P2`. Original wire_item is unchanged. Proof2 and inbox9
are two serialization layers for one new proof, not new stores.

### Reuse and validator compatibility

| Existing contract | Reuse unchanged / required dispatch |
|---|---|
| LocalNoteRecord1/local_format1 and LocalEnvelope | Reuse source/envelope shapes and cryptography; new producer must enforce Content admission. Existing Legacy mutation eligibility does not expand. |
| validateLocalNoteRecord, validateContentLocalNote, validateBrowserProjectBinding | Reuse unchanged after correct route and scope selection. |
| frameContentNote/unframeContentNote, canonical reader, compression functions, parseV3Pull/parseV3PushResponse, validateBrowserSealedBody | Reuse frozen wire/crypto checks. They do not mint authorship. |
| BrowserOutboxRecord1 | Unchanged fields/states; protocol3 original raw_body. Content-specific validator additionally joins C3. Generic enqueue cannot mint C3. |
| prepareBrowserUploadAcceptance | Reuse response validation to create baseReceipt1 in memory. |
| validateBrowserUploadPair | After R2 authentication, validate an in-memory baseReceipt1 view against outbox1. Do not persist that view or let receipt1 substitute for R2. Current helper does not accept R2 directly. |
| validateNoteIntent | v1 remains unchanged and rejects I2. New top-level version dispatcher required. |
| validateNoteHistoryRecord/Set, openHistoryCandidate | Current versions1/2 reject C3. Future dispatch adds a separate authenticated C3 branch; old leaf semantics and peer device restrictions stay intact. Shared ancestry traversal must understand C3 without forging candidate1/2 views. |
| BrowserContentNoteProof1/conflict proof1/2, candidate2 | Peer-only permanently; unchanged bytes and meaning. |
| validateBrowserInboxRecord | Current wrappers1–8 do not admit9. Add a distinct wrapper9/P2 branch in v9, without relabeling own wire as peer. |
| Receipt1 / generic commitUploadAcceptance | Legacy behavior remains; a new Content acceptance transaction writes R2. Current generic method writes only receipt1 and cannot be used as the Content authority commit. |
| head1, group1, frozen local_version1 | Preserve shape/semantics. Head frontier may include authenticated C3 via new version dispatch. Existing groups remain Legacy/peer contracts; no Content-local member is invented. |

Account-wide bulk readers currently map every intent/receipt/history row through old
validators. They require explicit v9 dispatch before calling unchanged leaves,
including unrelated Legacy notes and historical prefix verification. The shared
ordinal invariant counts all outbox rows plus both live intent versions exactly
once. Filtering away I2 before checking contiguity is unsafe. This is integration
work, not a claim that current Legacy runtime already reads the new variants.

## 4. Local Content intent lifecycle

| State (derived unless stated) | Durable evidence / permitted transition |
|---|---|
| No Content ownership | No I2/C3; existing Legacy behavior continues until an explicit eligible handover transaction. |
| Unsealed | I2 + matching canonical local mutation, reserved ordinal/event; no outbox/C3/R2. Same-operation coalescing increments generation with same event/revision/parent/ordinal. |
| Sealing interrupted | Same unsealed I2 after aborted preparation/transaction; no durable sealing flag or incomplete outbox is legal. No upload was allowed. |
| Sealed | C3 + identical outbox1 state sealed, I2 removed atomically. Frame choice/nonce/ciphertext immutable; no same-event coalescing. |
| Upload in flight / outcome unknown | Durable state remains sealed. HTTP state is ephemeral; reopen resends the exact raw_body. |
| Accepted | C3 + outbox1 accepted + authenticated R2, committed together. Receipt alone cannot create the origin. |
| Self-echo proven | Accepted chain + exact retained own inbox9/P2. No Note/head/group writes. |

No retry allocates a replacement event or ordinal. Do not delete blocked I2 and
leave a hole. Creation followed by deletion before first seal, resurrection, or a
change of operation/route/parent is explicitly blocked in this minimal design;
there is no implicit cancellation/reallocation or emitted-delete-without-genesis.
A later separately accepted design can add cancellation semantics.

Seal policy/errors may change diagnostics only. Coalescing resets error diagnostics
for the new generation after authenticating the previous generation and CAS. Once
sealed, even a now-preferred compression algorithm cannot change that event.

## 5. Canonical source and causal head

The only mutable Note content is the existing encrypted `localNotes` row, with
`localProjects` encrypted member_ids/source_revision. Snapshots in I2/C3 are immutable
historical evidence, never a second working source. No native import or parallel
Content document store is proposed.

Distinguish three counters: project source_revision is a CAS generation; local
Note note_revision tracks local edits (and existing remote apply can reset it);
cloud header.revision is derived from authenticated causal history. They are not
interchangeable. For genesis use revision1/parent null; otherwise parent is the
unique verified linear head and revision=parent.revision+1. Bounds/overflow fail.
No timestamp/LWW, max-revision guess or peer event chosen as winner.

Proposed T_mutate reads/validates scope, binding, encrypted source token, membership,
full Note history/frontier, open groups, pending intents, outbox/receipt lifecycle
and allocation cursor. It prepares new encrypted canonical source plus I2 outside
IDB; one strict readwrite CAS transaction commits localProjects/localNotes + I2 +
next_local_ordinal together. Source-only mutation without its intent is forbidden
for a Content-owned Note. New Note creation inserts one new account-unique Note and
membership atomically; it never rebrands a pre-existing unbound local Note as a
new cloud genesis. Existing unbound Notes need their already-supported Legacy
capture/bootstrap path; no new initial Content cohort is designed here.

**Ownership handover:** explicit selection at the first eligible Content mutation,
not inference from receiving peer Content. Initially require import_remote/captured,
active same bootstrap, supported project HTML route, authenticated single head,
source matches that head (or genuine new Note), no open group/retained conflicting
input, no live Legacy intent, and all earlier same-Note local events accepted and
self-echo proven. Do not drain/migrate Legacy automatically; complete its existing
lifecycle first. An active upload_existing cohort cannot be altered by this design.

I2 is the durable one-Note writer claim until it is replaced atomically by C3;
retained C3 in ancestry latches Content ownership thereafter, even if a later head
is a peer candidate2. No extra ownership boolean/record is needed. Shared composition
routes exactly one writer; it never tries Legacy after a Content failure. Existing
Legacy eligibility, intent1 sealing, wire bytes and self-echo semantics remain
unchanged for Legacy-owned Notes. Future inventory dispatch/ownership guarding is
required around these existing contracts, not a silent expansion of intent1.

Conservatively allow only one outstanding local event per Content Note: while its
head is sealed, in flight or accepted-awaiting-echo, a new local mutation is blocked.
After verified R2/P2, another I2 may use that head even if an earlier unrelated
server-sequence barrier still prevents ACK. Historical self-echo replay must remain
valid after descendants/new local text, without comparing to the current projection.

## 6. Codec8 framing / compression / encryption

From authenticated I2 snapshot obtain a Content-local source via local_format1
checks and validateContentLocalNote; remove only the local edit revision from the
wire Note. Create the existing ordinary NoteSyncPlaintext (inner version1) with
reserved header, then ContentNoteEvent wrapper version1 containing canonical user,
exact local device and pinned dependencies. Bootstrap and metadata_event_id come
from authenticated active lineage/Metadata history, not user input. Stage references
are sorted/unique and refer to the exact admitted Stage; first activation has none.
Metadata/Stage movement may retain authenticated ancestor coverage, never silently
replace dependencies or route in an existing intent. A lost/deleted/incompatible
lineage blocks sealing.

Use frameContentNote: WORTA-C1 magic, frame1/codec8/version1. Never send a Legacy
upsert descriptor for that frame: outbound descriptor is protocol3 Note operation
`event`, deleted_at null, including for an inner tombstone. Original header still
contains its ordinary upsert/delete mutation and parent.

Future browser writer gate must require current normal-user auth + exact bound local
device registration, authoritative mode3 (no automatic cutover), actual browser
Note reader declaration and successful noteReaderGate, current lineage/Metadata
proof and explicit writer activation. Existing browser compression-reader token is
not a Note-writer token; native NOTE_READER_SUPPORT is reference only. A failed
Note-reader gate blocks all Content emission; it does not allow a Legacy fallback.

Use selectWriterFrame and existing bounded policy. ID1 requires the existing
account compressionWriter authorization (`ready=true`, missing_devices=0) and current
reader declaration. Unknown/negative compression authorization selects ID0 **before
seal**; stale auth is a hard failure. Compression is inside E2EE: select frame first,
then encryptObjectBytes with the frozen Note object context, crypto1/AAD1.
Authenticate/decrypt before inspecting/decompressing any retained frame. Validate
wrapper/account/device/dependencies/header and exact frame compression marker against
C3. Apply existing local/codec/JSON/transport/size limits; reject oversized aggregate
intent/candidate/envelope before transaction, never truncate data.

Only encrypted object, bounded identity/header metadata and hashes are persisted.
No plaintext frame, Note content/title/tags/checklist, decrypted snapshot, access
or refresh tokens, AMK or key lease is stored in authority records/diagnostics.
Hashes are not encryption or a privacy promise for guessable content; retain only
needed existing canonical digests. Wipe temporary buffers where current utilities
support it; JavaScript object/string lifetime is not a guaranteed secure erase.

## 7. Atomic sealing and outbox creation

Prepare outside IDB: fresh auth/key lease and writer gates; authenticate I2/snapshot,
causal history and dependencies; frame/compress/encrypt once; validate saved outbound
body with validateBrowserSealedBody; build authenticated C3 with frozen I2. New
browser adapter serializes one protocol3 Note item with exact property allowlists.

T_seal scope: localProjects/localNotes, projectBindings, ownerHeads, legacyNoteHistory,
legacyNoteIntents, outbox, receipts, inbox, cursors. Re-read exact source token,
I2 generation/envelope, head/frontier/groups, dependencies and captured inventory;
require no competing same-event authority. Atomically add C3 and outbox1 sealed,
advance existing head1 by CAS, delete I2. Ordinal stays reserved; cursor does not
allocate it a second time. No source/projection rewrite during seal.

WebCrypto/HTTP awaits are outside IDB scheduling. Commit only in the strict
transaction's oncomplete, not request success. Abort/error/quota/session revocation
leaves I2/source and all other stores unchanged. Idempotent retry accepts only an
already stored exact C3/outbox pair; otherwise conflict, never replace a candidate.

Event/parent/revision/ordinal become immutable at the first T_mutate allocation;
within an unsealed event only explicitly CAS-coalesced generation/payload/timestamp
may change. Logical frame/compression/nonce/ciphertext become immutable at successful
T_seal. Crypto prepared in memory but never committed/emitted can be discarded after
an aborted seal and prepared anew from the still-unsealed I2; that is not an upload
retry. No network emission is allowed before T_seal. After it, every retry reads the
same raw_body; no reframing, recompression, nonce generation or replacement event.
A later compression/mode-gate change blocks incompatible sending rather than
rewriting persisted bytes.

## 8. Upload acceptance and receipt

Future explicit browser sender loads/authenticates C3 and sealed outbox, verifies
scope/gates, and posts its stored raw_body to the existing protocol3 push endpoint.
Use a dedicated validated Note raw-body adapter and parseV3PushResponse. Do not use
encodeV3MetadataPush/pushMetadata, reserialize byte arrays, instantiate native
ContentNoteRuntime, or widen metadata allowlists to masquerade as another family.
Server schema already supports Note/event; server receipt semantics stay frozen.

After authenticated HTTP success and exact single-event response, prepare R2 using
the current lease and C3. T_accept rechecks C3/exact outbox/receipt/inbox/sequence
uniqueness/scope/current guard; atomically stores R2 and outbox state accepted.
It includes legacyNoteHistory for C3 CAS as well as outbox/inbox/cursors/receipts.
No Note/head/group write or prefix movement. Reuse existing response parsing and
v1 pair checks via the validated base view, not the existing generic receipt1 write.

First accepted receipt is immutable, including its original duplicate diagnostic.
A duplicate response with same event/sequence returns the existing R2 unchanged;
conflicting sequence or ciphertext fails closed. A response is not a signed proof:
trusted browser code observes authenticated HTTPS and seals the local binding.

Crash after server success but before T_accept leaves outbox sealed. Resend identical
bytes; server's existing idempotent duplicate receipt supplies the same sequence,
then T_accept commits. If echo arrives first it remains received/unqualified until
R2 exists. Unlike the native lost-response shortcut, Browser does not derive R2
from that echo in this minimal design. Receipt1 or accepted flag alone is insufficient.

## 9. Own Content self-echo proof

Future separate prepare path: authenticate original retained codec8 ordinary-v1
wire, require wrapper device exactly S.deviceId and account identity exactly S;
load independently existing C3, accepted outbox1 and R2. Authenticate frozen I2,
C3 authorship E, exact encrypted wire/raw-body digest and R2 acceptance E. Join:

```text
scope account/device/project/Note/bootstrap
  == I2 identity == C3 identity == decoded original Content wrapper
C3 event/header/revision/parent/dependencies/compression
  == authenticated intent and exact decrypted original frame
H(outbox.raw_body string) == C3.raw_body_digest
outbox event/protocol/raw_body item == C3 outbound wire
incoming item after removing ONLY receive device_id/server_sequence
  == C3 outbound wire (no header operation rewrite)
R2 event/device/protocol/candidate_digest/wire_digest
  == accepted outbox and authenticated C3
R2.server_sequence == incoming.reference.server_sequence
```

Additionally validate full causal ancestry, supported route, current auth/key lease
and same active bootstrap. Historical dependencies must remain authenticated and
covered; incompatible/deleted lineage blocks new proof. Do not require current
localNotes to equal the old frozen source: newer local work is not echo authority.

T_echo includes inbox, history, outbox, receipts, binding and dependency anchor stores.
Recheck the exact prepared inventory/current guards and atomically replace only the
received row with wrapper9/P2. It writes no localProjects/localNotes, head, candidate,
intent, group, receipt or outbox. It does not increment source revision or conflict
generation, choose a winner, or generate another outbound event. Exact historical
replay returns already_proven with zero writes. Changed wire, missing C3/R2 or
wrong device/sequence is rejected; another device of the same account stays peer.
Existing own Content fixtures from C21.2.04 remain blocked, not backfilled.

## 10. Conflict interaction

Existing group1, local_version1, peer candidate2 and Content conflict proof1/2 remain
unchanged. A group is not closed and a winner is not chosen by writing or self-echo.
Existing Legacy-origin mixed conflict mutation/seal/self-echo behavior remains intact.

New Content handover, mutation and sealing are blocked while an unresolved group
exists for that Note. A group appearing after prepare invalidates CAS. Do not insert
I2 into local_version1, cast C3 to candidate2, or increment group generation for an
echo. Other independent Notes may continue if their own gates pass.

A peer sibling/fork that would require preserving a new Content-local branch is
retained in inbox as received and remains a prefix barrier. While I2 or an unconfirmed
C3 exists, a competing same-Note peer event cannot overwrite canonical source.
Retain both local evidence and incoming encrypted wire; block further writes/seal
when causal state is ambiguous. Safe exact own acknowledgment can still prove its
already emitted event without resolving that peer fork. Clean peer descendants
may use the shared history dispatcher only after the local parent is authenticated
and accepted/self-echo proven, with no open fork/pending mutation.

A Content-local mixed-conflict preservation extension would need additional frozen
version/member/proof contracts. **STOP that extension**; it is not hidden in these
four formats, not an automatic future activation prerequisite to be assumed done.
Existing supported peer-only and Legacy-local mixed flows remain regression gates.

## 11. Prefix / ACK integration

Proposed self-echo certificate is private, lease-bound and anchored to the exact
inbox/history/outbox/R2/binding/dependency inventory. Only full C3/R2 verification
can expose qualified sequence numbers; P2.outcome_digest or a public boolean cannot.
Add a separate self-echo certificate input to runtime preparation, structural prefix
calculation and ACK inventory. Existing peer Content certificates stay peer-only.

Version dispatch must cover new formats across full account snapshots, including
old peer proofs whose head ancestry now contains C3. Historical proofs keep their
original bytes; C3 adds authenticated ancestry, not a new peer applied outcome.
Unproven own events always cap the contiguous walk. Missing sequence or unsupported
family cannot be skipped even if a later own event is proven. An invariant failure
under an already committed prefix is corruption: stop ACK, never silently lower it.

Prefix commit and prepareAck/ackOnce retain their full inventory CAS, registration,
reader/registry/high-water/authoritative-mode gates and one existing ACK transport.
No upload receipt alone moves prefix; no proof alone sends ACK; no-progress sends
zero HTTP; no automatic loop, ready or cross-family barrier change is proposed.

## 12. Multi-tab, auth and key lifecycle

Reuse session-wide exclusive `worta-web:writer` Web Lock, ifAvailable:true; a second
session gets writer_busy. Do not invent a second lock that permits two producers.
Strict IDB transaction CAS remains necessary for overlapping async plans inside the
same session and for direct storage changes. Index uniqueness is additional defense,
not a replacement for authentication or full expected-old comparison.

Preparation captures immutable scope/current auth context, device binding, session
and current account lease. Recheck after every await, before HTTP, at transaction
scheduling and request callbacks; abort active transactions on logout/switch/key
revocation/session close. Database versionchange closes the old session. Serialize
all event/ordinal allocation through the same account cursor transaction.

Do not persist auth epochs, leases, tokens or writer-ready flags as reusable authority.
On reopen, derive current identity from existing browser provisioned identity and
fresh normal-user binding, unlock the correct key, authenticate retained records,
then reacquire gates. Never mint a replacement device merely to salvage a record.
Old HTTP completion after account switch cannot commit R2; the correct later
session may retry the same sealed bytes and obtain duplicate acceptance safely.

## 13. Crash recovery and corruption behavior

| Failure / crash | Required reopened behavior |
|---|---|
| Before/during T_mutate | Neither source+intent nor ordinal is partially committed; retry from fresh source token. |
| Coalescing/crypto preparation interrupted | Existing I2 generation survives; authenticate and CAS before retry. No transient frame had upload authority. |
| Between C3/outbox writes inside T_seal | Whole transaction aborts; I2 remains. Never expose sealed-half state. |
| After T_seal before HTTP / while HTTP in flight | Original C3/outbox survives; send identical raw body, no new event/crypto. |
| Server success before/during T_accept | Outbox remains sealed until complete; duplicate retry obtains receipt. |
| Accepted outbox but missing R2 / R2 without C3 | Impossible legal transaction result; corruption, block upload/echo/ACK. Do not repair from server echo or mutable source. |
| Echo before receipt | Received retained barrier; get HTTP duplicate receipt first. |
| During T_echo | Received or fully proven wrapper9, never partial proof; replay no source writes. |
| Old echo after newer working text/descendant | Authenticate historical chain and return acknowledgment/replay only; keep new projection and head. |
| Hash/AEAD/identity/sequence/parent mismatch | Keep encrypted evidence, report bounded error, block affected operation and ACK if safety cannot be proved; do not auto-delete/reseal. |
| Full valid old profile restored | Local validation cannot generally detect rollback of an entire previously valid profile without an external freshness anchor. Do not claim anti-rollback protection. |

Legal state is derived from rows; there is no durable upload_in_flight flag whose
loss can authorize a resend with different bytes. No unsupported automatic garbage
collection, candidate pruning, receipt replacement, ordinal compaction or ownership
reset. Recovery never copies native authority or fabricates proof from peer data.

## 14. Migration decision

| Option | Advantages | Disadvantages / profile impact | Safety constraints and recovery |
|---|---|---|---|
| 1 — keep v8, add new record variants | No DB version upgrade or extra stores. | Old v8 opener validates the same physical schema and may enter a profile before encountering unknown records. Old bulk readers cannot dispatch I2/C3/R2/inbox9; writer-ownership isolation is not guaranteed at open. | Would need a universal pre-open feature barrier understood by already released v8 clients; none exists. Reject for this design; no heuristic record cleanup/downgrade. |
| 2 — v9 format gate, same physical stores/indexes | Old v8 client fails VersionError/unsupported_version before accessing the new profile. Explicit one-way acceptance boundary; existing unique Note/event/ordinal/sequence indexes reused. | Upgrade prevents opening that profile with v8 even before writer activation; all account-wide readers need new dispatch. Upgrade/reopen acceptance required. | Validate old schema and structural retained invariants atomically; preserve all old bytes; crypto verification after unlock before authority use. Abort upgrade on structural corruption; no generated provenance. **RECOMMENDED.** |
| 3 — separate authority DB/store family or other minimal format gate | Separate new writer data can be isolated by name; avoids adding variants to some old readers. | Separate database breaks one-transaction source/intent/outbox atomicity and old source ownership safety. An extra store still needs v9 because current validateSchema requires exact stores/indexes. Additional per-Note ownership/source format adds complexity. | Cross-DB recovery/reconciliation would require a larger protocol. A new-store variant also needs explicit versioning and more migration coverage. Reject; no dual canonical sources. |

**Option2 selected: C21.2.06 implements the v9 format gate, with no writer activation.** This is
an intentional format/old-client exclusion decision, not a claim IDB physically
requires a version bump just to hold JSON. Current v8 remains correct for its barrier.

Exact proposed v9 physical schema is the current SCHEMA, **12 stores, zero additions
or index changes**:

| Store | Key path | Indexes (U=unique) |
|---|---|---|
| identities | canonical_user_id | local_account_id U; device_id U |
| accountBindings | local_account_id | canonical_user_id U |
| outbox | [account_id,event_id] | ordinal [account_id,device_id,local_ordinal] U; state [account_id,state,local_ordinal] |
| inbox | [account_id,server_sequence] | event [account_id,event_id] U; state [account_id,state,server_sequence] |
| cursors | [account_id,device_id] | none |
| receipts | [account_id,event_id] | server_sequence [account_id,server_sequence] U |
| projectBindings | [account_id,project_id] | bootstrap [account_id,bootstrap_id] U |
| ownerHeads | [account_id,owner_kind,owner_id] | none |
| localProjects | [account_id,project_id] | none |
| localNotes | [account_id,project_id,note_id] | identity [account_id,note_id] U |
| legacyNoteHistory | [account_id,project_id,note_id,record_kind,record_id] | event [account_id,event_id] U |
| legacyNoteIntents | [account_id,event_id] | note [account_id,project_id,note_id] U; ordinal [account_id,device_id,local_ordinal] U |

Sparse history event index continues to include candidates; head/group/local_version
records do not acquire a candidate event_id. I2→C3 moves the same global ordinal
from the intent index to the outbox index in one transaction. Schema version and
record version have separate meanings; inbox9 is not a thirteenth store.

Proposed 8→9 upgrade: under existing writer/session exclusion and versionchange,
validate exact v8 schema, scoped identities, old-version record allowlists, indices,
ordinal/receipt/inbox/history/cohort structural joins. Keep all old record bytes,
head/groups/prefix/ACK and baseline own Content barriers unchanged; create no I2/C3/
R2/P2 and activate no writer. Do not await crypto/HTTP inside versionchange. On unlock
reauthenticate encrypted history/source before mutation or qualification. Earlier
supported versions must follow validated existing upgrades plus this v8 gate,
without bypassing old checks. Preserve future-version and blocked-upgrade errors.

Acceptance prerequisites: populated v8 profiles with all old versions, mixed groups,
unsealed/sealed/accepted Legacy lifecycles, old proofs/prefix/ACK; direct/follow-on
upgrade and disk reopen; old v8 client rejection of v9; wrong schema/corrupt data
aborts with original v8 intact; interrupted upgrade; new client reading old bytes;
crypto corruption fails after unlock; writer disabled even after successful upgrade.
No automatic downgrade of a written v9 profile. Roll back feature activation, retain
evidence and use a v9-capable reader; do not reset/clean or discard records.

## 15. Security and compatibility invariants

Trust boundary: normal application code, origin/HTTPS, current auth/key runtime and
browser storage/transaction guarantees. A malicious storage editor without the key
cannot forge new authenticated I2/C3/R2, but can delete data, corrupt it, or restore
valid old records. A fully compromised running client with AMK/code execution can
forge local envelopes and UI/network decisions: these records are not remote
attestation, not protection from a fully compromised client, and not server-signed
proof of human authorship. No new signing service/key or crypto domain is assumed.

| Threat | Required response / boundary |
|---|---|
| Forged local candidate / peer candidate relabeling | C3 authorship E + authenticated frozen I2/source + exact original own frame; candidate2 peer validator never accepts own. |
| Forged accepted outbox | Accepted flag does not qualify; require C3 plus valid R2 binding the exact stored item. |
| Forged receipt / edited server sequence | Authenticate R2 E including baseReceipt1/sequence and C3 digest; receipt1 cannot substitute. |
| Replayed server echo | Exact event/device/sequence/wire C3/R2 join; old proof replays without projection/head/group mutation. |
| Duplicate event ID | Existing unique candidate/inbox indexes, allocation and cross-store exact joins; differing bytes/identity abort, never overwrite. |
| Candidate/wire mismatch | AEAD-bound C3 body hash + decrypt original frame and exact outbox comparison; no normalize-and-reseal. |
| Wrong account/device | AAD plus authenticated payload scope and current binding; same user/different device is peer. |
| Wrong bootstrap / changed lineage | I2/C3 authenticated dependencies + active binding CAS; migration/import cannot mint origin. |
| Wrong revision/parent | Retained parent chain, single frontier, source/intent/header checks; no max-revision or source edit counter inference. |
| Stale auth/key lease / account-switch completion | Current checks after awaits and in transaction callbacks; abort and discard prepared tokens, retain last committed evidence. |
| Concurrent tabs / stale transaction | Session Web Lock, strict transaction, full CAS and unique indices; no second writer or source-only fallback. |
| Crash seal→outbox / upload→receipt | Atomic T_seal/T_accept; original bytes retry, no half-state recovery by invention. |
| Malicious IndexedDB mutation | Reauthenticate rather than trust hashes/flags; invalid records block. Deletion/whole-valid-profile rollback remain availability/freshness limitations. |

Frozen: existing crypto/AAD and contexts, codec8 ordinary-v1, frame1, ID0/ID1 policy,
protocol3 and server receipt semantics; Legacy intent1/writer wire behavior; peer
proof1/candidate2/conflict proof1/2; head1/group1/local_version1 meaning; common ACK
transport. New local payload/record versions are explicit proposals, not hidden
reinterpretations. No frozen contract was found to require a change; if later
implementation discovers such a need, STOP and obtain a separate design decision.

## 16. Required tests and Chromium scenarios

These are **future acceptance requirements**, not tests run or changed in C21.2.05.

- Exact version dispatch: old fixtures remain byte-identical; I2/C3/R2/P2 not admitted
  by old leaves; no peer-only invariant weakening or receipt1 shortcut. Scope,
  route, timestamp/parent/generation/limit/AEAD tamper cases for every new record.
- Canonical mutation: one source, one writer, immutable event/ordinal identity,
  same-operation coalescing, clean handover, no source-only commit; genesis versus
  existing unbound source; blocked operation changes and pending creates/deletes;
  global ordinal accounting with simultaneous Legacy and Content Notes.
- Seal: abort after every candidate/head/outbox/delete write, quota, stale source/
  generation/group/Metadata/key/auth; zero partial authority; reopen and exact raw
  wire retry. ID0/ID1, compress-before-encrypt, bounded decompression after AEAD,
  capability loss, unsupported mode and deterministic retained bytes after reopen.
- Sender/R2: dedicated Note/event adapter, raw-body byte equality, no metadata
  encoder reuse; lost response/duplicate/current cursor/sequence collision/wrong
  event/body; auth switch and failure before/after receipt/outbox writes. Receipt1,
  fake accepted flags and tampered R2 never qualify.
- Self-echo: real production-origin I2→C3/outbox→authenticated push/R2→inbox/P2 chain;
  missing/fabricated authority negative cases; echo-before-receipt; wrong account/
  device/bootstrap/parent/revision/compression/sequence/wire; peer device same user;
  zero local source/head/group/intent writes, no generation increment; exact replay
  after new local generation, peer descendants and full profile reopen.
- Conflicts: all current peer Content, Legacy self-echo and mixed/history/post-seal
  regressions; existing group1 unchanged; Content handover/write blocked on group;
  new Content-local sibling retained without winner/projection changes or fake proof.
- Prefix/ACK: genuine P2 crosses only its own sequence when all preceding events
  qualify; unproven own event/other-family/missing earlier sequence stays a barrier;
  stale inventory never sends ACK; server-success/local-commit failure remains safe;
  existing registration/reader/registry/mode/no-progress/one-ACK contracts unchanged.
- Chromium with native IndexedDB/Web Locks and disposable disk profile: two tabs;
  real canonical edit/intent/seal helper chain, exact outbound network bytes, lost
  upload response, retry and acceptance, echo-before/after-R2, source unchanged on
  echo, later safe peer, blocked fork, logout/key lock, renderer and disk reopen;
  populated v8→v9 upgrade and old-client rejection; zero page errors. Fixtures may
  stub HTTP but must not fabricate a positive C3/R2 and call it production authorship.

## 17. Recommended implementation slices

**Planning identifiers only. Do not start them in C21.2.05.** Each depends on owner
acceptance of its predecessor. Activation remains off through .10; no server/native
changes or Resolution are included. Add new files only where these named concerns
cannot fit existing scoped modules.

| Proposed slice | Objective and components | Durable / migration impact | Activation, mandatory checks and rollback |
|---|---|---|---|
| C21.2.06 — versioned authority records | Implement strict I2/C3/R2/P2 leaves and shared version dispatch in persistence, syncDurability, intent/history/receipt/proof readers; retain old validation semantics. | Proposed versions + inbox9; explicit 8→9 format-gate migration, same12 stores/indexes; no producer writes new authority. | OFF. Populated migration/old-client rejection, shape/crypto-negative and old-fixture coverage. Abort upgrade on structural failure; v9-capable read-only fallback, no downgrade. Depends on accepted .05 and review of exact proposed shapes. |
| C21.2.07 — canonical source/intent ownership | Integrate future Content intent producer into localAuthority and shared Note routing/allocation; explicit clean handover and no conflict write. | I2 and authenticated intent_format2 payload; existing encrypted source1 unchanged. No further DB upgrade. | OFF in user composition. Source+intent+ordinal atomicity/coalescing, Legacy coexistence, unsupported route/group and auth/CAS tests. Failure aborts source mutation; no Legacy fallback. Depends on .06. |
| C21.2.08 — atomic codec8 sealing | Future Content sealer, frame/compression writer gates, C3 authorship, original outbox bytes and common ancestry dispatch. | C3 plus sealed_authorship payload; outbox1/head1 unchanged. No further migration. | OFF. All T_seal fault boundaries, ID0/ID1, nonce/wire immutability, reopen and old peer-proof ancestry regressions. Failure leaves I2; retain sealed bytes on later errors. Depends on .07. |
| C21.2.09 — exact upload and acceptance | Dedicated browser Note raw-body API adapter plus Content R2 prepare/commit; validate existing server response and replay same bytes. | R2 plus local content_receipt_format1 authentication payload; server receipts unchanged. No migration. | OFF. Exact raw network bytes, duplicate/lost response/echo-before-receipt, auth switch and atomic acceptance tests, Chromium restart. Failure retains sealed state; no receipt1 authority. Depends on .08. |
| C21.2.10 — own acknowledgment/prefix | Separate self-echo runtime/P2/inbox9 verifier and full account prefix/ACK composition. | P2/inbox9 already version-gated; no new format/migration. | OFF until independent acceptance. Real producer-chain Chromium, no projection/group writes, forged authority barriers, cross-family ACK and all mixed/peer/Legacy regressions. Invalid own event stays received; no ACK crossing. Depends on .09. |
| C21.2.11 — bounded activation acceptance | Only after explicit authorization: expose clean project-HTML import_remote writer composition with all current gates, deploy accepted implementation and verify durable lifecycle. | No new durable format/migration permitted in this slice. Stage/plain writing, capture/mixed Content-local writers remain out of this activation. | May activate only the accepted bounded writer/self-echo paths after gates and full Chromium/reopen/compatibility acceptance. Any unexplained format/transport/conflict issue STOP; disable new mutation/upload activation, retain/retry exact accepted evidence with v9 reader, ready=false. Depends on .10 acceptance and owner activation decision. |

## 18. Unresolved blockers / STOP decisions

1. Current production still has no Browser Content author/seal/candidate/outbox chain.
   This design is not a workaround for the accepted C21.2.04 barrier.
2. Proposed record versions, authenticated payload limits and v9 dispatcher/migration
   need implementation review and the future acceptance above. No new format passes
   current validators; no schema migration has been performed.
3. Metadata push encoder rejects Note/event. Future .09 needs its own stored-raw-body
   adapter on existing protocol3, not a native runtime copy or widened metadata route.
4. Browser Note capability/writer gate and producer composition are absent; existing
   compression-reader declaration and native capabilities cannot stand in for them.
5. Content-local mixed conflict creation/preservation, operation cancellation,
   resurrection, upload_existing/initial Content capture and Stage/plain activation
   are explicitly blocked/out of first activation. No group1/proof reinterpretation.
6. No anti-rollback/remote-attestation guarantee for a fully compromised client or
   restored valid profile. Server receipt authentication here is a trusted local
   observation, not a new server signature.
7. If four variants, existing crypto1/AAD1 context or unchanged server protocol cannot
   meet implementation checks, STOP that implementation and amend the design in an
   explicitly authorized slice; never silently add another store, proof or protocol.

Traceability for the mandatory 26 questions:

| # | Answer / location |
|---|---|
| 1 | Existing localNotes + localProjects membership, section5. |
| 2 | YES, immutable snapshots only; no second mutable source, sections3/5. |
| 3 | UUID4 and ordinal durably reserved in T_mutate before any wire, sections4/5. |
| 4 | Producer owns cloud revision/parent from authenticated head, distinct from source/local revisions, section5. |
| 5 | Shared verified parent chain, single frontier and head CAS; not max revision, section5. |
| 6 | Separate authenticated I2 in existing intent store, sections3/4. |
| 7 | Ordinary inner1, wrapper1, frame1/codec8/version1, section6. |
| 8 | Existing gate/policy before E2EE; immutable persisted frame authenticated on decrypt, section6. |
| 9 | Exact protocol3 Note/event raw body after existing Note encryption, sections6/7. |
| 10 | Encrypted snapshots/envelopes only, bounded metadata/hashes, section6. |
| 11 | Strict T_seal creates C3/outbox/removes I2/updates head atomically, section7. |
| 12 | Network only after durable seal; raw_body reused byte-for-byte, sections7/8. |
| 13 | Authenticated HTTP response→R2 + accepted outbox in T_accept, section8. |
| 14 | Authenticated frozen I2 + C3 authorship envelope + original own wire, sections3/9. |
| 15 | Accepted exact outbox, authenticated R2/sequence and original inbox echo→P2, section9. |
| 16 | Reuse strict source/codec/crypto/wire/response leaves; new version dispatch, section3 matrix. |
| 17 | Content proof1/conflict1/2 and candidate2 remain peer-only, sections3/15. |
| 18 | Four top-level variants I2/C3/R2/P2, wrapper9 and their named encrypted payload schemas; no seven independent stores/formats, section3. |
| 19 | v8 can physically hold JSON but lacks old-client exclusion; recommend explicit v9 format gate, section14. |
| 20 | Old bytes/validators unchanged; new client dispatch, old client fails before open, section14. |
| 21 | Derived legal states and atomic abort/retry; halves are corruption, section13. |
| 22 | Existing session Web Lock + strict IDB CAS/unique constraints, section12. |
| 23 | Fresh auth scope/lease; abort stale plans/completions; unlock reauthentication, section12. |
| 24 | Block Content writer on unresolved group, keep current Legacy mixed behavior and received forks, section10. |
| 25 | Private certificates reauthenticate full I2/C3/R2 lifecycle, contiguous scan/CAS, section11. |
| 26 | Reuse native causal/immutability patterns, not SQLite tables, source migration, IPC or inbox-derived acceptance, sections1/8/13. |

## 19. Plain-language summary

### Простыми словами

Браузеру нужна собственная надёжная история создания и отправки Content: иначе
полученное событие со своим device id нельзя отличить от записи, которой он не
создавал. Receipt сервера сообщает о принятии события, но сам по себе не доказывает
его прежнее локальное авторство.

Предлагаются четыре версии записей: зашифрованное намерение отправки, неизменяемый
локальный candidate с точными отправляемыми байтами, связанный с ним подтверждённый
receipt и отдельное доказательство собственного эха. Текст заметки остаётся в одном
существующем localNotes; исторические снимки не становятся второй рабочей заметкой.
Подтверждение не переписывает текст и не решает конфликт за пользователя.

Сохранение заметки и намерения, затем candidate и outbox, затем receipt и принятой
отправки выполняется отдельными атомарными шагами. После сбоя либо остаётся прежнее
состояние, либо целиком новое. Повторная отправка использует уже сохранённые байты,
без нового события или шифрования. Собственное эхо проверяется по всей этой цепочке,
а не только по device id или флагу accepted.

Рекомендуется будущая v9 без новых хранилищ и индексов, чтобы старый v8-клиент не
открыл профиль с непонятными ему writer-записями. Сейчас миграции нет. Будущие шаги
разделены на форматы/миграцию, локальное намерение, шифрование/outbox, отправку/receipt,
self-echo/ACK и отдельную ограниченную активацию. При нерешённом конфликте новый
Content writer будет заблокирован.

В этом задании создан только проект контракта. Content writer и self-echo остаются
выключены: их ещё нужно реализовать и независимо проверить. Peer Content и Legacy
продолжают работать в прежних границах; полная Web-синхронизация ещё не готова.

Documentation validation for C21.2.05:19 required sections,26 answer rows,36 existing
source links and61 key source-symbol checks verified; proposed variants compared
with current strict validator allowlists and12-store schema; previous family matrix
reviewed; documentation diff/scope and git diff --check PASS. No tests, Chromium,
typecheck, backend/native build or migration executed. Proposed runtime guarantees
are acceptance requirements, not measured results. Protected bytecode unchanged.

## C21.2.08A — reader capability audit (STOP)

Baseline `8aa3a38137ebae7b986cb763f91851024605cf91`; C21.2.08 Cloud run
`39201101699` SUCCESS, 6/6. The backend declaration stores per-device reader
versions. Its account-wide gate requires mode3 plus frame1/codec8 v1/compression0,
ordinary-v1 and Resolution-v2 on every registered device. It is reader readiness,
not writer authorization; mode3 alone grants no writer permission. No separate
Content writer authorization is consumed by the existing API.

Browser ordinary-v1 decode and protected apply exist. Resolution-v2 canonical
decode exists, but `BrowserContentNoteApply.prepare` routes only to
`prepareContentOrdinary`; Resolution apply remains separate and unactivated. Since
the frozen backend readiness contract requires Resolution-v2, browser support cannot
truthfully be declared complete. STOP before browser declaration or token creation.
No dormant gate or production writer was implemented. C21.2.08 sealing, Content
upload/self-echo and Resolution remain blocked. Next prerequisite: implement and
accept browser Resolution-v2 protected apply (or separately approve a truthful
server capability contract); then revisit the dormant gate. `ready=false`, progress
84.0%; no roadmap renumbering.

## C21.2.08B — Resolution-v2 protected apply contract / design only

**DESIGN ONLY / LOCAL DOCUMENTATION COMPLETE / REMOTE CI PENDING.** Baseline and
C21.2.08A audit SHA `90159a7ec56f46b83f4aa5f4b64ba2605ab02b0e`; independent
Cloud `39206686051` SUCCESS, 6/6 mandatory jobs (owner supplied). C21.2.08A is
REMOTELY ACCEPTED AUDIT ONLY, functionally blocked. C21.2.08 sealing remains
BLOCKED; C21.2.09 NOT STARTED. Official84.0%; C21/C21.2 IN PROGRESS;
C21.1.06 NOT LOCAL COMPLETE; ready=false. Everything proposed below is unimplemented.
This section extends the future reader design, not the existing C3 writer contract.

### B1. Audited code and decision

| Actual source | Constraint / reference behavior |
|---|---|
| [contentNoteApply.ts](../../frontend/src/platform/web/contentNoteApply.ts), [noteTransport.ts](../../frontend/src/platform/web/noteTransport.ts), [noteTransportPrerequisite.ts](../../frontend/src/platform/web/noteTransportPrerequisite.ts) | Production browser Content preparation selects ordinary-v1 only. Original AEAD, Metadata and Stage prerequisites issue opaque current certificates; none authorizes Resolution. |
| [noteHistoryRecords.ts](../../frontend/src/platform/web/noteHistoryRecords.ts), [noteHistory.ts](../../frontend/src/platform/web/noteHistory.ts) | candidate1/2/3 use ordinary headers; parent revision must be previous revision, frontier removes only single parents; head1 requires a candidate; group1 is open-only and currently one per Note. Immutable candidates/frozen versions cannot be rewritten. |
| [legacyNoteApply.ts](../../frontend/src/platform/web/legacyNoteApply.ts), [localAuthority.ts](../../frontend/src/platform/web/localAuthority.ts), [localAuthorityRecords.ts](../../frontend/src/platform/web/localAuthorityRecords.ts) | Plans bind real history, encrypted source and current lease. Current protected source hook writes one Note plus project, not the two-Note keep_both mutation. Project member_ids include stored tombstones. |
| [contentNoteProof.ts](../../frontend/src/platform/web/contentNoteProof.ts), [contentNoteConflictProof.ts](../../frontend/src/platform/web/contentNoteConflictProof.ts) | Applied proof ancestry follows a single chain. Open group verification assumes the current head or frozen branch; historical verification after closure needs a separately authenticated transition. |
| [ackPrerequisites.ts](../../frontend/src/platform/web/ackPrerequisites.ts), [provenPrefix.ts](../../frontend/src/platform/web/provenPrefix.ts), [persistence.ts](../../frontend/src/platform/web/persistence.ts) | Prefix requires exact authenticated family outcomes; schema is v9 / 12 stores; no Resolution proof or closed-group representation. Inbox9 is already reserved for own Content P2, not Resolution. |
| [canonicalReaders.ts](../../frontend/src/platform/web/canonicalReaders.ts), [contentNoteCodec.ts](../../frontend/src/cloud/contentNoteCodec.ts), [noteSyncResolutionV2Codec.ts](../../frontend/src/cloud/noteSyncResolutionV2Codec.ts) | Read-only decoding supports codec8/frame1 ID0/ID1 and embedded Resolution2; the frozen decoder defines four strategies, sorted 2..64 parents and portable Content route restrictions. Parsing is not protected apply. |
| [contentNoteRuntime.ts](../../frontend/src/cloud/contentNoteRuntime.ts), [contentNoteReader.ts](../../frontend/src/cloud/contentNoteReader.ts) | Native declaration/reader uses Tauri persistence; do not import this as browser authority. |
| [note_sync.rs](../../frontend/src-tauri/src/note_sync.rs), [content_note_sync.rs](../../frontend/src-tauri/src/content_note_sync.rs), [SQLite applied Resolution ledger](../../nfprogress/core/sqlite/migrations/023_note_sync_applied_resolutions.sql) | apply_resolution_with_content, peer_resolution_tip_proofs, peer_result_evidence_with_content and peer_resolution_replay_matches require published parents, exact local group/CAS, original objects and result evidence. Remote group IDs/generations may differ from local ones. keep_both advances both entity heads under the single Resolution event. Reference semantics only; native IPC/SQLite authority cannot be copied. |
| [backend services](../../backend/app/cloud/services.py), [capability schema](../../backend/app/cloud/schemas.py), [v3 routes](../../backend/app/cloud/sync_v3_router.py) | Declaration persists authenticated registered-device protocol metadata. content_note_gate requires all devices ready plus mode3. Opaque note/event push is rejected if the gate fails; pull also checks device readiness after Note events exist. This is readiness, not an independent server-issued writer permission. |

**Decision: select A, complete browser Resolution-v2 protected apply; propose v10.**
V9's bytes can physically store another object, but its accepted validators and old
clients cannot safely understand multi-parent nodes, conflict closure, clone anchors
or a new proof. Do not encode Resolution as ordinary candidate2/3, mutate group1 to
an unrecognized lifecycle, or reuse inbox9. V10 is an opening compatibility barrier;
no migration or production code changes occur in this slice.

### B2. Reader boundary and immutable input

The future browser-only reader takes `(current BrowserSyncScope, retained sequence)`;
caller-provided plaintext, result DTOs or proof flags are never authority. It loads
the original retained wire, decrypts with the current account AMK lease and binds
canonical user, account/device/profile, auth epoch and source device to the retained
descriptor. AMK AEAD plus the server descriptor is the existing identity contract,
not a new per-device signature. Crypto1/AAD1 binds user/project/Note.

For mode3: require protocol3, Note/event, deleted_at=null, WORTA-C1 frame1/codec8 v1,
ID0 or existing bounded ID1 decoding, wrapper account/device and exact descriptor
identity/revision/canonical time. Require embedded version2; preserve both the
original encrypted wire (including original nonce/ciphertext) and exact authenticated
canonical wrapper/Resolution payload under that original AEAD. Reopen the original
ciphertext whenever exact payload bytes are needed; do not persist duplicate
plaintext payloads. Never reframe, recompress or synthesize a v1 wire. Also specify a separate explicit C17 protocol2 Note/resolution decoder for
already retained legacy Resolution2: no codec fallback, no writer cutover and no
change to ordinary Legacy routing. The mode3 capability acceptance concerns the
framed Content route; legacy Resolution transport acceptance is tested separately.

Complete means all four frozen strategies within each owning codec's accepted
routes. Content retains project HTML/plain, stage-null or proven Stage, empty
metadata, no mindmap ownership, exact route consistency with all parents and the
keep_both retained Note. Legacy Resolution retains its existing C17 eligibility
restrictions. Do not claim mindmap or unsupported route support. Enforce frozen
payload/resource bounds and preflight local encrypted-source size/quota limits;
never truncate data or declare a rejected event applied. New typed Resolution source
admission must validate Content routes without widening Legacy source validators.
Audit the existing smaller local title/content limits explicitly during source-hook
implementation; unsupported size stays a visible barrier until that admission is
accepted. No capability declaration is justified merely by successful decoding.

### B3. Evidence needed before a result may touch source

1. Snapshot registered local identity, binding and active bootstrap. For Content,
   force fresh original-AEAD Metadata coverage and require the declared Metadata
   event to be a covered live ancestor of the exact current single live head.
   Authenticate exact Stage dependencies for both outputs; missing/changed/deleted
   Metadata or Stage authority blocks. A legacy envelope has no invented Content
   dependencies: bind its accepted bootstrap/current project authority explicitly.
2. Authenticate every parent from original retained Legacy/Content candidates or an
   already proven Resolution result anchor. All parents belong to this account,
   bootstrap, project, original Note and route. Require sorted unique resolved IDs
   (2..64), primary=first ID, additional=remaining IDs, exact equality with the
   payload's resolved_event_ids, no self-parent, and revision=max(parent revisions)+1.
   Traverse the full DAG, detect cycles, missing edges and cross-Note anchors; never
   follow just the primary parent or accept an arbitrary set of UUIDs.
3. Authenticate the complete current effective open local conflict group, its final
   members, generations, common ancestor and current frontier. Exact resolved IDs
   must equal its published tip IDs; a strict subset means missing evidence, extra
   or different tips mean stale conflict. Remote group UUID/generation are retained
   as authenticated sender metadata; they need not equal locally allocated values.
   Record an explicit remote-to-local mapping justified by the exact parent set,
   scope, snapshots and ancestry, never by matching group names alone.
4. A remote branch needs original AEAD plus actual applied/conflict-preserved inbox
   evidence. A local frozen branch needs its genuine frozen admission AND the exact
   sealed candidate, immutable accepted outbox/receipt and current lifecycle proof.
   Unpublished local intent is not a resolvable published parent. If later sealing
   coalesced the same local event, compare the actual published snapshot/generation,
   not the earlier frozen text; retain both witnesses. No pending I2/C3 branch,
   unsealed edit or newer canonical source may be silently consumed.
5. Decrypt canonical localProjects/localNotes and authenticate membership, current
   head/working branch, source revisions and whole-project source token. The source
   must equal the proven currently displayed branch, not merely have the same ID.
   Preserve the historical branch even when the result selects another version.
   An unrelated new local edit aborts instead of being overwritten.

These checks make the Resolution a decision over exactly the existing conflict,
not an authenticated request to overwrite whatever Note happens to exist now.
Manual merge is a received authenticated decision, not a merge invented by Web.

### B4. All frozen strategies

| Strategy | Mandatory result check and source effect |
|---|---|
| choose_version | selected_event_id is exactly one proven parent; result operation and full wire Note/tombstone equal that published parent's snapshot. Apply that result to the original Note. No implicit preferred branch. |
| manual_merge | Result must be an upsert, pass complete frozen validation, retain the original Note/project/route, and resolve the exact full parent set. The sender's authenticated merged content is used without recalculation. |
| delete | Result must be the validated original-route tombstone. Keep encrypted local tombstone and historical content; do not physically delete history or pretend one parent was chosen. |
| keep_both | Exactly two distinct live upsert parents. Original result is byte-semantic equal to selected parent. Retained result equals the other parent's wire record except its new id and received created_at/updated_at (the native frozen contract's allowed changes). Same project/Stage/format; never generate a new ID or timestamps on the receiver. Apply both in one transaction. |

keep_both collision checks cover the entire account's localNotes unique identity,
including tombstones and other projects, all history/clone anchors, pending intents,
sealed/accepted outbox, receipts and retained inbox descriptors, plus reserved output
IDs of any Resolution. A received future child may reference the planned clone but
is not an existing clone allocation; distinguish that reference from a conflicting
create/owner. Only exact proven replay may reuse an allocated clone. Both source
rows use existing encrypted local_format1/record1; project member_ids becomes the
sorted set of stored Note IDs (including tombstones), adding the clone once. One
project source_revision increment covers both rows; local mutation revision follows
the current protected peer-apply convention (0), while cloud revision is the
Resolution revision in history. Resource/identity limits abort the whole mutation.

### B5. Proposed exact durable extension (not implemented)

Use the same 12 stores, paths and indexes. Existing strict record variants retain
their shapes. UUIDs, safe integers, canonical timestamps, SHA256 hex and bounded
crypto1/AAD1 envelopes use existing validators. Unknown/additional fields reject.
`H` below is exactly account_id, device_id, project_id, note_id, bootstrap_id,
record_kind, record_id; each new history variant adds record_version as specified.

| Proposed record | Exact fields beyond H and record_version; invariants |
|---|---|
| Resolution4 in legacyNoteHistory | record_version=4; record_kind='resolution'; record_id=event_id; event_id, source_device_id, protocol_version, transport_kind, server_sequence, header, wire_item, wire_digest, payload_digest, dependency_digest, remote_group_id, remote_generation, local_group_id, local_generation, group_digest, parent_event_ids, strategy, result_operation, retained_note_id, evidence_envelope, record_digest. transport_kind is 'content_note_resolution_v2' (protocol3) or 'legacy_resolution_v2' (protocol2); header is exact frozen Resolution2 header. retained_note_id is null except keep_both. One immutable applied event, not candidate2/3; event index remains unique. |
| Head2 in legacyNoteHistory | record_version=2; record_kind='head'; record_id='head'; head_revision, linear_head_event_id, tip_event_ids, node_ref. node_ref is exactly {kind:'candidate',event_id} or {kind:'resolution_result',resolution_event_id,result_role,resolution_digest}; role is 'original' or 'retained'. No top-level event_id, so no event-index collision. Replace only this mutable head key with exact previous-head CAS and head_revision+1; preserve the previous head in encrypted Resolution evidence. |
| GroupTransition2 in legacyNoteHistory | record_version=2; record_kind='group_transition'; record_id=group_id; group_id, from_generation, from_digest, resolution_event_id, resolution_digest, resolved_parent_ids, effective_lifecycle='resolved', record_digest. One append-only closure per group; freeze original group1 bytes at this generation. It is invalid without authenticated Resolution4. Do not rewrite group1.lifecycle or delete it. |
| ResolutionProof1 inside inbox10 | proof record_version=1, owner_kind='note_resolution', outcome='applied'; account_id, bootstrap_id, protocol_version, reference, server_sequence, header, wire_digest, payload_digest, dependency_digest, resolution_digest, transition_digest, output_digests, outcome_digest. reference is exact original transport descriptor; output_digests is exactly {original:string,retained:string|null}, hashing the encrypted output records. No plaintext Note. |
| Inbox10 in inbox | Existing retained wire fields unchanged; record_version=10; state='note_resolution_proven'; resolution_proof=ResolutionProof1. The new version is unrelated to database version10 and cannot reuse inbox9/P2. |

Resolution4.evidence_envelope decrypts to an exact inner schema:
`resolution_format=1, kind='resolution_apply', identity, authenticated_payload,
parents, group_snapshot, head_before, source_before, source_after`.
Identity is all public Resolution4 fields except evidence_envelope/record_digest;
it is compared exactly, not trusted from the outer row. authenticated_payload is
exactly `{wire_frame_digest,wrapper_payload_digest,resolution_payload_digest}`: original
AEAD plaintext digest, canonical wrapper digest (null on protocol2), and frozen
Resolution digest. Original retained ciphertext preserves the exact bytes and must
be reopened and compared; hashes do not replace that payload. parents is the ordered array of exactly
`{event_id,revision,operation,history_digest,inbox_digest,publication_source,
server_sequence,local_mutation_generation,frozen_version_digest,snapshot_digest}`;
publication_source is remote, remote_applied or local_accepted; nullable local fields
are null for remote parents, frozen_version_digest is required for a local witness.
Each snapshot is rederived from its authenticated immutable history/publication
reference and compared with snapshot_digest; do not duplicate up to 64 large parent
snapshots in the new record. Group_snapshot is exact final group1; head_before is exact prior head; source_before
is exactly `{project,notes}` with the prior encrypted project and the original Note
record only (clone absence is pinned by inventory/identity CAS); source_after is
exactly `{project,notes}` with the resulting encrypted project and original/optional
retained encrypted Note records. Each notes array is sorted by note_id. The private
plan still CASes the whole project source token; unrelated source rows are not copied
into evidence.
No unencrypted content/snapshot is added to durable metadata. Reuse Note
crypto1/AAD1 under the original Note context, binding the new kind, identity and
scope inside AEAD. Hashes alone never confer authority. New evidence-envelope
plaintext is bounded at 64 MiB (five existing encrypted source records at most,
each currently bounded by 8 MiB plus base64/metadata overhead); the complete new
Resolution record is bounded at 128 MiB including the encrypted original wire and
base64 evidence. Use a dedicated strict evidence-envelope validator, not the 8 MiB
local-source validator. Preflight UTF-8/encoded sizes before encryption and before
any IDB write; quota failure stays atomic. This does not increase transport or local
source limits. The parent references make the bound independent of 64 parent
snapshot sizes. Acceptance must cover worst-case encoded sizes and avoid loading
unbounded history or plaintext copies; bounded sequential parent opening and
zeroizing temporary buffers are required.

Digest dependencies are acyclic: Resolution4 binds group-before/source-before and
authenticated outputs; its digest excludes record_digest. Transition binds that
Resolution digest; Head2 references it; inbox proof binds Resolution and transition
digests. No Resolution field hashes its own proof/head-after/transition digest.

The effective group lifecycle is derived: group1 without a valid transition is open;
with exactly one authenticated transition it is historically resolved. Never trust
its old literal 'open' as current after v10 dispatch. Allow multiple retained group1
records on a Note only when all but at most one have proven closures; each retains
its own immutable versions/proofs. Future groups start separately from the new
proven parent. Closure freezes membership/generation, and later sibling arrival
cannot append to the closed group or reopen it implicitly.

Historical parent validation must not recursively use the new Resolution proof
as justification for those same parents. First authenticate immutable wire and
pre-closure outcome/group witnesses against head_before and the prior DAG; then
validate the closure; only then expose the new DAG reachability to prefix consumers.
Detect cyclic proof/reference dependencies and fail closed. Leaf AEAD validation,
historical outcome validation and current-frontier qualification are separate passes.

The DAG resolver operates on `(account,bootstrap,project,note,event)` and consumes
all Resolution parents. A keep_both Resolution has **one** event-bearing Resolution4
under the original Note; the clone Head2 references its retained output. There is
no second candidate with the same event_id and no fake revision1 clone genesis.
The resolver loads the cross-Note Resolution4 from the same authenticated project
inventory. A clone's later ordinary child may use Resolution event ID as parent at
revision+1, but only for that record's retained_note_id; it cannot borrow the original
Note's scope. Frontier excludes all consumed parents, not just the first; fork tips
remain until a later exact closure. Existing candidate versions stay unchanged.

### B6. Preparation, atomic apply, history and prefix

Propose a separate browser Resolution runtime with private WeakMap plans, current
normal-user auth/key lease, profile lifecycle and existing exclusive writer lock.
No raw projection write API, Tauri invoke, network request or persisted grant.
After each await check currentness. Crypto/decompression/validation/encryption run
outside IDB against a complete immutable inventory; transaction scheduling remains
synchronous IDB callbacks. Plan is private, single-use, account/device/runtime-bound.

One strict readwrite transaction includes inbox, cursors, projectBindings, ownerHeads,
legacyNoteHistory, legacyNoteIntents, localProjects, localNotes, outbox and receipts.
Re-read and exactly CAS inbox/wire, account inventory, pull checkpoint, binding,
Metadata/Stage heads, all parents/publication evidence, active group/generation,
old heads and canonical encrypted source. Check clone absence again via the unique
identity index and inventory. Recheck auth/key/profile lifetime in every callback;
subscribe to invalidation and abort. Any stale evidence requires a fresh prepare.

Atomically add Resolution4, add GroupTransition2, update original Head2 and optional
clone Head2, write pre-encrypted original/clone source and project membership, and
replace only the received Resolution inbox row with inbox10/proof. Preserve every
old candidate, frozen version, original group and historical inbox proof. No writes
to outbox/receipt/intents or ordinal; no pull/proven-prefix/ACK cursor advancement.
No durable 'applying' half-state: commit makes all outputs visible, abort makes none.
A post-commit lost response is handled by exact replay, never re-encryption.

Existing history helpers, producer ownership checks and all proof readers need
explicit v10 dispatch before migration is enabled. Historical applied/conflict proofs
must continue to authenticate original encrypted material and historical membership
through the proven closure/previous-head snapshot; they must not require the current
head to equal the old applied branch. This supplements historical verification;
creation-time checks for an unresolved group remain strict. DAG ancestry keeps old
applied branches reachable through all parents. A late sibling of a closed decision
stays a new unproven/stale-conflict barrier unless a separately proven new conflict
transition can preserve it; never rewrite the old Resolution result automatically.

Future ordinary peer continuation must resolve both original and clone anchors,
including tombstone continuation and a later new conflict, before declaring reader
completion. Legacy mutation/sealing and Content I2/C3 producers must fail closed on
Resolution-owned Notes until their own parent/ownership paths are separately accepted;
untouched Notes retain existing behavior. Do not activate a writer as a reader test.

A separate authenticated Resolution prefix certificate reopens original AEAD,
evidence envelope, all parent proofs, closure and historical outputs; pins fresh
Metadata/Stage and complete inventory; then qualifies exactly this server sequence.
Do not equate stored inbox10 or a digest join with proof. Historical output records
are evidence, not a demand that a later legitimate source still equal old text.
Only a separately prepared contiguous-prefix commit may advance proven_prefix;
existing ACK registration/reader/registry/current-mode gates remain required.
All cross-family barriers stay in place. A keep_both event counts once, not twice.
No own Resolution self-echo is fabricated: source_device==current device without a
real accepted author chain stays blocked; designing peer apply does not authorize
self-echo or enable the dormant Content P2/inbox9 path.

### B7. Orphan, replay and reopen

Missing parent, bootstrap/dependency, group, accepted local publication or causal
ancestor leaves the original inbox record `received`, source/head/history untouched,
with safe runtime diagnostics. No new orphan record variant is necessary. A bounded
explicit retry pass can scan retained received rows after dependencies arrive;
its in-memory bookmark is disposable and resets on profile reopen. It must revisit
earlier orphans and process later prerequisites without skipping ACK gaps.
Extra tips, wrong scope, conflicting event/sequence, changed source or incompatible
route are distinct fail-closed errors, not an orphan turned into success. Conflicting
Resolution decisions over an already closed group stay unqualified; do not choose one.

Exact replay requires original sequence/event/wire, canonical payload, parents,
remote/local mapping, closure and both output witnesses to match; it reauthenticates
with the current lease and performs zero writes. No repeated clone creation,
project counter increment or historical-source overwrite. Duplicate event ID at a
different sequence or different event at the same sequence is rejected across the
account, including histories/receipts. IDB unique indexes plus manual cross-store
checks enforce this. Missing half-record, orphan closure, fake clone anchor or
altered encrypted evidence is corruption and blocks reopening for mutation/ACK;
never regenerate a proof from its outer hashes.

### B8. Migration and backend alternative

**V10 required; same 12 stores/indexes/key paths; no data conversion.** Implement
an explicit 9→10 versionchange transaction only after all v10 read/validation paths
are accepted. Structurally validate existing v9 identity, bindings, old variants,
indices, uniqueness, joins, source records and cursor bounds, preserving every byte.
Earlier supported upgrades must run their existing validation chain before this
step. Do not mint Resolution, head2, transition or inbox10 records during migration.
On corruption/request/quota/abort, abort the upgrade: v9 version and bytes remain.
A successful version bump cannot later be downgraded if unlock fails. After unlock,
reauthenticate original ciphertext, frozen I2/C3/Legacy history, all current source
and new Resolution evidence before writes or prefix/ACK are allowed. Structural
validation without keys is never cryptographic acceptance.

Old connections must close on versionchange; a blocking tab yields upgrade_blocked
and no destructive retry. Existing v9 openers explicitly request version9 and must
fail VersionError on a v10 profile; never open without an explicit version, delete
the database, clear stores or reinterpret unknown variants. Same-origin writer lock
remains required. Full profile restart uses fresh auth/account binding/AMK lease;
no plan, readiness token or flag survives. A valid v10-capable repair/read-only path
may retain encrypted evidence on failure, never silently downgrade or purge it.

Alternative B is an explicitly versioned server separation of ordinary and
Resolution capability. Existing fields already express zero support but the current
combined gate deliberately requires both; merely posting resolution=0 cannot safely
enable writing. Server cannot distinguish ordinary and Resolution inside opaque
codec8 Note/event ciphertext, and the stream has one account sequence/ACK cursor.
An ordinary-only browser can retain ciphertext and keep ACK capped before the first
Resolution; it cannot guarantee full stream ACK or ordinary descendants after that
barrier. Skipping or treating retention as apply is unsafe. A truthful alternative
would require a reviewed authenticated discriminator/versioned stream/dependency and
ACK contract plus old-client compatibility; a boolean relaxation is insufficient.
Reject B for this prerequisite. No backend API or readiness policy change proposed.

| Criterion | A — complete browser reader (selected) | B — versioned server separation (rejected here) |
|---|---|---|
| Data safety | Exact conflict/parents/source CAS; full four-strategy proof. | Safe only with additional opaque-routing/dependency and ACK design; current stream insufficient. |
| Compatibility | V10 blocks old local openers; frozen wire and native/backend contracts unchanged. | Must coordinate all server/native/browser versions and stale capability declarations. |
| Scope | Browser DAG, source hook, proof, migration and tests. | Backend protocol, clients, routing/retention/ACK and rollout design. |
| Migration | Browser v10 format gate; no existing record rewrite. | Likely server metadata/protocol rollout; does not by itself implement browser Resolution apply. |
| Maintenance / users | One accepted Resolution semantics, retained v9 data; deploy migration only after acceptance. | Two capability paths and stream semantics; risks inconsistent desktop/browser behavior. |

### B9. Ordered independently testable implementation plan

These are work packages, not new C-stage assignments or roadmap renumbering.

1. **Strict v10 record readers and DAG:** implement isolated new variants, encrypted
   evidence authentication, multi-parent/clone resolver and historical-proof dispatch;
   retain v9 bytes and old validator behavior. No producer, migration or capability.
2. **V10 compatibility gate:** implement populated-profile upgrade/reopen/old-client
   rejection only after all consumers safely dispatch new variants. No Resolution
   producer or declaration; test atomic rollback and unlock crypto separately.
3. **Read-only Resolution planner:** actual original-wire AEAD, dependency/parent/group
   and publication validation, all four strategy checks and private scoped plan;
   negative scope/generation/source tests. No durable changes or writer selection.
4. **Atomic protected source/apply:** one/two-Note hook, clone collision checking,
   append-only closure, Resolution4/head2/inbox10 and exact replay; genuine fixtures,
   every write-fault rollback and ordinary peer continuation on both output anchors.
5. **Historical proof and contiguous prefix acceptance:** fresh crypto certificate,
   preserved old Legacy/Content proofs and closure chains, all cross-family negative
   barriers; no automatic ACK scheduler, writer or self-echo activation.
6. **Real Chromium/restart and readiness prerequisite:** disk profiles, real crypto,
   source/history producer chains and genuine protected apply; focused/regressions,
   typecheck/build and mandatory CI coverage. Only after independent acceptance of
   the whole reader revisit C21.2.08A dormant declaration/gate/token. Declaration
   requires current registered auth/device, authoritative mode3, ready=true AND
   missing_devices=0; ID1 writer authorization remains separate. C21.2.08 can resume
   only after that prerequisite is accepted; C21.2.09 remains unstarted meanwhile.

### B10. Mandatory future acceptance matrix

| Area | Required positive and negative evidence |
|---|---|
| Strategies | choose live/delete parents, authenticated manual merge, delete, keep_both; genuine original encrypted Legacy/Content parents and local source, Stage/null and HTML/plain Content routes, valid ID0/ID1; invalid result/route/selected/retained snapshots and source size/quota boundaries. |
| Causality | 2, 3 and 64 parents; all edges, revision=max+1, primary/additional equality, sorted uniqueness, missing ancestor, cycles, extra tip, wrong scope, prior Resolution parent, clone child, post-Resolution new fork. |
| Groups/publication | Remote ID/generation differs from local; exact local generation CAS; new tip between prepare/commit; published local seal/coalescing vs frozen admission; no unpublished-intent substitution; historical proof survives closure and later edits. |
| Atomicity | Inject failure before/after every add/put and transaction completion, after original before clone, after head before proof, clone collision in another project/tombstone/pending owner; old source/evidence/counters exact on abort. Lost response and crash after commit replay without writes. |
| Orphan/replay | Resolution before all parents, before group/dependencies, parent arrival after reopen, bounded retry reaches late prerequisites without ACK skipping; duplicate event/sequence, conflicting second Resolution, forged closure/head, corrupted envelope and orphaned half-state reject. |
| Lifecycle | Wrong account/device/bootstrap, stale auth epoch, logout, key lock/rotation/invalidation, profile closure, two tabs/exclusive lock, source and Metadata/Stage drift at every await and commit boundary; no persistent authority flags. |
| Migration | Populated real v9 source/history/legacy intents/I2/C3 accepted formats unchanged, old explicit v9 opener rejected, blocked connection, structural corruption abort rollback, unlock AEAD corruption blocks writes, full renderer and disk/browser profile restart. |
| Prefix/regressions | Four-strategy authentic apply proof is required; fake outer hashes/inbox10 are insufficient. Original/clone count once; received/orphan/own echo/unsupported families remain barriers; no gap skipping or ACK>prefix/pull. Accepted Legacy self-echo, peer Content, mixed conflicts, local-unsealed frozen history, I2 ownership and unrelated Notes remain covered. |
| Chromium/CI | Real browser/profile/source/history/apply using disposable data; controlled HTTP fixtures may serve actual contracts, never fabricate reader capability. Zero page errors; no Content seal/outbox/push/self-echo or automatic capability/ACK activation. Add focused tests and real-browser scenarios as mandatory workflow checks when implemented. |

### Простыми словами

Браузер уже понимает текст Resolution-v2, но ещё не проверяет и не применяет решение
конфликта целиком. Для этого нужно доказать все исходные версии, неизменность
заметки и состава конфликта, а затем одной транзакцией применить результат. При
«сохранить обе» обе заметки и состав проекта должны измениться вместе.

Выбран полный browser reader с будущей IndexedDB v10: старые записи сохраняются,
а новая история явно описывает несколько родителей и завершение конфликта. Сейчас
это только проект; база всё ещё v9. Следующий пакет — строгие читатели новых
записей и проверка графа истории, без миграции и записи новых результатов. После
реализации, перезапусков и независимой приёмки можно вернуться к честному объявлению
capability и dormant gate. Content upload остаётся выключенным, C21.2.08 заблокирован.

## C21.2.08C — strict future-v10 readers / authenticated DAG / no migration

**LOCAL COMPLETE / REMOTE CI PENDING — READERS ONLY.** C21.2.08B is independently
REMOTELY ACCEPTED — DESIGN ONLY: SHA `b641612a66494fdc025b9bdb36aa54325189bf85`,
Cloud `39216444583` SUCCESS, 6/6 required jobs (owner supplied). C21.2.08A remains
accepted AUDIT ONLY; C21.2.08 sealing BLOCKED; C21.2.09 NOT STARTED. Official84.0%;
C21/C21.2 IN PROGRESS; C21.1.06 NOT LOCAL COMPLETE; ready=false.

### Audit and bounded implementation

Before implementation, existing candidate1 Legacy/candidate2 peer Content/candidate3
own Content dispatch, single-parent head1/frontier, open-only group1, frozen
local_version1, inbox1–9 and original-wire/crypto1/AAD1 joins were inspected. Existing
history event index is unique across event-bearing records; heads/transitions do
not acquire a duplicate event_id. Existing v9 validators reject unknown versions;
no accepted validator or active persistence/prefix reader was changed. Native C17
publication/strategy checks remain reference semantics only.

| Isolated reader | Implemented behavior |
|---|---|
| resolutionRecords.ts | Exact B5 outer allowlists for Resolution4, Head2, GroupTransition2, ResolutionProof1 and inbox10; strict scope/bootstrap when supplied, UUIDs, canonical times, safe integers, digest/envelope/transport/parent checks. Future dispatcher delegates old leaves to their unchanged validators. |
| resolutionAuthentication.ts | Reopens genuine original protocol2 Resolution or protocol3 codec8 ID0/ID1 wire and evidence AEAD under original Note crypto1/AAD1; exact inner schema and public identity; original payload/descriptor/source-device binding; genuine encrypted source before/after; parent publication and historical group/head witnesses; all four strategy equivalence rules. Explicit normal-user account/auth-epoch/key/profile wrapper; currentness checked after asynchronous work. No persistent authority token or apply/ACK certificate. |
| resolutionDag.ts | Scoped full-parent graph, unique event/record identities, 2..64 parents, max(parent revision)+1, missing/cyclic/cross-scope ancestry rejection, all-parent frontier consumption. One keep_both event with distinct original/retained result anchors, no duplicate event or clone genesis; exact retained ID ownership and later scoped child. |
| Historical lifecycle | Resolution authentication first validates immutable leaves, pre-closure group/working source and prior ancestors; then closure and resulting graph. No self-justifying parent proof. Old group1 remains literal open; only a fully authenticated matching transition gives effective resolved. Extra/dangling transitions or inbox10 reject; at most one effective open group. Later unresolved forks and old historical output projections can coexist. |

These modules are deliberately absent from active BrowserPersistence composition.
They take/read snapshots and return read-only interpretation, never schedule IDB,
HTTP, source/head/group/outbox writes, capability declaration or prefix qualification.
Current WEB_DATABASE_VERSION remains9, same12 stores/indexes/key paths; no migration.
The future v10 format gate is still a separate package and cannot open new formats
until its consumers are ready. The authenticated DAG result is not an ACK token.

B5 field sets are unchanged. Reader details for existing digest fields are explicit:
wire_digest hashes `{protocol_version,item}` using the retained item; payload_digest
hashes the canonical Resolution; wire_frame_digest is SHA256 of original AEAD
plaintext bytes (before frame normalization), and wrapper_payload_digest hashes the
canonical Content wrapper (null for protocol2). Ordinary parent outcome digests
must join exact original candidate/inbox wire, not merely matching event IDs.
For local_accepted, candidate + actual accepted outbox/receipt + frozen admission
are publication evidence. A missing self-echo is represented in the existing
inbox_digest field by the hash of canonical null; it never fabricates an inbox row
or grants self-echo. If retained inbox exists, its exact digest/wire must match.
The evidence AEAD authenticates this commitment alongside all publication witnesses.

Historical dependency_digest is checked against the exact authenticated inner
identity and final proof. Fresh original Metadata/Stage crypto establishes current
coverage separately; hashing today's changed owner heads cannot reproduce an old
snapshot. Original wrapper dependencies/bootstrap must still match and remain
covered. Historical source witnesses are decrypted and compared with the proven
working branch/result, not today's mutable Note text. Legacy source admission
retains its accepted metadata rules; Content source admission stays separate.

Bounded reading: dedicated evidence limit64MiB, record limit128MiB; precheck encoded
ciphertext size/canonical base64 bits before allocating decoded evidence; exact
UTF-8/JSON byte budgeting, sequential parent opening, cleared temporary byte buffers.
A snapshot above16384 history records is rejected in full, never truncated into a
false frontier. This is a fail-closed read budget, not a new durable field or an
activation/readiness claim. Future large-history paging/resource acceptance remains
required before production reader capability can be declared.

### Validation and limits of acceptance

Focused suites: **58 PASS / 2 files**. Positive authentication uses real AEAD and
actual protected ordinary parent history for the four strategies, 2/3 parents,
local accepted Legacy publication before self-echo, protocol2 and codec8 ID0/ID1;
wrong key/ciphertext, public/inner identity, source and parent/closure forgery reject.
64-parent case checks structural DAG/frontier over genuine original-AEAD ordinary
leaves; it is **not** a claim of 64-parent protected Resolution apply. The initial
64-parent setup through repeated existing apply exceeded the bounded test time;
it was replaced by the isolated reader/DAG case, not a capability stub or a skipped
required check. Real mutation/transaction acceptance is reserved for the apply slice.

Affected existing suites: **701 PASS / 22 files** (Legacy, peer/mixed Content,
local-unsealed/post-seal history, I2/C3, prefix/ACK and frozen codecs). New mandatory
Chromium test opens a disposable real v9 profile, creates genuine encrypted Legacy
capture/history through existing runtime, verifies isolated future helpers do no
writes/HTTP or new proof qualification, and compares all12 stores after full disk
profile restart: PASS, page errors0. It does not store/authenticate a future applied
Resolution in IndexedDB or claim protected apply acceptance. No gates were relaxed.
New focused suites and browser runner are mandatory in Cloud workflow; filters
preserved/extended, no skip/xfail/continue-on-error. Typecheck, production build,
workflow validation and git diff --check PASS; protected bytecode unchanged.

### Простыми словами

Новые читатели проверяют шифротекст Resolution, его родителей и опубликованные
версии, а затем историческое завершение конфликта. Они учитывают всех родителей,
а не только первого. При keep_both одно событие имеет два результата с разными
ID заметок; чужая заметка не может воспользоваться таким родителем.

Завершённая группа остаётся в истории: отдельное проверенное доказательство сообщает,
что она разрешена. Читатели ничего не меняют в заметках и не подтверждают новые
события серверу. База остаётся v9, новые форматы в неё не записываются. Следующий
ограниченный пакет — C21.2.08D, compatibility gate v10; реальный apply и capability
потребуют отдельных реализаций и приёмки. Content sealing/upload остаются выключены.

## C21.2.08D — IndexedDB v10 compatibility gate / safe migration

**LOCAL COMPLETE / REMOTE CI PENDING — MIGRATION ONLY** (2026-10-19).
C21.2.08C **REMOTELY ACCEPTED — READERS ONLY**: implementation SHA
`2ef393383d7e7e558485ae610dcf2856e7a4e846`, Cloud `39224079273` SUCCESS,
all 6 required jobs SUCCESS (owner supplied; no Actions polling).
Starting branch6.0 local/origin match that SHA; clean preflight.

The active database target is10, with the same12 stores, key paths and indexes.
Explicit native 9→10 versionchange is structural validation only: no conversion,
repair, record rewrite, deletion or fabricated evidence. The native transaction
aborts completely on schema/record/request/transaction failure, retaining version9
and original encrypted rows. Supported old1–8 upgrade validators remain unchanged;
new/empty databases create the same schema directly at10.

Dedicated indexedDbV9Migration.ts uses current version dispatch and Content authority
inventory joins rather than reusing the v8 gate. It checks identity/account/device
ownership (opener plus unique schema indexes), binding/bootstrap, encrypted source
outer records, Note-to-project source revisions, history/head/group/frozen versions,
Legacy1/Content I2 intents, candidate1/2/C3, outbox1/receipt1/R2, inbox1–9/proofs,
owner histories, event/sequence uniqueness, dense shared intent/outbox ordinals,
exact pull high-water and ACK≤prefix≤pull. Proven prefix must be contiguous and
cannot cross received or inbox9 self-echo barriers. Pending snapshots match current
source; parent and I2/C3 historical Metadata/Stage dependency witnesses must exist.
Encrypted project member_ids and plaintext content cannot be inspected keylessly:
existing source AEAD/member checks remain mandatory after unlock. Envelope structure
is checked during upgrade; successful migration is never an AEAD certificate.

Active consumer compatibility audit:

| Consumers | Compatibility decision |
|---|---|
| persistence.ts / syncDurability.ts | Explicit target10, exact physical schema, existing account/device and wire validators; no new record producer or generic unknown-format fallback. |
| noteHistory.ts / noteHistoryRecords.ts | Existing candidate1/2/3/head1/group1/local_version1 contract retained; unknown Resolution4/head2/transition rejected. Existing joins and current-key opening remain required. |
| noteIntents.ts / contentNoteIntents.ts / contentAuthorityInventory.ts | Legacy1 and I2 dispatch, C3/R2/inbox9 joins, shared ordinals and source ownership preserved. I2 stays dormant in production; no C3 producer added. |
| localAuthority.ts / legacyNoteApply.ts / contentNoteApply.ts / noteTransportGateway.ts | Current source AEAD/auth/key/session/CAS gates retained. Unsupported future history fails before source changes; existing I2/C3 ownership blocks Legacy/source-only overwrite. |
| provenPrefix.ts / ackPrerequisites.ts / registry and transport gates | Existing current-key proof qualification unchanged. Unknown history/inbox rejects; inbox9 remains an unqualified barrier; migration never advances prefix or ACK. |
| resolutionRecords.ts / resolutionDag.ts / resolutionAuthentication.ts | Isolated read-only future dispatch from accepted .08C; no production import, durable new-format write, readiness or ACK certificate. |

Version10 is an old-opener exclusion boundary, not permission to persist future
Resolution variants. Active old-format readers may reject unsupported future rows;
Resolution producers remain absent. This package does not assert full v10 Resolution
apply compatibility. A future producer still requires every consumer's explicit
new-format dispatch and protected apply/prefix acceptance before activation.

Owned sessions already revoke on versionchange, abort/drain tracked transactions,
close their connection and release the exclusive writer lock. An unrelated native
connection can block upgrading: return upgrade_blocked, never force-close another
tab, abort any delayed failed-open upgrade and allow a later retry. Old explicit9
openers receive VersionError after upgrade; there is no downgrade/clear/recreation.
Reopen and disk restart retain encrypted source/history/intent/transport/cursor rows.
New session auth/account binding/current AMK lease are needed again; no positive
authority token is persisted. Wrong keys, AEAD corruption or invalidated auth retain
evidence and fail closed after unlock, with no downgrade.

Validation: 42 focused v9 migration tests PASS; 236 affected migration/I2/C3/
Resolution regressions PASS (11-file run included the first39 migration cases).
Final mandatory affected C21 suite: 1895 tests PASS /64 files, including all42 new
cases. Chromium persistence acceptance PASS, including15 new disposable native
v9→v10 profiles, rich Legacy/peer Content/mixed frozen history, genuine dormant I2,
blocked upgrade/retry, native abort, browser interruption, structural corruption,
old9 VersionError, post-unlock AEAD/key failure and exact full disk reopen. C3/R2/
inbox9 specimens have real AEAD in unit tests; no browser C3 producer is claimed.
Separate Resolution readers Chromium v10 restart PASS. New migration scenarios:
HTTP0, new ACK0, page errors0; existing broader controlled transport scenarios retain
134 fixture API calls including17 bounded ACKs, no push or Resolution calls.
Typecheck/production build PASS (existing Vite dynamic-import/chunk-size warnings).
Workflow YAML, both path filters, mandatory focused and awaited browser coverage,
and git diff --check PASS. Initial stale version expectations were updated; final
checks have no failures or skips. Backend/native suites not required and not run.
Protected .pyc SHA256 unchanged; no Actions polling/waiting.

No Resolution4/Head2/GroupTransition2/inbox10/proof1 creation, protected apply,
Resolution producer, new Note capability, Content sealing/upload/self-echo,
positive Resolution ACK or production writer activation. Existing bounded ACK
semantics remain intact. Official84.0%; C21/C21.2 IN PROGRESS; C21.1.06 NOT LOCAL
COMPLETE; C21.2.08 functional sealing BLOCKED; .09 NOT STARTED; ready=false.
VPS security release gate, checkpoint history and roadmap numbering unchanged.

### Простыми словами

Обновляется только номер базы и проверяется согласованность её записей. Проекты,
заметки и зашифрованная история не переписываются. Если проверка или обновление
прерваны, база остаётся прежней v9. После успешного перехода старый клиент v9
получит отказ, чтобы не читать базу по устаревшим правилам. Разблокировка ключа и
проверка шифрования нужны заново; сам переход версии не доказывает подлинность
содержимого. Resolution apply и отправка Content остаются выключенными. Следующий
ограниченный шаг — C21.2.08E, read-only planner для Resolution-v2.

## C21.2.08E — Browser Resolution-v2 read-only planner / no apply

**LOCAL COMPLETE / REMOTE CI PENDING — PLANNER ONLY** (2026-10-19).
Starting branch6.0 local/origin `57a80c62e1e4bb0468b636f1fecf3ab89869451c`, clean.
C21.2.08D **REMOTELY ACCEPTED — MIGRATION ONLY**: same implementation SHA,
Cloud `39234175733` SUCCESS, all6 required jobs SUCCESS (owner supplied).
C21.2.08C REMOTELY ACCEPTED — READERS ONLY; .08A REMOTELY ACCEPTED — AUDIT ONLY.
No Actions polling/waiting. Official84.0%; C21/C21.2 IN PROGRESS; C21.1.06 NOT
LOCAL COMPLETE; C21.2.08 functional prerequisite BLOCKED; .09 NOT STARTED; ready=false.

Audit confirmed current IndexedDB10/same12 stores, intact v9 migration and isolated
future readers. Existing ordinary protected apply can produce genuine open group1,
original candidate1/2, encrypted working source and actual applied/conflict inbox
witnesses; Legacy sealing plus immutable acceptance can publish a frozen local
branch. No Resolution4/closure/proof needs to be invented to examine a received
Resolution. Native C17 strategy/collision semantics are reference only; no SQLite,
Tauri or native authority is reused.

resolutionPlanner.ts is a dormant internal browser module, absent from normal
persistence/editor/scheduler composition. It requires the existing private verified
device token, normal user/account binding, current auth epoch/AMK lease and live
owned profile. Registration is a separate existing prerequisite; planner never
registers a device, performs HTTP, changes capability or persists an authority flag.
The real browser scheduler checks durable identity/device/binding on readonly reads.

| Boundary | Read-only admission |
|---|---|
| Inventory | Strict readonly native cursors scoped to this account; select relevant project/Note history; retain full account identity reservations. Cursor/proofs/outbox/receipts/intents/source/bindings/owner heads are pinned and reread before returning. |
| Original wire | Crypto1/AAD1 under original canonical account/project/Note; protocol3 exact codec8/frame1 Resolution2 with account/device wrapper and ID0/ID1; protocol2 separate frozen C17 decoder, project HTML/stage-null route, no fallback or invented Content dependency. Original descriptor/event/sequence/revision/canonical time are bound; own source rejected without author authority. |
| Parents / group | Accepted DAG and strict current history, 2–64 exact sorted parent IDs, full frontier/common ancestor/revision, actual local group generation/member witnesses. Fresh original candidate AEAD, real retained apply/conflict proof or exact accepted local seal/outbox/receipt plus frozen admission. Unsealed I2/pending intents are never publication. Remote group UUID/generation are sender labels mapped by exact authenticated parents/snapshots/scope/ancestry, not UUID equality. |
| Dependencies | Fresh authenticated live Metadata ancestry and exact Stage reference coverage for both outputs; unavailable/changed/deleted authority blocks. Legacy uses real binding/bootstrap and authenticated project/source contract. |
| Source | Existing current-key project/member/Note authentication and private whole-project source token; encrypted working projection and decrypted wire Note must equal the displayed published branch. Newer incompatible local content blocks preparation. |
| Strategies | choose_version equals the selected published live/tombstone parent; manual_merge uses only authenticated valid sender upsert; delete requires original-route tombstone; keep_both uses exactly two live parents, copied selected output and the other output with only frozen ID/time changes. No receiver merge/ID/time generation. |
| Clone | Account-wide live/tombstone Notes, other projects, history/anchors, intents, outbox/receipt identities, inbox and authenticated pending Resolution reservations. An authenticated ordinary future child referencing this Resolution is a reference, not an allocated clone. Unknown/unproven reservations fail closed. |
| Token | Empty opaque object, module-private WeakMap, exact runtime/scope/device/auth/key/profile and inventory/source/group/publication/dependency binding. Bounded status explicitly says commitAuthorized=false and ackAuthorized=false. inspect rechecks source and inventory; drift/revocation rejects and no token is accepted by prefix/ACK. |

Resource admission uses native cursors, not an unbounded getAll followed by a late
size check: at most16384 rows/store and32MiB aggregate encoded inventory, plus16MiB
aggregate opened ordinary history material. Each cursor callback checks lifecycle;
parents open sequentially; existing decrypted-source8MiB/4000-Note and smaller
500-codepoint title/300000-codepoint content limits stay unchanged. Oversized valid
network material gets an explicit resource/source blocker, never truncation or a
positive plan. Temporary owned crypto/digest/serialization byte arrays are wiped.
No arbitrary storage/crypto errors or plaintext are returned as diagnostics.

Orphans get bounded missing_parent/missing_publication/missing_bootstrap/
dependency_unavailable/missing_conflict errors. Wrong identity, forged proof, extra
tips, source drift and clone collision reject without changing inbox or source.
Repeated prepares are read-only. After logout/account/device/key/profile or inventory
change a token cannot authorize further use. A future .08F transaction must
independently revalidate/CAS every witness before its first write; this token is
not an accepted Resolution proof, replay ledger or prefix certificate.

Genuine-witness boundary: accepted browser paths currently produce ordinary open
conflicts, not committed Resolution4/head2/closure/inbox10. The planner does not
manufacture those witnesses or admit a prior Resolution result as a published
parent merely from its UUID/hash. Closed-history replay, post-Resolution conflict
planning and durable result-anchor continuation are not claimed; they need actual
future apply/consumer-dispatch acceptance. C3 cannot be substituted for an accepted
Legacy frozen branch, and no new Content author/self-echo chain is claimed.

Validation: 81 focused planner tests PASS. Final mandatory affected C21 suite:
1976 tests PASS /65 files, including Legacy/Content/I2-C3, v10 migration,
Resolution readers/DAG and prefix/ACK regressions. Genuine protected ordinary
history supplies2/3 parents and the64-parent Legacy conflict; no structural-only
DAG specimen is claimed as positive conflict admission. All four strategies pass
for protocol2 and protocol3, including current Stage/plain/ID1 coverage; genuine
sealed/accepted frozen Legacy parent, pending I2 barrier, ciphertext/key/scope,
publication/group/source/dependency/collision/resource and lifecycle negatives pass.

Real Chromium10 disposable disk profile PASS: two protocols × four strategies,
actual encrypted local source, imported Metadata, ordinary protected apply and
conflict preservation, original Resolution wires, full browser/disk restart and
repeat fresh authenticated planning. Every native readwrite/add/put/delete/clear
attempt during planning is trapped: attempts0. Inbox remains received; outbox,
receipts, source, history and cursors stay exact. Missing parent/newer genuine local
source edit block; key/logout revoke; competing tab gets writer_busy. Planner HTTP0,
push0/new ACK0/Resolution writes0/page errors0. Four controlled registration calls
are external setup/rebind fixtures, not planner traffic or a production-server
registration acceptance claim. Stage/plain and64-parent admission are focused
real-AEAD/runtime tests; browser coverage uses genuine project HTML peer conflicts.

Typecheck/production build PASS; existing Vite dynamic-import/chunk-size warnings.
Workflow YAML/mandatory focused spec/browser step and both path filters, history/
release-gate preservation and git diff --check PASS. Initial fixture-reference,
stress-setup and TypeScript narrowing issues corrected; final failures0/skips0.
Backend/native suites unnecessary and not run. Protected .pyc SHA256 unchanged.
No GitHub Actions polling or waiting.

IndexedDB remains10; no migration/store/index/wire/backend/native changes. No
Resolution protected apply/producer/Resolution4/head2/transition/inbox10/proof write,
Content sealing/upload/self-echo, new Note capability, production Content writer,
Resolution prefix/ACK qualification or automatic retry scheduler. Existing Legacy
behavior and cross-family barriers remain unchanged. VPS security release gate,
previous checkpoint history and roadmap numbering remain intact.

### Простыми словами

Планировщик проверяет входящее решение конфликта: открывает исходный зашифрованный
пакет, доказывает каждую опубликованную родительскую версию и проверяет, что состав
конфликта, его поколение и текущая заметка всё ещё совпадают с доказанной историей.
Идентификатор группы у другого устройства может отличаться; сопоставление основано
на версиях и их происхождении. Проверяются выбор версии, готовое объединение от
отправителя, удаление и сохранение обеих заметок. Для второй заметки дополнительно
проверяется, что её идентификатор не занят, включая удалённые записи и историю.
Новая локальная правка не может быть молча заменена старым решением. Успешная
проверка возвращает только временный приватный токен: ни заметки, ни история,
ни подтверждение серверу не меняются. Следующий шаг .08F должен добавить отдельно
проверенную атомарную запись результата, истории и обеих заметок при keep_both.

## C21.2.08F — Browser Resolution-v2 atomic protected apply / dormant

**LOCAL COMPLETE / REMOTE CI PENDING — DORMANT APPLY ONLY** (2026-10-19).
Branch6.0 starting local HEAD/origin `45051917ba37a943e6af6d26c6746025d2c65e2d`,
clean; exact remote ref independently checked. C21.2.08E **REMOTELY ACCEPTED**:
SHA `45051917ba37a943e6af6d26c6746025d2c65e2d`, Cloud `39262249088` SUCCESS,
6/6 required jobs SUCCESS (owner-supplied acceptance; no Actions polling).
C21.2.08C/D remain REMOTELY ACCEPTED; .08A AUDIT ACCEPTED, functional gate incomplete.
Official progress84.0%; C21/C21.2 IN PROGRESS; C21.1.06 NOT LOCAL COMPLETE;
C21.2.08 FUNCTIONALLY BLOCKED; .09 NOT STARTED; ready=false. No roadmap renumbering.

The dormant planner's atomicApply() factory is the sole narrow handoff. Private
WeakMaps bind planner/apply tokens to the exact runtime, scope, source token,
normal-user auth epoch, verified device, AMK lease and profile. Apply preparation
repeats genuine planner authentication and rejects inventory drift; no opaque-token
DTO cast or caller-supplied plaintext/proof authority. The protected local hook
accepts only this private handoff and its exact bound local runtime. All original
wire/parent authentication, source encryption, evidence creation and digest work
finish before the native readwrite transaction. Original encrypted wire is retained
byte-for-byte; no reframe, recompression or synthetic parent publication.

Both protocol2 Legacy Resolution and protocol3 Content codec8 Resolution support
choose_version, manual_merge, delete and keep_both. Source uses existing encrypted
local_format1/record1, local Note revision0, one project source_revision increment,
unchanged project metadata and complete membership including tombstones. keep_both
uses the sender's distinct retained ID and timestamps; account-wide allocations,
other projects, tombstones/history/intents/outbox/receipts/inbox/reservations are
checked during fresh planning and pinned again by transaction CAS plus the native
unique identity index. A genuine future child reference does not allocate a clone.

Exact accepted B5 records only: immutable Resolution4, append-only GroupTransition2,
original Head2 and optional retained Head2, inbox10/ResolutionProof1. One event-bearing
Resolution, no clone genesis, no group1 lifecycle rewrite or losing-branch deletion.
Genuine evidence AEAD uses crypto1/AAD1 under the original Note context and exact
resolution_format/kind/identity/authenticated_payload/parents/group_snapshot/
head_before/source_before/source_after fields. Original frame, published parent
witnesses, pre-closure group/head and encrypted source outputs authenticate before
any write through the accepted future-v10 reader. Acyclic digest order is Resolution
→ transition → typed heads → proof → inbox. Public metadata contains no Note plaintext.
Evidence64MiB/record128MiB bounds remain; the existing32MiB/16384-row bounded
inventory limit is also checked on the predicted committed state before writing,
so resource-limited results are rejected rather than committed beyond replay bounds.
Existing local8MiB/4000-Note and smaller title/content admission limits remain.

One strict native transaction covers inbox/cursors/projectBindings/ownerHeads/
legacyNoteHistory/legacyNoteIntents/localProjects/localNotes/outbox/receipts; the
existing session scheduler adds identities/accountBindings and writer/profile checks.
A bounded cursor scan re-reads the entire account inventory, including original
received wire/sequence, cursor, binding/bootstrap, Metadata/Stage authority, all
parents/publications, project and complete source, group/frontier/heads, intents,
outbox/receipts and clone reservations. Every essential byte must equal the private
snapshot before any write. The protected source hook additionally checks the whole
project token and original/clone identities. Ordered writes add Resolution/closure,
update original/add clone head, put original/add clone source, put project, put inbox10.
Any stale input, constraint, quota error or abort rolls back every store. Only native
transaction completion returns success. Auth and key invalidation synchronously
abort pending apply; existing session closure aborts its tracked transaction. Every
asynchronous IDB callback checks lifetime. Tokens are single-use; no automatic retry.

Exact replay is read-only under fresh auth/key/device/profile: reopen original AEAD,
evidence, parents, closure, proof and both typed result anchors; compare encrypted
current outputs and project to the authenticated output witness. Missing half-state,
conflicting sequence/wire, corruption or source drift rejects without repair. No
nonce/ciphertext/proof generation, counter increment, clone or write during replay.
This F replay intentionally covers the exact still-current committed result. General
historical source advancement, post-Resolution ordinary continuation/new forks and
contiguous-prefix qualification remain later acceptance work, not claimed here.
Missing prerequisites retain received inbox/source/history/cursors unchanged with a
bounded blocker. Old production readers remain strict and fail closed on unsupported
new leaves; only the isolated authenticated future-v10 reader validates these results.

Validation: 55 focused real-AEAD apply tests PASS, including both transports/all four
strategies, Stage/plain/ID1 routes, genuine accepted local frozen parent,2/3/64
parents, future clone-child reference, private token/epoch binding, whole-inventory
CAS, orphan/wire/publication blockers, corrupted replay/half-records and all ordered
write boundaries. Final affected suite2039 PASS /67 files (includes55 focused and
8 key-context cases): Legacy/Content/I2-C3, v10 migration, DAG/planner and prefix/ACK.
Real disposable Chromium v10 PASS:8 genuine applies,24 native fault rollbacks,
8 full disk/browser restarts,16 zero-write replays; actual key/logout/profile-close
invalidation before completion, competing-tab writer_busy and native device identity
drift reject safely. No fabricated positive authority; push0/new ACK0/page errors0.
22 controlled device-registration fixture calls belong to external setup/rebind,
not apply/replay traffic. Typecheck/production build PASS (existing Vite warnings);
mandatory Cloud spec/browser step, strict workflow YAML, both path filters, historical
document preservation and git diff --check PASS. Final failures0/skips0; initial
test-environment/fixture assertions and TypeScript annotations corrected.
Backend/native suites unnecessary and not run; remote CI not polled.
Protected .pyc SHA256 unchanged; existing history and VPS Security Hardening &
Security Audit RELEASE GATE preserved. No GitHub Actions polling or waiting.

IndexedDB10; migration NONE; new stores/indexes0; no wire/backend/native changes.
No normal BrowserPersistence/editor/scheduler integration. Resolution producer,
Content sealing/upload/new self-echo, new Note capability, production Content writer
and Resolution prefix/ACK remain OFF; existing Legacy behavior and cross-family
prefix/ACK barriers unchanged. No pull/proven-prefix/ACK cursor, receipt, outbox,
intent or ordinal mutation. Full Web synchronization and full C21.2.08 are not complete.

### Простыми словами

Изолированный механизм умеет применить полученное решение: выбрать версию, взять
готовое объединение отправителя, удалить заметку или сохранить обе. Перед записью
он заново проверяет шифротекст, опубликованные версии и текущие данные. Заметки,
состав проекта, история решения и доказательство записываются одной транзакцией.
Поэтому keep_both не может оставить только половину результата: при сбое сохраняется
исходное состояние, при завершении появляются все записи вместе. После прерывания
клиент проверяет сохранённое решение; точный повтор не создаёт вторую копию заметки,
новый шифротекст или повторное увеличение счётчика. Повреждённая или неполная история
останавливает проверку, автоматического ремонта нет.

Этот путь и новые читатели остаются изолированными от обычной синхронизации.
Старые читатели не начинают молча принимать неизвестные форматы. Отправка Content
и подтверждение Resolution серверу выключены: ещё нужно отдельно доказать чтение
исторических результатов после дальнейших изменений и безопасный непрерывный
подтверждённый префикс. Следующий шаг — C21.2.08G, historical proof / contiguous prefix.
