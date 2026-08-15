from __future__ import annotations

from io import BytesIO

import pytest
from docx import Document

from nfprogress.core.errors import ValidationError
from nfprogress.core.repositories.storage import PickleRepository
from nfprogress.core.services.integrations import DocumentIntegrationService
from nfprogress.core.services.projects import ProjectService


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
