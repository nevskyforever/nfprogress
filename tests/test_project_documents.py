from __future__ import annotations

import base64

from fastapi.testclient import TestClient

from backend.app.config import RuntimeConfig
from backend.app.main import create_app


def test_document_autosave_and_linked_word_change_are_tracked(tmp_path):
    app = create_app(RuntimeConfig(
        data_dir=tmp_path, platform='desktop', allow_local_files=True,
    ))
    with TestClient(app) as client:
        project = client.post(
            '/api/projects', json={'name': 'Роман', 'goal': 1000, 'work_method': 'app'},
        ).json()
        document = {'type': 'doc', 'content': [{'type': 'paragraph', 'content': [{'type': 'text', 'text': 'Черновик'}]}]}
        saved = client.put(f"/api/documents/{project['id']}", json={'content': document})
        assert saved.status_code == 200
        assert saved.json()['content'] == document
        documents = client.get('/api/documents/list')
        assert documents.status_code == 200
        assert documents.json()[0]['project_id'] == project['id']
        assert documents.json()[0]['symbols'] == len('Черновик')
        assert documents.json()[0]['has_content'] is True

        path = tmp_path / 'roman.docx'
        assert client.put(f"/api/documents/{project['id']}/link", json={'path': str(path)}).status_code == 200
        payload = base64.b64encode(b'word-v1').decode('ascii')
        assert client.put(f"/api/documents/{project['id']}/docx", json={'content_base64': payload}).status_code == 200
        assert client.get(f"/api/documents/{project['id']}/external").json()['state'] == 'synced'

        path.write_bytes(b'word-v2')
        external = client.get(f"/api/documents/{project['id']}/external").json()
        assert external['state'] == 'word_changed'
        assert external['content_base64'] == base64.b64encode(b'word-v2').decode('ascii')


def test_text_progress_uses_document_symbols_and_document_scope_rules(tmp_path):
    app = create_app(RuntimeConfig(data_dir=tmp_path, platform='desktop', allow_local_files=True))
    with TestClient(app) as client:
        project = client.post(
            '/api/projects', json={'name': 'Роман', 'goal': 1000, 'work_method': 'app'},
        ).json()
        content = {'type': 'doc', 'content': [{'type': 'paragraph', 'content': [{'type': 'text', 'text': 'Текст'}]}]}
        assert client.put(f"/api/documents/{project['id']}", json={'content': content}).status_code == 200
        progress = client.post(f"/api/documents/{project['id']}/progress")
        assert progress.status_code == 200, progress.text
        assert progress.json()['progress']['added_symbols'] == len('Текст')

        created_staged_project = client.post(
            '/api/projects', json={'name': 'С этапами', 'goal': 1000},
        ).json()
        client.post(
            f"/api/projects/{created_staged_project['id']}/stages",
            json={'name': 'Этап', 'goal': 1000, 'work_method': 'app'},
        )
        staged_project = client.get(
            f"/api/projects/{created_staged_project['id']}",
        ).json()
        stage = staged_project['stages'][0]
        assert client.get(f"/api/documents/{staged_project['id']}").status_code == 422
        assert client.put(
            f"/api/documents/{staged_project['id']}", params={'stage_id': stage['id']},
            json={'content': content},
        ).status_code == 200


def test_work_methods_keep_existing_data_and_gate_record_sources(tmp_path):
    app = create_app(RuntimeConfig(data_dir=tmp_path, platform='desktop', allow_local_files=True))
    content = {'type': 'doc', 'content': [{'type': 'paragraph', 'content': [{'type': 'text', 'text': 'Текст'}]}]}
    with TestClient(app) as client:
        project = client.post('/api/projects', json={'name': 'Роман', 'goal': 1000}).json()
        assert project['work_method'] == 'manual'
        assert client.post(f"/api/projects/{project['id']}/progress", json={'new_total': 1}).status_code == 200
        assert client.put(f"/api/documents/{project['id']}", json={'content': content}).status_code == 422

        app_project = client.patch(
            f"/api/projects/{project['id']}", json={'work_method': 'app'},
        ).json()
        assert app_project['work_method'] == 'app'
        assert client.put(f"/api/documents/{project['id']}", json={'content': content}).status_code == 200
        assert client.post(f"/api/projects/{project['id']}/progress", json={'new_total': 20}).status_code == 422

        restored = client.patch(
            f"/api/projects/{project['id']}", json={'work_method': 'manual'},
        ).json()
        assert restored['work_method'] == 'manual'
        assert client.get(f"/api/documents/{project['id']}").status_code == 422
