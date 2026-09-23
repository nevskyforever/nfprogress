"""SQLite connection helpers for the shadow mirror."""

from __future__ import annotations

import sqlite3
from pathlib import Path
import re

from nfprogress.core.sqlite.schema import apply_migrations


_APPLICATION_VERSION = re.compile(
    r'^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$',
)
_VERSION_KEYS = ('data_created_by_version', 'data_last_written_by_version')
_USER_DATA_TABLES = (
    'projects', 'stages', 'progress_entries', 'notes', 'settings', 'game_state',
    'project_order', 'stage_order', 'progress_order', 'project_metadata',
    'project_folders', 'project_folder_members', 'project_bindings',
    'project_extensions', 'documents', 'document_bindings', 'cloud_sync_state',
    'cloud_sync_outbox', 'cloud_sync_event_objects', 'cloud_sync_inbox',
    'cloud_sync_entities', 'cloud_sync_project_bindings',
    'cloud_sync_note_intents', 'cloud_sync_note_intent_cursors',
    'cloud_account_bindings',
)


def register_remote_apply_authorization_guard(connection: sqlite3.Connection) -> None:
    """Install the fail-closed half of the cross-runtime Notes guard.

    SQLite resolves functions named by persistent triggers while preparing a
    statement.  Python never applies remote events, so its implementation can
    only deny an authorization capability.
    """
    connection.create_function('note_sync_remote_apply_authorized', 1, lambda _value: 0)


def current_application_version() -> str:
    # engine.version remains the canonical Python source; build tooling keeps
    # Cargo/Tauri package metadata synchronized with the same value.
    from engine import version

    value = str(version)
    if not _APPLICATION_VERSION.fullmatch(value):
        raise RuntimeError(f'invalid nfprogress application version: {value!r}')
    return value


def _quoted_sql(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def configure_application_metadata(
    connection: sqlite3.Connection,
    *,
    application_version: str,
    new_database: bool,
) -> None:
    """Initialize version rows and install writer-version triggers.

    Version mismatch is deliberately informational: existing valid values are
    read and validated but never used to block opening or writing.
    """
    if not _APPLICATION_VERSION.fullmatch(application_version):
        raise RuntimeError(
            f'invalid nfprogress application version: {application_version!r}',
        )
    rows = dict(connection.execute(
        'SELECT key,value FROM application_metadata WHERE key IN (?,?)',
        _VERSION_KEYS,
    ))
    for key, value in rows.items():
        if value is not None and not _APPLICATION_VERSION.fullmatch(value):
            raise RuntimeError(f'invalid application metadata {key}: {value!r}')
    initial = application_version if new_database else None
    now = "datetime('now')"
    connection.execute(
        f'INSERT OR IGNORE INTO application_metadata(key,value,updated_at) '
        f'VALUES(?,?,{now})',
        (_VERSION_KEYS[0], initial),
    )
    connection.execute(
        f'INSERT OR IGNORE INTO application_metadata(key,value,updated_at) '
        f'VALUES(?,?,{now})',
        (_VERSION_KEYS[1], initial),
    )
    quoted_version = _quoted_sql(application_version)
    for table in _USER_DATA_TABLES:
        for operation in ('INSERT', 'UPDATE', 'DELETE'):
            trigger = f'nfprogress_app_version_{table}_{operation.lower()}'
            connection.execute(f'DROP TRIGGER IF EXISTS {trigger}')
            connection.execute(
                f'CREATE TRIGGER {trigger} AFTER {operation} ON {table} BEGIN '
                'UPDATE application_metadata '
                f'SET value={quoted_version},updated_at=datetime(\'now\') '
                "WHERE key='data_last_written_by_version'; END",
            )
    connection.commit()


def database_path(data_root: str | Path) -> Path:
    return Path(data_root).expanduser().resolve() / 'nfprogress.db'


def open_database(data_root: str | Path) -> sqlite3.Connection:
    path = database_path(data_root)
    new_database = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    register_remote_apply_authorization_guard(connection)
    connection.execute('PRAGMA foreign_keys = ON')
    connection.execute('PRAGMA busy_timeout = 5000')
    try:
        apply_migrations(connection)
        configure_application_metadata(
            connection,
            application_version=current_application_version(),
            new_database=new_database,
        )
    except Exception:
        connection.close()
        raise
    return connection
