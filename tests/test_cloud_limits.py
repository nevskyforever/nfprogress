from __future__ import annotations

from alembic import command
from alembic.config import Config as AlembicConfig
import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.cloud.models import GlobalLimits, User, UserLimitOverrides
from backend.app.cloud.services import LimitsService
from test_cloud_auth import ROOT, _database_url, cloud_client, create_user, login, migrated_database


def _set_global(engine, value: int) -> None:
    with Session(engine) as session:
        limits = session.get(GlobalLimits, 1)
        assert limits is not None
        limits.max_cloud_projects = value
        session.commit()


def _set_override(engine, user_id, value: int | None) -> None:
    with Session(engine) as session:
        row = session.get(UserLimitOverrides, user_id)
        if row is None:
            row = UserLimitOverrides(user_id=user_id, max_cloud_projects_override=value)
            session.add(row)
        else:
            row.max_cloud_projects_override = value
        session.commit()


def _limits(client, access_token: str):
    return client.get('/api/v1/account/limits', headers={'Authorization': f'Bearer {access_token}'})


def test_c5_migration_chain_downgrade_and_existing_c4_data(migrated_database, monkeypatch):
    monkeypatch.setenv('NFPROGRESS_DATABASE_URL', _database_url())
    config = AlembicConfig(str(ROOT / 'alembic.ini'))
    command.downgrade(config, 'base')
    for revision in (
            'c1_postgresql_foundation', 'c2_account_auth_core',
            'c3_email_account_recovery', 'c4_registration_controls',
    ):
        command.upgrade(config, revision)
    user_id = create_user(migrated_database)
    with migrated_database.begin() as connection:
        connection.execute(text("UPDATE registration_settings SET mode = 'open', max_users = 7 WHERE id = 1"))

    command.upgrade(config, 'c5_limits_framework')
    with Session(migrated_database) as session:
        assert session.get(User, user_id) is not None
        assert session.execute(text('SELECT mode, max_users FROM registration_settings')).one() == ('open', 7)
        assert session.get(GlobalLimits, 1).max_cloud_projects == 20
        assert LimitsService().effective_for_user(session, user_id).max_cloud_projects == 20

    command.downgrade(config, 'c4_registration_controls')
    assert 'global_limits' not in inspect(migrated_database).get_table_names()
    assert 'user_limit_overrides' not in inspect(migrated_database).get_table_names()
    with Session(migrated_database) as session:
        assert session.get(User, user_id) is not None
        assert session.execute(text('SELECT mode, max_users FROM registration_settings')).one() == ('open', 7)
    command.upgrade(config, 'c5_limits_framework')
    command.upgrade(config, 'head')
    with Session(migrated_database) as session:
        assert session.get(GlobalLimits, 1).max_cloud_projects == 20


def test_effective_limits_default_override_clear_global_change_and_isolation(migrated_database):
    first_id = create_user(migrated_database, username='First', email='first@example.test')
    second_id = create_user(migrated_database, username='Second', email='second@example.test')
    service = LimitsService()
    with Session(migrated_database) as session:
        assert session.get(GlobalLimits, 1).max_cloud_projects == 20
        assert service.effective_for_user(session, first_id).max_cloud_projects == 20
        assert service.effective_for_user(session, second_id).max_cloud_projects == 20
    _set_override(migrated_database, second_id, 50)
    _set_global(migrated_database, 30)
    with Session(migrated_database) as session:
        assert service.effective_for_user(session, first_id).max_cloud_projects == 30
        assert service.effective_for_user(session, second_id).max_cloud_projects == 50
    _set_override(migrated_database, second_id, None)
    with Session(migrated_database) as session:
        assert service.effective_for_user(session, second_id).max_cloud_projects == 30
    _set_override(migrated_database, second_id, 0)
    with Session(migrated_database) as session:
        assert service.effective_for_user(session, second_id).max_cloud_projects == 0
        assert service.effective_for_user(session, first_id).max_cloud_projects == 30


def test_c5_postgresql_constraints_and_user_delete_cascade(migrated_database):
    user_id = create_user(migrated_database)
    with Session(migrated_database) as session:
        global_limits = session.get(GlobalLimits, 1)
        assert global_limits is not None
        global_limits.max_cloud_projects = -1
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        session.add(UserLimitOverrides(user_id=user_id, max_cloud_projects_override=-1))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        session.add(UserLimitOverrides(user_id=user_id, max_cloud_projects_override=0))
        session.commit()
        session.add(UserLimitOverrides(user_id=user_id, max_cloud_projects_override=5))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        session.execute(text('UPDATE global_limits SET max_cloud_projects = 0 WHERE id = 1'))
        session.commit()
        assert session.get(GlobalLimits, 1).max_cloud_projects == 0
        with pytest.raises(IntegrityError):
            session.execute(text('INSERT INTO global_limits (id, max_cloud_projects) VALUES (2, 1)'))
        session.rollback()
        with pytest.raises(IntegrityError):
            session.execute(text(
                "INSERT INTO user_limit_overrides (user_id, max_cloud_projects_override) "
                "VALUES ('00000000-0000-0000-0000-000000000001', 1)",
            ))
        session.rollback()
    with Session(migrated_database) as session:
        user = session.get(User, user_id)
        session.delete(user)
        session.commit()
    with Session(migrated_database) as session:
        assert session.get(UserLimitOverrides, user_id) is None
        assert session.get(GlobalLimits, 1) is not None


def test_limits_endpoint_uses_authenticated_identity_and_sanitizes_missing_global(cloud_client):
    client, engine = cloud_client
    first_id = create_user(engine, username='First', email='first@example.test')
    second_id = create_user(engine, username='Second', email='second@example.test')
    first = login(client, 'First').json()['access_token']
    second = login(client, 'Second').json()['access_token']
    assert client.get('/api/v1/account/limits').status_code == 401
    assert _limits(client, first).json() == {'max_cloud_projects': 20}
    _set_override(engine, second_id, 50)
    assert _limits(client, first).json() == {'max_cloud_projects': 20}
    assert _limits(client, second).json() == {'max_cloud_projects': 50}
    _set_global(engine, 30)
    assert _limits(client, first).json() == {'max_cloud_projects': 30}
    _set_override(engine, second_id, None)
    assert _limits(client, second).json() == {'max_cloud_projects': 30}
    assert client.get(f'/api/v1/account/limits?user_id={first_id}', headers={
        'Authorization': f'Bearer {second}',
    }).json() == {'max_cloud_projects': 30}
    with engine.begin() as connection:
        connection.execute(text('DELETE FROM global_limits WHERE id = 1'))
    unavailable = _limits(client, first)
    assert unavailable.status_code == 503
    assert unavailable.json() == {'detail': {
        'code': 'limits_unavailable', 'message': 'Limits are temporarily unavailable.',
    }}
