# NFProgress — F6 Documents / Word / Scrivener / filesystem runtime

F6 baseline: `89898945ff0ed71b27148e36ab00f9b90e1cd3ed`.

F6 is the development desktop implementation milestone. It moves the normal
Documents, Word, Scrivener and filesystem synchronization feature path from
the Python service to typed Vue/Tauri commands and Rust. F7 subsequently
removed the global sidecar, Nuitka packaging and startup orchestration; this
document records the F6 feature boundary and verification.

## Audited legacy behavior

| Operation | Legacy caller/service | Legacy storage/boundary | F6 desktop target |
| --- | --- | --- | --- |
| list/open/create/save/rename/delete | Vue `documentsApi` → `ProjectDocumentService` | `documents.json` | `DocumentRepository` → Rust → SQLite |
| editor autosave | `useDocumentSync`, 700 ms debounce and queue | JSON record | same queue, SQLite revision |
| project/stage text | document service scope key | `project_id:project` or `project_id:stage_id` | stable SQLite foreign keys |
| Word import/export/binding | Vue + Python document/integration services | DOCX path and hashes | Rust `WordCodec` and validated selected path |
| Word sync | Python `DocumentIntegrationService` | `synch`, `last_synch`, file mtime/size | `document_bindings`, SHA-256 and revision |
| Scrivener inspect/count | `scrivener_parser.py` | `.scrivx` + `Files/Docs`/`Files/Data` RTF | bounded Rust XML/package/RTF boundary |
| external change detection | editor five-second poll and Python 60-second task | source file | typed Rust command, native timer, hash coalescing |
| progress from source | `record_synchronized_progress` | project/stage progress | trusted Rust event/outbox path |

The legacy `documents.json` record fields are `project_id`, `stage_id`,
`content`, `exists`, `updated_at`, `docx_path`, `sync_state`,
`last_synced_hash`, `last_synced_at`, `local_dirty`, `word_dirty`,
`symbols` and `has_content`. The editor content is not flattened: the native
record stores the Tiptap/ProseMirror JSON value with format `tiptap-json/v1`.

## SQLite schema v6

`documents` stores `id`, unique stable `scope_key`, project/stage IDs, title,
structured content, content format, timestamps, monotonic revision and
`extensions_json`. `document_bindings` stores the external type/path/source
ID, last observed and last synchronized SHA-256 hashes, synchronized internal
revision, timestamp, sync state, expected self-write hash and JSON metadata.
`document_metadata` stores migration markers. `document_migration_orphans`
retains records whose project/stage relation cannot be proven.

The migration reads `documents.json` only before the
`documents_json_migration` marker exists, validates every relation, inserts
one transaction, preserves existing IDs, derives missing IDs as
`document-<sha256(project_id:stage-or-project)[:40]>`, and records the source
checksum. A second startup neither duplicates records nor imports stale JSON.
The old file is intentionally not deleted and remains a recovery artifact.

Project/stage renames and reorder operations do not change document relations.
When a project receives its first stage, an existing non-empty project document
is moved to that stable stage scope, matching the legacy behavior. Deleting a
project/stage deletes application-owned document metadata and bindings but
never deletes the linked external Word/Scrivener file.

## Native command surface

The desktop commands are:

```text
list_documents
get_document
save_document
record_document_progress
rename_document
delete_document
bind_document_file
read_document_external
accept_document_external
count_word_document
parse_word_document
import_word_document
export_word_document
write_document_word
write_document_word_content
inspect_scrivener
configure_document_sync
get_document_sync
get_project_document_syncs
remove_document_sync
run_document_sync
run_project_document_syncs
run_all_document_sync
```

TS `documentsApi` and `integrationsApi` select this boundary only when the
platform is Tauri. The web adapter remains HTTP/FastAPI-compatible. No
arbitrary read/write path or JSON file-operation command is exposed.

## Editor and synchronization safety

Autosave remains debounced and serialized. A late initial load is ignored once
the editor has a newer local revision, and save responses update metadata only
through the queued operation; they do not replace newer editor content. Native
external import parses DOCX directly to Tiptap JSON. Internal and external
state uses the tuple `(document revision, external SHA-256, last synchronized
revision/hash)`. States include `unlinked`, `synced`, `local_changed`,
`external_changed`, `conflict`, `missing_external` and typed recoverable
errors. Both sides changed since the last successful synchronization always
returns `conflict`; no side is silently selected.

Word writes use an fsynced temporary file followed by replacement. The native
polling timer runs every 60 seconds and the editor retains its explicit change
check. A source hash is compared before progress mutation, so repeated scans
do not duplicate progress or Game events. The expected final hash records an
NFProgress write and suppresses treating that write as an independent edit.

Document-derived progress is written through a private trusted Rust path that
creates the normal durable `ProgressAdded` event. The frontend cannot obtain
the trusted behavior by passing a `source` string. The event ID contains the
document scope and source hash/revision, making a repeated source state
idempotent.

## Word boundary

Only `.docx` is supported. Rust reads the expected DOCX ZIP/XML parts without
invoking Microsoft Word. It limits input to 100 MiB, archive entries to
10,000, declared expansion to 250 MiB and selected XML to 16 MiB. Absolute,
drive-like, backslash or parent-traversal ZIP names are rejected. DTD/entity
constructs are rejected. Relationships are not fetched, remote resources are
not opened, and `.docm`/macro content is rejected by extension; no executable
content is run.

Round-trip fidelity covers paragraphs, headings, bold, italic, underline,
strike, tabs and hard breaks. Unsupported Word styling or parts degrade to
text rather than executing or fetching content. Raw ZIP byte identity is not
promised; semantic text/format parity is the contract.

## Scrivener boundary

The importer supports the audited `project.scrivx`, root `.scrivx` and legacy
`binder.scrivproj` XML forms, binder IDs/titles/children, and RTF content under
`Files/Docs` or `Files/Data` for selected item counting. It does not rewrite
the source project. Snapshots, research, comments, custom metadata, corkboard,
compile settings and attachments are unsupported. XML is bounded and rejects
DTD/entity input; recursive package scanning bounds directories/files and
rejects symlinks so a package cannot escape its canonical root.

## Backups, migration and release boundary

Transitional Python backups now include SQLite, `documents.json` when present,
and `external_file_manifest.json` containing binding IDs, paths, source IDs,
hashes, revisions and sync timestamps. External files are references, not
implicit backup payloads. `MigrationBundle` v1 has optional `documents`,
`document_bindings` and `external_file_manifest` sections, preserving backward
compatibility for Web/legacy tooling. The future Legacy Migration Service may
convert these sections in isolation without requiring users to upload external
files unless they explicitly choose an asset backup mode.

Python document/integration code remains as the Web implementation, migration
oracle and parity fixture source. A production Bridge Release remains allowed
to normalize old IDs/bindings before F8, but no bridge format is introduced by
F6. Full restore, package inspection, bookmarks/security-scoped persistence,
Windows signed replacement qualification and release support matrices remain
F8 concerns.

## Verification

Focused Python document/integration tests: 50 passed; backup/schema checks: 33
passed. Rust formatting, x86_64 macOS target library check and Rust unit tests
pass, including stable ID, DOCX round-trip, traversal rejection and RTF
counting. Frontend typecheck and the full frontend test run pass (65 files,
261 tests). The full Python baseline remains 542 passed, 3 failed, 15 skipped
and 2 subtests passed; the three failures are unchanged legacy accessibility,
OpenAPI developer-response and week-symbol date-boundary tests.

The available ARM target was blocked at the F6 baseline by the missing bundled
`nfprogress-backend-aarch64-apple-darwin`. No fake binary was added; F7 removes
the packaging reference, so this file is no longer a build prerequisite.
