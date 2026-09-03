from __future__ import annotations

import json
import zipfile
from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from backend.app.config import RuntimeConfig
from backend.app.main import create_app
from nfprogress.core.services.xmind_import import import_xmind


def xmind_zip(name: str, content: str | bytes) -> bytes:
    stream = BytesIO()
    with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name, content)
    return stream.getvalue()


def modern_content() -> bytes:
    return json.dumps([
        {
            'id': 'sheet-id',
            'title': 'План романа',
            'rootTopic': {
                'id': 'xmind-root', 'title': 'Корень',
                'children': {'attached': [
                    {'id': 'one', 'title': 'Первая ветка', 'children': {'attached': [
                        {'id': 'deep', 'title': 'Глубокий узел'},
                    ]}},
                    {'id': 'two', 'title': 'Вторая ветка'},
                ]},
            },
        },
    ], ensure_ascii=False).encode()


def test_modern_json_preserves_tree_order_and_creates_new_ids():
    result = import_xmind(xmind_zip('content.json', modern_content()))[0]
    root = result['data']['nodeData']
    assert result['title'] == 'План романа'
    assert root['topic'] == 'Корень'
    assert [child['topic'] for child in root['children']] == ['Первая ветка', 'Вторая ветка']
    assert root['children'][0]['children'][0]['topic'] == 'Глубокий узел'
    assert root['id'].startswith('xmind-')
    assert root['id'] != 'xmind-root'


def test_old_xml_supports_nested_topics_and_namespaces():
    xml = '''<?xml version="1.0"?><xmap-content xmlns="urn:test"><sheet id="s">
      <topic id="r"><title>Корень XML</title><children><topics type="attached">
        <topic id="a"><title>Ветка</title><children><topics type="attached">
          <topic id="b"><title>Подветка</title></topic>
        </topics></children></topic>
      </topics></children></topic>
    </sheet></xmap-content>'''
    root = import_xmind(xmind_zip('content.xml', xml))[0]['data']['nodeData']
    assert root['topic'] == 'Корень XML'
    assert root['children'][0]['children'][0]['topic'] == 'Подветка'


def test_multiple_sheets_are_returned_in_file_order():
    content = json.dumps([
        {'title': 'Лист 1', 'rootTopic': {'title': 'A'}},
        {'title': 'Лист 2', 'rootTopic': {'title': 'B'}},
    ]).encode()
    assert [item['title'] for item in import_xmind(xmind_zip('content.json', content))] == ['Лист 1', 'Лист 2']


@pytest.mark.parametrize('payload', [b'not zip', b''])
def test_corrupted_zip_is_rejected(payload):
    with pytest.raises(Exception, match='ZIP'):
        import_xmind(payload)


def test_missing_content_is_rejected():
    with pytest.raises(Exception, match='отсутствует'):
        import_xmind(xmind_zip('metadata.json', '{}'))


def test_invalid_json_and_xml_are_rejected():
    with pytest.raises(Exception, match='JSON'):
        import_xmind(xmind_zip('content.json', b'{'))
    with pytest.raises(Exception, match='XML'):
        import_xmind(xmind_zip('content.xml', b'<broken>'))
    with pytest.raises(Exception, match='сущности'):
        import_xmind(xmind_zip('content.xml', b'<!DOCTYPE x [<!ENTITY e "x">]><xmap-content/>'))


def test_empty_map_and_invalid_children_are_rejected():
    with pytest.raises(Exception, match='root topic'):
        import_xmind(xmind_zip('content.json', b'[{"title":"Empty"}]'))
    with pytest.raises(Exception, match='дочерние'):
        import_xmind(xmind_zip('content.json', b'[{"rootTopic":{"title":"R","children":{"attached":{}}}}]'))


def test_api_failed_import_does_not_change_current_map(tmp_path):
    token = 'xmind-test-token'
    app = create_app(RuntimeConfig(data_dir=tmp_path, session_token=token, platform='web'))
    with TestClient(app, headers={'X-NFProgress-Token': token}) as client:
        project = client.post('/api/projects', json={'name': 'Роман', 'goal': 10}).json()
        path = f"/api/projects/{project['id']}/mindmap"
        original = {'nodeData': {'id': 'old', 'topic': 'Старое', 'children': []}}
        assert client.put(path, json={'data': original}).status_code == 200
        response = client.post(
            f"{path}/import/xmind",
            files={'file': ('broken.xmind', b'not zip', 'application/zip')},
        )
        assert response.status_code == 422
        assert client.get(path).json()['data'] == original
