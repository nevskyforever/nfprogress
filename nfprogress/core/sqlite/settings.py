"""SQLite authoritative settings storage and the legacy cutover."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

from nfprogress.core.sqlite.connection import open_database
from nfprogress.core.sqlite.repository import _json

T = TypeVar('T')


class SQLiteSettingsRepository:
    """Typed settings access backed only by the fixed ``settings`` table."""

    def __init__(self, data_root: str | Path) -> None:
        self.data_root = Path(data_root).expanduser().resolve()

    def get_all(self) -> dict[str, Any]:
        with open_database(self.data_root) as db:
            return {row['key']: json.loads(row['value_json'])
                    for row in db.execute('SELECT key, value_json FROM settings')}

    def write_all(self, values: dict[str, Any]) -> None:
        if not isinstance(values, dict):
            raise TypeError('settings data must be a dictionary')
        with open_database(self.data_root) as db:
            with db:
                self._write_in_transaction(db, values)

    def set(self, key: str, value: Any) -> None:
        with open_database(self.data_root) as db:
            with db:
                db.execute(
                    'INSERT INTO settings(key, value_json) VALUES(?, ?) '
                    'ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json',
                    (str(key), _json(value)),
                )

    def set_all(self, values: dict[str, Any]) -> None:
        """Atomically upsert a settings patch without deleting other keys."""
        if not isinstance(values, dict):
            raise TypeError('settings data must be a dictionary')
        with open_database(self.data_root) as db:
            with db:
                db.executemany(
                    'INSERT INTO settings(key, value_json) VALUES(?, ?) '
                    'ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json',
                    [(str(key), _json(value)) for key, value in values.items()],
                )

    def update(self, mutator: Callable[[dict[str, Any]], T]) -> T:
        if not callable(mutator):
            raise TypeError('mutator must be callable')
        with open_database(self.data_root) as db:
            with db:
                values = self.get_all_from_connection(db)
                result = mutator(values)
                self._write_in_transaction(db, values)
                return result

    @staticmethod
    def get_all_from_connection(db) -> dict[str, Any]:
        return {row['key']: json.loads(row['value_json'])
                for row in db.execute('SELECT key, value_json FROM settings')}

    @staticmethod
    def _write_in_transaction(db, values: dict[str, Any]) -> None:
        db.execute('DELETE FROM settings')
        db.executemany(
            'INSERT INTO settings(key, value_json) VALUES(?, ?)',
            [(str(key), _json(value)) for key, value in values.items()],
        )


def cutover_settings(data_root: str | Path, pickle_settings: dict[str, Any]) -> None:
    """Import the complete PKL state and switch ownership after parity."""
    if not isinstance(pickle_settings, dict):
        raise TypeError('settings data must be a dictionary')
    from nfprogress.core.sqlite.ownership import StorageOwner, Subsystem

    root = Path(data_root).expanduser().resolve()
    with open_database(root) as db:
        with db:
            row = db.execute(
                'SELECT owner FROM storage_ownership WHERE subsystem = ?',
                (Subsystem.SETTINGS.value,),
            ).fetchone()
            if row is None:
                raise RuntimeError('missing storage ownership for settings')
            if row['owner'] == StorageOwner.SQLITE.value:
                return
            SQLiteSettingsRepository._write_in_transaction(db, pickle_settings)
            actual = SQLiteSettingsRepository.get_all_from_connection(db)
            expected = {str(key): json.loads(_json(value))
                        for key, value in pickle_settings.items()}
            if actual != expected:
                raise RuntimeError('settings SQLite parity verification failed')
            db.execute(
                "UPDATE storage_ownership SET owner = ?, updated_at = datetime('now') "
                'WHERE subsystem = ?',
                (StorageOwner.SQLITE.value, Subsystem.SETTINGS.value),
            )
