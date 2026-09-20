from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.cloud.models import CloudProject, GlobalLimits, User, UserLimitOverrides
from backend.app.cloud.services import CloudProjectLimitError, CloudProjectService
from test_cloud_auth import ROOT, _database_url, cloud_client, create_user, login, migrated_database


def _headers(token: str) -> dict[str, str]:
    return {'Authorization': f'Bearer {token}'}


def _enable(client, token: str, project_id: str, **kwargs):
    return client.post(f'/api/v1/cloud/projects/{project_id}', headers=_headers(token), **kwargs)


def _set_global(engine, value: int) -> None:
    with Session(engine) as session:
        row = session.get(GlobalLimits, 1)
        assert row is not None
        row.max_cloud_projects = value
        session.commit()


def _set_override(engine, user_id, value: int | None) -> None:
    with Session(engine) as session:
        row = session.get(UserLimitOverrides, user_id)
        if row is None:
            session.add(UserLimitOverrides(user_id=user_id, max_cloud_projects_override=value))
        else:
            row.max_cloud_projects_override = value
        session.commit()


def test_cloud_project_api_ownership_quota_idempotency_and_no_content(cloud_client):
    client, engine = cloud_client
    first_id = create_user(engine, username='First', email='first@example.test')
    second_id = create_user(engine, username='Second', email='second@example.test')
    first, second = login(client, 'First').json()['access_token'], login(client, 'Second').json()['access_token']

    assert client.get('/api/v1/cloud/projects').status_code == 401
    assert _enable(client, first, 'project-a', json={'name': 'plaintext must not be accepted'}).json() == {'detail': {
        'code': 'cloud_project_content_not_accepted',
        'message': 'Cloud project content is not accepted by this API.',
    }}
    first_enabled = _enable(client, first, 'project-a')
    assert first_enabled.status_code == 200
    assert first_enabled.json() == {
        'cloud_project_ids': ['project-a'], 'cloud_project_count': 1, 'max_cloud_projects': 20,
    }
    assert _enable(client, first, 'project-a').json()['cloud_project_count'] == 1
    assert client.get('/api/v1/cloud/projects', headers=_headers(second)).json() == {
        'cloud_project_ids': [], 'cloud_project_count': 0, 'max_cloud_projects': 20,
    }
    # user_id is neither an input authority nor a response field.
    second_enabled = client.post('/api/v1/cloud/projects/project-b', params={'user_id': str(first_id)},
                                 headers=_headers(second))
    assert second_enabled.status_code == 200
    assert second_enabled.json()['cloud_project_ids'] == ['project-b']
    with Session(engine) as session:
        assert session.get(CloudProject, (first_id, 'project-a')) is not None
        assert session.get(CloudProject, (second_id, 'project-a')) is None
        assert session.execute(text('SELECT project_id FROM cloud_projects')).scalars().all() == ['project-a', 'project-b']


def test_cloud_project_limits_zero_inherit_exact_limit_and_disable(cloud_client):
    client, engine = cloud_client
    user_id = create_user(engine)
    token = login(client).json()['access_token']
    _set_global(engine, 2)
    assert _enable(client, token, 'one').status_code == 200
    assert _enable(client, token, 'two').status_code == 200
    reached = _enable(client, token, 'three')
    assert reached.status_code == 409 and reached.json()['detail']['code'] == 'cloud_project_limit_reached'
    assert client.delete('/api/v1/cloud/projects/one', headers=_headers(token)).status_code == 204
    assert client.delete('/api/v1/cloud/projects/one', headers=_headers(token)).status_code == 204
    assert _enable(client, token, 'three').status_code == 200
    _set_override(engine, user_id, 0)
    assert _enable(client, token, 'four').status_code == 409
    _set_override(engine, user_id, None)
    assert client.get('/api/v1/cloud/projects', headers=_headers(token)).json()['max_cloud_projects'] == 2
    _set_override(engine, user_id, 3)
    assert client.get('/api/v1/cloud/projects', headers=_headers(token)).json()['max_cloud_projects'] == 3
    _set_override(engine, user_id, None)


def test_lowered_limit_preserves_rows_and_existing_enable_stays_idempotent(cloud_client):
    client, engine = cloud_client
    create_user(engine)
    token = login(client).json()['access_token']
    _set_global(engine, 3)
    for project_id in ('one', 'two', 'three'):
        assert _enable(client, token, project_id).status_code == 200
    _set_global(engine, 1)
    state = client.get('/api/v1/cloud/projects', headers=_headers(token)).json()
    assert state['cloud_project_count'] == 3 and state['max_cloud_projects'] == 1
    assert _enable(client, token, 'one').status_code == 200
    assert _enable(client, token, 'four').json()['detail']['code'] == 'cloud_project_limit_reached'


def test_cloud_project_constraints_cascade_missing_limits_and_migration_roundtrip(migrated_database, monkeypatch):
    monkeypatch.setenv('NFPROGRESS_DATABASE_URL', _database_url())
    config = AlembicConfig(str(ROOT / 'alembic.ini'))
    user_id = create_user(migrated_database)
    with Session(migrated_database) as session:
        session.add(CloudProject(user_id=user_id, project_id='kept-id'))
        session.commit()
        session.add(CloudProject(user_id=user_id, project_id=''))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
    command.downgrade(config, 'c6_reserved_usernames')
    assert 'cloud_projects' not in inspect(migrated_database).get_table_names()
    with Session(migrated_database) as session:
        assert session.get(User, user_id) is not None
        assert session.get(GlobalLimits, 1) is not None
    command.upgrade(config, 'head')
    with Session(migrated_database) as session:
        assert session.scalar(select(func.count()).select_from(CloudProject)) == 0
        user = session.get(User, user_id)
        assert user is not None
        session.add(CloudProject(user_id=user_id, project_id='cascade'))
        session.commit()
        session.delete(user)
        session.commit()
        assert session.get(CloudProject, (user_id, 'cascade')) is None


def test_missing_limits_is_sanitized_for_registry(cloud_client):
    client, engine = cloud_client
    create_user(engine)
    token = login(client).json()['access_token']
    with engine.begin() as connection:
        connection.execute(text('DELETE FROM global_limits WHERE id = 1'))
    response = client.get('/api/v1/cloud/projects', headers=_headers(token))
    assert response.status_code == 503 and response.json()['detail']['code'] == 'limits_unavailable'
    assert _enable(client, token, 'project-a').status_code == 503


def test_concurrent_enable_respects_final_cloud_slot(migrated_database):
    user_id = create_user(migrated_database)
    _set_global(migrated_database, 1)
    barrier = threading.Barrier(2)

    def enable(project_id: str) -> str:
        with Session(migrated_database) as session:
            barrier.wait(timeout=10)
            try:
                CloudProjectService().enable(session, user_id, project_id)
                return 'enabled'
            except CloudProjectLimitError:
                return 'limit_reached'

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(enable, ('concurrent-a', 'concurrent-b')))
    assert sorted(outcomes) == ['enabled', 'limit_reached']
    with Session(migrated_database) as session:
        assert session.scalar(select(func.count()).select_from(CloudProject).where(
            CloudProject.user_id == user_id,
        )) == 1
