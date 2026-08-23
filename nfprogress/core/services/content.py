"""Qt-free localization and help projections for API/browser clients."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from help_content import HELP_SECTIONS, render_help_content
from nfprogress.core.agreement import AGREEMENT_ID, agreement_html
from translations_catalog import TRANSLATIONS


SUPPORTED_LANGUAGES = {
    'ru': 'Русский',
    'en': 'English',
    'es': 'Español',
    'de': 'Deutsch',
    'fr': 'Français',
    'pt_BR': 'Português (Brasil)',
}


def translate_source(text: str, language: str) -> str:
    """Translate one canonical Russian string without process-global locale state."""
    if language == 'ru':
        return text
    return TRANSLATIONS.get(language, {}).get(text, text)


class ContentService:
    def languages(self) -> list[dict[str, str]]:
        return [
            {'code': code, 'display_name': display_name}
            for code, display_name in SUPPORTED_LANGUAGES.items()
        ]

    def locale(self, language: str) -> dict[str, str]:
        self._validate_language(language)
        if language == 'ru':
            source_keys = set()
            for catalog in TRANSLATIONS.values():
                source_keys.update(catalog)
            return {source: source for source in sorted(source_keys)}
        return dict(TRANSLATIONS[language])

    def help(self, language: str = 'ru') -> list[dict[str, Any]]:
        self._validate_language(language)
        return [self._project_help(section, language) for section in HELP_SECTIONS]

    def agreement(self, language: str = 'ru') -> dict[str, str]:
        """Project the canonical agreement without importing Qt localization."""
        self._validate_language(language)
        return {
            'id': AGREEMENT_ID,
            'language': language,
            'html': agreement_html(language),
        }

    def _project_help(self, section: dict[str, Any], language: str) -> dict[str, Any]:
        result = {
            'key': section['key'],
            'title': translate_source(section['title'], language),
            'content': render_help_content(
                translate_source(section['content'], language),
            ),
        }
        children = section.get('children', ())
        if children:
            result['children'] = [
                self._project_help(child, language) for child in children
            ]
        else:
            result['children'] = []
        return result

    @staticmethod
    def _validate_language(language: str) -> None:
        if language not in SUPPORTED_LANGUAGES:
            from nfprogress.core.errors import ValidationError
            raise ValidationError('Неподдерживаемый язык интерфейса.')


__all__ = [
    'ContentService', 'SUPPORTED_LANGUAGES', 'translate_source',
]
