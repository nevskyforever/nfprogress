# C18.6.01 — authenticated Project cover acceptance

Baseline: `e11d6b6fc453b218738d1f6a0dd5b34a9eebb750`, branch `6.0`, HEAD =
origin/6.0, clean preflight. C18.5 independently CLOSED: implementation
`9b2c7594589b7dfa58b5b7fe83905f0336a7c710`, SQLite 37288645324 SUCCESS;
correction baseline, Cloud 37358324509 SUCCESS, all four jobs successful.
C18/C18.6 IN PROGRESS, official progress exactly 77.0%.

## Current-state map (audited before production changes)

* `projectMetadataCodec.ts` and native `project_metadata_sync.rs`: exact 12-field
  metadata v1, codec ID1, causal heads, generation/revision, full-tip conflicts,
  explicit reconciliation, immutable events/outbox, authenticated apply ledger.
* `ProjectMetadataMigrationRuntime`: explicit capture; exact sealed retry;
  retained inbound encrypted events; shared account ACK after native apply.
  Imports page verified histories before shell creation. Existing reader used
  sequence paging and requires persistent fairness for unavailable cover refs.
* `projectCoverPreparation.ts`: JPEG/PNG/WebP source <=20MiB; prepared JPEG
  <=2MiB, crop 2:3. Existing JPEG Data URL is local projection/migration source.
* `projectCoverCrypto.ts`: existing C11 `project_cover` object context includes
  authenticated user, project and client UUID blob ID; XChaCha20-Poly1305 1/1.
  Actual plaintext limit is 2MiB, not the assumed 8MiB. No COVER_AAD_PREFIX
  constant or separate cover crypto scheme exists in this branch.
* `encryptedCovers.ts` / backend encrypted blob router/service/store: actual API
  is PUT `/api/v1/cloud/projects/{project}/covers/{blob}` and GET same path;
  ciphertext <=2MiB+16, not 11MiB. Client-generated stable opaque UUID,
  PostgreSQL advisory serialization, write-once filesystem + immutable row,
  exact nonce/version/size/ciphertext digest duplicate detection; different
  same-ID bytes reject 409. Unknown scoped blob returns 404
  `encrypted_blob_unavailable`; missing storage 503; corrupt storage 503.
  No normal lifecycle DELETE/emergency-delete frontend method exists.
* Project dialogs save `cover_image`; native project metadata save intercepts
  portable edits but excludes cover. Engine normalizes local Data URLs; SQLite
  mirrors cover in local payload. No cover migration/runtime/upload authority
  exists. Local-only save must retain the local path with no binding creation.
* SyncDevice capabilities currently cover metadata v1/mode3 and codecs8–13;
  none proves cover-reference v2 support. Reader capability cannot be inferred
  from an old content/game version declaration.

## Bounded decisions

Preserve actual crypto/API/resource limits and all historical bytes. Cover bytes
are immutable Class A; reference/null removal is Class B within Metadata v2,
codec ID1. Reference v1 exact fields: version, blob_id, crypto_version,
aad_version, mime_type, plaintext_size, key_fingerprint, envelope_sha256.
Fingerprint hashes the existing derived cover object key, inside encrypted
metadata only. SHA256 hashes canonical encrypted envelope JSON (ordered
`aad_version,ciphertext,crypto_version,nonce`, canonical base64url bytes);
never plaintext. Context-bound AEAD verifies account/project/blob identity.

Schema38 is necessary: existing metadata immutable tables cannot hold mutable
upload progress and durable JPEG/blob authentication proof without changing their
contracts. Add only local cover intents, verified material, typed blockers;
reuse existing Metadata events/outbox/apply receipts/tips and schema37 reader
visits. A new non-secret SyncDevice reader version (0 or2) requires one forward
Alembic capability migration; no blob model/storage migration or redesign.

## Durable publication and apply

Explicit per-project publication captures the existing canonical JPEG Data URL
without recompression. Invalid/unsupported legacy sources remain local and block
publication. Startup, login, unlock, project opening and background cycles never
capture a legacy source. After activation, ordinary editor replacement/removal
captures a durable candidate and schedules the existing bounded sync cycle.
Local-only projects cannot capture a cloud intent or acquire a binding.

Publication states are captured → sealed → uploaded → metadata_pending → active,
with typed blocked states. The source, causal parents, stable blob UUID, encrypted
envelope and reference are immutable after their respective seal boundaries.
PUT exact retry handles a lost upload response without creating another blob.
The client GETs and authenticates the stored envelope before preparing Metadata.
Metadata sealing/upload retry reuses the existing exact outbox/event/self-echo
contract. Null removal needs no blob upload and never invokes emergency delete.

Incoming Metadata is authenticated first. Its strict reference then binds the
exact envelope, account/project/blob context, derived-key fingerprint, AEAD,
JPEG/MIME and exact size. Verified encrypted material and JPEG are committed to
an immutable local cache before Metadata apply. One SQLite transaction commits
Metadata head/receipt, reference, local Data URL projection, conflict evidence
and ACK proof. A failed transaction leaves the old projection/head intact and
the authenticated prepared material recoverable. Local cache/status is support
state; neither is a portable entity or an independent ACK cursor.

Missing 404/503 storage and invalid descriptor/digest/AEAD/JPEG are distinct
durable blockers linked to the retained encrypted Metadata event. Neither
rewrites the reference to null nor ACKs the event. Schema37 visit records rotate
retained events in bounded batches: unrelated later events can apply, while the
shared ACK prefix stays before the hole. Restoring the exact blob retries the
same event after reopen and advances ACK contiguously.

Concurrent cover replacements, remove/replace and name/cover edits use the
existing complete Metadata-tip conflict unit. Both refs/null branches survive;
resolution is causal, including a v1 branch resolved as v2 explicit null. Old
blobs remain retrievable. There is no field merge, LWW, GC or new authority.

## Capability and compatibility

Every registered device must declare metadata-cover reader version2 in addition
to mode3 before v2 publication. The backend checks this under the existing user
state lock. A v1-only device blocks publication; v1 histories/writers remain
readable and upgrade permits the original durable candidate to continue. No PKI.
The capability-only Alembic head is `c18_cover_readers`, descending from
`c18_game_readers`; fresh/prior-head/repeated upgrade and registered-device
preservation are tested. Existing encrypted blob storage is unchanged.

Metadata v1 canonical fixture/frame bytes, decode/apply and resolution remain
unchanged. Metadata v2 adds only cover_reference, including explicit null.
Cross-language vectors cover no-cover, cover, removal and resolution, codec ID1,
frame1, exact payload version and compression0. Unknown fields/header-version
mismatch fail closed. No codec14, C11 changes or other entity protocol changes.

## Acceptance evidence

* Real PostgreSQL + actual filesystem cover API/storage + production TS crypto
  + two distinct file-backed native SQLite databases: initial explicit migration,
  exact JPEG materialization, upload-before-reference, upload/Metadata lost
  response, self-echo, offline replacement, removal, concurrent replacement,
  remove/replace resolution, old blob retention, scoped authorization and server
  blindness pass. The test reopens each native database between calls.
* Missing-blob reception/reopen/recovery preserves the previous safe projection
  and blocks ACK. A later real Note8 applies while the Metadata hole remains;
  restored exact bytes complete the same event and both real backend ACKs
  converge. Native SQL-trigger interruption separately proves apply rollback.
* Restart boundaries: captured/sealed/uploaded intent, sealed Metadata outbox,
  accepted response lost, interrupted apply and retained missing event all reuse
  durable source/proof/event identity. No unauthenticated image is displayed.
* Strict ref/context/key/MIME/size/fingerprint/version/AAD/nonce/ciphertext/digest,
  truncated/oversized bytes and malformed JPEG negatives pass. Recomputed digest
  on modified encrypted bytes still fails AEAD. API same-ID different bytes409,
  exact retry, other user/project isolation and payload bounds remain covered.
* SQLite fresh and prefixes0–37 →38, populated37 containing previous entity
  evidence, reopen and immutable material/monotonic verification: 40 cover tests.
* Six-locale UI/help tested in Chromium: explicit publication and missing retry
  work in every locale; no untranslated non-Russian status strings. Normal save
  scheduling, malformed source and old-device blocking have focused tests.

## Coverage manifest and bounded validation

Cloud remains parallel, with independent disposable PostgreSQL services and
40-minute limits. No previous test selection was removed:

| Group | Baseline | Current selection | Local result |
| --- | --- | --- | --- |
| Mandatory foundation | 15 files /30 tests | same + cover gate/acceptance, 17 files /34 tests | 34 passed, 607.52s |
| Mandatory content-action | 11 files /22 tests | unchanged | 21 passed initially; exact stale-head expectation corrected/retest passed |
| Cloud/legacy regressions | 14 files /194 tests | unchanged | 193 passed initially; exact stale-head expectation corrected/retest passed |

Old union246 → new union250 unique PostgreSQL tests; zero mandatory skips,
no duplicate removal, no family lost or assertion weakened. The latest complete
cover acceptance and corrected Progress gate passed together with regressions
(195 passed); the remaining corrected Alembic-head test passed separately.
Completed accepted remote run37358324509 was read once for capacity: foundation
17:46, content-action18:47, regressions4:03. Cover remains in foundation with
meaningful margin; timeout was not increased and no CI rerun/poll was performed.

Other bounded local checks:

* Frontend existing workflow groups: 639 passed; three subsequently added tests
  passed in focused runs (current selected union642). Reference3, runtime6,
  Metadata runtime10 and cover UI3 are included. Typecheck/build passed.
* Rust library: 378 passed, one intentional headless bridge hook ignored; the
  hook runs in mandatory PostgreSQL acceptance. Additional conflict test and
  changed Metadata writer: 23 focused Metadata tests passed (current union379).
  cargo check passed; native Windows workflow filters retained.
* SQLite workflow group: 479 passed initially, three schema-fixture expectations
  corrected and exact retests passed; added populated37 test passed. Current
  selected union483, including40 cover tests. No new skips/xfail.
* Help/localization30 passed using native Cocoa Qt; generated frontend content
  check passed. Generation used explicit translations with zero network lookups.
* YAML structure, deterministic collection, affected Python syntax/imports,
  protected pyc evidence and git diff --check passed.

C18.6.01 **LOCAL COMPLETE / REMOTE CI PENDING**. C18.6/C18 IN PROGRESS, official
77.0%. Release gate, terminology audit and C21 local-Web-first remain intact.
No compression, external-file reattachment/path transport, arbitrary attachments,
telemetry or physical deletion/GC. Next slice only after independent acceptance:
C18.6.02 — LOCAL EXTERNAL FILES / EXPLICIT REATTACHMENT / PATH-LEAK ACCEPTANCE.
