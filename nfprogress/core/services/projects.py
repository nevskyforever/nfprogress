"""Qt-free project, stage, progress, and statistics application services."""

from __future__ import annotations

import math
import uuid
from collections import defaultdict
from datetime import date, datetime
from typing import Any, Callable

import engine

from nfprogress.core.errors import ConflictError, NotFoundError, ValidationError
from nfprogress.core.serialization import serialize_note, serialize_project


VALID_UNITS = frozenset({'symbols', 'A4', 'author_list', 'ficbook_pages'})
VALID_STATUSES = frozenset({'активен', 'в архиве', 'завершен'})


class ProjectService:
    """Own project mutations while retaining the proven legacy domain model."""

    def __init__(self, repository, game_service=None):
        self.repository = repository
        self.game_service = game_service

    def list_projects(
            self,
            *,
            status: str | None = None,
            search: str = '',
            sort: str = 'manual',
    ) -> list[dict[str, Any]]:
        if status is not None and status not in VALID_STATUSES:
            raise ValidationError('Неизвестный статус проекта.')
        data = self._read_projects_with_streak_refresh()
        projects = list(data.get('projects', {}).values())
        if status is not None:
            projects = [project for project in projects if project.status == status]

        query = search.strip().casefold()
        if query:
            projects = [
                project for project in projects
                if query in project.name.casefold()
                or any(query in stage.name.casefold() for stage in project.stages)
            ]

        saved_order = data.get('project_order', [])
        order_index = {
            project_id: index
            for index, project_id in enumerate(saved_order)
            if isinstance(project_id, str)
        } if isinstance(saved_order, list) else {}
        fallback_index = {
            project.project_id: index for index, project in enumerate(projects)
        }
        sorters: dict[str, Callable[[engine.Project], Any]] = {
            'manual': lambda project: (
                order_index.get(
                    project.project_id,
                    len(order_index) + fallback_index[project.project_id],
                ),
                project.name.casefold(),
            ),
            'name': lambda project: project.name.casefold(),
            'deadline': lambda project: (
                project.deadline == 'Нет',
                project.deadline if isinstance(project.deadline, date) else date.max,
                project.name.casefold(),
            ),
            'progress': lambda project: (-project.progress, project.name.casefold()),
            'updated': lambda project: (
                -self._date_ordinal(getattr(project, 'edit_date', None)),
                project.name.casefold(),
            ),
        }
        if sort not in sorters:
            raise ValidationError('Неизвестный порядок сортировки.')
        projects.sort(key=sorters[sort])
        return [serialize_project(project) for project in projects]

    def get_project(self, project_id: str) -> dict[str, Any]:
        data = self._read_projects_with_streak_refresh()
        project = self._find_project(data, project_id)
        return serialize_project(project)

    def refresh_streak_statuses(self) -> None:
        """Apply legacy daily streak/freeze transitions in repository context."""
        self.repository.update_projects(self._refresh_streak_statuses)

    def create_project(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = self._validated_name(payload.get('name'))
        unit = self._validated_unit(payload.get('unit', 'symbols'))
        infinite = bool(payload.get('infinite', False))
        goal = float('inf') if infinite else self._positive_number(payload.get('goal'), 'Цель')
        total = self._nonnegative_number(payload.get('total', 0), 'Текущее значение')
        goal = self._round_for_unit(goal, unit)
        total = self._round_for_unit(total, unit)
        if not infinite:
            self._ensure_convertible(goal, unit, 'Цель')
        self._ensure_convertible(total, unit, 'Текущее значение')
        deadline = self._validated_deadline(payload.get('deadline'))
        personal_goal = self._nonnegative_number(
            payload.get('personal_goal', 0), 'Цель на день',
        )
        self._ensure_convertible(personal_goal, unit, 'Цель на день')

        def mutate(data):
            projects = data.setdefault('projects', {})
            if name in projects:
                raise ConflictError('Проект с таким именем уже существует.')
            project = engine.Project(
                name=name,
                goal=goal,
                deadline=deadline,
                total_symbols=total,
                unit=unit,
                personal_goal_for_the_day=personal_goal,
                auto_freeze=bool(payload.get('auto_freeze', True)),
            )
            project.cover_image = self._validated_cover_image(payload.get('cover_image'))
            project.folder_id = self._validated_folder_id(data, payload.get('folder_id'))
            project.set_streak_state(bool(payload.get('streak_enabled', False)))
            for stage_payload in payload.get('stages', []):
                project.stages.append(self._new_stage(project, stage_payload))
            if project.stages:
                project.enable_stages = True
            elif bool(payload.get('stages_enabled', False)):
                project.convert_to_stages()
            project.combine_stage_mindmaps = bool(
                project.stages and payload.get('combine_stage_mindmaps', False)
            )
            project.get_today_goal_value()
            projects[project.name] = project
            order = data.setdefault('project_order', [])
            if not isinstance(order, list):
                order = data['project_order'] = []
            order.append(project.project_id)
            data['last'] = project.name
            return serialize_project(project)

        return self.repository.update_projects(mutate)

    def update_project(
            self, project_id: str, payload: dict[str, Any],
    ) -> dict[str, Any]:
        def mutate(data):
            project = self._find_project(data, project_id)
            if self._is_shared_project(project):
                raise ValidationError('Общий проект управляется через настройки.')
            if set(payload) != {'folder_id'}:
                self._require_editable(project)
            projects = data['projects']
            old_name = project.name
            old_unit = project.unit

            new_name = (
                self._validated_name(payload['name'])
                if 'name' in payload else old_name
            )
            if new_name != old_name and new_name in projects:
                raise ConflictError('Проект с таким именем уже существует.')

            new_unit = (
                self._validated_unit(payload['unit'])
                if 'unit' in payload else old_unit
            )
            if new_unit != old_unit:
                self._convert_entity_unit(project, old_unit, new_unit)

            requested_stages = payload.get('stages_enabled')
            convert_to_stages = requested_stages is True and not project.has_stages()
            if requested_stages is False and project.has_stages():
                project.convert_to_single()

            if 'infinite' in payload or 'goal' in payload:
                infinite = bool(payload.get('infinite', project.goal == float('inf')))
                if project.has_stages() and ('goal' in payload or infinite):
                    raise ValidationError('Цель проекта с этапами определяется целями этапов.')
                requested_goal = (
                    float('inf') if infinite
                    else self._round_for_unit(
                        self._positive_number(payload.get('goal', project.goal), 'Цель'),
                        new_unit,
                    )
                )
                if not infinite:
                    self._ensure_convertible(requested_goal, new_unit, 'Цель')
                project.goal = requested_goal
            if 'total' in payload:
                if project.has_stages():
                    raise ValidationError('Объём проекта с этапами определяется этапами.')
                requested_total = self._round_for_unit(
                    self._nonnegative_number(payload['total'], 'Текущее значение'),
                    new_unit,
                )
                self._ensure_convertible(
                    requested_total, new_unit, 'Текущее значение',
                )
                project.total_units = requested_total
            if convert_to_stages:
                # Apply explicitly submitted single-project values first so
                # conversion can preserve them in the initial stage.
                project.convert_to_stages()
            if 'deadline' in payload:
                project.deadline = self._validated_deadline(payload['deadline'])
            if 'personal_goal' in payload:
                personal_goal = self._nonnegative_number(
                    payload['personal_goal'], 'Цель на день',
                )
                self._ensure_convertible(personal_goal, new_unit, 'Цель на день')
                self._apply_daily_goal_streak_rules(
                    data, project, personal_goal, payload,
                )
                project.personal_goal_for_the_day = personal_goal
            if 'auto_freeze' in payload:
                project.auto_freeze = bool(payload['auto_freeze'])
            if 'cover_image' in payload:
                project.cover_image = self._validated_cover_image(payload['cover_image'])
            if 'folder_id' in payload:
                project.folder_id = self._validated_folder_id(data, payload['folder_id'])
            if 'streak_enabled' in payload:
                project.set_streak_state(bool(payload['streak_enabled']))

            project._name = new_name
            project.unit = new_unit
            project.edit_date = engine.today_for_test()
            for stage in project.stages:
                stage.parent_project_name = new_name
                stage.unit = new_unit
            project.combine_stage_mindmaps = bool(
                project.has_stages()
                and payload.get(
                    'combine_stage_mindmaps', project.combine_stage_mindmaps,
                )
            )
            project.get_today_goal_value(
                recalculate_from_current_progress=bool(payload.get('recalculate_plan', False)),
            )
            if new_name != old_name:
                del projects[old_name]
                projects[new_name] = project
                if data.get('last') == old_name:
                    data['last'] = new_name
            return serialize_project(project)

        return self.repository.update_projects(mutate)

    @staticmethod
    def _validated_cover_image(value: Any) -> str | None:
        if value is None:
            return None
        normalized = engine.normalize_project_cover_image(value)
        if normalized is None:
            raise ValidationError('Некорректное изображение обложки.')
        return normalized

    def delete_project(self, project_id: str) -> None:
        def mutate(data):
            project = self._find_project(data, project_id)
            if self._is_shared_project(project):
                raise ValidationError('Общий проект можно отключить только в настройках.')
            del data['projects'][project.name]
            order = data.get('project_order')
            if isinstance(order, list):
                data['project_order'] = [item for item in order if item != project.project_id]
            if data.get('last') == project.name:
                data['last'] = None

        self.repository.update_projects(mutate)

    def reorder_projects(self, project_ids: list[str]) -> list[dict[str, Any]]:
        def mutate(data):
            projects = list(data.get('projects', {}).values())
            existing_ids = {project.project_id for project in projects}
            requested_ids = set(project_ids)
            if (
                    not project_ids
                    or len(requested_ids) != len(project_ids)
                    or not requested_ids.issubset(existing_ids)
            ):
                raise ValidationError(
                    'Порядок должен содержать известные проекты без повторений.',
                )

            saved_order = data.get('project_order', [])
            normalized_order = [
                project_id for project_id in saved_order
                if isinstance(project_id, str) and project_id in existing_ids
            ] if isinstance(saved_order, list) else []
            normalized_order.extend(
                project.project_id
                for project in projects
                if project.project_id not in normalized_order
            )
            visible_positions = [
                index for index, project_id in enumerate(normalized_order)
                if project_id in requested_ids
            ]
            for index, project_id in zip(visible_positions, project_ids):
                normalized_order[index] = project_id
            data['project_order'] = normalized_order
            by_id = {project.project_id: project for project in projects}
            return [serialize_project(by_id[project_id]) for project_id in project_ids]

        return self.repository.update_projects(mutate)

    def list_folders(self) -> list[dict[str, str]]:
        data = self.repository.read_projects()
        return self._normalized_folders(data)

    def create_folder(self, name: str) -> dict[str, str]:
        normalized_name = self._validated_folder_name(name)

        def mutate(data):
            folders = self._normalized_folders(data)
            if any(folder['name'].casefold() == normalized_name.casefold() for folder in folders):
                raise ConflictError('Папка с таким названием уже существует.')
            folder = {'id': uuid.uuid4().hex, 'name': normalized_name}
            folders.append(folder)
            data['project_folders'] = folders
            return folder

        return self.repository.update_projects(mutate)

    def update_folder(self, folder_id: str, name: str) -> dict[str, str]:
        normalized_name = self._validated_folder_name(name)

        def mutate(data):
            folders = self._normalized_folders(data)
            folder = next((item for item in folders if item['id'] == folder_id), None)
            if folder is None:
                raise NotFoundError('Папка не найдена.')
            if any(
                item['id'] != folder_id and item['name'].casefold() == normalized_name.casefold()
                for item in folders
            ):
                raise ConflictError('Папка с таким названием уже существует.')
            folder['name'] = normalized_name
            data['project_folders'] = folders
            return folder

        return self.repository.update_projects(mutate)

    def delete_folder(self, folder_id: str) -> None:
        def mutate(data):
            folders = self._normalized_folders(data)
            if not any(folder['id'] == folder_id for folder in folders):
                raise NotFoundError('Папка не найдена.')
            data['project_folders'] = [folder for folder in folders if folder['id'] != folder_id]
            for project in data.get('projects', {}).values():
                if getattr(project, 'folder_id', None) == folder_id:
                    project.folder_id = None

        self.repository.update_projects(mutate)

    @staticmethod
    def _normalized_folders(data: dict[str, Any]) -> list[dict[str, str]]:
        raw_folders = data.get('project_folders', [])
        if not isinstance(raw_folders, list):
            return []
        folders: list[dict[str, str]] = []
        seen_ids: set[str] = set()
        for item in raw_folders:
            if not isinstance(item, dict):
                continue
            folder_id = item.get('id')
            name = item.get('name')
            if (
                not isinstance(folder_id, str) or not folder_id or folder_id in seen_ids
                or not isinstance(name, str) or not name.strip()
            ):
                continue
            seen_ids.add(folder_id)
            folders.append({'id': folder_id, 'name': name.strip()[:120]})
        return folders

    @classmethod
    def _validated_folder_id(cls, data: dict[str, Any], value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str) or not value:
            raise ValidationError('Некорректная папка проекта.')
        if not any(folder['id'] == value for folder in cls._normalized_folders(data)):
            raise ValidationError('Папка проекта не найдена.')
        return value

    @staticmethod
    def _validated_folder_name(value: Any) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValidationError('Введите название папки.')
        name = value.strip()
        if len(name) > 120:
            raise ValidationError('Название папки не должно быть длиннее 120 символов.')
        return name

    def set_project_archived(self, project_id: str, archived: bool) -> dict[str, Any]:
        def mutate(data):
            project = self._find_project(data, project_id)
            if self._is_shared_project(project):
                raise ValidationError('Общий проект нельзя архивировать.')
            if project.status == 'завершен':
                raise ValidationError('Завершённый проект нельзя архивировать или активировать.')
            if archived:
                project.status = 'в архиве'
                project.deadline = 'Нет'
                project.streaks = []
                project.streak_status = 'No'
            else:
                project.status = 'активен'
            project.edit_date = engine.today_for_test()
            return serialize_project(project)

        return self.repository.update_projects(mutate)

    def complete_project(self, project_id: str) -> dict[str, Any]:
        completion_events: list[dict[str, Any]] = []
        settings = self.repository.read_settings()

        def mutate(data):
            project = self._find_project(data, project_id)
            if project.status == 'завершен':
                for entity in [*project.stages, project]:
                    if entity.status == 'завершен':
                        completion_events.append(
                            self._completion_event(
                                project,
                                entity,
                                include_streak=bool(
                                    settings.get('global_streak', False)
                                ),
                            )
                        )
                return serialize_project(project)
            if project.goal == float('inf'):
                raise ValidationError('Бесконечный проект нельзя завершить по числовой цели.')
            if project.total_units < project.goal:
                raise ValidationError('Сначала достигните цели проекта.')
            completion_date = engine.today_for_test()
            for entity in engine.get_completion_entities(project):
                entity.status = 'завершен'
                entity.complete_date = completion_date
                completion_events.append(
                    self._completion_event(
                        project,
                        entity,
                        include_streak=bool(settings.get('global_streak', False)),
                    )
                )
            return serialize_project(project)

        payload = self.repository.update_projects(mutate)
        if self.game_service is not None and completion_events:
            # The game command is idempotent. If it fails after the project save,
            # retrying this endpoint safely reconciles the missing reward.
            self.game_service.record_completions(completion_events)
        return payload

    def create_stage(
            self, project_id: str, payload: dict[str, Any],
    ) -> dict[str, Any]:
        def mutate(data):
            project = self._find_project(data, project_id)
            self._require_editable(project)
            shared_project = self._is_shared_project(project)
            if any(stage.name == str(payload.get('name', '')).strip() for stage in project.stages):
                raise ConflictError('Этап с таким именем уже существует.')
            had_legacy_shared_source = bool(
                shared_project
                and not project.has_stages()
                and (project.notes or project.synch is not None)
            )
            if not project.has_stages() and (
                    project.notes or project.total_units or had_legacy_shared_source
            ):
                project.convert_to_stages()
                if had_legacy_shared_source:
                    project.stages[0]._name = 'Источник 1'
            stage_payload = dict(payload)
            if shared_project:
                stage_payload['infinite'] = True
                stage_payload.pop('goal', None)
            stage = self._new_stage(project, stage_payload)
            project.enable_stages = True
            project.stages.append(stage)
            project.edit_date = engine.today_for_test()
            return self._serialize_stage_with_parent(project, stage)

        return self.repository.update_projects(mutate)

    def update_stage(
            self, project_id: str, stage_id: str, payload: dict[str, Any],
    ) -> dict[str, Any]:
        def mutate(data):
            project = self._find_project(data, project_id)
            if self._is_shared_project(project):
                raise ValidationError('Источники Общего проекта не редактируются.')
            stage = self._find_stage(project, stage_id)
            self._require_editable(stage)
            old_unit = stage.unit
            new_unit = (
                self._validated_unit(payload['unit'])
                if 'unit' in payload else project.unit
            )
            if new_unit != project.unit:
                raise ValidationError('Единица этапа должна совпадать с единицей проекта.')
            if new_unit != old_unit:
                self._convert_entity_unit(stage, old_unit, new_unit)
            if 'name' in payload:
                name = self._validated_name(payload['name'])
                if any(item is not stage and item.name == name for item in project.stages):
                    raise ConflictError('Этап с таким именем уже существует.')
                stage._name = name
            if 'infinite' in payload or 'goal' in payload:
                infinite = bool(payload.get('infinite', stage.goal == float('inf')))
                requested_goal = (
                    float('inf') if infinite
                    else self._round_for_unit(
                        self._positive_number(payload.get('goal', stage.goal), 'Цель'),
                        new_unit,
                    )
                )
                if not infinite:
                    self._ensure_convertible(requested_goal, new_unit, 'Цель')
                stage.goal = requested_goal
            if 'total' in payload:
                requested_total = self._round_for_unit(
                    self._nonnegative_number(payload['total'], 'Текущее значение'),
                    new_unit,
                )
                self._ensure_convertible(
                    requested_total, new_unit, 'Текущее значение',
                )
                stage.total_units = requested_total
            if 'deadline' in payload:
                stage.deadline = self._validated_deadline(payload['deadline'])
            if 'personal_goal' in payload:
                personal_goal = self._nonnegative_number(
                    payload['personal_goal'], 'Цель на день',
                )
                self._ensure_convertible(personal_goal, new_unit, 'Цель на день')
                self._apply_daily_goal_streak_rules(
                    data, stage, personal_goal, payload,
                )
                stage.personal_goal_for_the_day = personal_goal
            if 'auto_freeze' in payload:
                stage.auto_freeze = bool(payload['auto_freeze'])
            if 'streak_enabled' in payload:
                stage.set_streak_state(bool(payload['streak_enabled']))
            stage.edit_date = engine.today_for_test()
            stage.get_today_goal_value(
                recalculate_from_current_progress=bool(payload.get('recalculate_plan', False)),
            )
            project.edit_date = engine.today_for_test()
            return self._serialize_stage_with_parent(project, stage)

        return self.repository.update_projects(mutate)

    def delete_stage(self, project_id: str, stage_id: str) -> None:
        def mutate(data):
            project = self._find_project(data, project_id)
            stage = self._find_stage(project, stage_id)
            project.stages.remove(stage)
            if not project.stages:
                project.enable_stages = False
                project.combine_stage_mindmaps = False
            project.edit_date = engine.today_for_test()

        self.repository.update_projects(mutate)

    def reorder_stages(self, project_id: str, stage_ids: list[str]) -> dict[str, Any]:
        def mutate(data):
            project = self._find_project(data, project_id)
            self._require_editable(project)
            existing = {stage.stage_id: stage for stage in project.stages}
            if set(stage_ids) != set(existing) or len(stage_ids) != len(existing):
                raise ValidationError('Порядок должен содержать каждый этап ровно один раз.')
            project.stages = [existing[stage_id] for stage_id in stage_ids]
            project.edit_date = engine.today_for_test()
            return serialize_project(project)

        return self.repository.update_projects(mutate)

    def complete_stage(self, project_id: str, stage_id: str) -> dict[str, Any]:
        completion_events: list[dict[str, Any]] = []
        settings = self.repository.read_settings()

        def mutate(data):
            project = self._find_project(data, project_id)
            stage = self._find_stage(project, stage_id)
            if stage.status == 'завершен':
                completion_events.append(
                    self._completion_event(
                        project,
                        stage,
                        include_streak=bool(settings.get('global_streak', False)),
                    )
                )
                return self._serialize_stage_with_parent(project, stage)
            if stage.goal == float('inf'):
                raise ValidationError('Бесконечный этап нельзя завершить по числовой цели.')
            if stage.total_units < stage.goal:
                raise ValidationError('Сначала достигните цели этапа.')
            stage.status = 'завершен'
            stage.complete_date = engine.today_for_test()
            completion_events.append(
                self._completion_event(
                    project,
                    stage,
                    include_streak=bool(settings.get('global_streak', False)),
                )
            )
            return self._serialize_stage_with_parent(project, stage)

        payload = self.repository.update_projects(mutate)
        if self.game_service is not None and completion_events:
            self.game_service.record_completions(completion_events)
        return payload

    def record_progress(
            self,
            project_id: str,
            *,
            new_total: float,
            stage_id: str | None = None,
    ) -> dict[str, Any]:
        return self._record_progress(
            project_id,
            new_total=new_total,
            stage_id=stage_id,
            occurred_at=None,
        )

    def record_synchronized_progress(
            self,
            project_id: str,
            *,
            new_total: float,
            source_modified_at: datetime,
            stage_id: str | None = None,
    ) -> dict[str, Any]:
        """Record external-file progress while preserving its trusted mtime."""
        occurred_at = self._validated_source_modified_at(source_modified_at)
        return self._record_progress(
            project_id,
            new_total=new_total,
            stage_id=stage_id,
            occurred_at=occurred_at,
        )

    def _record_progress(
            self,
            project_id: str,
            *,
            new_total: float,
            stage_id: str | None,
            occurred_at: datetime | None,
    ) -> dict[str, Any]:
        event: dict[str, Any] = {}
        settings = self.repository.read_settings()

        def mutate(data):
            project = self._find_project(data, project_id)
            entity = self._find_stage(project, stage_id) if stage_id else project
            self._require_editable(entity)
            if entity.has_stages():
                raise ValidationError('Записывайте прогресс в конкретный этап.')
            if occurred_at is None and getattr(entity, 'synch', None) is not None:
                raise ValidationError(
                    'Включена синхронизация. Ручная запись прогресса недоступна.',
                )
            total = self._round_for_unit(
                self._nonnegative_number(new_total, 'Новое общее значение'),
                entity.unit,
            )
            self._ensure_convertible(total, entity.unit, 'Новое общее значение')
            if math.isclose(float(total), float(entity.total_units), abs_tol=0.009):
                raise ConflictError('Значение не изменилось.')
            if occurred_at is not None:
                existing_dates = [
                    self._local_naive_datetime(note.date_create)
                    for note in entity.notes
                    if isinstance(getattr(note, 'date_create', None), datetime)
                ]
                if existing_dates and occurred_at < max(existing_dates):
                    raise ConflictError(
                        'sync_source_stale',
                        'Источник синхронизации устарел и не будет применён.',
                    )
            new_total_symbols = engine.unit_converter(entity.unit, total, 'symbols')
            added_symbols = new_total_symbols - entity.get_total_symbols()
            goal_symbols = entity.get_goal_symbols()
            added_progress = (
                0 if goal_symbols in (0, float('inf'))
                else added_symbols / goal_symbols * 100
            )
            note = engine.Note(
                new_total_symbols,
                added_symbols,
                added_progress,
                date_create=occurred_at,
            )
            entity.set_new_notes(note)
            entity.edit_date = engine.today_for_test()
            entity.get_streak_status()
            project.edit_date = entity.edit_date

            streak_events: list[dict[str, Any]] = []
            if (
                    added_symbols > 0
                    and settings.get('game_mode', False)
                    and settings.get('global_streak', False)
            ):
                bonus_entity = (
                    project
                    if entity is project or project.deadline != 'Нет'
                    else entity
                )
                local_status = bonus_entity.get_streak_status()
                bonus_day = engine.today_for_test()
                if engine.streak_bonus_is_due(
                        getattr(bonus_entity, 'last_streak_bonus', None), bonus_day,
                ):
                    streak_events.append({
                        'type': 'Local',
                        'status': local_status,
                        'length': engine.streak_length(bonus_entity.streaks),
                        'key': self._game_project_key(project, bonus_entity),
                    })
                if engine.streak_bonus_is_due(
                        data.get('last_global_streak_bonus'), bonus_day,
                ):
                    streak_events.append({
                        'type': 'Global',
                        'status': engine.global_streak_status(data),
                        'length': engine.streak_length(data.get('global_streaks', [])),
                    })
            event.update({
                'entry': serialize_note(note, entity.unit),
                'added_symbols': added_symbols,
                'project_key': self._game_project_key(project, entity),
                'project_progress': entity.progress,
                'entity_id': stage_id or project_id,
                'streak_events': streak_events,
            })
            return serialize_project(project)

        project_payload = self.repository.update_projects(mutate)
        game_result = None
        game_warning = None
        if self.game_service is not None and event.get('added_symbols'):
            try:
                game_result = self.game_service.record_project_progress(
                    added_symbols=event['added_symbols'],
                    project_key=event['project_key'],
                    project_progress=event['project_progress'],
                    streak_events=event['streak_events'],
                )
            except Exception as error:  # Progress is primary; never roll it back after save.
                game_warning = str(error)
        return {
            'project': project_payload,
            'entry': event['entry'],
            'added_symbols': event['added_symbols'],
            'game': game_result,
            'warning': game_warning,
        }

    @classmethod
    def _validated_source_modified_at(cls, value: Any) -> datetime:
        if not isinstance(value, datetime):
            raise ValidationError(
                'sync_source_timestamp_invalid',
                'Дата изменения источника синхронизации некорректна.',
            )
        normalized = cls._local_naive_datetime(value)
        if normalized > datetime.now():
            raise ValidationError(
                'sync_source_timestamp_invalid',
                'Дата изменения источника синхронизации некорректна.',
            )
        return normalized

    @staticmethod
    def _local_naive_datetime(value: datetime) -> datetime:
        if value.tzinfo is not None:
            return value.astimezone().replace(tzinfo=None)
        return value

    def delete_progress(
            self,
            project_id: str,
            entry_id: str,
            *,
            stage_id: str | None = None,
    ) -> dict[str, Any]:
        def mutate(data):
            project = self._find_project(data, project_id)
            entity = self._find_stage(project, stage_id) if stage_id else project
            self._require_editable(entity)
            note = next(
                (item for item in entity.notes if getattr(item, 'entry_id', None) == entry_id),
                None,
            )
            if note is None:
                raise NotFoundError('Запись прогресса не найдена.')
            entity.notes.remove(note)
            if entity.notes:
                entity.total_units = engine.unit_converter(
                    'symbols', entity.notes[-1].new_total, entity.unit,
                )
            else:
                entity.total_units = 0
            entity.edit_date = engine.today_for_test()
            entity.get_today_goal_value(recalculate_from_current_progress=True)
            project.edit_date = entity.edit_date
            return serialize_project(project)

        return self.repository.update_projects(mutate)

    def statistics(
            self, project_id: str, *, stage_id: str | None = None,
    ) -> dict[str, Any]:
        data = self.repository.read_projects()
        project = self._find_project(data, project_id)
        entity = self._find_stage(project, stage_id) if stage_id else project
        legacy = entity.get_statistic()
        symbols_by_day: dict[date, float] = defaultdict(float)
        for _stage_name, note in entity.get_notes_with_stage_names():
            symbols_by_day[note.get_date_create()] += note.get_added_symbols()
        best_day = max(symbols_by_day, key=symbols_by_day.get) if symbols_by_day else None
        symbols_by_weekday: dict[int, float] = defaultdict(float)
        for day, symbols in symbols_by_day.items():
            symbols_by_weekday[day.weekday()] += symbols
        best_weekday = (
            max(symbols_by_weekday, key=symbols_by_weekday.get)
            if symbols_by_weekday else None
        )
        active_days = int(legacy['Активных дней'])
        days_since_start = int(legacy['Дней с начала проекта'])
        return {
            'entity_id': stage_id or project_id,
            'unit': entity.unit,
            'metrics': {
                'entries_count': legacy['Кол-во записей'],
                'total': legacy['Всего написано в единице проекта'],
                'average_symbols_per_active_day': legacy['Среднее символов в день'],
                'average_symbols_per_entry': legacy['Среднее кол-во символов в записи'],
                'average_entries_per_active_day': legacy['Среднее кол-во записей в день'],
                'freezes_used': legacy['Использовано заморозок'],
                'best_day': (
                    {
                        'date': best_day.isoformat(),
                        'symbols': symbols_by_day[best_day],
                        'value': engine.unit_converter(
                            'symbols', symbols_by_day[best_day], entity.unit,
                        ),
                    }
                    if best_day is not None else None
                ),
                'best_weekday': (
                    {
                        'weekday': best_weekday,
                        'symbols': symbols_by_weekday[best_weekday],
                    }
                    if best_weekday is not None else None
                ),
                'current_streak': legacy['Текущий стрик (дней)'],
                'max_streak': legacy['Максимальный стрик'],
                'days_since_start': days_since_start,
                'active_days': active_days,
                'active_days_percent': round(
                    active_days / days_since_start * 100, 1,
                ) if days_since_start > 0 else 0,
            },
            'timeline': [
                {
                    'date': day.isoformat(),
                    'symbols': symbols,
                    'value': engine.unit_converter('symbols', symbols, entity.unit),
                }
                for day, symbols in sorted(symbols_by_day.items())
            ],
        }

    def today_summary(self) -> dict[str, Any]:
        """Return the legacy all-project daily total through the core.

        The Qt shell displays this total in symbols, including entries stored
        on stages. Keep that calculation in Python so the Vue workspace does
        not reconstruct writing-day rules from serialized notes.
        """
        data = self.repository.read_projects()
        today = engine.today_for_test()
        projects: list[dict[str, Any]] = []
        total_symbols = 0.0
        for project in data.get('projects', {}).values():
            symbols = float(project.get_added_symbols_today_value())
            total_symbols += symbols
            if not symbols:
                continue
            projects.append({
                'id': project.project_id,
                'name': project.name,
                'symbols': symbols,
                'unit': project.unit,
                'value': engine.unit_converter('symbols', symbols, project.unit),
            })
        return {
            'date': today.isoformat(),
            'symbols': total_symbols,
            'projects': projects,
        }

    def global_streak_summary(self) -> dict[str, Any]:
        """Expose the legacy global streak without duplicating its rules in Vue."""
        enabled = bool(self.repository.read_settings().get('global_streak', False))
        if not enabled:
            return {'enabled': False, 'status': 'Off', 'length': 0, 'max_length': 0}

        def summarize(data: dict[str, Any]) -> dict[str, Any]:
            self._refresh_streak_statuses(data)
            # global_streak_status preserves legacy day-boundary, recovery and
            # freeze rules. Running it inside update_projects routes its nested
            # legacy saves to this repository instead of the process default.
            status = engine.global_streak_status(data)
            length = engine.streak_length(data.get('global_streaks', []))
            return {
                'enabled': True,
                'status': str(status or 'No'),
                'length': length,
                'max_length': max(
                    int(data.get('max_global_streak', 0) or 0), length,
                ),
            }

        return self.repository.update_projects(summarize)

    @staticmethod
    def _refresh_streak_statuses(data: dict[str, Any]) -> None:
        """Advance missed local and global streak days exactly as legacy does."""
        engine.refresh_project_streak_statuses(data)
        engine.global_streak_status(data)

    def _read_projects_with_streak_refresh(self) -> dict[str, Any]:
        """Keep rendered project state in sync with automatic daily changes."""
        return self.repository.update_projects(
            lambda data: (self._refresh_streak_statuses(data), data)[1],
        )

    def _apply_daily_goal_streak_rules(
            self,
            data: dict[str, Any],
            entity: engine.Project,
            personal_goal: float,
            payload: dict[str, Any],
    ) -> None:
        """Preserve the legacy safeguards around an active daily streak."""
        old_goal = float(getattr(entity, 'personal_goal_for_the_day', 0) or 0)
        if math.isclose(personal_goal, old_goal, abs_tol=0.000001):
            return
        today = engine.today_for_test()
        streaks = getattr(entity, 'streaks', [])
        has_today_streak = engine.streak_contains_day(streaks, today)
        deadline_is_removed = 'deadline' in payload and payload['deadline'] is None

        if (
                personal_goal < old_goal
                and streaks
                and not has_today_streak
                and not deadline_is_removed
        ):
            raise ValidationError(
                'Нельзя уменьшить цель на день, пока не выполнена текущая.',
            )

        settings = self.repository.read_settings()
        requires_confirmation = (
            personal_goal > old_goal
            and bool(settings.get('global_streak', False))
        )
        if requires_confirmation and not payload.get('confirm_daily_goal_increase', False):
            raise ValidationError(
                'Вы хотите увеличить цель на день, уменьшить ее не выйдет, пока она не будет выполнена.\nПродолжить?',
            )
        if requires_confirmation and has_today_streak:
            engine.remove_streak_day(entity.streaks, today)

    @staticmethod
    def _find_project(data: dict[str, Any], project_id: str) -> engine.Project:
        for project in data.get('projects', {}).values():
            if getattr(project, 'project_id', None) == project_id:
                return project
        raise NotFoundError('Проект не найден.')

    @staticmethod
    def _find_stage(project: engine.Project, stage_id: str | None) -> engine.Stage:
        for stage in project.stages:
            if getattr(stage, 'stage_id', None) == stage_id:
                return stage
        raise NotFoundError('Этап не найден.')

    @staticmethod
    def _is_shared_project(project: engine.Project) -> bool:
        return not isinstance(project, engine.Stage) and project.name == 'Общий проект'

    @staticmethod
    def _require_editable(entity) -> None:
        if entity.status == 'завершен':
            raise ValidationError('Завершённая сущность доступна только для просмотра.')

    @staticmethod
    def _validated_name(value: Any) -> str:
        name = str(value or '').strip().replace('\x00', '')
        if not name:
            raise ValidationError('Введите название.')
        if len(name) > 300:
            raise ValidationError('Название слишком длинное.')
        return name

    @staticmethod
    def _validated_unit(value: Any) -> str:
        unit = str(value)
        if unit not in VALID_UNITS:
            raise ValidationError('Неизвестная единица измерения.')
        return unit

    @staticmethod
    def _number(value: Any, label: str) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ValidationError(f'{label} должно быть числом.') from None
        if not math.isfinite(number):
            raise ValidationError(f'{label} должно быть конечным числом.')
        return number

    @classmethod
    def _positive_number(cls, value: Any, label: str) -> float:
        number = cls._number(value, label)
        if number <= 0:
            raise ValidationError(f'{label} должно быть положительным числом.')
        return number

    @classmethod
    def _nonnegative_number(cls, value: Any, label: str) -> float:
        number = cls._number(value, label)
        if number < 0:
            raise ValidationError(f'{label} не может быть отрицательным.')
        return number

    @staticmethod
    def _round_for_unit(value: float, unit: str) -> float:
        if value == float('inf') or unit == 'author_list':
            return value
        return math.ceil(value)

    def _validated_deadline(self, value: Any):
        if value in (None, '', 'Нет'):
            return 'Нет'
        if isinstance(value, datetime):
            value = value.date()
        elif isinstance(value, str):
            try:
                value = date.fromisoformat(value)
            except ValueError:
                raise ValidationError('Дедлайн должен быть датой ISO 8601.') from None
        if not isinstance(value, date):
            raise ValidationError('Дедлайн должен быть датой ISO 8601.')
        with self.repository.storage_context():
            today = engine.today_for_test()
        if value < today:
            raise ValidationError('Дедлайн не может быть в прошлом.')
        return value

    def _new_stage(self, project: engine.Project, payload: dict[str, Any]) -> engine.Stage:
        name = self._validated_name(payload.get('name'))
        if any(stage.name == name for stage in project.stages):
            raise ConflictError('Этап с таким именем уже существует.')
        infinite = bool(payload.get('infinite', False))
        goal = (
            float('inf') if infinite
            else self._round_for_unit(
                self._positive_number(payload.get('goal'), 'Цель'), project.unit,
            )
        )
        total = self._round_for_unit(
            self._nonnegative_number(payload.get('total', 0), 'Текущее значение'),
            project.unit,
        )
        if not infinite:
            self._ensure_convertible(goal, project.unit, 'Цель')
        self._ensure_convertible(total, project.unit, 'Текущее значение')
        personal_goal = self._nonnegative_number(
            payload.get('personal_goal', 0), 'Цель на день',
        )
        self._ensure_convertible(personal_goal, project.unit, 'Цель на день')
        stage = engine.Stage(
            name=name,
            goal=goal,
            deadline=self._validated_deadline(payload.get('deadline')),
            total_symbols=total,
            unit=project.unit,
            personal_goal_for_the_day=personal_goal,
            parent_project_name=project.name,
            auto_freeze=bool(payload.get('auto_freeze', True)),
        )
        stage.set_streak_state(bool(payload.get('streak_enabled', False)))
        stage.get_today_goal_value()
        return stage

    @staticmethod
    def _convert_entity_unit(entity, old_unit: str, new_unit: str) -> None:
        if entity.has_stages():
            for stage in entity.stages:
                ProjectService._convert_entity_unit(stage, stage.unit, new_unit)
        else:
            converted_goal = engine.unit_converter(old_unit, entity.goal, new_unit)
            converted_total = engine.unit_converter(
                old_unit, entity.total_units, new_unit,
            )
            if converted_goal != float('inf'):
                ProjectService._ensure_convertible(
                    converted_goal, new_unit, 'Цель',
                )
            ProjectService._ensure_convertible(
                converted_total, new_unit, 'Текущее значение',
            )
            entity.goal = converted_goal
            entity.total_units = converted_total
            entity.unit = new_unit
        personal_goal = engine.unit_converter(
            old_unit,
            getattr(entity, 'personal_goal_for_the_day', 0),
            new_unit,
        )
        ProjectService._ensure_convertible(
            personal_goal, new_unit, 'Цель на день',
        )
        entity.personal_goal_for_the_day = personal_goal

    @staticmethod
    def _ensure_convertible(value: float, unit: str, label: str) -> None:
        try:
            symbols = engine.unit_converter(unit, value, 'symbols')
            finite = math.isfinite(float(symbols))
        except (OverflowError, TypeError, ValueError):
            finite = False
        if not finite:
            raise ValidationError(f'{label} слишком велико.')

    @staticmethod
    def _serialize_stage_with_parent(project, stage) -> dict[str, Any]:
        payload = serialize_project(stage)
        payload['parent_project_id'] = project.project_id
        return payload

    @staticmethod
    def _game_project_key(project, entity) -> str:
        if entity is project:
            return f'project:{project.project_id}'
        return f'stage:{project.project_id}:{entity.stage_id}'

    @classmethod
    def _completion_event(
            cls,
            project: engine.Project,
            entity: engine.Project,
            *,
            include_streak: bool,
    ) -> dict[str, Any]:
        streak_length = engine.streak_length(entity.streaks)
        return {
            'key': cls._game_project_key(project, entity),
            'streak_status': (
                'Complete'
                if include_streak and entity.deadline != 'Нет' and streak_length
                else ''
            ),
            'streak_length': streak_length,
        }

    @staticmethod
    def _date_ordinal(value: Any) -> int:
        if isinstance(value, datetime):
            return value.date().toordinal()
        if isinstance(value, date):
            return value.toordinal()
        return 0


__all__ = ['ProjectService', 'VALID_STATUSES', 'VALID_UNITS']
