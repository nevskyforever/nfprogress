"""Explicit Word and Scrivener integration workflows without Qt file dialogs."""

from __future__ import annotations

import math
import os
import tempfile
import zipfile
from contextlib import nullcontext
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import engine
from scrivener_parser import (
    find_scrivener_item_files,
    find_scrivener_xml,
    parse_scrivener_items,
    read_symbols_from_scrivener_item,
)

from nfprogress.core.errors import (
    ConflictError,
    DomainError,
    NotFoundError,
    ValidationError,
)


@dataclass(frozen=True, slots=True)
class _SyncSourceSnapshot:
    symbols: int
    modified_at: datetime


class DocumentIntegrationService:
    """Read only files selected by a client and route totals through progress."""

    def __init__(self, repository, project_service, *, allow_local_files: bool = False):
        self.repository = repository
        self.project_service = project_service
        self.allow_local_files = bool(allow_local_files)

    def configure_sync(
            self,
            project_id: str,
            *,
            sync_type: str,
            path: str,
            stage_id: str | None = None,
            item_id: str | None = None,
    ) -> dict[str, Any]:
        self._require_local_files()
        source = self._validate_source(sync_type, path, item_id=item_id)

        def mutate(data):
            project = self.project_service._find_project(data, project_id)
            entity = (
                self.project_service._find_stage(project, stage_id)
                if stage_id else project
            )
            if entity.status == 'завершен':
                raise ValidationError('Завершённая сущность доступна только для просмотра.')
            entity.synch = source
            entity.last_synch = None
            return self._sync_summary(project_id, stage_id, entity)

        return self.repository.update_projects(mutate)

    def remove_sync(
            self, project_id: str, *, stage_id: str | None = None,
    ) -> dict[str, Any]:
        self._require_local_files()

        def mutate(data):
            project = self.project_service._find_project(data, project_id)
            entity = (
                self.project_service._find_stage(project, stage_id)
                if stage_id else project
            )
            entity.synch = None
            entity.last_synch = None
            return self._sync_summary(project_id, stage_id, entity)

        return self.repository.update_projects(mutate)

    def remove_all_syncs(self, project_id: str) -> dict[str, Any]:
        """Atomically detach the project and every stage from local sources."""
        self._require_local_files()

        def mutate(data):
            project = self.project_service._find_project(data, project_id)
            entities = [project, *getattr(project, 'stages', [])]
            removed = sum(
                getattr(entity, 'synch', None) is not None
                for entity in entities
            )
            for entity in entities:
                entity.synch = None
                entity.last_synch = None
            return {
                'project_id': project_id,
                'removed': removed,
                'syncs': [
                    self._sync_summary(
                        project_id,
                        (
                            str(entity.stage_id)
                            if getattr(entity, 'is_stage', False) else None
                        ),
                        entity,
                    )
                    for entity in entities
                ],
            }

        return self.repository.update_projects(mutate)

    def get_sync(
            self, project_id: str, *, stage_id: str | None = None,
    ) -> dict[str, Any]:
        data = self.repository.read_projects()
        project = self.project_service._find_project(data, project_id)
        entity = self.project_service._find_stage(project, stage_id) if stage_id else project
        summary = self._sync_summary(project_id, stage_id, entity)
        if not self.allow_local_files:
            summary['path'] = None
        return summary

    def run_sync(
            self, project_id: str, *, stage_id: str | None = None,
    ) -> dict[str, Any]:
        self._require_local_files()
        locked = getattr(self.repository, 'locked', None)
        transaction = locked() if callable(locked) else nullcontext()
        with transaction:
            data = self.repository.read_projects()
            project = self.project_service._find_project(data, project_id)
            entity = (
                self.project_service._find_stage(project, stage_id)
                if stage_id else project
            )
            source = getattr(entity, 'synch', None)
            if isinstance(source, str):
                source = {'type': 'word', 'path': source}
            if not isinstance(source, dict):
                raise ValidationError('Синхронизация не настроена.')

            snapshot = self._read_source(source)
            total = self._normalized_total(entity, snapshot.symbols)
            if self._totals_match(total, entity.total_units):
                return {
                    'changed': False,
                    'symbols': snapshot.symbols,
                    'sync': self._mark_synced(project_id, stage_id),
                    'progress': None,
                }

            last_synced_at = getattr(entity, 'last_synch', None)
            if (
                    isinstance(last_synced_at, datetime)
                    and snapshot.modified_at
                    <= self._local_naive_datetime(last_synced_at)
            ):
                raise ConflictError(
                    'sync_source_stale',
                    'Источник синхронизации устарел и не будет применён.',
                )
            progress = self.project_service.record_synchronized_progress(
                project_id,
                stage_id=stage_id,
                new_total=total,
                source_modified_at=snapshot.modified_at,
            )
            return {
                'changed': True,
                'symbols': snapshot.symbols,
                'sync': self._mark_synced(project_id, stage_id),
                'progress': progress,
            }

    def sync_all_configured(self) -> dict[str, Any]:
        """Synchronize every active desktop source without stopping on one failure."""
        self._require_local_files()
        data = self.repository.read_projects()
        targets: list[tuple[str, str | None]] = []
        projects = data.get('projects', {})
        if isinstance(projects, dict):
            for project in projects.values():
                project_id = getattr(project, 'project_id', None)
                if not project_id:
                    continue
                if getattr(project, 'has_stages', lambda: False)():
                    targets.extend(
                        (str(project_id), str(stage.stage_id))
                        for stage in getattr(project, 'stages', [])
                        if (
                            getattr(stage, 'stage_id', None)
                            and getattr(stage, 'status', None) == 'активен'
                            and getattr(stage, 'synch', None) is not None
                        )
                    )
                elif (
                        getattr(project, 'status', None) == 'активен'
                        and getattr(project, 'synch', None) is not None
                ):
                    targets.append((str(project_id), None))

        items: list[dict[str, Any]] = []
        changed_count = 0
        for project_id, stage_id in targets:
            try:
                result = self.run_sync(project_id, stage_id=stage_id)
            except DomainError as error:
                items.append({
                    'project_id': project_id,
                    'stage_id': stage_id,
                    'ok': False,
                    'changed': False,
                    'symbols': None,
                    'error': error.as_dict(),
                })
                continue
            except Exception:
                items.append({
                    'project_id': project_id,
                    'stage_id': stage_id,
                    'ok': False,
                    'changed': False,
                    'symbols': None,
                    'error': {
                        'code': 'sync_failed',
                        'message': 'Не удалось прочитать источник синхронизации.',
                    },
                })
                continue
            changed = bool(result['changed'])
            changed_count += int(changed)
            items.append({
                'project_id': project_id,
                'stage_id': stage_id,
                'ok': True,
                'changed': changed,
                'symbols': int(result['symbols']),
                'error': None,
            })
        return {
            'checked': len(targets),
            'changed': changed_count,
            'failed': sum(not item['ok'] for item in items),
            'items': items,
        }

    def inspect_scrivener(self, path: str) -> list[dict[str, Any]]:
        self._require_local_files()
        project_path = Path(path).expanduser().resolve()
        items = self._load_scrivener_items(project_path)
        return [self._scrivener_item(item) for item in items]

    @classmethod
    def _scrivener_item(cls, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValidationError('Структура проекта Scrivener повреждена.')
        item_id = value.get('id')
        title = value.get('title')
        children = value.get('children', [])
        if not item_id or not isinstance(children, list):
            raise ValidationError('Структура проекта Scrivener повреждена.')
        return {
            'id': str(item_id),
            'title': str(title or 'Без названия'),
            'children': [cls._scrivener_item(child) for child in children],
        }

    @staticmethod
    def _load_scrivener_items(project_path: Path) -> list[dict[str, Any]]:
        try:
            xml_path = find_scrivener_xml(str(project_path))
            if not xml_path:
                raise ValidationError('Не найден файл проекта Scrivener.')
            items = parse_scrivener_items(xml_path)
        except ValidationError:
            raise
        except (OSError, SyntaxError, ValueError) as error:
            raise ValidationError('Не удалось прочитать проект Scrivener.') from error
        if not isinstance(items, list):
            raise ValidationError('Структура проекта Scrivener повреждена.')
        return items

    @classmethod
    def _has_scrivener_item(cls, items: list[Any], item_id: str) -> bool:
        expected = item_id.strip('{}').lower()
        for item in items:
            if not isinstance(item, dict):
                continue
            current = str(item.get('id', '')).strip('{}').lower()
            if current == expected:
                return True
            children = item.get('children', [])
            if isinstance(children, list) and cls._has_scrivener_item(
                    children, item_id,
            ):
                return True
        return False

    @staticmethod
    def count_uploaded_docx(content: bytes, filename: str) -> int:
        if Path(filename).suffix.lower() != '.docx':
            raise ValidationError('Поддерживаются только документы .docx.')
        if not content:
            raise ValidationError('Документ пуст.')
        if len(content) > 100 * 1024 * 1024:
            raise ValidationError('Документ превышает допустимый размер 100 МБ.')
        try:
            with zipfile.ZipFile(BytesIO(content)) as archive:
                entries = archive.infolist()
                expanded_size = sum(entry.file_size for entry in entries)
        except (zipfile.BadZipFile, OSError):
            raise ValidationError('Документ .docx повреждён.') from None
        if len(entries) > 10_000 or expanded_size > 250 * 1024 * 1024:
            raise ValidationError('Распакованный документ слишком велик.')
        descriptor, temporary_path = tempfile.mkstemp(suffix='.docx')
        try:
            with os.fdopen(descriptor, 'wb') as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            return engine.count_symbols_in_docx(temporary_path)
        except Exception as error:
            if isinstance(error, ValidationError):
                raise
            raise ValidationError('Не удалось прочитать документ .docx.') from error
        finally:
            Path(temporary_path).unlink(missing_ok=True)

    def apply_uploaded_docx(
            self,
            project_id: str,
            content: bytes,
            filename: str,
            *,
            stage_id: str | None = None,
    ) -> dict[str, Any]:
        """Apply an explicitly uploaded document through normal progress rules."""
        symbols = self.count_uploaded_docx(content, filename)
        locked = getattr(self.repository, 'locked', None)
        transaction = locked() if callable(locked) else nullcontext()
        with transaction:
            data = self.repository.read_projects()
            project = self.project_service._find_project(data, project_id)
            entity = (
                self.project_service._find_stage(project, stage_id)
                if stage_id else project
            )
            self.project_service._require_editable(entity)
            if entity.has_stages():
                raise ValidationError('Записывайте прогресс в конкретный этап.')
            total = self._normalized_total(entity, symbols)
            if not self._totals_match(total, entity.total_units):
                progress = self.project_service.record_progress(
                    project_id, stage_id=stage_id, new_total=total,
                )
                return {
                    'changed': True,
                    'symbols': symbols,
                    'project': progress['project'],
                    'progress': progress,
                }
            return {
                'changed': False,
                'symbols': symbols,
                'project': self.project_service.get_project(project_id),
                'progress': None,
            }

    def _mark_synced(self, project_id: str, stage_id: str | None) -> dict[str, Any]:
        def mutate(data):
            project = self.project_service._find_project(data, project_id)
            entity = (
                self.project_service._find_stage(project, stage_id)
                if stage_id else project
            )
            entity.last_synch = datetime.now()
            return self._sync_summary(project_id, stage_id, entity)

        return self.repository.update_projects(mutate)

    @staticmethod
    def _sync_summary(project_id: str, stage_id: str | None, entity) -> dict[str, Any]:
        source = getattr(entity, 'synch', None)
        if isinstance(source, str):
            source = {'type': 'word', 'path': source}
        return {
            'project_id': project_id,
            'stage_id': stage_id,
            'configured': isinstance(source, dict),
            'type': source.get('type') if isinstance(source, dict) else None,
            'path': source.get('path') if isinstance(source, dict) else None,
            'item_id': source.get('item_id') if isinstance(source, dict) else None,
            'last_synced_at': (
                entity.last_synch.isoformat()
                if isinstance(getattr(entity, 'last_synch', None), datetime)
                else None
            ),
            'desktop_only': True,
        }

    def _validate_source(
            self, sync_type: str, path: str, *, item_id: str | None,
    ) -> dict[str, str]:
        source_path = Path(path).expanduser().resolve()
        if sync_type == 'word':
            if source_path.suffix.lower() != '.docx':
                raise ValidationError('Поддерживаются только документы Word .docx.')
            if not source_path.is_file():
                raise NotFoundError('Документ Word не найден.')
            return {'type': 'word', 'path': str(source_path)}
        if sync_type == 'scrivener':
            if not source_path.exists():
                raise NotFoundError('Проект Scrivener не найден.')
            if not item_id:
                raise ValidationError('Выберите документ Scrivener.')
            items = self._load_scrivener_items(source_path)
            if not self._has_scrivener_item(items, item_id):
                raise ValidationError('Документ Scrivener не найден в проекте.')
            return {
                'type': 'scrivener',
                'path': str(source_path),
                'item_id': str(item_id),
            }
        raise ValidationError('Неизвестный тип синхронизации.')

    def _read_source(self, source: dict[str, Any]) -> _SyncSourceSnapshot:
        path = source.get('path')
        if not isinstance(path, str):
            raise NotFoundError(
                'sync_source_missing', 'Источник синхронизации не найден.',
            )
        source_path = Path(path)
        if not source_path.exists():
            raise NotFoundError(
                'sync_source_missing', 'Источник синхронизации не найден.',
            )
        if source.get('type') == 'word':
            if source_path.suffix.lower() != '.docx':
                raise ValidationError('Поддерживаются только документы Word .docx.')
            if not source_path.is_file():
                raise NotFoundError(
                    'sync_source_missing', 'Источник синхронизации не найден.',
                )
            before = self._source_stat(source_path)
            try:
                symbols = engine.count_symbols_in_docx(str(source_path))
            except Exception as error:
                raise ValidationError(
                    'sync_source_unreadable',
                    'Не удалось прочитать источник синхронизации.',
                ) from error
            after = self._source_stat(source_path)
            self._ensure_stable_source((before,), (after,))
            return _SyncSourceSnapshot(
                symbols=self._validated_symbols(symbols),
                modified_at=self._source_modified_at(before),
            )
        if source.get('type') == 'scrivener':
            item_id = source.get('item_id')
            if not item_id:
                raise ValidationError('Не выбран документ Scrivener.')
            try:
                xml_path_value = find_scrivener_xml(str(source_path))
            except OSError as error:
                raise ValidationError(
                    'sync_source_unreadable',
                    'Не удалось прочитать источник синхронизации.',
                ) from error
            if not xml_path_value:
                raise ConflictError(
                    'sync_source_stale',
                    'Источник синхронизации устарел и не будет применён.',
                )
            xml_path = Path(xml_path_value)
            items = self._load_scrivener_items(source_path)
            if not self._has_scrivener_item(items, str(item_id)):
                raise ConflictError(
                    'sync_source_stale',
                    'Источник синхронизации устарел и не будет применён.',
                )
            try:
                content_paths = find_scrivener_item_files(
                    source_path, str(item_id),
                )
            except OSError as error:
                raise ValidationError(
                    'sync_source_unreadable',
                    'Не удалось прочитать источник синхронизации.',
                ) from error
            if not content_paths:
                raise ConflictError(
                    'sync_source_stale',
                    'Источник синхронизации устарел и не будет применён.',
                )
            observed_paths = (xml_path, *content_paths)
            before = tuple(self._source_stat(item) for item in observed_paths)
            try:
                symbols = read_symbols_from_scrivener_item(
                    str(source_path), str(item_id),
                )
            except FileNotFoundError as error:
                raise ConflictError(
                    'sync_source_stale',
                    'Источник синхронизации устарел и не будет применён.',
                ) from error
            except (OSError, ValueError) as error:
                raise ValidationError(
                    'sync_source_unreadable',
                    'Не удалось прочитать источник синхронизации.',
                ) from error
            after = tuple(self._source_stat(item) for item in observed_paths)
            self._ensure_stable_source(before, after)
            modified_at = max(
                self._source_modified_at(item) for item in before
            )
            return _SyncSourceSnapshot(
                symbols=self._validated_symbols(symbols),
                modified_at=modified_at,
            )
        raise ValidationError('Неизвестный тип синхронизации.')

    def _normalized_total(self, entity, symbols: int) -> float:
        total = self.project_service._round_for_unit(
            engine.unit_converter('symbols', symbols, entity.unit),
            entity.unit,
        )
        self.project_service._ensure_convertible(
            total, entity.unit, 'Новое общее значение',
        )
        return total

    @staticmethod
    def _totals_match(first: float, second: float) -> bool:
        return math.isclose(float(first), float(second), abs_tol=0.009)

    @staticmethod
    def _source_stat(path: Path):
        try:
            return path.stat()
        except FileNotFoundError:
            raise NotFoundError(
                'sync_source_missing', 'Источник синхронизации не найден.',
            ) from None
        except OSError as error:
            raise ValidationError(
                'sync_source_unreadable',
                'Не удалось прочитать источник синхронизации.',
            ) from error

    @staticmethod
    def _ensure_stable_source(before: tuple[Any, ...], after: tuple[Any, ...]) -> None:
        before_signature = [
            (item.st_mtime_ns, item.st_size) for item in before
        ]
        after_signature = [
            (item.st_mtime_ns, item.st_size) for item in after
        ]
        if before_signature != after_signature:
            raise ConflictError(
                'sync_source_changed_during_read',
                'Источник синхронизации изменился во время чтения.',
            )

    @staticmethod
    def _source_modified_at(stat_result) -> datetime:
        try:
            value = datetime.fromtimestamp(stat_result.st_mtime)
        except (OSError, OverflowError, ValueError):
            raise ValidationError(
                'sync_source_timestamp_invalid',
                'Дата изменения источника синхронизации некорректна.',
            ) from None
        if value > datetime.now():
            raise ValidationError(
                'sync_source_timestamp_invalid',
                'Дата изменения источника синхронизации некорректна.',
            )
        return value

    @staticmethod
    def _validated_symbols(value: Any) -> int:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValidationError(
                'sync_source_unreadable',
                'Не удалось прочитать источник синхронизации.',
            )
        numeric = float(value)
        if not math.isfinite(numeric) or numeric < 0 or not numeric.is_integer():
            raise ValidationError(
                'sync_source_unreadable',
                'Не удалось прочитать источник синхронизации.',
            )
        return int(numeric)

    @staticmethod
    def _local_naive_datetime(value: datetime) -> datetime:
        if value.tzinfo is not None:
            return value.astimezone().replace(tzinfo=None)
        return value

    def _require_local_files(self) -> None:
        if not self.allow_local_files:
            raise ValidationError(
                'Прямой доступ к локальным файлам доступен только в desktop-приложении.',
            )


__all__ = ['DocumentIntegrationService']
