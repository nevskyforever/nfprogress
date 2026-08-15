"""Explicit Word and Scrivener integration workflows without Qt file dialogs."""

from __future__ import annotations

import os
import tempfile
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import engine
from scrivener_parser import (
    count_symbols_in_scrivener_item,
    find_scrivener_xml,
    parse_scrivener_items,
)

from nfprogress.core.errors import NotFoundError, ValidationError


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
        data = self.repository.read_projects()
        project = self.project_service._find_project(data, project_id)
        entity = self.project_service._find_stage(project, stage_id) if stage_id else project
        source = getattr(entity, 'synch', None)
        if isinstance(source, str):
            source = {'type': 'word', 'path': source}
        if not isinstance(source, dict):
            raise ValidationError('Синхронизация не настроена.')

        symbols = self._read_source(source)
        total = engine.unit_converter('symbols', symbols, entity.unit)
        if total == entity.total_units:
            return {
                'changed': False,
                'symbols': symbols,
                'sync': self._mark_synced(project_id, stage_id),
                'progress': None,
            }
        progress = self.project_service.record_progress(
            project_id, stage_id=stage_id, new_total=total,
        )
        return {
            'changed': True,
            'symbols': symbols,
            'sync': self._mark_synced(project_id, stage_id),
            'progress': progress,
        }

    def inspect_scrivener(self, path: str) -> list[dict[str, str]]:
        self._require_local_files()
        project_path = Path(path).expanduser().resolve()
        xml_path = find_scrivener_xml(str(project_path))
        if not xml_path:
            raise ValidationError('Не найден файл проекта Scrivener.')
        items = parse_scrivener_items(xml_path)
        return [
            {'id': str(item_id), 'title': str(title)}
            for item_id, title in items
        ]

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
            if find_scrivener_xml(str(source_path)) is None:
                raise ValidationError('Не найден файл проекта Scrivener.')
            return {
                'type': 'scrivener',
                'path': str(source_path),
                'item_id': str(item_id),
            }
        raise ValidationError('Неизвестный тип синхронизации.')

    @staticmethod
    def _read_source(source: dict[str, Any]) -> int:
        path = source.get('path')
        if not isinstance(path, str) or not Path(path).exists():
            raise NotFoundError('Источник синхронизации не найден.')
        if source.get('type') == 'word':
            if Path(path).suffix.lower() != '.docx':
                raise ValidationError('Поддерживаются только документы Word .docx.')
            return engine.count_symbols_in_docx(path)
        if source.get('type') == 'scrivener':
            item_id = source.get('item_id')
            if not item_id:
                raise ValidationError('Не выбран документ Scrivener.')
            return count_symbols_in_scrivener_item(path, item_id)
        raise ValidationError('Неизвестный тип синхронизации.')

    def _require_local_files(self) -> None:
        if not self.allow_local_files:
            raise ValidationError(
                'Прямой доступ к локальным файлам доступен только в desktop-приложении.',
            )


__all__ = ['DocumentIntegrationService']
