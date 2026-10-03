-- Codec10 owns full document content/title/scope; filesystem bindings remain local.
-- Generic immutable ciphertext, inbox/outbox and shared sequence stay unchanged.
CREATE TABLE cloud_document_migrations (
 account_id TEXT NOT NULL, project_id TEXT NOT NULL, entity_id TEXT NOT NULL, stage_id TEXT,
 lifecycle TEXT NOT NULL CHECK(lifecycle IN ('captured','publication_pending','self_echo_pending','active','conflict','blocked')),
 candidate_id TEXT NOT NULL, blocker TEXT,
 PRIMARY KEY(account_id,project_id,entity_id),
 FOREIGN KEY(project_id,account_id) REFERENCES cloud_sync_project_bindings(project_id,account_id)
);
CREATE TABLE cloud_document_candidates (
 candidate_id TEXT PRIMARY KEY, account_id TEXT NOT NULL, project_id TEXT NOT NULL,
 entity_id TEXT NOT NULL, stage_id TEXT, event_id TEXT,
 source_json TEXT NOT NULL CHECK(json_valid(source_json)),
 snapshot_json TEXT CHECK(snapshot_json IS NULL OR json_valid(snapshot_json)),
 blocker TEXT,
 UNIQUE(account_id,event_id)
);
CREATE TABLE cloud_document_events (
 account_id TEXT NOT NULL REFERENCES cloud_sync_state(account_id), event_id TEXT NOT NULL,
 project_id TEXT NOT NULL, entity_id TEXT NOT NULL, stage_id TEXT,
 canonical_frame BLOB NOT NULL CHECK(typeof(canonical_frame)='blob' AND length(canonical_frame) BETWEEN 20 AND 8388608),
 parents_json TEXT NOT NULL CHECK(json_valid(parents_json) AND json_type(parents_json)='array'),
 revision INTEGER NOT NULL CHECK(revision BETWEEN 1 AND 9007199254740991),
 state TEXT NOT NULL CHECK(state IN ('unsealed','sealed','waiting','applied','conflict_preserved')),
 blocker TEXT, server_sequence INTEGER, retry_ordinal INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY(account_id,event_id), UNIQUE(event_id), UNIQUE(account_id,server_sequence)
);
CREATE INDEX document_retry ON cloud_document_events(account_id,state,retry_ordinal,event_id);
CREATE TABLE cloud_document_tips (
 account_id TEXT NOT NULL, project_id TEXT NOT NULL, entity_id TEXT NOT NULL, event_id TEXT NOT NULL,
 PRIMARY KEY(account_id,project_id,entity_id,event_id),
 FOREIGN KEY(account_id,event_id) REFERENCES cloud_document_events(account_id,event_id)
);
CREATE TABLE cloud_document_projection (
 account_id TEXT NOT NULL, project_id TEXT NOT NULL, entity_id TEXT NOT NULL,
 head_event_id TEXT NOT NULL, snapshot_json TEXT NOT NULL CHECK(json_valid(snapshot_json)),
 PRIMARY KEY(account_id,project_id,entity_id),
 FOREIGN KEY(account_id,head_event_id) REFERENCES cloud_document_events(account_id,event_id)
);
CREATE TABLE cloud_document_apply_ledger (
 account_id TEXT NOT NULL,event_id TEXT NOT NULL,server_sequence INTEGER NOT NULL,
 outcome TEXT NOT NULL CHECK(outcome IN ('applied','conflict_preserved')),
 nonce BLOB NOT NULL CHECK(length(nonce)=24),ciphertext BLOB NOT NULL CHECK(length(ciphertext)>=16),
 PRIMARY KEY(account_id,event_id), UNIQUE(account_id,server_sequence),
 FOREIGN KEY(account_id,event_id) REFERENCES cloud_document_events(account_id,event_id),
 FOREIGN KEY(account_id,event_id) REFERENCES cloud_sync_inbox(account_id,event_id)
);
CREATE TABLE cloud_document_local_candidates (
 account_id TEXT NOT NULL,event_id TEXT NOT NULL, project_id TEXT NOT NULL,entity_id TEXT NOT NULL,
 source_json TEXT NOT NULL CHECK(json_valid(source_json)),
 PRIMARY KEY(account_id,event_id),
 FOREIGN KEY(account_id,event_id) REFERENCES cloud_document_events(account_id,event_id)
);
CREATE TABLE cloud_document_decisions (
 account_id TEXT NOT NULL,event_id TEXT NOT NULL,expected_tips TEXT NOT NULL CHECK(json_valid(expected_tips)),
 expected_local TEXT NOT NULL CHECK(json_valid(expected_local)),
 PRIMARY KEY(account_id,event_id)
);
-- Drafts are local, never fabricated cloud parents. Frozen events never mutate.
CREATE TABLE cloud_document_local_drafts (
 account_id TEXT NOT NULL,project_id TEXT NOT NULL,entity_id TEXT NOT NULL,
 snapshot_json TEXT NOT NULL CHECK(json_valid(snapshot_json)),
 projection_json TEXT NOT NULL CHECK(json_valid(projection_json)),updated_at TEXT NOT NULL,
 PRIMARY KEY(account_id,project_id,entity_id)
);
CREATE TRIGGER document_event_immutable BEFORE UPDATE ON cloud_document_events
WHEN NEW.account_id IS NOT OLD.account_id OR NEW.event_id IS NOT OLD.event_id
 OR NEW.project_id IS NOT OLD.project_id OR NEW.entity_id IS NOT OLD.entity_id OR NEW.stage_id IS NOT OLD.stage_id
 OR NEW.canonical_frame IS NOT OLD.canonical_frame OR NEW.parents_json IS NOT OLD.parents_json
 OR NEW.revision IS NOT OLD.revision OR (OLD.server_sequence IS NOT NULL AND NEW.server_sequence IS NOT OLD.server_sequence)
 OR (OLD.state IN ('applied','conflict_preserved') AND NEW.state IS NOT OLD.state)
BEGIN SELECT RAISE(ABORT,'immutable document event'); END;
CREATE TRIGGER document_event_retained BEFORE DELETE ON cloud_document_events
BEGIN SELECT RAISE(ABORT,'retained document history'); END;
CREATE TRIGGER document_object_immutable BEFORE UPDATE ON cloud_sync_event_objects
WHEN EXISTS(SELECT 1 FROM cloud_document_events WHERE account_id=OLD.account_id AND event_id=OLD.event_id)
BEGIN SELECT RAISE(ABORT,'immutable document object'); END;
CREATE TRIGGER document_object_retained BEFORE DELETE ON cloud_sync_event_objects
WHEN EXISTS(SELECT 1 FROM cloud_document_events WHERE account_id=OLD.account_id AND event_id=OLD.event_id)
BEGIN SELECT RAISE(ABORT,'retained document object'); END;
CREATE TRIGGER document_outbox_immutable BEFORE UPDATE ON cloud_sync_outbox
WHEN OLD.entity_type='document' AND (NEW.event_id IS NOT OLD.event_id OR NEW.account_id IS NOT OLD.account_id
 OR NEW.device_id IS NOT OLD.device_id OR NEW.project_id IS NOT OLD.project_id OR NEW.entity_id IS NOT OLD.entity_id
 OR NEW.entity_type IS NOT OLD.entity_type OR NEW.operation IS NOT OLD.operation OR NEW.revision IS NOT OLD.revision
 OR NEW.updated_at IS NOT OLD.updated_at OR NEW.deleted_at IS NOT OLD.deleted_at OR NEW.parent_event_id IS NOT OLD.parent_event_id
 OR NEW.local_ordinal IS NOT OLD.local_ordinal)
BEGIN SELECT RAISE(ABORT,'immutable document descriptor'); END;
CREATE TRIGGER cloud_document_candidates_update BEFORE UPDATE ON cloud_document_candidates
BEGIN SELECT RAISE(ABORT,'immutable document evidence'); END;
CREATE TRIGGER cloud_document_candidates_delete BEFORE DELETE ON cloud_document_candidates
BEGIN SELECT RAISE(ABORT,'immutable document evidence'); END;
CREATE TRIGGER cloud_document_apply_ledger_update BEFORE UPDATE ON cloud_document_apply_ledger
BEGIN SELECT RAISE(ABORT,'immutable document evidence'); END;
CREATE TRIGGER cloud_document_apply_ledger_delete BEFORE DELETE ON cloud_document_apply_ledger
BEGIN SELECT RAISE(ABORT,'immutable document evidence'); END;
CREATE TRIGGER cloud_document_local_candidates_update BEFORE UPDATE ON cloud_document_local_candidates
BEGIN SELECT RAISE(ABORT,'immutable document evidence'); END;
CREATE TRIGGER cloud_document_local_candidates_delete BEFORE DELETE ON cloud_document_local_candidates
BEGIN SELECT RAISE(ABORT,'immutable document evidence'); END;
CREATE TRIGGER cloud_document_decisions_update BEFORE UPDATE ON cloud_document_decisions
BEGIN SELECT RAISE(ABORT,'immutable document evidence'); END;
CREATE TRIGGER cloud_document_decisions_delete BEFORE DELETE ON cloud_document_decisions
BEGIN SELECT RAISE(ABORT,'immutable document evidence'); END;
CREATE TRIGGER document_insert_guard BEFORE INSERT ON documents
WHEN EXISTS(SELECT 1 FROM cloud_document_migrations WHERE entity_id=NEW.id)
AND NOT EXISTS(SELECT 1 FROM cloud_document_local_drafts d WHERE d.entity_id=NEW.id AND json_extract(d.snapshot_json,'$.id') IS NEW.id AND json_extract(d.snapshot_json,'$.project_id') IS NEW.project_id AND json_extract(d.snapshot_json,'$.stage_id') IS NEW.stage_id AND json_extract(d.snapshot_json,'$.title') IS NEW.title AND json_extract(d.snapshot_json,'$.content_format') IS NEW.content_format AND json_extract(d.snapshot_json,'$.created_at') IS NEW.created_at AND json_extract(d.snapshot_json,'$.content_json')=json(NEW.content_json) AND json_extract(d.snapshot_json,'$.extensions')=json(NEW.extensions_json))
AND NOT EXISTS(SELECT 1 FROM cloud_sync_remote_apply_authorizations a JOIN cloud_document_events e ON e.account_id=a.account_id AND e.event_id=a.event_id
 WHERE e.entity_id=NEW.id AND a.entity_id=e.entity_id AND a.project_id=e.project_id AND json_extract(json_extract(a.payload_json,'$.document'),'$.id') IS NEW.id AND json_extract(json_extract(a.payload_json,'$.document'),'$.project_id') IS NEW.project_id AND json_extract(json_extract(a.payload_json,'$.document'),'$.stage_id') IS NEW.stage_id AND json_extract(json_extract(a.payload_json,'$.document'),'$.title') IS NEW.title AND json_extract(json_extract(a.payload_json,'$.document'),'$.content_format') IS NEW.content_format AND json_extract(json_extract(a.payload_json,'$.document'),'$.created_at') IS NEW.created_at AND json_extract(json_extract(a.payload_json,'$.document'),'$.content_json')=json(NEW.content_json) AND json_extract(json_extract(a.payload_json,'$.document'),'$.extensions')=json(NEW.extensions_json) AND note_sync_remote_apply_authorized(a.capability))
BEGIN SELECT RAISE(ABORT,'document_mutation_requires_matching_intent'); END;

CREATE TRIGGER document_update_guard BEFORE UPDATE ON documents
WHEN EXISTS(SELECT 1 FROM cloud_document_migrations WHERE entity_id=OLD.id)
AND NOT EXISTS(SELECT 1 FROM cloud_document_local_drafts d WHERE d.entity_id=OLD.id AND json_extract(d.snapshot_json,'$.id') IS NEW.id AND json_extract(d.snapshot_json,'$.project_id') IS NEW.project_id AND json_extract(d.snapshot_json,'$.stage_id') IS NEW.stage_id AND json_extract(d.snapshot_json,'$.title') IS NEW.title AND json_extract(d.snapshot_json,'$.content_format') IS NEW.content_format AND json_extract(d.snapshot_json,'$.created_at') IS NEW.created_at AND json_extract(d.snapshot_json,'$.content_json')=json(NEW.content_json) AND json_extract(d.snapshot_json,'$.extensions')=json(NEW.extensions_json))
AND NOT EXISTS(SELECT 1 FROM cloud_sync_remote_apply_authorizations a JOIN cloud_document_events e ON e.account_id=a.account_id AND e.event_id=a.event_id
 WHERE e.entity_id=OLD.id AND a.entity_id=e.entity_id AND a.project_id=e.project_id AND json_extract(json_extract(a.payload_json,'$.document'),'$.id') IS NEW.id AND json_extract(json_extract(a.payload_json,'$.document'),'$.project_id') IS NEW.project_id AND json_extract(json_extract(a.payload_json,'$.document'),'$.stage_id') IS NEW.stage_id AND json_extract(json_extract(a.payload_json,'$.document'),'$.title') IS NEW.title AND json_extract(json_extract(a.payload_json,'$.document'),'$.content_format') IS NEW.content_format AND json_extract(json_extract(a.payload_json,'$.document'),'$.created_at') IS NEW.created_at AND json_extract(json_extract(a.payload_json,'$.document'),'$.content_json')=json(NEW.content_json) AND json_extract(json_extract(a.payload_json,'$.document'),'$.extensions')=json(NEW.extensions_json) AND note_sync_remote_apply_authorized(a.capability))
BEGIN SELECT RAISE(ABORT,'document_mutation_requires_matching_intent'); END;

CREATE TRIGGER document_delete_guard BEFORE DELETE ON documents
WHEN EXISTS(SELECT 1 FROM cloud_document_migrations WHERE entity_id=OLD.id)
AND NOT EXISTS(SELECT 1 FROM cloud_document_local_drafts d WHERE d.entity_id=OLD.id AND json_extract(d.snapshot_json,'$') IS NULL)
AND NOT EXISTS(SELECT 1 FROM cloud_sync_remote_apply_authorizations a JOIN cloud_document_events e ON e.account_id=a.account_id AND e.event_id=a.event_id
 WHERE e.entity_id=OLD.id AND a.entity_id=e.entity_id AND a.project_id=e.project_id AND json_extract(a.payload_json,'$.document') IS NULL AND note_sync_remote_apply_authorized(a.capability))
BEGIN SELECT RAISE(ABORT,'document_mutation_requires_matching_intent'); END;
CREATE TRIGGER document_extension_preservation BEFORE UPDATE ON documents
WHEN OLD.extensions_json IS NOT NEW.extensions_json AND OLD.extensions_json!='{}'
AND EXISTS(SELECT 1 FROM cloud_document_migrations WHERE entity_id=OLD.id)
BEGIN SELECT RAISE(ABORT,'document_unsupported_extension'); END;
CREATE TABLE cloud_document_project_blockers(account_id TEXT NOT NULL,project_id TEXT NOT NULL,blocker TEXT NOT NULL,evidence_json TEXT NOT NULL CHECK(json_valid(evidence_json)),PRIMARY KEY(account_id,project_id));
CREATE TABLE cloud_document_project_consent(account_id TEXT NOT NULL,project_id TEXT NOT NULL,created_at TEXT NOT NULL,PRIMARY KEY(account_id,project_id),FOREIGN KEY(project_id,account_id) REFERENCES cloud_sync_project_bindings(project_id,account_id));
