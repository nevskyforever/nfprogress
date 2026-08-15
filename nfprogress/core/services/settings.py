"""Settings use cases shared by legacy and browser clients."""

from __future__ import annotations

from datetime import time
from typing import Any

from nfprogress.core.errors import ValidationError
from nfprogress.core.serialization import to_json_safe
from nfprogress.core.services.content import SUPPORTED_LANGUAGES


GENERAL_KEYS = frozenset({
    'game_mode',
    'inf_project',
    'global_streak',
    'show_written_today_in_all_projects',
    'notification_display_time',
    'start_day_time',
    'language',
    'frontend_theme',
})
DESKTOP_KEYS = frozenset({
    'background_synch',
})
UI_STATE_KEYS = frozenset({
    'inventory_filter',
    'project_filter',
    'project_sort',
})
BOOLEAN_KEYS = frozenset({
    'game_mode',
    'inf_project',
    'global_streak',
    'show_written_today_in_all_projects',
    'background_synch',
})
PROJECT_FILTERS = frozenset({'Активен', 'В архиве', 'Завершен'})
PROJECT_SORTS = frozenset({'Название', 'Дедлайн', 'Прогресс'})


class SettingsService:
    def __init__(self, repository, *, platform: str = 'web'):
        self.repository = repository
        self.platform = platform

    def get(self) -> dict[str, Any]:
        values = self.repository.read_settings()
        if self.platform == 'desktop':
            values.setdefault('background_synch', True)
        return {
            'values': to_json_safe(values),
            'platform': self.platform,
            'capabilities': {
                'local_file_sync': self.platform == 'desktop',
                'background_file_sync': self.platform == 'desktop',
                # Legacy packages use a Qt-specific updater and release format.
                # Tauri updates stay disabled until signed Tauri artifacts exist.
                'native_updates': False,
                'remote_api': self.platform in {'web', 'ios', 'android'},
            },
            'editable_keys': sorted(
                GENERAL_KEYS
                | UI_STATE_KEYS
                | (DESKTOP_KEYS if self.platform == 'desktop' else frozenset())
            ),
        }

    def update(self, patch: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(patch, dict):
            raise ValidationError('Некорректные настройки.')
        allowed = GENERAL_KEYS | UI_STATE_KEYS
        if self.platform == 'desktop':
            allowed |= DESKTOP_KEYS
        unknown = set(patch) - allowed
        if unknown:
            raise ValidationError(
                f'Настройки недоступны на этой платформе: {", ".join(sorted(unknown))}.',
            )
        patch = self._validated_patch(patch)

        self.repository.update_settings(lambda settings: settings.update(patch))
        return self.get()

    @staticmethod
    def _validated_patch(patch: dict[str, Any]) -> dict[str, Any]:
        patch = dict(patch)
        for key in BOOLEAN_KEYS & patch.keys():
            if not isinstance(patch[key], bool):
                raise ValidationError(f'Настройка {key} должна быть логической.')
        if 'language' in patch and patch['language'] not in SUPPORTED_LANGUAGES:
            raise ValidationError('Неподдерживаемый язык интерфейса.')
        if 'frontend_theme' in patch and patch['frontend_theme'] not in {
            'system', 'light', 'dark',
        }:
            raise ValidationError('Неизвестная тема интерфейса.')
        if 'start_day_time' in patch:
            raw_time = patch['start_day_time']
            if not isinstance(raw_time, str):
                raise ValidationError('Время начала суток имеет неверный формат.')
            try:
                parsed_time = time.fromisoformat(raw_time)
            except ValueError:
                raise ValidationError(
                    'Время начала суток имеет неверный формат.',
                ) from None
            if parsed_time.tzinfo is not None:
                raise ValidationError('Время начала суток должно быть локальным.')
            patch['start_day_time'] = parsed_time.isoformat(timespec='seconds')
        if 'notification_display_time' in patch:
            if (
                    isinstance(patch['notification_display_time'], bool)
                    or not isinstance(patch['notification_display_time'], int)
            ):
                raise ValidationError('Время уведомления должно быть целым числом.')
            duration = patch['notification_display_time']
            if not 1 <= duration <= 120:
                raise ValidationError('Время уведомления должно быть от 1 до 120 секунд.')
            patch = {**patch, 'notification_display_time': duration}
        if 'project_filter' in patch and patch['project_filter'] not in PROJECT_FILTERS:
            raise ValidationError('Неизвестный фильтр проектов.')
        if 'project_sort' in patch and patch['project_sort'] not in PROJECT_SORTS:
            raise ValidationError('Неизвестная сортировка проектов.')
        if 'inventory_filter' in patch:
            value = patch['inventory_filter']
            if not isinstance(value, str) or not value.strip() or len(value) > 100:
                raise ValidationError('Неверный фильтр инвентаря.')
            patch['inventory_filter'] = value.strip()
        return patch


__all__ = ['SettingsService']
