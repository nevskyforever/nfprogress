# F5 — Python-free Mind Elixir / XMind runtime

Status: development desktop runtime complete. F6 document/integration runtime
is complete for the development desktop path.

## Baseline

The actual baseline HEAD is `295809e8969171e200d5acdce8ce59580ed25892`
(`295809e`). The documented F4 profile is `539 passed, 3 failed, 15 skipped,
2 subtests passed`; the full baseline invocation did not complete in the
available run window. The post-F5 full run completed with `542 passed, 3
failed, 15 skipped, 2 subtests passed` in 30.61s. The three known failures are
legacy accessibility,
the developer OpenAPI response-model assertion and the week-symbol date
boundary fixture. They are not attributed to F5.

## Runtime audit

| Operation | Vue/Mind Elixir caller | TypeScript | Tauri/Rust | Before F5 | Storage/effects | F5 target |
| --- | --- | --- | --- | --- | --- | --- |
| Create/open map | `MindMapEditor`, `useProjectNotes` | `notesRepository` | no command / Python API | API → Python | Project/Stage `mindmap` | `load_map` → SQLite |
| Save map | editor save event | `SQLiteNotesRepository.saveMindMap` | `save_map` | API → Python normalize/save | map-owned payload + linked Notes | typed transaction |
| Edit/add/remove node | editor event bridge | map JSON passthrough | `save_map` | API → Python | node IDs/order/opaque data | same, Python-free |
| `freeNodes` / floating items | embedded Mind Elixir editor | `normalization.ts` | `mindmap.rs` | Python normalizer | free nodes, links, note markers | bounded opaque roundtrip |
| Map-linked Notes | Notes page/editor | repository + `MindMapEditor` | `reconcile_map_notes`, Note commands | Python reconciliation | separate `notes` rows | one SQLite transaction |
| Project/stage map | resource hub/editor | scope adapter | `compose_combined_map` / split | Python compose/split | project + stage payloads | stable ownership markers |
| Reset/delete map | no separate legacy delete API | save empty map | `save_map`; owner delete commands | Python save/cleanup | map payload and Notes | explicit save/owner cleanup |
| Import XMind | file input and sheet chooser | repository returns sheets | `import_xmind` | Python ZIP/XML service | no write until selected sheet is saved | bounded Rust parser |
| Export | no supported map export path found | — | — | — | — | deferred; not invented in F5 |
| Normalization/legacy formats | editor/repository boundary | `core/mindmap/normalization.ts` | `mindmap::normalize` | `engine.py` | opaque JSON envelope | parity-compatible pure layers |

The Web `ApiNotesRepository` and Python FastAPI routes remain intentionally
available for the Web product. They are not selected by the Tauri repository.
The global sidecar still starts for other subsystems; this milestone does not
remove it.

## Canonical map contract

The canonical persisted DTO is the existing Mind Elixir JSON envelope, typed at
the boundary as a JSON object with a required `nodeData` root. Every tree node
has a non-empty stable `id`, string `topic` and ordered `children` array.
Direction, layout, style, metadata, custom fields, `freeNodes`, floating items,
floating links and unknown envelope/node fields remain in the JSON payload.
The TS and Rust normalizers reject malformed roots, bound payload/node/depth/
topic sizes, and normalize only known editor-owned structures. Unknown fields
are copied through; they are not moved into a second relational model.

`freeNodes` preserve their IDs, ordered children, note marker, root position and
opaque fields. Floating items preserve opaque fields while validating kind,
coordinates and parent references. Normal map mutations do not regenerate
node IDs or reorder children. Existing styles/layout fields survive ordinary
roundtrip because the node object is cloned rather than rebuilt.

Project maps use the existing root node ID, with deterministic fallback
`project-map-{project_id}`. Stage maps use the existing root node ID, with
fallback `stage-map-{stage_id}`. Combined project views use transient
`nfprogress-stage-*` IDs and explicit source/stage markers; saving restores
the original stage IDs and remaps arrows/summaries to them. Imported XMind
IDs are not trusted: Rust generates IDs from the archive fingerprint, sheet
index and tree path, preserving repeat-import determinism while avoiding
collisions between different archives. Child order is source order.

## Storage and transactions

No new table or schema migration was required. `mindmap` remains an opaque
section of the authoritative SQLite `projects.payload_json` or
`stages.payload_json`; Rust updates only that section plus map timestamps.
Project progress, folders, bindings, extensions, document references and other
payload keys are retained. This is the minimum model because F2 already stores
the complete map payload without loss.

`save_map` validates the map and ownership, then opens one SQLite transaction.
It writes the project/stage map and reconciles linked Notes before commit. A
failure rolls back both. Loading an existing map also performs idempotent
reconciliation, so an old map can materialize its Notes without Python.
Malformed SQLite map JSON returns a recoverable error; it is never replaced by
an empty map. Repeated saves cannot create duplicate map Notes: reconciliation
indexes by `source_node_id` and uses `mindmap-{sha256(source_node_id)[:28]}`
for new row IDs.

## Notes contract

Notes are not embedded authoritative copies inside the map. A map note is a
free node marked `nfprogressNote=true` or the supported legacy floating note;
its text is the node `topic` or floating `text`. The Note row is separate and
has `source_type=mindmap`, `source_map_id` equal to the map root ID,
`source_node_id` equal to the stable node ID, plain content and the derived
system tag `карта`. Note title, checklist/archive/color and other Note-owned
fields remain separate.

Map node → Note is created or updated during load/save reconciliation. Note
content → map updates the same node in a transaction. Deleting a linked Note
removes the corresponding map note subtree (and arrows, summaries and
floating links touching that subtree), then deletes the row in that same
transaction. A normal node rename/move does not alter the linked Note.
Deleting a map node therefore deletes its linked Note on the next save; this
matches the existing Python semantics. There was no separate map-delete API in
the audited product. Resetting by saving an empty valid map removes its linked
map Notes through reconciliation. Project/stage deletion explicitly removes
owned Notes and the owning SQLite row; no FK cascade is relied on. No
project↔stage conversion path with map transfer was found in the supported
desktop code, so no new transformation semantics were introduced.

## XMind boundary and security

Rust reads only ZIP entries named `content.json` or `content.xml`, without
blind extraction. JSON supports the existing modern array-of-sheets shape
with `rootTopic` and `children.attached`. XML supports the existing old
namespace-tolerant `sheet`/`topic`/`children`/`topics type="attached"` shape.
The result is structural tree data only. Multiple sheets are returned in file
order and the Vue dialog requires explicit sheet selection; no sheet is
silently discarded. Unsupported styling, images, attachments, relationships,
external links and proprietary metadata are ignored/deferred and never opened,
downloaded or executed. Topics are imported as bounded plain text; they are
not injected as HTML.

The parser enforces: 50 MiB input, 2,048 archive entries, 100 MiB declared
decompressed total, 16 MiB selected content, 100 sheets, 50,000 nodes, depth
512 and 300,000 Unicode characters per topic. It rejects duplicate/absolute/
parent-traversal/drive-like paths, unsafe ZIP entries, malformed archives,
oversized content, malformed JSON/XML, empty topics and DTD/entity declarations.
XML is parsed with quick-xml with no external entity/network resolution. The
frontend file input supplies bytes directly; no arbitrary frontend path is
accepted. Existing Note HTML rendering keeps its sanitizer boundary, while
XMind topics enter the text-only Mind Elixir payload, so the importer does not
create an obvious HTML/XSS path.

## Python parity and migration

`engine.normalize_mindmap_data` and the Python XMind importer remain in place
as behavioral oracles for Web and migration. The new TS normalizer covers the
same required root/free-node/floating-field semantics and the Rust unit tests
cover opaque-field/ID preservation, note roundtrip, JSON/XML tree order,
multiple-sheet structure, malformed entity input, traversal and sheet limits.
The existing Python fixtures cover simple/nested trees, multiple sheets,
invalid JSON/XML and failed-import non-mutation. The two implementations need
not be byte-identical for generated XMind IDs, but their tree shape, topics and
ordering are equivalent; imported external IDs are intentionally remapped.

F6 keeps this boundary intact: Documents, Word, Scrivener and filesystem sync
now use their own typed Rust/Tauri boundary and do not route through the map
runtime or the Python sidecar. Map payloads remain nested in the owning
Project/Stage SQLite record; no duplicate document/map authority is introduced.

MigrationBundle v1 is unchanged: maps already travel losslessly in the
Projects DTO payload, so adding a duplicate map section would create another
truth model. The Legacy Migration Service continues to decode old PKL state in
isolation and can normalize/prepare the map section for trusted import. The
new desktop runtime never reads pickle or calls Python for maps.

## Verification and readiness

- Actual HEAD before changes: `295809e`.
- Focused Python map/XMind oracle tests remain available; no Python map code was
  deleted.
- `cargo fmt --check`, `cargo check --target x86_64-apple-darwin --lib` and
  `cargo test --target x86_64-apple-darwin --lib`: passed, 23 Rust unit tests.
- Frontend normalization/repository tests and TypeScript checks: passed.
- Full Python profile after F5: `542 passed, 3 failed, 15 skipped, 2 subtests
  passed`; the three failures are exactly the documented baseline failures.
- Full frontend test/build: `65` test files and `261` tests passed; production
  build passed with existing chunk-size/dynamic-import warnings.
- The default cargo check remains blocked by the pre-existing missing bundled
  `binaries/nfprogress-backend-aarch64-apple-darwin`; no fake binary was added.

Normal desktop map calls to localhost/FastAPI/Python are zero after F5. Python
remains only in the Web adapter, legacy migration service and oracle tests;
the sidecar remains for Documents and other integrations. Production Python
bridge updates remain allowed through F8. F7 still owns global sidecar and
packaging removal; F8 owns release qualification and recovery matrices.
