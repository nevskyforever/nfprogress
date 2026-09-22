-- C15.4D2A explicitly binds an opaque local account scope to the canonical
-- backend user UUID obtained from an authenticated normal-user session.
CREATE TABLE cloud_account_bindings (
    local_account_id TEXT PRIMARY KEY NOT NULL
        REFERENCES cloud_sync_state(account_id) ON DELETE CASCADE,
    canonical_user_id TEXT NOT NULL UNIQUE CHECK (
        length(canonical_user_id) = 36
        AND canonical_user_id = lower(canonical_user_id)
        AND length(replace(canonical_user_id, '-', '')) = 32
        AND substr(canonical_user_id, 9, 1) = '-'
        AND substr(canonical_user_id, 14, 1) = '-'
        AND substr(canonical_user_id, 19, 1) = '-'
        AND substr(canonical_user_id, 24, 1) = '-'
        AND canonical_user_id NOT GLOB '*[^0-9a-f-]*'
    ),
    created_at TEXT NOT NULL,
    validated_at TEXT NOT NULL
);

CREATE TRIGGER cloud_account_bindings_identity_immutable
BEFORE UPDATE OF local_account_id, canonical_user_id ON cloud_account_bindings
WHEN NEW.local_account_id IS NOT OLD.local_account_id
  OR NEW.canonical_user_id IS NOT OLD.canonical_user_id
BEGIN
    SELECT RAISE(ABORT, 'cloud_account_binding_identity_is_immutable');
END;
