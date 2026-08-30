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
        project = client.post('/api/projects', json={'name': 'Роман', 'goal': 1000}).json()
        document = {'type': 'doc', 'content': [{'type': 'paragraph', 'content': [{'type': 'text', 'text': 'Черновик'}]}]}
        saved = client.put(f"/api/documents/{project['id']}", json={'content': document})
        assert saved.status_code == 200
        assert saved.json()['content'] == document

        path = tmp_path / 'roman.docx'
        assert client.put(f"/api/documents/{project['id']}/link", json={'path': str(path)}).status_code == 200
        payload = base64.b64encode(b'word-v1').decode('ascii')
        assert client.put(f"/api/documents/{project['id']}/docx", json={'content_base64': payload}).status_code == 200
        assert client.get(f"/api/documents/{project['id']}/external").json()['state'] == 'synced'

        path.write_bytes(b'word-v2')
        external = client.get(f"/api/documents/{project['id']}/external").json()
        assert external['state'] == 'word_changed'
        assert external['content_base64'] == base64.b64encode(b'word-v2').decode('ascii')
