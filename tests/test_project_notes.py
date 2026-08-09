import json
import os
import pickle
import time
import xml.etree.ElementTree as ET
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtWidgets import QApplication

import engine
from mindmap import MindMapDialog
from project_notes import (
    ProjectNotesService,
    ProjectNotesDialog,
    extract_mindmap_notes,
    note_html_to_plain_text,
    remove_mindmap_note,
    sanitize_note_html,
    set_mindmap_note_text,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
requires_native_webview = pytest.mark.skipif(
    os.environ.get('QT_QPA_PLATFORM') == 'offscreen',
    reason='Qt WebView requires a native windowing platform.',
)


@pytest.fixture(scope='module', autouse=True)
def qt_application():
    return QApplication.instance() or QApplication([])


def _map_data(note_id='map-note', text='Текст карты'):
    return {
        'nodeData': {
            'id': 'root-node',
            'topic': 'Роман',
            'children': [
                {'id': 'scene-node', 'topic': 'Сцена', 'children': []},
            ],
        },
        'freeNodes': [
            {
                'id': note_id,
                'topic': text,
                'children': [],
                'position': {'x': 320, 'y': 180},
                'nfprogressFreeRoot': True,
                'nfprogressNote': True,
            },
        ],
        'arrows': [
            {'id': 'note-link', 'from': note_id, 'to': 'scene-node', 'label': ''},
        ],
        'summaries': [],
    }


def _service(monkeypatch, project, *other_projects):
    data = {
        'projects': {
            item.name: item for item in (project, *other_projects)
        },
    }
    saves = []
    monkeypatch.setattr(engine, 'load_data', lambda: data)
    monkeypatch.setattr(engine, 'save_data', lambda saved: saves.append(saved))
    return ProjectNotesService(project), data, saves


def test_project_migration_adds_stable_note_fields_and_repairs_rows():
    project = engine.Project(name='Book', goal=1000)
    del project.project_id
    del project.project_notes
    project.migrate()
    first_id = project.project_id

    project.project_notes = [
        {
            'id': 'normal',
            'source_type': 'project',
            'title': 12,
            'content': '<b>ok</b>',
            'tags': ['Сюжет', '#карта', 'сюжет'],
        },
        {'id': 'broken-map', 'source_type': 'mindmap'},
    ]
    project.migrate()

    assert project.project_id == first_id
    assert project.project_notes[0]['title'] == '12'
    assert project.project_notes[0]['tags'] == ['Сюжет']
    assert len(project.project_notes) == 1


def test_existing_native_map_notes_are_indexed_idempotently(monkeypatch):
    project = engine.Project(name='Book', goal=1000)
    project.mindmap_data = _map_data()
    service, _, saves = _service(monkeypatch, project)

    notes, _ = service.load_notes()
    assert len(notes) == 1
    note = notes[0]
    assert note['content'] == 'Текст карты'
    assert note['source_type'] == 'mindmap'
    assert note['source_map_id'] == 'root-node'
    assert note['source_node_id'] == 'map-note'
    assert note['system_tags'] == ['карта']
    assert project.project_notes[0]['content'] == ''
    first_record_id = note['id']

    notes_again, _ = service.load_notes()
    assert [item['id'] for item in notes_again] == [first_record_id]
    assert len(project.project_notes) == 1
    assert len(saves) == 1


def test_legacy_floating_notes_migrate_without_duplicates(monkeypatch):
    project = engine.Project(name='Legacy', goal=1000)
    project.mindmap_data = {
        'nodeData': {'id': 'legacy-root', 'topic': 'Legacy', 'children': []},
        'nfprogressFloatingItems': [
            {
                'id': 'legacy-note',
                'kind': 'note',
                'text': 'Старая заметка',
                'x': 40,
                'y': 60,
            },
        ],
    }
    service, _, _ = _service(monkeypatch, project)

    first, _ = service.load_notes()
    second, _ = service.load_notes()

    assert first[0]['content'] == 'Старая заметка'
    assert first[0]['source_node_id'] == 'legacy-note'
    assert [note['id'] for note in first] == [note['id'] for note in second]
    assert len(project.project_notes) == 1
    assert project.mindmap_data['nfprogressFloatingItems'][0]['text'] == 'Старая заметка'


def test_mindmap_refresh_emits_only_changed_card(monkeypatch):
    project = engine.Project(name='Book', goal=1000)
    project.mindmap_data = _map_data()
    service, _, _ = _service(monkeypatch, project)
    service.load_notes()
    events = []
    service.event_emitted.connect(
        lambda event_type, payload, origin, revision: events.append(
            (event_type, payload, origin, revision),
        )
    )

    project.mindmap_data['freeNodes'][0]['topic'] = 'Обновлено на карте'
    service.refresh_from_storage('mindmap')

    assert len(events) == 1
    assert events[0][0] == 'noteUpdated'
    assert events[0][1]['content'] == 'Обновлено на карте'
    assert events[0][2] == 'mindmap'


def test_notes_edit_updates_same_map_entity_and_emits_silent_command(monkeypatch):
    project = engine.Project(name='Book', goal=1000)
    project.mindmap_data = _map_data()
    service, _, saves = _service(monkeypatch, project)
    notes, _ = service.load_notes()
    note_id = notes[0]['id']
    commands = []
    service.map_command.connect(
        lambda command, node_id, text: commands.append((command, node_id, text))
    )

    updated = service.update_note(note_id, {'content': 'Из общей карточки'})

    assert extract_mindmap_notes(project.mindmap_data) == [
        {'id': 'map-note', 'text': 'Из общей карточки'},
    ]
    assert updated['content'] == 'Из общей карточки'
    assert commands == [('update', 'map-note', 'Из общей карточки')]
    assert project.project_notes[0]['content'] == ''
    assert project.project_notes[0]['revision'] == 1
    assert len(saves) == 2


def test_map_card_title_never_renames_mind_elixir_item(monkeypatch):
    project = engine.Project(name='Book', goal=1000)
    project.mindmap_data = _map_data(text='Исходный текст')
    service, _, _ = _service(monkeypatch, project)
    notes, _ = service.load_notes()

    updated = service.update_note(notes[0]['id'], {'title': 'Карточный заголовок'})

    assert updated['title'] == 'Карточный заголовок'
    assert extract_mindmap_notes(project.mindmap_data)[0]['text'] == 'Исходный текст'
    assert project.mindmap_data['nodeData']['children'][0]['topic'] == 'Сцена'


def test_deleting_map_card_removes_note_and_keeps_other_nodes(monkeypatch):
    project = engine.Project(name='Book', goal=1000)
    project.mindmap_data = _map_data()
    service, _, _ = _service(monkeypatch, project)
    notes, _ = service.load_notes()
    commands = []
    service.map_command.connect(
        lambda command, node_id, text: commands.append((command, node_id, text))
    )

    service.delete_note(notes[0]['id'])

    assert extract_mindmap_notes(project.mindmap_data) == []
    assert project.mindmap_data['nodeData']['id'] == 'root-node'
    assert project.mindmap_data['nodeData']['children'] == [
        {'id': 'scene-node', 'topic': 'Сцена', 'children': []},
    ]
    assert project.mindmap_data['arrows'] == []
    assert project.project_notes == []
    assert commands == [('delete', 'map-note', '')]


def test_deleting_note_on_map_removes_orphan_record(monkeypatch):
    project = engine.Project(name='Book', goal=1000)
    project.mindmap_data = _map_data()
    service, _, _ = _service(monkeypatch, project)
    notes, _ = service.load_notes()
    deleted_id = notes[0]['id']
    events = []
    service.event_emitted.connect(
        lambda event_type, payload, origin, revision: events.append(
            (event_type, payload, origin),
        )
    )

    project.mindmap_data['freeNodes'] = []
    project.mindmap_data['arrows'] = []
    service.refresh_from_storage('mindmap')

    assert project.project_notes == []
    assert events == [('noteDeleted', deleted_id, 'mindmap')]


def test_node_move_and_regular_node_rename_do_not_break_link(monkeypatch):
    project = engine.Project(name='Book', goal=1000)
    project.mindmap_data = _map_data()
    service, _, _ = _service(monkeypatch, project)
    first, _ = service.load_notes()

    project.mindmap_data['freeNodes'][0]['position'] = {'x': 900, 'y': 420}
    project.mindmap_data['nodeData']['children'][0]['topic'] = 'Новое имя сцены'
    second = service.refresh_from_storage('mindmap')

    assert second[0]['id'] == first[0]['id']
    assert second[0]['source_node_id'] == 'map-note'
    assert second[0]['content'] == 'Текст карты'


def test_copied_map_note_gets_a_distinct_card(monkeypatch):
    project = engine.Project(name='Book', goal=1000)
    project.mindmap_data = _map_data()
    service, _, _ = _service(monkeypatch, project)
    first, _ = service.load_notes()
    copied = dict(project.mindmap_data['freeNodes'][0])
    copied.update({
        'id': 'copied-map-note',
        'topic': 'Копия заметки',
        'position': {'x': 460, 'y': 260},
    })
    project.mindmap_data['freeNodes'].append(copied)

    notes = service.refresh_from_storage('mindmap')

    assert {note['source_node_id'] for note in notes} == {
        'map-note', 'copied-map-note',
    }
    assert len({note['id'] for note in notes}) == 2
    assert first[0]['id'] in {note['id'] for note in notes}


def test_link_and_metadata_survive_a_pickle_restart(monkeypatch):
    project = engine.Project(name='Book', goal=1000)
    project.mindmap_data = _map_data()
    service, data, _ = _service(monkeypatch, project)
    notes, _ = service.load_notes()
    service.update_note(notes[0]['id'], {
        'title': 'Отдельный заголовок',
        'pinned': True,
        'color': 'yellow',
    })

    restored_data = pickle.loads(pickle.dumps(data))
    restored_project = restored_data['projects']['Book']
    monkeypatch.setattr(engine, 'load_data', lambda: restored_data)
    monkeypatch.setattr(engine, 'save_data', lambda _data: None)
    restored_notes, _ = ProjectNotesService(restored_project).load_notes()

    assert restored_notes[0]['id'] == notes[0]['id']
    assert restored_notes[0]['source_node_id'] == 'map-note'
    assert restored_notes[0]['content'] == 'Текст карты'
    assert restored_notes[0]['title'] == 'Отдельный заголовок'
    assert restored_notes[0]['pinned'] is True
    assert restored_notes[0]['color'] == 'yellow'


def test_normal_notes_features_and_project_isolation(monkeypatch):
    first = engine.Project(name='First', goal=1000)
    second = engine.Project(name='Second', goal=1000)
    service, _, _ = _service(monkeypatch, first, second)

    created = service.create_note()
    assert created['title'] == ''
    assert created['display_title'] == ''
    updated = service.update_note(
        created['id'],
        {
            'title': 'План',
            'content': '<b>Текст</b><script>alert(1)</script>',
            'color': 'blue',
            'pinned': True,
            'archived': True,
            'tags': ['сюжет', '#карта'],
            'checklist': [
                {'id': 'check-1', 'text': 'Проверить', 'checked': True},
            ],
        },
    )

    assert updated['title'] == 'План'
    assert updated['content'] == '<b>Текст</b>alert(1)'
    assert updated['color'] == 'blue'
    assert updated['pinned'] is True
    assert updated['archived'] is True
    assert updated['tags'] == ['сюжет']
    assert updated['checklist'][0]['checked'] is True
    assert second.project_notes == []


def test_recreated_project_with_same_name_does_not_reuse_old_notes_service(
    monkeypatch,
):
    original = engine.Project(name='Book', goal=1000)
    service, data, _ = _service(monkeypatch, original)
    replacement = engine.Project(name='Book', goal=1000)
    data['projects']['Book'] = replacement

    with pytest.raises(ValueError):
        service.create_note()

    assert replacement.project_notes == []


def test_completed_stage_notes_are_read_only(monkeypatch):
    stage = engine.Stage(
        name='Editing',
        goal=1000,
        status='завершен',
        parent_project_name='Book',
    )
    parent = engine.Project(name='Book', goal=1000)
    parent.enable_stages = True
    parent.stages = [stage]
    data = {'projects': {'Book': parent}}
    monkeypatch.setattr(engine, 'load_data', lambda: data)
    monkeypatch.setattr(engine, 'save_data', lambda _data: None)
    service = ProjectNotesService(stage)

    notes, read_only = service.load_notes()

    assert notes == []
    assert read_only is True
    with pytest.raises(PermissionError):
        service.create_note()


def test_staged_project_aggregates_and_routes_stage_notes(monkeypatch):
    draft = engine.Stage(
        name='Черновик',
        goal=1000,
        parent_project_name='Book',
    )
    draft.mindmap_data = _map_data(
        note_id='shared-map-note',
        text='Идея из черновика',
    )
    editing = engine.Stage(
        name='Редактура',
        goal=1000,
        status='завершен',
        parent_project_name='Book',
    )
    editing.mindmap_data = _map_data(
        note_id='shared-map-note',
        text='Идея из редактуры',
    )
    project = engine.Project(name='Book', goal=2000)
    project.enable_stages = True
    project.stages = [draft, editing]
    outside = engine.Project(name='Outside', goal=1000)
    outside.project_notes = engine.normalize_project_note_records([{
        'id': 'outside-note',
        'title': 'Чужая заметка',
        'content': 'Не должна отображаться',
    }])
    data = {'projects': {'Book': project, 'Outside': outside}}
    monkeypatch.setattr(engine, 'load_data', lambda: data)
    monkeypatch.setattr(engine, 'save_data', lambda _data: None)

    draft_service = ProjectNotesService(draft)
    draft_note = draft_service.create_note()
    draft_service.update_note(draft_note['id'], {
        'title': 'План первой главы',
        'content': '<p>Сцена у реки</p>',
    })
    service = ProjectNotesService(project)

    notes, read_only = service.load_notes()

    assert read_only is False
    assert len(notes) == 3
    assert len({note['id'] for note in notes}) == 3
    assert {note['stage_name'] for note in notes} == {'Черновик', 'Редактура'}
    assert all(note['id'].startswith('stage:') for note in notes)
    assert all(note['title'] != 'Чужая заметка' for note in notes)
    assert service.view_context() == {
        'hasStages': True,
        'stages': [
            {'id': draft.stage_id, 'name': 'Черновик'},
            {'id': editing.stage_id, 'name': 'Редактура'},
        ],
    }
    assert {
        note['stage_name']: note['owner_order'] for note in notes
    } == {'Черновик': 1, 'Редактура': 2}

    draft_card = next(note for note in notes if note['title'] == 'План первой главы')
    updated = service.update_note(draft_card['id'], {'title': 'Новый план'})
    assert updated['stage_name'] == 'Черновик'
    assert next(
        note for note in draft.project_notes if note['source_type'] == 'project'
    )['title'] == 'Новый план'
    assert outside.project_notes[0]['title'] == 'Чужая заметка'

    draft_map_card = next(
        note for note in notes
        if note['stage_name'] == 'Черновик' and note['source_type'] == 'mindmap'
    )
    editing_map_card = next(
        note for note in notes
        if note['stage_name'] == 'Редактура' and note['source_type'] == 'mindmap'
    )
    service.update_note(draft_map_card['id'], {'content': 'Обновлено из проекта'})
    assert extract_mindmap_notes(draft.mindmap_data)[0]['text'] == 'Обновлено из проекта'
    assert extract_mindmap_notes(editing.mindmap_data)[0]['text'] == 'Идея из редактуры'
    map_owner, node_id = service.get_map_target(draft_map_card['id'])
    assert map_owner.stage_id == draft.stage_id
    assert node_id == 'shared-map-note'
    assert editing_map_card['read_only'] is True
    with pytest.raises(PermissionError):
        service.update_note(editing_map_card['id'], {'title': 'Нельзя изменить'})
    service.delete_note(draft_map_card['id'])
    assert extract_mindmap_notes(draft.mindmap_data) == []
    assert extract_mindmap_notes(editing.mindmap_data)[0]['text'] == 'Идея из редактуры'

    project_note = service.create_note()
    assert project_note['owner_type'] == 'project'
    assert project_note['stage_name'] is None
    assert project_note['id'].startswith('project:')


def test_drag_order_is_persisted(monkeypatch):
    project = engine.Project(name='Book', goal=1000)
    service, _, _ = _service(monkeypatch, project)
    first = service.create_note()
    second = service.create_note()

    service.update_order([second['id'], first['id']])
    by_id = {note['id']: note for note in project.project_notes}

    assert by_id[second['id']]['sort_order'] == 0
    assert by_id[first['id']]['sort_order'] == 1


def test_map_helpers_support_legacy_update_and_safe_removal():
    legacy = {
        'nodeData': {'id': 'root', 'topic': 'Book', 'children': []},
        'nfprogressFloatingItems': [
            {'id': 'old', 'kind': 'note', 'text': 'Old', 'x': 20, 'y': 30},
        ],
        'nfprogressFloatingLinks': [
            {
                'id': 'link', 'fromType': 'floating', 'from': 'old',
                'toType': 'node', 'to': 'root',
            },
        ],
    }

    updated = set_mindmap_note_text(legacy, 'old', 'New')
    removed = remove_mindmap_note(updated, 'old')

    assert extract_mindmap_notes(updated) == [{'id': 'old', 'text': 'New'}]
    assert extract_mindmap_notes(removed) == []
    assert removed['nodeData']['id'] == 'root'
    assert removed['nfprogressFloatingLinks'] == []


def test_rich_text_sanitizer_rejects_active_content_and_unsafe_links():
    source = (
        '<p onclick="bad()">Safe <strong>text</strong>'
        '<img src=x onerror=bad()>'
        '<a href="javascript:bad()">bad link</a>'
        '<a href="https://example.com">good link</a></p>'
    )
    sanitized = sanitize_note_html(source)

    assert 'onclick' not in sanitized
    assert '<img' not in sanitized
    assert 'javascript:' not in sanitized
    assert '<strong>text</strong>' in sanitized
    assert 'href="https://example.com"' in sanitized
    assert note_html_to_plain_text(sanitized) == 'Safe textbad linkgood link'


def test_ui_resources_are_local_and_packaged():
    main_ui = ET.parse(PROJECT_ROOT / 'UI template' / 'main_window.ui').getroot()
    button = main_ui.find(".//widget[@name='btn_project_notes']")
    assert button is not None
    assert button.find("property[@name='text']/string").text == 'Заметки'
    assert button.find("property[@name='accessibleName']/string").text
    assert button.find("property[@name='icon']") is None
    assert button.find("property[@name='minimumSize']") is None
    assert 'self.btn_project_notes.setIcon(' not in (
        PROJECT_ROOT / 'main_UI.py'
    ).read_text()

    notes_html = (PROJECT_ROOT / 'notes_assets' / 'index.html').read_text()
    notes_js = (PROJECT_ROOT / 'notes_assets' / 'app.js').read_text()
    notes_css = (PROJECT_ROOT / 'notes_assets' / 'styles.css').read_text()
    notice = (PROJECT_ROOT / 'notes_assets' / 'NOTICE.txt').read_text()
    assert 'http://' not in notes_html and 'https://' not in notes_html
    assert 'Content-Security-Policy' in notes_html
    assert 'worker-src blob:' in notes_html
    assert 'note-editor-layer' in notes_html
    assert 'note-editor-actions' not in notes_html
    assert notes_html.count('class="toolbar-icon"') >= 2
    assert '▦' not in notes_html and '▣' not in notes_html
    assert 'new Muuri' in notes_js
    assert 'dragHandle' in notes_js
    assert 'color-select' not in notes_js
    assert 'color-swatch' in notes_js
    assert 'aria-pressed' in notes_js
    assert 'window.prompt' not in notes_js
    assert 'link-editor' in notes_js
    assert 'pinFilled' in notes_js
    assert 'editable-tag-chip' in notes_js
    assert 'note.stage_name' in notes_js
    assert 'stage-notes-toggle' in notes_html
    assert 'stage-filter-button' in notes_html
    assert 'quick-note-button' in notes_html
    assert "useDragContainer: false" in notes_js
    assert '.color-swatch' in notes_css
    assert 'border-radius: 50%' in notes_css
    assert '.toolbar-icon' in notes_css
    assert 'suppressExternalSync' in (
        PROJECT_ROOT / 'mindmap_assets' / 'app.js'
    ).read_text()
    assert 'License: MIT' in notice
    assert (PROJECT_ROOT / 'notes_assets' / 'vendor' / 'muuri.min.js').is_file()
    assert (PROJECT_ROOT / 'notes_assets' / 'vendor' / 'MUURI-LICENSE.md').is_file()

    for build_file in (
        PROJECT_ROOT / 'build-mac-arm.sh',
        PROJECT_ROOT / 'build-mac-intel.sh',
        PROJECT_ROOT / '.github' / 'workflows' / 'build.yml',
    ):
        assert 'notes_assets' in build_file.read_text()


def test_notes_frontend_exposes_incremental_bridge_api():
    source = (PROJECT_ROOT / 'notes_assets' / 'app.js').read_text()
    mindmap_source = (PROJECT_ROOT / 'mindmap_assets' / 'app.js').read_text()

    for event_name in (
        'createNote', 'updateNote', 'deleteNote', 'updateOrder',
        'openMindMapNode',
    ):
        assert event_name in source
    for method_name in ('applyEvent', 'themeChanged', 'updateTranslations'):
        assert method_name in source
    for method_name in ('focusNode', 'updateNodeNote', 'removeNodeNote'):
        assert method_name in mindmap_source


def test_mindmap_note_records_do_not_duplicate_text():
    map_data = _map_data(text='Единственный источник текста')
    project = engine.Project(name='Book', goal=1000)
    project.mindmap_data = map_data
    map_record = {
        'id': 'record',
        'title': '',
        'content': 'stale duplicate',
        'source_type': 'mindmap',
        'source_map_id': 'root-node',
        'source_node_id': 'map-note',
    }

    normalized = engine.normalize_project_note_records([map_record])

    assert normalized[0]['content'] == ''
    assert json.dumps(map_data, ensure_ascii=False).count('Единственный источник текста') == 1


def _wait_until(application, condition, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        application.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    return False


def _run_javascript(application, dialog, source):
    results = []
    dialog.web_view.runJavaScript(source, results.append)
    assert _wait_until(application, lambda: bool(results))
    return results[0]


def _process_events_for(application, duration=0.2):
    deadline = time.monotonic() + duration
    while time.monotonic() < deadline:
        application.processEvents()
        time.sleep(0.01)


@requires_native_webview
def test_project_notes_dialog_loads_and_syncs_incrementally(monkeypatch):
    application = QApplication.instance() or QApplication([])
    project = engine.Project(name='Native Notes', goal=1000)
    project.mindmap_data = _map_data(text='До изменения')
    service, _, _ = _service(monkeypatch, project)
    opened_nodes = []
    dialog = ProjectNotesDialog(
        service,
        lambda _map_owner, node_id: opened_nodes.append(node_id),
    )
    dialog.show()

    assert _wait_until(application, lambda: dialog._ready)
    assert dialog.web_view.focusPolicy() == Qt.FocusPolicy.StrongFocus
    initial_state = json.loads(_run_javascript(
        application,
        dialog,
        'window.nfprogressNotes.getState()',
    ))
    assert initial_state['noteCount'] == 1
    assert json.loads(_run_javascript(
        application,
        dialog,
        """
        JSON.stringify({
          editors: document.querySelectorAll('.notes-grid .rich-toolbar').length,
          editable: document.querySelectorAll(
            '.notes-grid [contenteditable="true"], .notes-grid textarea'
          ).length
        })
        """,
    )) == {'editors': 0, 'editable': 0}

    theme_state = json.loads(_run_javascript(
        application,
        dialog,
        """
        (() => {
          window.nfprogressNotes.themeChanged({
            window: '#101214', surface: '#181b1f', surfaceAlt: '#22262b',
            text: '#f3f4f6', muted: '#aeb4bd', border: '#58606b',
            accent: '#8ca2ff', accentText: '#111318', dark: true
          });
          return JSON.stringify({
            windowColor: getComputedStyle(document.documentElement)
              .getPropertyValue('--window').trim(),
            dark: document.body.classList.contains('dark-theme')
          });
        })()
        """,
    ))
    assert theme_state == {'windowColor': '#101214', 'dark': True}

    dialog.resize(560, 650)
    assert _wait_until(
        application,
        lambda: _run_javascript(application, dialog, 'window.innerWidth') <= 520,
    )
    assert _wait_until(
        application,
        lambda: _run_javascript(
            application,
            dialog,
            """
            (() => {
              const item = document.querySelector('.note-item');
              return item.getBoundingClientRect().width
                / item.parentElement.getBoundingClientRect().width;
            })()
            """,
        ) > 0.9,
    )
    dialog.resize(1180, 760)
    assert _wait_until(
        application,
        lambda: _run_javascript(application, dialog, 'window.innerWidth') > 900,
    )

    _run_javascript(
        application,
        dialog,
        "document.getElementById('new-note').click(); true",
    )
    assert _wait_until(
        application,
        lambda: len(project.project_notes) == 2,
    )
    assert _wait_until(
        application,
        lambda: _run_javascript(
            application,
            dialog,
            "document.activeElement?.classList.contains('note-content') || false",
        ),
    )
    created_state = json.loads(_run_javascript(
        application,
        dialog,
        'window.nfprogressNotes.getState()',
    ))
    assert created_state['editorOpen'] is True
    assert created_state['activeNoteId'] is not None
    shortcut_state = json.loads(_run_javascript(
        application,
        dialog,
        """
        (() => {
          const content = document.querySelector('.note-editor-item .note-content');
          content.textContent = 'Горячие клавиши';
          const range = document.createRange();
          range.setStart(content.firstChild, 0);
          range.setEnd(content.firstChild, 7);
          const selection = window.getSelection();
          selection.removeAllRanges();
          selection.addRange(range);
          const boldEvent = new KeyboardEvent('keydown', {
            bubbles: true, cancelable: true, key: 'и', code: 'KeyB', metaKey: true
          });
          content.dispatchEvent(boldEvent);
          const selectEvent = new KeyboardEvent('keydown', {
            bubbles: true, cancelable: true, key: 'ф', code: 'KeyA', metaKey: true
          });
          content.dispatchEvent(selectEvent);
          const copyEvent = new KeyboardEvent('keydown', {
            bubbles: true, cancelable: true, key: 'с', code: 'KeyC', metaKey: true
          });
          content.dispatchEvent(copyEvent);
          const pasteWithoutData = new Event('paste', {
            bubbles: true, cancelable: true
          });
          content.dispatchEvent(pasteWithoutData);
          return JSON.stringify({
            boldPrevented: boldEvent.defaultPrevented,
            boldApplied: Boolean(content.querySelector('b, strong')),
            selectedText: selection.toString(),
            nativeCopyAllowed: !copyEvent.defaultPrevented,
            nativePasteAllowed: !pasteWithoutData.defaultPrevented,
            boldShortcuts: document.querySelector(
              '.rich-toolbar [aria-keyshortcuts*="Meta+B"]'
            ) !== null
          });
        })()
        """,
    ))
    assert shortcut_state == {
        'boldPrevented': True,
        'boldApplied': True,
        'selectedText': 'Горячие клавиши',
        'nativeCopyAllowed': True,
        'nativePasteAllowed': True,
        'boldShortcuts': True,
    }
    _run_javascript(
        application,
        dialog,
        """
        (() => {
          const handle = document.querySelector(
            '[data-source="project"] .drag-handle'
          );
          handle.dispatchEvent(new KeyboardEvent('keydown', {
            bubbles: true,
            key: 'ArrowUp'
          }));
          return true;
        })()
        """,
    )
    assert _wait_until(
        application,
        lambda: next(
            note['sort_order']
            for note in project.project_notes
            if note['source_type'] == 'project'
        ) == 0,
    )

    palette_state = json.loads(_run_javascript(
        application,
        dialog,
        """
        (() => {
          const card = document.querySelector(
            '.note-editor-item[data-source="project"]'
          );
          const title = card.querySelector('.note-title');
          const content = card.querySelector('.note-content');
          const tags = card.querySelector('.tag-input');
          title.value = 'Обычная заметка';
          title.dispatchEvent(new Event('input', { bubbles: true }));
          content.innerHTML = '<strong>Жирный текст</strong> и продолжение<script>bad()</script>';
          content.dispatchEvent(new Event('input', { bubbles: true }));
          tags.value = 'сюжет, идея, #карта';
          tags.dispatchEvent(new Event('input', { bubbles: true }));
          tags.dispatchEvent(new KeyboardEvent('keydown', {
            bubbles: true, cancelable: true, key: 'Enter'
          }));
          const toggle = card.querySelector('.color-palette-toggle');
          const paletteIcon = toggle.querySelector('svg');
          toggle.click();
          const palette = card.querySelector('.color-palette');
          const swatches = [...palette.querySelectorAll('.color-swatch')];
          const paletteWasVisible = !palette.hidden;
          const distinctColors = new Set(swatches.map(
            swatch => getComputedStyle(swatch).backgroundColor
          )).size;
          const blue = palette.querySelector('[data-note-color="blue"]');
          const blueStyle = getComputedStyle(blue);
          blue.click();
          const noteCard = card.querySelector('.note-card');
          const footer = card.querySelector('.card-footer');
          const done = card.querySelector('#note-editor-done');
          const archive = footer.querySelector('.card-action');
          const colorProbe = document.createElement('span');
          colorProbe.style.color = 'var(--card-blue)';
          noteCard.appendChild(colorProbe);
          const expectedBlue = getComputedStyle(colorProbe).color;
          colorProbe.remove();
          return JSON.stringify({
            paletteWasVisible,
            paletteIconVisible: paletteIcon.getBoundingClientRect().width >= 20,
            swatchCount: swatches.length,
            distinctColors,
            circleBorderRadius: blueStyle.borderRadius,
            selectedBlue: blue.getAttribute('aria-pressed') === 'true',
            hasColorIndicator: Boolean(
              toggle.querySelector('.color-current-swatch')
            ),
            paletteClosed: palette.hidden,
            doneInsideFooter: done?.parentElement === footer,
            doneAligned: Math.abs(
              done.getBoundingClientRect().top - archive.getBoundingClientRect().top
            ) < 2,
            editorUsesSelectedColor:
              getComputedStyle(noteCard).backgroundColor === expectedBlue,
            dialogIsTransparent:
              getComputedStyle(document.getElementById('note-editor-dialog'))
                .backgroundColor === 'rgba(0, 0, 0, 0)',
            clickableTags: card.querySelectorAll(
              '.editable-tag-chip .tag-chip'
            ).length,
            adaptiveTagInput:
              tags.getBoundingClientRect().width
                < card.querySelector('.tag-area').getBoundingClientRect().width
          });
        })()
        """,
    ))
    assert palette_state['paletteWasVisible'] is True
    assert palette_state['paletteIconVisible'] is True
    assert palette_state['swatchCount'] == len(engine.PROJECT_NOTE_COLORS)
    assert palette_state['distinctColors'] == len(engine.PROJECT_NOTE_COLORS)
    assert palette_state['circleBorderRadius'] == '50%'
    assert palette_state['selectedBlue'] is True
    assert palette_state['hasColorIndicator'] is False
    assert palette_state['paletteClosed'] is True
    assert palette_state['doneInsideFooter'] is True
    assert palette_state['doneAligned'] is True
    assert palette_state['editorUsesSelectedColor'] is True
    assert palette_state['dialogIsTransparent'] is True
    assert palette_state['clickableTags'] == 2
    assert palette_state['adaptiveTagInput'] is True
    assert _wait_until(
        application,
        lambda: any(
            note['source_type'] == 'project'
            and note['title'] == 'Обычная заметка'
            and note['color'] == 'blue'
            and note['tags'] == ['сюжет', 'идея']
            and '<strong>Жирный текст</strong>' in note['content']
            and '<script>' not in note['content']
            for note in project.project_notes
        ),
    )

    link_state = json.loads(_run_javascript(
        application,
        dialog,
        """
        (() => {
          const card = document.querySelector(
            '.note-editor-item[data-source="project"]'
          );
          const content = card.querySelector('.note-content');
          const text = content.querySelector('strong')?.firstChild;
          const range = document.createRange();
          range.selectNodeContents(text);
          const selection = window.getSelection();
          selection.removeAllRanges();
          selection.addRange(range);
          const linkButton = [...card.querySelectorAll('.rich-toolbar .format-button')]
            .find(button => button.getAttribute('aria-keyshortcuts')?.includes('Control+K'));
          linkButton.click();
          const editor = card.querySelector('.link-editor');
          const input = editor.querySelector('.link-url-input');
          input.value = 'example.com/note';
          editor.dispatchEvent(new Event('submit', {
            bubbles: true, cancelable: true
          }));
          const link = content.querySelector('a');
          return JSON.stringify({
            editorOpened: Boolean(editor),
            editorClosed: !card.querySelector('.link-editor'),
            href: link?.getAttribute('href'),
            text: link?.textContent
          });
        })()
        """,
    ))
    assert link_state == {
        'editorOpened': True,
        'editorClosed': True,
        'href': 'https://example.com/note',
        'text': 'Жирный текст',
    }
    assert _wait_until(
        application,
        lambda: any(
            note['source_type'] == 'project'
            and '<a href="https://example.com/note"' in note['content']
            for note in project.project_notes
        ),
    )

    dismissed_link_state = json.loads(_run_javascript(
        application,
        dialog,
        """
        (() => {
          const card = document.querySelector(
            '.note-editor-item[data-source="project"]'
          );
          const content = card.querySelector('.note-content');
          const text = [...content.childNodes].find(
            node => node.nodeType === Node.TEXT_NODE
              && node.textContent.includes('продолжение')
          );
          const range = document.createRange();
          const start = text.textContent.indexOf('продолжение');
          range.setStart(text, start);
          range.setEnd(text, start + 'продолжение'.length);
          const selection = window.getSelection();
          selection.removeAllRanges();
          selection.addRange(range);
          const buttons = [...card.querySelectorAll('.rich-toolbar .format-button')];
          const linkButton = buttons.find(
            button => button.getAttribute('aria-keyshortcuts')?.includes('Control+K')
          );
          const boldButton = buttons.find(
            button => button.getAttribute('aria-keyshortcuts')?.includes('Control+B')
          );
          linkButton.click();
          const editor = card.querySelector('.link-editor');
          editor.querySelector('.link-url-input').value = 'outside.example';
          boldButton.dispatchEvent(new MouseEvent('pointerdown', {
            bubbles: true, cancelable: true
          }));
          const links = [...content.querySelectorAll('a')];
          return JSON.stringify({
            editorOpened: Boolean(editor),
            editorClosed: !card.querySelector('.link-editor'),
            secondLinkText: links[1]?.textContent,
            secondLinkHref: links[1]?.getAttribute('href'),
            linkCount: links.length
          });
        })()
        """,
    ))
    assert dismissed_link_state == {
        'editorOpened': True,
        'editorClosed': True,
        'secondLinkText': 'продолжение',
        'secondLinkHref': 'https://outside.example/',
        'linkCount': 2,
    }
    assert _wait_until(
        application,
        lambda: any(
            note['source_type'] == 'project'
            and 'href="https://outside.example/"' in note['content']
            and '>продолжение</a>' in note['content']
            for note in project.project_notes
        ),
    )
    no_selection_link_state = json.loads(_run_javascript(
        application,
        dialog,
        """
        (() => {
          const card = document.querySelector(
            '.note-editor-item[data-source="project"]'
          );
          const content = card.querySelector('.note-content');
          const range = document.createRange();
          range.selectNodeContents(content);
          range.collapse(false);
          const selection = window.getSelection();
          selection.removeAllRanges();
          selection.addRange(range);
          const linkButton = [...card.querySelectorAll('.rich-toolbar .format-button')]
            .find(button => button.getAttribute('aria-keyshortcuts')?.includes('Control+K'));
          linkButton.click();
          return JSON.stringify({
            editorOpened: Boolean(card.querySelector('.link-editor')),
            linkCount: content.querySelectorAll('a').length
          });
        })()
        """,
    ))
    assert no_selection_link_state == {
        'editorOpened': False,
        'linkCount': 2,
    }

    pin_state = json.loads(_run_javascript(
        application,
        dialog,
        """
        (() => {
          const pin = document.querySelector(
            '.note-editor-item[data-source="project"] .pin-action'
          );
          const emptyBefore = !pin.querySelector('.pin-fill');
          const disabledBefore = pin.disabled;
          pin.click();
          const activePin = document.querySelector(
            '.note-editor-item[data-source="project"] .pin-action'
          );
          const filledImmediately = Boolean(activePin.querySelector('.pin-fill'));
          const pressedImmediately = activePin.getAttribute('aria-pressed') === 'true';
          const buttons = document.querySelectorAll(
            '.note-editor-item[data-source="project"] .rich-toolbar .format-button'
          );
          buttons[buttons.length - 1].click();
          return JSON.stringify({
            emptyBefore,
            disabledBefore,
            filledImmediately,
            pressedImmediately,
            filledAfter: Boolean(activePin.querySelector('.pin-fill')),
            pressedAfter: activePin.getAttribute('aria-pressed') === 'true'
          });
        })()
        """,
    ))
    assert pin_state == {
        'emptyBefore': True,
        'disabledBefore': False,
        'filledImmediately': True,
        'pressedImmediately': True,
        'filledAfter': True,
        'pressedAfter': True,
    }
    assert _wait_until(
        application,
        lambda: any(
            note['source_type'] == 'project'
            and note['pinned']
            and len(note['checklist']) == 1
            for note in project.project_notes
        ),
    )
    _run_javascript(
        application,
        dialog,
        """
        (() => {
          const card = document.querySelector(
            '.note-editor-item[data-source="project"]'
          );
          const text = card.querySelector('.checklist-text');
          const checkbox = card.querySelector('.checklist-row input[type="checkbox"]');
          text.value = 'Проверить хронологию';
          text.dispatchEvent(new Event('input', { bubbles: true }));
          checkbox.checked = true;
          checkbox.dispatchEvent(new Event('change', { bubbles: true }));
          return true;
        })()
        """,
    )
    assert _wait_until(
        application,
        lambda: any(
            note['source_type'] == 'project'
            and note['checklist'][0]['text'] == 'Проверить хронологию'
            and note['checklist'][0]['checked'] is True
            for note in project.project_notes
        ),
    )

    _run_javascript(
        application,
        dialog,
        """
        (() => {
          const card = document.querySelector(
            '.note-editor-item[data-source="project"]'
          );
          const actions = card.querySelectorAll('.card-footer .card-action');
          actions[0].click();
          return true;
        })()
        """,
    )
    assert _wait_until(
        application,
        lambda: any(
            note['source_type'] == 'project' and note['archived']
            for note in project.project_notes
        ),
    )
    _run_javascript(
        application,
        dialog,
        """
        (() => {
          document.getElementById('archive-toggle').click();
          const card = document.querySelector('[data-source="project"]');
          card.querySelector('.card-footer .card-action').click();
          document.getElementById('archive-toggle').click();
          return true;
        })()
        """,
    )
    assert _wait_until(
        application,
        lambda: any(
            note['source_type'] == 'project' and not note['archived']
            for note in project.project_notes
        ),
    )
    _run_javascript(
        application,
        dialog,
        """
        (() => {
          const tag = [...document.querySelectorAll(
            '.notes-grid [data-source="project"] .tag-chip'
          )].find(candidate => candidate.textContent === '#сюжет');
          tag.click();
          return true;
        })()
        """,
    )
    assert _wait_until(
        application,
        lambda: (
            (state := json.loads(_run_javascript(
                application,
                dialog,
                'window.nfprogressNotes.getState()',
            )))['selectedTag'] == 'сюжет'
            and len(state['visibleIds']) == 1
        ),
    )
    _run_javascript(
        application,
        dialog,
        "document.querySelector('#tag-filter-menu button').click(); true",
    )
    assert _wait_until(
        application,
        lambda: json.loads(_run_javascript(
            application,
            dialog,
            'window.nfprogressNotes.getState()',
        ))['selectedTag'] is None,
    )

    _run_javascript(
        application,
        dialog,
        """
        (() => {
          document.querySelector(
            '.notes-grid [data-source="mindmap"] .note-card'
          ).click();
          const editor = document.querySelector(
            '.note-editor-item[data-source="mindmap"] textarea'
          );
          editor.value = 'После изменения';
          editor.dispatchEvent(new Event('input', { bubbles: true }));
          return true;
        })()
        """,
    )
    assert _wait_until(
        application,
        lambda: extract_mindmap_notes(project.mindmap_data)[0]['text']
        == 'После изменения',
    )
    assert _run_javascript(
        application,
        dialog,
        "document.querySelector('.note-editor-item[data-source=\"mindmap\"] .note-title').placeholder",
    ) == 'После изменения'

    _run_javascript(
        application,
        dialog,
        "document.querySelector('[data-source=\"mindmap\"] .system-tag').click(); true",
    )
    assert _wait_until(
        application,
        lambda: (
            (state := json.loads(_run_javascript(
                application,
                dialog,
                'window.nfprogressNotes.getState()',
            )))['selectedTag'] == 'карта'
            and len(state['visibleIds']) == 1
        ),
    )
    _run_javascript(
        application,
        dialog,
        "document.querySelector('#tag-filter-menu button').click(); true",
    )
    assert _wait_until(
        application,
        lambda: json.loads(_run_javascript(
            application,
            dialog,
            'window.nfprogressNotes.getState()',
        ))['selectedTag'] is None,
    )

    _run_javascript(
        application,
        dialog,
        """
        (() => {
          const input = document.getElementById('search-input');
          input.value = '#карта';
          input.dispatchEvent(new Event('input', { bubbles: true }));
          return true;
        })()
        """,
    )
    assert _wait_until(
        application,
        lambda: len(json.loads(_run_javascript(
            application,
            dialog,
            'window.nfprogressNotes.getState()',
        ))['visibleIds']) == 1,
    )
    _run_javascript(
        application,
        dialog,
        "document.querySelector('.open-map-action').click(); true",
    )
    assert _wait_until(application, lambda: opened_nodes == ['map-note'])

    _run_javascript(
        application,
        dialog,
        """
        (() => {
          const input = document.getElementById('search-input');
          input.value = '';
          input.dispatchEvent(new Event('input', { bubbles: true }));
          return true;
        })()
        """,
    )
    assert _wait_until(
        application,
        lambda: len(json.loads(_run_javascript(
            application,
            dialog,
            'window.nfprogressNotes.getState()',
        ))['visibleIds']) == 2,
    )
    _run_javascript(
        application,
        dialog,
        """
        (() => {
          document.querySelector(
            '.notes-grid [data-source="project"] .note-card'
          ).click();
          const title = document.querySelector(
            '.note-editor-item[data-source="project"] .note-title'
          );
          title.value = 'Сохранить при закрытии';
          title.dispatchEvent(new Event('input', { bubbles: true }));
          return true;
        })()
        """,
    )
    dialog.close()
    assert _wait_until(
        application,
        lambda: any(
            note['source_type'] == 'project'
            and note['title'] == 'Сохранить при закрытии'
            for note in project.project_notes
        ),
    )
    dialog.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    application.processEvents()


@requires_native_webview
def test_staged_project_dialog_displays_and_searches_stage_notes(monkeypatch):
    application = QApplication.instance() or QApplication([])
    draft = engine.Stage(
        name='Черновик',
        goal=1000,
        parent_project_name='Staged Notes',
    )
    editing = engine.Stage(
        name='Редактура',
        goal=1000,
        status='завершен',
        parent_project_name='Staged Notes',
    )
    draft.project_notes = engine.normalize_project_note_records([{
        'id': 'draft-note',
        'title': 'Первая глава',
        'content': '<p>Начальная сцена</p>',
    }])
    editing.project_notes = engine.normalize_project_note_records([{
        'id': 'editing-note',
        'title': 'Проверка текста',
        'content': '<p>Финальная вычитка</p>',
    }])
    project = engine.Project(name='Staged Notes', goal=2000)
    project.enable_stages = True
    project.stages = [draft, editing]
    service, _, _ = _service(monkeypatch, project)
    dialog = ProjectNotesDialog(service, lambda _owner, _node_id: None)
    dialog.show()

    assert _wait_until(application, lambda: dialog._ready)
    initial_state = json.loads(_run_javascript(
        application,
        dialog,
        'window.nfprogressNotes.getState()',
    ))
    assert initial_state['noteCount'] == 2
    assert initial_state['hasStages'] is True
    assert initial_state['includeStageNotes'] is False
    assert initial_state['visibleIds'] == []
    assert bool(_run_javascript(
        application,
        dialog,
        "document.getElementById('stage-notes-toggle').hidden",
    )) is False
    assert json.loads(_run_javascript(
        application,
        dialog,
        """
        (() => {
          const iconSize = selector => {
            const rect = document.querySelector(selector).getBoundingClientRect();
            return [Math.round(rect.width), Math.round(rect.height)];
          };
          return JSON.stringify({
            stages: iconSize('#stage-notes-toggle .toolbar-icon'),
            archive: iconSize('#archive-toggle .toolbar-icon')
          });
        })()
        """,
    )) == {'stages': [20, 20], 'archive': [20, 20]}

    _run_javascript(
        application,
        dialog,
        "document.getElementById('stage-notes-toggle').click(); true",
    )
    assert _wait_until(
        application,
        lambda: (
            (state := json.loads(_run_javascript(
                application,
                dialog,
                'window.nfprogressNotes.getState()',
            )))['includeStageNotes'] is True
            and len(state['visibleIds']) == 2
        ),
    )
    badges = json.loads(_run_javascript(
        application,
        dialog,
        """
        JSON.stringify([...document.querySelectorAll('.stage-badge')]
          .map(element => element.textContent))
        """,
    ))
    assert badges == ['Этап: Черновик', 'Этап: Редактура']
    _run_javascript(
        application,
        dialog,
        f"""
        document.querySelector(
          '.notes-grid [data-stage-id="{editing.stage_id}"] .note-card'
        ).click(); true
        """,
    )
    assert bool(_run_javascript(
        application,
        dialog,
        "document.querySelector('.note-editor-item .note-title').disabled",
    )) is True
    _run_javascript(
        application,
        dialog,
        "document.getElementById('note-editor-done').click(); true",
    )

    _run_javascript(
        application,
        dialog,
        f"""
        (() => {{
          const buttons = [...document.querySelectorAll('#stage-filter-menu button')];
          buttons.find(button => button.textContent === 'Редактура').click();
          return true;
        }})()
        """,
    )
    assert _wait_until(
        application,
        lambda: (
            (state := json.loads(_run_javascript(
                application,
                dialog,
                'window.nfprogressNotes.getState()',
            )))['selectedStageId'] == editing.stage_id
            and len(state['visibleIds']) == 1
        ),
    )
    assert _run_javascript(
        application,
        dialog,
        "document.querySelector('.stage-badge').textContent",
    ) == 'Этап: Редактура'
    _run_javascript(
        application,
        dialog,
        "document.querySelector('#stage-filter-menu button').click(); true",
    )
    _run_javascript(
        application,
        dialog,
        "document.getElementById('stage-sort-toggle').click(); true",
    )
    assert _wait_until(
        application,
        lambda: json.loads(_run_javascript(
            application,
            dialog,
            'window.nfprogressNotes.getState()',
        ))['sortByStage'] is True,
    )

    _run_javascript(
        application,
        dialog,
        """
        (() => {
          const input = document.getElementById('search-input');
          input.value = 'Финальная вычитка';
          input.dispatchEvent(new Event('input', { bubbles: true }));
          return true;
        })()
        """,
    )
    assert _wait_until(
        application,
        lambda: len(json.loads(_run_javascript(
            application,
            dialog,
            'window.nfprogressNotes.getState()',
        ))['visibleIds']) == 1,
    )
    assert _run_javascript(
        application,
        dialog,
        "document.querySelector('.stage-badge').textContent",
    ) == 'Этап: Редактура'

    _run_javascript(
        application,
        dialog,
        """
        (() => {
          const search = document.getElementById('search-input');
          search.value = '';
          search.dispatchEvent(new Event('input', { bubbles: true }));
          return true;
        })()
        """,
    )
    assert _wait_until(
        application,
        lambda: len(json.loads(_run_javascript(
            application,
            dialog,
            'window.nfprogressNotes.getState()',
        ))['visibleIds']) == 2,
    )
    _run_javascript(
        application,
        dialog,
        f"""
        (() => {{
          document.querySelector(
            '.notes-grid [data-stage-id="{draft.stage_id}"] .note-card'
          ).click();
          const title = document.querySelector(
            '.note-editor-item[data-stage-id="{draft.stage_id}"] .note-title'
          );
          title.value = 'Новая первая глава';
          title.dispatchEvent(new Event('input', {{ bubbles: true }}));
          return true;
        }})()
        """,
    )
    assert _wait_until(
        application,
        lambda: draft.project_notes[0]['title'] == 'Новая первая глава',
    )
    dialog.close()
    assert _wait_until(application, lambda: not dialog.isVisible())
    dialog.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    application.processEvents()


@requires_native_webview
def test_notes_cards_follow_addition_order_and_snap_to_grid(monkeypatch):
    application = QApplication.instance() or QApplication([])
    project = engine.Project(name='Grid Notes', goal=1000)
    project.project_notes = engine.normalize_project_note_records([
        {
            'id': f'grid-{index}',
            'title': '' if index == 4 else f'Заметка {index + 1}',
            'content': f'<p>Текст карточки {index + 1}</p>',
            'sort_order': index,
            'created_at': f'2026-01-01T00:00:0{index}+00:00',
        }
        for index in range(5)
    ])
    service, _, _ = _service(monkeypatch, project)
    dialog = ProjectNotesDialog(service, lambda _owner, _node_id: None)
    dialog.resize(1280, 760)
    dialog.show()

    assert _wait_until(application, lambda: dialog._ready)
    assert _wait_until(
        application,
        lambda: len(json.loads(_run_javascript(
            application,
            dialog,
            'window.nfprogressNotes.getState()',
        ))['visibleIds']) == 5,
    )
    layout = json.loads(_run_javascript(
        application,
        dialog,
        """
        (() => {
          const grid = document.getElementById('other-grid').getBoundingClientRect();
          const items = [...document.querySelectorAll('#other-grid .note-item')]
            .map(item => {
              const rect = item.getBoundingClientRect();
              return {
                id: item.dataset.noteId,
                left: rect.left - grid.left,
                top: rect.top - grid.top,
                width: rect.width,
                height: rect.height
              };
            });
          return JSON.stringify(items);
        })()
        """,
    ))
    assert [item['id'] for item in layout] == [f'grid-{index}' for index in range(5)]
    first_row = [item for item in layout if abs(item['top'] - layout[0]['top']) < 2]
    assert len(first_row) == 4
    assert len({round(item['left']) for item in first_row}) == 4
    for item in layout:
        column = item['left'] / item['width']
        assert abs(column - round(column)) < 0.03
    for index, item in enumerate(layout):
        for other in layout[index + 1:]:
            horizontal_overlap = (
                item['left'] < other['left'] + other['width'] - 1
                and other['left'] < item['left'] + item['width'] - 1
            )
            vertical_overlap = (
                item['top'] < other['top'] + other['height'] - 1
                and other['top'] < item['top'] + item['height'] - 1
            )
            assert not (horizontal_overlap and vertical_overlap)
    assert json.loads(_run_javascript(
        application,
        dialog,
        """
        JSON.stringify({
          toolbars: document.querySelectorAll('.notes-grid .rich-toolbar').length,
          editables: document.querySelectorAll(
            '.notes-grid [contenteditable="true"], .notes-grid textarea'
          ).length
        })
        """,
    )) == {'toolbars': 0, 'editables': 0}
    assert json.loads(_run_javascript(
        application,
        dialog,
        """
        (() => {
          const card = document.querySelector('[data-note-id="grid-4"] .note-card');
          return JSON.stringify({
            titleVisible: Boolean(card.querySelector('.note-preview-title')),
            content: card.querySelector('.note-content-preview')?.textContent || ''
          });
        })()
        """,
    )) == {'titleVisible': False, 'content': 'Текст карточки 5'}

    _run_javascript(
        application,
        dialog,
        """
        document.querySelector(
          '.notes-grid [data-note-id="grid-2"] .note-card'
        ).click(); true
        """,
    )
    editor_state = json.loads(_run_javascript(
        application,
        dialog,
        'window.nfprogressNotes.getState()',
    ))
    assert editor_state['editorOpen'] is True
    assert editor_state['activeNoteId'] == 'grid-2'
    assert _run_javascript(
        application,
        dialog,
        "document.querySelectorAll('.note-editor-item .rich-toolbar').length",
    ) == 1
    _run_javascript(
        application,
        dialog,
        "document.getElementById('note-editor-done').click(); true",
    )
    assert _wait_until(
        application,
        lambda: _run_javascript(
            application,
            dialog,
            """
            (() => {
              const grid = document.getElementById('other-grid');
              const item = grid.querySelector('.note-item');
              return grid.getBoundingClientRect().height
                > item.getBoundingClientRect().height;
            })()
            """,
        ),
    )

    _run_javascript(
        application,
        dialog,
        """
        (() => {
          const handle = document.querySelector('[data-note-id="grid-0"] .drag-handle');
          handle.dispatchEvent(new KeyboardEvent('keydown', {
            bubbles: true,
            key: 'ArrowRight'
          }));
          return true;
        })()
        """,
    )
    assert _wait_until(
        application,
        lambda: json.loads(_run_javascript(
            application,
            dialog,
            'window.nfprogressNotes.getState()',
        ))['visibleIds'][:2] == ['grid-1', 'grid-0'],
    )
    assert _wait_until(
        application,
        lambda: next(
            note['sort_order'] for note in project.project_notes
            if note['id'] == 'grid-1'
        ) == 0,
    )

    dialog.close()
    assert _wait_until(application, lambda: not dialog.isVisible())
    dialog.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    application.processEvents()


@requires_native_webview
def test_mindmap_dialog_applies_silent_notes_commands_to_the_linked_node():
    application = QApplication.instance() or QApplication([])
    saved = []
    dialog = MindMapDialog(
        'Native Map',
        _map_data(),
        saved.append,
        focus_node_id='map-note',
    )
    dialog.show()

    assert _wait_until(application, lambda: dialog._ready)
    _process_events_for(application)
    assert bool(_run_javascript(
        application,
        dialog,
        """
        [...document.querySelectorAll('me-tpc')].some(
          element => element.nodeObj.id === 'map-note'
            && element.classList.contains('selected')
        )
        """,
    )) is True

    dialog.apply_notes_command('update', 'map-note', 'Из карточки')
    _process_events_for(application)
    updated = json.loads(_run_javascript(
        application,
        dialog,
        'window.nfprogressMindMap.getDataString()',
    ))
    assert updated['freeNodes'][0]['topic'] == 'Из карточки'
    assert saved == []

    dialog.apply_notes_command('delete', 'map-note')
    _process_events_for(application)
    remaining = json.loads(_run_javascript(
        application,
        dialog,
        'window.nfprogressMindMap.getDataString()',
    ))
    assert remaining['freeNodes'] == []
    assert remaining['nodeData']['id'] == 'root-node'
    assert remaining['nodeData']['children'][0]['id'] == 'scene-node'
    assert saved == []

    dialog._allow_close = True
    dialog.close()
    dialog.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    application.processEvents()
