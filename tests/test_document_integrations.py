from __future__ import annotations

import os
from datetime import datetime, timedelta
from io import BytesIO

import pytest
from docx import Document
from fastapi.testclient import TestClient

from backend.app.config import RuntimeConfig
from backend.app.main import create_app
from nfprogress.core.errors import ConflictError, NotFoundError, ValidationError
from nfprogress.core.repositories.storage import PickleRepository
from nfprogress.core.services.integrations import DocumentIntegrationService
from nfprogress.core.services.projects import ProjectService
from nfprogress.core.services.settings import SettingsService


def _docx_bytes(text: str) -> bytes:
    document = Document()
    document.add_paragraph(text)
    stream = BytesIO()
    document.save(stream)
    return stream.getvalue()


def test_uploaded_word_document_is_counted_without_persisting_manuscript():
    content = _docx_bytes('Три слова здесь')
    assert DocumentIntegrationService.count_uploaded_docx(content, 'book.docx') == 15


def test_uploaded_word_document_must_be_a_bounded_zip_container():
    with pytest.raises(ValidationError, match='повреждён'):
        DocumentIntegrationService.count_uploaded_docx(b'not-a-zip', 'book.docx')


def test_uploaded_word_document_routes_progress_through_project_service(tmp_path):
    repository = PickleRepository(tmp_path)
    projects = ProjectService(repository)
    project = projects.create_project({
        'name': 'Book', 'goal': 100, 'unit': 'symbols',
    })
    service = DocumentIntegrationService(repository, projects)

    imported = service.apply_uploaded_docx(
        project['id'], _docx_bytes('1234567890'), 'book.docx',
    )

    assert imported['changed'] is True
    assert imported['symbols'] == 10
    assert imported['progress']['added_symbols'] == 10
    assert imported['project']['total'] == 10
    repeated = service.apply_uploaded_docx(
        project['id'], _docx_bytes('1234567890'), 'book.docx',
    )
    assert repeated['changed'] is False
    assert repeated['progress'] is None


def test_local_file_configuration_is_desktop_only(tmp_path):
    repository = PickleRepository(tmp_path)
    projects = ProjectService(repository)
    project = projects.create_project({'name': 'Book', 'goal': 100, 'unit': 'symbols'})
    service = DocumentIntegrationService(repository, projects, allow_local_files=False)

    with pytest.raises(ValidationError, match='desktop'):
        service.configure_sync(
            project['id'], sync_type='word', path=str(tmp_path / 'book.docx'),
        )


def test_desktop_word_sync_routes_delta_through_progress_service(tmp_path):
    path = tmp_path / 'book.docx'
    path.write_bytes(_docx_bytes('1234567890'))
    repository = PickleRepository(tmp_path / 'data')
    projects = ProjectService(repository)
    project = projects.create_project({'name': 'Book', 'goal': 100, 'unit': 'symbols'})
    service = DocumentIntegrationService(repository, projects, allow_local_files=True)

    service.configure_sync(project['id'], sync_type='word', path=str(path))
    result = service.run_sync(project['id'])

    assert result['changed'] is True
    assert result['symbols'] == 10
    assert result['progress']['added_symbols'] == 10
    assert result['sync']['last_synced_at']

    web = DocumentIntegrationService(
        repository, projects, allow_local_files=False,
    )
    assert web.get_sync(project['id'])['path'] is None
    with pytest.raises(ValidationError, match='desktop'):
        web.remove_sync(project['id'])


def test_desktop_batch_sync_isolates_source_failures(tmp_path):
    good_path = tmp_path / 'good.docx'
    good_path.write_bytes(_docx_bytes('1234567890'))
    missing_path = tmp_path / 'missing.docx'
    repository = PickleRepository(tmp_path / 'data')
    projects = ProjectService(repository)
    good = projects.create_project({'name': 'Good', 'goal': 100, 'unit': 'symbols'})
    missing = projects.create_project({'name': 'Missing', 'goal': 100, 'unit': 'symbols'})
    service = DocumentIntegrationService(repository, projects, allow_local_files=True)
    service.configure_sync(good['id'], sync_type='word', path=str(good_path))
    data = repository.read_projects()
    missing_project = next(
        item for item in data['projects'].values()
        if item.project_id == missing['id']
    )
    missing_project.synch = {'type': 'word', 'path': str(missing_path)}
    repository.write_projects(data)

    result = service.sync_all_configured()

    assert result['checked'] == 2
    assert result['changed'] == 1
    assert result['failed'] == 1
    assert [item['ok'] for item in result['items']] == [True, False]


def test_desktop_capabilities_match_background_runtime(tmp_path):
    desktop = SettingsService(
        PickleRepository(tmp_path), platform='desktop',
    ).get()

    assert desktop['values']['background_synch'] is True
    assert desktop['capabilities']['background_file_sync'] is True
    assert desktop['capabilities']['native_updates'] is False
    assert 'check_updates' not in desktop['editable_keys']


def test_scrivener_inspection_preserves_nested_binder_tree(tmp_path):
    project_path = tmp_path / 'book.scriv'
    project_path.mkdir()
    (project_path / 'project.scrivx').write_text(
        '''<?xml version="1.0" encoding="UTF-8"?>
        <ScrivenerProject><Binder>
          <BinderItem UUID="draft"><Title>Черновик</Title><Children>
            <BinderItem UUID="chapter"><Title>Глава 1</Title></BinderItem>
          </Children></BinderItem>
        </Binder></ScrivenerProject>''',
        encoding='utf-8',
    )
    repository = PickleRepository(tmp_path / 'data')
    service = DocumentIntegrationService(
        repository, ProjectService(repository), allow_local_files=True,
    )

    items = service.inspect_scrivener(str(project_path))

    assert items == [{
        'id': 'draft',
        'title': 'Черновик',
        'children': [{
            'id': 'chapter',
            'title': 'Глава 1',
            'children': [],
        }],
    }]


def test_scrivener_sync_rejects_unknown_or_stale_binder_item(tmp_path):
    project_path = tmp_path / 'book.scriv'
    project_path.mkdir()
    (project_path / 'project.scrivx').write_text(
        '''<?xml version="1.0" encoding="UTF-8"?>
        <ScrivenerProject><Binder>
          <BinderItem UUID="chapter"><Title>Глава</Title></BinderItem>
        </Binder></ScrivenerProject>''',
        encoding='utf-8',
    )
    repository = PickleRepository(tmp_path / 'data')
    projects = ProjectService(repository)
    project = projects.create_project({
        'name': 'Book', 'goal': 100, 'total': 10, 'unit': 'symbols',
    })
    service = DocumentIntegrationService(
        repository, projects, allow_local_files=True,
    )

    with pytest.raises(ValidationError, match='не найден в проекте'):
        service.configure_sync(
            project['id'], sync_type='scrivener', path=str(project_path),
            item_id='invented',
        )

    data = repository.read_projects()
    stored = next(iter(data['projects'].values()))
    stored.synch = {
        'type': 'scrivener', 'path': str(project_path), 'item_id': 'removed',
    }
    repository.write_projects(data)

    with pytest.raises(ConflictError) as stale:
        service.run_sync(project['id'])
    assert stale.value.code == 'sync_source_stale'
    assert projects.get_project(project['id'])['total'] == 10


def test_direct_sync_uses_upload_rounding_tolerance(tmp_path):
    path = tmp_path / 'book.docx'
    path.write_bytes(_docx_bytes('1234567890'))
    repository = PickleRepository(tmp_path / 'data')
    projects = ProjectService(repository)
    project = projects.create_project({
        'name': 'Book', 'goal': 100, 'unit': 'symbols',
    })
    data = repository.read_projects()
    stored = next(iter(data['projects'].values()))
    stored.total_units = 10.005
    repository.write_projects(data)
    service = DocumentIntegrationService(
        repository, projects, allow_local_files=True,
    )
    service.configure_sync(project['id'], sync_type='word', path=str(path))

    result = service.run_sync(project['id'])

    assert result['changed'] is False
    assert result['progress'] is None
    assert projects.get_project(project['id'])['progress_entries'] == []


def test_direct_sync_preserves_source_mtime_on_progress_entry(tmp_path):
    path = tmp_path / 'book.docx'
    path.write_bytes(_docx_bytes('1234567890'))
    source_time = datetime.now() - timedelta(hours=2)
    os.utime(path, (source_time.timestamp(), source_time.timestamp()))
    repository = PickleRepository(tmp_path / 'data')
    projects = ProjectService(repository)
    project = projects.create_project({
        'name': 'Book', 'goal': 100, 'unit': 'symbols',
    })
    service = DocumentIntegrationService(
        repository, projects, allow_local_files=True,
    )
    service.configure_sync(project['id'], sync_type='word', path=str(path))

    result = service.run_sync(project['id'])

    created_at = datetime.fromisoformat(result['progress']['entry']['created_at'])
    assert abs((created_at - source_time).total_seconds()) < 0.01


def test_stale_or_missing_word_source_never_overwrites_progress(tmp_path):
    path = tmp_path / 'book.docx'
    path.write_bytes(_docx_bytes('1234567890'))
    repository = PickleRepository(tmp_path / 'data')
    projects = ProjectService(repository)
    project = projects.create_project({
        'name': 'Book', 'goal': 100, 'unit': 'symbols',
    })
    service = DocumentIntegrationService(
        repository, projects, allow_local_files=True,
    )
    service.configure_sync(project['id'], sync_type='word', path=str(path))
    service.run_sync(project['id'])
    projects.record_synchronized_progress(
        project['id'], new_total=20, source_modified_at=datetime.now(),
    )

    with pytest.raises(ConflictError) as stale:
        service.run_sync(project['id'])
    assert stale.value.code == 'sync_source_stale'
    assert projects.get_project(project['id'])['total'] == 20

    path.unlink()
    with pytest.raises(NotFoundError) as missing:
        service.run_sync(project['id'])
    assert missing.value.code == 'sync_source_missing'
    saved = service.get_sync(project['id'])
    assert saved['configured'] is True
    assert projects.get_project(project['id'])['total'] == 20


def test_future_source_timestamp_is_rejected_without_a_progress_entry(tmp_path):
    path = tmp_path / 'book.docx'
    path.write_bytes(_docx_bytes('1234567890'))
    future = datetime.now() + timedelta(days=1)
    os.utime(path, (future.timestamp(), future.timestamp()))
    repository = PickleRepository(tmp_path / 'data')
    projects = ProjectService(repository)
    project = projects.create_project({
        'name': 'Book', 'goal': 100, 'unit': 'symbols',
    })
    service = DocumentIntegrationService(
        repository, projects, allow_local_files=True,
    )
    service.configure_sync(project['id'], sync_type='word', path=str(path))

    with pytest.raises(ValidationError) as invalid:
        service.run_sync(project['id'])

    assert invalid.value.code == 'sync_source_timestamp_invalid'
    current = projects.get_project(project['id'])
    assert current['total'] == 0
    assert current['progress_entries'] == []


def test_synchronized_progress_rejects_invalid_or_out_of_order_timestamp(tmp_path):
    repository = PickleRepository(tmp_path / 'data')
    projects = ProjectService(repository)
    project = projects.create_project({
        'name': 'Book', 'goal': 100, 'unit': 'symbols',
    })
    projects.record_progress(project['id'], new_total=10)

    with pytest.raises(ValidationError) as invalid:
        projects.record_synchronized_progress(
            project['id'],
            new_total=20,
            source_modified_at='not-a-datetime',
        )
    assert invalid.value.code == 'sync_source_timestamp_invalid'

    with pytest.raises(ConflictError) as stale:
        projects.record_synchronized_progress(
            project['id'],
            new_total=20,
            source_modified_at=datetime.now() - timedelta(days=1),
        )
    assert stale.value.code == 'sync_source_stale'
    current = projects.get_project(project['id'])
    assert current['total'] == 10
    assert len(current['progress_entries']) == 1


def test_scrivener_binder_item_without_content_cannot_reset_progress(tmp_path):
    project_path = tmp_path / 'book.scriv'
    project_path.mkdir()
    (project_path / 'project.scrivx').write_text(
        '''<?xml version="1.0" encoding="UTF-8"?>
        <ScrivenerProject><Binder>
          <BinderItem UUID="chapter"><Title>Глава</Title></BinderItem>
        </Binder></ScrivenerProject>''',
        encoding='utf-8',
    )
    repository = PickleRepository(tmp_path / 'data')
    projects = ProjectService(repository)
    project = projects.create_project({
        'name': 'Book', 'goal': 100, 'total': 10, 'unit': 'symbols',
    })
    service = DocumentIntegrationService(
        repository, projects, allow_local_files=True,
    )
    service.configure_sync(
        project['id'], sync_type='scrivener', path=str(project_path),
        item_id='chapter',
    )

    with pytest.raises(ConflictError) as stale:
        service.run_sync(project['id'])

    assert stale.value.code == 'sync_source_stale'
    assert projects.get_project(project['id'])['total'] == 10


def test_scrivener_sync_reads_selected_rtf_and_preserves_mtime(tmp_path):
    project_path = tmp_path / 'book.scriv'
    content_path = project_path / 'Files' / 'Data' / 'chapter' / 'Data.rtf'
    content_path.parent.mkdir(parents=True)
    content_path.write_text(r'{\rtf1\ansi 1234567890}', encoding='utf-8')
    xml_path = project_path / 'project.scrivx'
    xml_path.write_text(
        '''<?xml version="1.0" encoding="UTF-8"?>
        <ScrivenerProject><Binder>
          <BinderItem UUID="chapter"><Title>Глава</Title></BinderItem>
        </Binder></ScrivenerProject>''',
        encoding='utf-8',
    )
    source_time = datetime.now() - timedelta(hours=2)
    for path in (content_path, xml_path):
        os.utime(path, (source_time.timestamp(), source_time.timestamp()))
    repository = PickleRepository(tmp_path / 'data')
    projects = ProjectService(repository)
    project = projects.create_project({
        'name': 'Book', 'goal': 100, 'unit': 'symbols',
    })
    service = DocumentIntegrationService(
        repository, projects, allow_local_files=True,
    )
    service.configure_sync(
        project['id'], sync_type='scrivener', path=str(project_path),
        item_id='{CHAPTER}',
    )

    result = service.run_sync(project['id'])

    assert result['changed'] is True
    assert result['symbols'] == 10
    created_at = datetime.fromisoformat(result['progress']['entry']['created_at'])
    assert abs((created_at - source_time).total_seconds()) < 0.01


def test_remove_all_syncs_matches_legacy_stage_workflow(tmp_path):
    repository = PickleRepository(tmp_path / 'data')
    projects = ProjectService(repository)
    project = projects.create_project({
        'name': 'Book',
        'goal': 200,
        'unit': 'symbols',
        'stages': [
            {'name': 'One', 'goal': 100},
            {'name': 'Two', 'goal': 100},
        ],
    })
    data = repository.read_projects()
    stored = next(iter(data['projects'].values()))
    for stage in stored.stages:
        stage.synch = {
            'type': 'word',
            'path': str(tmp_path / f'{stage.stage_id}.docx'),
        }
        stage.last_synch = datetime.now()
    repository.write_projects(data)
    service = DocumentIntegrationService(
        repository, projects, allow_local_files=True,
    )

    removed = service.remove_all_syncs(project['id'])

    assert removed['removed'] == 2
    assert len(removed['syncs']) == 3
    assert all(not item['configured'] for item in removed['syncs'])
    saved = repository.read_projects()
    saved_project = next(iter(saved['projects'].values()))
    assert all(stage.synch is None for stage in saved_project.stages)
    assert all(stage.last_synch is None for stage in saved_project.stages)


def test_project_syncs_preserve_legacy_stage_bindings_and_run_them(tmp_path):
    path = tmp_path / 'book.docx'
    path.write_bytes(_docx_bytes('1234567890'))
    repository = PickleRepository(tmp_path / 'data')
    projects = ProjectService(repository)
    project = projects.create_project({
        'name': 'Book',
        'goal': 200,
        'unit': 'symbols',
        'stages': [
            {'name': 'One', 'goal': 100},
            {'name': 'Two', 'goal': 100},
        ],
    })
    service = DocumentIntegrationService(
        repository, projects, allow_local_files=True,
    )
    synced_stage = project['stages'][1]
    service.configure_sync(
        project['id'],
        sync_type='word',
        path=str(path),
        stage_id=synced_stage['id'],
    )

    summaries = service.get_project_syncs(project['id'])
    result = service.run_project_syncs(project['id'])

    assert len(summaries['syncs']) == 2
    assert [item['stage_id'] for item in summaries['syncs'] if item['configured']] == [
        synced_stage['id'],
    ]
    assert result['checked'] == 1
    assert result['failed'] == 0
    assert result['items'][0]['stage_id'] == synced_stage['id']


def test_sync_errors_and_detach_all_have_typed_api_contracts(tmp_path):
    path = tmp_path / 'book.docx'
    path.write_bytes(_docx_bytes('1234567890'))
    app = create_app(RuntimeConfig(
        data_dir=tmp_path / 'data',
        platform='test',
        allow_local_files=True,
    ))
    with TestClient(app) as client:
        created = client.post('/api/projects', json={
            'name': 'Book',
            'goal': 200,
            'unit': 'symbols',
            'stages': [
                {'name': 'One', 'goal': 100},
                {'name': 'Two', 'goal': 100},
            ],
        }).json()
        for stage in created['stages']:
            configured = client.put(
                f"/api/projects/{created['id']}/sync",
                json={
                    'type': 'word',
                    'path': str(path),
                    'stage_id': stage['id'],
                },
            )
            assert configured.status_code == 200, configured.text

        listed = client.get(f"/api/projects/{created['id']}/sync/all")
        assert listed.status_code == 200, listed.text
        assert [item['stage_id'] for item in listed.json()['syncs']] == [
            stage['id'] for stage in created['stages']
        ]
        assert all(item['configured'] for item in listed.json()['syncs'])

        project_run = client.post(f"/api/projects/{created['id']}/sync/run-all")
        assert project_run.status_code == 200, project_run.text
        assert project_run.json()['checked'] == 2
        assert project_run.json()['failed'] == 0

        path.unlink()
        failed = client.post(
            f"/api/projects/{created['id']}/sync/run",
            params={'stage_id': created['stages'][0]['id']},
        )
        assert failed.status_code == 404
        assert failed.json()['detail']['code'] == 'sync_source_missing'

        detached = client.delete(
            f"/api/projects/{created['id']}/sync/all",
        )
        assert detached.status_code == 200, detached.text
        assert detached.json()['removed'] == 2
        assert all(
            not item['configured'] for item in detached.json()['syncs']
        )
