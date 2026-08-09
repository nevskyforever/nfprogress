import subprocess
import sys
from pathlib import Path

from translations_catalog import TRANSLATIONS, _load_language_catalog


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_main_ui_import_keeps_optional_native_stacks_lazy():
    script = """
import sys
import main_UI

optional_modules = {
    'docx',
    'lxml',
    'mindmap',
    'project_notes',
    'update_checker',
    'PySide6.QtQuick',
    'PySide6.QtWebView',
}
loaded = optional_modules.intersection(sys.modules)
assert not loaded, sorted(loaded)
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_translation_catalog_caches_only_the_last_decoded_language():
    _load_language_catalog.cache_clear()

    assert TRANSLATIONS["en"]["Настройки"] == "Settings"
    assert _load_language_catalog.cache_info().currsize == 1

    assert TRANSLATIONS["de"]["Настройки"] == "Einstellungen"
    cache_info = _load_language_catalog.cache_info()
    assert cache_info.maxsize == 1
    assert cache_info.currsize == 1
