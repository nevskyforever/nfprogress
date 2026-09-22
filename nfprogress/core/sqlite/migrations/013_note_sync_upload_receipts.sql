-- C15.5B: durable server acceptance for already-sealed Note events.
CREATE TABLE IF NOT EXISTS cloud_sync_upload_receipts (
    account_id TEXT NOT NULL CHECK (length(account_id) BETWEEN 1 AND 512),
    event_id TEXT PRIMARY KEY NOT NULL REFERENCES cloud_sync_outbox(event_id) ON DELETE RESTRICT,
    device_id TEXT NOT NULL CHECK (length(device_id) = 36),
    server_sequence INTEGER NOT NULL CHECK (server_sequence >= 1),
    duplicate INTEGER NOT NULL CHECK (duplicate IN (0, 1)),
    accepted_at TEXT NOT NULL,
    UNIQUE (account_id, server_sequence)
);
CREATE INDEX IF NOT EXISTS idx_cloud_sync_upload_receipts_account
    ON cloud_sync_upload_receipts(account_id, event_id);
