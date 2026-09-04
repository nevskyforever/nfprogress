"""Thread-safe access to the legacy nfprogress pickle stores.

The repository deliberately keeps the on-disk format unchanged.  It gives the
new application layer an explicit storage root while the legacy UI can continue
to use :mod:`engine` with its existing platform-specific defaults.
"""

from __future__ import annotations

import shutil
import os
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock, RLock, local
from typing import Any, TypeVar

import engine
from nfprogress.core.sqlite.connection import open_database


T = TypeVar('T')
_PROCESS_LOCKS: dict[str, RLock] = {}
_PROCESS_LOCKS_GUARD = Lock()
_THREAD_LOCK_STATE = local()


def _process_lock(path: Path) -> RLock:
    key = os.path.normcase(str(path.resolve()))
    with _PROCESS_LOCKS_GUARD:
        return _PROCESS_LOCKS.setdefault(key, RLock())


def _acquire_file_lock(stream) -> None:
    """Acquire one advisory byte lock on Windows or the whole file on POSIX."""
    if os.name == 'nt':
        import msvcrt

        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b'\0')
            stream.flush()
        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
        return

    import fcntl

    fcntl.flock(stream.fileno(), fcntl.LOCK_EX)


def _release_file_lock(stream) -> None:
    if os.name == 'nt':
        import msvcrt

        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        return

    import fcntl

    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


class PickleRepository:
    """Persist legacy projects, settings, and game state under one directory."""

    _STORE_NAMES = frozenset({'data', 'settings', 'gamer'})

    def __init__(self, base_dir: str | Path) -> None:
        if base_dir is None:
            raise TypeError('base_dir must be an explicit path')
        self.base_dir = Path(base_dir).expanduser().resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._lock = _process_lock(self.base_dir)

    @property
    def transaction_lock(self) -> RLock:
        """Return the re-entrant lock used by repository transactions."""
        return self._lock

    @contextmanager
    def storage_context(self) -> Iterator[Path]:
        """Route nested legacy engine/game persistence to ``base_dir``."""
        with engine.data_directory_context(self.base_dir) as data_dir:
            yield data_dir

    @contextmanager
    def locked(self) -> Iterator[PickleRepository]:
        """Hold process/thread locks and activate the explicit storage context."""
        key = os.path.normcase(str(self.base_dir))
        with self._lock:
            active_paths = getattr(_THREAD_LOCK_STATE, 'paths', set())
            if key in active_paths:
                with self.storage_context():
                    yield self
                return

            lock_path = self.base_dir / '.nfprogress.lock'
            with lock_path.open('a+b') as lock_stream:
                _acquire_file_lock(lock_stream)
                _THREAD_LOCK_STATE.paths = {*active_paths, key}
                try:
                    with self.storage_context():
                        yield self
                finally:
                    _THREAD_LOCK_STATE.paths = active_paths
                    _release_file_lock(lock_stream)

    def read_projects(self) -> dict[str, Any]:
        """Read the complete legacy project-data envelope."""
        from nfprogress.core.sqlite import StorageOwner, StorageOwnershipRepository, Subsystem
        if StorageOwnershipRepository(self.base_dir).get_owner(Subsystem.PROJECTS) == StorageOwner.SQLITE:
            from nfprogress.core.game_state import SQLiteGameRepository
            return SQLiteGameRepository(self.base_dir).read_projects()
        with self.locked():
            return engine.load_data()

    def write_projects(self, data: dict[str, Any]) -> None:
        """Atomically write the complete legacy project-data envelope."""
        from nfprogress.core.sqlite import StorageOwner, StorageOwnershipRepository, Subsystem
        if StorageOwnershipRepository(self.base_dir).get_owner(Subsystem.PROJECTS) == StorageOwner.SQLITE:
            from nfprogress.core.game_state import SQLiteGameRepository
            if StorageOwnershipRepository(self.base_dir).get_owner(Subsystem.GAME) == StorageOwner.SQLITE:
                SQLiteGameRepository(self.base_dir).write_game_data(data)
                return
            raise RuntimeError('Projects are SQLite-authoritative; legacy writes are disabled.')
        if not isinstance(data, dict):
            raise TypeError('project data must be a dictionary')
        with self.locked():
            engine.atomic_pickle_save(data, engine.get_data_file_path('data'))
            self._sync_shadow_after_pickle_save()

    def update_projects(self, mutator: Callable[[dict[str, Any]], T]) -> T:
        """Read, mutate, and save project data as one re-entrant transaction.

        ``mutator`` receives the mutable full legacy envelope.  Its return value
        is passed back to the caller; the envelope itself is always the value
        persisted after a successful callback.
        """
        from nfprogress.core.sqlite import StorageOwner, StorageOwnershipRepository, Subsystem
        if StorageOwnershipRepository(self.base_dir).get_owner(Subsystem.PROJECTS) == StorageOwner.SQLITE:
            raise RuntimeError('Projects are SQLite-authoritative; legacy writes are disabled.')
        if not callable(mutator):
            raise TypeError('mutator must be callable')
        with self.locked():
            data = engine.load_data()
            result = mutator(data)
            engine.atomic_pickle_save(data, engine.get_data_file_path('data'))
            self._sync_shadow_after_pickle_save()
            return result

    def read_settings(self) -> dict[str, Any]:
        from nfprogress.core.sqlite import (
            SQLiteSettingsRepository, StorageOwner,
            StorageOwnershipRepository, Subsystem,
        )
        if StorageOwnershipRepository(self.base_dir).get_owner(Subsystem.SETTINGS) == StorageOwner.SQLITE:
            return SQLiteSettingsRepository(self.base_dir).get_all()
        with self.locked():
            return engine.load_settings()

    def write_settings(self, data: dict[str, Any]) -> None:
        if not isinstance(data, dict):
            raise TypeError('settings data must be a dictionary')
        from nfprogress.core.sqlite import (
            SQLiteSettingsRepository, StorageOwner,
            StorageOwnershipRepository, Subsystem,
        )
        if StorageOwnershipRepository(self.base_dir).get_owner(Subsystem.SETTINGS) == StorageOwner.SQLITE:
            SQLiteSettingsRepository(self.base_dir).write_all(data)
            return
        with self.locked():
            engine.atomic_pickle_save(data, engine.get_data_file_path('settings'))
            self._sync_shadow_after_pickle_save()

    def update_settings(self, mutator: Callable[[dict[str, Any]], T]) -> T:
        """Read, mutate, and save settings without a lost-update window."""
        if not callable(mutator):
            raise TypeError('mutator must be callable')
        from nfprogress.core.sqlite import (
            SQLiteSettingsRepository, StorageOwner,
            StorageOwnershipRepository, Subsystem,
        )
        if StorageOwnershipRepository(self.base_dir).get_owner(Subsystem.SETTINGS) == StorageOwner.SQLITE:
            return SQLiteSettingsRepository(self.base_dir).update(mutator)
        with self.locked():
            settings = engine.load_settings()
            result = mutator(settings)
            engine.atomic_pickle_save(
                settings, engine.get_data_file_path('settings'),
            )
            self._sync_shadow_after_pickle_save()
            return result

    def read_gamer(self) -> Any:
        """Read and migrate game state using the legacy game implementation."""
        from nfprogress.core.sqlite import StorageOwner, StorageOwnershipRepository, Subsystem
        if StorageOwnershipRepository(self.base_dir).get_owner(Subsystem.GAME) == StorageOwner.SQLITE:
            from nfprogress.core.game_state import SQLiteGameRepository
            return SQLiteGameRepository(self.base_dir).read_gamer()
        import game
        with self.locked():
            return game.load_game()

    def notes_repository(self):
        """Return the Notes repository selected by the ownership table."""
        from nfprogress.core.sqlite import (
            SQLiteNotesRepository, StorageOwner, StorageOwnershipRepository,
            Subsystem,
        )
        if StorageOwnershipRepository(self.base_dir).get_owner(Subsystem.NOTES) == StorageOwner.SQLITE:
            return SQLiteNotesRepository(self.base_dir)
        return None

    def write_gamer(self, gamer: Any) -> None:
        """Atomically write a game-state object without changing its format."""
        from nfprogress.core.sqlite import StorageOwner, StorageOwnershipRepository, Subsystem
        if StorageOwnershipRepository(self.base_dir).get_owner(Subsystem.GAME) == StorageOwner.SQLITE:
            from nfprogress.core.game_state import SQLiteGameRepository
            SQLiteGameRepository(self.base_dir).write_gamer(gamer)
            return
        with self.locked():
            engine.atomic_pickle_save(gamer, engine.get_data_file_path('gamer'))
            self._sync_shadow_after_pickle_save()

    def synchronize_shadow(self) -> None:
        """Rebuild SQLite from PKL; PKL remains untouched and authoritative."""
        from nfprogress.core.sqlite import SQLiteMirrorRepository
        from nfprogress.core.sqlite import StorageOwner, StorageOwnershipRepository, Subsystem
        with self.locked():
            try:
                owners = StorageOwnershipRepository(self.base_dir).owners()
                if all(owner == StorageOwner.SQLITE for owner in owners.values()):
                    # A fully cut-over desktop has no legacy source to mirror.
                    with open_database(self.base_dir) as db:
                        db.execute('PRAGMA integrity_check').fetchone()
                    return
                SQLiteMirrorRepository(self.base_dir).rebuild(
                    engine.load_data() if owners[Subsystem.PROJECTS] == StorageOwner.PICKLE else {},
                    engine.load_settings() if owners[Subsystem.SETTINGS] == StorageOwner.PICKLE else {},
                    __import__('game').load_game() if owners[Subsystem.GAME] == StorageOwner.PICKLE else None,
                )
            except Exception as error:
                SQLiteMirrorRepository(self.base_dir).mark_dirty(error)
                raise

    def _sync_shadow_after_pickle_save(self) -> None:
        """Best-effort mirror update after a successful legacy write."""
        from nfprogress.core.sqlite import SQLiteMirrorRepository

        try:
            SQLiteMirrorRepository(self.base_dir).rebuild(
                engine.load_data(),
                engine.load_settings(),
                __import__('game').load_game(),
            )
        except Exception as error:
            SQLiteMirrorRepository(self.base_dir).mark_dirty(error)

    def create_backup(self, names: Iterable[str] | str | None = None) -> Path:
        """Copy existing stores into a unique timestamped snapshot directory.

        Source files are never moved or removed.  Missing stores are simply
        omitted, which allows this method to be called before a partial migration.
        """
        store_names = self._validate_store_names(names)
        with self.locked():
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
            backups_root = self.base_dir / 'backups'
            backup_dir = backups_root / timestamp
            suffix = 1
            while backup_dir.exists():
                backup_dir = backups_root / f'{timestamp}-{suffix}'
                suffix += 1
            backup_dir.mkdir(parents=True)

            for name in store_names:
                source = self.base_dir / f'{name}.pkl'
                if source.is_file():
                    shutil.copy2(source, backup_dir / source.name)
            database = self.base_dir / 'nfprogress.db'
            # The SQLite database may contain authoritative settings and Notes,
            # so every backup is a recoverable application snapshot regardless
            # of which legacy pickle store triggered it.
            if database.is_file():
                shutil.copy2(database, backup_dir / database.name)
            return backup_dir

    def backup(self, names: Iterable[str] | str | None = None) -> Path:
        """Alias for :meth:`create_backup` used by migration code."""
        return self.create_backup(names)

    @classmethod
    def _validate_store_names(
        cls,
        names: Iterable[str] | str | None,
    ) -> tuple[str, ...]:
        if names is None:
            return tuple(sorted(cls._STORE_NAMES))
        requested = (names,) if isinstance(names, str) else tuple(names)
        unknown = [name for name in requested if name not in cls._STORE_NAMES]
        if unknown:
            raise ValueError(f'unknown pickle store: {unknown[0]!r}')
        return requested
