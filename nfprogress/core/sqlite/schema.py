"""Versioned SQLite schema and migration runner."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from nfprogress.core.sqlite.ordering import (
    validate_order_invariants,
    validate_project_order,
)


MIGRATIONS_DIR = Path(__file__).with_name('migrations')
CURRENT_SCHEMA_VERSION = 24


def apply_migrations(connection: sqlite3.Connection) -> int:
    # Direct callers (including recovery and migration tests) need the same
    # fail-closed function before a persistent Notes trigger can be prepared.
    connection.create_function('note_sync_remote_apply_authorized', 1, lambda _value: 0)
    connection.execute('PRAGMA foreign_keys = ON')
    connection.execute(
        'CREATE TABLE IF NOT EXISTS schema_info '
        '(schema_version INTEGER NOT NULL)',
    )
    # The event table is created before migrations because F3's migration adds
    # retry/poison-event columns to the F2 table.
    connection.execute(
        'CREATE TABLE IF NOT EXISTS domain_events ('
        'event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL, '
        'project_id TEXT NOT NULL, stage_id TEXT, progress_id TEXT, '
        'effective_date TEXT, delta_symbols REAL, context_json TEXT NOT NULL, '
        'created_at TEXT NOT NULL, processed_at TEXT, '
        "consumer TEXT NOT NULL DEFAULT 'game', version INTEGER NOT NULL DEFAULT 1)",
    )
    rows = connection.execute(
        'SELECT schema_version FROM schema_info',
    ).fetchall()
    if len(rows) > 1:
        raise RuntimeError('schema_info contains more than one schema version')
    version = int(rows[0][0]) if rows else 0
    if version > CURRENT_SCHEMA_VERSION:
        raise RuntimeError(f'unsupported future SQLite schema version: {version}')
    for next_version in range(version + 1, CURRENT_SCHEMA_VERSION + 1):
        migration = MIGRATIONS_DIR / {
            1: '001_initial.sql',
            2: '002_storage_ownership.sql',
            3: '003_project_order.sql',
            4: '004_projects_authority.sql',
            5: '005_game_authority.sql',
            6: '006_documents_authority.sql',
            7: '007_application_metadata.sql',
            8: '008_cloud_sync_protocol.sql',
            9: '009_encrypted_sync_substrate.sql',
            10: '010_note_sync_intents.sql',
            11: '011_note_sync_intent_fairness.sql',
            12: '012_cloud_account_bindings.sql',
            13: '013_note_sync_upload_receipts.sql',
            14: '014_note_sync_upload_fairness.sql',
            15: '015_note_sync_remote_apply.sql',
            16: '016_cloud_project_bootstrap.sql',
            17: '017_note_sync_conflicts.sql',
            18: '018_note_sync_pending_resolutions.sql',
            19: '019_note_sync_resolution_outbox.sql',
            20: '020_note_sync_resolution_sealing.sql',
            21: '021_note_sync_resolution_upload_receipts.sql',
            22: '022_note_sync_resolution_inbox.sql',
            23: '023_note_sync_applied_resolutions.sql',
            24: '024_note_sync_multigeneration_tips.sql',
        }[next_version]
        sql = migration.read_text(encoding='utf-8')
        # executescript is wrapped explicitly because its implicit transaction
        # handling otherwise commits before running the script.
        # Keep the semantic guard in the same transaction as the migration.
        # Migration 003 creates the order relation, so an existing project
        # aggregate must not be allowed to advance the schema marker while
        # that relation is empty or incomplete.
        try:
            connection.executescript(f'BEGIN;\n{sql}\n')
            if next_version >= 3:
                validate_project_order(connection)
            if next_version >= 4:
                validate_order_invariants(connection)
            connection.execute('DELETE FROM schema_info')
            connection.execute(
                'INSERT INTO schema_info(schema_version) VALUES (?)',
                (next_version,),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    connection.execute(
        'CREATE INDEX IF NOT EXISTS idx_domain_events_pending '
        'ON domain_events(consumer, status, processed_at, created_at, event_id)'
    )
    return CURRENT_SCHEMA_VERSION
