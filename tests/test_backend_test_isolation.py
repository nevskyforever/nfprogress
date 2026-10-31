from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def protected_database(tmp_path: Path):
    sentinel = tmp_path / 'protected' / 'nfprogress.db'
    sentinel.parent.mkdir()
    with sqlite3.connect(sentinel) as db:
        db.execute('CREATE TABLE sentinel (value TEXT NOT NULL)')
        db.execute('INSERT INTO sentinel(value) VALUES (?)', ('isolated test data',))
    sentinel.chmod(0o444)
    before = (hashlib.sha256(sentinel.read_bytes()).digest(), sentinel.stat().st_mtime_ns)
    yield sentinel
    assert (hashlib.sha256(sentinel.read_bytes()).digest(), sentinel.stat().st_mtime_ns) == before


def _environment(sentinel: Path) -> dict[str, str]:
    return os.environ | {
        'NFPROGRESS_ENV': 'test',
        'NFPROGRESS_DATA_DIR': str(sentinel.parent),
        'NFPROGRESS_TEST_DATA_DIR': str(sentinel.parent),
        'WORTA_ISOLATION_SENTINEL': str(sentinel),
        'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
        'PYTHONDONTWRITEBYTECODE': '1',
    }


def test_direct_pytest_isolates_import_and_rejects_outside_database(protected_database: Path) -> None:
    profiles = []
    for _ in range(2):
        result = subprocess.run(
            [sys.executable, '-m', 'pytest', '-q', '-s', '--basetemp', str(protected_database.parent), 'tests/isolation_probe.py::test_import_and_outside_database_rejected'],
            cwd=ROOT, env=_environment(protected_database), capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert '1 passed' in result.stdout
        profile_line = next(line for line in result.stdout.splitlines() if line.startswith('ISOLATED_PROFILE='))
        profile = Path(profile_line.partition('=')[2])
        assert not profile.exists()
        profiles.append(profile)
    assert profiles[0] != profiles[1]


def test_even_a_caught_outside_attempt_fails_the_test_run(protected_database: Path) -> None:
    result = subprocess.run(
        [sys.executable, '-m', 'pytest', '-q', 'tests/isolation_probe.py::test_caught_outside_database_attempt'],
        cwd=ROOT, env=_environment(protected_database), capture_output=True, text=True, timeout=60,
    )
    assert result.returncode != 0
    assert 'Test isolation rejected 1 outside-profile database access attempt' in result.stdout


@pytest.mark.parametrize('value', [None, '', '   '])
def test_missing_test_data_path_fails_before_backend_import(protected_database: Path, value: str | None) -> None:
    environment = _environment(protected_database)
    if value is None:
        environment.pop('NFPROGRESS_DATA_DIR')
    else:
        environment['NFPROGRESS_DATA_DIR'] = value
    result = subprocess.run(
        [sys.executable, '-c', 'import backend.app.main'],
        cwd=ROOT, env=environment, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode != 0
    assert 'NFPROGRESS_DATA_DIR is required in test mode' in result.stderr


def test_explicit_test_app_requires_a_data_path_without_blocking_config_only_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.config import RuntimeConfig
    from backend.app.main import create_app

    monkeypatch.delenv('NFPROGRESS_DATA_DIR')
    assert RuntimeConfig.from_env().data_dir is None
    with pytest.raises(ValueError, match='NFPROGRESS_DATA_DIR is required in test mode'):
        create_app(RuntimeConfig(environment='test'))


def test_acceptance_runner_ignores_inherited_data_directory(protected_database: Path, tmp_path: Path) -> None:
    executable = tmp_path / 'bin'
    executable.mkdir()
    log = tmp_path / 'runner-profile.txt'
    python = executable / 'python3'
    python.write_text(
        '#!/bin/sh\n'
        'printf "%s\\n%s\\n%s\\n" "$NFPROGRESS_DATA_DIR" "$NFPROGRESS_TEST_DATA_DIR" "$NFPROGRESS_CLOUD_BLOB_DIR" >> "$WORTA_TEST_PROFILE_LOG"\n'
        'exec "$WORTA_TEST_REAL_PYTHON" "$@"\n', encoding='utf-8',
    )
    python.chmod(0o755)
    environment = _environment(protected_database) | {
        'PATH': str(executable) + os.pathsep + os.environ['PATH'],
        'WORTA_TEST_REAL_PYTHON': sys.executable,
        'WORTA_TEST_PROFILE_LOG': str(log),
    }
    profiles = []
    for _ in range(2):
        result = subprocess.run(
            ['bash', 'scripts/maintenance/local_acceptance.sh', 'quick'],
            cwd=ROOT, env=environment, capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        lines = log.read_text(encoding='utf-8').splitlines()
        assert len(lines) >= 3 and len(lines) % 3 == 0
        data, test_data, blobs = map(Path, lines[:3])
        assert data == test_data and data.name == 'app'
        assert blobs.parent == data.parent and blobs.name == 'blobs'
        assert data.parent != protected_database.parent
        assert not data.parent.exists()
        assert all(lines[index:index + 3] == lines[:3] for index in range(0, len(lines), 3))
        profiles.append(data.parent)
        log.unlink()
    assert profiles[0] != profiles[1]


def test_acceptance_runner_stops_if_temp_profile_cannot_be_created(protected_database: Path, tmp_path: Path) -> None:
    executable = tmp_path / 'bin'
    executable.mkdir()
    mktemp = executable / 'mktemp'
    mktemp.write_text('#!/bin/sh\nexit 1\n', encoding='utf-8')
    mktemp.chmod(0o755)
    environment = _environment(protected_database) | {'PATH': str(executable) + os.pathsep + os.environ['PATH']}
    result = subprocess.run(
        ['bash', 'scripts/maintenance/local_acceptance.sh', 'quick'],
        cwd=ROOT, env=environment, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode != 0
    assert '[PASS] task-owned test profile is isolated' not in result.stdout


def test_acceptance_runner_cleans_its_profile_after_a_failure(protected_database: Path, tmp_path: Path) -> None:
    executable = tmp_path / 'bin'
    executable.mkdir()
    log = tmp_path / 'profile.txt'
    mktemp = executable / 'mktemp'
    mktemp.write_text(
        '#!/bin/sh\n'
        'created=$("$WORTA_REAL_MKTEMP" "$@") || exit 1\n'
        'printf "%s\\n" "$created" > "$WORTA_TEST_PROFILE_LOG"\n'
        'printf "%s\\n" "$created"\n', encoding='utf-8',
    )
    mktemp.chmod(0o755)
    git = executable / 'git'
    git.write_text('#!/bin/sh\nexit 7\n', encoding='utf-8')
    git.chmod(0o755)
    real_mktemp = shutil.which('mktemp')
    assert real_mktemp is not None
    environment = _environment(protected_database) | {
        'PATH': str(executable) + os.pathsep + os.environ['PATH'],
        'WORTA_REAL_MKTEMP': real_mktemp,
        'WORTA_TEST_PROFILE_LOG': str(log),
    }
    result = subprocess.run(
        ['bash', 'scripts/maintenance/local_acceptance.sh', 'quick'],
        cwd=ROOT, env=environment, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode != 0
    assert '[PASS] task-owned test profile is isolated' in result.stdout
    assert not Path(log.read_text(encoding='utf-8').strip()).exists()
