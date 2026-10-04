-- C18.5.06: preserve the accepted opaque account inbox while extending routing.
-- Rebuild only its closed entity-type constraint; preserve every catalog byte/proof.
CREATE TEMP TABLE c37_catalog_blockers AS SELECT * FROM cloud_catalog_inbox_blockers;
DROP TABLE cloud_catalog_inbox_blockers;
DROP TRIGGER project_inbox_cross_scope_insert;
CREATE TABLE cloud_sync_account_inbox37 (
    account_id TEXT NOT NULL REFERENCES cloud_sync_state(account_id),
    event_id TEXT NOT NULL CHECK(length(event_id)=36),
    canonical_user_id TEXT NOT NULL CHECK(length(canonical_user_id)=36),
    scope TEXT NOT NULL CHECK(scope='account'),
    server_sequence INTEGER NOT NULL CHECK(server_sequence BETWEEN 1 AND 9007199254740991),
    device_id TEXT NOT NULL CHECK(length(device_id)=36),
    entity_id TEXT NOT NULL CHECK(length(CAST(entity_id AS BLOB)) BETWEEN 1 AND 512),
    entity_type TEXT NOT NULL CHECK(entity_type IN ('folder','folder_order','folder_membership','project_order','account_game')),
    operation TEXT NOT NULL CHECK(operation IN ('upsert','delete')),
    sync_revision INTEGER NOT NULL CHECK(sync_revision BETWEEN 1 AND 9007199254740991),
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    crypto_version INTEGER NOT NULL CHECK(crypto_version=2),
    aad_version INTEGER NOT NULL CHECK(aad_version=2),
    nonce BLOB NOT NULL CHECK(length(nonce)=24),
    ciphertext BLOB NOT NULL CHECK(length(ciphertext) BETWEEN 16 AND 8388624),
    state TEXT NOT NULL DEFAULT 'received' CHECK(state IN ('received','blocked')),
    error_code TEXT CHECK(error_code IN ('account_entity_codec_not_activated','decrypt_failed','account_scope_rejected')),
    received_at TEXT NOT NULL,
    PRIMARY KEY(account_id,event_id),
    UNIQUE(account_id,server_sequence),
    CHECK((operation='delete')=(deleted_at IS NOT NULL))
);
INSERT INTO cloud_sync_account_inbox37 SELECT * FROM cloud_sync_account_inbox;
DROP TABLE cloud_sync_account_inbox;
ALTER TABLE cloud_sync_account_inbox37 RENAME TO cloud_sync_account_inbox;
CREATE INDEX idx_account_inbox_received ON cloud_sync_account_inbox(account_id,state,server_sequence);
-- Scope collisions cannot manufacture a project apply proof at an account sequence.
CREATE TRIGGER account_inbox_cross_scope_insert BEFORE INSERT ON cloud_sync_account_inbox
WHEN EXISTS(SELECT 1 FROM cloud_sync_inbox WHERE account_id=NEW.account_id AND (event_id=NEW.event_id OR server_sequence=NEW.server_sequence))
BEGIN SELECT RAISE(ABORT,'cross-scope inbox collision'); END;
CREATE TRIGGER project_inbox_cross_scope_insert BEFORE INSERT ON cloud_sync_inbox
WHEN EXISTS(SELECT 1 FROM cloud_sync_account_inbox WHERE account_id=NEW.account_id AND (event_id=NEW.event_id OR server_sequence=NEW.server_sequence))
BEGIN SELECT RAISE(ABORT,'cross-scope inbox collision'); END;
CREATE TRIGGER account_inbox_immutable BEFORE UPDATE OF account_id,event_id,canonical_user_id,scope,server_sequence,device_id,entity_id,entity_type,operation,sync_revision,updated_at,deleted_at,crypto_version,aad_version,nonce,ciphertext ON cloud_sync_account_inbox
BEGIN SELECT RAISE(ABORT,'immutable account inbox'); END;

CREATE TABLE cloud_catalog_inbox_blockers (
 account_id TEXT NOT NULL,event_id TEXT NOT NULL,code TEXT NOT NULL,
 PRIMARY KEY(account_id,event_id),
 FOREIGN KEY(account_id,event_id) REFERENCES cloud_sync_account_inbox(account_id,event_id),
 CHECK(code IN ('account_entity_codec_not_activated','decrypt_failed','account_scope_rejected','invalid_catalog_frame','catalog_dependency_missing','catalog_parent_unknown','catalog_membership_changed','catalog_project_unproven','catalog_folder_has_members','catalog_resource_limit','catalog_dependency_conflict','unsupported_catalog_source'))
);

INSERT INTO cloud_catalog_inbox_blockers SELECT * FROM c37_catalog_blockers;
DROP TABLE c37_catalog_blockers;

-- History is immutable; game_state remains a local compatibility read model.
CREATE TABLE cloud_game_events (
 account_id TEXT NOT NULL REFERENCES cloud_sync_state(account_id),event_id TEXT NOT NULL CHECK(length(event_id)=36),
 scope TEXT NOT NULL CHECK(scope IN ('project','account')),owner_key TEXT NOT NULL,
 project_id TEXT,stage_id TEXT,entity_id TEXT NOT NULL,
 canonical_frame BLOB NOT NULL CHECK(typeof(canonical_frame)='blob' AND length(canonical_frame) BETWEEN 20 AND 1048576),
 parents_json TEXT NOT NULL CHECK(json_valid(parents_json) AND json_type(parents_json)='array'),
 revision INTEGER NOT NULL CHECK(revision BETWEEN 1 AND 9007199254740991),
 state TEXT NOT NULL CHECK(state IN ('unsealed','sealed','waiting','applied','conflict_preserved')),
 nonce BLOB,ciphertext BLOB,server_sequence INTEGER,receipt_sequence INTEGER,retry_ordinal INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY(account_id,event_id),UNIQUE(account_id,server_sequence),
 CHECK((scope='account' AND project_id IS NULL AND stage_id IS NULL AND owner_key='account') OR (scope='project' AND project_id IS NOT NULL)),
 CHECK((nonce IS NULL)=(ciphertext IS NULL)),CHECK(nonce IS NULL OR length(nonce)=24),
 CHECK(ciphertext IS NULL OR length(ciphertext) BETWEEN 16 AND 1048592)
);
CREATE INDEX cloud_game_retry ON cloud_game_events(account_id,state,retry_ordinal,event_id);
CREATE TABLE cloud_game_tips (
 account_id TEXT NOT NULL,owner_key TEXT NOT NULL,event_id TEXT NOT NULL,
 PRIMARY KEY(account_id,owner_key,event_id),
 FOREIGN KEY(account_id,event_id) REFERENCES cloud_game_events(account_id,event_id)
);
CREATE TABLE cloud_game_snapshots (
 account_id TEXT NOT NULL,event_id TEXT NOT NULL,snapshot_json TEXT NOT NULL CHECK(json_valid(snapshot_json)),
 PRIMARY KEY(account_id,event_id), FOREIGN KEY(account_id,event_id) REFERENCES cloud_game_events(account_id,event_id)
);
CREATE TABLE cloud_game_projection (
 account_id TEXT NOT NULL,owner_key TEXT NOT NULL,head_event_id TEXT NOT NULL,
 snapshot_json TEXT NOT NULL CHECK(json_valid(snapshot_json)),generation INTEGER NOT NULL CHECK(generation>=1),
 PRIMARY KEY(account_id,owner_key),FOREIGN KEY(account_id,head_event_id) REFERENCES cloud_game_events(account_id,event_id)
);
CREATE TABLE cloud_game_candidates (
 candidate_id TEXT PRIMARY KEY,account_id TEXT NOT NULL,owner_key TEXT NOT NULL,
 source_json TEXT NOT NULL CHECK(json_valid(source_json) AND length(CAST(source_json AS BLOB))<=67108864),
 base_json TEXT CHECK(base_json IS NULL OR json_valid(base_json)),created_at TEXT NOT NULL
);
CREATE TABLE cloud_game_migrations (
 account_id TEXT NOT NULL REFERENCES cloud_sync_state(account_id),owner_key TEXT NOT NULL,
 candidate_id TEXT NOT NULL,lifecycle TEXT NOT NULL CHECK(lifecycle IN ('captured','publication_pending','self_echo_pending','active','conflict','blocked')),
 blocker TEXT,PRIMARY KEY(account_id,owner_key)
);
CREATE TABLE cloud_game_rewards (
 account_id TEXT NOT NULL,reward_id TEXT NOT NULL,event_id TEXT NOT NULL,
 project_action_id TEXT NOT NULL,canonical_frame BLOB NOT NULL,
 PRIMARY KEY(account_id,reward_id),UNIQUE(account_id,event_id),UNIQUE(account_id,project_action_id),
 FOREIGN KEY(account_id,event_id) REFERENCES cloud_game_events(account_id,event_id),
 FOREIGN KEY(account_id,project_action_id) REFERENCES cloud_game_events(account_id,event_id)
);
CREATE TABLE cloud_game_sources (
 account_id TEXT NOT NULL,source_key TEXT NOT NULL,project_action_id TEXT NOT NULL,reward_action_id TEXT,
 PRIMARY KEY(account_id,source_key),UNIQUE(account_id,project_action_id),
 FOREIGN KEY(account_id,project_action_id) REFERENCES cloud_game_events(account_id,event_id),
 FOREIGN KEY(account_id,reward_action_id) REFERENCES cloud_game_events(account_id,event_id)
);
CREATE TABLE cloud_game_compensations (
 account_id TEXT NOT NULL,target_action_id TEXT NOT NULL,event_id TEXT NOT NULL,
 PRIMARY KEY(account_id,target_action_id),UNIQUE(account_id,event_id),
 FOREIGN KEY(account_id,event_id) REFERENCES cloud_game_events(account_id,event_id)
);
CREATE TABLE cloud_game_apply_ledger (
 account_id TEXT NOT NULL,event_id TEXT NOT NULL,server_sequence INTEGER NOT NULL,
 outcome TEXT NOT NULL CHECK(outcome IN ('applied','conflict_preserved')),
 nonce BLOB NOT NULL CHECK(length(nonce)=24),ciphertext BLOB NOT NULL,canonical_frame BLOB NOT NULL,
 PRIMARY KEY(account_id,event_id),UNIQUE(account_id,server_sequence),
 FOREIGN KEY(account_id,event_id) REFERENCES cloud_game_events(account_id,event_id)
);
CREATE TABLE cloud_game_decisions (
 account_id TEXT NOT NULL,event_id TEXT NOT NULL,expected_tips_json TEXT NOT NULL CHECK(json_valid(expected_tips_json)),
 expected_local_json TEXT NOT NULL CHECK(json_valid(expected_local_json)),
 expected_payload_json TEXT NOT NULL CHECK(json_valid(expected_payload_json)),
 PRIMARY KEY(account_id,event_id),FOREIGN KEY(account_id,event_id) REFERENCES cloud_game_events(account_id,event_id)
);
CREATE TABLE cloud_game_blockers (
 account_id TEXT NOT NULL,owner_key TEXT NOT NULL,event_id TEXT NOT NULL DEFAULT '',code TEXT NOT NULL,
 PRIMARY KEY(account_id,owner_key,event_id),
 CHECK(code IN ('game_codec_not_activated','game_dependency_progress_missing','game_dependency_project_action_missing',
 'game_project_authority_unresolved','game_stage_authority_unresolved','game_legacy_extension_unsupported',
 'game_resource_limit','game_noncommutative_conflict','game_reward_duplicate_mismatch','game_parent_unknown',
 'game_exact_replay_mismatch','game_developer_state_restricted','game_unsupported_local_mutation','game_invalid_rule',
 'game_scope_mismatch','invalid_game_payload','decrypt_failed','game_readers_not_ready','game_legacy_local_conflict'))
);
CREATE TABLE cloud_game_write_intents (
 account_id TEXT NOT NULL,event_id TEXT NOT NULL,payload_json TEXT NOT NULL CHECK(json_valid(payload_json)),
 PRIMARY KEY(account_id,event_id),FOREIGN KEY(account_id,event_id) REFERENCES cloud_game_events(account_id,event_id)
);
-- Scheduling evidence only: this is neither a pull cursor nor ACK authority.
CREATE TABLE cloud_game_reader_visits (
 account_id TEXT NOT NULL REFERENCES cloud_sync_state(account_id),event_id TEXT NOT NULL,
 ordinal INTEGER NOT NULL CHECK(ordinal BETWEEN 1 AND 9007199254740991),
 PRIMARY KEY(account_id,event_id)
);
CREATE TRIGGER game_event_immutable BEFORE UPDATE ON cloud_game_events
WHEN NEW.account_id IS NOT OLD.account_id OR NEW.event_id IS NOT OLD.event_id OR NEW.scope IS NOT OLD.scope
 OR NEW.owner_key IS NOT OLD.owner_key OR NEW.project_id IS NOT OLD.project_id OR NEW.stage_id IS NOT OLD.stage_id
 OR NEW.entity_id IS NOT OLD.entity_id OR NEW.canonical_frame IS NOT OLD.canonical_frame OR NEW.parents_json IS NOT OLD.parents_json
 OR NEW.revision IS NOT OLD.revision OR (OLD.nonce IS NOT NULL AND (NEW.nonce IS NOT OLD.nonce OR NEW.ciphertext IS NOT OLD.ciphertext))
 OR (OLD.server_sequence IS NOT NULL AND NEW.server_sequence IS NOT OLD.server_sequence)
 OR (OLD.receipt_sequence IS NOT NULL AND NEW.receipt_sequence IS NOT OLD.receipt_sequence)
 OR (OLD.state IN ('applied','conflict_preserved') AND NEW.state IS NOT OLD.state)
BEGIN SELECT RAISE(ABORT,'immutable game event'); END;
CREATE TRIGGER game_event_retained BEFORE DELETE ON cloud_game_events BEGIN SELECT RAISE(ABORT,'retained game history'); END;
-- Processing counters remain local; a recorded source cannot later be changed
-- into another semantic action while retaining its original reward relation.
CREATE TRIGGER game_domain_source_immutable BEFORE UPDATE OF event_id,event_type,project_id,stage_id,progress_id,delta_symbols,context_json,version ON domain_events
WHEN EXISTS(SELECT 1 FROM cloud_game_sources WHERE source_key=OLD.event_id)
 AND (NEW.event_id IS NOT OLD.event_id OR NEW.event_type IS NOT OLD.event_type
 OR NEW.project_id IS NOT OLD.project_id OR NEW.stage_id IS NOT OLD.stage_id
 OR NEW.progress_id IS NOT OLD.progress_id OR NEW.delta_symbols IS NOT OLD.delta_symbols
 OR NEW.context_json IS NOT OLD.context_json OR NEW.version IS NOT OLD.version)
BEGIN SELECT RAISE(ABORT,'immutable game domain source'); END;
CREATE TRIGGER game_snapshots_immutable BEFORE UPDATE ON cloud_game_snapshots BEGIN SELECT RAISE(ABORT,'immutable game evidence'); END;
CREATE TRIGGER game_snapshots_retained BEFORE DELETE ON cloud_game_snapshots BEGIN SELECT RAISE(ABORT,'retained game evidence'); END;
CREATE TRIGGER game_candidates_immutable BEFORE UPDATE ON cloud_game_candidates BEGIN SELECT RAISE(ABORT,'immutable game evidence'); END;
CREATE TRIGGER game_candidates_retained BEFORE DELETE ON cloud_game_candidates BEGIN SELECT RAISE(ABORT,'retained game evidence'); END;
CREATE TRIGGER game_rewards_immutable BEFORE UPDATE ON cloud_game_rewards BEGIN SELECT RAISE(ABORT,'immutable game evidence'); END;
CREATE TRIGGER game_rewards_retained BEFORE DELETE ON cloud_game_rewards BEGIN SELECT RAISE(ABORT,'retained game evidence'); END;
CREATE TRIGGER game_sources_immutable BEFORE UPDATE ON cloud_game_sources BEGIN SELECT RAISE(ABORT,'immutable game evidence'); END;
CREATE TRIGGER game_sources_retained BEFORE DELETE ON cloud_game_sources BEGIN SELECT RAISE(ABORT,'retained game evidence'); END;
CREATE TRIGGER game_compensations_immutable BEFORE UPDATE ON cloud_game_compensations BEGIN SELECT RAISE(ABORT,'immutable game evidence'); END;
CREATE TRIGGER game_compensations_retained BEFORE DELETE ON cloud_game_compensations BEGIN SELECT RAISE(ABORT,'retained game evidence'); END;
CREATE TRIGGER game_apply_ledger_immutable BEFORE UPDATE ON cloud_game_apply_ledger BEGIN SELECT RAISE(ABORT,'immutable game evidence'); END;
CREATE TRIGGER game_apply_ledger_retained BEFORE DELETE ON cloud_game_apply_ledger BEGIN SELECT RAISE(ABORT,'retained game evidence'); END;
CREATE TRIGGER game_decisions_immutable BEFORE UPDATE ON cloud_game_decisions BEGIN SELECT RAISE(ABORT,'immutable game evidence'); END;
CREATE TRIGGER game_decisions_retained BEFORE DELETE ON cloud_game_decisions BEGIN SELECT RAISE(ABORT,'retained game evidence'); END;
CREATE TRIGGER game_write_intents_immutable BEFORE UPDATE ON cloud_game_write_intents BEGIN SELECT RAISE(ABORT,'immutable game evidence'); END;
CREATE TRIGGER game_write_intents_retained BEFORE DELETE ON cloud_game_write_intents BEGIN SELECT RAISE(ABORT,'retained game evidence'); END;

-- Compatibility writes remain lossless local evidence. They cannot silently
-- overwrite portable authority after either runtime has activated the ledger.
ALTER TABLE cloud_game_write_intents ADD COLUMN prior_payload_json TEXT
 CHECK(prior_payload_json IS NULL OR json_valid(prior_payload_json));
CREATE TABLE cloud_game_local_mutations (
 mutation_id INTEGER PRIMARY KEY,account_id TEXT NOT NULL,
 prior_payload_json TEXT NOT NULL CHECK(json_valid(prior_payload_json)),
 payload_json TEXT NOT NULL CHECK(json_valid(payload_json)),created_at TEXT NOT NULL,
 CHECK(length(CAST(prior_payload_json AS BLOB))<=67108864 AND length(CAST(payload_json AS BLOB))<=67108864)
);
CREATE TABLE cloud_game_local_restrictions (
 code TEXT PRIMARY KEY CHECK(code='game_developer_state_restricted'),
 source_json TEXT NOT NULL CHECK(json_valid(source_json)),created_at TEXT NOT NULL
);
CREATE TRIGGER game_local_mutations_immutable BEFORE UPDATE ON cloud_game_local_mutations BEGIN SELECT RAISE(ABORT,'immutable local game evidence'); END;
CREATE TRIGGER game_local_mutations_retained BEFORE DELETE ON cloud_game_local_mutations BEGIN SELECT RAISE(ABORT,'retained local game evidence'); END;
CREATE TRIGGER game_local_restrictions_immutable BEFORE UPDATE ON cloud_game_local_restrictions BEGIN SELECT RAISE(ABORT,'immutable developer game evidence'); END;
CREATE TRIGGER game_compatibility_write_evidence AFTER UPDATE OF payload_json ON game_state
WHEN EXISTS(SELECT 1 FROM cloud_game_apply_ledger)
 AND (
  json_remove(COALESCE(json_extract(OLD.payload_json,'$.gamer'),'{}'),'$.writing_session','$.last_health_recovery_at') IS NOT
   json_remove(COALESCE(json_extract(NEW.payload_json,'$.gamer'),'{}'),'$.writing_session','$.last_health_recovery_at')
  OR json_extract(OLD.payload_json,'$.global_streak') IS NOT json_extract(NEW.payload_json,'$.global_streak')
  OR json_extract(OLD.payload_json,'$.project_game_state') IS NOT json_extract(NEW.payload_json,'$.project_game_state')
  OR json_remove(COALESCE(json_extract(OLD.payload_json,'$.extensions'),'{}'),'$.progress_deletions','$.lifecycle_events') IS NOT
   json_remove(COALESCE(json_extract(NEW.payload_json,'$.extensions'),'{}'),'$.progress_deletions','$.lifecycle_events')
 )
 AND NOT EXISTS(
  SELECT 1 FROM cloud_sync_remote_apply_authorizations a JOIN cloud_game_events e USING(account_id,event_id)
  WHERE a.entity_id='game_state' AND a.operation='upsert' AND a.payload_json=NEW.payload_json
   AND a.prior_payload_json=OLD.payload_json AND note_sync_remote_apply_authorized(a.capability)
 )
 AND NOT EXISTS(
  SELECT 1 FROM cloud_game_write_intents w JOIN cloud_game_events e USING(account_id,event_id)
   JOIN cloud_game_projection p ON p.account_id=e.account_id AND p.head_event_id=e.event_id
  WHERE w.payload_json=NEW.payload_json AND w.prior_payload_json=OLD.payload_json
 )
BEGIN
 INSERT INTO cloud_game_local_mutations(account_id,prior_payload_json,payload_json,created_at)
 SELECT DISTINCT account_id,OLD.payload_json,NEW.payload_json,NEW.updated_at FROM cloud_game_apply_ledger;
 INSERT INTO cloud_game_blockers(account_id,owner_key,event_id,code)
 SELECT DISTINCT account_id,'account','','game_unsupported_local_mutation' FROM cloud_game_apply_ledger WHERE 1
 ON CONFLICT(account_id,owner_key,event_id) DO NOTHING;
 UPDATE cloud_game_migrations SET lifecycle='blocked',blocker='game_unsupported_local_mutation'
 WHERE account_id IN (SELECT DISTINCT account_id FROM cloud_game_apply_ledger);
END;
CREATE TRIGGER game_compatibility_history_retained BEFORE DELETE ON game_state
WHEN EXISTS(SELECT 1 FROM cloud_game_apply_ledger)
BEGIN SELECT RAISE(ABORT,'game projection deletion requires ledger rebuild'); END;
