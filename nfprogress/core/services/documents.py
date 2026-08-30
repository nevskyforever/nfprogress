"""Rich project documents stored independently from legacy progress pickles."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nfprogress.core.errors import NotFoundError, ValidationError
import engine


EMPTY_DOCUMENT = {'type': 'doc', 'content': [{'type': 'paragraph'}]}


class ProjectDocumentService:
    """Persist Tiptap JSON and mediate binary DOCX links on desktop.

    DOCX conversion intentionally remains in the TypeScript client.  The sidecar
    only owns local paths and bytes, exactly as the existing integration service.
    """

    def __init__(self, repository, project_service, *, allow_local_files: bool) -> None:
        self.repository = repository
        self.project_service = project_service
        self.allow_local_files = allow_local_files

    def get(self, project_id: str, stage_id: str | None = None) -> dict[str, Any]:
        key = self._key(project_id, stage_id)
        with self.repository.locked():
            self._validate_document_owner(project_id, stage_id)
            return self._public(self._load().get(key) or self._new(project_id, stage_id))

    def list_existing(self) -> list[dict[str, Any]]:
        with self.repository.locked():
            records = self._load().values()
            visible = []
            for record in records:
                if not record.get('exists'):
                    continue
                try:
                    self._validate_document_owner(record['project_id'], record.get('stage_id'))
                except NotFoundError:
                    continue
                visible.append(self._public(record))
            return visible

    def save(self, project_id: str, content: dict[str, Any], stage_id: str | None = None) -> dict[str, Any]:
        if not isinstance(content, dict) or content.get('type') != 'doc':
            raise ValidationError('Документ должен быть в формате Tiptap JSON.')
        key = self._key(project_id, stage_id)
        with self.repository.locked():
            self._validate_document_owner(project_id, stage_id)
            records = self._load()
            record = records.get(key) or self._new(project_id, stage_id)
            record.update({'content': content, 'exists': True, 'updated_at': self._now(), 'local_dirty': True})
            records[key] = record
            self._write(records)
            return self._public(record)

    def link(self, project_id: str, path: str, stage_id: str | None = None) -> dict[str, Any]:
        if not self.allow_local_files:
            raise ValidationError('Связь с локальным Word-файлом доступна только в desktop-приложении.')
        source = Path(path).expanduser().resolve()
        if source.suffix.lower() != '.docx':
            raise ValidationError('Поддерживаются только документы Word .docx.')
        key = self._key(project_id, stage_id)
        with self.repository.locked():
            self._validate_document_owner(project_id, stage_id)
            records = self._load()
            record = records.get(key) or self._new(project_id, stage_id)
            record.update({'docx_path': str(source), 'exists': True, 'updated_at': self._now(), 'local_dirty': True})
            records[key] = record
            self._write(records)
            return self._public(record)

    def write_docx(self, project_id: str, payload: str, stage_id: str | None = None) -> dict[str, Any]:
        key = self._key(project_id, stage_id)
        try:
            raw = base64.b64decode(payload, validate=True)
        except (ValueError, TypeError) as error:
            raise ValidationError('Некорректные данные DOCX.') from error
        with self.repository.locked():
            self._validate_document_owner(project_id, stage_id)
            records = self._load(); record = records.get(key)
            if not record or not record.get('docx_path'):
                raise ValidationError('Сначала свяжите документ с файлом Word.')
            path = Path(record['docx_path'])
            path.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary = tempfile.mkstemp(prefix='.nfprogress-', suffix='.docx', dir=path.parent)
            try:
                with os.fdopen(descriptor, 'wb') as stream:
                    stream.write(raw); stream.flush(); os.fsync(stream.fileno())
                os.replace(temporary, path)
            finally:
                if os.path.exists(temporary): os.unlink(temporary)
            record.update({'last_synced_hash': self._hash(raw), 'last_synced_at': self._now(), 'local_dirty': False, 'word_dirty': False, 'sync_state': 'synced'})
            records[key] = record; self._write(records)
            return self._public(record)

    def read_external_docx(self, project_id: str, stage_id: str | None = None) -> dict[str, Any]:
        key = self._key(project_id, stage_id)
        with self.repository.locked():
            self._validate_document_owner(project_id, stage_id)
            records = self._load(); record = records.get(key)
            if not record or not record.get('docx_path'): return {'state': 'unlinked'}
            path = Path(record['docx_path'])
            if not path.is_file(): return {'state': 'missing'}
            raw = path.read_bytes(); digest = self._hash(raw)
            if digest == record.get('last_synced_hash'): return {'state': 'synced'}
            state = 'conflict' if record.get('local_dirty') else 'word_changed'
            record.update({'word_dirty': True, 'sync_state': state})
            records[key] = record; self._write(records)
            return {'state': state, 'content_base64': base64.b64encode(raw).decode('ascii'), 'hash': digest}

    def accept_word(self, project_id: str, content: dict[str, Any], source_hash: str, stage_id: str | None = None) -> dict[str, Any]:
        key = self._key(project_id, stage_id)
        with self.repository.locked():
            self._validate_document_owner(project_id, stage_id)
            records = self._load(); record = records.get(key) or self._new(project_id, stage_id)
            record.update({'content': content, 'exists': True, 'updated_at': self._now(), 'last_synced_hash': source_hash, 'last_synced_at': self._now(), 'local_dirty': False, 'word_dirty': False, 'sync_state': 'synced'})
            records[key] = record; self._write(records)
            return self._public(record)

    def record_text_progress(
            self, project_id: str, stage_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a normal synchronized progress entry from the internal text."""
        key = self._key(project_id, stage_id)
        with self.repository.locked():
            self._validate_document_owner(project_id, stage_id)
            record = self._load().get(key)
            symbols = self._symbol_count(record.get('content', {})) if record else 0
            if symbols <= 0:
                raise ValidationError('Сначала добавьте текст в документ.')
            data = self.repository.read_projects()
            project = self.project_service._find_project(data, project_id)
            entity = self.project_service._find_stage(project, stage_id) if stage_id else project
            total = engine.unit_converter('symbols', symbols, entity.unit)
            if abs(float(total) - float(entity.total_units)) < 0.009:
                return {'changed': False, 'symbols': symbols, 'progress': None}
            changed_at = self._parse_updated_at(record.get('updated_at'))
            progress = self.project_service.record_synchronized_progress(
                project_id, stage_id=stage_id, new_total=total,
                source_modified_at=changed_at,
            )
            return {'changed': True, 'symbols': symbols, 'progress': progress}

    def ensure_external_sync_can_be_configured(
            self, project_id: str, stage_id: str | None = None,
    ) -> None:
        """Keep file synchronization and an internal manuscript mutually exclusive."""
        key = self._key(project_id, stage_id)
        with self.repository.locked():
            record = self._load().get(key)
            if record and self._symbol_count(record.get('content', {})) > 0:
                raise ValidationError(
                    'Сначала очистите текст документа или используйте «Добавить запись».',
                )

    def _validate_owner(self, project_id: str, stage_id: str | None) -> None:
        data = self.repository.read_projects()
        project = self.project_service._find_project(data, project_id)
        if stage_id: self.project_service._find_stage(project, stage_id)

    def _validate_document_owner(self, project_id: str, stage_id: str | None) -> None:
        data = self.repository.read_projects()
        project = self.project_service._find_project(data, project_id)
        entity = self.project_service._find_stage(project, stage_id) if stage_id else project
        if stage_id is None and getattr(project, 'stages', []):
            raise ValidationError('У проекта с этапами нет отдельного текста.')
        if getattr(entity, 'synch', None) is not None:
            raise ValidationError('У синхронизируемого проекта или этапа нет отдельного текста.')

    @staticmethod
    def _symbol_count(value: object) -> int:
        if isinstance(value, dict):
            return len(str(value.get('text', ''))) + sum(
                ProjectDocumentService._symbol_count(item)
                for item in value.get('content', [])
                if isinstance(item, dict)
            )
        return 0

    @staticmethod
    def _parse_updated_at(value: object) -> datetime:
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value)
                return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
            except ValueError:
                pass
        return datetime.now()

    @staticmethod
    def _key(project_id: str, stage_id: str | None) -> str: return f'{project_id}:{stage_id or "project"}'
    @staticmethod
    def _now() -> str: return datetime.now(timezone.utc).isoformat()
    @staticmethod
    def _hash(raw: bytes) -> str: return hashlib.sha256(raw).hexdigest()
    @staticmethod
    def _new(project_id: str, stage_id: str | None) -> dict[str, Any]:
        return {'project_id': project_id, 'stage_id': stage_id, 'content': EMPTY_DOCUMENT, 'exists': False, 'updated_at': None, 'docx_path': None, 'sync_state': 'unlinked', 'last_synced_hash': None, 'last_synced_at': None, 'local_dirty': False, 'word_dirty': False}
    @classmethod
    def _public(cls, record: dict[str, Any]) -> dict[str, Any]:
        result = dict(record)
        result['symbols'] = cls._symbol_count(result.get('content', {}))
        result['has_content'] = result['symbols'] > 0
        return result
    def _path(self) -> Path: return self.repository.base_dir / 'documents.json'
    def _load(self) -> dict[str, dict[str, Any]]:
        path = self._path()
        if not path.exists(): return {}
        try:
            value = json.loads(path.read_text(encoding='utf-8'))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError): return {}
    def _write(self, records: dict[str, dict[str, Any]]) -> None:
        path = self._path(); descriptor, temporary = tempfile.mkstemp(prefix='.documents-', suffix='.json', dir=path.parent)
        try:
            with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
                json.dump(records, stream, ensure_ascii=False); stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary): os.unlink(temporary)
