-- C17 D2B0B: conflict tip/version generations record when immutable evidence
-- was discovered. They are not rewritten when the conflict group's current
-- CAS generation advances. Applied-resolution proof must therefore match the
-- complete tip membership while independently CAS-checking the group.

DROP TRIGGER cloud_sync_note_applied_resolution_parent_insert_guard;
DROP TRIGGER cloud_sync_note_applied_resolution_completion_guard;

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
                 AND inbox.operation = NEW.parent_operation
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

CREATE TRIGGER cloud_sync_note_applied_resolution_completion_guard
BEFORE UPDATE OF lifecycle ON cloud_sync_note_applied_resolutions
WHEN NEW.lifecycle = 'applied' AND (
    NOT EXISTS(
        SELECT 1 FROM cloud_sync_note_conflict_groups AS conflict_group
        WHERE conflict_group.group_id = NEW.local_conflict_group_id
          AND conflict_group.account_id = NEW.account_id
          AND conflict_group.project_id = NEW.project_id
          AND conflict_group.entity_id = NEW.entity_id
          AND conflict_group.entity_type = 'note'
          AND conflict_group.generation = NEW.local_conflict_generation
          AND conflict_group.lifecycle IN ('open', 'resolving')
    )
    OR NEW.revision != (
        SELECT max(parent.parent_revision) + 1
        FROM cloud_sync_note_applied_resolution_parents AS parent
        WHERE parent.account_id = NEW.account_id
          AND parent.resolution_event_id = NEW.resolution_event_id
    )
    OR
    (SELECT count(*)
     FROM cloud_sync_note_applied_resolution_parents AS parent
     WHERE parent.account_id = NEW.account_id
       AND parent.resolution_event_id = NEW.resolution_event_id) != NEW.parent_count
    OR EXISTS(
        SELECT 1 FROM json_each(NEW.parent_event_ids_json) AS expected
        LEFT JOIN cloud_sync_note_applied_resolution_parents AS parent
          ON parent.account_id = NEW.account_id
         AND parent.resolution_event_id = NEW.resolution_event_id
         AND parent.parent_ordinal = CAST(expected.key AS INTEGER)
         AND parent.parent_event_id = expected.value
        WHERE parent.parent_event_id IS NULL
    )
    OR (SELECT count(*)
        FROM cloud_sync_note_conflict_tips AS tip
        WHERE tip.group_id = NEW.local_conflict_group_id) != NEW.parent_count
    OR EXISTS(
        SELECT 1 FROM json_each(NEW.parent_event_ids_json) AS expected
        LEFT JOIN cloud_sync_note_applied_resolution_parents AS parent
          ON parent.account_id = NEW.account_id
         AND parent.resolution_event_id = NEW.resolution_event_id
         AND parent.parent_ordinal = CAST(expected.key AS INTEGER)
         AND parent.parent_event_id = expected.value
        LEFT JOIN cloud_sync_note_conflict_tips AS tip
          ON tip.group_id = NEW.local_conflict_group_id
         AND tip.event_id = expected.value
         AND tip.version_id = parent.conflict_version_id
        WHERE parent.parent_event_id IS NULL OR tip.event_id IS NULL
    )
)
BEGIN SELECT RAISE(ABORT, 'note_applied_resolution_parent_proof_incomplete'); END;
