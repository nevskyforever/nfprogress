-- Local support only: neither cover material nor transfer status is a sync entity.
CREATE TABLE cloud_cover_intents (
 account_id TEXT NOT NULL REFERENCES cloud_sync_state(account_id),
 intent_id TEXT NOT NULL PRIMARY KEY,
 project_id TEXT NOT NULL REFERENCES projects(id),
 device_id TEXT NOT NULL,
 source_json TEXT NOT NULL CHECK(json_valid(source_json)),
 metadata_json TEXT NOT NULL CHECK(json_valid(metadata_json)),
 parents_json TEXT NOT NULL CHECK(json_valid(parents_json)),
 source_cover TEXT,
 blob_id TEXT,
 reference_json TEXT CHECK(reference_json IS NULL OR json_valid(reference_json)),
 nonce BLOB,
 ciphertext BLOB,
 state TEXT NOT NULL CHECK(state IN ('captured','sealed','uploaded','metadata_pending','active','blocked')),
 event_id TEXT REFERENCES cloud_sync_metadata_events(event_id),
 blocker TEXT,
 created_at TEXT NOT NULL
);
CREATE UNIQUE INDEX idx_cover_pending ON cloud_cover_intents(account_id,project_id)
 WHERE state NOT IN ('active');
CREATE TRIGGER cover_intent_source_immutable BEFORE UPDATE ON cloud_cover_intents
 WHEN NEW.account_id IS NOT OLD.account_id OR NEW.intent_id IS NOT OLD.intent_id
 OR NEW.project_id IS NOT OLD.project_id OR NEW.device_id IS NOT OLD.device_id
 OR NEW.source_json IS NOT OLD.source_json OR NEW.metadata_json IS NOT OLD.metadata_json
 OR NEW.parents_json IS NOT OLD.parents_json OR NEW.source_cover IS NOT OLD.source_cover
 OR NEW.created_at IS NOT OLD.created_at
 BEGIN SELECT RAISE(ABORT,'immutable cover candidate'); END;
CREATE TRIGGER cover_intent_sealed_immutable BEFORE UPDATE ON cloud_cover_intents
 WHEN OLD.nonce IS NOT NULL AND (NEW.nonce IS NOT OLD.nonce OR NEW.ciphertext IS NOT OLD.ciphertext
 OR NEW.blob_id IS NOT OLD.blob_id OR NEW.reference_json IS NOT OLD.reference_json)
 BEGIN SELECT RAISE(ABORT,'immutable sealed cover'); END;
CREATE TABLE cloud_cover_material (
 account_id TEXT NOT NULL REFERENCES cloud_sync_state(account_id),
 project_id TEXT NOT NULL,
 blob_id TEXT NOT NULL,
 reference_json TEXT NOT NULL CHECK(json_valid(reference_json)),
 nonce BLOB NOT NULL CHECK(length(nonce)=24),
 ciphertext BLOB NOT NULL CHECK(length(ciphertext) BETWEEN 20 AND 2097168),
 jpeg BLOB NOT NULL CHECK(length(jpeg) BETWEEN 4 AND 2097152),
 remote_verified INTEGER NOT NULL CHECK(remote_verified IN (0,1)),
 PRIMARY KEY(account_id,project_id,blob_id)
);
CREATE TRIGGER cover_material_immutable BEFORE UPDATE ON cloud_cover_material
 WHEN NEW.account_id IS NOT OLD.account_id OR NEW.project_id IS NOT OLD.project_id
 OR NEW.blob_id IS NOT OLD.blob_id OR NEW.reference_json IS NOT OLD.reference_json
 OR NEW.nonce IS NOT OLD.nonce OR NEW.ciphertext IS NOT OLD.ciphertext
 OR NEW.jpeg IS NOT OLD.jpeg OR NEW.remote_verified < OLD.remote_verified
 BEGIN SELECT RAISE(ABORT,'immutable verified cover material'); END;
CREATE TRIGGER cover_material_retained BEFORE DELETE ON cloud_cover_material
 BEGIN SELECT RAISE(ABORT,'cover material retained'); END;
CREATE TABLE cloud_cover_blockers (
 account_id TEXT NOT NULL,
 event_id TEXT NOT NULL,
 project_id TEXT NOT NULL,
 reference_json TEXT NOT NULL CHECK(json_valid(reference_json)),
 code TEXT NOT NULL CHECK(code IN ('cover_blob_missing','cover_blob_invalid')),
 PRIMARY KEY(account_id,event_id),
 FOREIGN KEY(account_id,event_id) REFERENCES cloud_sync_inbox(account_id,event_id)
);
