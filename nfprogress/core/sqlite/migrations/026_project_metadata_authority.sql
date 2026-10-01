-- Visible C16 shell authority is separate from the authenticated metadata projection.
-- An explicit initial reconciliation authorizes later authenticated causal descendants.
CREATE TABLE cloud_sync_metadata_reconciliation (
    account_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    head_event_id TEXT NOT NULL,
    portable_json TEXT NOT NULL CHECK (json_valid(portable_json) AND json_type(portable_json) = 'object'),
    reconciled_at TEXT NOT NULL,
    PRIMARY KEY (account_id, project_id),
    FOREIGN KEY (account_id, head_event_id) REFERENCES cloud_sync_metadata_events(account_id, event_id) ON DELETE RESTRICT,
    FOREIGN KEY (project_id, account_id) REFERENCES cloud_sync_project_bindings(project_id, account_id)
);
CREATE TABLE cloud_sync_metadata_decisions (
    account_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('keep_local', 'manual', 'edit', 'choose_branch', 'resolve_manual')),
    source_json TEXT NOT NULL CHECK (json_valid(source_json) AND json_type(source_json) = 'object'),
    proposed_json TEXT NOT NULL CHECK (json_valid(proposed_json) AND json_type(proposed_json) = 'object'),
    expected_tips_json TEXT NOT NULL CHECK (json_valid(expected_tips_json) AND json_type(expected_tips_json) = 'array'),
    state TEXT NOT NULL CHECK (state IN ('pending', 'applied', 'conflict')),
    created_at TEXT NOT NULL,
    PRIMARY KEY (account_id, event_id),
    FOREIGN KEY (account_id, event_id) REFERENCES cloud_sync_metadata_events(account_id, event_id) ON DELETE RESTRICT,
    FOREIGN KEY (project_id, account_id) REFERENCES cloud_sync_project_bindings(project_id, account_id)
);
CREATE INDEX idx_cloud_sync_metadata_decisions_project
    ON cloud_sync_metadata_decisions(account_id, project_id, state);

CREATE TRIGGER cloud_sync_metadata_decision_identity_immutable
BEFORE UPDATE ON cloud_sync_metadata_decisions
WHEN NEW.account_id IS NOT OLD.account_id OR NEW.project_id IS NOT OLD.project_id
  OR NEW.event_id IS NOT OLD.event_id OR NEW.kind IS NOT OLD.kind
  OR NEW.source_json IS NOT OLD.source_json OR NEW.proposed_json IS NOT OLD.proposed_json
  OR NEW.expected_tips_json IS NOT OLD.expected_tips_json OR NEW.created_at IS NOT OLD.created_at
BEGIN SELECT RAISE(ABORT, 'immutable metadata decision'); END;
CREATE TRIGGER cloud_sync_metadata_reconciliation_insert_guard
BEFORE INSERT ON cloud_sync_metadata_reconciliation
WHEN NOT EXISTS (
  SELECT 1 FROM cloud_sync_metadata_events event
  WHERE event.account_id=NEW.account_id AND event.project_id=NEW.project_id
    AND event.event_id=NEW.head_event_id AND event.state='applied'
    AND event.payload_json=NEW.portable_json
)
BEGIN SELECT RAISE(ABORT, 'metadata reconciliation requires authenticated apply proof'); END;
CREATE TRIGGER cloud_sync_metadata_reconciliation_update_guard
BEFORE UPDATE ON cloud_sync_metadata_reconciliation
WHEN NOT EXISTS (
  SELECT 1 FROM cloud_sync_metadata_events event
  WHERE event.account_id=NEW.account_id AND event.project_id=NEW.project_id
    AND event.event_id=NEW.head_event_id AND event.state='applied'
    AND event.payload_json=NEW.portable_json
)
BEGIN SELECT RAISE(ABORT, 'metadata reconciliation requires authenticated apply proof'); END;
