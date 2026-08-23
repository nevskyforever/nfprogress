from fastapi.testclient import TestClient

from backend.app.config import RuntimeConfig
from backend.app.main import create_app


def _response_schema(openapi: dict, path: str, method: str, status: str) -> dict:
    return openapi['paths'][path][method]['responses'][status][
        'content'
    ]['application/json']['schema']


def test_openapi_exposes_structured_content_settings_and_notes_contracts(tmp_path):
    app = create_app(RuntimeConfig(
        data_dir=tmp_path,
        session_token='contract-token',
        platform='web',
    ))
    openapi = app.openapi()
    schemas = openapi['components']['schemas']

    languages = _response_schema(
        openapi, '/api/content/languages', 'get', '200',
    )
    assert languages['items']['$ref'].endswith('/LanguageOptionResponse')
    assert schemas['LanguageOptionResponse']['properties']['code']['enum'] == [
        'ru', 'en', 'es', 'de', 'fr', 'pt_BR',
    ]

    help_sections = _response_schema(
        openapi, '/api/content/help', 'get', '200',
    )
    assert help_sections['items']['$ref'].endswith('/HelpSectionResponse')
    assert schemas['HelpSectionResponse']['properties']['children']['items'][
        '$ref'
    ].endswith('/HelpSectionResponse')

    settings_ref = _response_schema(
        openapi, '/api/settings', 'get', '200',
    )['$ref']
    assert settings_ref.endswith('/SettingsResponse')
    assert set(schemas['PlatformCapabilitiesResponse']['properties']) == {
        'local_file_sync',
        'background_file_sync',
        'native_updates',
        'remote_api',
    }

    expected_response_models = {
        ('/api/projects/streaks/global', 'get', '200'):
            'GlobalStreakSummaryResponse',
        ('/api/projects/{project_id}/notes', 'get', '200'):
            'NotesListResponse',
        ('/api/projects/{project_id}/notes', 'post', '201'):
            'ProjectNoteResponse',
        ('/api/projects/{project_id}/notes/{note_id}', 'get', '200'):
            'ProjectNoteResponse',
        ('/api/projects/{project_id}/notes/order', 'put', '200'):
            'NoteOrderResponse',
        ('/api/projects/{project_id}/mindmap', 'get', '200'):
            'MindMapResponse',
        ('/api/projects/{project_id}/mindmap', 'put', '200'):
            'MindMapUpdateResponse',
    }
    for (path, method, status), model_name in expected_response_models.items():
        schema = _response_schema(openapi, path, method, status)
        assert schema['$ref'].endswith(f'/{model_name}')

    note_properties = schemas['ProjectNoteResponse']['properties']
    assert note_properties['checklist']['items']['$ref'].endswith(
        '/NoteChecklistItemResponse',
    )
    assert note_properties['source_type']['enum'] == ['project', 'mindmap']
    assert schemas['NotesListResponse']['properties']['context'][
        '$ref'
    ].endswith('/NotesViewContextResponse')
    assert 'notes' not in schemas['MindMapResponse']['properties']
    assert schemas['MindMapUpdateResponse']['properties']['notes']['items'][
        '$ref'
    ].endswith('/ProjectNoteResponse')


def test_typed_models_preserve_existing_notes_and_mindmap_payloads(tmp_path):
    app = create_app(RuntimeConfig(
        data_dir=tmp_path,
        session_token='contract-token',
        platform='web',
    ))
    headers = {'X-NFProgress-Token': 'contract-token'}

    with TestClient(app, headers=headers) as client:
        project = client.post('/api/projects', json={
            'name': 'Contract project',
            'goal': 1_000,
            'unit': 'symbols',
        }).json()
        note = client.post(
            f"/api/projects/{project['id']}/notes",
        ).json()
        updated_note = client.patch(
            f"/api/projects/{project['id']}/notes/{note['id']}",
            json={
                'checklist': [{
                    'id': 'check-1',
                    'text': 'Structured item',
                    'checked': True,
                }],
            },
        )
        assert updated_note.status_code == 200, updated_note.text
        assert updated_note.json()['checklist'] == [{
            'id': 'check-1',
            'text': 'Structured item',
            'checked': True,
        }]

        mindmap = client.get(
            f"/api/projects/{project['id']}/mindmap",
        )
        assert mindmap.status_code == 200, mindmap.text
        assert 'notes' not in mindmap.json()

        saved = client.put(
            f"/api/projects/{project['id']}/mindmap",
            json={'data': {
                'nodeData': {
                    'id': 'root',
                    'topic': 'Contract map',
                    'children': [],
                    'pluginField': {'enabled': True},
                },
            }},
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()['data']['nodeData']['pluginField'] == {
            'enabled': True,
        }
        assert isinstance(saved.json()['notes'], list)
