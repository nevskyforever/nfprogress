-- Application-version metadata is independent from schema_info. It records
-- which nfprogress version created or most recently wrote user data without
-- imposing any compatibility policy.
CREATE TABLE IF NOT EXISTS application_metadata (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TEXT NOT NULL
);
