"""Isolate test imports before any backend module creates its global app."""
from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path
from typing import NoReturn
from urllib.parse import unquote, urlsplit
from urllib.request import url2pathname

import pytest


_owned_profile = tempfile.TemporaryDirectory(prefix='worta-pytest-')
_profile = Path(_owned_profile.name).resolve(strict=True)
_scratch = _profile / 'tmp'
_scratch.mkdir(mode=0o700)
_violations = 0
tempfile.tempdir = str(_scratch)
os.environ['TMPDIR'] = str(_scratch)
os.environ['TEMP'] = str(_scratch)
os.environ['TMP'] = str(_scratch)
os.environ['NFPROGRESS_DATA_DIR'] = str(_profile / 'app')
os.environ['NFPROGRESS_TEST_DATA_DIR'] = str(_profile / 'app')
os.environ['NFPROGRESS_CLOUD_BLOB_DIR'] = str(_profile / 'blobs')
os.environ['NFPROGRESS_ENV'] = 'test'
os.environ['NFPROGRESS_PLATFORM'] = 'web'
os.environ.pop('NFPROGRESS_DATABASE_URL', None)
os.environ.pop('NFPROGRESS_TAURI_RUNTIME', None)


def _reject(message: str) -> NoReturn:
    global _violations
    _violations += 1
    raise PermissionError(message)


def _database_path(value: object) -> Path | None:
    if isinstance(value, int):
        return None
    try:
        raw = os.fsdecode(os.fspath(value))
    except TypeError:
        _reject('Test isolation cannot verify SQLite path.')
    if raw in ('', ':memory:'):
        return None
    if raw.startswith('file:'):
        uri = urlsplit(raw)
        if uri.netloc not in ('', 'localhost'):
            _reject('Test isolation rejects remote SQLite URIs.')
        if uri.path == ':memory:':
            return None
        raw = url2pathname(unquote(uri.path))
    try:
        return Path(raw).expanduser().resolve()
    except (OSError, RuntimeError, ValueError):
        _reject('Test isolation cannot resolve SQLite path.')


def _audit_sqlite(event: str, args: tuple[object, ...]) -> None:
    if event == 'sqlite3.connect':
        path = _database_path(args[0])
    elif event == 'open' and args and not isinstance(args[0], int):
        try:
            raw = os.fsdecode(os.fspath(args[0]))
        except TypeError:
            return
        if not re.search(r'\.(?:db|sqlite|sqlite3)(?:-(?:wal|shm|journal))?$', raw, re.IGNORECASE):
            return
        path = _database_path(raw)
    else:
        return
    if path is not None and not path.is_relative_to(_profile):
        _reject('Test isolation rejected a database outside the temporary profile.')


sys.addaudithook(_audit_sqlite)


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    # tmp_path and backend imports must share one owned root, even if a caller
    # supplies an unsafe inherited data directory or --basetemp.
    config.option.basetemp = str(_profile / 'pytest')


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if _violations:
        reporter = session.config.pluginmanager.get_plugin('terminalreporter')
        if reporter is not None:
            reporter.write_line(f'Test isolation rejected {_violations} outside-profile database access attempt(s).')
        if exitstatus == 0:
            session.exitstatus = pytest.ExitCode.TESTS_FAILED
