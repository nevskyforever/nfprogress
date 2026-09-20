from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import Mock

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError

from backend.app.config import RuntimeConfig
from backend.app.db import CloudDatabase, DatabaseReadiness
from backend.app.db.database import POSTGRESQL_CONNECT_TIMEOUT_SECONDS
from backend.app.main import create_app


DATABASE_URL = 'postgresql+psycopg://cloud_user:do-not-leak@localhost:5432/nfprogress_test'
ROOT = Path(__file__).resolve().parents[1]


def test_development_configuration_allows_legacy_web_without_postgresql(monkeypatch):
    monkeypatch.delenv('NFPROGRESS_DATABASE_URL', raising=False)
    monkeypatch.delenv('NFPROGRESS_ENV', raising=False)

    config = RuntimeConfig.from_env()

    assert config.environment == 'development'
    assert config.database_url is None
    assert CloudDatabase(config.database_url).readiness() == DatabaseReadiness.NOT_CONFIGURED


def test_production_configuration_requires_postgresql_url():
    with pytest.raises(ValueError, match='NFPROGRESS_DATABASE_URL is required'):
        RuntimeConfig(environment='production')

    config = RuntimeConfig(
        environment='production', database_url=DATABASE_URL,
        auth_secret='test-only-auth-secret-with-at-least-32-characters',
    )
    assert config.require_database_url() == DATABASE_URL


def test_invalid_environment_and_non_postgresql_url_are_rejected_without_secret_echo():
    with pytest.raises(ValueError, match='NFPROGRESS_ENV must be one of'):
        RuntimeConfig(environment='staging')

    secret_url = 'sqlite:///do-not-leak.sqlite'
    with pytest.raises(ValueError) as error:
        RuntimeConfig(database_url=secret_url)
    assert secret_url not in str(error.value)
    assert secret_url not in repr(RuntimeConfig())
    assert 'do-not-leak' not in repr(RuntimeConfig(database_url=DATABASE_URL))


def test_cloud_database_reuses_one_engine_and_disposes_it(monkeypatch):
    engine = Mock()
    create_engine_mock = Mock(return_value=engine)
    monkeypatch.setattr('backend.app.db.database.create_engine', create_engine_mock)
    database = CloudDatabase(DATABASE_URL)

    assert database.engine is engine
    assert database.engine is engine
    create_engine_mock.assert_called_once_with(
        DATABASE_URL,
        pool_pre_ping=True,
        connect_args={'connect_timeout': POSTGRESQL_CONNECT_TIMEOUT_SECONDS},
    )
    database.dispose()

    engine.dispose.assert_called_once_with()


def test_cloud_session_scope_closes_the_request_session():
    database = CloudDatabase(DATABASE_URL)
    session = Mock()
    database._session_factory = Mock(return_value=session)
    scope = database.session_scope()

    assert next(scope) is session
    scope.close()

    session.close.assert_called_once_with()
    session.rollback.assert_not_called()


def test_readiness_endpoint_reports_configured_healthy_database(tmp_path):
    app = create_app(RuntimeConfig(data_dir=tmp_path, database_url=DATABASE_URL))
    app.state.cloud_database.readiness = Mock(return_value=DatabaseReadiness.READY)

    with TestClient(app) as client:
        response = client.get('/ready')

    assert response.status_code == 200
    assert response.json() == {'status': 'ok', 'database': 'ready'}


def test_readiness_endpoint_reports_unavailable_database_without_fallback(tmp_path):
    app = create_app(RuntimeConfig(data_dir=tmp_path, database_url=DATABASE_URL))
    app.state.cloud_database.readiness = Mock(return_value=DatabaseReadiness.UNAVAILABLE)
    legacy_repository = app.state.services.repository
    legacy_repository.read_settings = Mock(side_effect=AssertionError('legacy fallback'))

    with TestClient(app) as client:
        response = client.get('/ready')

    assert response.status_code == 503
    assert response.json() == {'status': 'not_ready', 'database': 'unavailable'}
    legacy_repository.read_settings.assert_not_called()


def test_readiness_endpoint_reports_unconfigured_cloud_database(tmp_path):
    app = create_app(RuntimeConfig(data_dir=tmp_path))

    with TestClient(app) as client:
        response = client.get('/ready')

    assert response.status_code == 503
    assert response.json() == {'status': 'not_ready', 'database': 'not_configured'}


def test_readiness_connection_failure_is_sanitized(monkeypatch):
    database = CloudDatabase(DATABASE_URL)
    connection = Mock()
    connection.__enter__ = Mock(side_effect=OperationalError('SELECT 1', {}, OSError('secret host')))
    connection.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(database.engine, 'connect', Mock(return_value=connection))

    assert database.readiness() == DatabaseReadiness.UNAVAILABLE


@pytest.mark.skipif(
    not os.environ.get('NFPROGRESS_TEST_DATABASE_URL'),
    reason='requires a dedicated real PostgreSQL database in NFPROGRESS_TEST_DATABASE_URL',
)
def test_alembic_upgrade_empty_postgresql_database_to_head_twice(monkeypatch):
    """This is intentionally real PostgreSQL coverage, never SQLite emulation."""
    test_database_url = os.environ['NFPROGRESS_TEST_DATABASE_URL']
    assert test_database_url.startswith('postgresql+psycopg://')
    migration_engine = create_engine(test_database_url)
    try:
        with migration_engine.begin() as connection:
            connection.execute(text('DROP TABLE IF EXISTS reserved_usernames CASCADE'))
            connection.execute(text('DROP TABLE IF EXISTS user_limit_overrides CASCADE'))
            connection.execute(text('DROP TABLE IF EXISTS global_limits CASCADE'))
            connection.execute(text('DROP TABLE IF EXISTS registration_settings CASCADE'))
            connection.execute(text('DROP TABLE IF EXISTS password_reset_tokens CASCADE'))
            connection.execute(text('DROP TABLE IF EXISTS email_verification_tokens CASCADE'))
            connection.execute(text('DROP TABLE IF EXISTS auth_refresh_tokens CASCADE'))
            connection.execute(text('DROP TABLE IF EXISTS auth_sessions CASCADE'))
            connection.execute(text('DROP TABLE IF EXISTS users CASCADE'))
            connection.execute(text('DROP TABLE IF EXISTS alembic_version'))

        monkeypatch.setenv('NFPROGRESS_ENV', 'test')
        monkeypatch.setenv('NFPROGRESS_DATABASE_URL', test_database_url)
        alembic_config = AlembicConfig(str(ROOT / 'alembic.ini'))
        command.upgrade(alembic_config, 'head')
        command.upgrade(alembic_config, 'head')

        with migration_engine.connect() as connection:
            assert set(inspect(connection).get_table_names()) == {
                'alembic_version', 'users', 'auth_sessions', 'auth_refresh_tokens',
                'email_verification_tokens', 'password_reset_tokens', 'registration_settings',
                'global_limits', 'user_limit_overrides', 'reserved_usernames',
            }
            assert connection.execute(text('SELECT version_num FROM alembic_version')).scalar_one() == (
                'c6_reserved_usernames'
            )
    finally:
        with migration_engine.begin() as connection:
            connection.execute(text('DROP TABLE IF EXISTS reserved_usernames CASCADE'))
            connection.execute(text('DROP TABLE IF EXISTS user_limit_overrides CASCADE'))
            connection.execute(text('DROP TABLE IF EXISTS global_limits CASCADE'))
            connection.execute(text('DROP TABLE IF EXISTS registration_settings CASCADE'))
            connection.execute(text('DROP TABLE IF EXISTS password_reset_tokens CASCADE'))
            connection.execute(text('DROP TABLE IF EXISTS email_verification_tokens CASCADE'))
            connection.execute(text('DROP TABLE IF EXISTS auth_refresh_tokens CASCADE'))
            connection.execute(text('DROP TABLE IF EXISTS auth_sessions CASCADE'))
            connection.execute(text('DROP TABLE IF EXISTS users CASCADE'))
            connection.execute(text('DROP TABLE IF EXISTS alembic_version'))
        migration_engine.dispose()
