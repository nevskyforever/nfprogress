-- Explicit per-project structural migration. Snapshot and identities never mutate.
CREATE TABLE cloud_sync_structural_migrations (
 account_id TEXT NOT NULL, project_id TEXT NOT NULL, migration_id TEXT NOT NULL UNIQUE,
 generation INTEGER NOT NULL CHECK(generation>0),
 manifest_json TEXT NOT NULL CHECK(json_valid(manifest_json)),
 state TEXT NOT NULL CHECK(state IN ('candidate_captured','publication_pending','published_self_echo_pending','active','conflict','blocked')),
 blockers_json TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(blockers_json)),
 created_at TEXT NOT NULL,
 PRIMARY KEY(account_id,project_id,generation),
 FOREIGN KEY(project_id,account_id) REFERENCES cloud_sync_project_bindings(project_id,account_id)
);
CREATE TRIGGER structural_migration_identity_immutable BEFORE UPDATE ON cloud_sync_structural_migrations
WHEN NEW.account_id IS NOT OLD.account_id OR NEW.project_id IS NOT OLD.project_id
 OR NEW.generation IS NOT OLD.generation OR NEW.migration_id IS NOT OLD.migration_id OR NEW.manifest_json IS NOT OLD.manifest_json OR NEW.created_at IS NOT OLD.created_at
BEGIN SELECT RAISE(ABORT,'structural_migration_immutable'); END;
CREATE TRIGGER structural_migration_no_delete BEFORE DELETE ON cloud_sync_structural_migrations
BEGIN SELECT RAISE(ABORT,'structural_migration_immutable'); END;
-- Full-tip decisions preserve their frozen frame and parent list in existing
-- immutable structural_events; version 2 is distinct from ordinary v1 edits.
CREATE TABLE cloud_sync_structural_local_orders (
 account_id TEXT NOT NULL, project_id TEXT NOT NULL, event_id TEXT NOT NULL,
 order_json TEXT NOT NULL CHECK(json_valid(order_json)),
 PRIMARY KEY(account_id,project_id,event_id)
);
CREATE TRIGGER structural_local_order_no_update BEFORE UPDATE ON cloud_sync_structural_local_orders
BEGIN SELECT RAISE(ABORT,'structural_local_order_immutable'); END;
CREATE TRIGGER structural_local_order_no_delete BEFORE DELETE ON cloud_sync_structural_local_orders
BEGIN SELECT RAISE(ABORT,'structural_local_order_immutable'); END;
-- A later Stage creation freezes its companion order intent before commit.
CREATE TABLE cloud_sync_structural_order_intents (
 account_id TEXT NOT NULL, project_id TEXT NOT NULL, stage_event_id TEXT NOT NULL,
 order_event_json TEXT NOT NULL CHECK(json_valid(order_event_json)),
 PRIMARY KEY(account_id,stage_event_id)
);
CREATE TRIGGER structural_order_intent_no_update BEFORE UPDATE ON cloud_sync_structural_order_intents
BEGIN SELECT RAISE(ABORT,'structural_order_intent_immutable'); END;
CREATE TRIGGER structural_order_intent_no_delete BEFORE DELETE ON cloud_sync_structural_order_intents
BEGIN SELECT RAISE(ABORT,'structural_order_intent_immutable'); END;

CREATE TABLE cloud_sync_structural_decisions (
 account_id TEXT NOT NULL, event_id TEXT NOT NULL,
 expected_local_json TEXT NOT NULL CHECK(json_valid(expected_local_json)),
 PRIMARY KEY(account_id,event_id),
 FOREIGN KEY(account_id,event_id) REFERENCES cloud_sync_structural_events(account_id,event_id)
);
CREATE TRIGGER structural_decision_no_update BEFORE UPDATE ON cloud_sync_structural_decisions
BEGIN SELECT RAISE(ABORT,'structural_decision_immutable'); END;
CREATE TRIGGER structural_decision_no_delete BEFORE DELETE ON cloud_sync_structural_decisions
BEGIN SELECT RAISE(ABORT,'structural_decision_immutable'); END;
