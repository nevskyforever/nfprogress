-- C18.4.01 project structural substrate. No automatic capture/publication.
-- Only stage and stage_order share this bounded causal substrate; generic
-- transport objects, inbox, outbox and receipts remain in their existing tables.
CREATE TABLE cloud_sync_stage_candidates (
 candidate_id TEXT PRIMARY KEY NOT NULL,
 account_id TEXT NOT NULL,
 project_id TEXT NOT NULL,
 stage_id TEXT NOT NULL,
 device_id TEXT NOT NULL,
 bootstrap_id TEXT NOT NULL,
 metadata_event_id TEXT NOT NULL,
 generation INTEGER NOT NULL CHECK(generation BETWEEN 1 AND 9007199254740991),
 snapshot_json TEXT NOT NULL CHECK(json_valid(snapshot_json)),
 source_json TEXT NOT NULL CHECK(json_valid(source_json)),
 unsupported_json TEXT NOT NULL CHECK(json_valid(unsupported_json) AND json_type(unsupported_json)='array'),
 created_at TEXT NOT NULL,
 UNIQUE(account_id,project_id,stage_id,device_id,generation),
 FOREIGN KEY(project_id,account_id) REFERENCES cloud_sync_project_bindings(project_id,account_id)
);
CREATE TRIGGER cloud_sync_structural_candidate_no_update BEFORE UPDATE ON cloud_sync_stage_candidates
BEGIN SELECT RAISE(ABORT,'stage_candidate_immutable'); END;
CREATE TRIGGER cloud_sync_structural_candidate_no_delete BEFORE DELETE ON cloud_sync_stage_candidates
BEGIN SELECT RAISE(ABORT,'stage_candidate_immutable'); END;

-- Project binding is deliberately not an FK: an authenticated arrival with
-- missing project/metadata authority must survive as an orphan, never fabricate it.
CREATE TABLE cloud_sync_structural_events (
 account_id TEXT NOT NULL REFERENCES cloud_sync_state(account_id) ON DELETE RESTRICT,
 event_id TEXT NOT NULL CHECK(length(event_id)=36),
 project_id TEXT NOT NULL,
 entity_type TEXT NOT NULL CHECK(entity_type IN ('stage','stage_order')),
 entity_id TEXT NOT NULL,
 canonical_frame BLOB NOT NULL CHECK(typeof(canonical_frame)='blob' AND length(canonical_frame) BETWEEN 20 AND 1048596),
 parent_event_id TEXT,
 metadata_event_id TEXT NOT NULL,
 revision INTEGER NOT NULL CHECK(revision BETWEEN 1 AND 9007199254740991),
 generation INTEGER NOT NULL CHECK(generation BETWEEN 1 AND 9007199254740991),
 operation TEXT NOT NULL CHECK(operation IN ('create','update','delete')),
 state TEXT NOT NULL CHECK(state IN ('unsealed','sealed','orphan','applied','conflict_preserved','tombstone_blocked')),
 blocker TEXT,
 server_sequence INTEGER,
 retry_ordinal INTEGER NOT NULL DEFAULT 0 CHECK(retry_ordinal>=0),
 PRIMARY KEY(account_id,event_id), UNIQUE(event_id), UNIQUE(account_id,server_sequence),
 CHECK((operation='create' AND parent_event_id IS NULL AND revision=1 AND generation=1) OR (operation!='create' AND parent_event_id IS NOT NULL AND revision>1 AND generation>1)),
 CHECK(entity_type!='stage_order' OR (entity_id='stage_order' AND operation!='delete'))
);
CREATE INDEX structural_retry ON cloud_sync_structural_events(account_id,state,retry_ordinal,event_id);
CREATE TRIGGER cloud_sync_structural_event_immutable BEFORE UPDATE ON cloud_sync_structural_events
WHEN NEW.account_id IS NOT OLD.account_id OR NEW.event_id IS NOT OLD.event_id
 OR NEW.project_id IS NOT OLD.project_id OR NEW.entity_type IS NOT OLD.entity_type
 OR NEW.entity_id IS NOT OLD.entity_id OR NEW.canonical_frame IS NOT OLD.canonical_frame
 OR NEW.parent_event_id IS NOT OLD.parent_event_id OR NEW.metadata_event_id IS NOT OLD.metadata_event_id
 OR NEW.revision IS NOT OLD.revision OR NEW.generation IS NOT OLD.generation OR NEW.operation IS NOT OLD.operation
 OR (OLD.server_sequence IS NOT NULL AND NEW.server_sequence IS NOT OLD.server_sequence)
BEGIN SELECT RAISE(ABORT,'structural_event_immutable'); END;
CREATE TRIGGER cloud_sync_structural_event_no_delete BEFORE DELETE ON cloud_sync_structural_events
BEGIN SELECT RAISE(ABORT,'structural_event_immutable'); END;
CREATE TABLE cloud_sync_structural_tips (
 account_id TEXT NOT NULL, project_id TEXT NOT NULL,
 entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, event_id TEXT NOT NULL,
 PRIMARY KEY(account_id,project_id,entity_type,entity_id,event_id),
 FOREIGN KEY(account_id,event_id) REFERENCES cloud_sync_structural_events(account_id,event_id)
);
CREATE TABLE cloud_sync_structural_projection (
 account_id TEXT NOT NULL, project_id TEXT NOT NULL,
 entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, head_event_id TEXT NOT NULL,
 PRIMARY KEY(account_id,project_id,entity_type,entity_id),
 FOREIGN KEY(account_id,head_event_id) REFERENCES cloud_sync_structural_events(account_id,event_id)
);
CREATE TABLE cloud_sync_structural_apply_ledger (
 account_id TEXT NOT NULL, event_id TEXT NOT NULL,
 outcome TEXT NOT NULL CHECK(outcome IN ('applied','conflict_preserved')),
 server_sequence INTEGER NOT NULL,
 nonce BLOB NOT NULL CHECK(length(nonce)=24), ciphertext BLOB NOT NULL CHECK(length(ciphertext)>=16),
 PRIMARY KEY(account_id,event_id),
 FOREIGN KEY(account_id,event_id) REFERENCES cloud_sync_structural_events(account_id,event_id)
);
CREATE TRIGGER cloud_sync_structural_ledger_no_update BEFORE UPDATE ON cloud_sync_structural_apply_ledger
BEGIN SELECT RAISE(ABORT,'structural_ledger_immutable'); END;
CREATE TRIGGER cloud_sync_structural_ledger_no_delete BEFORE DELETE ON cloud_sync_structural_apply_ledger
BEGIN SELECT RAISE(ABORT,'structural_ledger_immutable'); END;
CREATE TRIGGER cloud_sync_structural_object_no_update BEFORE UPDATE ON cloud_sync_event_objects
WHEN EXISTS(SELECT 1 FROM cloud_sync_structural_events WHERE account_id=OLD.account_id AND event_id=OLD.event_id)
BEGIN SELECT RAISE(ABORT,'structural_object_immutable'); END;
CREATE TRIGGER cloud_sync_structural_object_no_delete BEFORE DELETE ON cloud_sync_event_objects
WHEN EXISTS(SELECT 1 FROM cloud_sync_structural_events WHERE account_id=OLD.account_id AND event_id=OLD.event_id)
BEGIN SELECT RAISE(ABORT,'structural_object_immutable'); END;
CREATE TRIGGER cloud_sync_structural_outbox_immutable BEFORE UPDATE ON cloud_sync_outbox
WHEN OLD.entity_type IN ('stage','stage_order') AND (
 NEW.event_id IS NOT OLD.event_id OR NEW.account_id IS NOT OLD.account_id OR NEW.device_id IS NOT OLD.device_id
 OR NEW.project_id IS NOT OLD.project_id OR NEW.entity_type IS NOT OLD.entity_type OR NEW.entity_id IS NOT OLD.entity_id
 OR NEW.operation IS NOT OLD.operation OR NEW.revision IS NOT OLD.revision OR NEW.parent_event_id IS NOT OLD.parent_event_id
 OR NEW.updated_at IS NOT OLD.updated_at OR NEW.deleted_at IS NOT OLD.deleted_at OR NEW.local_ordinal IS NOT OLD.local_ordinal)
BEGIN SELECT RAISE(ABORT,'structural_outbox_immutable'); END;
