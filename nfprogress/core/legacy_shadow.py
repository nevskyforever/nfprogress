"""Keep the SQLite migration shadow derived from authoritative legacy files."""

from __future__ import annotations

import logging
import os
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


def sync_legacy_sqlite_shadow(
        data_root: str | Path, *, raise_on_error: bool = False,
) -> bool:
    """Atomically prepare a 6.0-qualified DB from legacy PKL/JSON sources.

    This bridge version always treats the legacy files as runtime authority.
    SQLite ownership describes the prepared target contract only and never
    suppresses a later rebuild. Nested calls are ignored so a save cannot
    recursively start another preparation.
    """
    if _legacy_shadow_sync_active.get():
        return False

    root = Path(data_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    with _root_lock(root):
        token = _legacy_shadow_sync_active.set(True)
        try:
            from nfprogress.migration_helper import prepare_bridge_snapshot

            prepare_bridge_snapshot(root)
            return True
        except Exception:
            if raise_on_error:
                raise
            LOGGER.exception('Legacy 6.0 snapshot preparation failed')
            return False
        finally:
            _legacy_shadow_sync_active.reset(token)


def reconcile_legacy_sqlite_shadow(data_root: str | Path) -> bool:
    """Best-effort startup healing for a pickle-authoritative profile."""
    return sync_legacy_sqlite_shadow(data_root)
