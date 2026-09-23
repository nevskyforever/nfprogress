-- C15.7B.  The capability is checked by a connection-scoped UDF.  Normal
-- Python/Rust connections install the same function fail-closed.
CREATE TABLE cloud_sync_remote_apply_authorizations (
    event_id TEXT PRIMARY KEY NOT NULL,
    account_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    operation TEXT NOT NULL CHECK(operation IN ('upsert','delete')),
    payload_json TEXT,
    prior_payload_json TEXT,
    capability TEXT NOT NULL UNIQUE
);
DROP TRIGGER notes_require_sync_intent_insert;
DROP TRIGGER notes_require_sync_intent_update;
DROP TRIGGER notes_require_sync_intent_delete;

-- Keep migration-010's local branch verbatim in meaning; only the additional
-- branch is available to the dedicated remote-apply connection.
CREATE TRIGGER notes_require_sync_intent_insert BEFORE INSERT ON notes
WHEN EXISTS(SELECT 1 FROM cloud_sync_project_bindings WHERE project_id=NEW.project_id)
AND NOT EXISTS(SELECT 1 FROM cloud_sync_project_bindings b JOIN cloud_sync_outbox e ON e.account_id=b.account_id AND e.project_id=NEW.project_id AND e.entity_id=NEW.id AND e.entity_type='note' AND e.operation='upsert' AND e.lifecycle='unsealed' AND e.local_ordinal>0 JOIN cloud_sync_note_intents i ON i.event_id=e.event_id WHERE b.project_id=NEW.project_id AND i.snapshot_json=NEW.payload_json AND json_extract(NEW.payload_json,'$.id')=NEW.id AND json_extract(NEW.payload_json,'$.project_id')=NEW.project_id AND json_extract(NEW.payload_json,'$.stage_id') IS NEW.stage_id AND json_type(NEW.payload_json,'$.updated_at')='text' AND json_extract(NEW.payload_json,'$.updated_at')=NEW.updated_at)
AND NOT EXISTS(SELECT 1 FROM cloud_sync_remote_apply_authorizations a JOIN cloud_sync_project_bindings b ON b.project_id=a.project_id AND b.account_id=a.account_id WHERE a.project_id=NEW.project_id AND a.entity_id=NEW.id AND a.operation='upsert' AND a.payload_json=NEW.payload_json AND note_sync_remote_apply_authorized(a.capability))
BEGIN SELECT RAISE(ABORT,'bound_note_mutation_requires_matching_sync_intent'); END;
CREATE TRIGGER notes_require_sync_intent_update BEFORE UPDATE ON notes
WHEN (EXISTS(SELECT 1 FROM cloud_sync_project_bindings WHERE project_id=OLD.project_id) OR EXISTS(SELECT 1 FROM cloud_sync_project_bindings WHERE project_id=NEW.project_id))
AND NOT EXISTS(SELECT 1 FROM cloud_sync_project_bindings b JOIN cloud_sync_outbox e ON e.account_id=b.account_id AND e.project_id=NEW.project_id AND e.entity_id=NEW.id AND e.entity_type='note' AND e.operation='upsert' AND e.lifecycle='unsealed' AND e.local_ordinal>0 JOIN cloud_sync_note_intents i ON i.event_id=e.event_id WHERE b.project_id=NEW.project_id AND i.snapshot_json=NEW.payload_json AND json_extract(NEW.payload_json,'$.id')=NEW.id AND json_extract(NEW.payload_json,'$.project_id')=NEW.project_id AND json_extract(NEW.payload_json,'$.stage_id') IS NEW.stage_id AND json_type(NEW.payload_json,'$.updated_at')='text' AND json_extract(NEW.payload_json,'$.updated_at')=NEW.updated_at)
AND NOT EXISTS(SELECT 1 FROM cloud_sync_remote_apply_authorizations a JOIN cloud_sync_project_bindings b ON b.project_id=a.project_id AND b.account_id=a.account_id WHERE OLD.project_id=NEW.project_id AND OLD.id=NEW.id AND a.project_id=NEW.project_id AND a.entity_id=NEW.id AND a.operation='upsert' AND a.payload_json=NEW.payload_json AND a.prior_payload_json=OLD.payload_json AND note_sync_remote_apply_authorized(a.capability))
BEGIN SELECT RAISE(ABORT,'bound_note_mutation_requires_matching_sync_intent'); END;
CREATE TRIGGER notes_require_sync_intent_delete BEFORE DELETE ON notes
WHEN EXISTS(SELECT 1 FROM cloud_sync_project_bindings WHERE project_id=OLD.project_id)
AND NOT EXISTS(SELECT 1 FROM cloud_sync_project_bindings b JOIN cloud_sync_outbox e ON e.account_id=b.account_id AND e.project_id=OLD.project_id AND e.entity_id=OLD.id AND e.entity_type='note' AND e.operation='delete' AND e.lifecycle='unsealed' AND e.local_ordinal>0 JOIN cloud_sync_note_intents i ON i.event_id=e.event_id WHERE b.project_id=OLD.project_id AND json_extract(i.snapshot_json,'$.id')=OLD.id AND json_extract(i.snapshot_json,'$.project_id')=OLD.project_id AND json_extract(i.snapshot_json,'$.stage_id') IS json_extract(OLD.payload_json,'$.stage_id') AND json_extract(i.snapshot_json,'$.source_type') IS json_extract(OLD.payload_json,'$.source_type') AND json_extract(i.snapshot_json,'$.source_map_id') IS json_extract(OLD.payload_json,'$.source_map_id') AND json_extract(i.snapshot_json,'$.source_node_id') IS json_extract(OLD.payload_json,'$.source_node_id') AND json_extract(i.snapshot_json,'$.content_format') IS json_extract(OLD.payload_json,'$.content_format') AND json_type(i.snapshot_json,'$.deleted_at')='text' AND json_extract(i.snapshot_json,'$.deleted_at')=e.deleted_at AND e.updated_at=e.deleted_at)
AND NOT EXISTS(SELECT 1 FROM cloud_sync_remote_apply_authorizations a JOIN cloud_sync_project_bindings b ON b.project_id=a.project_id AND b.account_id=a.account_id WHERE a.project_id=OLD.project_id AND a.entity_id=OLD.id AND a.operation='delete' AND a.prior_payload_json=OLD.payload_json AND note_sync_remote_apply_authorized(a.capability))
BEGIN SELECT RAISE(ABORT,'bound_note_mutation_requires_matching_sync_intent'); END;

CREATE TRIGGER notes_remote_apply_consume_insert AFTER INSERT ON notes BEGIN DELETE FROM cloud_sync_remote_apply_authorizations WHERE project_id=NEW.project_id AND entity_id=NEW.id AND operation='upsert' AND payload_json=NEW.payload_json AND note_sync_remote_apply_authorized(capability); END;
CREATE TRIGGER notes_remote_apply_consume_update AFTER UPDATE ON notes BEGIN DELETE FROM cloud_sync_remote_apply_authorizations WHERE project_id=NEW.project_id AND entity_id=NEW.id AND operation='upsert' AND payload_json=NEW.payload_json AND prior_payload_json=OLD.payload_json AND note_sync_remote_apply_authorized(capability); END;
CREATE TRIGGER notes_remote_apply_consume_delete AFTER DELETE ON notes BEGIN DELETE FROM cloud_sync_remote_apply_authorizations WHERE project_id=OLD.project_id AND entity_id=OLD.id AND operation='delete' AND prior_payload_json=OLD.payload_json AND note_sync_remote_apply_authorized(capability); END;
