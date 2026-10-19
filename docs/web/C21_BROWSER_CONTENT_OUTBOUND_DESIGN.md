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
