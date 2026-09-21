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
        database.execute("""INSERT INTO cloud_sync_outbox(
            event_id,account_id,device_id,project_id,entity_id,entity_type,operation,
            revision,updated_at,deleted_at,created_at
        ) VALUES('123e4567-e89b-42d3-a456-426614174001','account',
            '123e4567-e89b-42d3-a456-426614174000','project','entity','note','upsert',
            1,'now',NULL,'now')""")
        database.commit()
        assert _metadata(database)['data_last_written_by_version'] == '9.8.7-test.1'



def test_existing_v6_database_without_metadata_opens_and_starts_unknown(tmp_path):
    with open_database(tmp_path):
        pass
    path = tmp_path / "nfprogress.db"
    with sqlite3.connect(path) as database:
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
