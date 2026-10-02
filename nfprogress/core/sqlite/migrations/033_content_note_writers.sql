-- Forward-only codec8 writer sidecar. C15/C17 remain the sole Note history engine.
CREATE TABLE cloud_content_note_migrations (
 account_id TEXT NOT NULL, project_id TEXT NOT NULL, migration_id TEXT NOT NULL,
 activated INTEGER NOT NULL DEFAULT 0 CHECK(activated IN (0,1)), created_at TEXT NOT NULL,
 PRIMARY KEY(account_id,project_id),
 FOREIGN KEY(project_id) REFERENCES cloud_sync_project_bindings(project_id)
);
CREATE TABLE cloud_content_note_candidates (
 candidate_id TEXT PRIMARY KEY,account_id TEXT NOT NULL,project_id TEXT NOT NULL,note_id TEXT NOT NULL,
 device_id TEXT NOT NULL,event_id TEXT,source_json TEXT NOT NULL CHECK(json_valid(source_json)),
 canonical_frame BLOB,blocker TEXT,created_at TEXT NOT NULL, evidence_json TEXT NOT NULL CHECK(json_valid(evidence_json)),
 UNIQUE(account_id,event_id),
 FOREIGN KEY(account_id,project_id) REFERENCES cloud_content_note_migrations(account_id,project_id)
);
CREATE TRIGGER content_note_candidate_immutable BEFORE UPDATE ON cloud_content_note_candidates
BEGIN SELECT RAISE(ABORT,'immutable content Note candidate'); END;
CREATE TRIGGER content_note_candidate_retained BEFORE DELETE ON cloud_content_note_candidates
BEGIN SELECT RAISE(ABORT,'retained content Note candidate'); END;
CREATE TABLE cloud_content_note_writer_events (
 event_id TEXT PRIMARY KEY REFERENCES cloud_sync_outbox(event_id),account_id TEXT NOT NULL,
 canonical_frame BLOB NOT NULL CHECK(length(canonical_frame)<=8388608),blocker TEXT,
 snapshot_json TEXT NOT NULL CHECK(json_valid(snapshot_json)),mutation_generation INTEGER NOT NULL CHECK(mutation_generation>0)
);
CREATE TRIGGER content_note_writer_frame_immutable BEFORE UPDATE OF canonical_frame,snapshot_json,mutation_generation ON cloud_content_note_writer_events
WHEN EXISTS(SELECT 1 FROM cloud_sync_event_objects o WHERE o.account_id=OLD.account_id AND o.event_id=OLD.event_id)
BEGIN SELECT RAISE(ABORT,'sealed content Note frame is immutable'); END;
CREATE TRIGGER content_note_writer_retained BEFORE DELETE ON cloud_content_note_writer_events
BEGIN SELECT RAISE(ABORT,'retained content Note writer'); END;

DROP TRIGGER notes_require_sync_intent_insert;
DROP TRIGGER notes_require_sync_intent_update;
DROP TRIGGER notes_require_sync_intent_delete;
CREATE TRIGGER notes_require_sync_intent_insert BEFORE INSERT ON notes
WHEN ((json_extract(NEW.payload_json,'$.source_type') IS NULL OR json_extract(NEW.payload_json,'$.content_format') IS NULL) OR (json_extract(NEW.payload_json,'$.source_type')='project' AND json_extract(NEW.payload_json,'$.content_format')='html' AND NEW.stage_id IS NULL) OR EXISTS(SELECT 1 FROM cloud_content_note_migrations m JOIN cloud_sync_project_bindings b ON b.account_id=m.account_id AND b.project_id=m.project_id WHERE m.project_id=NEW.project_id AND (m.activated=1 OR EXISTS(SELECT 1 FROM cloud_content_note_receipts r JOIN cloud_sync_inbox i ON i.account_id=r.account_id AND i.event_id=r.event_id WHERE i.project_id=m.project_id AND r.account_id=m.account_id AND r.outcome='applied')) AND json_extract(NEW.payload_json,'$.source_type')='project') OR EXISTS(SELECT 1 FROM cloud_content_note_receipts r JOIN cloud_sync_inbox i ON i.account_id=r.account_id AND i.event_id=r.event_id JOIN cloud_sync_project_bindings b ON b.account_id=r.account_id AND b.project_id=i.project_id WHERE i.project_id=NEW.project_id AND r.outcome='applied' AND json_extract(NEW.payload_json,'$.source_type')='project'))
AND EXISTS(SELECT 1 FROM cloud_sync_project_bindings WHERE project_id=NEW.project_id)
AND NOT EXISTS(SELECT 1 FROM cloud_content_note_candidates c JOIN cloud_content_note_writer_events e ON e.event_id=c.event_id LEFT JOIN cloud_content_note_receipts r ON r.account_id=c.account_id AND r.event_id=c.event_id WHERE c.project_id=NEW.project_id AND c.note_id=NEW.id AND r.outcome IS NULL)
AND NOT EXISTS(SELECT 1 FROM cloud_sync_project_bindings b JOIN cloud_sync_outbox e ON e.account_id=b.account_id AND e.project_id=NEW.project_id AND e.entity_id=NEW.id AND e.entity_type='note' AND e.operation='upsert' AND e.lifecycle='unsealed' AND e.local_ordinal>0 JOIN cloud_sync_note_intents i ON i.event_id=e.event_id WHERE b.project_id=NEW.project_id AND i.snapshot_json=NEW.payload_json AND json_extract(NEW.payload_json,'$.id')=NEW.id AND json_extract(NEW.payload_json,'$.project_id')=NEW.project_id AND json_extract(NEW.payload_json,'$.stage_id') IS NEW.stage_id AND json_type(NEW.payload_json,'$.updated_at')='text' AND json_extract(NEW.payload_json,'$.updated_at')=NEW.updated_at)
AND NOT EXISTS(SELECT 1 FROM cloud_sync_remote_apply_authorizations a JOIN cloud_sync_project_bindings b ON b.project_id=a.project_id AND b.account_id=a.account_id WHERE a.project_id=NEW.project_id AND a.entity_id=NEW.id AND a.operation='upsert' AND a.payload_json=NEW.payload_json AND note_sync_remote_apply_authorized(a.capability))
BEGIN SELECT RAISE(ABORT,'bound_note_mutation_requires_matching_sync_intent'); END;
CREATE TRIGGER notes_require_sync_intent_update BEFORE UPDATE ON notes
WHEN ((json_extract(OLD.payload_json,'$.source_type') IS NULL OR json_extract(OLD.payload_json,'$.content_format') IS NULL) OR (json_extract(OLD.payload_json,'$.source_type')='project' AND json_extract(OLD.payload_json,'$.content_format')='html' AND OLD.stage_id IS NULL) OR (json_extract(NEW.payload_json,'$.source_type')='project' AND json_extract(NEW.payload_json,'$.content_format')='html' AND NEW.stage_id IS NULL) OR EXISTS(SELECT 1 FROM cloud_content_note_migrations m JOIN cloud_sync_project_bindings b ON b.account_id=m.account_id AND b.project_id=m.project_id WHERE m.project_id=NEW.project_id AND (m.activated=1 OR EXISTS(SELECT 1 FROM cloud_content_note_receipts r JOIN cloud_sync_inbox i ON i.account_id=r.account_id AND i.event_id=r.event_id WHERE i.project_id=m.project_id AND r.account_id=m.account_id AND r.outcome='applied')) AND json_extract(NEW.payload_json,'$.source_type')='project') OR EXISTS(SELECT 1 FROM cloud_content_note_receipts r JOIN cloud_sync_inbox i ON i.account_id=r.account_id AND i.event_id=r.event_id JOIN cloud_sync_project_bindings b ON b.account_id=r.account_id AND b.project_id=i.project_id WHERE i.project_id=NEW.project_id AND r.outcome='applied' AND json_extract(NEW.payload_json,'$.source_type')='project'))
AND (EXISTS(SELECT 1 FROM cloud_sync_project_bindings WHERE project_id=OLD.project_id) OR EXISTS(SELECT 1 FROM cloud_sync_project_bindings WHERE project_id=NEW.project_id))
AND NOT EXISTS(SELECT 1 FROM cloud_content_note_candidates c JOIN cloud_content_note_writer_events e ON e.event_id=c.event_id LEFT JOIN cloud_content_note_receipts r ON r.account_id=c.account_id AND r.event_id=c.event_id WHERE c.project_id=NEW.project_id AND c.note_id=NEW.id AND r.outcome IS NULL)
AND NOT EXISTS(SELECT 1 FROM cloud_sync_project_bindings b JOIN cloud_sync_outbox e ON e.account_id=b.account_id AND e.project_id=NEW.project_id AND e.entity_id=NEW.id AND e.entity_type='note' AND e.operation='upsert' AND e.lifecycle='unsealed' AND e.local_ordinal>0 JOIN cloud_sync_note_intents i ON i.event_id=e.event_id WHERE b.project_id=NEW.project_id AND i.snapshot_json=NEW.payload_json AND json_extract(NEW.payload_json,'$.id')=NEW.id AND json_extract(NEW.payload_json,'$.project_id')=NEW.project_id AND json_extract(NEW.payload_json,'$.stage_id') IS NEW.stage_id AND json_type(NEW.payload_json,'$.updated_at')='text' AND json_extract(NEW.payload_json,'$.updated_at')=NEW.updated_at)
AND NOT EXISTS(SELECT 1 FROM cloud_sync_remote_apply_authorizations a JOIN cloud_sync_project_bindings b ON b.project_id=a.project_id AND b.account_id=a.account_id WHERE OLD.project_id=NEW.project_id AND OLD.id=NEW.id AND a.project_id=NEW.project_id AND a.entity_id=NEW.id AND a.operation='upsert' AND a.payload_json=NEW.payload_json AND a.prior_payload_json=OLD.payload_json AND note_sync_remote_apply_authorized(a.capability))
BEGIN SELECT RAISE(ABORT,'bound_note_mutation_requires_matching_sync_intent'); END;
CREATE TRIGGER notes_require_sync_intent_delete BEFORE DELETE ON notes
WHEN ((json_extract(OLD.payload_json,'$.source_type') IS NULL OR json_extract(OLD.payload_json,'$.content_format') IS NULL) OR (json_extract(OLD.payload_json,'$.source_type')='project' AND json_extract(OLD.payload_json,'$.content_format')='html' AND OLD.stage_id IS NULL) OR EXISTS(SELECT 1 FROM cloud_content_note_migrations m JOIN cloud_sync_project_bindings b ON b.account_id=m.account_id AND b.project_id=m.project_id WHERE m.project_id=OLD.project_id AND (m.activated=1 OR EXISTS(SELECT 1 FROM cloud_content_note_receipts r JOIN cloud_sync_inbox i ON i.account_id=r.account_id AND i.event_id=r.event_id WHERE i.project_id=m.project_id AND r.account_id=m.account_id AND r.outcome='applied')) AND json_extract(OLD.payload_json,'$.source_type')='project') OR EXISTS(SELECT 1 FROM cloud_content_note_receipts r JOIN cloud_sync_inbox i ON i.account_id=r.account_id AND i.event_id=r.event_id JOIN cloud_sync_project_bindings b ON b.account_id=r.account_id AND b.project_id=i.project_id WHERE i.project_id=OLD.project_id AND r.outcome='applied' AND json_extract(OLD.payload_json,'$.source_type')='project'))
AND EXISTS(SELECT 1 FROM cloud_sync_project_bindings WHERE project_id=OLD.project_id)
AND NOT EXISTS(SELECT 1 FROM cloud_content_note_candidates c JOIN cloud_content_note_writer_events e ON e.event_id=c.event_id LEFT JOIN cloud_content_note_receipts r ON r.account_id=c.account_id AND r.event_id=c.event_id WHERE c.project_id=OLD.project_id AND c.note_id=OLD.id AND r.outcome IS NULL)
AND NOT EXISTS(SELECT 1 FROM cloud_sync_project_bindings b JOIN cloud_sync_outbox e ON e.account_id=b.account_id AND e.project_id=OLD.project_id AND e.entity_id=OLD.id AND e.entity_type='note' AND e.operation='delete' AND e.lifecycle='unsealed' AND e.local_ordinal>0 JOIN cloud_sync_note_intents i ON i.event_id=e.event_id WHERE b.project_id=OLD.project_id AND json_extract(i.snapshot_json,'$.id')=OLD.id AND json_extract(i.snapshot_json,'$.project_id')=OLD.project_id AND json_extract(i.snapshot_json,'$.stage_id') IS json_extract(OLD.payload_json,'$.stage_id') AND json_extract(i.snapshot_json,'$.source_type') IS json_extract(OLD.payload_json,'$.source_type') AND json_extract(i.snapshot_json,'$.source_map_id') IS json_extract(OLD.payload_json,'$.source_map_id') AND json_extract(i.snapshot_json,'$.source_node_id') IS json_extract(OLD.payload_json,'$.source_node_id') AND json_extract(i.snapshot_json,'$.content_format') IS json_extract(OLD.payload_json,'$.content_format') AND json_type(i.snapshot_json,'$.deleted_at')='text' AND json_extract(i.snapshot_json,'$.deleted_at')=e.deleted_at AND e.updated_at=e.deleted_at)
AND NOT EXISTS(SELECT 1 FROM cloud_sync_remote_apply_authorizations a JOIN cloud_sync_project_bindings b ON b.project_id=a.project_id AND b.account_id=a.account_id WHERE a.project_id=OLD.project_id AND a.entity_id=OLD.id AND a.operation='delete' AND a.prior_payload_json=OLD.payload_json AND note_sync_remote_apply_authorized(a.capability))
BEGIN SELECT RAISE(ABORT,'bound_note_mutation_requires_matching_sync_intent'); END;


CREATE TABLE cloud_content_note_resolution_events (
 event_id TEXT PRIMARY KEY REFERENCES cloud_sync_note_resolution_outbox(resolution_event_id),
 account_id TEXT NOT NULL, canonical_frame BLOB NOT NULL CHECK(length(canonical_frame)<=8388608), blocker TEXT
);
CREATE TRIGGER content_note_resolution_frame_immutable BEFORE UPDATE OF canonical_frame ON cloud_content_note_resolution_events
BEGIN SELECT RAISE(ABORT,'immutable content Note resolution frame'); END;
CREATE TRIGGER content_note_resolution_retained BEFORE DELETE ON cloud_content_note_resolution_events
BEGIN SELECT RAISE(ABORT,'retained content Note resolution'); END;

CREATE TRIGGER content_note_route_immutable BEFORE UPDATE ON notes
WHEN EXISTS(SELECT 1 FROM cloud_sync_project_bindings WHERE project_id=OLD.project_id)
AND json_extract(OLD.payload_json,'$.source_type')='project'
AND (OLD.id IS NOT NEW.id OR OLD.project_id IS NOT NEW.project_id OR OLD.stage_id IS NOT NEW.stage_id
 OR json_extract(OLD.payload_json,'$.source_type') IS NOT json_extract(NEW.payload_json,'$.source_type')
 OR json_extract(OLD.payload_json,'$.source_map_id') IS NOT json_extract(NEW.payload_json,'$.source_map_id')
 OR json_extract(OLD.payload_json,'$.source_node_id') IS NOT json_extract(NEW.payload_json,'$.source_node_id')
 OR json_extract(OLD.payload_json,'$.content_format') IS NOT json_extract(NEW.payload_json,'$.content_format'))
BEGIN SELECT RAISE(ABORT,'content Note source/owner transition is unsupported'); END;

-- Local edits made after explicit capture but before its verified self echo.
-- These are not cloud events; the frozen candidate never changes.
CREATE TABLE cloud_content_note_pending_local_changes (
 account_id TEXT NOT NULL, project_id TEXT NOT NULL, note_id TEXT NOT NULL,
 operation TEXT NOT NULL CHECK(operation IN ('upsert','delete')),
 snapshot_json TEXT NOT NULL CHECK(json_valid(snapshot_json)),updated_at TEXT NOT NULL,
 PRIMARY KEY(account_id,project_id,note_id)
);

-- Rendered local state must still match when the C17 decision is applied.
CREATE TABLE cloud_content_note_resolution_decisions (
 resolution_event_id TEXT PRIMARY KEY, expected_local_json TEXT NOT NULL CHECK(json_valid(expected_local_json))
);
CREATE TRIGGER content_note_decision_immutable BEFORE UPDATE ON cloud_content_note_resolution_decisions
BEGIN SELECT RAISE(ABORT,'immutable Note decision'); END;
CREATE TRIGGER content_note_decision_retained BEFORE DELETE ON cloud_content_note_resolution_decisions
BEGIN SELECT RAISE(ABORT,'retained Note decision'); END;

-- An unauthenticated local row is evidence, never a synthetic cloud parent.
CREATE TABLE cloud_content_note_local_candidates (
 account_id TEXT NOT NULL,event_id TEXT NOT NULL,project_id TEXT NOT NULL,note_id TEXT NOT NULL,
 local_snapshot TEXT NOT NULL CHECK(json_valid(local_snapshot)),
 PRIMARY KEY(account_id,event_id)
);
CREATE TRIGGER content_note_local_candidate_immutable BEFORE UPDATE ON cloud_content_note_local_candidates
BEGIN SELECT RAISE(ABORT,'immutable local Note candidate'); END;
CREATE TRIGGER content_note_local_candidate_retained BEFORE DELETE ON cloud_content_note_local_candidates
BEGIN SELECT RAISE(ABORT,'retained local Note candidate'); END;
CREATE TABLE cloud_content_note_import_decisions (
 account_id TEXT NOT NULL,event_id TEXT NOT NULL,expected_local TEXT NOT NULL CHECK(json_valid(expected_local)),
 keep_local INTEGER NOT NULL CHECK(keep_local IN (0,1)),updated_at TEXT NOT NULL,
 PRIMARY KEY(account_id,event_id,expected_local,keep_local,updated_at),
 FOREIGN KEY(account_id,event_id) REFERENCES cloud_content_note_local_candidates(account_id,event_id)
);
CREATE TRIGGER content_note_import_decision_immutable BEFORE UPDATE ON cloud_content_note_import_decisions
BEGIN SELECT RAISE(ABORT,'immutable Note import decision'); END;
CREATE TRIGGER content_note_import_decision_retained BEFORE DELETE ON cloud_content_note_import_decisions
BEGIN SELECT RAISE(ABORT,'retained Note import decision'); END;

CREATE TABLE cloud_content_note_writer_scan (
 account_id TEXT NOT NULL,device_id TEXT NOT NULL,sealed INTEGER NOT NULL CHECK(sealed IN (0,1)),last_event_id TEXT NOT NULL,
 PRIMARY KEY(account_id,device_id,sealed)
);
