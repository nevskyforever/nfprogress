import json
import os
import time

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS', '--disable-gpu --no-sandbox')

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication

import engine
import main_UI
from main_UI import EditProject, MainWindow
from mindmap import MindMapBridge, MindMapDialog


def _map_data(topic='Роман'):
    return {
        'nodeData': {
            'id': 'root-node',
            'topic': topic,
            'children': [],
        },
    }


def _wait_until(app, condition, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    return False


def _run_javascript(app, dialog, script):
    results = []
    dialog.web_view.page().runJavaScript(script, results.append)
    assert _wait_until(app, lambda: bool(results))
    return results[0]


def _process_events_for(app, duration):
    deadline = time.monotonic() + duration
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)


def test_project_and_stage_migrate_mindmap_data():
    project = engine.Project(name='Book', goal=1000)
    del project.mindmap_data
    del project.combine_stage_mindmaps
    project.migrate()
    assert project.mindmap_data is None
    assert project.combine_stage_mindmaps is False

    project.mindmap_data = _map_data()
    project.migrate()
    assert project.mindmap_data == _map_data()

    stage = engine.Stage(name='Draft', goal=500, parent_project_name='Book')
    stage.mindmap_data = {'nodeData': {'id': '', 'topic': 'Draft', 'children': []}}
    stage.migrate()
    assert stage.mindmap_data is None
    assert stage.combine_stage_mindmaps is False

    project.enable_stages = True
    project.stages = [stage]
    project.combine_stage_mindmaps = True
    project.migrate()
    assert project.combine_stage_mindmaps is True

    project.combine_stage_mindmaps = 'yes'
    project.migrate()
    assert project.combine_stage_mindmaps is False


def test_project_and_stage_maps_are_independent():
    project = engine.Project(name='Book', goal=1000)
    project.mindmap_data = _map_data('Book plan')

    project.convert_to_stages()
    project.stages[0].mindmap_data = _map_data('Draft plan')

    assert project.mindmap_data == _map_data('Book plan')
    assert project.stages[0].mindmap_data == _map_data('Draft plan')


def test_combined_project_map_round_trip_updates_stage_and_project_content():
    project = engine.Project(name='Book', goal=1000)
    project.mindmap_data = {
        'nodeData': {
            'id': 'project-root',
            'topic': 'Book plan',
            'children': [
                {'id': 'project-note', 'topic': 'General note', 'children': []},
            ],
        },
        'arrows': [],
        'summaries': [],
    }
    draft = engine.Stage(
        name='Draft',
        goal=500,
        parent_project_name='Book',
        stage_id='draft-stage',
    )
    draft.mindmap_data = {
        'nodeData': {
            'id': 'stage-root',
            'topic': 'Draft plan',
            'children': [
                {'id': 'scene', 'topic': 'First scene', 'children': []},
            ],
        },
        'arrows': [
            {
                'id': 'stage-link',
                'from': 'stage-root',
                'to': 'scene',
                'label': 'Order',
            },
        ],
        'summaries': [
            {
                'id': 'stage-summary',
                'parent': 'stage-root',
                'start': 0,
                'end': 0,
                'label': 'Opening',
            },
        ],
    }
    editing = engine.Stage(
        name='Editing',
        goal=500,
        parent_project_name='Book',
        stage_id='editing-stage',
    )
    project.enable_stages = True
    project.stages = [draft, editing]
    project.combine_stage_mindmaps = True

    combined = engine.compose_project_mindmap(project)
    own_node, draft_branch, editing_branch = combined['nodeData']['children']
    assert own_node['topic'] == 'General note'
    assert draft_branch['topic'] == 'Draft'
    assert editing_branch['topic'] == 'Editing'
    assert draft_branch['nfprogressStageId'] == draft.stage_id
    assert draft_branch['nfprogressStageRoot'] is True
    assert editing_branch['children'] == []
    assert project.mindmap_data['nodeData']['children'] == [
        {'id': 'project-note', 'topic': 'General note', 'children': []},
    ]

    draft_branch['topic'] = 'This must not rename the stage root'
    draft_branch['children'][0]['topic'] = 'Changed scene'
    draft_branch['children'].append({
        'id': 'new-stage-node',
        'topic': 'Second scene',
        'children': [],
    })
    own_node['topic'] = 'Changed general note'
    combined['nodeData']['children'].insert(1, {
        'id': 'new-project-node',
        'topic': 'Project-only idea',
        'children': [],
    })
    combined['arrows'].extend([
        {
            'id': 'stage-arrow',
            'from': draft_branch['children'][0]['id'],
            'to': 'new-stage-node',
        },
        {
            'id': 'cross-arrow',
            'from': 'new-stage-node',
            'to': 'new-project-node',
        },
    ])

    project_map, stage_maps = engine.split_combined_project_mindmap(
        project,
        combined,
    )

    assert [node['topic'] for node in project_map['nodeData']['children']] == [
        'Changed general note',
        'Project-only idea',
    ]
    assert stage_maps[draft.stage_id]['nodeData']['topic'] == 'Draft plan'
    assert [
        node['topic']
        for node in stage_maps[draft.stage_id]['nodeData']['children']
    ] == ['Changed scene', 'Second scene']
    assert stage_maps[draft.stage_id]['arrows'] == [
        {
            'id': 'stage-link',
            'from': 'stage-root',
            'to': 'scene',
            'label': 'Order',
        },
        {
            'id': 'stage-arrow',
            'from': 'scene',
            'to': 'new-stage-node',
        },
    ]
    assert stage_maps[draft.stage_id]['summaries'] == [
        {
            'id': 'stage-summary',
            'parent': 'stage-root',
            'start': 0,
            'end': 0,
            'label': 'Opening',
        },
    ]
    assert stage_maps[editing.stage_id]['nodeData']['topic'] == 'Editing'
    assert len(project_map['arrows']) == 1
    assert project_map['arrows'][0]['to'] == 'new-project-node'
    serialized_results = json.dumps([project_map, stage_maps])
    assert 'nfprogressStageId' not in serialized_results
    assert 'nfprogressStageRoot' not in serialized_results
    assert 'nfprogressSourceId' not in serialized_results

    project.mindmap_data = project_map
    draft.mindmap_data = stage_maps[draft.stage_id]
    editing.mindmap_data = stage_maps[editing.stage_id]
    recomposed = engine.compose_project_mindmap(project)
    node_ids = set()

    def collect_ids(node):
        node_ids.add(node['id'])
        for child in node.get('children', []):
            collect_ids(child)

    collect_ids(recomposed['nodeData'])
    cross_arrow = next(
        arrow for arrow in recomposed['arrows']
        if arrow['id'] == 'cross-arrow'
    )
    assert cross_arrow['from'] in node_ids
    assert cross_arrow['to'] in node_ids


def test_combined_project_map_tracks_stage_names_and_order():
    project = engine.Project(name='Book', goal=1000)
    first = engine.Stage(
        name='Draft',
        goal=500,
        parent_project_name='Book',
        stage_id='draft-stage',
    )
    second = engine.Stage(
        name='Editing',
        goal=500,
        parent_project_name='Book',
        stage_id='editing-stage',
    )
    first.mindmap_data = _map_data('Independent draft root')
    second.mindmap_data = _map_data('Independent editing root')
    project.enable_stages = True
    project.combine_stage_mindmaps = True
    project.stages = [first, second]

    first._name = 'First draft'
    project.stages = [second, first]
    combined = engine.compose_project_mindmap(project)

    assert [
        child['topic'] for child in combined['nodeData']['children']
    ] == ['Editing', 'First draft']
    assert first.mindmap_data['nodeData']['topic'] == 'Independent draft root'
    assert second.mindmap_data['nodeData']['topic'] == 'Independent editing root'


def test_combined_map_marks_completed_stage_without_notice_node():
    project = engine.Project(name='Book', goal=1000)
    completed = engine.Stage(
        name='Editing',
        goal=1000,
        parent_project_name='Book',
        stage_id='editing-stage',
        status='завершен',
    )
    completed.mindmap_data = _map_data('Editing')
    project.enable_stages = True
    project.combine_stage_mindmaps = True
    project.stages = [completed]

    combined = engine.compose_project_mindmap(project)
    stage_branch = combined['nodeData']['children'][0]

    assert stage_branch['topic'] == '✅ Editing'
    assert stage_branch['nfprogressReadOnly'] is True
    assert stage_branch['nfprogressEmptyStageMap'] is True
    assert stage_branch['children'] == []

    _, stage_maps = engine.split_combined_project_mindmap(project, combined)
    assert stage_maps[completed.stage_id]['nodeData'] == _map_data(
        'Editing'
    )['nodeData']
    assert stage_maps[completed.stage_id]['arrows'] == []
    assert stage_maps[completed.stage_id]['summaries'] == []
    assert 'nfprogress' not in json.dumps(stage_maps)


def test_combined_map_passes_empty_stage_message_to_status_area(monkeypatch):
    project = engine.Project(name='Book', goal=1000)
    completed = engine.Stage(
        name='Editing',
        goal=1000,
        parent_project_name='Book',
        status='завершен',
    )
    completed.mindmap_data = _map_data('Editing')
    project.enable_stages = True
    project.combine_stage_mindmaps = True
    project.stages = [completed]
    opened = []

    class FakeDialog:
        def __init__(self, *args, **kwargs):
            opened.append((args, kwargs))

        def exec(self):
            return None

    monkeypatch.setattr(main_UI, 'MindMapDialog', FakeDialog)

    class Owner:
        _is_stage = MainWindow._is_stage
        _save_mindmap_data = MainWindow._save_mindmap_data

    MainWindow.open_mindmap(Owner(), project)

    assert opened[0][0][1]['nodeData']['children'][0]['children'] == []
    assert opened[0][1]['status_message'] == (
        'Карта не была создана при работе над этапом.'
    )


def test_mindmap_bridge_validates_and_deduplicates_saves():
    saved = []
    failures = []
    bridge = MindMapBridge('Роман', None, False, saved.append)
    bridge.failed.connect(failures.append)

    payload = json.dumps(_map_data(), ensure_ascii=False)
    assert bridge.persist_payload(payload) is True
    assert bridge.persist_payload(payload) is True
    assert saved == [_map_data()]

    assert bridge.persist_payload('{"nodeData": {}}') is False
    assert failures
    assert saved == [_map_data()]

    read_only_bridge = MindMapBridge('Роман', _map_data(), True, saved.append)
    assert read_only_bridge.persist_payload(payload) is True
    assert saved == [_map_data()]


def test_saving_map_preserves_fresh_project_progress(monkeypatch):
    selected_project = engine.Project(name='Book', goal=1000, total_symbols=100)
    stored_project = engine.Project(name='Book', goal=1000, total_symbols=700)
    stored_data = {'projects': {'Book': stored_project}}
    saved_data = []
    monkeypatch.setattr(engine, 'load_data', lambda: stored_data)
    monkeypatch.setattr(engine, 'save_data', saved_data.append)

    class Owner:
        _is_stage = MainWindow._is_stage
        _find_stage_parent = MainWindow._find_stage_parent

    MainWindow._save_mindmap_data(Owner(), selected_project, _map_data())

    assert stored_project.total_units == 700
    assert stored_project.mindmap_data == _map_data()
    assert selected_project.mindmap_data == _map_data()
    assert saved_data == [stored_data]


def test_saving_combined_map_updates_stage_without_stale_progress(monkeypatch):
    selected_project = engine.Project(name='Book', goal=1000)
    selected_stage = engine.Stage(
        name='Draft',
        goal=1000,
        total_symbols=100,
        parent_project_name='Book',
        stage_id='draft-stage',
    )
    selected_stage.mindmap_data = _map_data('Draft plan')
    selected_completed_stage = engine.Stage(
        name='Editing',
        goal=1000,
        parent_project_name='Book',
        stage_id='editing-stage',
        status='завершен',
    )
    selected_completed_stage.mindmap_data = _map_data('Editing plan')
    selected_project.enable_stages = True
    selected_project.combine_stage_mindmaps = True
    selected_project.stages = [selected_stage, selected_completed_stage]

    stored_project = engine.Project(name='Book', goal=1000)
    stored_stage = engine.Stage(
        name='Draft',
        goal=1000,
        total_symbols=700,
        parent_project_name='Book',
        stage_id='draft-stage',
    )
    stored_stage.mindmap_data = _map_data('Draft plan')
    stored_completed_stage = engine.Stage(
        name='Editing',
        goal=1000,
        parent_project_name='Book',
        stage_id='editing-stage',
        status='завершен',
    )
    stored_completed_stage.mindmap_data = _map_data('Editing plan')
    stored_project.enable_stages = True
    stored_project.combine_stage_mindmaps = True
    stored_project.stages = [stored_stage, stored_completed_stage]
    stored_data = {'projects': {'Book': stored_project}}
    saved_data = []
    monkeypatch.setattr(engine, 'load_data', lambda: stored_data)
    monkeypatch.setattr(engine, 'save_data', saved_data.append)
    monkeypatch.setattr(engine, 'dev_mode', True)

    combined = engine.compose_project_mindmap(selected_project)
    stage_branch = combined['nodeData']['children'][0]
    stage_branch['children'].append({
        'id': 'new-stage-node',
        'topic': 'New scene',
        'children': [],
    })
    completed_branch = combined['nodeData']['children'][1]
    completed_branch['children'].append({
        'id': 'discarded-completed-node',
        'topic': 'Must stay read-only',
        'children': [],
    })

    class Owner:
        _is_stage = MainWindow._is_stage
        _find_stage_parent = MainWindow._find_stage_parent

    MainWindow._save_mindmap_data(
        Owner(),
        selected_project,
        combined,
        combined_stage_maps=True,
    )

    assert stored_stage.total_units == 700
    assert stored_stage.mindmap_data['nodeData']['children'][0]['topic'] == 'New scene'
    assert stored_completed_stage.mindmap_data == _map_data('Editing plan')
    assert selected_stage.mindmap_data == stored_stage.mindmap_data
    assert stored_project.mindmap_data['nodeData']['children'] == []
    assert saved_data == [stored_data]


def test_empty_completed_stage_map_shows_explanation_instead_of_editor(
        monkeypatch,
):
    stage = engine.Stage(
        name='Editing',
        goal=1000,
        parent_project_name='Book',
        status='завершен',
    )
    stage.mindmap_data = _map_data('Editing')
    messages = []
    opened = []
    monkeypatch.setattr(
        main_UI.QMessageBox,
        'information',
        lambda parent, title, message: messages.append((title, message)),
    )
    monkeypatch.setattr(
        main_UI,
        'MindMapDialog',
        lambda *args, **kwargs: opened.append((args, kwargs)),
    )

    class Owner:
        _is_stage = MainWindow._is_stage
        _save_mindmap_data = MainWindow._save_mindmap_data

    MainWindow.open_mindmap(Owner(), stage)

    assert messages == [
        ('Карта', 'Карта не была создана при работе над этапом.'),
    ]
    assert opened == []


def test_completed_stage_map_opens_read_only_even_in_developer_mode(monkeypatch):
    stage = engine.Stage(
        name='Editing',
        goal=1000,
        parent_project_name='Book',
        status='завершен',
    )
    stage.mindmap_data = _map_data('Editing plan')
    opened = []

    class FakeDialog:
        def __init__(self, *args, **kwargs):
            opened.append((args, kwargs))

        def exec(self):
            return None

    monkeypatch.setattr(main_UI, 'MindMapDialog', FakeDialog)
    monkeypatch.setattr(engine, 'dev_mode', True)

    class Owner:
        _is_stage = MainWindow._is_stage
        _save_mindmap_data = MainWindow._save_mindmap_data

    MainWindow.open_mindmap(Owner(), stage)

    assert opened[0][1]['read_only'] is True


def test_edit_project_shows_combined_map_checkbox_for_staged_project(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(
        engine,
        'load_settings',
        lambda: {'global_streak': False, 'game_mode': False},
    )
    project = engine.Project(name='Book', goal=1000)
    project.enable_stages = True
    project.stages = [
        engine.Stage(
            name='Draft',
            goal=1000,
            parent_project_name='Book',
        ),
    ]
    project.combine_stage_mindmaps = True

    dialog = EditProject(project)
    app.processEvents()
    assert not dialog.combine_stage_mindmaps_checkBox.isHidden()
    assert dialog.is_combined_mindmap_enabled() is True

    dialog.close()
    dialog.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


def test_mindmap_dialog_loads_local_editor_and_creates_default_map():
    app = QApplication.instance() or QApplication([])
    saved = []
    dialog = MindMapDialog('Тестовая книга', None, saved.append)
    dialog.show()

    assert _wait_until(app, lambda: dialog._ready and bool(saved))
    assert saved[0]['nodeData']['topic'] == 'Тестовая книга'
    assert dialog.save_status_label.text()

    results = []
    dialog.web_view.page().runJavaScript(
        'window.nfprogressMindMap.getDataString()',
        results.append,
    )
    assert _wait_until(app, lambda: bool(results))
    assert json.loads(results[0])['nodeData']['topic'] == 'Тестовая книга'

    dialog._allow_close = True
    dialog.close()
    dialog.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


def test_mindmap_dialog_displays_empty_stage_message_in_status_area():
    app = QApplication.instance() or QApplication([])
    message = 'Карта не была создана при работе над этапом.'
    dialog = MindMapDialog(
        'Book',
        _map_data('Book'),
        lambda data: None,
        status_message=message,
    )
    dialog.show()

    assert _wait_until(app, lambda: dialog._ready)
    assert dialog.save_status_label.text() == message
    assert dialog._bridge.last_error == ''

    dialog._allow_close = True
    dialog.close()
    dialog.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


def test_mindmap_focus_control_opens_and_closes_first_level_branch():
    app = QApplication.instance() or QApplication([])
    map_data = {
        'nodeData': {
            'id': 'book-root',
            'topic': 'Book',
            'children': [{
                'id': 'draft-branch',
                'topic': 'Draft',
                'children': [{
                    'id': 'scene',
                    'topic': 'First scene',
                    'children': [],
                }],
            }],
        },
    }
    dialog = MindMapDialog('Book', map_data, lambda data: None)
    dialog.show()

    assert _wait_until(app, lambda: dialog._ready)
    assert _run_javascript(
        app,
        dialog,
        """
        (() => {
          const branch = [...document.querySelectorAll('me-tpc')].find(
            element => element.nodeObj.topic === 'Draft'
          );
          branch.dispatchEvent(new PointerEvent('pointerdown', {
            bubbles: true,
            button: 0,
            pointerId: 1,
            pointerType: 'mouse',
          }));
          branch.dispatchEvent(new PointerEvent('pointerup', {
            bubbles: true,
            button: 0,
            pointerId: 1,
            pointerType: 'mouse',
          }));
          return Boolean(document.querySelector('#focusBranch'));
        })()
        """,
    ) is True
    _process_events_for(app, 0.03)
    focus_state = json.loads(_run_javascript(
        app,
        dialog,
        """
        (() => {
          const control = document.querySelector('#focusBranch');
          control.click();
          return JSON.stringify({
            rootTopic: document.querySelector('me-root > me-tpc').nodeObj.topic,
            active: control.classList.contains('nfprogress-focus-active'),
          });
        })()
        """,
    ))
    assert focus_state == {'rootTopic': 'Draft', 'active': True}
    _process_events_for(app, 0.1)
    assert dialog._bridge.last_error == ''
    assert dialog.save_status_label.text() == 'Карта готова.'
    restored_state = json.loads(_run_javascript(
        app,
        dialog,
        """
        (() => {
          const control = document.querySelector('#focusBranch');
          control.click();
          return JSON.stringify({
            rootTopic: document.querySelector('me-root > me-tpc').nodeObj.topic,
            active: control.classList.contains('nfprogress-focus-active'),
          });
        })()
        """,
    ))
    assert restored_state == {'rootTopic': 'Book', 'active': False}

    dialog._allow_close = True
    dialog.close()
    dialog.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


def test_focus_control_reports_empty_completed_stage_in_status_area():
    app = QApplication.instance() or QApplication([])
    project = engine.Project(name='Book', goal=1000)
    stage = engine.Stage(
        name='Editing',
        goal=1000,
        parent_project_name='Book',
        stage_id='editing-stage',
        status='завершен',
    )
    stage.mindmap_data = _map_data('Editing')
    project.enable_stages = True
    project.combine_stage_mindmaps = True
    project.stages = [stage]
    message = 'Карта не была создана при работе над этапом.'
    dialog = MindMapDialog(
        project.name,
        engine.compose_project_mindmap(project),
        lambda data: None,
        status_message=message,
    )
    dialog.show()

    assert _wait_until(app, lambda: dialog._ready)
    dialog._on_editor_saved()
    assert dialog.save_status_label.text() == 'Все изменения сохранены.'
    assert _run_javascript(
        app,
        dialog,
        """
        (() => {
          const branch = [...document.querySelectorAll('me-tpc')].find(
            element => element.nodeObj.nfprogressEmptyStageMap
          );
          branch.dispatchEvent(new PointerEvent('pointerdown', {
            bubbles: true,
            button: 0,
            pointerId: 1,
            pointerType: 'mouse',
          }));
          branch.dispatchEvent(new PointerEvent('pointerup', {
            bubbles: true,
            button: 0,
            pointerId: 1,
            pointerType: 'mouse',
          }));
          return Boolean(branch);
        })()
        """,
    ) is True
    _process_events_for(app, 0.03)
    focus_state = json.loads(_run_javascript(
        app,
        dialog,
        """
        (() => {
          const control = document.querySelector('#focusBranch');
          control.click();
          return JSON.stringify({
            rootTopic: document.querySelector('me-root > me-tpc').nodeObj.topic,
            active: control.classList.contains('nfprogress-focus-active'),
          });
        })()
        """,
    ))

    assert focus_state == {'rootTopic': 'Book', 'active': False}
    assert _wait_until(app, lambda: dialog.save_status_label.text() == message)
    assert dialog._bridge.last_error == ''

    dialog._allow_close = True
    dialog.close()
    dialog.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


def test_combined_stage_branch_edit_round_trips_through_editor():
    app = QApplication.instance() or QApplication([])
    project = engine.Project(name='Book', goal=1000)
    stage = engine.Stage(
        name='Draft',
        goal=1000,
        parent_project_name='Book',
        stage_id='draft-stage',
    )
    stage.mindmap_data = {
        'nodeData': {
            'id': 'stage-root',
            'topic': 'Draft plan',
            'children': [
                {'id': 'scene', 'topic': 'First scene', 'children': []},
            ],
        },
    }
    project.enable_stages = True
    project.combine_stage_mindmaps = True
    project.stages = [stage]
    saved = []
    dialog = MindMapDialog(
        project.name,
        engine.compose_project_mindmap(project),
        saved.append,
    )
    dialog.show()

    assert _wait_until(app, lambda: dialog._ready)
    assert _run_javascript(
        app,
        dialog,
        """
        (() => {
          const node = [...document.querySelectorAll('me-tpc')].find(
            element => element.nodeObj.topic === 'First scene'
          );
          node.dispatchEvent(new PointerEvent('pointerup', {
            bubbles: true,
            button: 0,
            pointerType: 'mouse',
          }));
          return Boolean(node.nodeObj.nfprogressStageId);
        })()
        """,
    )
    _process_events_for(app, 0.03)
    assert _run_javascript(
        app,
        dialog,
        """
        (() => {
          const node = [...document.querySelectorAll('me-tpc')].find(
            element => element.nodeObj.topic === 'First scene'
          );
          node.dispatchEvent(new PointerEvent('pointerup', {
            bubbles: true,
            button: 0,
            pointerType: 'mouse',
          }));
          const editor = document.querySelector('#input-box');
          editor.textContent = 'Changed in project map';
          editor.dispatchEvent(new FocusEvent('blur'));
          return !document.querySelector('#input-box');
        })()
        """,
    )
    assert _wait_until(app, lambda: bool(saved))

    _, stage_maps = engine.split_combined_project_mindmap(
        project,
        saved[-1],
    )
    assert (
        stage_maps[stage.stage_id]['nodeData']['children'][0]['topic']
        == 'Changed in project map'
    )

    dialog._allow_close = True
    dialog.close()
    dialog.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


def test_completed_stage_branch_is_read_only_in_combined_editor():
    app = QApplication.instance() or QApplication([])
    project = engine.Project(name='Book', goal=1000)
    stage = engine.Stage(
        name='Editing',
        goal=1000,
        parent_project_name='Book',
        stage_id='editing-stage',
        status='завершен',
    )
    stage.mindmap_data = {
        'nodeData': {
            'id': 'stage-root',
            'topic': 'Editing plan',
            'children': [
                {'id': 'scene', 'topic': 'First scene', 'children': []},
            ],
        },
    }
    project.enable_stages = True
    project.combine_stage_mindmaps = True
    project.stages = [stage]
    saved = []
    dialog = MindMapDialog(
        project.name,
        engine.compose_project_mindmap(project),
        saved.append,
    )
    dialog.show()

    assert _wait_until(app, lambda: dialog._ready)
    edit_state = json.loads(_run_javascript(
        app,
        dialog,
        """
        (() => {
          const node = [...document.querySelectorAll('me-tpc')].find(
            element => element.nodeObj.topic === 'First scene'
          );
          node.dispatchEvent(new PointerEvent('pointerup', {
            bubbles: true,
            button: 0,
            pointerType: 'mouse',
          }));
          node.dispatchEvent(new PointerEvent('pointerup', {
            bubbles: true,
            button: 0,
            pointerType: 'mouse',
          }));
          return JSON.stringify({
            markedReadOnly: node.classList.contains(
              'nfprogress-read-only-stage'
            ),
            editorOpened: Boolean(document.querySelector('#input-box')),
          });
        })()
        """,
    ))
    assert edit_state == {
        'markedReadOnly': True,
        'editorOpened': False,
    }

    dialog._allow_close = True
    dialog.close()
    dialog.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


def test_mindmap_autosave_keeps_node_editor_open():
    app = QApplication.instance() or QApplication([])
    saved = []
    dialog = MindMapDialog('Тестовая книга', _map_data(), saved.append)
    dialog.show()

    assert _wait_until(app, lambda: dialog._ready)
    assert _run_javascript(
        app,
        dialog,
        """
        (() => {
          const node = document.querySelector('me-tpc');
          node.dispatchEvent(new PointerEvent('pointerup', {
            bubbles: true,
            button: 0,
            pointerType: 'mouse',
          }));
          return Boolean(node);
        })()
        """,
    )
    _process_events_for(app, 0.03)
    assert _run_javascript(
        app,
        dialog,
        """
        (() => {
          const node = document.querySelector('me-tpc');
          node.dispatchEvent(new PointerEvent('pointerup', {
            bubbles: true,
            button: 0,
            pointerType: 'mouse',
          }));
          const editor = document.querySelector('#input-box');
          window.__mindmapEditorBlurred = false;
          editor.blur = () => { window.__mindmapEditorBlurred = true; };
          window.setTimeout(() => editor.focus(), 390);
          return Boolean(editor);
        })()
        """,
    )

    _process_events_for(app, 0.7)
    edit_state = json.loads(_run_javascript(
        app,
        dialog,
        """
        JSON.stringify({
          editing: Boolean(document.querySelector('#input-box')),
          blurred: window.__mindmapEditorBlurred,
        })
        """,
    ))
    assert edit_state == {'editing': True, 'blurred': False}

    assert _run_javascript(
        app,
        dialog,
        """
        (() => {
          const editor = document.querySelector('#input-box');
          editor.textContent = 'Новая глава';
          editor.dispatchEvent(new FocusEvent('blur'));
          return !document.querySelector('#input-box');
        })()
        """,
    )
    assert _wait_until(
        app,
        lambda: (
            bool(saved)
            and saved[-1]['nodeData']['topic'] == 'Новая глава'
        ),
    )

    dialog._allow_close = True
    dialog.close()
    dialog.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()
