"""Authoritative storage ownership for SQLite-backed subsystems."""

from __future__ import annotations

import sqlite3
from enum import StrEnum
from pathlib import Path

from nfprogress.core.sqlite.connection import open_database


class Subsystem(StrEnum):
    PROJECTS = 'projects'
    SETTINGS = 'settings'
    NOTES = 'notes'
    GAME = 'game'


class StorageOwner(StrEnum):
    PICKLE = 'pickle'
    SQLITE = 'sqlite'


SUBSYSTEMS = tuple(Subsystem)


class StorageOwnershipRepository:
    """Centralized access to the source-of-truth ownership table."""

    def __init__(self, data_root: str | Path) -> None:
        self.data_root = Path(data_root).expanduser().resolve()

    def get_owner(self, subsystem: Subsystem | str) -> StorageOwner:
        subsystem = self._subsystem(subsystem)
        with open_database(self.data_root) as db:
            row = db.execute(
                'SELECT owner FROM storage_ownership WHERE subsystem = ?',
                (subsystem.value,),
            ).fetchone()
        if row is None:
            raise RuntimeError(f'missing storage ownership for {subsystem.value!r}')
        try:
            return StorageOwner(row['owner'])
        except ValueError as error:
            raise RuntimeError(
                f'unknown storage owner for {subsystem.value!r}: {row["owner"]!r}',
            ) from error

    def owners(self) -> dict[Subsystem, StorageOwner]:
        return {subsystem: self.get_owner(subsystem) for subsystem in SUBSYSTEMS}

    def set_owner(self, subsystem: Subsystem | str, owner: StorageOwner | str) -> None:
        """Set ownership transactionally for a future controlled cutover flow."""
        subsystem = self._subsystem(subsystem)
        try:
            owner = StorageOwner(owner)
        except ValueError as error:
            raise ValueError(f'unknown storage owner: {owner!r}') from error
        with open_database(self.data_root) as db:
            with db:
                db.execute(
                    'UPDATE storage_ownership SET owner = ?, updated_at = datetime(\'now\') '
                    'WHERE subsystem = ?', (owner.value, subsystem.value),
                )
                if db.execute('SELECT changes()').fetchone()[0] != 1:
                    raise RuntimeError(f'missing storage ownership for {subsystem.value!r}')

    @staticmethod
    def _subsystem(subsystem: Subsystem | str) -> Subsystem:
        try:
            return Subsystem(subsystem)
        except ValueError as error:
            raise ValueError(f'unknown storage subsystem: {subsystem!r}') from error
