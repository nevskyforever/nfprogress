# C18.8.01 — complete-project multi-device acceptance

Status: LOCAL COMPLETE / REMOTE CI PENDING. C18.8/C18 IN PROGRESS;
official progress77.0%.
No C18 points awarded and no C21/public release/deployment work.

Original implementation started at `10b3a39a1197bbd9f30edb9a04cb09cda5e810bd`.
The six unfinished C18.8 files were preserved through the separate storage
maintenance commit. This same slice resumes at
`a3da1f431baf7676a2277c13baf5300e4a76a711`; it was not restarted or rebased.

## Independently accepted prerequisite

C18.7.03 implementation `5f463653e3dbc5a6dad91295c4f371caf158c83c`, SDK recovery
`10b3a39a1197bbd9f30edb9a04cb09cda5e810bd`. Owner/GPT supplied Cloud38077802438
SUCCESS: Frontend admin, Android compression packaging, PostgreSQL mandatory
foundation/content-action and cloud/legacy regressions. SDK resolution, Web
build, Capacitor sync, exact assets, actual assembleDebug and final APK notice
verification all SUCCESS. Recovery-only diff did not trigger SQLite; accepted
C18.7.02 SQLite37973599074 SUCCESS remains applicable. C18.7 CLOSED by that
independent verification, not by this implementation task.

## Topology and production ownership

One synthetic authenticated account, connected Project P=`project-1`, two live
Stages S1/S2, one account folder F1 and local-only Project L on A. A/B/C use
independent registered identities and files `device-A/nfprogress.db`,
`device-B/nfprogress.db`, `device-C/nfprogress.db` under the isolated test root.
They share only the account's synthetic AMK and portable authenticated history.
Every headless native command exits/reopens its actual file-backed SQLite DB.
The backend is the real ASGI API with an isolated real PostgreSQL database and
real encrypted cover storage. No graphical/browser→Tauri dependency.

`test_cloud_c18_complete_project_acceptance.py` orchestrates existing acceptance
bridges. It does not reduce canonical events or choose winners in a replacement
sync engine: production TS codec/AEAD/sealing and production native guarded
appliers/ordinary writers/decisions own those operations. Mode3 mixed inbox and
the existing native shared-ACK proof own cursors. Seed SQL creates legacy/source
fixtures only; controlled blob availability and local F source are test stimuli.

Project Metadata carries name, goal2000, symbols, deadline2026-12-31,
personal goal400, auto-freeze, stage enablement and work-method preference.
Combined display is enabled later through a causal full Metadata record, after
map authorities are prepared. Normal manuscript writes belong to S1/S2 because
a Project in stage mode has no separate active project manuscript. Progress
uses S1 and its exact authenticated tips; the project aggregate remains derived.

## Supported authority/evidence matrix

| Family | Canonical/causal evidence | Integrated operation |
|---|---|---|
| Project Metadata | Canonical payload/ledger, complete event history, tips | Genesis, concurrent full-record renames, explicit resolution, cover transitions |
| Cover blob/reference | Exact immutable encrypted blob, authenticated envelope proof, durable JPEG/ref material | Upload before Metadata; GET404 blocker/restart/retry; explicit null removal, retain old blob |
| Stages | Independent structural canonical frames/ledgers/tips | S1/S2 create/import; later ordinary S1 metadata mutation |
| Stage Order | Full canonical permutation + authenticated stage heads | Exact live order S1/S2 |
| Project HTML Note | Existing C15 v1 history, Note head, authenticated inbox/projection | Bootstrap original history, read/self-echo, no codec8 re-genesis |
| Project plain Note | Note8 canonical receipts/head/projection | Explicit activation, safe event beyond cover hole, causal tombstone |
| Stage plain/HTML Notes | Note8 canonical receipts/head/projection, Stage dependency | Both supported routes on S1 |
| Project/Stage maps | Complete Map9 frames/history/tips/receipts | Both scopes, map-owned annotation capture and derived Notes |
| Derived map Notes | Normalized local projection matches authority on every peer | Annotation title/tags/checklist; no independent Note outbox |
| Documents | Document10 frame histories/tips/apply receipts and exact title/content/scope | S1 large manuscript, content conflict; S2 delete-vs-edit, resolution then tombstone |
| Progress | Progress11 complete chains/frames/tips/receipts and projection | Multiple S1 entries, two concurrent branches, explicit rebase |
| Project Game | Game12 histories/tips/receipts/projections | Genesis and ordinary credited Progress actions |
| Account Game | Game13 account history, action/reward proof, projection | Correlated immutable reward ledger, exact retry/reopen/self-echo |
| Catalog Folder/Folder Order | Catalog4/5 canonical history/tips/receipts | F1/order, concurrent folder rename, explicit resolution |
| Folder Membership | Catalog6 relation/tips/receipts | P→F1 then explicit null/removal |
| Project Order | Catalog7 canonical connected-project list | Includes P, excludes L |
| Local-only/Class C | No cloud binding/catalog membership/path/hash transport | L, local Word binding/proposal, raw synch/last_synch remain device-local |

Convergence compares canonical immutable histories, current tip identities,
authenticated ledger evidence and supported normalized projections, not local
SQLite revision, selection, path, timestamp winner or cache identity. Note
projection timestamp spellings are normalized and its local revision removed;
portable event bytes/lineages are still compared exactly. Local bindings/domain
consumer execution state legitimately differ and never become cloud truth.
Historical inbox disposition is compared as authenticated/proven, not as an
identical per-device choice to project versus preserve a branch. Each peer must
separately prove the entire prefix with the production native ACK validator;
immutable event/frame/receipt bytes and final tip sets are compared exactly.

## Integrated checkpoints

All checkpoints below passed the final real-PostgreSQL positive acceptance.

1. Initial A/B/C apply includes legacy Note, Metadata, structural/order, all Note
   routes, maps, both Documents, Progress, Project/Account Game and Catalog.
2. Eligible large ordinary Documents use production ID1 selection after explicit
   all-device server admission. Small structural/history frames remain ID0.
   No persisted frame is patched to force compression.
3. Upload response is discarded for sealed Documents; reopened pending rows retry
   the same event/nonce/ciphertext without invoking another seal/compressor.
4. Missing cover uses a blob already uploaded immutably, temporarily unavailable
   at the API. B retains the authenticated reference/event and durable typed
   blocker; native ACK remains before the hole. B writes an unrelated Note from
   its still-proven Metadata head; it applies beyond the hole without ACK leap.
   Restoring that same blob permits exact-event retry/materialization/apply.
5. Lost ACK response is followed by a new native proof read from the reopened
   database and idempotent server ACK before local cursor commit.
6. C remains offline from a proven durable cursor while A/B create simultaneous
   Metadata, Document, folder, Progress and Document delete/edit conflicts.
   Full version/tip sets persist and unrelated authorities remain coherent.
   Complete conflict preservation can be ACK-safe without complete convergence.
   Child conflicts are applied while Metadata is proven, before introducing its
   conflict. Metadata then blocks their writers/views without erasing either
   child branch. Resolving Metadata restores the existing child conflict views.
7. Existing explicit full-tip Metadata/Document/Catalog decisions and Progress
   rebase resolve them. Resolving Metadata cannot erase Document branches.
   Fresh ordinary edits from A and B descend from accepted Document tips.
8. A Note and Document tombstone, account membership removal, cover null and
   ordinary structural mutation retain unrelated authorities and old history.
   C catches up through all retained branches/resolutions from its old cursor.
9. Final matrix verifies all three peers, safe contiguous ACK, no duplicate apply
   or reward, retained old nonce/ciphertext/blobs and no unresolved supported
   conflict. Repeated empty cycles cannot change the proven state.

## Privacy and separate Class F negative

A unique synthetic Class C sentinel is present in local document/project binding
and legacy synch/last_synch source data, not manuscript/user-authored text.
Canonical frames/payloads before encryption and portable peer authority/ledger
snapshots must exclude it. HTTP request hooks check captured body bytes without
logging paths/content. PostgreSQL object/event/device/project/blob descriptors
are inspected for sentinel/plaintext exposure; peers must not acquire A's local
bindings or L. No binding endpoint/table/portable extension is introduced.

An account Folder object replayed into Project Metadata context must fail under
the frozen project1/AAD1 vs account2/AAD2 separation. It cannot create apply/ACK
proof. No crypto/version change or server plaintext decoding is involved.

A separate connected-project case preserves a nonempty unsupported Document
extension on B, then receives a valid authenticated Document event. The native
owner remains blocked, bytes remain locally intact, inbox remains orphaned, no
Document apply receipt exists and shared ACK cannot pass that event. Reopened
retry cannot turn the lossy/incomplete copy into full-sync evidence. No codec
for deferred F fields/orphans is invented.

## CI coverage and validation

The existing mandatory foundation/content-action and regression selections stay
unchanged. New `complete-project` mandatory matrix shard uses an independent
PostgreSQL service with the same40-minute timeout and fail-fast=false. Native
bridge is precompiled before bounded per-command IPC calls so cold Cargo setup
does not consume an individual bridge's180-second runtime allowance.

SQLite explicitly triggers on this test and retains all Windows fail-fast steps;
additional independent native cover/compression checks prove the substrate used
by the mixed fixture. PostgreSQL orchestration is not duplicated in SQLite.
Android packaging remains independent/unchanged, not an on-device runtime gate.

Validation: frontend13 files/101 PASS; native cover5/compression5/
compressed Document restart-ACK1 PASS; native full393 PASS (existing IPC hook
actually executes through the PG bridge); Python SQLite491 PASS. TypeScript
check/production build/cargo check, YAML/unchanged-union/fail-fast/path-filter
checks and diff check PASS. Final positive integrated PG1 PASS in773.23s;
final separate F-negative PG1 PASS in54.96s, zero mandatory skips. The complete
new shard union is these two cases, executed as focused selections after fixture
repairs; neither test depends on the other's database. Every case resets its own
disposable PostgreSQL schema. No already-green broad native/SQLite/TS union was
repeated after these Python-only repairs.

Initial and final exact A/B/C authority equality, cover hole/recovery, five
conflict families, all explicit resolutions, causal ordinary continuation,
tombstones/removals and C's long-gap catch-up PASS. Final account sequence is53;
all three native/shared and server ACKs are53. Supported unresolved conflicts0,
unproven positive-case inbox rows0. Original encrypted event nonce/ciphertext
pairs and the old immutable cover blob are retained. Empty repeated cycles leave
the complete snapshot unchanged. Local-only L/bindings/sentinels never appear in
portable frames, HTTP bodies, server rows or peer local bindings. Account ciphertext
replay into Project crypto context fails closed.

Development exposed a fixture ordering error: pending Metadata authority blocks
child apply. The fixture now preserves child conflicts before adding Metadata
conflict and asserts the exact dependency blocker rather than bypassing it.
Normal Metadata editor calls also use the full existing editor payload, retaining
derived Progress support fields. Document ancestry assertions use frozen codec10
`parents`; historical apply-versus-conflict disposition is local support state,
while native proof and exact canonical bytes/tips remain mandatory. No production
bug/repair was established: production files, schemas, protocols, crypto and
compression selection/limits remain unchanged.

Real PostgreSQL executed under explicit user authorization;
default sandbox TCP denial is handled by the allowed local execution mechanism.
SQLite38/Alembic `c18_compression_readers` unchanged. No new migration, release,
telemetry or C21 implementation. C18.8.01 LOCAL COMPLETE / REMOTE CI PENDING.

### Reproducible validation commands

Python commands use `PYTHONDONTWRITEBYTECODE=1`; real-PG commands require a
dedicated `NFPROGRESS_TEST_DATABASE_URL` and test data root. Local execution
redirects the legacy app-data lookup to that isolated root before pytest imports
the backend. No production application database is opened. Cargo commands use
`CARGO_INCREMENTAL=0` for the storage-safe validation policy.

| Selection/command | Result |
|---|---|
| `pytest --collect-only -q tests/test_cloud_c18_complete_project_acceptance.py` | 2 cases |
| Positive focused selection below | 1 PASS / 773.23s |
| F-negative focused selection below | 1 PASS / 54.96s |
| Frontend command below | 13 files / 101 PASS |
| `cargo test --manifest-path frontend/src-tauri/Cargo.toml --lib cover_` | 5 PASS |
| `cargo test --manifest-path frontend/src-tauri/Cargo.toml --lib frame_compression` | 5 PASS |
| `cargo test --manifest-path frontend/src-tauri/Cargo.toml --lib compressed_apply_bad_stream_retry_restart_and_canonical_identity` | 1 PASS |
| `cargo test --manifest-path frontend/src-tauri/Cargo.toml --lib` | 393 PASS; existing bridge hook explicitly runs in PG acceptance |
| Python SQLite workflow selection below | 491 PASS |
| `npm --prefix frontend run build` (includes typecheck) | PASS |
| `cargo check --manifest-path frontend/src-tauri/Cargo.toml` | PASS |
| YAML/retained-step/matrix/path-filter audit; `git diff --check` | PASS |

```sh
python -m pytest -q -rs -x tests/test_cloud_c18_complete_project_acceptance.py::test_complete_project_three_devices_all_authorities_and_causal_convergence
python -m pytest -q -rs -x tests/test_cloud_c18_complete_project_acceptance.py::test_complete_project_unsupported_document_extension_retained_blocks_ack
```

```sh
cd frontend
npm test -- --run --maxWorkers=1 \
  src/cloud/frameCompression.spec.ts src/cloud/compressionWriter.spec.ts \
  src/cloud/contentActionIntegration.spec.ts src/cloud/projectMetadataCodec.spec.ts \
  src/cloud/stageCodec.spec.ts src/cloud/accountCatalogCodec.spec.ts \
  src/cloud/contentNoteCodec.spec.ts src/cloud/mapCodec.spec.ts \
  src/cloud/documentCodec.spec.ts src/cloud/progressCodec.spec.ts \
  src/cloud/gameCodec.spec.ts src/cloud/projectCoverCrypto.spec.ts \
  src/crypto/crypto.vectors.spec.ts
```

```sh
python -m pytest -q -rs \
  tests/test_c9_sqlite_sync.py tests/test_c18_metadata_sqlite.py \
  tests/test_c18_cover_sqlite.py tests/test_c18_external_local_boundary.py \
  tests/test_c18_stage_sqlite.py tests/test_c18_account_sqlite.py \
  tests/test_c18_catalog_sqlite.py tests/test_c18_content_note_sqlite.py \
  tests/test_c18_map_sqlite.py tests/test_c18_document_sqlite.py \
  tests/test_c18_progress_sqlite.py tests/test_c18_game_sqlite.py \
  tests/test_c18_content_action_integration.py \
  tests/test_c15_7b_cross_runtime_udf_proof.py tests/test_application_metadata.py \
  tests/test_f8_recovery.py tests/test_api.py tests/test_c18_compression_distribution.py
```

Expected workflows: Cloud backend tests; SQLite sync substrate tests.
Storage audit after all test/build processes exited: maintenance dry-run found
only the allowlisted generated `frontend/src-tauri/target` (apparent2,863,607,426B,
allocated2,909,310,976B). `clean_generated.py --apply` removed that output only;
final dry-run potential0B. Main dependencies, other worktrees, Git history,
user data and protected pyc are retained. Disposable task PostgreSQL DB removed
after validation; the shared local server and unrelated databases are retained.
Remaining risks: hosted Linux/PostgreSQL and Windows/native execution is still
pending independent remote verification. Observed local new-shard test union is
13m48s; CI cold setup/bridge compilation adds runtime and remains subject to its
unchanged40-minute budget. Android device runtime is not claimed by this slice.
Remote acceptance is not claimed, and Actions must not be polled after push.
Only independent full-green owner/GPT verification may close C18.8/C18 and award
84.0%; C21 Web begins only under a separate prompt, local-browser-first.
