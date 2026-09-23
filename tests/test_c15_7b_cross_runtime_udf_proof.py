"""Real-SQLite proof for the cross-runtime fail-closed authorization UDF."""

from __future__ import annotations

import sqlite3

import pytest

from nfprogress.core.sqlite.connection import register_remote_apply_authorization_guard


def _install_guard_schema(connection: sqlite3.Connection) -> None:
    connection.executescript('''
        CREATE TABLE notes(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
        CREATE TABLE local_intents(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
        CREATE TABLE remote_authorizations(capability TEXT PRIMARY KEY, id TEXT NOT NULL, payload TEXT NOT NULL);
        CREATE TRIGGER notes_guard_insert BEFORE INSERT ON notes WHEN NOT CASE
          WHEN EXISTS(SELECT 1 FROM local_intents i WHERE i.id=NEW.id AND i.payload=NEW.payload) THEN 1
          WHEN EXISTS(SELECT 1 FROM remote_authorizations a WHERE a.id=NEW.id AND a.payload=NEW.payload
            AND note_sync_remote_apply_authorized(a.capability)) THEN 1
          ELSE 0 END
        BEGIN SELECT RAISE(ABORT, 'bound_note_mutation_requires_matching_sync_intent'); END;
        CREATE TRIGGER notes_guard_update BEFORE UPDATE ON notes WHEN NOT CASE
          WHEN EXISTS(SELECT 1 FROM local_intents i WHERE i.id=NEW.id AND i.payload=NEW.payload) THEN 1
          WHEN EXISTS(SELECT 1 FROM remote_authorizations a WHERE a.id=NEW.id AND a.payload=NEW.payload
            AND note_sync_remote_apply_authorized(a.capability)) THEN 1
          ELSE 0 END
        BEGIN SELECT RAISE(ABORT, 'bound_note_mutation_requires_matching_sync_intent'); END;
        CREATE TRIGGER notes_guard_delete BEFORE DELETE ON notes WHEN NOT CASE
          WHEN EXISTS(SELECT 1 FROM local_intents i WHERE i.id=OLD.id AND i.payload=OLD.payload) THEN 1
          WHEN EXISTS(SELECT 1 FROM remote_authorizations a WHERE a.id=OLD.id AND a.payload=OLD.payload
            AND note_sync_remote_apply_authorized(a.capability)) THEN 1
          ELSE 0 END
        BEGIN SELECT RAISE(ABORT, 'bound_note_mutation_requires_matching_sync_intent'); END;
    ''')


def test_python_fail_closed_guard_keeps_local_intents_and_rejects_authorizations(tmp_path) -> None:
    database = tmp_path / 'cross-runtime-proof.sqlite'
    connection = sqlite3.connect(database)
    register_remote_apply_authorization_guard(connection)
    assert connection.execute('PRAGMA trusted_schema').fetchone()[0] == 1
    _install_guard_schema(connection)
    connection.execute("INSERT INTO local_intents VALUES ('n', 'one')")
    connection.execute("INSERT INTO notes VALUES ('n', 'one')")
    connection.execute("DELETE FROM local_intents")
    connection.execute("INSERT INTO local_intents VALUES ('n', 'two')")
    connection.execute("UPDATE notes SET payload='two' WHERE id='n'")
    connection.execute("DELETE FROM local_intents")
    connection.execute("INSERT INTO local_intents VALUES ('n', 'two')")
    connection.execute("DELETE FROM notes WHERE id='n'")
    connection.execute("DELETE FROM local_intents")
    connection.execute("INSERT INTO remote_authorizations VALUES ('pretend', 'n', 'remote')")
    with pytest.raises(sqlite3.IntegrityError, match='bound_note'):
        connection.execute("INSERT INTO notes VALUES ('n', 'remote')")
    connection.close()


def test_missing_udf_fails_closed_when_preparing_protected_write(tmp_path) -> None:
    database = tmp_path / 'cross-runtime-external.sqlite'
    first = sqlite3.connect(database)
    register_remote_apply_authorization_guard(first)
    _install_guard_schema(first)
    first.commit()
    first.close()
    external = sqlite3.connect(database)
    with pytest.raises(sqlite3.OperationalError, match='no such function'):
        external.execute("INSERT INTO notes VALUES ('n', 'x')")
