-- C15.4D1B durable cursors make bounded Note intent listing a round-robin
-- traversal. cloud_sync_outbox remains the only event queue; these two rows
-- only remember where each explicit listing mode stopped.
CREATE TABLE cloud_sync_note_intent_cursors (
    mode TEXT PRIMARY KEY NOT NULL CHECK (mode IN ('regular', 'retry_blocked')),
    account_id TEXT CHECK (
        account_id IS NULL OR length(account_id) BETWEEN 1 AND 512
    ),
    device_id TEXT CHECK (device_id IS NULL OR length(device_id) = 36),
    local_ordinal INTEGER CHECK (local_ordinal IS NULL OR local_ordinal > 0),
    event_id TEXT CHECK (event_id IS NULL OR (
        length(event_id) = 36
        AND length(replace(event_id, '-', '')) = 32
        AND substr(event_id, 9, 1) = '-'
        AND substr(event_id, 14, 1) = '-'
        AND substr(event_id, 19, 1) = '-'
        AND substr(event_id, 24, 1) = '-'
        AND event_id NOT GLOB '*[^0-9A-Fa-f-]*'
    )),
    updated_at TEXT NOT NULL,
    CHECK (
        (account_id IS NULL AND device_id IS NULL
            AND local_ordinal IS NULL AND event_id IS NULL)
        OR
        (account_id IS NOT NULL AND device_id IS NOT NULL
            AND local_ordinal IS NOT NULL AND event_id IS NOT NULL)
    )
);

INSERT INTO cloud_sync_note_intent_cursors(
    mode,account_id,device_id,local_ordinal,event_id,updated_at
) VALUES
    ('regular',NULL,NULL,NULL,NULL,strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    ('retry_blocked',NULL,NULL,NULL,NULL,strftime('%Y-%m-%dT%H:%M:%fZ','now'));
