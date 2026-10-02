-- Account catalog authority is explicit. Transport inbox bytes remain immutable.
CREATE TABLE cloud_catalog_state (
 account_id TEXT PRIMARY KEY REFERENCES cloud_sync_state(account_id),
 state TEXT NOT NULL CHECK(state IN ('captured','publication_pending','self_echo_pending','active','conflict','blocked')),
 snapshot_json TEXT NOT NULL CHECK(json_valid(snapshot_json)),
 local_json TEXT NOT NULL CHECK(json_valid(local_json)),
 blocker TEXT,
 created_at TEXT NOT NULL
);
CREATE TRIGGER catalog_snapshot_immutable BEFORE UPDATE OF snapshot_json,created_at,account_id ON cloud_catalog_state
BEGIN SELECT RAISE(ABORT,'immutable catalog snapshot'); END;
CREATE TABLE cloud_catalog_events (
 account_id TEXT NOT NULL REFERENCES cloud_sync_state(account_id),event_id TEXT NOT NULL,
 entity_type TEXT NOT NULL CHECK(entity_type IN ('folder','folder_order','folder_membership','project_order')),
 entity_id TEXT NOT NULL,canonical_frame BLOB NOT NULL CHECK(length(canonical_frame) BETWEEN 20 AND 4194324),
 state TEXT NOT NULL CHECK(state IN ('unsealed','sealed','accepted','orphan','blocked','applied','conflict_preserved')),
 blocker TEXT,nonce BLOB,ciphertext BLOB,server_sequence INTEGER,receipt_sequence INTEGER,
 PRIMARY KEY(account_id,event_id),UNIQUE(account_id,server_sequence),
 CHECK((nonce IS NULL)=(ciphertext IS NULL)),CHECK(nonce IS NULL OR length(nonce)=24)
);
CREATE TRIGGER catalog_event_immutable BEFORE UPDATE OF account_id,event_id,entity_type,entity_id,canonical_frame ON cloud_catalog_events
BEGIN SELECT RAISE(ABORT,'immutable catalog event'); END;
CREATE TRIGGER catalog_ciphertext_immutable BEFORE UPDATE OF nonce,ciphertext ON cloud_catalog_events
WHEN OLD.nonce IS NOT NULL AND (OLD.nonce IS NOT NEW.nonce OR OLD.ciphertext IS NOT NEW.ciphertext)
BEGIN SELECT RAISE(ABORT,'immutable catalog ciphertext'); END;
CREATE TRIGGER catalog_event_no_delete BEFORE DELETE ON cloud_catalog_events
BEGIN SELECT RAISE(ABORT,'retained catalog history'); END;
CREATE TABLE cloud_catalog_tips (
 account_id TEXT NOT NULL,entity_type TEXT NOT NULL,entity_id TEXT NOT NULL,event_id TEXT NOT NULL,
 PRIMARY KEY(account_id,entity_type,entity_id,event_id),
 FOREIGN KEY(account_id,event_id) REFERENCES cloud_catalog_events(account_id,event_id)
);
CREATE TABLE cloud_catalog_projection (
 account_id TEXT NOT NULL,entity_type TEXT NOT NULL,entity_id TEXT NOT NULL,head_event_id TEXT NOT NULL,
 payload_json TEXT NOT NULL CHECK(json_valid(payload_json)),deleted INTEGER NOT NULL CHECK(deleted IN (0,1)),
 PRIMARY KEY(account_id,entity_type,entity_id),FOREIGN KEY(account_id,head_event_id) REFERENCES cloud_catalog_events(account_id,event_id)
);
CREATE TABLE cloud_catalog_apply_ledger (
 account_id TEXT NOT NULL,event_id TEXT NOT NULL,server_sequence INTEGER NOT NULL,
 canonical_frame BLOB NOT NULL,nonce BLOB NOT NULL,ciphertext BLOB NOT NULL,
 outcome TEXT NOT NULL CHECK(outcome IN ('applied','conflict_preserved')),
 PRIMARY KEY(account_id,event_id),FOREIGN KEY(account_id,event_id) REFERENCES cloud_catalog_events(account_id,event_id)
);
CREATE TRIGGER catalog_ledger_immutable BEFORE UPDATE ON cloud_catalog_apply_ledger
BEGIN SELECT RAISE(ABORT,'immutable catalog proof'); END;
CREATE TRIGGER catalog_ledger_no_delete BEFORE DELETE ON cloud_catalog_apply_ledger
BEGIN SELECT RAISE(ABORT,'retained catalog proof'); END;
CREATE TABLE cloud_catalog_decisions (
 account_id TEXT NOT NULL,event_id TEXT NOT NULL,expected_tips_json TEXT NOT NULL,expected_local_json TEXT NOT NULL,
 PRIMARY KEY(account_id,event_id),FOREIGN KEY(account_id,event_id) REFERENCES cloud_catalog_events(account_id,event_id)
);
CREATE TRIGGER catalog_decision_immutable BEFORE UPDATE ON cloud_catalog_decisions
BEGIN SELECT RAISE(ABORT,'immutable catalog decision'); END;
-- Existing disconnect is local removal, not authenticated remote deletion.
CREATE TRIGGER catalog_binding_removal_guard BEFORE DELETE ON cloud_sync_project_bindings
WHEN EXISTS(SELECT 1 FROM cloud_catalog_state WHERE account_id=OLD.account_id)
BEGIN SELECT RAISE(ABORT,'catalog_disconnect_requires_reconciliation'); END;
CREATE TABLE cloud_catalog_local_conflicts (
 account_id TEXT NOT NULL,entity_type TEXT NOT NULL,entity_id TEXT NOT NULL,
 candidate_json TEXT NOT NULL CHECK(json_valid(candidate_json)),
 PRIMARY KEY(account_id,entity_type,entity_id)
);
CREATE TABLE cloud_catalog_candidates (
 candidate_id TEXT PRIMARY KEY,account_id TEXT NOT NULL,source_json TEXT NOT NULL,
 blocker TEXT,created_at TEXT NOT NULL
);
CREATE TRIGGER catalog_candidate_immutable BEFORE UPDATE ON cloud_catalog_candidates
BEGIN SELECT RAISE(ABORT,'immutable catalog local candidate'); END;
CREATE TRIGGER catalog_candidate_no_delete BEFORE DELETE ON cloud_catalog_candidates
BEGIN SELECT RAISE(ABORT,'retained catalog local candidate'); END;
-- Keep typed reader failures without rewriting the accepted opaque inbox/schema30.
CREATE TABLE cloud_catalog_inbox_blockers (
 account_id TEXT NOT NULL,event_id TEXT NOT NULL,code TEXT NOT NULL,
 PRIMARY KEY(account_id,event_id),
 FOREIGN KEY(account_id,event_id) REFERENCES cloud_sync_account_inbox(account_id,event_id),
 CHECK(code IN ('account_entity_codec_not_activated','decrypt_failed','account_scope_rejected','invalid_catalog_frame','catalog_dependency_missing','catalog_parent_unknown','catalog_membership_changed','catalog_project_unproven','catalog_folder_has_members','catalog_resource_limit','catalog_dependency_conflict','unsupported_catalog_source'))
);
