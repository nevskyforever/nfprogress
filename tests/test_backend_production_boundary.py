from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app import __main__ as backend_cli
from backend.app.cloud.email import SmtpEmailSender
from backend.app.cloud.models import User
from backend.app.config import RuntimeConfig
from backend.app.main import create_app
from test_cloud_auth import AUTH_SECRET, create_user, login, migrated_database


DATABASE_URL = 'postgresql+psycopg://stage:do-not-log@127.0.0.1:1/stage'


def _production_config(**overrides) -> RuntimeConfig:
    values = dict(environment='production', database_url=DATABASE_URL,
                  auth_secret=AUTH_SECRET)
    values.update(overrides)
    return RuntimeConfig(**values)


def test_production_cloud_excludes_legacy_routes_and_plaintext_storage(tmp_path, monkeypatch):
    from backend.app import main as backend_main

    def reject_plaintext_access(*_args, **_kwargs):
        raise AssertionError('production cloud accessed a plaintext store')

    monkeypatch.setattr(backend_main.engine, 'get_app_data_dir', reject_plaintext_access)
    monkeypatch.setattr(backend_main, 'PickleRepository', reject_plaintext_access)
    data_dir = tmp_path / 'must-not-exist'
    app = create_app(_production_config(data_dir=data_dir))
    assert app.state.services is None
    with TestClient(app) as client:
        paths = client.get('/openapi.json').json()['paths']
        assert all(path.startswith(('/api/v1/', '/api/v2/', '/api/v3/'))
                   or path in {'/health', '/ready'}
                   for path in paths)
        assert '/api/v1/auth/login' in paths
        assert '/api/v1/admin/users' in paths
        for headers in ({}, {'X-NFProgress-Token': 'anything'}):
            assert client.get('/api/projects', headers=headers).status_code == 404
            assert client.post('/api/projects', headers=headers, json={}).status_code == 404
        assert client.get('/api/v1/admin/users').status_code == 401
    assert not data_dir.exists()


@pytest.mark.parametrize('unsafe', [
    {'session_token': 'legacy-token'},
    {'developer_mode': True},
    {'allow_local_files': True},
    {'platform': 'ios'},
])
def test_production_cloud_rejects_unsafe_profiles(unsafe):
    with pytest.raises(ValueError) as error:
        _production_config(**unsafe)
    assert 'do-not-log' not in str(error.value)
    assert AUTH_SECRET not in str(error.value)


def test_production_desktop_requires_legacy_session_token():
    with pytest.raises(ValueError, match='NFPROGRESS_SESSION_TOKEN'):
        _production_config(platform='desktop')
    desktop = _production_config(platform='desktop', session_token='desktop-token')
    assert desktop.cloud_only is False
    assert 'desktop-token' not in repr(desktop)


def test_invalid_database_url_does_not_echo_credentials():
    with pytest.raises(ValueError) as error:
        _production_config(database_url='postgresql+psycopg://user:do-not-log@localhost:do-not-log/db')
    assert 'do-not-log' not in str(error.value)


def test_cli_preserves_runtime_email_blob_and_auth_config(monkeypatch, tmp_path, capsys):
    values = {
        'NFPROGRESS_ENV': 'production',
        'NFPROGRESS_PLATFORM': 'web',
        'NFPROGRESS_DATABASE_URL': DATABASE_URL,
        'NFPROGRESS_AUTH_SECRET': AUTH_SECRET,
        'NFPROGRESS_ALLOWED_ORIGINS': 'https://private.example.test',
        'NFPROGRESS_PUBLIC_WEB_URL': 'https://private.example.test',
        'NFPROGRESS_SMTP_HOST': 'smtp.example.test',
        'NFPROGRESS_SMTP_PORT': '465',
        'NFPROGRESS_SMTP_USERNAME': 'mailer',
        'NFPROGRESS_SMTP_PASSWORD': 'do-not-log-smtp-secret',
        'NFPROGRESS_SMTP_FROM_EMAIL': 'mail@example.test',
        'NFPROGRESS_SMTP_FROM_NAME': 'WORTA',
        'NFPROGRESS_SMTP_SECURITY': 'implicit_tls',
        'NFPROGRESS_CLOUD_BLOB_DIR': str(tmp_path / 'blobs'),
        'NFPROGRESS_DATA_DIR': str(tmp_path / 'unused-legacy'),
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    captured = {}

    def capture_run(app, **options):
        captured['app'] = app
        captured['options'] = options

    # Build the real ASGI app through the CLI. Only the network serving call is
    # intercepted so this unit test cannot bind a persistent listener.
    monkeypatch.setattr(backend_cli.uvicorn, 'run', capture_run)
    assert backend_cli.main(['--host', '127.0.0.1']) == 0
    app = captured['app']
    config = app.state.runtime_config
    assert config.database_url == DATABASE_URL and config.auth_secret == AUTH_SECRET
    assert config.allowed_origins == ('https://private.example.test',)
    assert config.public_web_url == 'https://private.example.test'
    assert config.cloud_blob_dir == tmp_path / 'blobs'
    assert (config.smtp_host, config.smtp_port, config.smtp_username,
            config.smtp_password, config.smtp_from_email, config.smtp_from_name,
            config.smtp_security) == (
                'smtp.example.test', 465, 'mailer', 'do-not-log-smtp-secret',
                'mail@example.test', 'WORTA', 'implicit_tls')
    assert isinstance(app.state.email_sender, SmtpEmailSender)
    assert config.cloud_only and not config.allow_local_files
    assert app.state.services is None
    assert not (tmp_path / 'unused-legacy').exists()
    assert not (tmp_path / 'blobs').exists()
    output = capsys.readouterr()
    diagnostics = output.out + output.err + repr(config)
    assert 'do-not-log-smtp-secret' not in diagnostics
    assert 'do-not-log@' not in diagnostics
    assert AUTH_SECRET not in diagnostics
    assert 'mailer' not in repr(config)


def test_cli_rejects_incomplete_email_and_remote_legacy_without_secret_echo(
        monkeypatch, capsys):
    monkeypatch.setenv('NFPROGRESS_ENV', 'production')
    monkeypatch.setenv('NFPROGRESS_DATABASE_URL', DATABASE_URL)
    monkeypatch.setenv('NFPROGRESS_AUTH_SECRET', AUTH_SECRET)
    monkeypatch.setenv('NFPROGRESS_SMTP_PORT', 'do-not-log-smtp-secret')
    with pytest.raises(ValueError) as error:
        backend_cli.main([])
    assert 'do-not-log-smtp-secret' not in str(error.value)
    monkeypatch.delenv('NFPROGRESS_SMTP_PORT')
    monkeypatch.setenv('NFPROGRESS_SMTP_HOST', 'smtp.example.test')
    with pytest.raises(ValueError, match='SMTP configuration must be complete'):
        backend_cli.main([])
    monkeypatch.delenv('NFPROGRESS_SMTP_HOST')
    monkeypatch.setenv('NFPROGRESS_ENV', 'development')
    with pytest.raises(SystemExit, match='production cloud'):
        backend_cli.main(['--host', '0.0.0.0', '--allow-remote'])
    output = capsys.readouterr()
    assert AUTH_SECRET not in output.out + output.err


def test_cli_rejects_production_dev_data_before_copy(monkeypatch):
    monkeypatch.setenv('NFPROGRESS_ENV', 'production')
    monkeypatch.setenv('NFPROGRESS_DATABASE_URL', DATABASE_URL)
    monkeypatch.setenv('NFPROGRESS_AUTH_SECRET', AUTH_SECRET)
    monkeypatch.setattr(backend_cli.engine, 'prepare_web_test_data',
        lambda: pytest.fail('production copied plaintext development data'))
    with pytest.raises(SystemExit, match='Development data options'):
        backend_cli.main(['--dev-data'])
    with pytest.raises(SystemExit, match='Development data options'):
        backend_cli.main(['--prepare-dev-data'])


def test_cli_remote_bind_requires_and_uses_cloud_only_profile(monkeypatch):
    monkeypatch.setenv('NFPROGRESS_ENV', 'production')
    monkeypatch.setenv('NFPROGRESS_DATABASE_URL', DATABASE_URL)
    monkeypatch.setenv('NFPROGRESS_AUTH_SECRET', AUTH_SECRET)
    captured = {}
    monkeypatch.setattr(backend_cli.uvicorn, 'run',
        lambda app, **options: captured.update(app=app, options=options))
    assert backend_cli.main(['--host', '0.0.0.0', '--allow-remote']) == 0
    assert captured['app'].state.runtime_config.cloud_only
    assert captured['app'].state.services is None
    assert captured['options']['host'] == '0.0.0.0'


def test_development_web_and_desktop_keep_legacy_routes(tmp_path):
    for platform in ('web', 'desktop'):
        app = create_app(RuntimeConfig(data_dir=tmp_path / platform,
            platform=platform, session_token='local-token',
            allow_local_files=platform == 'desktop'))
        with TestClient(app) as client:
            assert '/api/projects' in client.get('/openapi.json').json()['paths']
            assert client.get('/api/projects').status_code == 401
            assert client.get('/api/projects', headers={
                'X-NFProgress-Token': 'local-token',
            }).status_code == 200


def test_production_desktop_retains_token_protected_local_api(tmp_path):
    app = create_app(_production_config(platform='desktop',
        session_token='desktop-token', data_dir=tmp_path, allow_local_files=True))
    with TestClient(app) as client:
        assert '/api/projects' in client.get('/openapi.json').json()['paths']
        assert client.get('/api/projects').status_code == 401
        assert client.get('/api/projects', headers={
            'X-NFProgress-Token': 'desktop-token',
        }).status_code == 200


def test_real_cli_listener_excludes_legacy_routes(tmp_path):
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith('NFPROGRESS_')}
    environment.update(NFPROGRESS_ENV='production', NFPROGRESS_PLATFORM='web',
                       NFPROGRESS_DATABASE_URL=DATABASE_URL,
                       NFPROGRESS_AUTH_SECRET=AUTH_SECRET,
                       NFPROGRESS_DATA_DIR=str(tmp_path / 'unused-legacy'))
    process = subprocess.Popen([sys.executable, '-m', 'backend.app', '--host',
        '127.0.0.1', '--port', str(port)], env=environment,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        base = f'http://127.0.0.1:{port}'
        deadline = time.monotonic() + 30
        while True:
            try:
                with urlopen(base + '/health', timeout=1) as response:
                    assert response.status == 200
                break
            except (URLError, TimeoutError):
                if process.poll() is not None or time.monotonic() >= deadline:
                    pytest.fail('production CLI did not start its loopback listener')
                time.sleep(0.1)
        with urlopen(base + '/openapi.json', timeout=2) as response:
            assert '/api/projects' not in response.read().decode()
        for path, expected in (('/api/projects', 404), ('/api/v1/admin/users', 401)):
            with pytest.raises(HTTPError) as error:
                urlopen(base + path, timeout=2)
            assert error.value.code == expected
        assert not (tmp_path / 'unused-legacy').exists()
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def test_production_cloud_keeps_real_login_and_admin_authorization(migrated_database, tmp_path):
    from test_cloud_auth import _database_url

    app = create_app(_production_config(database_url=_database_url(),
        data_dir=tmp_path / 'unused-legacy'))
    with TestClient(app) as client:
        create_user(migrated_database, username='Normal', email='normal@example.test')
        admin_id = create_user(migrated_database, username='Admin', email='admin@example.test')
        with Session(migrated_database) as session:
            admin = session.get(User, admin_id)
            admin.role = 'admin'
            session.commit()
        normal_login = login(client, 'Normal')
        admin_login = login(client, 'Admin')
        assert normal_login.status_code == 200 and admin_login.status_code == 200
        normal_headers = {'Authorization': f"Bearer {normal_login.json()['access_token']}"}
        admin_headers = {'Authorization': f"Bearer {admin_login.json()['access_token']}"}
        assert client.get('/api/v1/admin/users').status_code == 401
        assert client.get('/api/v1/admin/users', headers=normal_headers).status_code == 403
        assert client.get('/api/v1/admin/users', headers=admin_headers).status_code == 200
        assert client.get('/api/v1/auth/registration').json()['mode'] == 'closed'
    assert not (tmp_path / 'unused-legacy').exists()
