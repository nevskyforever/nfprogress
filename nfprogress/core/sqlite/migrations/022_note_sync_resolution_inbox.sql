-- C17 D2A: resolution shares the account-wide inbound sequence and cursor.
ALTER TABLE cloud_sync_inbox RENAME TO cloud_sync_inbox_v21;
DROP INDEX idx_cloud_sync_inbox_processing;
CREATE TABLE cloud_sync_inbox (
 account_id TEXT NOT NULL CHECK(length(account_id) BETWEEN 1 AND 512), event_id TEXT NOT NULL CHECK(length(event_id)=36 AND length(replace(event_id,'-',''))=32 AND substr(event_id,9,1)='-' AND substr(event_id,14,1)='-' AND substr(event_id,19,1)='-' AND substr(event_id,24,1)='-' AND event_id NOT GLOB '*[^0-9A-Fa-f-]*'), server_sequence INTEGER NOT NULL CHECK(server_sequence>=1), device_id TEXT NOT NULL CHECK(length(device_id)=36), project_id TEXT NOT NULL CHECK(length(project_id) BETWEEN 1 AND 512), entity_id TEXT NOT NULL CHECK(length(entity_id) BETWEEN 1 AND 512), entity_type TEXT NOT NULL CHECK(length(entity_type) BETWEEN 1 AND 128), operation TEXT NOT NULL CHECK(operation IN ('upsert','delete','event','resolution')), sync_revision INTEGER NOT NULL CHECK(sync_revision>=1), updated_at TEXT NOT NULL, deleted_at TEXT,
 state TEXT NOT NULL CHECK(state IN ('received','unknown_entity','orphan','applied','conflict','conflict_preserved','rejected')), received_at TEXT NOT NULL, applied_at TEXT, error_code TEXT, conflict_group_id TEXT REFERENCES cloud_sync_note_conflict_groups(group_id) ON DELETE RESTRICT, conflict_preserved_at TEXT,
 PRIMARY KEY(account_id,event_id), UNIQUE(account_id,server_sequence),
 CHECK((operation='delete' AND deleted_at IS NOT NULL) OR (operation!='delete' AND deleted_at IS NULL)),
 CHECK(operation!='resolution' OR (entity_type='note' AND sync_revision>=2)),
 CHECK((state='conflict_preserved' AND conflict_group_id IS NOT NULL AND conflict_preserved_at IS NOT NULL) OR (state!='conflict_preserved' AND conflict_group_id IS NULL AND conflict_preserved_at IS NULL))
);
INSERT INTO cloud_sync_inbox SELECT * FROM cloud_sync_inbox_v21;
DROP TABLE cloud_sync_inbox_v21;
CREATE INDEX idx_cloud_sync_inbox_processing ON cloud_sync_inbox(account_id,state,server_sequence);
CREATE TRIGGER cloud_sync_resolution_inbox_immutable_update BEFORE UPDATE ON cloud_sync_inbox WHEN (OLD.operation='resolution' OR NEW.operation='resolution') AND (NEW.account_id!=OLD.account_id OR NEW.event_id!=OLD.event_id OR NEW.server_sequence!=OLD.server_sequence OR NEW.device_id!=OLD.device_id OR NEW.project_id!=OLD.project_id OR NEW.entity_id!=OLD.entity_id OR NEW.entity_type!=OLD.entity_type OR NEW.operation!=OLD.operation OR NEW.sync_revision!=OLD.sync_revision OR NEW.updated_at!=OLD.updated_at OR NEW.deleted_at IS NOT OLD.deleted_at OR NEW.received_at!=OLD.received_at) BEGIN SELECT RAISE(ABORT,'resolution_inbox_identity_is_immutable'); END;
CREATE TRIGGER cloud_sync_resolution_inbox_immutable_delete BEFORE DELETE ON cloud_sync_inbox WHEN OLD.operation='resolution' BEGIN SELECT RAISE(ABORT,'resolution_inbox_is_immutable'); END;
CREATE TRIGGER cloud_sync_resolution_inbox_object_immutable_update BEFORE UPDATE ON cloud_sync_event_objects WHEN EXISTS(SELECT 1 FROM cloud_sync_inbox inbox WHERE inbox.account_id=OLD.account_id AND inbox.event_id=OLD.event_id AND inbox.operation='resolution') BEGIN SELECT RAISE(ABORT,'resolution_inbox_encrypted_object_is_immutable'); END;
CREATE TRIGGER cloud_sync_resolution_inbox_object_immutable_delete BEFORE DELETE ON cloud_sync_event_objects WHEN EXISTS(SELECT 1 FROM cloud_sync_inbox inbox WHERE inbox.account_id=OLD.account_id AND inbox.event_id=OLD.event_id AND inbox.operation='resolution') BEGIN SELECT RAISE(ABORT,'resolution_inbox_encrypted_object_is_immutable'); END;
