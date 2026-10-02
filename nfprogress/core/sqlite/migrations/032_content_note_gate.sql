-- One additional frame/dependency receipt; C15/C17 remain the Note history engine.
CREATE TABLE cloud_content_note_receipts (
 account_id TEXT NOT NULL,event_id TEXT NOT NULL,server_sequence INTEGER NOT NULL,
 canonical_frame BLOB,nonce BLOB NOT NULL CHECK(length(nonce)=24),ciphertext BLOB NOT NULL,
 outcome TEXT NOT NULL CHECK(outcome IN ('waiting','applied','conflict_preserved')),
 blocker TEXT,PRIMARY KEY(account_id,event_id),UNIQUE(account_id,server_sequence),
 FOREIGN KEY(account_id,event_id) REFERENCES cloud_sync_inbox(account_id,event_id),
 CHECK(canonical_frame IS NULL OR length(canonical_frame)<=8388608)
);
CREATE TRIGGER content_note_receipt_immutable BEFORE UPDATE OF account_id,event_id,server_sequence,nonce,ciphertext ON cloud_content_note_receipts
BEGIN SELECT RAISE(ABORT,'immutable content Note receipt'); END;
CREATE TRIGGER content_note_frame_immutable BEFORE UPDATE OF canonical_frame ON cloud_content_note_receipts
WHEN OLD.canonical_frame IS NOT NULL AND OLD.canonical_frame IS NOT NEW.canonical_frame
BEGIN SELECT RAISE(ABORT,'immutable content Note frame'); END;
CREATE TRIGGER content_note_receipt_no_delete BEFORE DELETE ON cloud_content_note_receipts
BEGIN SELECT RAISE(ABORT,'retained content Note proof'); END;

CREATE TRIGGER content_note_outcome_final BEFORE UPDATE OF outcome,blocker ON cloud_content_note_receipts
WHEN OLD.outcome IN ('applied','conflict_preserved') AND (NEW.outcome!=OLD.outcome OR NEW.blocker IS NOT NULL)
BEGIN SELECT RAISE(ABORT,'final content Note outcome'); END;

-- Preserve C17 guards; extend only exact retained framed Note proofs.
DROP TRIGGER cloud_sync_note_applied_resolution_insert_guard;
CREATE TRIGGER cloud_sync_note_applied_resolution_insert_guard
BEFORE INSERT ON cloud_sync_note_applied_resolutions
WHEN NEW.lifecycle != 'applying'
  OR NEW.applied_at IS NOT NULL
  OR NOT EXISTS(
      SELECT 1
      FROM cloud_sync_inbox AS inbox
      JOIN cloud_sync_event_objects AS object
        ON object.account_id = inbox.account_id AND object.event_id = inbox.event_id
      WHERE inbox.account_id = NEW.account_id
        AND inbox.event_id = NEW.resolution_event_id
        AND inbox.server_sequence = NEW.server_sequence
        AND inbox.device_id = NEW.source_device_id
        AND inbox.project_id = NEW.project_id
        AND inbox.entity_id = NEW.entity_id
        AND inbox.entity_type = 'note'
        AND (inbox.operation = 'resolution' OR (inbox.operation='event' AND EXISTS(SELECT 1 FROM cloud_content_note_receipts r WHERE r.account_id=inbox.account_id AND r.event_id=inbox.event_id AND r.server_sequence=inbox.server_sequence AND r.nonce=object.nonce AND r.ciphertext=object.ciphertext AND json_extract(CAST(substr(r.canonical_frame,21) AS TEXT),'$.event.version')=2)))
        AND inbox.sync_revision = NEW.revision
        AND inbox.updated_at = NEW.event_updated_at
        AND inbox.deleted_at IS NULL
        AND inbox.state IN ('received', 'orphan')
  )
  OR NOT EXISTS(
      SELECT 1 FROM cloud_sync_note_conflict_groups AS conflict_group
      WHERE conflict_group.group_id = NEW.local_conflict_group_id
        AND conflict_group.account_id = NEW.account_id
        AND conflict_group.project_id = NEW.project_id
        AND conflict_group.entity_id = NEW.entity_id
        AND conflict_group.entity_type = 'note'
        AND conflict_group.generation = NEW.local_conflict_generation
        AND conflict_group.lifecycle IN ('open', 'resolving')
  )
  OR EXISTS(
      SELECT 1 FROM cloud_sync_note_causal_history AS history
      WHERE history.account_id = NEW.account_id
        AND history.server_sequence = NEW.server_sequence
  )
  OR EXISTS(
      SELECT 1 FROM cloud_sync_upload_receipts AS receipt
      WHERE receipt.account_id = NEW.account_id
        AND receipt.server_sequence = NEW.server_sequence
  )
  OR EXISTS(
      SELECT 1 FROM cloud_sync_note_resolution_upload_receipts AS receipt
      WHERE receipt.account_id = NEW.account_id
        AND receipt.resolution_event_id = NEW.resolution_event_id
        AND receipt.server_sequence != NEW.server_sequence
  )
  OR EXISTS(
      SELECT 1 FROM cloud_sync_note_resolution_upload_receipts AS receipt
      WHERE receipt.account_id = NEW.account_id
        AND receipt.server_sequence = NEW.server_sequence
        AND receipt.resolution_event_id != NEW.resolution_event_id
  )
BEGIN SELECT RAISE(ABORT, 'note_applied_resolution_proof_invalid'); END;

DROP TRIGGER cloud_sync_note_applied_resolution_parent_insert_guard;
CREATE TRIGGER cloud_sync_note_applied_resolution_parent_insert_guard
BEFORE INSERT ON cloud_sync_note_applied_resolution_parents
WHEN NOT EXISTS(
    SELECT 1
    FROM cloud_sync_note_applied_resolutions AS resolution
    JOIN cloud_sync_note_conflict_groups AS conflict_group
      ON conflict_group.group_id = resolution.local_conflict_group_id
     AND conflict_group.account_id = resolution.account_id
     AND conflict_group.project_id = resolution.project_id
     AND conflict_group.entity_id = resolution.entity_id
     AND conflict_group.entity_type = 'note'
     AND conflict_group.generation = resolution.local_conflict_generation
     AND conflict_group.lifecycle IN ('open', 'resolving')
    JOIN cloud_sync_note_conflict_versions AS version
      ON version.version_id = NEW.conflict_version_id
     AND version.group_id = resolution.local_conflict_group_id
     AND version.account_id = resolution.account_id
     AND version.project_id = resolution.project_id
     AND version.entity_id = resolution.entity_id
     AND version.entity_type = 'note'
     AND version.event_id = NEW.parent_event_id
     AND version.revision = NEW.parent_revision
     AND version.operation = NEW.parent_operation
     AND version.snapshot_json = NEW.parent_snapshot_json
     AND version.parent_event_id = conflict_group.common_parent_event_id
    JOIN cloud_sync_note_conflict_tips AS tip
      ON tip.group_id = resolution.local_conflict_group_id
     AND tip.version_id = version.version_id
     AND tip.event_id = NEW.parent_event_id
    WHERE resolution.account_id = NEW.account_id
      AND resolution.resolution_event_id = NEW.resolution_event_id
      AND resolution.lifecycle = 'applying'
      AND NEW.parent_ordinal < resolution.parent_count
      AND json_extract(
          resolution.parent_event_ids_json,
          '$[' || NEW.parent_ordinal || ']'
      ) = NEW.parent_event_id
      AND (
          (NEW.publication_source = 'remote'
           AND version.source = 'remote'
           AND version.server_sequence = NEW.server_sequence
           AND EXISTS(
               SELECT 1 FROM cloud_sync_inbox AS inbox
               WHERE inbox.account_id = NEW.account_id
                 AND inbox.event_id = NEW.parent_event_id
                 AND inbox.server_sequence = NEW.server_sequence
                 AND inbox.project_id = resolution.project_id
                 AND inbox.entity_id = resolution.entity_id
                 AND inbox.entity_type = 'note'
                 AND (inbox.operation = NEW.parent_operation OR (inbox.operation='event' AND EXISTS(SELECT 1 FROM cloud_content_note_receipts r WHERE r.account_id=inbox.account_id AND r.event_id=inbox.event_id AND r.server_sequence=inbox.server_sequence AND r.outcome='conflict_preserved' AND json_extract(CAST(substr(r.canonical_frame,21) AS TEXT),'$.event.header.operation')=NEW.parent_operation)))
                 AND inbox.sync_revision = NEW.parent_revision
                 AND inbox.state = 'conflict_preserved'
                 AND inbox.conflict_group_id = resolution.local_conflict_group_id
           ))
          OR
          (NEW.publication_source = 'remote_applied'
           AND version.source = 'remote_applied'
           AND version.server_sequence = NEW.server_sequence
           AND EXISTS(
               SELECT 1 FROM cloud_sync_note_causal_history AS history
               WHERE history.account_id = NEW.account_id
                 AND history.event_id = NEW.parent_event_id
                 AND history.server_sequence = NEW.server_sequence
                 AND history.project_id = resolution.project_id
                 AND history.entity_id = resolution.entity_id
                 AND history.entity_type = 'note'
                 AND history.revision = NEW.parent_revision
                 AND history.operation = NEW.parent_operation
                 AND history.snapshot_json = NEW.parent_snapshot_json
           ))
          OR
          (NEW.publication_source = 'local_accepted'
           AND version.source = 'local_unsealed'
           AND version.local_mutation_generation = NEW.local_mutation_generation
           AND EXISTS(
               SELECT 1
               FROM cloud_sync_outbox AS outbox
               JOIN cloud_sync_upload_receipts AS receipt
                 ON receipt.account_id = outbox.account_id
                AND receipt.event_id = outbox.event_id
               WHERE outbox.account_id = NEW.account_id
                 AND outbox.event_id = NEW.parent_event_id
                 AND outbox.project_id = resolution.project_id
                 AND outbox.entity_id = resolution.entity_id
                 AND outbox.entity_type = 'note'
                 AND outbox.operation = NEW.parent_operation
                 AND outbox.revision = NEW.parent_revision
                 AND outbox.lifecycle = 'accepted'
                 AND receipt.device_id = outbox.device_id
                 AND receipt.server_sequence = NEW.server_sequence
           ))
      )
)
BEGIN SELECT RAISE(ABORT, 'note_applied_resolution_parent_proof_invalid'); END;
