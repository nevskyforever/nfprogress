"""Settings use cases shared by legacy and browser clients."""

from __future__ import annotations

from datetime import time
from typing import Any

import engine

from nfprogress.core.errors import ValidationError
from nfprogress.core.agreement import AGREEMENT_ID
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
    'frontend_motion',
})
DESKTOP_KEYS = frozenset({
    'background_synch',
})
UI_STATE_KEYS = frozenset({
    'frontend_project_filter',
    'frontend_project_sort',
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
FRONTEND_PROJECT_FILTERS = frozenset({'all', 'активен', 'в архиве', 'завершен'})
FRONTEND_PROJECT_SORTS = frozenset({'name', 'deadline', 'progress', 'updated'})


class SettingsService:
    def __init__(
            self, repository, *, platform: str = 'web', developer_mode: bool = False,
    ):
        self.repository = repository
        self.platform = platform
        self.developer_mode = developer_mode

    def get(self) -> dict[str, Any]:
        values = dict(self.repository.read_settings())
        values.setdefault('frontend_motion', 'full')
        values['developer_mode'] = self.developer_mode
        if self.platform == 'desktop':
            values.setdefault('background_synch', True)
        return {
            'values': to_json_safe(values),
            'platform': self.platform,
            'capabilities': {
                'local_file_sync': self.platform == 'desktop',
                'background_file_sync': self.platform == 'desktop',
                # The UI additionally checks the Tauri release-build flag, so
                # unsigned local/dev bundles never contact the update channel.
                'native_updates': self.platform == 'desktop',
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

        if {'inf_project', 'global_streak'} & patch.keys():
            self._update_project_settings(patch)
        else:
            self.repository.update_settings(lambda settings: settings.update(patch))
        return self.get()

    def accept_user_agreement(self, agreement_id: str) -> dict[str, Any]:
        """Persist the legacy-compatible acceptance after version validation."""
        if agreement_id != AGREEMENT_ID:
            raise ValidationError(
                'Условия использования изменились. Перезагрузите соглашение.',
            )
        self.repository.update_settings(
            lambda settings: settings.update({'user_agreement': True}),
        )
        return self.get()

    def _update_project_settings(self, patch: dict[str, Any]) -> None:
        """Apply settings whose legacy semantics also mutate project storage."""
        with self.repository.locked():
            settings = self.repository.read_settings()
            data = self.repository.read_projects()
            projects = data.setdefault('projects', {})

            removes_infinite_project = (
                patch.get('inf_project') is False
                and any(key in projects for key in ('Общий проект', 'inf_project'))
            )
            clears_streaks = (
                patch.get('global_streak') is False
                and self._has_streak_state(data)
            )
            if removes_infinite_project or clears_streaks:
                self.repository.create_backup(('data', 'settings'))

            if 'inf_project' in patch:
                self._set_infinite_project(data, patch['inf_project'])
            if patch.get('global_streak') is False:
                self._clear_streaks(data)

            settings.update(patch)
            self.repository.write_projects(data)
            self.repository.write_settings(settings)

    @staticmethod
    def _set_infinite_project(data: dict[str, Any], enabled: bool) -> None:
        projects = data.setdefault('projects', {})
        if enabled:
            legacy_project = projects.pop('inf_project', None)
            if legacy_project is not None:
                legacy_project.name = 'Общий проект'
                projects['Общий проект'] = legacy_project
            elif 'Общий проект' not in projects:
                projects['Общий проект'] = engine.Project(
                    name='Общий проект', goal=float('inf'), progress=100,
                )
            return
        projects.pop('Общий проект', None)
        projects.pop('inf_project', None)

    @staticmethod
    def _has_streak_state(data: dict[str, Any]) -> bool:
        if data.get('global_streaks') or data.get('last_global_streak_bonus'):
            return True
        for project in data.get('projects', {}).values():
            if getattr(project, 'streaks', None):
                return True
            if any(getattr(stage, 'streaks', None) for stage in project.stages):
                return True
        return False

    @staticmethod
    def _clear_streaks(data: dict[str, Any]) -> None:
        data['global_streaks'] = []
        data['global_streak_status'] = 'No'
        data['max_global_streak'] = 0
        data['last_global_streak_bonus'] = None
        data['last_global_streak_lost_date'] = None
        for project in data.get('projects', {}).values():
            project.streaks = []
            project.streak_status = 'No'
            for stage in getattr(project, 'stages', []):
                stage.streaks = []
                stage.streak_status = 'No'

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
        if 'frontend_motion' in patch and patch['frontend_motion'] not in {
            'system', 'full', 'reduced',
        }:
            raise ValidationError('Неизвестный режим анимации интерфейса.')
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
            # Keep the established Qt range. The new frontend uses the same
            # persisted setting for its accessible notification stack.
            if not 1 <= duration <= 3600:
                raise ValidationError('Время уведомления должно быть от 1 до 3600 секунд.')
            patch = {**patch, 'notification_display_time': duration}
        if 'project_filter' in patch and patch['project_filter'] not in PROJECT_FILTERS:
            raise ValidationError('Неизвестный фильтр проектов.')
        if 'project_sort' in patch and patch['project_sort'] not in PROJECT_SORTS:
            raise ValidationError('Неизвестная сортировка проектов.')
        if (
                'frontend_project_filter' in patch
                and patch['frontend_project_filter'] not in FRONTEND_PROJECT_FILTERS
        ):
            raise ValidationError('Неизвестный фильтр проектов для нового интерфейса.')
        if (
                'frontend_project_sort' in patch
                and patch['frontend_project_sort'] not in FRONTEND_PROJECT_SORTS
        ):
            raise ValidationError('Неизвестная сортировка проектов для нового интерфейса.')
        if 'inventory_filter' in patch:
            value = patch['inventory_filter']
            if not isinstance(value, str) or not value.strip() or len(value) > 100:
                raise ValidationError('Неверный фильтр инвентаря.')
            patch['inventory_filter'] = value.strip()
        return patch


__all__ = ['SettingsService']
