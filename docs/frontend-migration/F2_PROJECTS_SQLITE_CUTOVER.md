# F2 — Projects/Stages/Progress SQLite cutover

Status: implemented from baseline `df1696ef37fbc5480581b23330016333c7fb8c61`.

## Authority and startup

Before F2, Projects, Stages and Progress were PKL-authoritative; Settings and
Notes were SQLite-authoritative; Game remained PKL-authoritative. F2 imports the
legacy state as `MigrationBundle` v1, verifies IDs, relations, order, payloads,
extensions, folders and bindings, and only then updates
`storage_ownership.projects` to `sqlite`. The import is transactional and the
owner switch is a separate guarded transaction after verification. Any failure
before that switch leaves the owner as `pickle`.

The Tauri-spawned sidecar marks itself with `NFPROGRESS_TAURI_RUNTIME=1`; its
startup performs the one-shot cutover. A second startup sees `owner=sqlite` and
does not read or import `data.pkl`. The old PKL is retained as a recovery
artifact and a backup is created before import. Direct FastAPI test/web
instances do not perform a desktop cutover and remain a separate backend
adapter.

Healthy SQLite-owned Projects reads never fall back to API/PKL. Rust commands
reject writes unless `owner=sqlite`; Python `PickleRepository` rejects project
reads/writes under the same owner. SQLite read errors are explicit errors, not
stale-mirror recovery.

## Mutation audit

| Operation | Vue caller | TS boundary | Tauri command | Python path | F2 owner/effects |
| --- | --- | --- | --- | --- | --- |
| Create project | project create form/store | `projectsApi.create` | `create_project` | web API only | SQLite aggregate + appended order |
| Metadata update | detail form/store | `ProjectMetadataRepository` | `update_project_metadata` | web API only | SQLite name/goal/unit/deadline/infinite |
| General project update | detail/settings forms | `projectsApi.update` | `update_project` | web API only | SQLite payload/config fields |
| Reorder projects | projects store | metadata repository | `reorder_projects` | web API only | validated complete order |
| Create/update/delete stage | stage controls | `projectsApi` adapter | `create_stage`, `update_stage`, `delete_stage` | web API only | SQLite stage/order/payload; Notes cleanup explicit |
| Stage reorder | stage controls | `projectsApi` adapter | `reorder_stages` | web API only | validated complete stage order |
| Add/delete progress | progress store/repository | `ProgressRepository` | `add_*_progress`, `delete_progress` | web API only | SQLite row, order, totals and outbox event |
| Complete/archive/reopen | lifecycle controls | `projectsApi` adapter | lifecycle commands | web API only | SQLite status/date; Game event boundary |
| Folder CRUD/membership | project/folder UI | `projectsApi` adapter | folder commands | web API only | SQLite folder tables and membership |
| Sync/integration writes | integration services | existing web adapter | trusted path not exposed to UI | transitional Python | blocked from PKL after owner switch |
| Documents/maps/files | document/integration UI | existing document adapters | not migrated in F2 | Python service | references/payload preserved; F5 owns cutover |

No Vue code issues SQL or a generic Tauri bridge. DTOs use strict camelCase
deserialization with unknown fields rejected.

## Semantics and transactions

Create appends a stable generated ID to `project_order`, preserves defaults,
dates, unit, goal/infinite mode, streak/settings metadata, stages, folder
membership and unknown payload fields. Metadata changes are narrow and retain
the complete JSON payload. Reordering requires every existing ID exactly once;
duplicates, unknown IDs and incomplete orders are rejected.

Stage create/update/delete preserves stage payload and order. Deletion removes
only related Notes explicitly in the same SQLite transaction; it does not touch
external files or silently perform Game/document cascades. Project deletion
similarly performs explicit Notes cleanup, removes aggregate relations and
records `ProjectDeleted` before deleting the aggregate. Existing map-linked
Notes are not selected by generic FK cascade; their relation is handled by the
explicit Notes policy.

Progress accepts only manual/app entities without a sync binding, normalizes
the requested unit using existing conversion rules, rejects unchanged totals,
stores timestamps/effective values and recalculates stage/project cached totals
from ordered rows. Author-list rounding remains ties-to-even at the existing
pure-calculation boundary; other displayed unit totals use the legacy ceiling
rule. Delete removes the exact progress row and derives the new total from the
remaining ordered entries.

## Game boundary

Projects mutations enqueue compact SQLite `domain_events` with stable keys:
`ProgressAdded`, `ProgressDeleted`, `ProjectCompleted`, `StageCompleted`,
`ProjectStatusChanged` and `ProjectDeleted`. Payloads contain event ID/type,
project/stage/progress IDs, delta where applicable and a small source/version
context; no whole project blob is sent. `INSERT OR IGNORE` makes retries
idempotent. Game remains PKL-authoritative. If Game processing fails after a
committed Projects transaction, the durable event remains pending and the
Projects mutation is not rolled back as a distributed transaction.

## Preservation and recovery

Migration and subsequent payload updates preserve unknown extensions, Mind
Elixir data, `synch`/`last_synch` bindings, provider hashes/paths and document
references. Folders and memberships are represented in SQLite and remain
independent of PKL. Current backup includes SQLite-owned Projects state; old
PKL-only backups require the legacy migration path. `mirror_state` is healthy
with `source_format=migration_bundle` after cutover and is not interpreted as
a requirement to rebuild a Projects PKL mirror.

## Long-Term Legacy Migration Service

This is roadmap architecture, not an F2 endpoint:

```text
upload → static validation → queued isolated worker
        → restricted legacy decoder → validated MigrationBundle
        → preview → download or authenticated normal importer
```

The decoder must never run `pickle.load(user_upload)` in the production web
process. Static inspection checks protocol, size, opcode count, globals,
classes and forbidden opcodes before decoding. The decoder allowlist contains
only known historical NFProgress classes and safe builtin values; unknown
modules/classes and arbitrary callable resolution are rejected. The worker has
no production credentials, DB/cloud metadata, home directory, host filesystem,
Docker socket, SSH keys or network egress; it uses a read-only root, isolated
temporary volume, CPU/RAM/process/file-size/time limits, and is destroyed after
the job. It emits only a versioned bundle, never a privileged DB write.

Bundle packaging may be `.nfprogress-migration`/ZIP, with path traversal,
absolute path, symlink, duplicate-name, Unicode-confusion and archive-bomb
checks. `MigrationBundle` remains the only decoder/importer boundary and must
include format/version, source app/schema versions, counts, checksums,
created-at, payload sections and optional assets manifest; unsupported future
versions are rejected explicitly.

Mode A converts and returns a short-lived download. Mode B validates, previews,
then calls the normal authenticated account importer; it does not silently
merge duplicate IDs/projects. Empty workspace or explicit conflict strategy is
required. The service uses HTTPS, short retention/automatic deletion, no raw
content logs or analytics, unguessable job IDs, owner/session-only results,
privacy notice, CSRF/session authorization, quotas, rate limits and per-user
concurrency limits. Local development/release helpers are separate from this
future service. Before PKL support ends, desktop must export the new bundle or
backup format locally.
