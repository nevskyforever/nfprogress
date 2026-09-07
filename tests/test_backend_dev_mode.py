from __future__ import annotations

from pathlib import Path

import pytest

from backend.app import __main__ as backend_cli


def test_web_dev_data_selects_isolated_profile_with_real_data(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[str] = []
    captured: dict[str, object] = {}
    development_dir = tmp_path / 'web_test_data'

    monkeypatch.setattr(
        backend_cli.engine,
        'prepare_web_test_data',
        lambda: calls.append('prepare') or development_dir,
    )
    monkeypatch.setattr(
        backend_cli,
        'create_app',
        lambda config: captured.setdefault('config', config),
    )
    monkeypatch.setattr(
        backend_cli.uvicorn,
        'run',
        lambda _app, **kwargs: captured.setdefault('uvicorn', kwargs),
    )

    assert backend_cli.main([
        '--host', '127.0.0.1',
        '--port', '8123',
        '--platform', 'web',
        '--dev-data',
    ]) == 0

    config = captured['config']
    assert config.data_dir == development_dir
    assert config.platform == 'web'
    assert calls == ['prepare']
    assert captured['uvicorn']['port'] == 8123


def test_non_web_dev_data_refreshes_canonical_tauri_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        backend_cli.engine,
        'refresh_test_data',
        lambda: calls.append('refresh'),
    )
    monkeypatch.setattr(
        backend_cli.engine,
        'get_test_data_dir',
        lambda: Path('/tmp/tauri-test-data'),
    )
    monkeypatch.setattr(
        backend_cli,
        'create_app',
        lambda config: captured.setdefault('config', config),
    )
    monkeypatch.setattr(
        backend_cli.uvicorn,
        'run',
        lambda _app, **kwargs: captured.setdefault('uvicorn', kwargs),
    )

    assert backend_cli.main([
        '--platform', 'desktop', '--dev-data',
    ]) == 0

    config = captured['config']
    assert config.data_dir == Path('/tmp/tauri-test-data')
    assert config.platform == 'desktop'
    assert calls == ['refresh']


def test_dev_data_cannot_be_combined_with_explicit_directory(
    tmp_path: Path,
) -> None:
    with pytest.raises(SystemExit, match='cannot be combined'):
        backend_cli.main(['--dev-data', '--data-dir', str(tmp_path)])
