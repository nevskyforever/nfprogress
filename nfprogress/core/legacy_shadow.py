"""Keep the SQLite migration shadow derived from authoritative legacy files."""

from __future__ import annotations

import json
import logging
import os
import pickle
import shutil
import sqlite3
import tempfile
from contextvars import ContextVar
from pathlib import Path
from threading import Lock, RLock


LOGGER = logging.getLogger(__name__)
_legacy_shadow_sync_active = ContextVar(
    'nfprogress_legacy_shadow_sync_active', default=False,
)
_ROOT_LOCKS: dict[str, RLock] = {}
_ROOT_LOCKS_GUARD = Lock()


def _root_lock(root: Path) -> RLock:
    key = os.path.normcase(str(root))
    with _ROOT_LOCKS_GUARD:
        return _ROOT_LOCKS.setdefault(key, RLock())


def _pickle_owns_profile(root: Path) -> bool:
    """Return whether a bridge rebuild may derive SQLite from legacy files."""
    database = root / 'nfprogress.db'
    if not database.is_file():
        return True
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(
            f'file:{database.resolve().as_posix()}?mode=ro', uri=True,
        )
        table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='storage_ownership'",
        ).fetchone()
        if table is None:
            return True
        owners = {
            str(row[0]): str(row[1])
            for row in connection.execute(
                'SELECT subsystem,owner FROM storage_ownership',
            )
        }
        expected = {'projects', 'settings', 'notes', 'game'}
        return set(owners) == expected and all(
            owners[name] == 'pickle' for name in expected
        )
    except sqlite3.DatabaseError:
        # A corrupt derived database must not outrank readable legacy sources.
        return True
    finally:
        if connection is not None:
            connection.close()


def _load_documents(root: Path) -> dict[str, object]:
    path = root / 'documents.json'
    if not path.is_file():
        return {}
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError('documents.json must contain an object')
    return value


def _load_gamer_without_migration(root: Path):
    """Read gamer.pkl without allowing migration code to rewrite the source."""
    import game

    path = root / 'gamer.pkl'
    if not path.is_file():
        return game.Gamer()
    with path.open('rb') as stream:
        return pickle.load(stream)


def _mark_dirty(root: Path, error: Exception) -> None:
    from nfprogress.core.sqlite import SQLiteMirrorRepository

    try:
        SQLiteMirrorRepository(root).mark_dirty(error)
        return
    except Exception:
        LOGGER.exception('Could not mark upgraded SQLite mirror dirty')

    database = root / 'nfprogress.db'
    if not database.is_file():
        return
    try:
        with sqlite3.connect(database) as connection:
            table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' "
                "AND name='mirror_state'",
            ).fetchone()
            if table is not None:
                connection.execute(
                    "UPDATE mirror_state SET sync_status='dirty',last_error=? "
                    'WHERE id=1',
                    (str(error),),
                )
    except sqlite3.DatabaseError:
        LOGGER.exception('Could not mark legacy SQLite mirror dirty')


def sync_legacy_sqlite_shadow(
        data_root: str | Path, *, raise_on_error: bool = False,
) -> bool:
    """Atomically rebuild and verify SQLite from legacy PKL/JSON sources.

    The legacy files are read-only inputs.  A nested call caused by
    ``game.load_game()`` migration is ignored so ``Gamer.save()`` cannot
    recursively start another rebuild.
    """
    if _legacy_shadow_sync_active.get():
        return False

    root = Path(data_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    with _root_lock(root):
        if not _pickle_owns_profile(root):
            return False
        token = _legacy_shadow_sync_active.set(True)
        staging: Path | None = None
        try:
            import engine
            from nfprogress.core.sqlite import SQLiteMirrorRepository

            with engine.data_directory_context(root):
                projects = engine.load_data()
                settings = engine.load_settings()
                gamer = _load_gamer_without_migration(root)
            documents = _load_documents(root)

            staging = Path(tempfile.mkdtemp(
                prefix='.nfprogress-shadow-', dir=root,
            ))
            source_documents = root / 'documents.json'
            if source_documents.is_file():
                shutil.copy2(source_documents, staging / 'documents.json')
            SQLiteMirrorRepository(staging).rebuild(
                projects, settings, gamer, documents,
            )
            os.replace(staging / 'nfprogress.db', root / 'nfprogress.db')
            return True
        except Exception as error:
            _mark_dirty(root, error)
            if raise_on_error:
                raise
            LOGGER.exception('Legacy SQLite shadow synchronization failed')
            return False
        finally:
            _legacy_shadow_sync_active.reset(token)
            if staging is not None:
                shutil.rmtree(staging, ignore_errors=True)


def reconcile_legacy_sqlite_shadow(data_root: str | Path) -> bool:
    """Best-effort startup healing for a pickle-authoritative profile."""
    return sync_legacy_sqlite_shadow(data_root)
