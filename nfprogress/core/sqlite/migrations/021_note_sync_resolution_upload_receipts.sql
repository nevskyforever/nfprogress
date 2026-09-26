-- C17 Pass 2F-C1. Resolution events have a private v2 lifecycle and cannot
-- reuse cloud_sync_upload_receipts: that v1 table has an intentional FK to
-- cloud_sync_outbox. Rebuild only the resolution outbox to widen its CHECK.
DROP TRIGGER cloud_sync_note_resolution_outbox_immutable_update;
DROP TRIGGER cloud_sync_note_resolution_outbox_immutable_delete;
DROP TRIGGER cloud_sync_note_resolution_dependencies_immutable_update;
DROP TRIGGER cloud_sync_note_resolution_dependencies_immutable_delete;
DROP TRIGGER cloud_sync_note_resolution_outbox_sealed_requires_object;
DROP TRIGGER cloud_sync_note_resolution_object_immutable_update;
DROP TRIGGER cloud_sync_note_resolution_object_immutable_delete;
DROP TRIGGER cloud_sync_note_resolution_freeze_parent_update;
DROP TRIGGER cloud_sync_note_resolution_freeze_parent_delete;
DROP TRIGGER cloud_sync_note_resolution_block_v1_intent;

ALTER TABLE cloud_sync_note_resolution_dependencies RENAME TO cloud_sync_note_resolution_dependencies_v20;
ALTER TABLE cloud_sync_note_resolution_outbox RENAME TO cloud_sync_note_resolution_outbox_v20;
CREATE TABLE cloud_sync_note_resolution_outbox (
 resolution_event_id TEXT PRIMARY KEY NOT NULL REFERENCES cloud_sync_note_pending_resolutions(resolution_event_id) ON DELETE RESTRICT,
 account_id TEXT NOT NULL CHECK(length(account_id) BETWEEN 1 AND 512), device_id TEXT NOT NULL CHECK(length(device_id)=36),
 project_id TEXT NOT NULL CHECK(length(project_id) BETWEEN 1 AND 512), entity_id TEXT NOT NULL CHECK(length(entity_id) BETWEEN 1 AND 512), clone_entity_id TEXT,
 conflict_group_id TEXT NOT NULL REFERENCES cloud_sync_note_conflict_groups(group_id) ON DELETE RESTRICT,
 conflict_generation INTEGER NOT NULL CHECK(conflict_generation>=1), revision INTEGER NOT NULL CHECK(revision>=2),
 parent_event_ids_json TEXT NOT NULL CHECK(json_valid(parent_event_ids_json) AND json_type(parent_event_ids_json)='array' AND json_array_length(parent_event_ids_json) BETWEEN 2 AND 64),
 strategy TEXT NOT NULL CHECK(strategy IN ('choose_version','manual_merge','keep_both','delete')),
 result_operation TEXT NOT NULL CHECK(result_operation IN ('upsert','delete')),
 canonical_payload BLOB NOT NULL CHECK(length(canonical_payload) BETWEEN 1 AND 8388608),
 lifecycle TEXT NOT NULL CHECK(lifecycle IN ('local_pending','sealed_local','accepted')), applied_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(conflict_group_id), CHECK(clone_entity_id IS NULL OR (length(clone_entity_id) BETWEEN 1 AND 512 AND clone_entity_id != entity_id)),
 CHECK((strategy='keep_both')=(clone_entity_id IS NOT NULL))
);
INSERT INTO cloud_sync_note_resolution_outbox SELECT * FROM cloud_sync_note_resolution_outbox_v20;
CREATE TABLE cloud_sync_note_resolution_dependencies (
 resolution_event_id TEXT NOT NULL REFERENCES cloud_sync_note_resolution_outbox(resolution_event_id) ON DELETE RESTRICT,
 parent_event_id TEXT NOT NULL CHECK(length(parent_event_id)=36), source TEXT NOT NULL CHECK(source IN ('remote','remote_applied','local_unsealed')),
 server_sequence INTEGER CHECK(server_sequence IS NULL OR server_sequence>=1), local_mutation_generation INTEGER CHECK(local_mutation_generation IS NULL OR local_mutation_generation>=1),
 local_outbox_lifecycle TEXT CHECK(local_outbox_lifecycle IS NULL OR local_outbox_lifecycle IN ('unsealed','sealed','accepted')),
 upload_receipt_sequence INTEGER CHECK(upload_receipt_sequence IS NULL OR upload_receipt_sequence>=1),
 snapshot_json TEXT NOT NULL CHECK(json_valid(snapshot_json) AND json_type(snapshot_json)='object'), recorded_at TEXT NOT NULL,
 PRIMARY KEY(resolution_event_id,parent_event_id),
 CHECK((source IN ('remote','remote_applied') AND server_sequence IS NOT NULL AND local_mutation_generation IS NULL AND local_outbox_lifecycle IS NULL) OR (source='local_unsealed' AND server_sequence IS NULL AND local_mutation_generation IS NOT NULL AND local_outbox_lifecycle IS NOT NULL))
);
INSERT INTO cloud_sync_note_resolution_dependencies SELECT * FROM cloud_sync_note_resolution_dependencies_v20;
DROP TABLE cloud_sync_note_resolution_dependencies_v20;
DROP TABLE cloud_sync_note_resolution_outbox_v20;
CREATE INDEX idx_cloud_sync_note_resolution_outbox_scope ON cloud_sync_note_resolution_outbox(account_id,project_id,entity_id,lifecycle);

CREATE TABLE cloud_sync_note_resolution_upload_receipts (
 account_id TEXT NOT NULL CHECK(length(account_id) BETWEEN 1 AND 512),
 resolution_event_id TEXT PRIMARY KEY NOT NULL REFERENCES cloud_sync_note_resolution_outbox(resolution_event_id) ON DELETE RESTRICT,
 device_id TEXT NOT NULL CHECK(length(device_id)=36),
 server_sequence INTEGER NOT NULL CHECK(server_sequence>=1),
 duplicate INTEGER NOT NULL CHECK(duplicate IN (0,1)), accepted_at TEXT NOT NULL,
 UNIQUE(account_id,server_sequence)
);
CREATE INDEX idx_cloud_sync_note_resolution_upload_receipts_account ON cloud_sync_note_resolution_upload_receipts(account_id,resolution_event_id);

CREATE TRIGGER cloud_sync_upload_receipts_resolution_sequence_conflict BEFORE INSERT ON cloud_sync_upload_receipts
WHEN EXISTS(SELECT 1 FROM cloud_sync_note_resolution_upload_receipts resolution WHERE resolution.account_id=NEW.account_id AND resolution.server_sequence=NEW.server_sequence)
BEGIN SELECT RAISE(ABORT,'note_sync_receipt_sequence_conflict'); END;
CREATE TRIGGER cloud_sync_note_resolution_receipts_v1_sequence_conflict BEFORE INSERT ON cloud_sync_note_resolution_upload_receipts
WHEN EXISTS(SELECT 1 FROM cloud_sync_upload_receipts receipt WHERE receipt.account_id=NEW.account_id AND receipt.server_sequence=NEW.server_sequence)
BEGIN SELECT RAISE(ABORT,'note_sync_receipt_sequence_conflict'); END;
CREATE TRIGGER cloud_sync_note_resolution_receipt_requires_sealed_object BEFORE INSERT ON cloud_sync_note_resolution_upload_receipts
WHEN NOT EXISTS(SELECT 1 FROM cloud_sync_note_resolution_outbox resolution JOIN cloud_sync_event_objects object ON object.account_id=resolution.account_id AND object.event_id=resolution.resolution_event_id WHERE resolution.resolution_event_id=NEW.resolution_event_id AND resolution.account_id=NEW.account_id AND resolution.device_id=NEW.device_id AND resolution.lifecycle='sealed_local')
BEGIN SELECT RAISE(ABORT,'note_resolution_receipt_requires_sealed_object'); END;

CREATE TRIGGER cloud_sync_note_resolution_outbox_immutable_update BEFORE UPDATE ON cloud_sync_note_resolution_outbox
WHEN NEW.resolution_event_id!=OLD.resolution_event_id OR NEW.account_id!=OLD.account_id OR NEW.device_id!=OLD.device_id OR NEW.project_id!=OLD.project_id OR NEW.entity_id!=OLD.entity_id OR NEW.clone_entity_id IS NOT OLD.clone_entity_id OR NEW.conflict_group_id!=OLD.conflict_group_id OR NEW.conflict_generation!=OLD.conflict_generation OR NEW.revision!=OLD.revision OR NEW.parent_event_ids_json!=OLD.parent_event_ids_json OR NEW.strategy!=OLD.strategy OR NEW.result_operation!=OLD.result_operation OR NEW.canonical_payload!=OLD.canonical_payload OR NEW.applied_at!=OLD.applied_at OR NOT ((OLD.lifecycle='local_pending' AND NEW.lifecycle='sealed_local') OR (OLD.lifecycle='sealed_local' AND NEW.lifecycle='accepted'))
BEGIN SELECT RAISE(ABORT,'note_resolution_outbox_is_immutable'); END;
CREATE TRIGGER cloud_sync_note_resolution_outbox_immutable_delete BEFORE DELETE ON cloud_sync_note_resolution_outbox BEGIN SELECT RAISE(ABORT,'note_resolution_outbox_is_immutable'); END;
CREATE TRIGGER cloud_sync_note_resolution_dependencies_immutable_update BEFORE UPDATE ON cloud_sync_note_resolution_dependencies BEGIN SELECT RAISE(ABORT,'note_resolution_dependency_is_immutable'); END;
CREATE TRIGGER cloud_sync_note_resolution_dependencies_immutable_delete BEFORE DELETE ON cloud_sync_note_resolution_dependencies BEGIN SELECT RAISE(ABORT,'note_resolution_dependency_is_immutable'); END;
CREATE TRIGGER cloud_sync_note_resolution_outbox_sealed_requires_object AFTER UPDATE OF lifecycle ON cloud_sync_note_resolution_outbox WHEN NEW.lifecycle IN ('sealed_local','accepted') AND NOT EXISTS(SELECT 1 FROM cloud_sync_event_objects object WHERE object.account_id=NEW.account_id AND object.event_id=NEW.resolution_event_id) BEGIN SELECT RAISE(ABORT,'note_resolution_sealed_object_missing'); END;
CREATE TRIGGER cloud_sync_note_resolution_outbox_accepted_requires_receipt AFTER UPDATE OF lifecycle ON cloud_sync_note_resolution_outbox WHEN NEW.lifecycle='accepted' AND NOT EXISTS(SELECT 1 FROM cloud_sync_note_resolution_upload_receipts receipt WHERE receipt.account_id=NEW.account_id AND receipt.resolution_event_id=NEW.resolution_event_id AND receipt.device_id=NEW.device_id) BEGIN SELECT RAISE(ABORT,'note_resolution_accepted_receipt_missing'); END;
CREATE TRIGGER cloud_sync_note_resolution_object_immutable_update BEFORE UPDATE ON cloud_sync_event_objects WHEN EXISTS(SELECT 1 FROM cloud_sync_note_resolution_outbox resolution WHERE resolution.account_id=OLD.account_id AND resolution.resolution_event_id=OLD.event_id) BEGIN SELECT RAISE(ABORT,'note_resolution_encrypted_object_is_immutable'); END;
CREATE TRIGGER cloud_sync_note_resolution_object_immutable_delete BEFORE DELETE ON cloud_sync_event_objects WHEN EXISTS(SELECT 1 FROM cloud_sync_note_resolution_outbox resolution WHERE resolution.account_id=OLD.account_id AND resolution.resolution_event_id=OLD.event_id) BEGIN SELECT RAISE(ABORT,'note_resolution_encrypted_object_is_immutable'); END;
CREATE TRIGGER cloud_sync_note_resolution_freeze_parent_update BEFORE UPDATE OF mutation_generation,snapshot_json ON cloud_sync_note_intents WHEN EXISTS(SELECT 1 FROM cloud_sync_note_resolution_dependencies dependency JOIN cloud_sync_note_resolution_outbox resolution ON resolution.resolution_event_id=dependency.resolution_event_id WHERE dependency.parent_event_id=OLD.event_id AND dependency.source='local_unsealed' AND resolution.lifecycle IN ('local_pending','sealed_local','accepted')) BEGIN SELECT RAISE(ABORT,'note_resolution_parent_is_frozen'); END;
CREATE TRIGGER cloud_sync_note_resolution_freeze_parent_delete BEFORE DELETE ON cloud_sync_note_intents WHEN EXISTS(SELECT 1 FROM cloud_sync_note_resolution_dependencies dependency JOIN cloud_sync_note_resolution_outbox resolution ON resolution.resolution_event_id=dependency.resolution_event_id WHERE dependency.parent_event_id=OLD.event_id AND dependency.source='local_unsealed' AND resolution.lifecycle IN ('local_pending','sealed_local','accepted')) AND NOT EXISTS(SELECT 1 FROM cloud_sync_event_objects object WHERE object.event_id=OLD.event_id) BEGIN SELECT RAISE(ABORT,'note_resolution_parent_cannot_be_removed_unsealed'); END;
CREATE TRIGGER cloud_sync_note_resolution_block_v1_intent AFTER INSERT ON cloud_sync_note_intents WHEN EXISTS(SELECT 1 FROM cloud_sync_outbox event JOIN cloud_sync_note_resolution_outbox resolution ON resolution.account_id=event.account_id AND resolution.project_id=event.project_id AND (resolution.entity_id=event.entity_id OR resolution.clone_entity_id=event.entity_id) WHERE event.event_id=NEW.event_id AND resolution.lifecycle IN ('local_pending','sealed_local')) BEGIN SELECT RAISE(ABORT,'note_resolution_requires_protocol_v2'); END;
