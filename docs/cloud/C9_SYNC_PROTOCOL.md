# C9 — Sync Protocol

C9 defines WORTA sync transport protocol v1 (`SYNC_PROTOCOL_VERSION = 1`). It is a metadata-only foundation, not project synchronisation and not an E2EE implementation.

## Boundary

An authenticated account registers a UUID device identity with `PUT /api/v1/sync/devices/{device_id}`. The ID is stable per account/device, is not an authentication credential or encryption key, and the same UUID under different accounts remains isolated. All sync endpoints require ordinary C2 bearer authentication.

The envelope is `event_id`, `device_id`, `project_id`, `entity_id`, `entity_type`, `operation`, `revision`, `updated_at`, and optional `deleted_at`. Event and device IDs are UUIDs; project/entity IDs remain bounded strings; entity type is a bounded machine token. Operations are `upsert`, `delete`, and `event`. Revisions are positive local/domain-layer metadata: C9 does not resolve conflicts.

`delete` is a transport tombstone and requires `deleted_at`; it remains in the server log and is returned by pull. C9 never deletes project or entity data as a consequence. Client timestamps must be timezone-aware metadata only.

No envelope, PostgreSQL table, or SQLite outbox contains project names, descriptions, documents, notes, maps, game context, arbitrary JSON, plaintext payload, ciphertext, covers, or attachments. In particular, the existing local `domain_events` table remains Game/domain infrastructure and contains `context_json`; it is not reused as a cloud outbox.

## Delivery and ordering

The local lifecycle is:

```text
local mutation -> stable event_id -> cloud_sync_outbox -> push -> accepted -> delivered locally
```

An event ID is generated before the first network attempt and persisted in the outbox. A retry resends the same envelope and event ID; a network error never generates a replacement ID.

`POST /api/v1/sync/push` accepts at most 100 metadata envelopes atomically. Every new event is checked against C8's `(user_id, project_id)` registry; it never allocates a cloud slot. An unregistered device is rejected. The server locks the per-user `sync_user_state` row, assigns a fresh `server_sequence`, and stores the event. Its `(user_id, event_id)` primary key and `(user_id, server_sequence)` uniqueness enforce isolation and deduplication.

C9 provides at-least-once delivery with idempotent server acceptance; it does not claim end-to-end exactly-once execution. A retry with canonically identical metadata returns the original sequence with `duplicate=true`. Reusing an event ID with different canonical metadata is rejected with `409 sync_event_id_conflict`. This covers concurrent duplicate deliveries as well: state-row locking serializes sequence allocation and database constraints remain the final guard.

Server sequence is transport ordering, not conflict resolution. It is monotonically allocated per user account, does not depend on client clocks, and is not a claim about which user version is correct. C17 will define content conflict resolution.

## Pull and acknowledgements

`GET /api/v1/sync/pull?since=<cursor>&device_id=<uuid>&limit=...` uses only `server_sequence`, returns events with sequence strictly greater than the cursor in ascending sequence order, and uses bounded cursor pagination (default 200, maximum 500). Own events may be returned and clients deduplicate by `event_id`. An empty page retains the supplied cursor.

`POST /api/v1/sync/ack` records a registered device's monotonic acknowledged cursor. Equal acknowledgements are idempotent; smaller ones do not regress it; cursors above the user's current high-water mark fail with `sync_cursor_invalid`. C9 performs no event-log garbage collection.

All request contracts reject unexpected fields, so a `payload`, `content`, or arbitrary JSON field is not an accidental upload path. Unsupported protocol versions return `sync_protocol_version_unsupported`.

## Local foundation and deferred work

SQLite schema version 8 adds account-scoped `cloud_sync_state` (device and cursors) and `cloud_sync_outbox` (retry metadata and tombstones). Neither table has a content/payload/ciphertext column or an entity foreign key that could erase a tombstone.

C8's `encryptedInitialUpload = false` remains false. These endpoints do not make `LOCAL_ONLY -> ENABLING_SYNC -> SYNCED` a production flow, do not simulate `SYNCED`, and do not alter legacy `work_method == "sync"`.

C9 does not apply Game events, XP, coins, streaks, rewards, or `context_json`; it proves only transport-log idempotency. It also does not introduce desktop background sync, Android/Web clients, C21 cookie authentication, C7 Admin changes, encrypted objects, or ciphertext storage. The next work remains C10 threat model, C11 crypto module, C12 crypto tests, C13 encrypted schema, then C15's first encrypted object lifecycle.
