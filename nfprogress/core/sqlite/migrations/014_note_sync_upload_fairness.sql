-- C15.5C: one durable cursor per local account prevents a busy device from
-- monopolising bounded sealed-upload reads after restart.
CREATE TABLE cloud_sync_note_upload_cursors (
    account_id TEXT PRIMARY KEY NOT NULL CHECK (length(account_id) BETWEEN 1 AND 512),
    device_id TEXT CHECK (device_id IS NULL OR length(device_id) = 36),
    updated_at TEXT NOT NULL
);
