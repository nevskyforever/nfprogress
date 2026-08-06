import os
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QAccessible
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QWidget,
)

from accessibility import (
    announce_accessible_text,
    install_accessibility,
    is_interactive_widget,
    refresh_accessibility,
    set_item_accessible_text,
)
from localization import SUPPORTED_LANGUAGES, set_language, tr


PROJECT_ROOT = Path(__file__).resolve().parents[1]
UI_TEMPLATES = PROJECT_ROOT / "UI template"

FORM_CONTROLS = {
    "QLineEdit",
    "QTextEdit",
    "QPlainTextEdit",
    "QComboBox",
    "QSpinBox",
    "QDoubleSpinBox",
    "QDateEdit",
    "QDateTimeEdit",
    "QTimeEdit",
    "QListWidget",
    "QTreeWidget",
    "QTableWidget",
    "QTabWidget",
    "QSlider",
}
TEXT_CONTROLS = {"QPushButton", "QToolButton", "QCheckBox", "QRadioButton"}


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _property_text(widget, property_name):
    prop = widget.find(f"property[@name='{property_name}']")
    return "".join(prop.itertext()).strip() if prop is not None else ""


def test_ui_templates_expose_names_labels_and_tab_order():
    for ui_path in sorted(UI_TEMPLATES.glob("*.ui")):
        root = ET.parse(ui_path).getroot()
        window = root.find("widget")
        assert _property_text(window, "accessibleName"), ui_path.name

        buddy_targets = {
            _property_text(label, "buddy")
            for label in root.iter("widget")
            if label.get("class") == "QLabel"
        }
        buddy_targets.discard("")

        focusable_names = []
        for widget in root.iter("widget"):
            widget_class = widget.get("class")
            object_name = widget.get("name")
            if widget_class in TEXT_CONTROLS:
                assert (
                    _property_text(widget, "text")
                    or _property_text(widget, "accessibleName")
                ), f"{ui_path.name}: {object_name}"
                focusable_names.append(object_name)
            elif widget_class in FORM_CONTROLS:
                assert (
                    _property_text(widget, "accessibleName")
                    or _property_text(widget, "placeholderText")
                    or object_name in buddy_targets
                ), f"{ui_path.name}: {object_name}"
                focusable_names.append(object_name)

        if focusable_names:
            tabstops = root.find("tabstops")
            assert tabstops is not None, ui_path.name
            declared_tabstops = {
                element.text for element in tabstops.findall("tabstop")
            }
            assert declared_tabstops, ui_path.name
            assert set(focusable_names) <= declared_tabstops, (
                f"{ui_path.name}: missing tabstops "
                f"{sorted(set(focusable_names) - declared_tabstops)}"
            )


def test_generated_forms_receive_runtime_accessible_names(app):
    from UI_fiiles.bank import Ui_Bamk
    from UI_fiiles.confirm_dialog import Ui_confirm_dialog
    from UI_fiiles.create_custom_award import Ui_create_castom_item
    from UI_fiiles.create_project import Ui_create_project
    from UI_fiiles.developer_mode import Ui_developer_node
    from UI_fiiles.freeze_project import Ui_freeze_projrct
    from UI_fiiles.main_window import Ui_main_window
    from UI_fiiles.new_bank_product import Ui_Dialog as Ui_NewBankProduct
    from UI_fiiles.project_stats import Ui_project_stats
    from UI_fiiles.settings import Ui_Dialog as Ui_Settings
    from UI_fiiles.synch_window import Ui_sych_window
    from UI_fiiles.user_agreement import Ui_user_agreement

    forms = (
        (QDialog, Ui_Bamk),
        (QDialog, Ui_confirm_dialog),
        (QDialog, Ui_create_castom_item),
        (QDialog, Ui_create_project),
        (QDialog, Ui_developer_node),
        (QDialog, Ui_freeze_projrct),
        (QMainWindow, Ui_main_window),
        (QDialog, Ui_NewBankProduct),
        (QDialog, Ui_project_stats),
        (QDialog, Ui_Settings),
        (QDialog, Ui_sych_window),
        (QDialog, Ui_user_agreement),
    )

    for root_class, ui_class in forms:
        root = root_class()
        ui = ui_class()
        ui.setupUi(root)
        refresh_accessibility(root)

        assert root.accessibleName(), ui_class.__name__
        for widget in root.findChildren(QWidget):
            object_name = widget.objectName()
            if not object_name or object_name.startswith("qt_"):
                continue
            if is_interactive_widget(widget):
                assert widget.accessibleName(), (
                    f"{ui_class.__name__}: "
                    f"{type(widget).__name__} {object_name}"
                )
        root.deleteLater()


def test_accessible_names_are_localized_in_every_supported_language():
    names = []
    for ui_path in UI_TEMPLATES.glob("*.ui"):
        root = ET.parse(ui_path).getroot()
        names.extend(
            _property_text(widget, "accessibleName")
            for widget in root.iter("widget")
            if _property_text(widget, "accessibleName")
        )

    for language in SUPPORTED_LANGUAGES:
        if language == "ru":
            continue
        untranslated = {
            name for name in names
            if name != "nfprogress" and tr(name, language) == name
        }
        assert not untranslated, f"{language}: {sorted(untranslated)}"


def test_custom_progress_exposes_text_value(app):
    from UI_fiiles.project_widget import CircularProgressBar

    progress = CircularProgressBar()
    progress.setValueImmediate(42)

    assert progress.accessibleName()
    assert progress.accessibleDescription() == "42%"
    interface = QAccessible.queryAccessibleInterface(progress)
    assert interface.role() == QAccessible.Role.ProgressBar
    assert interface.valueInterface().currentValue() == 42


def test_embedded_widget_has_non_visual_accessible_list_item(app):
    project_list = QListWidget()
    project_list.setAccessibleName("Проекты")
    item = QListWidgetItem()
    project_list.addItem(item)
    widget = QWidget()
    widget.setAccessibleName("Доступное описание проекта")
    project_list.setItemWidget(item, widget)
    set_item_accessible_text(item, widget.accessibleName())
    second_item = QListWidgetItem()
    project_list.addItem(second_item)
    second_widget = QWidget()
    second_widget.setAccessibleName("Второй проект")
    project_list.setItemWidget(second_item, second_widget)
    set_item_accessible_text(second_item, second_widget.accessibleName())
    install_accessibility(app)
    project_list.show()
    project_list.setFocus()
    announce_accessible_text(project_list, widget.accessibleName())
    app.processEvents()

    assert project_list.currentRow() == 0
    assert item.text() == ""
    assert item.data(Qt.ItemDataRole.DisplayRole) is None
    assert (
        item.data(Qt.ItemDataRole.AccessibleTextRole)
        == "Доступное описание проекта"
    )
    assert project_list.accessibleDescription() == "Доступное описание проекта"
    interface = QAccessible.queryAccessibleInterface(project_list)
    assert interface.child(0).text(QAccessible.Text.Name) == (
        "Доступное описание проекта"
    )
    assert interface.child(0).state().focusable

    QTest.keyClick(project_list, Qt.Key.Key_Down)
    app.processEvents()

    assert project_list.currentRow() == 1
    assert interface.child(1).text(QAccessible.Text.Name) == "Второй проект"


def test_project_information_and_game_controls_are_navigable(app):
    from UI_fiiles.main_window import Ui_main_window

    root = QMainWindow()
    ui = Ui_main_window()
    ui.setupUi(root)
    ui.project_info.setVisible(True)
    ui.status.setText("активен")
    refresh_accessibility(root)
    root.show()
    app.processEvents()

    assert ui.status.focusPolicy() == Qt.FocusPolicy.StrongFocus
    assert ui.status.accessibleName() == "Статус: активен"
    assert "Статус: активен" in ui.scrollArea_5.accessibleDescription()

    ui.tabWidget.setCurrentWidget(ui.game_tab)
    refresh_accessibility(root)
    app.processEvents()

    assert (
        ui.button_for_buy_selected_item.focusPolicy()
        == Qt.FocusPolicy.StrongFocus
    )
    assert ui.frame_5.focusPolicy() == Qt.FocusPolicy.StrongFocus
    assert "Параметры персонажа" in ui.frame_5.accessibleName()
    assert ui.about_selected_goods.accessibleDescription()
    assert ui.item_shop_list.accessibleName()

    focus_chain_names = set()
    current = ui.tabWidget
    visited = set()
    while id(current) not in visited:
        visited.add(id(current))
        current = current.nextInFocusChain()
        if (
            current.isVisibleTo(root)
            and current.isEnabled()
            and current.focusPolicy() != Qt.FocusPolicy.NoFocus
        ):
            focus_chain_names.add(current.objectName())

    assert {
        "frame_5",
        "game_shop_tabs",
        "item_shop_list",
        "about_selected_goods",
        "button_for_buy_selected_item",
        "inventory_list",
        "quests_tabs",
        "available_quests_list",
        "parameters_tabs",
        "buf_list",
    } <= focus_chain_names


def test_project_with_stages_announces_toggle_shortcut(app):
    import engine
    from UI_fiiles.project_widget import ProjectWidget

    project = engine.Project(name="Книга", unit="symbols")
    project.enable_stages = True
    project.stages = [
        engine.Stage(
            name="Черновик",
            goal=1000,
            parent_project_name=project.name,
        )
    ]
    widget = ProjectWidget(project, False, expanded=False)

    assert "Показать этапы" in widget.accessibleName()
    assert "Ctrl+Enter" in widget.accessibleName()
    assert widget.accessibleDescription() == "Показать этапы. Ctrl+Enter"

    project_list = QListWidget()
    item = QListWidgetItem()
    project_list.addItem(item)
    project_list.setItemWidget(item, widget)
    set_item_accessible_text(
        item,
        widget.accessibleName(),
        widget.accessibleDescription(),
    )
    project_list.show()
    app.processEvents()

    interface = QAccessible.queryAccessibleInterface(project_list).child(0)
    assert interface.text(QAccessible.Text.Description) == (
        "Показать этапы. Ctrl+Enter"
    )
    widget.stop_animations()


def test_buff_rows_expose_complete_accessible_text(app):
    import game_data
    from game_UI import GameMenuController

    buff = game_data.Buff(
        name="Тестовый баф",
        description="Увеличивает опыт",
        buff_type=game_data.Buff.POSITIVE,
        target_cf="exp",
        value=2,
    )

    class FakeGamer:
        cf = {}

        def normalize_cf(self):
            return None

        def get_all_buffs(self, positive=True):
            return [(buff, 2)] if positive else []

    controller = GameMenuController.__new__(GameMenuController)
    controller.gamer = FakeGamer()
    controller.ui = SimpleNamespace(
        buf_list=QListWidget(),
        debuf_list=QListWidget(),
    )
    controller.load_buffs_list(True)
    controller.ui.buf_list.show()
    app.processEvents()

    item = controller.ui.buf_list.item(0)
    accessible_text = item.data(Qt.ItemDataRole.AccessibleTextRole)
    assert "Тестовый баф x2" in accessible_text
    assert "Увеличивает опыт" in accessible_text
    assert "Количество: 2" in accessible_text
    interface = QAccessible.queryAccessibleInterface(
        controller.ui.buf_list
    )
    assert interface.child(0).text(QAccessible.Text.Name) == accessible_text


def test_accessible_widgets_use_current_interface_locale(app):
    set_language(app, "ru")
    root = QMainWindow()
    refresh_accessibility(root)
    root.show()
    app.processEvents()

    attributes = QAccessible.queryAccessibleInterface(
        root
    ).attributesInterface()
    assert QAccessible.Attribute.Locale in attributes.attributeKeys()
    assert (
        attributes.attributeValue(QAccessible.Attribute.Locale).name()
        == "ru_RU"
    )
