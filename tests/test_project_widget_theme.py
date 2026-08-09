from types import SimpleNamespace

import engine
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QListWidget, QListWidgetItem

from main_UI import MainWindow
from UI_fiiles.project_widget import ProjectWidget


def _palette(base, text, highlight, highlighted_text, mid):
    palette = QPalette()
    for group in (
        QPalette.ColorGroup.Active,
        QPalette.ColorGroup.Inactive,
        QPalette.ColorGroup.Disabled,
    ):
        palette.setColor(group, QPalette.ColorRole.Window, base)
        palette.setColor(group, QPalette.ColorRole.Base, base)
        palette.setColor(group, QPalette.ColorRole.WindowText, text)
        palette.setColor(group, QPalette.ColorRole.Text, text)
        palette.setColor(group, QPalette.ColorRole.Highlight, highlight)
        palette.setColor(group, QPalette.ColorRole.HighlightedText, highlighted_text)
        palette.setColor(group, QPalette.ColorRole.Mid, mid)
    return palette


def test_project_widget_refreshes_selection_colors_after_palette_change():
    app = QApplication.instance() or QApplication([])
    original_palette = QPalette(app.palette())
    light_palette = _palette(
        QColor('#f6f6f6'), QColor('#1c1c1c'), QColor('#1769aa'),
        QColor('#ffffff'), QColor('#9e9e9e'),
    )
    dark_palette = _palette(
        QColor('#242424'), QColor('#f4f4f4'), QColor('#315d8a'),
        QColor('#ffffff'), QColor('#707070'),
    )

    try:
        app.setPalette(light_palette)
        project = engine.Project(name='Тестовый проект', goal=1000, unit='symbols')
        widget = ProjectWidget(project, False)
        project_list = QListWidget()
        item = QListWidgetItem()
        project_list.addItem(item)
        project_list.setItemWidget(item, widget)
        project_list.setCurrentItem(item)
        owner = SimpleNamespace(list_projects=project_list)
        MainWindow._sync_project_widget_selection(owner, item, None)

        assert widget.name.palette().color(QPalette.ColorRole.WindowText) == (
            light_palette.color(QPalette.ColorRole.HighlightedText)
        )
        assert widget.circular_progress._end_color == (
            light_palette.color(QPalette.ColorRole.HighlightedText)
        )
        assert widget.circular_progress._background_color != (
            light_palette.color(QPalette.ColorRole.Highlight)
        )

        app.setPalette(dark_palette)
        app.processEvents()

        assert widget.name.palette().color(QPalette.ColorRole.WindowText) == (
            dark_palette.color(QPalette.ColorRole.HighlightedText)
        )
        assert widget.circular_progress._end_color == (
            dark_palette.color(QPalette.ColorRole.HighlightedText)
        )
        assert widget.circular_progress._background_color != (
            dark_palette.color(QPalette.ColorRole.Highlight)
        )

        project_list.setCurrentItem(None)
        MainWindow._sync_project_widget_selection(owner, None, item)
        assert widget.name.palette().color(QPalette.ColorRole.WindowText) == (
            dark_palette.color(QPalette.ColorRole.WindowText)
        )
        assert widget.circular_progress._end_color == (
            dark_palette.color(QPalette.ColorRole.Highlight)
        )
    finally:
        app.setPalette(original_palette)
        app.processEvents()
