"""Mind Elixir editor embedded in a native Qt WebView dialog."""

import base64
import json
from pathlib import Path

from PySide6.QtCore import Q_ARG, QMetaObject, QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QCloseEvent
from PySide6.QtQuick import QQuickView
from PySide6.QtWebView import QtWebView
from PySide6.QtWidgets import QDialog, QFileDialog, QMenu, QVBoxLayout, QWidget

import engine
from UI_fiiles.mindmap_dialog import Ui_mindmap_dialog
from localization import (
    LocalizedMessageBox as QMessageBox,
    current_language,
    tr,
)


QtWebView.initialize()


def _canonical_json(data):
    return json.dumps(
        data,
        ensure_ascii=False,
        sort_keys=True,
        separators=(',', ':'),
    )


def _without_module_exports(source):
    marker = '\nexport {'
    if marker not in source:
        raise ValueError('JavaScript module export block is missing.')
    return source.rsplit(marker, 1)[0]


def _standalone_editor_html(assets_path):
    """Build one offline document because native WebViews reject local file URLs."""
    index_html = (assets_path / 'index.html').read_text(encoding='utf-8')
    styles = (assets_path / 'MindElixir.css').read_text(encoding='utf-8')
    mind_elixir = _without_module_exports(
        (assets_path / 'MindElixir.js').read_text(encoding='utf-8')
    )
    translations = _without_module_exports(
        (assets_path / 'i18n.js').read_text(encoding='utf-8')
    )
    application = (assets_path / 'app.js').read_text(encoding='utf-8')
    application = '\n'.join(
        line for line in application.splitlines()
        if not line.startswith('import ')
    )
    bundle = '\n'.join((
        f'const MindElixir = (() => {{\n{mind_elixir}\nreturn P;\n}})();',
        'const { de, en, es, fr, pt, ru } = (() => {'
        f'\n{translations}\n'
        'return { de: v, en: n, es: r, fr: s, pt: l, ru: a };\n})();',
        application,
    ))
    index_html = index_html.replace(
        '<link rel="stylesheet" href="MindElixir.css">',
        f'<style>{styles}</style>',
    )
    return index_html.replace(
        '<script type="module" src="app.js"></script>',
        f'<script>{bundle}</script>',
    )


class MindMapBridge(QObject):
    """Expose initial data and persistence callbacks to the local editor page."""

    ready_received = Signal()
    changed_received = Signal()
    saved = Signal()
    failed = Signal(str)
    status_received = Signal(str)

    def __init__(self, entity_name, mindmap_data, read_only, save_callback, parent=None):
        super().__init__(parent)
        self.entity_name = entity_name
        self.mindmap_data = engine.normalize_mindmap_data(mindmap_data)
        self.read_only = bool(read_only)
        self.save_callback = save_callback
        self.last_error = ''
        self._last_serialized = (
            _canonical_json(self.mindmap_data)
            if self.mindmap_data is not None
            else None
        )

    @Slot(result=str)
    def initialPayload(self):
        return json.dumps(
            {
                'data': self.mindmap_data,
                'editorLabel': tr('Редактор карты'),
                'emptyStageMapText': tr(
                    'Карта не была создана при работе над этапом.'
                ),
                'floatingNodeName': tr('Свободный узел'),
                'floatingNoteName': tr('Новая заметка'),
                'floatingItemsLabel': tr('Свободные элементы карты'),
                'addFloatingNodeLabel': tr('Добавить свободный узел'),
                'addFloatingNoteLabel': tr('Добавить плавающую заметку'),
                'locale': current_language(),
                'loadingText': tr('Загрузка карты…'),
                'newTopicName': tr('Новая тема'),
                'readOnly': self.read_only,
                'rootTopic': self.entity_name,
            },
            ensure_ascii=False,
        )

    @Slot()
    def ready(self):
        self.ready_received.emit()

    @Slot()
    def changed(self):
        if not self.read_only:
            self.changed_received.emit()

    @Slot(str)
    def save(self, payload):
        self.persist_payload(payload)

    @Slot(str)
    def reportError(self, details):
        self.last_error = str(details)
        self.failed.emit(tr('Не удалось загрузить редактор карты.'))

    @Slot(str)
    def showStatus(self, message):
        self.status_received.emit(str(message))

    def persist_payload(self, payload):
        if self.read_only:
            return True

        try:
            parsed = json.loads(payload)
            normalized = engine.normalize_mindmap_data(parsed)
            if normalized is None:
                raise ValueError(tr('Редактор вернул повреждённые данные карты.'))
            serialized = _canonical_json(normalized)
            if serialized != self._last_serialized:
                self.save_callback(normalized)
                self._last_serialized = serialized
            self.mindmap_data = normalized
        except Exception as error:
            self.last_error = str(error)
            self.failed.emit(tr('Не удалось сохранить карту.'))
            return False

        self.last_error = ''
        self.saved.emit()
        return True


class NativeWebView(QWidget):
    """Expose the QML WebView through the small API used by the dialog."""

    loadFinished = Signal(bool, str)

    def __init__(self, qml_path, parent=None):
        super().__init__(parent)
        self._callbacks = {}
        self._next_request_id = 1
        self._view = QQuickView()
        self._view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        self._view.setSource(QUrl.fromLocalFile(str(qml_path)))
        self._container = QWidget.createWindowContainer(self._view, self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._container)

        root = self._view.rootObject()
        if root is None:
            details = '; '.join(error.toString() for error in self._view.errors())
            raise RuntimeError(details or tr('Не удалось загрузить редактор карты.'))
        self._root = root
        self._root.pageLoadFinished.connect(self.loadFinished)
        self._root.javaScriptResult.connect(self._handle_java_script_result)

    def page(self):
        """Keep compatibility with the former QWebEngineView call sites."""
        return self

    def loadHtml(self, html):
        QMetaObject.invokeMethod(
            self._root,
            'loadHtml',
            Q_ARG('QVariant', html),
        )

    def runJavaScript(self, script, callback=None):
        request_id = self._next_request_id
        self._next_request_id += 1
        if callback is not None:
            self._callbacks[request_id] = callback
        invoked = QMetaObject.invokeMethod(
            self._root,
            'runJavaScript',
            Q_ARG('QVariant', script),
            Q_ARG('QVariant', request_id),
        )
        if not invoked:
            self._callbacks.pop(request_id, None)
            if callback is not None:
                callback(None)

    def shutdown(self):
        self._callbacks.clear()
        try:
            self._root.pageLoadFinished.disconnect(self.loadFinished)
            self._root.javaScriptResult.disconnect(self._handle_java_script_result)
        except RuntimeError:
            pass
        self._view.setSource(QUrl())

    @Slot(int, object)
    def _handle_java_script_result(self, request_id, result):
        callback = self._callbacks.pop(request_id, None)
        if callback is not None:
            callback(result)


class MindMapDialog(QDialog, Ui_mindmap_dialog):
    EXPORT_FORMATS = {
        'png': (
            'Экспорт в PNG',
            'Экспортировать в PNG',
            'Изображение PNG (*.png)',
            '.png',
        ),
        'svg': (
            'Экспорт в SVG',
            'Экспортировать в SVG',
            'Векторное изображение SVG (*.svg)',
            '.svg',
        ),
        'json': (
            'Экспорт в JSON',
            'Экспортировать в JSON',
            'Карта Mind Elixir (*.json)',
            '.json',
        ),
    }

    def __init__(
            self,
            entity_name,
            mindmap_data,
            save_callback,
            *,
            read_only=False,
            status_message=None,
            parent=None,
    ):
        super().__init__(parent)
        self.setupUi(self)
        self.read_only = bool(read_only)
        self.status_message = status_message
        self._ready = False
        self._closing_after_save = False
        self._allow_close = False
        self._poll_in_flight = False
        self._export_in_progress = False

        self.setWindowTitle(f"{tr('Карта')} — {entity_name}")
        self.map_title_label.setText(f"{tr('Карта')}: {entity_name}")
        if self.read_only:
            self.instructions_label.setText(
                tr('Завершённый проект или этап: карта доступна только для просмотра.')
            )
        else:
            self.instructions_label.setText(
                tr(
                    'Выберите узел: Tab — дочерний, Enter — соседний, F2 — изменить, '
                    'Delete — удалить. Свободные узлы и заметки добавляются кнопками, '
                    'перетаскиваются за карточку и редактируются двойным щелчком или F2. '
                    'Для свободного узла Tab добавляет дочерний узел, Enter — соседний. '
                    'Карта сохраняется автоматически.'
                )
            )

        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self._request_explicit_save)
        self.export_button.setEnabled(False)
        self._export_menu = QMenu(self)
        for export_format, export_details in self.EXPORT_FORMATS.items():
            action = self._export_menu.addAction(
                tr(export_details[0]),
            )
            action.triggered.connect(
                lambda checked=False, format_name=export_format: self._request_export(
                    format_name,
                ),
            )
        self.export_button.setMenu(self._export_menu)
        self.close_button.clicked.connect(self.close)

        qml_path = Path(engine.resource_path('mindmap_assets/WebViewHost.qml'))
        try:
            self.web_view = NativeWebView(qml_path, self.mindmap_container)
        except RuntimeError as error:
            self._on_editor_failed(tr('Не удалось загрузить редактор карты.'))
            self.save_status_label.setToolTip(str(error))
            return
        self.web_view.setAccessibleName(tr('Редактор карты'))
        self._page = self.web_view.page()
        self.mindmap_layout.addWidget(self.web_view)

        self._bridge = MindMapBridge(
            entity_name,
            mindmap_data,
            self.read_only,
            save_callback,
            self,
        )
        self._bridge.ready_received.connect(self._on_editor_ready)
        self._bridge.changed_received.connect(self._on_editor_changed)
        self._bridge.saved.connect(self._on_editor_saved)
        self._bridge.failed.connect(self._on_editor_failed)
        self._bridge.status_received.connect(self._on_status_message)

        self.web_view.loadFinished.connect(self._on_page_loaded)

        self._event_timer = QTimer(self)
        self._event_timer.setInterval(100)
        self._event_timer.timeout.connect(self._poll_editor_events)

        assets_path = Path(engine.resource_path('mindmap_assets'))
        try:
            editor_html = _standalone_editor_html(assets_path)
        except (OSError, ValueError) as error:
            self._bridge.last_error = str(error)
            self._on_editor_failed(tr('Не найдены файлы редактора карты.'))
        else:
            self.web_view.loadHtml(editor_html)

    def _on_page_loaded(self, successful, error_text=''):
        if not successful:
            self._bridge.last_error = str(error_text)
            self._on_editor_failed(tr('Не удалось загрузить редактор карты.'))
            return
        self._bridge.last_error = ''
        payload = self._bridge.initialPayload()
        script = (
            '(() => {'
            'if (!window.nfprogressMindMap) return false;'
            f'window.nfprogressMindMap.initialize(JSON.parse({json.dumps(payload)}));'
            'return true;'
            '})()'
        )
        self._page.runJavaScript(script, self._on_editor_initialized)

    def _on_editor_initialized(self, initialized):
        if not initialized:
            self._on_editor_failed(tr('Не удалось загрузить редактор карты.'))
            return
        self._event_timer.start()
        self._poll_editor_events()

    def _poll_editor_events(self):
        if self._poll_in_flight:
            return
        self._poll_in_flight = True
        self._page.runJavaScript(
            'window.nfprogressMindMap.takeEvents()',
            self._process_editor_events,
        )

    def _process_editor_events(self, payload):
        self._poll_in_flight = False
        if not isinstance(payload, str):
            return
        try:
            events = json.loads(payload)
        except (TypeError, ValueError):
            return
        for event in events:
            event_type = event.get('type')
            if event_type == 'ready':
                self._on_editor_ready()
            elif event_type == 'changed':
                self._bridge.changed()
            elif event_type == 'save':
                self._bridge.persist_payload(event.get('payload'))
            elif event_type == 'error':
                self._bridge.reportError(event.get('details', ''))
            elif event_type == 'status':
                self._bridge.showStatus(event.get('message', ''))
            elif event_type == 'export':
                self._finish_export(
                    event.get('format'),
                    event.get('data'),
                )
            elif event_type == 'exportError':
                self._finish_export_error(event.get('details', ''))

    def _on_editor_ready(self):
        self._ready = True
        self.save_button.setEnabled(not self.read_only)
        self.export_button.setEnabled(True)
        self._show_ready_status()

    def _show_ready_status(self):
        self.save_status_label.setToolTip('')
        if self.status_message:
            self.save_status_label.setText(tr(self.status_message))
        elif self.read_only:
            self.save_status_label.setText(tr('Карта доступна только для просмотра.'))
        else:
            self.save_status_label.setText(tr('Карта готова.'))

    def _on_editor_changed(self):
        self.save_status_label.setText(tr('Есть несохранённые изменения.'))

    def _on_editor_saved(self):
        self.save_status_label.setText(tr('Все изменения сохранены.'))
        self.save_status_label.setToolTip('')

    def _on_editor_failed(self, message):
        self.save_status_label.setText(message)
        self.save_status_label.setToolTip(self._bridge.last_error if hasattr(self, '_bridge') else '')

    def _on_status_message(self, message):
        self.save_status_label.setText(message)
        self.save_status_label.setToolTip('')

    def _request_explicit_save(self):
        if not self._ready or self.read_only:
            return
        self.save_status_label.setText(tr('Сохранение карты…'))
        self._page.runJavaScript(
            'window.nfprogressMindMap.getDataString()',
            self._finish_explicit_save,
        )

    def _finish_explicit_save(self, payload):
        if not isinstance(payload, str):
            self._on_editor_failed(tr('Не удалось получить данные карты.'))
            return
        self._bridge.persist_payload(payload)

    def _request_export(self, export_format):
        if (
            not self._ready
            or self._export_in_progress
            or export_format not in self.EXPORT_FORMATS
        ):
            return
        self._export_in_progress = True
        self.export_button.setEnabled(False)
        self.save_status_label.setText(tr('Подготовка экспорта…'))
        self._page.runJavaScript(
            f'window.nfprogressMindMap.requestExport({json.dumps(export_format)})',
        )

    def _finish_export(self, export_format, data):
        if not self._export_in_progress:
            return
        self._export_in_progress = False
        self.export_button.setEnabled(self._ready)
        export_details = self.EXPORT_FORMATS.get(export_format)
        if export_details is None or not isinstance(data, str):
            self._finish_export_error('Invalid export payload.')
            return

        _, title, file_filter, suffix = export_details
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            tr(title),
            f'{self.windowTitle()}{suffix}',
            tr(file_filter),
        )
        if not file_name:
            self._show_ready_status()
            return

        target_path = Path(file_name)
        if target_path.suffix.lower() != suffix:
            target_path = target_path.with_suffix(suffix)
        try:
            if export_format == 'json':
                exported_data = json.loads(data)
                target_path.write_text(
                    json.dumps(exported_data, ensure_ascii=False, indent=2),
                    encoding='utf-8',
                )
            else:
                _, separator, encoded = data.partition(',')
                if not separator:
                    raise ValueError('Missing image data URL.')
                target_path.write_bytes(base64.b64decode(encoded, validate=True))
        except (OSError, ValueError, json.JSONDecodeError) as error:
            self._finish_export_error(str(error))
            return

        self.save_status_label.setText(tr('Карта экспортирована.'))
        self.save_status_label.setToolTip('')

    def _finish_export_error(self, details):
        self._export_in_progress = False
        self.export_button.setEnabled(self._ready)
        self.save_status_label.setText(tr('Не удалось экспортировать карту.'))
        self.save_status_label.setToolTip(str(details))

    def _request_close_save(self):
        self._closing_after_save = True
        self.save_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self.save_status_label.setText(tr('Сохранение карты…'))
        self._page.runJavaScript(
            'window.nfprogressMindMap.getDataString()',
            self._finish_close_save,
        )

    def _finish_close_save(self, payload):
        saved = isinstance(payload, str) and self._bridge.persist_payload(payload)
        if saved:
            self._allow_close = True
            self.close()
            return

        self._closing_after_save = False
        self.save_button.setEnabled(not self.read_only and self._ready)
        self.export_button.setEnabled(self._ready)
        answer = QMessageBox.question(
            self,
            'Ошибка',
            'Не удалось сохранить карту. Закрыть окно без сохранения?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self._allow_close = True
            self.close()

    def reject(self):
        self.close()

    def closeEvent(self, event: QCloseEvent):
        if self._allow_close or self.read_only or not self._ready:
            if hasattr(self, '_event_timer'):
                self._event_timer.stop()
            if hasattr(self, 'web_view'):
                self.web_view.shutdown()
            event.accept()
            return
        event.ignore()
        if not self._closing_after_save:
            self._request_close_save()
