import json
import os
import time

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS', '--disable-gpu --no-sandbox')

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication

import engine
from main_UI import MainWindow
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
    project.migrate()
    assert project.mindmap_data is None

    project.mindmap_data = _map_data()
    project.migrate()
    assert project.mindmap_data == _map_data()

    stage = engine.Stage(name='Draft', goal=500, parent_project_name='Book')
    stage.mindmap_data = {'nodeData': {'id': '', 'topic': 'Draft', 'children': []}}
    stage.migrate()
    assert stage.mindmap_data is None


def test_project_and_stage_maps_are_independent():
    project = engine.Project(name='Book', goal=1000)
    project.mindmap_data = _map_data('Book plan')

    project.convert_to_stages()
    project.stages[0].mindmap_data = _map_data('Draft plan')

    assert project.mindmap_data == _map_data('Book plan')
    assert project.stages[0].mindmap_data == _map_data('Draft plan')


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
