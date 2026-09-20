# C8 — Cloud Project State

C8 creates a metadata-only registry for future WORTA cloud projects. A row in PostgreSQL `cloud_projects` means only that a stable project ID belongs to an authenticated user and consumes one cloud-project slot. It is not a copy of a project and is not evidence that project data has synchronised.

## Registry and ownership

`cloud_projects` has a composite primary key of `(user_id, project_id)`, a creation timestamp, and a cascading foreign key to `users`. Project IDs use `VARCHAR(512)`: current Desktop creation and legacy migration produce 32-character hexadecimal strings, but SQLite, Rust/Tauri and compatibility APIs expose the established contract as a string rather than a UUID. The bounded string therefore preserves compatible real IDs without forcing a UUID migration.

The authenticated `current_user` is the only owner authority. The client never supplies an owner ID, rows of one user are invisible to another, and deleting a user removes only that user's registry rows. No project name, description, text, notes, stages, sources, game data, cover, attachment, JSON payload, or encrypted object is in this table.

## API and quota

Authenticated endpoints are:

- `GET /api/v1/cloud/projects`
- `POST /api/v1/cloud/projects/{project_id}`
- `DELETE /api/v1/cloud/projects/{project_id}`

GET and successful enable return IDs, `cloud_project_count`, and the effective `max_cloud_projects`; they never return project content. Enable accepts no request body. A body is rejected so C8 cannot become a temporary plaintext-upload path. Disable is metadata-only and returns `204`.

The C5 formula remains `user_override ?? global_default`; the global default is 20, `0` is a real zero limit, and `NULL` inherits. Only current-user `cloud_projects` rows count. Local Desktop and future Android projects remain unlimited; ordinary project creation and legacy Web compatibility storage never consult C8.

Enable and disable are idempotent. An already present project succeeds even when an administrator later lowers the limit below usage. A new row at or above the effective limit returns `409` with stable code `cloud_project_limit_reached`. Disabling removes only the registry row and frees a slot; it does not delete, archive, or otherwise modify the local project. If limits configuration is unavailable, C5's `503 limits_unavailable` contract is retained.

Administrators may lower a limit below existing use. Existing registry rows remain intact; no automatic conversion or deletion occurs. Further new enables are blocked until use falls below the lowered limit.

For an enable allocation, C8 starts a transaction and takes PostgreSQL `SELECT ... FOR UPDATE` lock on that user row. It then checks an existing row, computes the effective limit, counts that user's registry rows, and inserts only if a slot remains. This serializes allocations for one user across workers without process-local locking or a table-wide lock. Different users remain independent.

## Client lifecycle and safety boundary

The typed client lifecycle is:

```text
LOCAL_ONLY -> ENABLING_SYNC -> SYNCED
                         \-> SYNC_ERROR -> ENABLING_SYNC
SYNCED -> DISABLING_SYNC -> LOCAL_ONLY
DISABLING_SYNC -> SYNC_ERROR
```

On an error, the local copy remains the safety/authority copy. These states are client-side future sync states, not a PostgreSQL enum. The C8 production capability `encryptedInitialUpload` is intentionally false. Thus the future project switch labelled «На всех устройствах» remains gated: C8 cannot expose a normal enable flow that presents a registry reservation as `SYNCED`.

The existing `work_method == "sync"` and `sync_available` are document/source synchronization concepts. C8 does not reuse or alter them.

## E2EE and later stages

C8 deliberately does not upload plaintext or ciphertext project content. It does not add objects, devices, revisions, outbox, tombstones, cursors, conflict handling, or `/sync/*` endpoints. It also grants the C7 Admin Panel no project-content endpoint.

The sequence remains C9 Sync Protocol, C10 Crypto Threat Model, C11 Crypto Module, C12 Crypto Tests, C13 Encrypted Cloud Schema, then later encrypted initial upload and UI enablement (C15+). C21's normal-Web persistent cookie authentication is also unchanged: C8 neither adds cookies nor changes C7 Admin's memory-only access and refresh tokens.
