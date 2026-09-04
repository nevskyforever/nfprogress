# NFProgress — F1 SQLite authority audit

Audit and implementation baseline: `84298c5154a30f86b61ae4f614a1d3fc445b091d`.
F1 implementation commit is recorded in the final migration status after the
commit is created.

## Scope and ownership

F1 prepares a complete, authoritative-capable Projects aggregate without
switching runtime ownership:

```text
projects/stages/progress = PKL authoritative
settings                 = SQLite authoritative
notes                    = SQLite authoritative
game                     = PKL authoritative
```

The aggregate boundary is `projects`, `stages`, `progress_entries`,
`project_order`, `project_folders`, project-local bindings and preserved
extension payloads. Notes, Game, Settings and Documents remain separate
domains. Project-side document/integration references are retained as
extension or binding payload; external files are not copied into SQLite.

## Legacy field inventory

| Field group | Legacy location | v3 status | v4 representation | Classification |
| --- | --- | --- | --- | --- |
| Project identity/name/goal/unit/status/dates | `Project` attributes | normalized + projection payload | unchanged normalized columns + payload | runtime-important |
| Total/progress/deadline/plans | `Project` attributes | payload projection | payload, with query columns where v3 already had them | runtime-important |
| Streak/freeze project state | `Project` attributes | payload projection | preserved in payload; Game ownership remains separate | compatibility data, not F1 rules |
| Stage identity/parent/order/options | `Project.stages`, `Stage` | normalized + payload; order was rowid | parent FK + payload; current row order retained | runtime-important |
| Progress ID/timestamp/totals/delta/contribution | `Project/Stage.notes` | normalized + payload; rowid order | same plus `progress_order` stable positions | runtime-important |
| `synch`, `last_synch` | Project/Stage attributes | omitted from v3 serializer | `project_bindings` typed columns + full binding payload | lossless blocker fixed |
| Mind Elixir map | `mindmap_data` | usually nested in payload | nested payload retained byte-for-byte for valid JSON shapes | opaque F1 payload |
| Cover/folder reference | project attributes/root `project_folders` | cover/folder ID only | cover in payload; typed `project_folders` table | Projects domain |
| Folder catalogue | `data.pkl['project_folders']` | absent | `project_folders(id,name,position,payload_json)` | Projects domain |
| Unknown Project/Stage attributes | object `__dict__` | not guaranteed | `project_extensions(entity_type,entity_id,payload_json)` | forward compatibility |
| Unknown root project fields | data envelope | absent | `project_metadata.root_extensions` | forward compatibility |
| `last` project selection | data envelope | absent | `project_metadata.project_last` | UI compatibility |
| Notifications/global streak | data envelope | absent | not imported by F1 Projects storage | Game-owned, F3 |
| `documents.json` records/content | separate JSON file | absent | not copied into Projects tables | Documents, F5 |
| external Word/Scrivener files | filesystem | absent | binding path/hash/source metadata only | external-file manifest, F5 |

The normalized v3 payload does not make a pickle lossless: it cannot recover
omitted bindings, root fields, unknown attributes, or external files. F1
therefore imports the legacy objects into a canonical DTO before writing the
v4 representation.

## v4 schema

The migration source of truth is the existing SQL migration directory. Python
and Rust both execute the same `001`–`004` files; Rust embeds those files at
compile time and Python remains compatible during the transitional runtime.
v4 adds:

- `project_metadata` for the project envelope's selected root values and
  unknown root extension object;
- `project_folders` with stable IDs, deterministic positions and preserved
  folder metadata, plus `project_folder_members` for the typed project
  relation;
- `project_bindings` for project/stage source type, path, source ID, hash,
  last-sync timestamp and the complete binding payload;
- `project_extensions` for unknown root/project/stage/progress JSON-safe data;
- `progress_order` for stable, deterministic legacy history order;
- `migration_sources` for source format/version, checksums, sizes and capture
  metadata used by backup-aware verification;
- a transactional rebuild of `notes` with `ON DELETE RESTRICT` FKs.

The core v3 columns are intentionally retained, so old SQL clients and the
transitional mirror remain compatible. `stages -> projects`,
`progress_entries -> projects/stages`, `project_order -> projects`, and
bindings -> project/stage use foreign keys. Notes use RESTRICT because Notes
are SQLite-authoritative and deletion of a project storage row is not allowed
to silently delete Notes. Cross-domain Notes cleanup is an orchestration
operation for F2, not a repository side effect.

## Canonical migration DTO and importer

`nfprogress.core.migration.MigrationBundle` is DTO version 1. It contains
Projects, Stages, progress entries, normalized order, folders, project
metadata, root extensions and source-manifest slots. Settings, Notes and Game
are intentionally not mixed into this Projects DTO. Known fields are carried
in typed normalized/payload records; unknown object attributes are copied to
`extra_fields`; bindings retain both typed lookup fields and the original
JSON-safe payload.

The selected parser strategy is a migration-only Python helper. Reading
arbitrary pickle object graphs in Rust would require unsafe class behavior or
a restricted parser that is not justified for the F1 storage contract. The
helper loads legacy PKL using the existing compatibility classes, emits the
canonical DTO, and imports it through parameterized SQLite operations. It does
not write PKL, does not run in normal Tauri runtime, leaves source files
untouched, and rejects missing IDs, broken parent relations, incomplete order,
or Notes relations that would otherwise be lost.

`import_projects_bundle()` is one transaction and is idempotent by replacing
only the Projects representation with the same stable IDs. Re-running the
same DTO does not duplicate rows. Existing Notes are copied inside that same
transaction solely to satisfy RESTRICT parent FKs; Settings/Game are not
touched. A failed import rolls back the copy and all project writes.

## Rust foundation

`frontend/src-tauri/src/sqlite.rs` is now the canonical Rust DB opener and
versioned migration runner. It rejects future schema versions, rejects a
corrupt multi-row `schema_info`, enables foreign keys, and applies a 5-second
busy timeout. Tauri setup opens the fixed application DB path before starting
the existing sidecar. This is a migration/opening change only; it does not
switch ownership.

`project_repository.rs` provides typed read methods (`get_project`,
`list_projects`, `get_stage`, `list_stages`, `list_progress`,
`get_project_order`) and narrow write primitives for insert/update/delete of
projects, stages and progress, order updates, and aggregate insertion.
Project creation/order and aggregate writes use transactions. Project/stage
deletes are storage-only and do not award Game rewards, touch external files,
or delete Notes. RESTRICT FKs make an accidental cross-domain delete fail and
roll back.

## Deferred or PKL-only state

Notifications, global streaks, reward markers and Gamer state are Game-owned
and remain PKL until F3. Full `documents.json` migration and external-file
manifests are F5. Mindmap semantics, XMind, Word/Scrivener parsing and
lifecycle orchestration are not implemented in F1. The Projects owner remains
`pickle`; no frontend mutation path or normal Rust Tauri command writes the
new repository yet. F2 must add the controlled ownership guard/cutover and
cross-domain Notes lifecycle orchestration.
