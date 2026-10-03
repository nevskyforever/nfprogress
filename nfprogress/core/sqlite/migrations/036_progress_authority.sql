-- Codec11 owns causal progress facts; scalars and progress_order remain projections.
-- Generic immutable ciphertext, inbox/outbox and shared sequence stay unchanged.
CREATE TABLE cloud_progress_migrations (
 account_id TEXT NOT NULL, project_id TEXT NOT NULL, entity_id TEXT NOT NULL, stage_id TEXT,
 lifecycle TEXT NOT NULL CHECK(lifecycle IN ('captured','publication_pending','self_echo_pending','active','conflict','blocked')),
 candidate_id TEXT NOT NULL, blocker TEXT,
 PRIMARY KEY(account_id,project_id,entity_id),
 FOREIGN KEY(project_id,account_id) REFERENCES cloud_sync_project_bindings(project_id,account_id)
);
CREATE TABLE cloud_progress_candidates (
 candidate_id TEXT PRIMARY KEY, account_id TEXT NOT NULL, project_id TEXT NOT NULL,
 entity_id TEXT NOT NULL, stage_id TEXT, event_id TEXT,
 source_json TEXT NOT NULL CHECK(json_valid(source_json)),
 snapshot_json TEXT CHECK(snapshot_json IS NULL OR json_valid(snapshot_json)),
 blocker TEXT,
 UNIQUE(account_id,event_id)
);
CREATE TABLE cloud_progress_events (
 account_id TEXT NOT NULL REFERENCES cloud_sync_state(account_id), event_id TEXT NOT NULL,
 project_id TEXT NOT NULL, entity_id TEXT NOT NULL, stage_id TEXT,
 canonical_frame BLOB NOT NULL CHECK(typeof(canonical_frame)='blob' AND length(canonical_frame) BETWEEN 20 AND 8388608),
 parents_json TEXT NOT NULL CHECK(json_valid(parents_json) AND json_type(parents_json)='array'),
 revision INTEGER NOT NULL CHECK(revision BETWEEN 1 AND 9007199254740991),
 state TEXT NOT NULL CHECK(state IN ('unsealed','sealed','waiting','applied','conflict_preserved')),
 blocker TEXT, server_sequence INTEGER, retry_ordinal INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY(account_id,event_id), UNIQUE(event_id), UNIQUE(account_id,server_sequence)
);
CREATE INDEX progress_retry ON cloud_progress_events(account_id,state,retry_ordinal,event_id);
CREATE TABLE cloud_progress_tips (
 account_id TEXT NOT NULL, project_id TEXT NOT NULL, entity_id TEXT NOT NULL, event_id TEXT NOT NULL,
 PRIMARY KEY(account_id,project_id,entity_id,event_id),
 FOREIGN KEY(account_id,event_id) REFERENCES cloud_progress_events(account_id,event_id)
);
CREATE TABLE cloud_progress_projection (
 account_id TEXT NOT NULL, project_id TEXT NOT NULL, entity_id TEXT NOT NULL,
 head_event_id TEXT NOT NULL, snapshot_json TEXT NOT NULL CHECK(json_valid(snapshot_json)),
 PRIMARY KEY(account_id,project_id,entity_id),
 FOREIGN KEY(account_id,head_event_id) REFERENCES cloud_progress_events(account_id,event_id)
);
CREATE TABLE cloud_progress_apply_ledger (
 account_id TEXT NOT NULL,event_id TEXT NOT NULL,server_sequence INTEGER NOT NULL,
 outcome TEXT NOT NULL CHECK(outcome IN ('applied','conflict_preserved')),
 nonce BLOB NOT NULL CHECK(length(nonce)=24),ciphertext BLOB NOT NULL CHECK(length(ciphertext)>=16),
 PRIMARY KEY(account_id,event_id), UNIQUE(account_id,server_sequence),
 FOREIGN KEY(account_id,event_id) REFERENCES cloud_progress_events(account_id,event_id),
 FOREIGN KEY(account_id,event_id) REFERENCES cloud_sync_inbox(account_id,event_id)
);
CREATE TABLE cloud_progress_local_candidates (
 account_id TEXT NOT NULL,event_id TEXT NOT NULL, project_id TEXT NOT NULL,entity_id TEXT NOT NULL,
 source_json TEXT NOT NULL CHECK(json_valid(source_json)),
 PRIMARY KEY(account_id,event_id),
 FOREIGN KEY(account_id,event_id) REFERENCES cloud_progress_events(account_id,event_id)
);
CREATE TABLE cloud_progress_decisions (
 account_id TEXT NOT NULL,event_id TEXT NOT NULL,expected_tips TEXT NOT NULL CHECK(json_valid(expected_tips)),
 expected_local TEXT NOT NULL CHECK(json_valid(expected_local)),
 PRIMARY KEY(account_id,event_id)
);
CREATE TRIGGER progress_event_immutable BEFORE UPDATE ON cloud_progress_events
WHEN NEW.account_id IS NOT OLD.account_id OR NEW.event_id IS NOT OLD.event_id
 OR NEW.project_id IS NOT OLD.project_id OR NEW.entity_id IS NOT OLD.entity_id OR NEW.stage_id IS NOT OLD.stage_id
 OR NEW.canonical_frame IS NOT OLD.canonical_frame OR NEW.parents_json IS NOT OLD.parents_json
 OR NEW.revision IS NOT OLD.revision OR (OLD.server_sequence IS NOT NULL AND NEW.server_sequence IS NOT OLD.server_sequence)
 OR (OLD.state IN ('applied','conflict_preserved') AND NEW.state IS NOT OLD.state)
BEGIN SELECT RAISE(ABORT,'immutable progress event'); END;
CREATE TRIGGER progress_event_retained BEFORE DELETE ON cloud_progress_events
BEGIN SELECT RAISE(ABORT,'retained progress history'); END;
CREATE TRIGGER progress_object_immutable BEFORE UPDATE ON cloud_sync_event_objects
WHEN EXISTS(SELECT 1 FROM cloud_progress_events WHERE account_id=OLD.account_id AND event_id=OLD.event_id)
BEGIN SELECT RAISE(ABORT,'immutable progress object'); END;
CREATE TRIGGER progress_object_retained BEFORE DELETE ON cloud_sync_event_objects
WHEN EXISTS(SELECT 1 FROM cloud_progress_events WHERE account_id=OLD.account_id AND event_id=OLD.event_id)
BEGIN SELECT RAISE(ABORT,'retained progress object'); END;
CREATE TRIGGER progress_outbox_immutable BEFORE UPDATE ON cloud_sync_outbox
WHEN OLD.entity_type='progress' AND (NEW.event_id IS NOT OLD.event_id OR NEW.account_id IS NOT OLD.account_id
 OR NEW.device_id IS NOT OLD.device_id OR NEW.project_id IS NOT OLD.project_id OR NEW.entity_id IS NOT OLD.entity_id
 OR NEW.entity_type IS NOT OLD.entity_type OR NEW.operation IS NOT OLD.operation OR NEW.revision IS NOT OLD.revision
 OR NEW.updated_at IS NOT OLD.updated_at OR NEW.deleted_at IS NOT OLD.deleted_at OR NEW.parent_event_id IS NOT OLD.parent_event_id
 OR NEW.local_ordinal IS NOT OLD.local_ordinal)
BEGIN SELECT RAISE(ABORT,'immutable progress descriptor'); END;
CREATE TRIGGER cloud_progress_candidates_update BEFORE UPDATE ON cloud_progress_candidates
BEGIN SELECT RAISE(ABORT,'immutable progress evidence'); END;
CREATE TRIGGER cloud_progress_candidates_delete BEFORE DELETE ON cloud_progress_candidates
BEGIN SELECT RAISE(ABORT,'immutable progress evidence'); END;
CREATE TRIGGER cloud_progress_apply_ledger_update BEFORE UPDATE ON cloud_progress_apply_ledger
BEGIN SELECT RAISE(ABORT,'immutable progress evidence'); END;
CREATE TRIGGER cloud_progress_apply_ledger_delete BEFORE DELETE ON cloud_progress_apply_ledger
BEGIN SELECT RAISE(ABORT,'immutable progress evidence'); END;
CREATE TRIGGER cloud_progress_local_candidates_update BEFORE UPDATE ON cloud_progress_local_candidates
BEGIN SELECT RAISE(ABORT,'immutable progress evidence'); END;
CREATE TRIGGER cloud_progress_local_candidates_delete BEFORE DELETE ON cloud_progress_local_candidates
BEGIN SELECT RAISE(ABORT,'immutable progress evidence'); END;
CREATE TRIGGER cloud_progress_decisions_update BEFORE UPDATE ON cloud_progress_decisions
BEGIN SELECT RAISE(ABORT,'immutable progress evidence'); END;
CREATE TRIGGER cloud_progress_decisions_delete BEFORE DELETE ON cloud_progress_decisions
BEGIN SELECT RAISE(ABORT,'immutable progress evidence'); END;

CREATE TABLE cloud_progress_capture_cursor (account_id TEXT NOT NULL,project_id TEXT NOT NULL,entity_id TEXT NOT NULL,next_position INTEGER NOT NULL DEFAULT 0 CHECK(next_position>=0),tail_event_id TEXT,PRIMARY KEY(account_id,project_id,entity_id));
CREATE TABLE cloud_progress_write_intents(account_id TEXT NOT NULL,event_id TEXT NOT NULL,project_id TEXT NOT NULL,entity_id TEXT NOT NULL,stage_id TEXT,entity_payload TEXT NOT NULL CHECK(json_valid(entity_payload)),entries_json TEXT NOT NULL CHECK(json_valid(entries_json)),PRIMARY KEY(account_id,event_id),FOREIGN KEY(account_id,event_id) REFERENCES cloud_progress_events(account_id,event_id));
CREATE TRIGGER progress_write_intents_update BEFORE UPDATE ON cloud_progress_write_intents BEGIN SELECT RAISE(ABORT,'immutable progress intent'); END;
CREATE TRIGGER progress_write_intents_delete BEFORE DELETE ON cloud_progress_write_intents BEGIN SELECT RAISE(ABORT,'retained progress intent'); END;
-- Progress freezes each append immediately; other writers retain their pending-intent rule.
DROP INDEX idx_cloud_sync_outbox_c15_unsealed_entity;
CREATE UNIQUE INDEX idx_cloud_sync_outbox_c15_unsealed_entity
 ON cloud_sync_outbox(account_id,project_id,entity_id,entity_type)
 WHERE lifecycle='unsealed' AND entity_type NOT IN ('project_metadata','progress');

CREATE TRIGGER progress_insert_guard BEFORE INSERT ON progress_entries WHEN EXISTS(SELECT 1 FROM cloud_progress_migrations WHERE project_id=NEW.project_id AND stage_id IS NEW.stage_id) AND NOT EXISTS(SELECT 1 FROM cloud_progress_write_intents w JOIN cloud_progress_events e USING(account_id,event_id) JOIN cloud_progress_projection p ON p.account_id=w.account_id AND p.project_id=w.project_id AND p.entity_id=w.entity_id AND p.head_event_id=w.event_id WHERE w.project_id=NEW.project_id AND w.stage_id IS NEW.stage_id AND e.state IN ('unsealed','sealed') AND EXISTS(SELECT 1 FROM json_each(w.entries_json) j WHERE json_extract(j.value,'$.id')=NEW.id AND json(j.value)=json(NEW.payload_json) AND json_extract(j.value,'$.created_at') IS NEW.created_at AND json_extract(j.value,'$.added_symbols') IS NEW.added_symbols AND json_extract(j.value,'$.added_progress') IS NEW.added_progress)) AND NOT EXISTS(SELECT 1 FROM cloud_sync_remote_apply_authorizations a JOIN cloud_progress_events e ON e.account_id=a.account_id AND e.event_id=a.event_id WHERE a.project_id=NEW.project_id AND e.stage_id IS NEW.stage_id AND e.project_id=a.project_id AND e.entity_id=a.entity_id AND note_sync_remote_apply_authorized(a.capability) AND EXISTS(SELECT 1 FROM json_each(a.payload_json,'$.entries') j WHERE json_extract(j.value,'$.id')=NEW.id AND json(j.value)=json(NEW.payload_json) AND json_extract(j.value,'$.created_at') IS NEW.created_at AND json_extract(j.value,'$.added_symbols') IS NEW.added_symbols AND json_extract(j.value,'$.added_progress') IS NEW.added_progress)) BEGIN SELECT RAISE(ABORT,'progress_mutation_requires_matching_intent'); END;

CREATE TRIGGER progress_update_guard BEFORE UPDATE ON progress_entries WHEN EXISTS(SELECT 1 FROM cloud_progress_migrations WHERE project_id=NEW.project_id AND stage_id IS NEW.stage_id) AND NOT EXISTS(SELECT 1 FROM cloud_progress_write_intents w JOIN cloud_progress_events e USING(account_id,event_id) JOIN cloud_progress_projection p ON p.account_id=w.account_id AND p.project_id=w.project_id AND p.entity_id=w.entity_id AND p.head_event_id=w.event_id WHERE w.project_id=NEW.project_id AND w.stage_id IS NEW.stage_id AND e.state IN ('unsealed','sealed') AND EXISTS(SELECT 1 FROM json_each(w.entries_json) j WHERE json_extract(j.value,'$.id')=NEW.id AND json(j.value)=json(NEW.payload_json) AND json_extract(j.value,'$.created_at') IS NEW.created_at AND json_extract(j.value,'$.added_symbols') IS NEW.added_symbols AND json_extract(j.value,'$.added_progress') IS NEW.added_progress)) AND NOT EXISTS(SELECT 1 FROM cloud_sync_remote_apply_authorizations a JOIN cloud_progress_events e ON e.account_id=a.account_id AND e.event_id=a.event_id WHERE a.project_id=NEW.project_id AND e.stage_id IS NEW.stage_id AND e.project_id=a.project_id AND e.entity_id=a.entity_id AND note_sync_remote_apply_authorized(a.capability) AND EXISTS(SELECT 1 FROM json_each(a.payload_json,'$.entries') j WHERE json_extract(j.value,'$.id')=NEW.id AND json(j.value)=json(NEW.payload_json) AND json_extract(j.value,'$.created_at') IS NEW.created_at AND json_extract(j.value,'$.added_symbols') IS NEW.added_symbols AND json_extract(j.value,'$.added_progress') IS NEW.added_progress)) BEGIN SELECT RAISE(ABORT,'progress_mutation_requires_matching_intent'); END;

CREATE TRIGGER progress_delete_guard BEFORE DELETE ON progress_entries WHEN EXISTS(SELECT 1 FROM cloud_progress_migrations WHERE project_id=OLD.project_id AND stage_id IS OLD.stage_id) AND NOT EXISTS(SELECT 1 FROM cloud_progress_write_intents w JOIN cloud_progress_events e USING(account_id,event_id) JOIN cloud_progress_projection p ON p.account_id=w.account_id AND p.project_id=w.project_id AND p.entity_id=w.entity_id AND p.head_event_id=w.event_id WHERE w.project_id=OLD.project_id AND w.stage_id IS OLD.stage_id AND e.state IN ('unsealed','sealed') ) AND NOT EXISTS(SELECT 1 FROM cloud_sync_remote_apply_authorizations a JOIN cloud_progress_events e ON e.account_id=a.account_id AND e.event_id=a.event_id WHERE a.project_id=OLD.project_id AND e.stage_id IS OLD.stage_id AND e.project_id=a.project_id AND e.entity_id=a.entity_id AND note_sync_remote_apply_authorized(a.capability) ) BEGIN SELECT RAISE(ABORT,'progress_mutation_requires_matching_intent'); END;

CREATE TRIGGER projects_progress_projection_guard BEFORE UPDATE ON projects WHEN (json_extract(NEW.payload_json,'$.total') IS NOT json_extract(OLD.payload_json,'$.total') OR json_extract(NEW.payload_json,'$.progress') IS NOT json_extract(OLD.payload_json,'$.progress') OR json_extract(NEW.payload_json,'$.progress_entries') IS NOT json_extract(OLD.payload_json,'$.progress_entries')) AND EXISTS(SELECT 1 FROM cloud_progress_migrations WHERE project_id=NEW.id) AND NOT EXISTS(SELECT 1 FROM cloud_progress_write_intents w JOIN cloud_progress_events e USING(account_id,event_id) JOIN cloud_progress_projection p ON p.account_id=w.account_id AND p.project_id=w.project_id AND p.entity_id=w.entity_id AND p.head_event_id=w.event_id WHERE w.project_id=NEW.id AND w.stage_id IS NULL AND e.state IN ('unsealed','sealed')  AND json_extract(w.entity_payload,'$.total') IS json_extract(NEW.payload_json,'$.total') AND json_extract(w.entity_payload,'$.progress') IS json_extract(NEW.payload_json,'$.progress') AND json_extract(w.entity_payload,'$.progress_entries') IS json_extract(NEW.payload_json,'$.progress_entries')) AND NOT EXISTS(SELECT 1 FROM cloud_sync_remote_apply_authorizations a JOIN cloud_progress_events e ON e.account_id=a.account_id AND e.event_id=a.event_id WHERE a.project_id=NEW.id AND e.stage_id IS NULL AND e.project_id=a.project_id AND e.entity_id=a.entity_id AND note_sync_remote_apply_authorized(a.capability)  AND json_extract(a.payload_json,'$.entity_payload.total') IS json_extract(NEW.payload_json,'$.total') AND json_extract(a.payload_json,'$.entity_payload.progress') IS json_extract(NEW.payload_json,'$.progress') AND json_extract(a.payload_json,'$.entity_payload.progress_entries') IS json_extract(NEW.payload_json,'$.progress_entries')) AND NOT (EXISTS(SELECT 1 FROM stages WHERE project_id=NEW.id) AND json_extract(NEW.payload_json,'$.progress_entries') IS json_extract(OLD.payload_json,'$.progress_entries') AND json_extract(NEW.payload_json,'$.total') IS (SELECT SUM(COALESCE(json_extract(payload_json,'$.total'),0.0)) FROM stages WHERE project_id=NEW.id) AND json_extract(NEW.payload_json,'$.progress') IS CASE WHEN NEW.infinite OR COALESCE(NEW.goal,0)<=0 THEN 0.0 ELSE json_extract(NEW.payload_json,'$.total')/NEW.goal*100.0 END) BEGIN SELECT RAISE(ABORT,'progress_scalar_is_derived'); END;

CREATE TRIGGER stages_progress_projection_guard BEFORE UPDATE ON stages WHEN (json_extract(NEW.payload_json,'$.total') IS NOT json_extract(OLD.payload_json,'$.total') OR json_extract(NEW.payload_json,'$.progress') IS NOT json_extract(OLD.payload_json,'$.progress') OR json_extract(NEW.payload_json,'$.progress_entries') IS NOT json_extract(OLD.payload_json,'$.progress_entries')) AND EXISTS(SELECT 1 FROM cloud_progress_migrations WHERE project_id=NEW.project_id AND stage_id IS NEW.id) AND NOT EXISTS(SELECT 1 FROM cloud_progress_write_intents w JOIN cloud_progress_events e USING(account_id,event_id) JOIN cloud_progress_projection p ON p.account_id=w.account_id AND p.project_id=w.project_id AND p.entity_id=w.entity_id AND p.head_event_id=w.event_id WHERE w.project_id=NEW.project_id AND w.stage_id IS NEW.id AND e.state IN ('unsealed','sealed')  AND json_extract(w.entity_payload,'$.total') IS json_extract(NEW.payload_json,'$.total') AND json_extract(w.entity_payload,'$.progress') IS json_extract(NEW.payload_json,'$.progress') AND json_extract(w.entity_payload,'$.progress_entries') IS json_extract(NEW.payload_json,'$.progress_entries')) AND NOT EXISTS(SELECT 1 FROM cloud_sync_remote_apply_authorizations a JOIN cloud_progress_events e ON e.account_id=a.account_id AND e.event_id=a.event_id WHERE a.project_id=NEW.project_id AND e.stage_id IS NEW.id AND e.project_id=a.project_id AND e.entity_id=a.entity_id AND note_sync_remote_apply_authorized(a.capability)  AND json_extract(a.payload_json,'$.entity_payload.total') IS json_extract(NEW.payload_json,'$.total') AND json_extract(a.payload_json,'$.entity_payload.progress') IS json_extract(NEW.payload_json,'$.progress') AND json_extract(a.payload_json,'$.entity_payload.progress_entries') IS json_extract(NEW.payload_json,'$.progress_entries')) BEGIN SELECT RAISE(ABORT,'progress_scalar_is_derived'); END;

-- Global positions are compatibility placement; admitted chains never have an order writer.
CREATE TRIGGER progress_order_admitted_update BEFORE UPDATE ON progress_order
WHEN EXISTS(SELECT 1 FROM progress_entries e JOIN cloud_progress_migrations m ON m.project_id=e.project_id AND m.stage_id IS e.stage_id WHERE e.id=OLD.entry_id) AND NOT (NEW.entry_id IS OLD.entry_id AND NEW.position=(SELECT COUNT(*) FROM progress_order WHERE position<OLD.position) AND (EXISTS(SELECT 1 FROM cloud_sync_remote_apply_authorizations a JOIN cloud_progress_events e ON e.account_id=a.account_id AND e.event_id=a.event_id WHERE note_sync_remote_apply_authorized(a.capability)) OR EXISTS(SELECT 1 FROM cloud_progress_write_intents w JOIN cloud_progress_events e USING(account_id,event_id) JOIN cloud_progress_projection p ON p.account_id=w.account_id AND p.project_id=w.project_id AND p.entity_id=w.entity_id AND p.head_event_id=w.event_id WHERE e.state IN ('unsealed','sealed'))))
BEGIN SELECT RAISE(ABORT,'progress_order_is_derived'); END;
CREATE TRIGGER progress_order_admitted_insert BEFORE INSERT ON progress_order
WHEN EXISTS(SELECT 1 FROM progress_entries e JOIN cloud_progress_migrations m ON m.project_id=e.project_id AND m.stage_id IS e.stage_id WHERE e.id=NEW.entry_id)
AND (NEW.position IS NOT (SELECT COALESCE(MAX(position),-1)+1 FROM progress_order)
 OR NOT EXISTS(SELECT 1 FROM progress_entries row JOIN cloud_progress_write_intents w ON w.project_id=row.project_id AND w.stage_id IS row.stage_id JOIN cloud_progress_events e USING(account_id,event_id) JOIN cloud_progress_projection p ON p.account_id=w.account_id AND p.project_id=w.project_id AND p.entity_id=w.entity_id AND p.head_event_id=w.event_id WHERE row.id=NEW.entry_id AND e.state IN ('unsealed','sealed'))
 AND NOT EXISTS(SELECT 1 FROM progress_entries row JOIN cloud_sync_remote_apply_authorizations a ON a.project_id=row.project_id JOIN cloud_progress_events e ON e.account_id=a.account_id AND e.event_id=a.event_id AND e.stage_id IS row.stage_id WHERE row.id=NEW.entry_id AND note_sync_remote_apply_authorized(a.capability)))
BEGIN SELECT RAISE(ABORT,'progress_order_is_derived'); END;
CREATE TRIGGER progress_order_admitted_delete BEFORE DELETE ON progress_order
WHEN EXISTS(SELECT 1 FROM progress_entries e JOIN cloud_progress_migrations m ON m.project_id=e.project_id AND m.stage_id IS e.stage_id WHERE e.id=OLD.entry_id)
AND NOT EXISTS(SELECT 1 FROM progress_entries row JOIN cloud_progress_write_intents w ON w.project_id=row.project_id AND w.stage_id IS row.stage_id JOIN cloud_progress_events e USING(account_id,event_id) JOIN cloud_progress_projection p ON p.account_id=w.account_id AND p.project_id=w.project_id AND p.entity_id=w.entity_id AND p.head_event_id=w.event_id WHERE row.id=OLD.entry_id AND e.state IN ('unsealed','sealed'))
AND NOT EXISTS(SELECT 1 FROM progress_entries row JOIN cloud_sync_remote_apply_authorizations a ON a.project_id=row.project_id JOIN cloud_progress_events e ON e.account_id=a.account_id AND e.event_id=a.event_id AND e.stage_id IS row.stage_id WHERE row.id=OLD.entry_id AND note_sync_remote_apply_authorized(a.capability))
BEGIN SELECT RAISE(ABORT,'progress_order_is_derived'); END;

-- Moving a row cannot escape the admitted source-scope guards.
CREATE TRIGGER progress_admitted_identity_guard BEFORE UPDATE ON progress_entries
WHEN (NEW.id IS NOT OLD.id OR NEW.project_id IS NOT OLD.project_id OR NEW.stage_id IS NOT OLD.stage_id)
AND EXISTS(SELECT 1 FROM cloud_progress_migrations WHERE project_id=OLD.project_id AND stage_id IS OLD.stage_id)
BEGIN SELECT RAISE(ABORT,'progress_identity_is_immutable'); END;
