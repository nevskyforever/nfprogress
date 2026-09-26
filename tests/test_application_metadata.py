from __future__ import annotations

import sqlite3

import engine

from nfprogress.core.sqlite.connection import (
    configure_application_metadata,
    open_database,
)
from nfprogress.core.sqlite.schema import CURRENT_SCHEMA_VERSION


def _metadata(connection) -> dict[str, str | None]:
    return dict(connection.execute(
        "SELECT key,value FROM application_metadata "
        "WHERE key IN ('data_created_by_version','data_last_written_by_version')"
    ))


def test_new_database_records_canonical_nfprogress_version(tmp_path):
    with open_database(tmp_path) as database:
        assert database.execute(
            "SELECT schema_version FROM schema_info"
        ).fetchone()[0] == CURRENT_SCHEMA_VERSION
        assert _metadata(database) == {
            "data_created_by_version": engine.version,
            "data_last_written_by_version": engine.version,
        }


def test_created_version_is_immutable_and_last_written_tracks_writer(tmp_path):
    with open_database(tmp_path) as database:
        created = _metadata(database)["data_created_by_version"]
        configure_application_metadata(
            database, application_version="9.8.7-test.1", new_database=False,
        )
        database.execute(
            "INSERT INTO settings(key,value_json) VALUES('theme','\"dark\"')"
        )
        database.commit()
        assert _metadata(database) == {
            "data_created_by_version": created,
            "data_last_written_by_version": "9.8.7-test.1",
        }
        configure_application_metadata(
            database, application_version=engine.version, new_database=False,
        )
        # A version mismatch alone has no compatibility effect and does not
        # rewrite last_written until user data is successfully changed.
        assert _metadata(database)["data_last_written_by_version"] == "9.8.7-test.1"
        database.execute(
            "UPDATE settings SET value_json='\"light\"' WHERE key='theme'"
        )
        database.commit()
        assert _metadata(database) == {
            "data_created_by_version": created,
            "data_last_written_by_version": engine.version,
        }


def test_c9_sync_metadata_writes_track_the_application_version(tmp_path):
    with open_database(tmp_path) as database:
        configure_application_metadata(
            database, application_version="9.8.7-test.1", new_database=False,
        )
        database.execute("""INSERT INTO cloud_sync_state(
            account_id,device_id,pull_cursor,ack_cursor,created_at,updated_at
        ) VALUES('account','123e4567-e89b-42d3-a456-426614174000',0,0,'now','now')""")
        database.commit()
        assert _metadata(database)['data_last_written_by_version'] == '9.8.7-test.1'
        database.execute(
            "INSERT INTO projects(id,name,infinite,unit,status,payload_json) "
            "VALUES('project','Project',0,'symbols','active','{}')"
        )
        database.execute(
            "INSERT INTO project_order(project_id,position) VALUES('project',0)"
        )
        database.execute(
            "INSERT INTO cloud_sync_project_bindings(project_id,account_id,created_at,updated_at) "
            "VALUES('project','account','now','now')"
        )
        database.execute("""INSERT INTO cloud_sync_outbox(
            event_id,account_id,device_id,project_id,entity_id,entity_type,operation,
            revision,updated_at,deleted_at,created_at,local_ordinal,lifecycle
        ) VALUES('123e4567-e89b-42d3-a456-426614174001','account',
            '123e4567-e89b-42d3-a456-426614174000','project','entity','note','upsert',
            1,'now',NULL,'now',1,'unsealed')""")
        database.execute("""INSERT INTO cloud_sync_note_intents(
            event_id,mutation_generation,snapshot_json,seal_state,
            seal_attempt_count,state_updated_at
        ) VALUES('123e4567-e89b-42d3-a456-426614174001',1,
            '{"id":"entity","project_id":"project"}','pending',0,'now')""")
        database.commit()
        assert _metadata(database)['data_last_written_by_version'] == '9.8.7-test.1'


def test_c17_resolution_proof_tables_install_application_version_triggers(tmp_path):
    with open_database(tmp_path) as database:
        trigger_names = {
            row[0]
            for row in database.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger' "
                "AND name LIKE 'nfprogress_app_version_cloud_sync_note_%'"
            )
        }

    for table in (
        'cloud_sync_note_resolution_upload_receipts',
        'cloud_sync_note_applied_resolutions',
        'cloud_sync_note_applied_resolution_parents',
    ):
        for operation in ('insert', 'update', 'delete'):
            assert f'nfprogress_app_version_{table}_{operation}' in trigger_names



def test_existing_v6_database_without_metadata_opens_and_starts_unknown(tmp_path):
    with open_database(tmp_path):
        pass
    path = tmp_path / "nfprogress.db"
    with sqlite3.connect(path) as database:
        database.execute("DROP TRIGGER notes_require_sync_intent_insert")
        database.execute("DROP TRIGGER notes_require_sync_intent_update")
        database.execute("DROP TRIGGER notes_require_sync_intent_delete")
        database.execute("DROP TRIGGER notes_remote_apply_consume_insert")
        database.execute("DROP TRIGGER notes_remote_apply_consume_update")
        database.execute("DROP TRIGGER notes_remote_apply_consume_delete")
        # Migration 021 owns one trigger on the still-existing v1 receipt
        # table, so remove it before deleting its referenced resolution table.
        database.execute("DROP TRIGGER cloud_sync_upload_receipts_resolution_sequence_conflict")
        database.execute("DROP TRIGGER cloud_sync_note_resolution_receipts_v1_sequence_conflict")
        database.execute("DROP TRIGGER cloud_sync_note_resolution_receipt_requires_sealed_object")
        database.execute("DROP TRIGGER cloud_sync_note_resolution_outbox_accepted_requires_receipt")
        database.execute("DROP TRIGGER cloud_sync_note_resolution_receipt_immutable_update")
        database.execute("DROP TRIGGER cloud_sync_note_resolution_receipt_immutable_delete")
        database.execute("DROP TRIGGER cloud_sync_resolution_inbox_immutable_update")
        database.execute("DROP TRIGGER cloud_sync_resolution_inbox_immutable_delete")
        database.execute("DROP TRIGGER cloud_sync_resolution_inbox_object_immutable_update")
        database.execute("DROP TRIGGER cloud_sync_resolution_inbox_object_immutable_delete")
        database.execute("DROP TRIGGER cloud_sync_note_applied_resolution_insert_guard")
        database.execute("DROP TRIGGER cloud_sync_note_applied_resolution_parent_set_guard")
        database.execute("DROP TRIGGER cloud_sync_note_applied_resolution_immutable_update")
        database.execute("DROP TRIGGER cloud_sync_note_applied_resolution_completion_guard")
        database.execute("DROP TRIGGER cloud_sync_note_applied_resolution_immutable_delete")
        database.execute("DROP TRIGGER cloud_sync_upload_receipts_applied_resolution_sequence_conflict")
        database.execute("DROP TRIGGER cloud_sync_note_causal_history_applied_resolution_sequence_conflict")
        database.execute("DROP TRIGGER cloud_sync_note_resolution_receipts_applied_sequence_conflict")
        database.execute("DROP TRIGGER cloud_sync_note_applied_resolution_parent_insert_guard")
        database.execute("DROP TRIGGER cloud_sync_note_applied_resolution_parent_immutable_update")
        database.execute("DROP TRIGGER cloud_sync_note_applied_resolution_parent_immutable_delete")
        database.execute("DROP TRIGGER cloud_sync_resolution_inbox_applied_insert_guard")
        database.execute("DROP TRIGGER cloud_sync_resolution_inbox_applied_update_guard")
        database.execute("DROP TRIGGER cloud_sync_resolution_inbox_applied_is_final")
        database.execute("DROP TRIGGER cloud_sync_note_resolution_block_v1_intent")
        database.execute("DROP TABLE cloud_sync_note_applied_resolution_parents")
        database.execute("DROP TABLE cloud_sync_note_applied_resolutions")
        database.execute("DROP TABLE cloud_sync_note_resolution_upload_receipts")
        database.execute("DROP TABLE cloud_sync_project_bootstraps")
        database.execute("DROP TABLE cloud_account_bindings")
        database.execute("DROP TABLE cloud_sync_note_intent_cursors")
        database.execute("DROP TABLE cloud_sync_note_intents")
        database.execute("DROP TABLE cloud_sync_project_bindings")
        database.execute("DROP TABLE cloud_sync_event_objects")
        database.execute("DROP TABLE cloud_sync_inbox")
        database.execute("DROP TABLE cloud_sync_note_resolution_dependencies")
        database.execute("DROP TABLE cloud_sync_note_resolution_outbox")
        database.execute("DROP TABLE cloud_sync_note_pending_resolutions")
        database.execute("DROP TABLE cloud_sync_note_conflict_tips")
        database.execute("DROP TABLE cloud_sync_note_conflict_versions")
        database.execute("DROP TABLE cloud_sync_note_conflict_groups")
        database.execute("DROP TABLE cloud_sync_note_causal_history")
        database.execute("DROP TABLE cloud_sync_entities")
        database.execute("DROP TABLE cloud_sync_remote_apply_authorizations")
        database.execute("DROP TABLE cloud_sync_upload_receipts")
        database.execute("DROP TABLE cloud_sync_note_upload_cursors")
        database.execute("DROP TABLE cloud_sync_outbox")
        database.execute("DROP TABLE cloud_sync_state")
        database.execute("DROP TABLE application_metadata")
        database.execute("UPDATE schema_info SET schema_version=6")

    with open_database(tmp_path) as database:
        assert _metadata(database) == {
            "data_created_by_version": None,
            "data_last_written_by_version": None,
        }
        database.execute(
            "INSERT INTO settings(key,value_json) VALUES('language','\"ru\"')"
        )
        database.commit()
        assert _metadata(database) == {
            "data_created_by_version": None,
            "data_last_written_by_version": engine.version,
        }


def test_different_valid_saved_version_never_blocks_opening(tmp_path):
    with open_database(tmp_path) as database:
        database.execute(
            "UPDATE application_metadata SET value='99.0.0' "
            "WHERE key='data_last_written_by_version'"
        )
        database.commit()

    with open_database(tmp_path) as database:
        assert _metadata(database)["data_last_written_by_version"] == "99.0.0"
        database.execute(
            "INSERT INTO settings(key,value_json) VALUES('language','\"en\"')"
        )
        database.commit()
        assert _metadata(database)["data_last_written_by_version"] == engine.version
