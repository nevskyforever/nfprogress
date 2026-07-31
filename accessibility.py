"""Shared screen-reader and keyboard accessibility configuration."""

from __future__ import annotations

import re
import weakref
from collections.abc import Iterable

from PySide6.QtCore import QEvent, QLocale, QObject, QTimer, Qt
from PySide6.QtGui import (
    QAccessible,
    QAccessibleAnnouncementEvent,
    QAccessibleEvent,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QAbstractItemView,
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QGroupBox,
    QLabel,
    QLineEdit,
    QScrollArea,
    QTabWidget,
    QTextEdit,
    QListWidget,
    QListWidgetItem,
    QWidget,
)

from localization import current_language, tr


_GENERATED_NAME_PROPERTY = "_nf_accessible_name_generated"
_DYNAMIC_UPDATES_PROPERTY = "_nf_accessibility_updates_connected"
_LOCALE_NAMES = {
    "ru": "ru_RU",
    "en": "en_US",
    "es": "es_ES",
    "de": "de_DE",
    "fr": "fr_FR",
    "pt_BR": "pt_BR",
}

# Связи сохраняют подпись поля в accessibility-дереве даже в тех текущих
# сгенерированных формах, которые были созданы до добавления buddy в .ui.
_FIELD_LABELS = {
    "award_name_le": "item_name_label",
    "award_price_le": "item_price_label",
    "le_name": "label",
    "le_goal": "label_2",
    "de_deadline": "label_3",
    "le_personal_goal_for_the_day": "label_8",
    "le_total_symbols": "label_4",
    "cb_unit": "label_7",
    "exp": "label_3",
    "health": "label_4",
    "coins": "label_2",
    "level": "label",
    "test_date": "test_date_cb",
    "new_symbols": "label_9",
    "sort_project_box": "label_5",
    "filter_project_box": "label_4",
    "note_list": "label_2",
    "value_for_buy_selected_item": "label_14",
    "value_for_buy_selected_potion": "label_12",
    "value_for_buy_selected_item_3": "label_16",
    "value_for_use_selected_item": "label_13",
    "productivity_skill_points": "label_6",
    "skill_points_profitability": "label_7",
    "endurance_skill_points": "label_8",
    "return_date_dateedit": "return_date_label",
    "notification_display_time_spinBox": "label_5",
    "start_day_time": "label_6",
    "language_comboBox": "language_label",
    "exp_progressbar": "gamer_exp",
    "gamer_health_progressbar": "gamer_health",
}

# У элементов без отдельной видимой подписи имя берётся из уже существующей
# локализуемой строки интерфейса.
_ACCESSIBLE_NAMES = {
    "tabWidget": "nfprogress",
    "list_projects": "Проекты",
    "search_project": "Поиск...",
    "game_shop_tabs": "Магазин",
    "item_shop_list": "Предметы",
    "potion_shop_list": "Зелья",
    "item_shop_list_2": "Награды",
    "inventory_list": "Инвентарь",
    "inventory_filter_comboBox": "Инвентарь",
    "quests_tabs": "Квесты",
    "available_quests_list": "Квесты",
    "active_quests_list": "Квесты",
    "completed_quests_list": "Квесты",
    "parameters_tabs": "Параметры персонажа",
    "buf_list": "Бафы",
    "debuf_list": "Дебафы",
    "gamer_parameters_list": "Параметры персонажа",
    "type_of_sych_cb": "Cинхронизация",
    "test_date": "Дата для теста:",
    "loan_partial_repayment_amount": "Частичное погашение",
    "active_deposit_topup_amount": "Пополнить вклад",
    "lineEdit": "Сумма (100.0)",
    "message": "Подтверждение",
    "game_tab": "Игровой режим",
}

_TAB_ORDERS = (
    # Главное окно.
    (
        "filter_project_box",
        "sort_project_box",
        "search_project",
        "btn_create_project",
        "written_today_in_all_projects_label",
        "global_streak_status",
        "list_projects",
        "btn_synch_project",
        "btn_change_project",
        "btn_complete_project",
        "btn_archived_project",
        "btn_delete_project",
        "share_progress",
        "name_selected_project",
        "scrollArea_5",
        "status",
        "total",
        "goal",
        "added_today",
        "need",
        "unit",
        "deadline",
        "progress",
        "today_goal",
        "streaks",
        "max_streak",
        "streak_status",
        "l",
        "note_list",
        "new_symbols",
        "pb_save_flash_note",
        "delete_note",
    ),
    (
        "frame_5",
        "bank_btn",
        "game_shop_tabs",
        "item_shop_list",
        "about_selected_goods",
        "value_for_buy_selected_item",
        "button_for_buy_selected_item",
        "potion_shop_list",
        "scrollArea_4",
        "value_for_buy_selected_potion",
        "button_for_buy_selected_potion",
        "item_shop_list_2",
        "about_selected_goods_3",
        "value_for_buy_selected_item_3",
        "button_for_buy_selected_item_3",
        "button_for_create_custom_award",
        "button_for_edit_selected_custom_award",
        "button_for_delete_selected_custom_award",
        "inventory_list",
        "inventory_filter_comboBox",
        "about_selected_inventory_item",
        "value_for_use_selected_item",
        "button_for_selected_item",
        "button_to_sell_selected_item",
    ),
    (
        "quests_tabs",
        "available_quests_list",
        "scrollArea_3",
        "button_for_start_selected_quest",
        "active_quests_list",
        "scrollArea_2",
        "button_for_stop_selected_quest",
        "completed_quests_list",
        "scrollArea",
    ),
    (
        "parameters_tabs",
        "buf_list",
        "scrollArea_7",
        "debuf_list",
        "scrol_area",
        "gamer_parameters_list",
        "scrollArea_6",
        "productivity_skill_points",
        "skill_points_profitability",
        "endurance_skill_points",
    ),
    # Создание и редактирование проекта.
    (
        "le_name",
        "le_goal",
        "de_deadline",
        "checkBox",
        "le_personal_goal_for_the_day",
        "le_total_symbols",
        "cb_unit",
        "enable_Stages",
        "add_Stage",
        "streak_checkBox",
        "auto_freeze_checkBox",
    ),
    ("award_name_le", "award_price_le", "inflation_checkBox"),
    (
        "language_comboBox",
        "enable_global_streak_checkBox",
        "enable_game_mode_checkBox",
        "enable_inf_projects_checkBox",
        "written_today_in_all_projects_checkBox",
        "notification_display_time_spinBox",
        "start_day_time",
        "check_uodates",
    ),
    ("lineEdit", "return_date_dateedit", "withdrawal_of_interest_from_a_deposit"),
    ("test_date_cb", "test_date", "level", "health", "coins", "exp"),
    (
        "take_credit_btn",
        "return_credit_btn",
        "make_a_loan_payment",
        "loan_partial_repayment_amount",
        "partial_loan_repayment",
        "make_deposit_btn",
        "active_deposit_topup_amount",
        "return_deposit_btn",
        "withdraw_interest_from_a_deposit",
    ),
)

_PROJECT_INFO_FIELDS = (
    ("status", "label_status"),
    ("total", "label_total"),
    ("goal", "label_goal"),
    ("added_today", "label_today_added"),
    ("need", "label_need"),
    ("unit", "unit_label"),
    ("deadline", "label_deadline"),
    ("progress", "label_progress"),
    ("today_goal", "label_today_goal"),
    ("streaks", "label_streaks"),
    ("max_streak", "label_max_streak"),
    ("streak_status", "label_streak_status"),
    ("l", "last_note"),
)


def announce_accessible_text(
    widget: QWidget,
    text: str,
    *,
    update_description: bool = True,
) -> None:
    """Announce a selection without changing its model or visual layout."""
    text = _plain_text(text)
    if not text:
        return
    if update_description:
        _set_accessible_description(widget, text)
    widget_ref = weakref.ref(widget)

    def announce():
        source = widget_ref()
        if source is None:
            return
        try:
            event = QAccessibleAnnouncementEvent(source, text)
            event.setPoliteness(QAccessible.AnnouncementPoliteness.Polite)
            QAccessible.updateAccessibility(event)
        except RuntimeError:
            return

    QTimer.singleShot(0, announce)


def set_item_accessible_text(
    item: QListWidgetItem,
    text: str,
    description: str = "",
) -> None:
    """Name a model item for screen readers without adding painted text."""
    item.setData(Qt.ItemDataRole.AccessibleTextRole, _plain_text(text))
    item.setData(
        Qt.ItemDataRole.AccessibleDescriptionRole,
        _plain_text(description),
    )


def _plain_text(text: str) -> str:
    """Return concise text without HTML or mnemonic markers."""
    plain = re.sub(r"<[^>]+>", " ", text or "")
    plain = re.sub(r"\s+", " ", plain).strip()
    return plain.replace("&&", "\0").replace("&", "").replace("\0", "&").rstrip(":")


def _set_generated_name(widget: QWidget, name: str) -> None:
    name = _plain_text(name)
    if not name:
        return
    if not widget.accessibleName() or widget.property(_GENERATED_NAME_PROPERTY):
        _set_accessible_name(widget, name)
        widget.setProperty(_GENERATED_NAME_PROPERTY, True)


def _set_accessible_name(widget: QWidget, name: str) -> None:
    name = _plain_text(name)
    if not name or widget.accessibleName() == name:
        return
    widget.setAccessibleName(name)
    QAccessible.updateAccessibility(
        QAccessibleEvent(widget, QAccessible.Event.NameChanged)
    )


def _set_accessible_description(widget: QWidget, description: str) -> None:
    description = _plain_text(description)
    if widget.accessibleDescription() == description:
        return
    widget.setAccessibleDescription(description)
    QAccessible.updateAccessibility(
        QAccessibleEvent(widget, QAccessible.Event.DescriptionChanged)
    )


def _iter_widgets(root: QWidget) -> Iterable[QWidget]:
    yield root
    yield from root.findChildren(QWidget)


def _connect_field_labels(root: QWidget) -> None:
    for field_name, label_name in _FIELD_LABELS.items():
        field = root.findChild(QWidget, field_name)
        label = root.findChild(QLabel, label_name)
        if field is None or label is None:
            continue
        label.setBuddy(field)
        _set_generated_name(field, label.text())


def _configure_project_information(root: QWidget) -> None:
    project_info = root.findChild(QGroupBox, "project_info")
    if project_info is None:
        return

    summary = []
    project_name = root.findChild(QLabel, "name_selected_project")
    if project_name is not None:
        project_name.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        _set_accessible_name(project_name, project_name.text())
        if project_name.text():
            summary.append(project_name.text())

    for value_name, heading_name in _PROJECT_INFO_FIELDS:
        value = root.findChild(QLabel, value_name)
        heading = root.findChild(QLabel, heading_name)
        if value is None or heading is None:
            continue
        value.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        field_text = f"{_plain_text(heading.text())}: {_plain_text(value.text())}"
        _set_accessible_name(value, field_text)
        if not value.isHidden() and value.text():
            summary.append(field_text)

    for label_name in (
        "written_today_in_all_projects_label",
        "global_streak_status",
    ):
        label = root.findChild(QLabel, label_name)
        if label is not None:
            label.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            _set_accessible_name(label, label.text())

    summary_text = ". ".join(summary)
    _set_accessible_description(project_info, summary_text)
    scroll_area = root.findChild(QScrollArea, "scrollArea_5")
    if scroll_area is not None:
        title = project_info.title()
        _set_accessible_name(
            scroll_area,
            f"{title}. {summary_text}" if summary_text else title,
        )
        _set_accessible_description(scroll_area, summary_text)


def _configure_game_status(root: QWidget) -> None:
    status_frame = root.findChild(QWidget, "frame_5")
    if status_frame is None:
        return
    status_frame.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    texts = []
    for label_name in (
        "gamer_label",
        "gamer_coins",
        "gamer_exp",
        "gamer_health",
    ):
        label = root.findChild(QLabel, label_name)
        if label is None:
            continue
        text = _plain_text(label.text())
        if text:
            texts.append(text)
    summary = ". ".join(texts)
    title = tr("Параметры персонажа")
    _set_accessible_name(
        status_frame,
        f"{title}. {summary}" if summary else title,
    )
    _set_accessible_description(status_frame, summary)


def _configure_scroll_area(scroll_area: QScrollArea) -> None:
    group_box = scroll_area.parentWidget()
    while group_box is not None and not isinstance(group_box, QGroupBox):
        group_box = group_box.parentWidget()
    title = group_box.title() if group_box is not None else scroll_area.accessibleName()
    if not title:
        title = scroll_area.window().windowTitle()

    labels = [
        label
        for label in scroll_area.findChildren(QLabel)
        if not label.isHidden() and label.text()
    ]
    labels.sort(
        key=lambda label: (
            label.mapTo(scroll_area, label.rect().topLeft()).y(),
            label.mapTo(scroll_area, label.rect().topLeft()).x(),
        )
    )
    texts = []
    for label in labels:
        text = _plain_text(label.text())
        if text and text not in texts:
            texts.append(text)
    summary = ". ".join(texts)
    _set_accessible_name(
        scroll_area,
        f"{title}. {summary}" if summary else title,
    )
    _set_accessible_description(scroll_area, summary)


def _schedule_window_refresh(widget: QWidget) -> None:
    window_ref = weakref.ref(widget.window())

    def refresh():
        window = window_ref()
        if window is None:
            return
        try:
            refresh_accessibility(window)
        except RuntimeError:
            return

    QTimer.singleShot(0, refresh)


def _connect_dynamic_updates(widget: QWidget) -> None:
    if widget.property(_DYNAMIC_UPDATES_PROPERTY):
        return
    if isinstance(widget, QAbstractItemView):
        widget.selectionModel().currentChanged.connect(
            lambda *_args, source=widget: _schedule_window_refresh(source)
        )
    elif isinstance(widget, QTabWidget):
        widget.currentChanged.connect(
            lambda _index, source=widget: _schedule_window_refresh(source)
        )
    else:
        return
    widget.setProperty(_DYNAMIC_UPDATES_PROPERTY, True)


def _configure_widget(widget: QWidget) -> None:
    mapped_name = _ACCESSIBLE_NAMES.get(widget.objectName())
    if mapped_name:
        _set_generated_name(widget, tr(mapped_name))

    if widget.isWindow() and widget.windowTitle():
        _set_accessible_name(widget, widget.windowTitle())
        widget.setProperty(_GENERATED_NAME_PROPERTY, True)

    if isinstance(widget, QAbstractButton):
        if (
            widget.objectName()
            and not widget.objectName().startswith("qt_")
            and widget.focusPolicy() == Qt.FocusPolicy.NoFocus
        ):
            widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        if widget.objectName() == "checkBox":
            _set_generated_name(widget, f"{tr('Дедлайн')}: {widget.text()}")
        elif widget.text():
            _set_generated_name(widget, widget.text())
        elif widget.toolTip():
            _set_generated_name(widget, widget.toolTip())

    if isinstance(widget, (QLineEdit, QTextEdit)) and not widget.accessibleName():
        placeholder = widget.placeholderText()
        if placeholder:
            _set_generated_name(widget, placeholder)
        elif isinstance(widget, QTextEdit) and widget.isReadOnly():
            _set_generated_name(widget, widget.window().windowTitle())

    if widget.toolTip() and not widget.accessibleDescription():
        _set_accessible_description(widget, widget.toolTip())

    if isinstance(widget, QScrollArea):
        _configure_scroll_area(widget)
    _connect_dynamic_updates(widget)


def _apply_tab_order(root: QWidget) -> None:
    for object_names in _TAB_ORDERS:
        widgets = [root.findChild(QWidget, name) for name in object_names]
        if any(widget is None for widget in widgets):
            continue
        for first, second in zip(widgets, widgets[1:]):
            QWidget.setTabOrder(first, second)


def refresh_accessibility(root: QWidget) -> None:
    """Refresh accessibility metadata for a window and its child widgets."""
    locale = QLocale(_LOCALE_NAMES[current_language()])
    _connect_field_labels(root)
    for widget in _iter_widgets(root):
        if widget.locale() != locale:
            widget.setLocale(locale)
        _configure_widget(widget)
    _configure_project_information(root)
    _configure_game_status(root)
    _apply_tab_order(root)


class _AccessibilityManager(QObject):
    """Configure both static and dynamically created widgets."""

    def eventFilter(self, watched, event):
        if isinstance(watched, QWidget):
            if event.type() in (QEvent.Type.Polish, QEvent.Type.Show):
                if watched.isWindow():
                    refresh_accessibility(watched)
                else:
                    _configure_widget(watched)
            elif event.type() == QEvent.Type.FocusIn:
                if isinstance(watched, QScrollArea):
                    _configure_scroll_area(watched)
                if isinstance(watched, QListWidget):
                    current_item = watched.currentItem()
                    if current_item is None and watched.count():
                        watched.setCurrentRow(0)
                        current_item = watched.currentItem()
                    if current_item is not None:
                        embedded_widget = watched.itemWidget(current_item)
                        item_text = current_item.data(
                            Qt.ItemDataRole.AccessibleTextRole
                        )
                        if not item_text:
                            item_text = current_item.text()
                        if (
                            embedded_widget is not None
                            and embedded_widget.accessibleName()
                        ):
                            item_text = embedded_widget.accessibleName()
                        announcement_source = (
                            embedded_widget
                            or watched.parentWidget()
                            or watched
                        )
                        announce_accessible_text(
                            announcement_source,
                            item_text,
                            update_description=False,
                        )
                _configure_project_information(watched.window())
                _configure_game_status(watched.window())
        return super().eventFilter(watched, event)


def install_accessibility(app: QApplication) -> None:
    """Install the application-wide accessibility filter once."""
    if getattr(app, "_nf_accessibility_manager", None) is not None:
        return
    manager = _AccessibilityManager(app)
    app.installEventFilter(manager)
    app._nf_accessibility_manager = manager


def is_interactive_widget(widget: QWidget) -> bool:
    """Return whether a control requires an accessible name."""
    return isinstance(
        widget,
        (
            QAbstractButton,
            QAbstractItemView,
            QAbstractSpinBox,
            QComboBox,
            QLineEdit,
            QTabWidget,
            QTextEdit,
        ),
    )
