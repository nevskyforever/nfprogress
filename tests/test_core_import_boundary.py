"""Regression coverage for the Qt-free shared application boundary."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import engine
import game
import game_data


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_IMPORTS = (
    'engine',
    'game',
    'game_data',
    'nfprogress.core.storage',
    'nfprogress.core.serialization.projections',
    'nfprogress.core.services.content',
    'nfprogress.core.services.game',
    'nfprogress.core.services.integrations',
    'nfprogress.core.services.notes',
    'nfprogress.core.services.projects',
    'nfprogress.core.services.settings',
)
UI_IMPORT = re.compile(
    r'^\s*(?:from|import)\s+(?:main_UI|game_UI|UI_fiiles)\b',
    re.MULTILINE,
)


def test_core_modules_import_without_pyside_or_ui_dependencies():
    """The backend boundary must stay usable in a Python-only sidecar."""
    import_guard = f'''\
import builtins

original_import = builtins.__import__


def guarded_import(name, *args, **kwargs):
    if name == "PySide6" or name.startswith("PySide6."):
        raise RuntimeError(f"Qt import is forbidden in the shared core: {{name}}")
    return original_import(name, *args, **kwargs)


builtins.__import__ = guarded_import
for module_name in {CORE_IMPORTS!r}:
    __import__(module_name)
'''
    result = subprocess.run(
        [sys.executable, '-c', import_guard],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout

    sources = [
        PROJECT_ROOT / 'engine.py',
        PROJECT_ROOT / 'game.py',
        PROJECT_ROOT / 'game_data.py',
        *(PROJECT_ROOT / 'nfprogress' / 'core').rglob('*.py'),
    ]
    for source_path in sources:
        source = source_path.read_text(encoding='utf-8')
        assert 'PySide6' not in source, source_path.relative_to(PROJECT_ROOT)
        assert UI_IMPORT.search(source) is None, source_path.relative_to(PROJECT_ROOT)


def test_pickle_domain_classes_keep_their_legacy_module_paths():
    """Existing pickle payloads still resolve their authoritative classes."""
    assert engine.Project.__module__ == 'engine'
    assert engine.Stage.__module__ == 'engine'
    assert game.Gamer.__module__ == 'game'
    assert game_data.Buff.__module__ == 'game_data'
