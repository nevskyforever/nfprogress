"""Mind Elixir editor embedded in a Qt WebEngine dialog."""

import json
import os
from pathlib import Path


def _chromium_flags_without_skia_graphite(flags):
    """Add the Graphite opt-out without discarding existing Chromium flags."""
    tokens = str(flags or '').split()
    disable_features_prefix = '--disable-features='
    for index, token in enumerate(tokens):
        if not token.startswith(disable_features_prefix):
            continue
        features = token[len(disable_features_prefix):].split(',')
        if 'SkiaGraphite' not in features:
            features.append('SkiaGraphite')
        tokens[index] = disable_features_prefix + ','.join(features)
        break
    else:
        tokens.append(f'{disable_features_prefix}SkiaGraphite')
    return ' '.join(tokens)


os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = (
    _chromium_flags_without_skia_graphite(
        os.environ.get('QTWEBENGINE_CHROMIUM_FLAGS', '')
    )
)

from PySide6.QtCore import QObject, QUrl, Signal, Slot
from PySide6.QtGui import QCloseEvent, QDesktopServices
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QDialog

import engine
from UI_fiiles.mindmap_dialog import Ui_mindmap_dialog
from localization import (
    LocalizedMessageBox as QMessageBox,
    current_language,
    tr,
)


def _canonical_json(data):
    return json.dumps(
        data,
        ensure_ascii=False,
        sort_keys=True,
        separators=(',', ':'),
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


class MindMapPage(QWebEnginePage):
    """Keep map links out of the embedded editor page."""

    def acceptNavigationRequest(self, url, navigation_type, is_main_frame):
        if navigation_type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked:
            if url.scheme() in {'http', 'https', 'mailto'}:
                QDesktopServices.openUrl(url)
            return False
        return super().acceptNavigationRequest(url, navigation_type, is_main_frame)


class MindMapDialog(QDialog, Ui_mindmap_dialog):
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

        self.setWindowTitle(f"{tr('Карта')} — {entity_name}")
        self.map_title_label.setText(f"{tr('Карта')}: {entity_name}")
        if self.read_only:
            self.instructions_label.setText(
                tr('Завершённый проект или этап: карта доступна только для просмотра.')
            )

        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self._request_explicit_save)
        self.close_button.clicked.connect(self.close)

        self.web_view = QWebEngineView(self.mindmap_container)
        self.web_view.setAccessibleName(tr('Редактор карты'))
        self._page = MindMapPage(self.web_view)
        self.web_view.setPage(self._page)
        self.mindmap_layout.addWidget(self.web_view)

        settings = self.web_view.settings()
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls,
            True,
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
            False,
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows,
            False,
        )

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

        self._channel = QWebChannel(self._page)
        self._channel.registerObject('mindmapBridge', self._bridge)
        self._page.setWebChannel(self._channel)
        self._page.loadFinished.connect(self._on_page_loaded)

        editor_path = Path(engine.resource_path('mindmap_assets/index.html'))
        if editor_path.is_file():
            self.web_view.load(QUrl.fromLocalFile(str(editor_path)))
        else:
            self._on_editor_failed(tr('Не найдены файлы редактора карты.'))

    def _on_page_loaded(self, successful):
        if not successful:
            self._on_editor_failed(tr('Не удалось загрузить редактор карты.'))

    def _on_editor_ready(self):
        self._ready = True
        self.save_button.setEnabled(not self.read_only)
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

    def _request_close_save(self):
        self._closing_after_save = True
        self.save_button.setEnabled(False)
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
            event.accept()
            return
        event.ignore()
        if not self._closing_after_save:
            self._request_close_save()
