# C18.7.01 compression gate (9 October 2026)

Status: **LOCAL COMPLETE / REMOTE CI PENDING** after the validation recorded
below. Production writers remain **compression0**. C18.7/C18 remain IN PROGRESS;
o roadmap points awarded, official progress **77.0%**.

## Accepted prerequisites

Owner/GPT supplied independent acceptance of C18.6.02 implementation
`b361d72f7505d8e7de1139c3f2f697081d728b82`: SQLite **37438328166 SUCCESS**
(Python/Rust); Cloud **37438328232 SUCCESS** (Frontend, foundation,
content-action, regressions). C18.6.02 REMOTELY ACCEPTED; **C18.6 CLOSED**.
The existing cover/local integration boundary is unchanged.

## Current frame inventory

All rows use `WORTA-C1`, frame version1, a 20-byte header, big-endian u32
uncompressed and payload sizes. All encoders below continue hardcoding ID0 and
identical equal size fields. Each listed reader retains its old validation for
ID0; a matching ID1 codec/version first obtains a bounded ID0 *view*, then uses
that identical canonical decoder. The view is never a replacement history/event.

| IDs | Entity | Codec versions | Maximum canonical bytes | TS frame/unframe | Rust frame/unframe | Capability |
|---|---|---|---:|---|---|---|
|1|Project Metadata|1,2|1,048,576|projectMetadataCodec.ts: frameProjectMetadata/unframeProjectMetadata|project_metadata_sync.rs: independent unframe_metadata_event; writer uses canonical payload|compression_zero; metadata-cover2 still only ID0|
|2,3|Stage / Stage order|1,2|1,048,576|stageCodec.ts: frameStructuralEvent/unframeStructuralEvent|stage_sync.rs: frame/unframe|existing structural/mode3 ID0 gate|
|4–7|Folder/order/membership/project order|1|4,194,304|accountCatalogCodec.ts: frameCatalogEvent/unframeCatalogEvent|account_catalog.rs: frame/unframe|existing catalog/mode3 ID0 gate|
|8|Framed Note|1 (inner ordinary1 / resolution2)|8,388,588|contentNoteCodec.ts: frameContentNote/unframeContentNote|content_note_writer.rs encoder; content_note_sync.rs decode|NOTE_READER_SUPPORT compression_zero|
|9|Map|1|8,388,588|mapCodec.ts: frameMapEvent/unframeMapEvent|map_codec.rs: encode/decode|MAP_READER_SUPPORT compression_zero|
|10|Document|1|8,388,588|documentCodec.ts: frameDocumentEvent/unframeDocumentEvent|document_codec.rs: encode/decode|DOCUMENT_READER_SUPPORT compression_zero|
|11|Progress|1|8,388,588|progressCodec.ts: frameProgressEvent/unframeProgressEvent|progress_codec.rs: encode/decode|PROGRESS_READER_SUPPORT compression_zero|
|12,13|Project / Account Game|1|1,048,556|gameCodec.ts: frameGameEvent/unframeGameEvent|game_codec.rs: frame/unframe|game-reader-capabilities compression_zero|

These are aggregate byte ceilings, **not permission to enlarge fields**.
Metadata/Stage strings remain bounded to512 UTF-8 bytes; Document text nodes1MiB,
50,000 nodes/depth60/preflight160; Map owning validation/depth512 unchanged.
Catalog entity/parent limits unchanged. Historical unframed Note1/resolution2
never enter this transform. Old fixtures were not regenerated.

Authentication precedes parsing/decompression: project readers use C11 AEAD
context, account readers use account crypto2/AAD2. Native protected entry points
continue requiring the authenticated renderer lease and exact inbox/object/scope
proof, then repeat frame/codec/canonical validation before transactional apply.
A decoded view does not grant an apply receipt or ACK. Compression adds no crypto,
codec ID/version, transport, schema or cursor. Reader duplication remains; only
the bounded transform is shared, without a broad codec refactor.

## Candidate and license gate

The repository is GPLv3. Review used **actual npm tarballs, package metadata,
upstream pinned source/lock files, and locally cached crate LICENSE/Cargo.toml**,
not package-description license snippets. Compatibility conclusions below are
technical distribution review, based on retaining the permissive notices and
existing GPLv3 corresponding-source/release obligations.

| Candidate | Exact frontend / Rust | License / dependency evidence | Decision |
|---|---|---|---|
|zlib/DEFLATE RFC1950+1951|pako2.1.0 / flate2 1.1.9|pako MIT AND Zlib, **zero runtime transitive npm dependencies**; actual LICENSE and zlib source notice read. Rust details below.|**SELECTED**, ID1. Bounded low-level APIs, checksum, small window, no WASM; already present family.|
|Brotli RFC7932|brotli-wasm3.0.1 / native brotli8.0.4|JS tarball Apache2.0 LICENSE read; no npm runtime dependencies. Upstream v3.0.1 lock embeds brotli5.0.0/decompressor4.0.0, alloc-no-stdlib2.0.3, alloc-stdlib0.2.1 and wasm-bindgen0.2.80 tree. Native cached8.0.4 BSD3 AND MIT, decompressor5.0.3 BSD3/MIT, alloc0.2.4/2.0.4 BSD3 sources read.|**REJECTED**: additional1,057,020-byte WASM, async instantiation/bundler paths; output cap exists but JS wrapper exposes no maximum decoder window/allocator budget. Quality4 is worse on the seeded word-prose band; smaller streams on other records do not remove the weight/window-budget rejection. Full embedded WASM license closure not admitted; no rejected package installed in product.|
|Zstandard RFC8878|@bokuweb/zstd-wasm0.0.27; contemplated zstd0.13.3|npm metadata MIT, zero npm dependencies, wasm251,806bytes. Tarball **does not contain LICENSE**. Actual `simple/decompress.js` calls malloc(contentSize from untrusted frame), exposes no streaming/window cap; permits multiple/skippable frames. Exact embedded-C source/license build provenance not established.|**REJECTED before benchmark/admission** for unsafe allocation API and incomplete binary license evidence. Rust package not admitted; no guessed transitive legal clearance. A different audited implementation would require a new gate.|

Primary evidence:
[pako2.1.0 source](https://github.com/nodeca/pako/tree/2.1.0),
[pako license](https://github.com/nodeca/pako/blob/2.1.0/LICENSE),
[flate2 pinned crate](https://crates.io/crates/flate2/1.1.9),
[Brotli wrapper pinned lock](https://github.com/httptoolkit/brotli-wasm/blob/v3.0.1/Cargo.lock),
[Brotli wrapper API](https://github.com/httptoolkit/brotli-wasm/tree/v3.0.1),
[Zstandard wrapper](https://github.com/bokuweb/zstd-wasm),
[RFC1950](https://www.rfc-editor.org/rfc/rfc1950),
[RFC1951](https://www.rfc-editor.org/rfc/rfc1951).
RFC1950 describes an implementable format without known patent requirement;
no special patent promise is invented for any candidate.

Selected native dependency closure, already locked before this slice:

| Package/version | Actual source license choice |
|---|---|
|flate2 1.1.9|MIT (alternative Apache2.0)|
|miniz_oxide0.8.9|MIT (alternatives Zlib/Apache2.0)|
|adler2 2.0.1|MIT (alternatives0BSD/Apache2.0)|
|simd-adler32 0.3.10|MIT|
|crc32fast1.5.0|MIT (alternative Apache2.0)|
|cfg-if1.0.4|MIT (alternative Apache2.0)|
|zlib-rs0.6.7|Zlib|

`cargo tree -e features -i flate2` proves existing ZIP feature unification enables
zlib-rs as well as rust_backend; production native uses **zlib-rs0.6.7**. Cached
miniz_oxide0.8.9 was separately benchmarked and interoperates. No system zlib/C
compiler/WASM/library runtime is added. Cargo.lock adds only the direct edge,
**zero new crates**. The transitive JSZIP-local pako1.0.11 stays intact for DOCX;
adding pako2.1.0 does not silently upgrade the legacy JSZIP dependency.

MIT/Zlib notice conditions add no incompatible distribution restriction to
GPLv3. Required complete notices are included now in
`frontend/public/licenses/C18-compression.txt`: pako MIT + upstream zlib source
notice and the selected native closure. Vite copies this asset to Web output;
Tauri bundles that output; Capacitor copies the same output. Keep these notices
in binary/Web/Android distributions and source packages; do not remove upstream
notices or misrepresent modifications. No dependencies were modified. The
existing GPLv3 release gate still requires corresponding application/source and
pinned dependency availability when distributing; this slice does not publish
an application release. No selected dependency imposes additional source release
beyond GPLv3. Rejected package licenses are not copied into product assets.

## Corpus and measurements

`scripts/compression/corpus.mjs` generates **54 deterministic cases** without
private data. `compressionCorpus.spec.ts` passes every actual event through its
production encoder and compares canonical bytes. Metadata1/2/cover-removal/
resolution, Stage and4096-item order, catalog folder/2000-item order, HTML/plain
Note, owning/annotated/large2000-node Map, Tiptap/prose Document, Progress
(genesis/append/rebase/delete), Project/Account Game and full-tip resolution are
represented. RU/EN/Unicode, repeated JSON keys, seeded varied prose and random
ASCII are included. Actual authenticated event headers are larger than256B;
the16B and67KB random policy probes are explicitly **not admitted entity frames**.
No JPEG/DOCX/Scrivener bytes are compression targets.

Measurements are local evidence, not CI speed assertions. Node26.4.0 JS run,
release Rust macOS Apple Silicon, level6 zlib / quality4 Brotli, first-call cold
cost included, same exact canonical input. RSS is approximate **whole-process
RSS**, accumulated across candidates/corpus, not per-decoder peak allocation.
Native times use release binaries; no artificial millisecond pass threshold.

| Case | Input B | zlib JS/Rust B | JS comp/decomp ms | Rust comp/decomp ms | Brotli JS/Rust B | Brotli JS comp/decomp ms |
|---|---:|---:|---:|---:|---:|---:|
|projectMetadataV2.json:v1|669|360/365|4.61/2.97|0.10/0.01|350/350|5.66/2.63|
|metadata-larger|2,430|356/362|0.21/0.07|0.03/0.01|336/336|0.25/0.05|
|stage-order-large|272,754|22,271/22,393|13.53/8.71|1.26/0.20|8,867/8,867|14.63/3.12|
|catalog-order-large|136,243|10,974/11,115|3.34/1.01|0.69/0.15|4,886/4,886|6.01/0.22|
|note-plain|40,252|1,496/1,611|0.99/0.17|0.11/0.03|1,235/1,235|2.09/0.20|
|note-html|39,658|1,501/1,590|0.83/0.10|0.10/0.03|1,238/1,238|2.04/0.18|
|large-map|135,552|12,416/12,478|3.13/0.70|1.40/0.12|11,003/11,003|6.93/0.62|
|document-narrative-65536|73,233|2,026/2,083|1.03/0.29|0.21/0.04|1,695/1,695|3.52/0.17|
|document-narrative-1048576|1,158,368|15,626/16,156|20.61/3.68|2.03/0.39|7,779/7,810|33.63/1.46|
|document-prose-16384|20,247|2,316/2,333|0.40/0.11|0.26/0.02|2,914/2,914|0.99/0.06|
|document-prose-262144|267,654|22,021/21,822|14.05/1.43|5.14/0.22|33,253/33,253|12.12/0.99|
|document-prose-8200000|8,303,423|653,685/646,781|395.18/47.71|163.47/7.97|1,016,999/938,072|463.19/30.66|
|progressCodecV1.json:append-stage|897|389/388|0.15/0.13|0.05/0.02|378/378|0.25/0.05|
|gameCodecV1.json:account-resolution|501|217/217|0.14/0.06|0.03/0.01|212/212|0.18/0.04|
|tiny-policy-probe-not-entity|16|24/24|0.32/0.25|0.01/0.00|20/20|0.34/0.20|
|random-policy-probe-not-entity|67,030|54,585/54,763|9.94/0.99|2.20/0.29|54,912/54,912|3.63/1.04|

For every row, absolute saving is input minus output; percentage is100×saving/input, throughput is input/time. The reproducible benchmark emits these fields for all52 cases. Cold native crate build is excluded from payload timing. Native Brotli8.0.4 release timings for the8.3MB prose case: 85.77/20.43ms comp/decomp.
Aggregate pako: 10,555,974→815,237B, 92.28% saving; cumulative JS comp/decomp 479.17/72.81ms.
Aggregate brotli: 10,555,974→1,161,011B, 89.00% saving; cumulative JS comp/decomp 567.53/44.81ms.

Production frontend build vs isolated baseline archive: total JS 12,419,577→12,487,781B (**+68,204B**); independently gzipped sum 2,659,159→2,679,618B (**+20,459B**). These totals include unchanged vendor/mind-map assets and chunk movement; they are not initial-route download measurements. Notices add 12,064B separate static asset. Native: zero new crates/system libraries; a full release-app binary delta was not measured, so none is fabricated. Capacitor copies the same JS/notices delta, no WASM/plugin/native decoder added. Whole-process JS RSS range 99,074,048–219,889,664B; that is not claimed as isolated peak decoder memory.

## Frozen algorithm, decoder and dormant writer policy

**ID0 = none; ID1 = exactly one RFC1950 zlib stream carrying RFC1951 DEFLATE,
including Adler-32; no gzip/raw-DEFLATE fallback. IDs2+ remain unsupported.**

| Contract | Exact value/policy |
|---|---|
|Compressed input (ID1)|1,048,576B maximum, checked before decode; ID0 retains existing8MiB−20/global and entity limit|
|Declared output|minimum1B for ID1; maximum8,388,588B **and owning codec's lower ceiling** before allocation|
|Expansion|declared ≤512×actual compressed input; actual output cannot exceed declared; over-ratio writer candidate stays ID0|
|Decoder allocation|exact declared+1B overflow sentinel, never a growing collection; max8,388,589B|
|Window|RFC1950 CINFO≤7, max32,768B; no larger window/header accepted|
|Scratch|16,384B output progress slices into the same allocation; fixed library window/Huffman state, no general output allocator|
|Frame normalization|second exact20+declaredB view; aggregate output/view ≤16,777,197B, plus bounded library state/input; no third joined payload|
|Dictionaries|FDICT rejected; no supplied/shared/adaptive/history/server dictionary|
|Members|exactly1; empty output disallowed; complete StreamEnd plus checksum required|
|Concatenation/trailing|reject any remaining byte; do not auto-reset/join streams|
|Work|input≤1MiB/output≤8MiB, 16KiB positive-progress steps, immediate abort on decoder error/no progress; constant32KiB window. No wall-clock timing-dependent acceptance or infinite retry.|
|Writer threshold|original≥1,024B, saving≥128B **and** ≥10%; compressed≤1MiB and ratio≤512|
|Writer level|6, fresh independent compressor/window15 per immutable event|
|Entity allowlist|canonical event codecs1–13, subject to owning validation and the next all-device reader gate|
|Denylist|unframed legacy history; JPEG covers; DOCX/RTF/Scrivener/external source bytes; attachments; credentials; local bindings/support/cache; unknown codecs/extensions|
|Near limit / incompressible|no relaxed entity limit; output above compressed cap/insufficient saving/over-ratio returns ID0; a sealed event is never recompressed|

`frameCompression.ts` uses pinned pako low-level zlib APIs, with explicit
consumed input and output counters. It never calls `inflate()` convenience
wrapper. `frame_compression.rs` uses flate2 `Decompress`, caller-owned fixed
output slices and total_in/total_out, never an unbounded Read-to-end in cloud
apply. Header/method/window/dictionary checks happen before library creation.
Both require checksum, exact end/length and no remaining input. High-ratio
actual output with a forged small declaration hits the overflow sentinel and
fails before unbounded expansion. Encoder validation stays with each entity.
The benchmark's convenience decoder is **test/tooling only**, not production.

Typed codes in both safe diagnostics lists: `compression_unsupported`,
`compression_invalid_stream`, `compression_input_limit`,
`compression_output_limit`, `compression_resource_limit`,
`compression_length_mismatch`. Every runtime retains the exact nonce/ciphertext
and records its bounded blocker, never applies/ACKs failure. Historical
account/game CHECK allowlists remain unchanged: their compatible generic blocker
is stored with precise `{code}` evidence under a scoped
`frame_compression_blocker:[account,event]` key in existing Class-C
application_metadata, transactionally; project inbox permits the precise code
itself. This local support evidence is never portable/ACK authority. No schema39,
Alembic migration, new cursor, backend decompression or capability activation.

## Side-channel decision

Review applies individually to Metadata, Stage/order, catalog, Note, Map,
Document, Progress and Project/Account Game. Each record may contain private user
text/names/facts, so ciphertext lengths reveal compressibility. None of these
frozen schemas transports encryption keys, authentication tokens/passwords or
mixes independently authorized users. Server descriptors do not inject plaintext
into a newly encrypted event. A server cannot forge authenticated reflected
fields. Registered peers already possess the relevant account/project key;
their ability to read content is not created by compression. Local external
imports remain explicit comparison/proposals under accepted C18.6.02, with no
automatic repeated server-controlled reflection. There is no existing shared
untrusted-collaborator/public-import length-query service in this architecture.
Thus canonical events1–13 are admitted for the **future gated** policy under
this threat model, with independent per-event state only. Cross-event/user/server
and adaptive dictionaries are forbidden. If a future automatic public/reflected
input or independently privileged collaborator is introduced, its entity stays
ID0 until this analysis is repeated. User text can itself contain sensitive
words; this review does not claim compression hides all information about length.

## Capability and immutable retry boundary

Every existing `compression_zero:true` declaration still means **only ID0**.
Nothing in this slice advertises ID1 or allows a production writer to emit it.
C18.7.02 must introduce an explicit account-owned reader declaration (proposed
shape `frame_version:1, reader_version:1, compression_ids:[0,1]`), prove all
participating registered readers support every retained codec before publishing,
and preserve legacy `compression_zero` compatibility. No server schema field is
invented here. Compression policy is fixed before first seal; sealed frame,
nonce/ciphertext, ID and event/parent identity are immutable exact retry material.
No local codec/version/schema expansion, C11/AAD1 or account crypto2/AAD2 change.

## Fixed vectors, failure and restart proof

Shared `frameCompressionV1.json` contains original canonical recipe bytes/SHA256,
codec/version/ID1, declared/actual sizes, both pinned JS and production native
compressed bytes and complete TS **and native** frames. Both languages consume the **same file**.
Small Metadata, realistic Document, large Document,8.35MB near-limit valid
Document and random-small Metadata (policy ID0) are covered. TS and native encoders
need not produce identical compressed bytes; their exact recovered canonical
bytes/hash must match. Native fixture producer uses application feature-unified
flate2/zlib-rs; the separate miniz candidate also cross-decodes the same format.

Tests cover TS→TS, Rust→Rust, TS→Rust, Rust→TS; all13 owning readers; old ID0
re-encoding; truncation at every offset; corrupt Adler/body/header; forbidden
window/dictionary; declaration shorter/longer/over-limit; tiny claimed bomb;
actual expansion past a small declaration; input cap; concatenation/trailing;
unknownID2; valid compression containing invalid entity/deep JSON. No allocation
of a giant claimed output is used to prove the guard.

TS production AEAD seals a compressed substrate vector, persists frame/nonce/
ciphertext to an isolated file, reopens it and retries exact bytes despite dormant
policy, then authenticates and decodes the same frame. This is substrate proof,
not ID1 writer activation. Native file-backed schema38 test retains32 typed
blocked Project/Account Game events, reopens, visits later retained sequences,
keeps apply ledger empty and computes shared ACK candidate0 below sequence1.
Scope/ciphertext mismatch cannot insert trusted blocker evidence. A frontend
Document runtime test proves authenticated malformed ID1 is blocked, not applied,
and traverses after-sequence7 without immediate retries. Existing full shared
ACK/outbox/multi-device PostgreSQL suites remain required; no independent blob or
compression ACK is added.

Chromium runs the exact frontend pako module and both producer vectors, including
near-limit bytes, through Vite's browser path; no Buffer/zlib/fs/Tauri APIs occur
in production compression code. Capacitor uses this same module. Actual Android
APK/device execution is **not claimed**: no Android-device CI is configured here;
that platform build/device proof remains for the platform acceptance gate.

## Reproducible checks

```sh
node scripts/compression/corpus.mjs > /tmp/c18-compression-corpus.json
node scripts/compression/benchmark.mjs /tmp/c18-compression-corpus.json
cargo run --release --manifest-path frontend/src-tauri/Cargo.toml \
  --example c18_compression_benchmark -- /tmp/c18-compression-corpus.json /tmp/c18-compression-native.json
cd frontend
npm test -- --run src/cloud/frameCompression.spec.ts src/cloud/compressionCorpus.spec.ts \
  src/cloud/contentActionIntegration.spec.ts src/cloud/documentSyncRuntime.spec.ts
npm run build
```

Optional rejected Brotli benchmark uses a temporary extracted3.0.1 tarball via
`C18_BROTLI_PACKAGE`; native comparison used isolated flate2=1.1.9/brotli=8.0.4
release harness. Neither rejected package is a product dependency. CI tests make
no timing assertions.


Final local evidence (one broad pass, focused repairs/retests only):

- Frontend curated union **660 unique tests passed**: broad run657passed with3
  local Node26 timeouts; the affected42-test group passed on pinned CI
  Node20.19.0, without test/assertion/timeout changes. Added vector/corpus and
  authenticated Document blocker tests are selected in the existing Frontend
  job. Final owning-reader/codec/diagnostics focus and metadata runtime focus
  pass; complete two-producer vectors10 and corpus1 pass separately.
- Native SQLite library broad pass387passed,3 exact failures corrected (safe
  code list ordering, test-only float serialization, historical blocker CHECK
  mapping),1 existing ignored headless hook. Focused repaired cases and added
  account blocker prove **391 unique native tests passed** in the resulting
  union. The ignored hook is not a skipped acceptance scenario: it is executed
  by the mandatory real PostgreSQL headless harness. New compression/security
  tests have **zero ignores/skips**.
- SQLite workflow-equivalent Python union **486passed**, zero skips (424.61s).
- Real PostgreSQL mandatory foundation **34passed** (1898.48s), content-action
  **23passed** (2106.55s), cloud/legacy **197passed** (310.39s): **254 unique**,
  zero skips. Three separate local databases used, mirroring independent CI
  services; source/toolchain rebuild contention during local development is
  included in these wall times. These are test-command times, not promises
  about final GitHub job/setup duration. New mandatory native compression adds
  seconds to foundation, **no PostgreSQL test group is enlarged or removed**.
- Browser: both complete fixed producer streams for five cases through portable
  frontend pako in Chromium, including8.35MB near-limit output. Reproducible
  empty-page harness: `scripts/compression/browser-vectors.mjs` (start isolated
  Vite; harness does not mount the application or call its API).
- `npm run build` (including TypeScript typecheck), `cargo check`, YAML/shard/
  timeout checks and `git diff --check` pass. Existing build warnings remain.
  Fresh/every-prefix/populated/reopen schema38 tests are in the unchanged
  SQLite union; no migration file is changed.

Coverage manifest: old and new PostgreSQL file selections are identical;
Frontend old selected files are a subset of new ones (two added specs plus
stronger existing registry/blocker proofs); Rust full Windows library selection
is retained, with foundation `frame_compression` explicitly added. No exact
execution duplicate removed, no unique family removed, no xfail/skip/assertion
weakening. Cloud retains Frontend + foundation + content-action + regressions,
independent PostgreSQL services,40-minute PostgreSQL limits and matrix fail-fast
false. SQLite Windows30-minute native and Python15-minute jobs remain. Both
push/PR filters include new compression module/vectors/tooling, dependency lock
and notice assets. No workflow collapse/timeout increase or unrelated trigger
change.

Compatibility audit: all historical codec1–13/unframed Note goldens retained;
no entity/version/crypto/scope/ACK/local-only contract expansion. Protected pyc
size/mtime and original Git state unchanged. Generated Tauri schema build churn
is excluded from the change. Release gate, final terminology audit and C21
local-Web-first preserved. Remaining risks: synthetic/cold timing is machine
specific and is not a real manuscript performance guarantee; Android build/device
and complete app-native binary delta not measured; independent remote CI and the
all-device capability/writer activation gate still required. Do not close C18.7
or C18 and do not poll Actions after push.
