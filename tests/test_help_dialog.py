import os
import re

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication, QMainWindow

from UI_fiiles.main_window import Ui_main_window
from help_content import HELP_SECTIONS
from localization import set_language, tr
from main_UI import HelpDialog


APP = QApplication.instance() or QApplication([])


def flatten_sections(sections):
    for section in sections:
        yield section
        yield from flatten_sections(section.get("children", ()))


def test_help_content_has_unique_translatable_sections():
    sections = list(flatten_sections(HELP_SECTIONS))
    keys = [section["key"] for section in sections]

    assert len(sections) >= 30
    assert len(keys) == len(set(keys))
    assert {
        "create_project",
        "stages",
        "deadlines",
        "game_mode",
        "creative_rhythm",
        "writing_sessions",
        "cabinet",
    }.issubset(keys)
    assert all(section["content"].startswith("<html>") for section in sections)
    assert all(len(section["content"]) <= 3000 for section in sections)


def test_help_content_is_localized_in_every_supported_language():
    cyrillic = re.compile(r"[А-Яа-яЁё]")
    sections = list(flatten_sections(HELP_SECTIONS))

    for language in ("en", "es", "de", "fr", "pt_BR"):
        for section in sections:
            translated_content = tr(section["content"], language)
            assert not cyrillic.search(tr(section["title"], language))
            assert not cyrillic.search(translated_content)
            assert re.findall(r"<[^>]+>", translated_content) == re.findall(
                r"<[^>]+>", section["content"]
            )


def test_help_action_is_in_menu_bar_with_required_shortcut():
    window = QMainWindow()
    ui = Ui_main_window()
    ui.setupUi(window)

    assert ui.help_menu.menuAction() in ui.menuBar.actions()
    assert ui.help_action in ui.help_menu.actions()
    assert ui.help_action.shortcut().toString(
        QKeySequence.SequenceFormat.PortableText
    ) == "Ctrl+H"
    assert ui.help_action.shortcutContext() == Qt.ShortcutContext.ApplicationShortcut


def test_help_dialog_builds_navigation_and_initial_content():
    dialog = HelpDialog()

    assert dialog.help_tree.topLevelItemCount() == len(HELP_SECTIONS)
    assert len(dialog._content_by_key) == len(list(flatten_sections(HELP_SECTIONS)))
    assert dialog.help_tree.currentItem().data(
        0, Qt.ItemDataRole.UserRole
    ) == "quick_start"
    assert "nfprogress" in dialog.help_content.toPlainText()


def test_help_dialog_uses_reviewed_translation_for_article_heading():
    set_language(APP, "en")
    try:
        dialog = HelpDialog()
        cabinet_item = None
        pending = [
            dialog.help_tree.topLevelItem(index)
            for index in range(dialog.help_tree.topLevelItemCount())
        ]
        while pending:
            item = pending.pop()
            if item.data(0, Qt.ItemDataRole.UserRole) == "cabinet":
                cabinet_item = item
                break
            pending.extend(item.child(index) for index in range(item.childCount()))

        dialog.help_tree.setCurrentItem(cabinet_item)

        assert cabinet_item.text(0) == "Cabinet, Relics, and Sets"
        assert dialog.help_content.toPlainText().startswith(
            "Cabinet, Relics, and Sets"
        )
    finally:
        set_language(APP, "ru")
