-- Codec9 owns complete Project/Stage maps and derived Note projections.
-- Generic immutable ciphertext, inbox/outbox and shared sequence stay unchanged.
CREATE TABLE cloud_map_migrations (
 account_id TEXT NOT NULL, project_id TEXT NOT NULL, entity_id TEXT NOT NULL, stage_id TEXT,
 lifecycle TEXT NOT NULL CHECK(lifecycle IN ('captured','publication_pending','self_echo_pending','active','conflict','blocked')),
 candidate_id TEXT NOT NULL, blocker TEXT,
 PRIMARY KEY(account_id,project_id,entity_id),
 FOREIGN KEY(project_id,account_id) REFERENCES cloud_sync_project_bindings(project_id,account_id)
);
CREATE TABLE cloud_map_candidates (
 candidate_id TEXT PRIMARY KEY, account_id TEXT NOT NULL, project_id TEXT NOT NULL,
 entity_id TEXT NOT NULL, stage_id TEXT, event_id TEXT,
 source_json TEXT NOT NULL CHECK(json_valid(source_json)),
 snapshot_json TEXT CHECK(snapshot_json IS NULL OR json_valid(snapshot_json)),
 annotation_evidence TEXT NOT NULL CHECK(json_valid(annotation_evidence)), blocker TEXT,
 UNIQUE(account_id,event_id)
);
CREATE TABLE cloud_map_events (
 account_id TEXT NOT NULL REFERENCES cloud_sync_state(account_id), event_id TEXT NOT NULL,
 project_id TEXT NOT NULL, entity_id TEXT NOT NULL, stage_id TEXT,
 canonical_frame BLOB NOT NULL CHECK(typeof(canonical_frame)='blob' AND length(canonical_frame) BETWEEN 20 AND 8388608),
 parents_json TEXT NOT NULL CHECK(json_valid(parents_json) AND json_type(parents_json)='array'),
 revision INTEGER NOT NULL CHECK(revision BETWEEN 1 AND 9007199254740991),
 state TEXT NOT NULL CHECK(state IN ('unsealed','sealed','waiting','applied','conflict_preserved')),
 blocker TEXT, server_sequence INTEGER, retry_ordinal INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY(account_id,event_id), UNIQUE(event_id), UNIQUE(account_id,server_sequence)
);
CREATE INDEX map_retry ON cloud_map_events(account_id,state,retry_ordinal,event_id);
CREATE TABLE cloud_map_tips (
 account_id TEXT NOT NULL, project_id TEXT NOT NULL, entity_id TEXT NOT NULL, event_id TEXT NOT NULL,
 PRIMARY KEY(account_id,project_id,entity_id,event_id),
 FOREIGN KEY(account_id,event_id) REFERENCES cloud_map_events(account_id,event_id)
);
CREATE TABLE cloud_map_projection (
 account_id TEXT NOT NULL, project_id TEXT NOT NULL, entity_id TEXT NOT NULL,
 head_event_id TEXT NOT NULL, snapshot_json TEXT NOT NULL CHECK(json_valid(snapshot_json)),
 PRIMARY KEY(account_id,project_id,entity_id),
 FOREIGN KEY(account_id,head_event_id) REFERENCES cloud_map_events(account_id,event_id)
);
CREATE TABLE cloud_map_apply_ledger (
 account_id TEXT NOT NULL,event_id TEXT NOT NULL,server_sequence INTEGER NOT NULL,
 outcome TEXT NOT NULL CHECK(outcome IN ('applied','conflict_preserved')),
 nonce BLOB NOT NULL CHECK(length(nonce)=24),ciphertext BLOB NOT NULL CHECK(length(ciphertext)>=16),
 PRIMARY KEY(account_id,event_id), UNIQUE(account_id,server_sequence),
 FOREIGN KEY(account_id,event_id) REFERENCES cloud_map_events(account_id,event_id),
 FOREIGN KEY(account_id,event_id) REFERENCES cloud_sync_inbox(account_id,event_id)
);
CREATE TABLE cloud_map_local_candidates (
 account_id TEXT NOT NULL,event_id TEXT NOT NULL, project_id TEXT NOT NULL,entity_id TEXT NOT NULL,
 source_json TEXT NOT NULL CHECK(json_valid(source_json)),
 PRIMARY KEY(account_id,event_id),
 FOREIGN KEY(account_id,event_id) REFERENCES cloud_map_events(account_id,event_id)
);
CREATE TABLE cloud_map_decisions (
 account_id TEXT NOT NULL,event_id TEXT NOT NULL,expected_tips TEXT NOT NULL CHECK(json_valid(expected_tips)),
 expected_local TEXT NOT NULL CHECK(json_valid(expected_local)),
 PRIMARY KEY(account_id,event_id)
);
CREATE TABLE cloud_map_import_decisions (
 account_id TEXT NOT NULL,event_id TEXT NOT NULL,decision_id TEXT NOT NULL,
 expected_local TEXT NOT NULL CHECK(json_valid(expected_local)),choice TEXT NOT NULL CHECK(choice IN ('remote','local')),
 PRIMARY KEY(account_id,event_id,decision_id)
);
-- Drafts are local, never fabricated cloud parents. Frozen events never mutate.
CREATE TABLE cloud_map_local_drafts (
 account_id TEXT NOT NULL,project_id TEXT NOT NULL,entity_id TEXT NOT NULL,
 snapshot_json TEXT NOT NULL CHECK(json_valid(snapshot_json)),
 projection_json TEXT NOT NULL CHECK(json_valid(projection_json)),updated_at TEXT NOT NULL,
 PRIMARY KEY(account_id,project_id,entity_id)
);
CREATE TABLE cloud_map_combined_groups (
 group_id TEXT PRIMARY KEY,project_id TEXT NOT NULL,expected_json TEXT NOT NULL CHECK(json_valid(expected_json)),
 owners_json TEXT NOT NULL CHECK(json_valid(owners_json)),created_at TEXT NOT NULL
);
CREATE TRIGGER map_event_immutable BEFORE UPDATE ON cloud_map_events
WHEN NEW.account_id IS NOT OLD.account_id OR NEW.event_id IS NOT OLD.event_id
 OR NEW.project_id IS NOT OLD.project_id OR NEW.entity_id IS NOT OLD.entity_id OR NEW.stage_id IS NOT OLD.stage_id
 OR NEW.canonical_frame IS NOT OLD.canonical_frame OR NEW.parents_json IS NOT OLD.parents_json
 OR NEW.revision IS NOT OLD.revision OR (OLD.server_sequence IS NOT NULL AND NEW.server_sequence IS NOT OLD.server_sequence)
 OR (OLD.state IN ('applied','conflict_preserved') AND NEW.state IS NOT OLD.state)
BEGIN SELECT RAISE(ABORT,'immutable map event'); END;
CREATE TRIGGER map_event_retained BEFORE DELETE ON cloud_map_events
BEGIN SELECT RAISE(ABORT,'retained map history'); END;
CREATE TRIGGER map_object_immutable BEFORE UPDATE ON cloud_sync_event_objects
WHEN EXISTS(SELECT 1 FROM cloud_map_events WHERE account_id=OLD.account_id AND event_id=OLD.event_id)
BEGIN SELECT RAISE(ABORT,'immutable map object'); END;
CREATE TRIGGER map_object_retained BEFORE DELETE ON cloud_sync_event_objects
WHEN EXISTS(SELECT 1 FROM cloud_map_events WHERE account_id=OLD.account_id AND event_id=OLD.event_id)
BEGIN SELECT RAISE(ABORT,'retained map object'); END;
CREATE TRIGGER map_outbox_immutable BEFORE UPDATE ON cloud_sync_outbox
WHEN OLD.entity_type='map' AND (NEW.event_id IS NOT OLD.event_id OR NEW.account_id IS NOT OLD.account_id
 OR NEW.device_id IS NOT OLD.device_id OR NEW.project_id IS NOT OLD.project_id OR NEW.entity_id IS NOT OLD.entity_id
 OR NEW.entity_type IS NOT OLD.entity_type OR NEW.operation IS NOT OLD.operation OR NEW.revision IS NOT OLD.revision
 OR NEW.updated_at IS NOT OLD.updated_at OR NEW.deleted_at IS NOT OLD.deleted_at OR NEW.parent_event_id IS NOT OLD.parent_event_id
 OR NEW.local_ordinal IS NOT OLD.local_ordinal)
BEGIN SELECT RAISE(ABORT,'immutable map descriptor'); END;
CREATE TRIGGER cloud_map_candidates_update BEFORE UPDATE ON cloud_map_candidates
BEGIN SELECT RAISE(ABORT,'immutable map evidence'); END;
CREATE TRIGGER cloud_map_candidates_delete BEFORE DELETE ON cloud_map_candidates
BEGIN SELECT RAISE(ABORT,'immutable map evidence'); END;
CREATE TRIGGER cloud_map_apply_ledger_update BEFORE UPDATE ON cloud_map_apply_ledger
BEGIN SELECT RAISE(ABORT,'immutable map evidence'); END;
CREATE TRIGGER cloud_map_apply_ledger_delete BEFORE DELETE ON cloud_map_apply_ledger
BEGIN SELECT RAISE(ABORT,'immutable map evidence'); END;
CREATE TRIGGER cloud_map_local_candidates_update BEFORE UPDATE ON cloud_map_local_candidates
BEGIN SELECT RAISE(ABORT,'immutable map evidence'); END;
CREATE TRIGGER cloud_map_local_candidates_delete BEFORE DELETE ON cloud_map_local_candidates
BEGIN SELECT RAISE(ABORT,'immutable map evidence'); END;
CREATE TRIGGER cloud_map_decisions_update BEFORE UPDATE ON cloud_map_decisions
BEGIN SELECT RAISE(ABORT,'immutable map evidence'); END;
CREATE TRIGGER cloud_map_decisions_delete BEFORE DELETE ON cloud_map_decisions
BEGIN SELECT RAISE(ABORT,'immutable map evidence'); END;
CREATE TRIGGER cloud_map_import_decisions_update BEFORE UPDATE ON cloud_map_import_decisions
BEGIN SELECT RAISE(ABORT,'immutable map evidence'); END;
CREATE TRIGGER cloud_map_import_decisions_delete BEFORE DELETE ON cloud_map_import_decisions
BEGIN SELECT RAISE(ABORT,'immutable map evidence'); END;
CREATE TRIGGER cloud_map_combined_groups_update BEFORE UPDATE ON cloud_map_combined_groups
BEGIN SELECT RAISE(ABORT,'immutable map evidence'); END;
CREATE TRIGGER cloud_map_combined_groups_delete BEFORE DELETE ON cloud_map_combined_groups
BEGIN SELECT RAISE(ABORT,'immutable map evidence'); END;
CREATE TRIGGER map_projects_write_guard BEFORE UPDATE ON projects
WHEN (json_extract(OLD.payload_json,'$.mindmap') IS NOT json_extract(NEW.payload_json,'$.mindmap')
 OR json_extract(OLD.payload_json,'$.map_note_annotations') IS NOT json_extract(NEW.payload_json,'$.map_note_annotations'))
AND EXISTS(SELECT 1 FROM cloud_map_migrations m WHERE m.project_id=OLD.id AND m.stage_id IS NULL AND m.lifecycle!='blocked')
AND NOT EXISTS(SELECT 1 FROM cloud_map_local_drafts d JOIN cloud_map_migrations m
 ON m.account_id=d.account_id AND m.project_id=d.project_id AND m.entity_id=d.entity_id
 WHERE m.project_id=OLD.id AND m.stage_id IS NULL AND json_extract(d.projection_json,'$.owner_payload')=json(NEW.payload_json))
AND NOT EXISTS(SELECT 1 FROM cloud_sync_remote_apply_authorizations a JOIN cloud_map_events e
 ON e.account_id=a.account_id AND e.event_id=a.event_id
 WHERE a.project_id=OLD.id AND a.entity_id=e.entity_id AND e.stage_id IS NULL
 AND json_extract(a.payload_json,'$.owner_payload')=json(NEW.payload_json)
 AND note_sync_remote_apply_authorized(a.capability))
BEGIN SELECT RAISE(ABORT,'map_mutation_requires_matching_intent'); END;
CREATE TRIGGER map_stages_write_guard BEFORE UPDATE ON stages
WHEN (json_extract(OLD.payload_json,'$.mindmap') IS NOT json_extract(NEW.payload_json,'$.mindmap')
 OR json_extract(OLD.payload_json,'$.map_note_annotations') IS NOT json_extract(NEW.payload_json,'$.map_note_annotations'))
AND EXISTS(SELECT 1 FROM cloud_map_migrations m WHERE m.project_id=OLD.project_id AND m.stage_id=OLD.id AND m.lifecycle!='blocked')
AND NOT EXISTS(SELECT 1 FROM cloud_map_local_drafts d JOIN cloud_map_migrations m
 ON m.account_id=d.account_id AND m.project_id=d.project_id AND m.entity_id=d.entity_id
 WHERE m.project_id=OLD.project_id AND m.stage_id=OLD.id AND json_extract(d.projection_json,'$.owner_payload')=json(NEW.payload_json))
AND NOT EXISTS(SELECT 1 FROM cloud_sync_remote_apply_authorizations a JOIN cloud_map_events e
 ON e.account_id=a.account_id AND e.event_id=a.event_id
 WHERE a.project_id=OLD.project_id AND a.entity_id=e.entity_id AND e.stage_id IS OLD.id
 AND json_extract(a.payload_json,'$.owner_payload')=json(NEW.payload_json)
 AND note_sync_remote_apply_authorized(a.capability))
BEGIN SELECT RAISE(ABORT,'map_mutation_requires_matching_intent'); END;
CREATE TRIGGER map_notes_insert_guard BEFORE INSERT ON notes
WHEN json_extract(NEW.payload_json,'$.source_type')='mindmap'
AND EXISTS(SELECT 1 FROM cloud_map_migrations m WHERE m.project_id=NEW.project_id
 AND m.stage_id IS NEW.stage_id AND m.lifecycle!='blocked')
AND NOT EXISTS(SELECT 1 FROM cloud_map_local_drafts d JOIN cloud_map_migrations m
 ON m.account_id=d.account_id AND m.project_id=d.project_id AND m.entity_id=d.entity_id,
 json_each(d.projection_json,'$.notes') n
 WHERE m.project_id=NEW.project_id AND m.stage_id IS NEW.stage_id AND n.value=json(NEW.payload_json))
AND NOT EXISTS(SELECT 1 FROM cloud_sync_remote_apply_authorizations a JOIN cloud_map_events e
 ON e.account_id=a.account_id AND e.event_id=a.event_id,
 json_each(a.payload_json,'$.notes') n
 WHERE a.project_id=NEW.project_id AND e.stage_id IS NEW.stage_id AND n.value=json(NEW.payload_json)
 AND note_sync_remote_apply_authorized(a.capability))
BEGIN SELECT RAISE(ABORT,'derived_note_requires_owning_map_intent'); END;
CREATE TRIGGER map_notes_update_guard BEFORE UPDATE ON notes
WHEN json_extract(NEW.payload_json,'$.source_type')='mindmap'
AND EXISTS(SELECT 1 FROM cloud_map_migrations m WHERE m.project_id=NEW.project_id
 AND m.stage_id IS NEW.stage_id AND m.lifecycle!='blocked')
AND NOT EXISTS(SELECT 1 FROM cloud_map_local_drafts d JOIN cloud_map_migrations m
 ON m.account_id=d.account_id AND m.project_id=d.project_id AND m.entity_id=d.entity_id,
 json_each(d.projection_json,'$.notes') n
 WHERE m.project_id=NEW.project_id AND m.stage_id IS NEW.stage_id AND n.value=json(NEW.payload_json))
AND NOT EXISTS(SELECT 1 FROM cloud_sync_remote_apply_authorizations a JOIN cloud_map_events e
 ON e.account_id=a.account_id AND e.event_id=a.event_id,
 json_each(a.payload_json,'$.notes') n
 WHERE a.project_id=NEW.project_id AND e.stage_id IS NEW.stage_id AND n.value=json(NEW.payload_json)
 AND note_sync_remote_apply_authorized(a.capability))
BEGIN SELECT RAISE(ABORT,'derived_note_requires_owning_map_intent'); END;
CREATE TRIGGER map_notes_delete_guard BEFORE DELETE ON notes
WHEN json_extract(OLD.payload_json,'$.source_type')='mindmap'
AND EXISTS(SELECT 1 FROM cloud_map_migrations m WHERE m.project_id=OLD.project_id
 AND m.stage_id IS OLD.stage_id AND m.lifecycle!='blocked')
AND NOT EXISTS(SELECT 1 FROM cloud_map_local_drafts d JOIN cloud_map_migrations m
 ON m.account_id=d.account_id AND m.project_id=d.project_id AND m.entity_id=d.entity_id,
 json_each(d.projection_json,'$.removed_notes') n
 WHERE m.project_id=OLD.project_id AND m.stage_id IS OLD.stage_id AND n.value=json(OLD.payload_json))
AND NOT EXISTS(SELECT 1 FROM cloud_sync_remote_apply_authorizations a JOIN cloud_map_events e
 ON e.account_id=a.account_id AND e.event_id=a.event_id,
 json_each(a.payload_json,'$.removed_notes') n
 WHERE a.project_id=OLD.project_id AND e.stage_id IS OLD.stage_id AND n.value=json(OLD.payload_json)
 AND note_sync_remote_apply_authorized(a.capability))
BEGIN SELECT RAISE(ABORT,'derived_note_requires_owning_map_intent'); END;
