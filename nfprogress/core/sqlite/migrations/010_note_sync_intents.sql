-- C15.4B1 durable Note sync-intent substrate. cloud_sync_outbox remains the
-- only event queue; cloud_sync_note_intents is its typed unsealed sidecar.
CREATE TABLE cloud_sync_project_bindings (
    project_id TEXT PRIMARY KEY NOT NULL
        REFERENCES projects(id) ON DELETE RESTRICT,
    account_id TEXT NOT NULL
        REFERENCES cloud_sync_state(account_id) ON DELETE RESTRICT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX idx_cloud_sync_project_bindings_account
    ON cloud_sync_project_bindings(account_id, project_id);

CREATE TABLE cloud_sync_note_intents (
    event_id TEXT PRIMARY KEY NOT NULL
        REFERENCES cloud_sync_outbox(event_id) ON DELETE CASCADE,
    mutation_generation INTEGER NOT NULL CHECK (mutation_generation >= 1),
    snapshot_json TEXT NOT NULL CHECK (
        json_valid(snapshot_json) AND json_type(snapshot_json) = 'object'
    ),
    seal_state TEXT NOT NULL CHECK (
        seal_state IN ('pending', 'retryable_error', 'blocked', 'invariant_error')
    ),
    seal_attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (seal_attempt_count >= 0),
    last_error_code TEXT CHECK (
        last_error_code IS NULL OR length(last_error_code) BETWEEN 1 AND 128
    ),
    next_attempt_at TEXT,
    state_updated_at TEXT NOT NULL,
    CHECK (
        (seal_state = 'pending' AND last_error_code IS NULL AND next_attempt_at IS NULL)
        OR (seal_state = 'retryable_error' AND last_error_code IS NOT NULL)
        OR (seal_state IN ('blocked', 'invariant_error')
            AND last_error_code IS NOT NULL AND next_attempt_at IS NULL)
    )
);

-- local_ordinal=0 is the compatibility default for pre-C15.4 rows. New
-- C15.4 events always receive a positive ordinal, so old rows cannot make the
-- additive upgrade fail while all new event chains remain unique.
CREATE UNIQUE INDEX idx_cloud_sync_outbox_c15_unsealed_entity
    ON cloud_sync_outbox(account_id, project_id, entity_id, entity_type)
    WHERE lifecycle = 'unsealed';
CREATE UNIQUE INDEX idx_cloud_sync_outbox_c15_entity_revision
    ON cloud_sync_outbox(account_id, project_id, entity_id, entity_type, revision)
    WHERE lifecycle != 'legacy';
CREATE UNIQUE INDEX idx_cloud_sync_outbox_c15_local_ordinal
    ON cloud_sync_outbox(account_id, device_id, local_ordinal)
    WHERE lifecycle != 'legacy' AND local_ordinal > 0;
CREATE INDEX idx_cloud_sync_note_intents_pending
    ON cloud_sync_note_intents(seal_state, next_attempt_at, state_updated_at, event_id)
    WHERE seal_state IN ('pending', 'retryable_error');

CREATE TRIGGER cloud_sync_note_intents_validate_insert
AFTER INSERT ON cloud_sync_note_intents
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1 FROM cloud_sync_outbox AS event
        WHERE event.event_id = NEW.event_id
          AND event.entity_type = 'note'
          AND event.lifecycle = 'unsealed'
          AND event.local_ordinal > 0
          AND event.operation IN ('upsert', 'delete')
          AND json_extract(NEW.snapshot_json, '$.id') = event.entity_id
          AND json_extract(NEW.snapshot_json, '$.project_id') = event.project_id
          AND (
              event.operation = 'upsert'
              OR (
                  json_type(NEW.snapshot_json, '$.stage_id') IS NOT NULL
                  AND json_type(NEW.snapshot_json, '$.source_type') = 'text'
                  AND json_type(NEW.snapshot_json, '$.source_map_id') IS NOT NULL
                  AND json_type(NEW.snapshot_json, '$.source_node_id') IS NOT NULL
                  AND json_type(NEW.snapshot_json, '$.content_format') = 'text'
                  AND json_type(NEW.snapshot_json, '$.deleted_at') = 'text'
                  AND json_extract(NEW.snapshot_json, '$.deleted_at') = event.deleted_at
                  AND event.updated_at = event.deleted_at
              )
          )
    ) THEN RAISE(ABORT, 'note_sync_intent_requires_unsealed_note_event') END;
END;

CREATE TRIGGER cloud_sync_note_intents_validate_update
AFTER UPDATE ON cloud_sync_note_intents
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1 FROM cloud_sync_outbox AS event
        WHERE event.event_id = NEW.event_id
          AND NEW.event_id IS OLD.event_id
          AND event.entity_type = 'note'
          AND event.lifecycle = 'unsealed'
          AND event.local_ordinal > 0
          AND event.operation IN ('upsert', 'delete')
          AND json_extract(NEW.snapshot_json, '$.id') = event.entity_id
          AND json_extract(NEW.snapshot_json, '$.project_id') = event.project_id
          AND (
              event.operation = 'upsert'
              OR (
                  json_type(NEW.snapshot_json, '$.stage_id') IS NOT NULL
                  AND json_type(NEW.snapshot_json, '$.source_type') = 'text'
                  AND json_type(NEW.snapshot_json, '$.source_map_id') IS NOT NULL
                  AND json_type(NEW.snapshot_json, '$.source_node_id') IS NOT NULL
                  AND json_type(NEW.snapshot_json, '$.content_format') = 'text'
                  AND json_type(NEW.snapshot_json, '$.deleted_at') = 'text'
                  AND json_extract(NEW.snapshot_json, '$.deleted_at') = event.deleted_at
                  AND event.updated_at = event.deleted_at
              )
          )
    ) THEN RAISE(ABORT, 'note_sync_intent_requires_unsealed_note_event') END;
END;

-- Identity, revision and ordering are immutable while the plaintext sidecar
-- exists. Coalescing may change only operation/timestamps plus sidecar data.
CREATE TRIGGER cloud_sync_outbox_protect_note_intent_relation
BEFORE UPDATE OF account_id, device_id, project_id, entity_id, entity_type,
                 revision, parent_event_id, local_ordinal, lifecycle
ON cloud_sync_outbox
WHEN EXISTS (
    SELECT 1 FROM cloud_sync_note_intents AS intent
    WHERE intent.event_id = OLD.event_id
)
AND (
    NEW.account_id IS NOT OLD.account_id
    OR NEW.device_id IS NOT OLD.device_id
    OR NEW.project_id IS NOT OLD.project_id
    OR NEW.entity_id IS NOT OLD.entity_id
    OR NEW.entity_type IS NOT OLD.entity_type
    OR NEW.revision IS NOT OLD.revision
    OR NEW.parent_event_id IS NOT OLD.parent_event_id
    OR NEW.local_ordinal IS NOT OLD.local_ordinal
    OR NEW.lifecycle IS NOT OLD.lifecycle
)
BEGIN
    SELECT RAISE(ABORT, 'note_sync_intent_event_identity_is_immutable');
END;

-- Local-only projects are intentionally unaffected. For a bound project the
-- exact future stored payload must already be represented by an unsealed event.
CREATE TRIGGER notes_require_sync_intent_insert
BEFORE INSERT ON notes
WHEN EXISTS (
    SELECT 1 FROM cloud_sync_project_bindings AS binding
    WHERE binding.project_id = NEW.project_id
)
AND NOT EXISTS (
    SELECT 1
    FROM cloud_sync_project_bindings AS binding
    JOIN cloud_sync_outbox AS event
      ON event.account_id = binding.account_id
     AND event.project_id = NEW.project_id
     AND event.entity_id = NEW.id
     AND event.entity_type = 'note'
     AND event.operation = 'upsert'
     AND event.lifecycle = 'unsealed'
     AND event.local_ordinal > 0
    JOIN cloud_sync_note_intents AS intent ON intent.event_id = event.event_id
    WHERE binding.project_id = NEW.project_id
      AND intent.snapshot_json = NEW.payload_json
      AND json_extract(NEW.payload_json, '$.id') = NEW.id
      AND json_extract(NEW.payload_json, '$.project_id') = NEW.project_id
      AND json_extract(NEW.payload_json, '$.stage_id') IS NEW.stage_id
      AND json_type(NEW.payload_json, '$.updated_at') = 'text'
      AND json_extract(NEW.payload_json, '$.updated_at') = NEW.updated_at
)
BEGIN
    SELECT RAISE(ABORT, 'bound_note_mutation_requires_matching_sync_intent');
END;

CREATE TRIGGER notes_require_sync_intent_update
BEFORE UPDATE ON notes
WHEN (
    EXISTS (
        SELECT 1 FROM cloud_sync_project_bindings AS binding
        WHERE binding.project_id = OLD.project_id
    )
    OR EXISTS (
        SELECT 1 FROM cloud_sync_project_bindings AS binding
        WHERE binding.project_id = NEW.project_id
    )
)
AND NOT EXISTS (
    SELECT 1
    FROM cloud_sync_project_bindings AS binding
    JOIN cloud_sync_outbox AS event
      ON event.account_id = binding.account_id
     AND event.project_id = NEW.project_id
     AND event.entity_id = NEW.id
     AND event.entity_type = 'note'
     AND event.operation = 'upsert'
     AND event.lifecycle = 'unsealed'
     AND event.local_ordinal > 0
    JOIN cloud_sync_note_intents AS intent ON intent.event_id = event.event_id
    WHERE binding.project_id = NEW.project_id
      AND intent.snapshot_json = NEW.payload_json
      AND json_extract(NEW.payload_json, '$.id') = NEW.id
      AND json_extract(NEW.payload_json, '$.project_id') = NEW.project_id
      AND json_extract(NEW.payload_json, '$.stage_id') IS NEW.stage_id
      AND json_type(NEW.payload_json, '$.updated_at') = 'text'
      AND json_extract(NEW.payload_json, '$.updated_at') = NEW.updated_at
)
BEGIN
    SELECT RAISE(ABORT, 'bound_note_mutation_requires_matching_sync_intent');
END;

CREATE TRIGGER notes_require_sync_intent_delete
BEFORE DELETE ON notes
WHEN EXISTS (
    SELECT 1 FROM cloud_sync_project_bindings AS binding
    WHERE binding.project_id = OLD.project_id
)
AND NOT EXISTS (
    SELECT 1
    FROM cloud_sync_project_bindings AS binding
    JOIN cloud_sync_outbox AS event
      ON event.account_id = binding.account_id
     AND event.project_id = OLD.project_id
     AND event.entity_id = OLD.id
     AND event.entity_type = 'note'
     AND event.operation = 'delete'
     AND event.lifecycle = 'unsealed'
     AND event.local_ordinal > 0
    JOIN cloud_sync_note_intents AS intent ON intent.event_id = event.event_id
    WHERE binding.project_id = OLD.project_id
      AND json_extract(intent.snapshot_json, '$.id') = OLD.id
      AND json_extract(intent.snapshot_json, '$.project_id') = OLD.project_id
      AND json_extract(intent.snapshot_json, '$.stage_id')
          IS json_extract(OLD.payload_json, '$.stage_id')
      AND json_extract(intent.snapshot_json, '$.source_type')
          IS json_extract(OLD.payload_json, '$.source_type')
      AND json_extract(intent.snapshot_json, '$.source_map_id')
          IS json_extract(OLD.payload_json, '$.source_map_id')
      AND json_extract(intent.snapshot_json, '$.source_node_id')
          IS json_extract(OLD.payload_json, '$.source_node_id')
      AND json_extract(intent.snapshot_json, '$.content_format')
          IS json_extract(OLD.payload_json, '$.content_format')
      AND json_type(intent.snapshot_json, '$.deleted_at') = 'text'
      AND json_extract(intent.snapshot_json, '$.deleted_at') = event.deleted_at
      AND event.updated_at = event.deleted_at
)
BEGIN
    SELECT RAISE(ABORT, 'bound_note_mutation_requires_matching_sync_intent');
END;
