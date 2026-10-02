-- C18.4.04: opaque account history only. No catalog writers or apply proof.
CREATE TABLE cloud_sync_account_inbox (
    account_id TEXT NOT NULL REFERENCES cloud_sync_state(account_id),
    event_id TEXT NOT NULL CHECK(length(event_id)=36),
    canonical_user_id TEXT NOT NULL CHECK(length(canonical_user_id)=36),
    scope TEXT NOT NULL CHECK(scope='account'),
    server_sequence INTEGER NOT NULL CHECK(server_sequence BETWEEN 1 AND 9007199254740991),
    device_id TEXT NOT NULL CHECK(length(device_id)=36),
    entity_id TEXT NOT NULL CHECK(length(CAST(entity_id AS BLOB)) BETWEEN 1 AND 512),
    entity_type TEXT NOT NULL CHECK(entity_type IN ('folder','folder_order','folder_membership','project_order')),
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
