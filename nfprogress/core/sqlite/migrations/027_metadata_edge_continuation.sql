-- Account-scoped pre-import reconstruction: no project shell/binding is created.
CREATE TABLE cloud_sync_metadata_imports (
 account_id TEXT NOT NULL REFERENCES cloud_sync_state(account_id), project_id TEXT NOT NULL,
 bootstrap_id TEXT NOT NULL, cursor INTEGER NOT NULL DEFAULT 0 CHECK(cursor>=0),
 state TEXT NOT NULL DEFAULT 'running' CHECK(state IN ('running','complete','blocked')),
 blocker TEXT, event_count INTEGER NOT NULL DEFAULT 0 CHECK(event_count BETWEEN 0 AND 3200),
 payload_bytes INTEGER NOT NULL DEFAULT 0 CHECK(payload_bytes BETWEEN 0 AND 16777216),
 PRIMARY KEY(account_id,project_id)
);
CREATE TABLE cloud_sync_metadata_import_events (
 account_id TEXT NOT NULL, project_id TEXT NOT NULL, event_id TEXT NOT NULL,
 server_sequence INTEGER NOT NULL CHECK(server_sequence>0), canonical_payload BLOB NOT NULL,
 PRIMARY KEY(account_id,project_id,event_id), UNIQUE(account_id,project_id,server_sequence),
 FOREIGN KEY(account_id,project_id) REFERENCES cloud_sync_metadata_imports(account_id,project_id)
);
CREATE TABLE cloud_sync_metadata_import_tips (
 account_id TEXT NOT NULL, project_id TEXT NOT NULL, event_id TEXT NOT NULL,
 PRIMARY KEY(account_id,project_id,event_id),
 FOREIGN KEY(account_id,project_id,event_id) REFERENCES cloud_sync_metadata_import_events(account_id,project_id,event_id)
);
CREATE TABLE cloud_sync_metadata_import_pages (
 account_id TEXT NOT NULL, project_id TEXT NOT NULL, expected_cursor INTEGER NOT NULL,
 next_cursor INTEGER NOT NULL, page_identity TEXT NOT NULL, has_more INTEGER NOT NULL,
 PRIMARY KEY(account_id,project_id,expected_cursor),
 FOREIGN KEY(account_id,project_id) REFERENCES cloud_sync_metadata_imports(account_id,project_id)
);
CREATE TABLE cloud_sync_metadata_invalidated_decisions (
 account_id TEXT NOT NULL, event_id TEXT NOT NULL, observed_tips_json TEXT NOT NULL,
 reason TEXT NOT NULL CHECK(reason='tip_set_changed'), invalidated_at TEXT NOT NULL,
 PRIMARY KEY(account_id,event_id),
 FOREIGN KEY(account_id,event_id) REFERENCES cloud_sync_metadata_decisions(account_id,event_id)
);
CREATE TRIGGER cloud_sync_metadata_import_event_immutable_update BEFORE UPDATE ON cloud_sync_metadata_import_events
BEGIN SELECT RAISE(ABORT,'immutable metadata import event'); END;
CREATE TRIGGER cloud_sync_metadata_import_event_immutable_delete BEFORE DELETE ON cloud_sync_metadata_import_events
BEGIN SELECT RAISE(ABORT,'immutable metadata import event'); END;
CREATE TRIGGER cloud_sync_metadata_invalidation_immutable_update BEFORE UPDATE ON cloud_sync_metadata_invalidated_decisions
BEGIN SELECT RAISE(ABORT,'immutable metadata invalidation'); END;
CREATE TRIGGER cloud_sync_metadata_invalidation_immutable_delete BEFORE DELETE ON cloud_sync_metadata_invalidated_decisions
BEGIN SELECT RAISE(ABORT,'immutable metadata invalidation'); END;
CREATE TRIGGER cloud_sync_metadata_import_cursor_forward BEFORE UPDATE ON cloud_sync_metadata_imports
WHEN NEW.cursor<OLD.cursor OR NEW.bootstrap_id IS NOT OLD.bootstrap_id OR NEW.account_id IS NOT OLD.account_id OR NEW.project_id IS NOT OLD.project_id
BEGIN SELECT RAISE(ABORT,'metadata import progress is forward-only'); END;
-- Metadata replacement resolutions may have the same causal revision as the
-- superseded immutable intent. Keep the existing Note/other entity constraints.
DROP INDEX idx_cloud_sync_outbox_c15_unsealed_entity;
CREATE UNIQUE INDEX idx_cloud_sync_outbox_c15_unsealed_entity
 ON cloud_sync_outbox(account_id,project_id,entity_id,entity_type)
 WHERE lifecycle='unsealed' AND entity_type!='project_metadata';
DROP INDEX idx_cloud_sync_outbox_c15_entity_revision;
CREATE UNIQUE INDEX idx_cloud_sync_outbox_c15_entity_revision
 ON cloud_sync_outbox(account_id,project_id,entity_id,entity_type,revision)
 WHERE lifecycle!='legacy' AND entity_type!='project_metadata';
CREATE UNIQUE INDEX idx_cloud_sync_metadata_single_pending_decision
 ON cloud_sync_metadata_decisions(account_id,project_id) WHERE state='pending';
CREATE TRIGGER cloud_sync_metadata_import_page_immutable_update BEFORE UPDATE ON cloud_sync_metadata_import_pages
BEGIN SELECT RAISE(ABORT,'immutable metadata import page'); END;
CREATE TRIGGER cloud_sync_metadata_import_page_immutable_delete BEFORE DELETE ON cloud_sync_metadata_import_pages
BEGIN SELECT RAISE(ABORT,'immutable metadata import page'); END;
