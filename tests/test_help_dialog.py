import os
import platform
import re
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QApplication, QMainWindow, QMenu

from UI_fiiles.main_window import Ui_main_window
from help_content import HELP_SECTIONS, render_help_content
from localization import MINDMAP_HELP_SOURCE, set_language, tr
from macos_help_search import (
    HelpSearchItem,
    create_macos_help_search,
    ranked_help_search_items,
)
from main_UI import HelpDialog, MainWindow


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
        "mind_maps",
        "deadlines",
        "game_mode",
        "creative_rhythm",
        "writing_sessions",
        "cabinet",
    }.issubset(keys)
    assert all(section["content"].startswith("<html>") for section in sections)
    assert all(len(section["content"]) <= 3000 for section in sections)
    assert next(
        section["content"] for section in sections if section["key"] == "mind_maps"
    ) == MINDMAP_HELP_SOURCE


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


def test_project_notes_help_preserves_the_canonical_system_tag():
    section = next(
        section for section in flatten_sections(HELP_SECTIONS)
        if section['key'] == 'project_notes'
    )
    for language in ('ru', 'en', 'es', 'de', 'fr', 'pt_BR'):
        rendered = render_help_content(tr(section['content'], language))
        assert rendered.count('#карта') == 4


def test_help_action_is_in_menu_bar_with_required_shortcut():
    window = QMainWindow()
    ui = Ui_main_window()
    ui.setupUi(window)

    assert ui.help_menu.menuAction() in ui.menuBar.actions()
    assert ui.help_action in ui.help_menu.actions()
    assert not hasattr(ui, "help_search_action")
    assert ui.help_topics_menu.menuAction() in ui.help_menu.actions()
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


def test_help_dialog_searches_titles_and_article_text():
    set_language(APP, "ru")
    dialog = HelpDialog()

    dialog.help_search.setText("банк")

    assert dialog.help_tree.currentItem().data(
        0, Qt.ItemDataRole.UserRole
    ) == "bank"

    dialog.help_search.setText("капитализирует")

    assert dialog.help_tree.currentItem().data(
        0, Qt.ItemDataRole.UserRole
    ) == "bank"
    assert dialog.help_content.toPlainText().startswith("Банк")

    dialog.help_search.setText("заведомо отсутствующий запрос")

    assert dialog.help_tree.currentItem() is None
    assert dialog.help_content.toPlainText() == "Поиск не дал результатов"

    dialog.help_search.clear()

    assert dialog.help_tree.currentItem().data(
        0, Qt.ItemDataRole.UserRole
    ) == "bank"


def test_help_topic_menu_and_system_index_include_every_section():
    set_language(APP, "ru")
    opened_sections = []
    owner = SimpleNamespace(
        help_topics_menu=QMenu(),
        _help_topic_actions=[],
        _help_search_items=(),
        _macos_help_search=None,
        show_help=lambda section_key: opened_sections.append(section_key),
    )

    MainWindow._rebuild_help_topics_menu(owner)

    bank_action = next(
        action for action in owner._help_topic_actions
        if action.data() == "bank"
    )
    assert bank_action.text() == "Банк"
    assert bank_action.menuRole() == QAction.MenuRole.NoRole
    assert len(owner._help_search_items) == len(list(flatten_sections(HELP_SECTIONS)))

    native_matches = ranked_help_search_items(
        owner._help_search_items, "банк", 10
    )
    assert native_matches[0].key == "bank"
    assert native_matches[0].display_path == ("Игровой режим", "Банк")

    bank_action.trigger()

    assert opened_sections == ["bank"]


def test_macos_help_search_handler_registers_when_available():
    item = HelpSearchItem.create(
        key="bank",
        display_path=("Игровой режим", "Банк"),
        titles=("Банк", "Bank"),
        text_parts=("Кредит, вклад и банковский рейтинг",),
    )
    opened_sections = []

    bridge = create_macos_help_search((item,), opened_sections.append)

    if platform.system() != "Darwin":
        assert bridge is None
        return

    assert bridge is not None
    try:
        assert bridge.is_registered
        assert bridge.search("  ", 10) == ()
        assert bridge.search("банк", 10) == ("bank",)
        assert bridge.localized_titles("bank") == ("Игровой режим", "Банк")
    finally:
        bridge.unregister()
    assert not bridge.is_registered


def test_system_help_index_uses_selected_language():
    updated_indexes = []
    owner = SimpleNamespace(
        help_topics_menu=QMenu(),
        _help_topic_actions=[],
        _help_search_items=(),
        _macos_help_search=SimpleNamespace(
            update_items=lambda items: updated_indexes.append(tuple(items))
        ),
        show_help=lambda _section_key: None,
    )
    set_language(APP, "en")
    try:
        MainWindow._rebuild_help_topics_menu(owner)
        matches = ranked_help_search_items(updated_indexes[-1], "bank", 10)

        assert matches[0].key == "bank"
        assert matches[0].display_path == ("Game mode", "Bank")
    finally:
        set_language(APP, "ru")


def test_help_search_messages_are_localized():
    expected_messages = {
        "en": ("Search Help…", "No search results"),
        "es": ("Buscar en la ayuda…", "La búsqueda no produjo resultados"),
        "de": ("Hilfe durchsuchen…", "Die Suche ergab keine Treffer"),
        "fr": (
            "Rechercher dans l’aide…",
            "La recherche n’a donné aucun résultat",
        ),
        "pt_BR": (
            "Pesquisar na ajuda…",
            "A pesquisa não encontrou resultados",
        ),
    }
    try:
        for language, (placeholder, no_results) in expected_messages.items():
            set_language(APP, language)
            dialog = HelpDialog()

            assert dialog.help_search.placeholderText() == placeholder

            dialog.help_search.setText("query-with-no-matches-7281")

            assert dialog.help_content.toPlainText() == no_results
    finally:
        set_language(APP, "ru")


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
