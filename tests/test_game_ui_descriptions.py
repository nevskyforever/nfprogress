import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow

import game
from UI_fiiles.main_window import Ui_main_window
from game_UI import GameMenuController
from localization import set_language, tr


APP = QApplication.instance() or QApplication([])


def create_ui():
    window = QMainWindow()
    ui = Ui_main_window()
    ui.setupUi(window)
    return window, ui


def test_inventory_and_cabinet_share_their_own_tab_group():
    window, ui = create_ui()

    assert ui.inventory_cabinet_tabs.indexOf(ui.inventory_frame) == 0
    assert ui.inventory_cabinet_tabs.indexOf(ui.cabinet_tab) == 1
    assert ui.parameters_tabs.indexOf(ui.cabinet_tab) == -1
    assert ui.tabWidget.currentIndex() == 0
    assert ui.game_shop_tabs.currentIndex() == 0
    assert ui.inventory_cabinet_tabs.currentIndex() == 0
    assert ui.quests_tabs.currentIndex() == 0
    assert ui.parameters_tabs.currentIndex() == 0

    window.close()


def test_specialization_choice_shows_description_before_and_after_selection():
    set_language(APP, "ru")
    window, ui = create_ui()
    controller = GameMenuController.__new__(GameMenuController)
    controller.ui = ui
    controller.gamer = SimpleNamespace(specialization=None, level=game.SPECIALIZATION_LEVEL)

    ui.specialization_combo.setCurrentIndex(1)
    controller.update_specialization_choice_ui()
    description = game.SPECIALIZATIONS["ritualist"]["description"]

    assert description in ui.specialization_status.text()
    assert ui.specialization_combo.toolTip() == description
    assert ui.specialization_combo.itemData(
        1, Qt.ItemDataRole.ToolTipRole
    ) == description

    controller.gamer.specialization = "ritualist"
    controller.update_specialization_choice_ui()
    assert ui.specialization_combo.toolTip() == description

    window.close()


def test_creative_event_controls_explain_selected_outcome():
    set_language(APP, "ru")
    window, ui = create_ui()
    controller = GameMenuController.__new__(GameMenuController)
    controller.ui = ui
    controller.gamer = SimpleNamespace(pending_creative_event="unexpected_idea")

    ui.creative_event_choice_combo.setCurrentIndex(1)
    controller.update_creative_event_ui()

    assert game.CREATIVE_EVENTS["unexpected_idea"]["risk_description"] in (
        ui.creative_event_choice_combo.toolTip()
    )
    assert tr("Решить событие выбранным способом") in (
        ui.resolve_creative_event_button.toolTip()
    )
    assert ui.creative_event_choice_combo.itemData(
        0, Qt.ItemDataRole.ToolTipRole
    ) == tr("Надёжный выбор даёт гарантированную награду события без риска.")

    window.close()
