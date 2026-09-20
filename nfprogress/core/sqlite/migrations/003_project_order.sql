CREATE TABLE IF NOT EXISTS project_order (
    project_id TEXT PRIMARY KEY,
    position INTEGER NOT NULL UNIQUE CHECK (position >= 0)
);

CREATE INDEX IF NOT EXISTS idx_project_order_position
    ON project_order(position);

-- A newly-created representation has no trustworthy ordering until the
-- pickle-owned Projects domain has been mirrored into it.
UPDATE mirror_state
SET sync_status = 'rebuild_required',
    last_error = 'Project ordering representation requires a mirror rebuild'
WHERE id = 1;
