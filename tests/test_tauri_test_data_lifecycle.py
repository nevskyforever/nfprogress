from __future__ import annotations

import os
import subprocess
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _fake_python(path: Path) -> None:
    path.write_text(textwrap.dedent("""
        #!/bin/bash
        set -euo pipefail
        if [ "${1:-}" = "-m" ] && [ "${2:-}" = "nfprogress.migration_helper" ]; then
          exit "${TEST_VERIFY_EXIT:-0}"
        fi
        if [ "${1:-}" = "-c" ]; then
          exit 0
        fi
        if [ "${1:-}" = "-m" ] && [ "${2:-}" = "backend.app" ]; then
          printf '%s\n' refresh >> "$TEST_REFRESH_LOG"
          exit 0
        fi
        exit 2
    """).lstrip(), encoding='utf-8')
    path.chmod(0o755)


def test_prepare_script_reuses_valid_persistent_profile(tmp_path: Path) -> None:
    fake_python = tmp_path / 'python'
    _fake_python(fake_python)
    refresh_log = tmp_path / 'refresh.log'
    result = subprocess.run(
        [str(ROOT / 'scripts' / 'prepare-tauri-test-data.sh')],
        cwd=ROOT,
        env=os.environ | {
            'HOME': str(tmp_path),
            'TMPDIR': str(tmp_path),
            'NFPROGRESS_PYTHON': str(fake_python),
            'TEST_REFRESH_LOG': str(refresh_log),
            'TEST_VERIFY_EXIT': '0',
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert 'persistent Tauri test_data' in result.stdout
    assert not refresh_log.exists()


def test_prepare_script_refreshes_only_when_missing_or_explicit(tmp_path: Path) -> None:
    fake_python = tmp_path / 'python'
    _fake_python(fake_python)
    refresh_log = tmp_path / 'refresh.log'
    environment = os.environ | {
        'HOME': str(tmp_path),
        'TMPDIR': str(tmp_path),
        'NFPROGRESS_PYTHON': str(fake_python),
        'TEST_REFRESH_LOG': str(refresh_log),
        'TEST_VERIFY_EXIT': '1',
    }

    initialized = subprocess.run(
        [str(ROOT / 'scripts' / 'prepare-tauri-test-data.sh')],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    refreshed = subprocess.run(
        [str(ROOT / 'scripts' / 'prepare-tauri-test-data.sh'), '--refresh'],
        cwd=ROOT,
        env=environment | {'TEST_VERIFY_EXIT': '0'},
        capture_output=True,
        text=True,
        check=False,
    )

    assert initialized.returncode == 0, initialized.stdout + initialized.stderr
    assert refreshed.returncode == 0, refreshed.stdout + refreshed.stderr
    assert refresh_log.read_text(encoding='utf-8').splitlines() == ['refresh', 'refresh']


def test_importing_engine_does_not_create_or_refresh_test_data(tmp_path: Path) -> None:
    result = subprocess.run(
        ['python3.13', '-c', 'import engine'],
        cwd=ROOT,
        env=os.environ | {'HOME': str(tmp_path)},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert not (tmp_path / 'Documents' / 'nfprogress' / 'test_data').exists()
