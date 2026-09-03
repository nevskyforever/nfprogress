"""Authoritative SQLite storage and controlled cutover for project notes."""

from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import engine

from nfprogress.core.errors import ConflictError, NotFoundError
from nfprogress.core.sqlite.connection import open_database
from nfprogress.core.sqlite.ownership import StorageOwner, StorageOwnershipRepository, Subsystem
from nfprogress.core.sqlite.repository import _json


NOTE_FIELDS = frozenset({
    'id', 'project_id', 'stage_id', 'title', 'content', 'content_format',
    'checklist', 'color', 'pinned', 'archived', 'sort_order', 'tags',
    'source_type', 'source_map_id', 'source_node_id', 'created_at',
    'updated_at', 'revision', 'metadata',
})


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _json_object(value: str) -> dict[str, Any]:
    decoded = json.loads(value)
    if not isinstance(decoded, dict):
        raise ValueError('note payload must be an object')
    return decoded


def _metadata(raw: Mapping[str, Any]) -> dict[str, Any]:
    existing = raw.get('metadata')
    result = deepcopy(existing) if isinstance(existing, dict) else {}
    for key, value in raw.items():
        if key not in NOTE_FIELDS:
            result[str(key)] = deepcopy(value)
    return result


def _canonical_record(
        raw: object,
        *,
        project_id: str,
        stage_id: str | None,
        fallback_index: int = 0,
        map_text: str | None = None,
) -> dict[str, Any] | None:
    if not isinstance(raw, Mapping):
        return None
    source_type = raw.get('source_type', 'project')
    if source_type not in {'project', 'mindmap'}:
        source_type = 'project'
    source_node_id = raw.get('source_node_id')
    source_map_id = raw.get('source_map_id')
    if source_type == 'mindmap' and (not isinstance(source_node_id, str) or not source_node_id):
        return None
    if source_type != 'mindmap':
        source_node_id = None
        source_map_id = None
    elif not isinstance(source_map_id, str) or not source_map_id:
        source_map_id = None

    note_id = raw.get('id')
    if not isinstance(note_id, str) or not note_id:
        seed = _json({
            'project_id': project_id,
            'stage_id': stage_id,
            'index': fallback_index,
            'source_type': source_type,
            'source_node_id': source_node_id,
            'title': raw.get('title', ''),
            'content': raw.get('content', ''),
            'created_at': raw.get('created_at', ''),
        })
        note_id = uuid.uuid5(uuid.NAMESPACE_URL, f'nfprogress-note:{seed}').hex

    title = raw.get('title', '')
    content = raw.get('content', '')
    created_at = raw.get('created_at', '')
    updated_at = raw.get('updated_at', created_at)
    if not isinstance(title, str):
        title = '' if title is None else str(title)
    if not isinstance(content, str):
        content = '' if content is None else str(content)
    if not isinstance(created_at, str):
        created_at = str(created_at) if created_at else ''
    if not isinstance(updated_at, str):
        updated_at = created_at
    if source_type == 'mindmap' and map_text is not None:
        content = str(map_text).replace('\x00', '')[:300_000]

    tags = []
    seen_tags: set[str] = set()
    for tag in raw.get('tags', []) if isinstance(raw.get('tags', []), list) else []:
        if not isinstance(tag, str):
            continue
        tag = tag.replace('\x00', '').strip().lstrip('#').strip()[:64]
        key = tag.casefold()
        if tag and key != 'карта' and key not in seen_tags:
            tags.append(tag)
            seen_tags.add(key)

    checklist = []
    seen_checklist: set[str] = set()
    for item in raw.get('checklist', []) if isinstance(raw.get('checklist', []), list) else []:
        if not isinstance(item, Mapping):
            continue
        item_id = item.get('id')
        if not isinstance(item_id, str) or not item_id or item_id in seen_checklist:
            item_id = uuid.uuid4().hex
        text = item.get('text', '')
        checklist.append({
            'id': item_id,
            'text': ('' if text is None else str(text)).replace('\x00', '')[:2_000],
            'checked': bool(item.get('checked', False)),
        })
        seen_checklist.add(item_id)

    color = raw.get('color', 'default')
    if color not in engine.PROJECT_NOTE_COLORS:
        color = 'default'
    sort_order = raw.get('sort_order', fallback_index)
    if not isinstance(sort_order, int) or isinstance(sort_order, bool):
        sort_order = fallback_index
    revision = raw.get('revision', 0)
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
        revision = 0
    return {
        'id': note_id,
        'project_id': project_id,
        'stage_id': stage_id,
        'title': title.replace('\x00', '')[:500],
        'content': content.replace('\x00', '')[:300_000],
        'content_format': 'plain' if source_type == 'mindmap' else 'html',
        'checklist': checklist[:500] if source_type == 'project' else [],
        'color': color,
        'pinned': bool(raw.get('pinned', False)),
        'archived': bool(raw.get('archived', False)),
        'sort_order': max(0, sort_order),
        'tags': tags,
        'source_type': source_type,
        'source_map_id': source_map_id,
        'source_node_id': source_node_id,
        'created_at': created_at,
        'updated_at': updated_at,
        'revision': revision,
        'metadata': _metadata(raw),
    }


def _map_texts(entity: object) -> dict[str, str]:
    from nfprogress.core.services.notes import extract_mindmap_notes
    return {item['id']: item['text'] for item in extract_mindmap_notes(getattr(entity, 'mindmap_data', None))}


def canonical_notes_from_projects(projects: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Build the complete legacy Notes state without mutating pickle objects."""
    result: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    project_map = projects.get('projects', {}) if isinstance(projects, Mapping) else {}
    for project in project_map.values() if isinstance(project_map, Mapping) else []:
        project_id = getattr(project, 'project_id', None)
        if not isinstance(project_id, str) or not project_id:
            continue
        entities = [(project, None), *[(stage, getattr(stage, 'stage_id', None)) for stage in getattr(project, 'stages', [])]]
        for entity, stage_id in entities:
            if stage_id is not None and not isinstance(stage_id, str):
                continue
            map_texts = _map_texts(entity)
            map_data = engine.normalize_mindmap_data(getattr(entity, 'mindmap_data', None))
            map_id = map_data['nodeData']['id'] if map_data is not None else None
            records = getattr(entity, 'project_notes', [])
            normalized: list[dict[str, Any]] = []
            for index, raw in enumerate(records if isinstance(records, list) else []):
                source_id = raw.get('source_node_id') if isinstance(raw, Mapping) else None
                item = _canonical_record(
                    raw, project_id=project_id, stage_id=stage_id,
                    fallback_index=index, map_text=map_texts.get(source_id),
                )
                if item is not None:
                    if item['source_type'] == 'mindmap':
                        item['source_map_id'] = map_id
                    normalized.append(item)
            by_source = {
                item['source_node_id']: item for item in normalized
                if item['source_type'] == 'mindmap'
            }
            next_order = max((item['sort_order'] for item in normalized), default=-1) + 1
            for source_id, text in map_texts.items():
                if source_id in by_source:
                    continue
                item = _canonical_record(
                    {'source_type': 'mindmap', 'source_node_id': source_id,
                     'source_map_id': map_id},
                    project_id=project_id, stage_id=stage_id,
                    fallback_index=next_order, map_text=text,
                )
                if item is None:
                    continue
                item['source_map_id'] = map_id
                normalized.append(item)
                next_order += 1
            for item in normalized:
                if item['id'] in seen_ids:
                    item['id'] = uuid.uuid5(
                        uuid.NAMESPACE_URL,
                        f"nfprogress-note-collision:{project_id}:{stage_id}:{item['id']}",
                    ).hex
                seen_ids.add(item['id'])
                result.append(item)
    return result


class SQLiteNotesRepository:
    """Fixed-query Notes repository; it never writes projects or stages."""

    def __init__(self, data_root: str | Path) -> None:
        self.data_root = Path(data_root).expanduser().resolve()
        self.ownership = StorageOwnershipRepository(self.data_root)

    def _require_owner(self) -> None:
        if self.ownership.get_owner(Subsystem.NOTES) != StorageOwner.SQLITE:
            raise RuntimeError('SQLite notes are not authoritative yet.')

    @staticmethod
    def _row(row) -> dict[str, Any]:
        return _json_object(row['payload_json'])

    def list(self, project_id: str, stage_id: str | None = None) -> list[dict[str, Any]]:
        self._require_owner()
        with open_database(self.data_root) as db:
            if stage_id is None:
                rows = db.execute(
                    'SELECT payload_json FROM notes WHERE project_id = ? AND stage_id IS NULL '
                    "ORDER BY json_extract(payload_json, '$.archived'), "
                    "json_extract(payload_json, '$.pinned') DESC, "
                    "json_extract(payload_json, '$.sort_order'), "
                    "json_extract(payload_json, '$.created_at'), rowid",
                    (project_id,),
                ).fetchall()
            else:
                rows = db.execute(
                    'SELECT payload_json FROM notes WHERE project_id = ? AND stage_id = ? '
                    "ORDER BY json_extract(payload_json, '$.archived'), "
                    "json_extract(payload_json, '$.pinned') DESC, "
                    "json_extract(payload_json, '$.sort_order'), "
                    "json_extract(payload_json, '$.created_at'), rowid",
                    (project_id, stage_id),
                ).fetchall()
        return [self._row(row) for row in rows]

    def list_all(self, project_id: str) -> list[dict[str, Any]]:
        self._require_owner()
        with open_database(self.data_root) as db:
            rows = db.execute(
                'SELECT payload_json FROM notes WHERE project_id = ? '
                "ORDER BY json_extract(payload_json, '$.archived'), "
                "json_extract(payload_json, '$.pinned') DESC, "
                "json_extract(payload_json, '$.sort_order'), "
                "json_extract(payload_json, '$.created_at'), rowid",
                (project_id,),
            ).fetchall()
        return [self._row(row) for row in rows]

    def get(self, note_id: str, project_id: str | None = None) -> dict[str, Any] | None:
        self._require_owner()
        with open_database(self.data_root) as db:
            query = 'SELECT payload_json FROM notes WHERE id = ?'
            params: list[Any] = [note_id]
            if project_id is not None:
                query += ' AND project_id = ?'
                params.append(project_id)
            row = db.execute(query, params).fetchone()
        return self._row(row) if row is not None else None

    def validate_relation(self, project_id: str, stage_id: str | None = None) -> None:
        self._require_owner()
        with open_database(self.data_root) as db:
            status = db.execute('SELECT sync_status FROM mirror_state WHERE id = 1').fetchone()
            if status is None or status['sync_status'] != 'healthy':
                raise ConflictError('Локальный backend недоступен.')
            project = db.execute('SELECT 1 FROM projects WHERE id = ?', (project_id,)).fetchone()
            if project is None:
                raise NotFoundError('Проект больше не существует.')
            if stage_id is not None:
                stage = db.execute(
                    'SELECT project_id FROM stages WHERE id = ?', (stage_id,),
                ).fetchone()
                if stage is None or stage['project_id'] != project_id:
                    raise NotFoundError('Этап больше не существует.')

    def create(self, record: Mapping[str, Any]) -> dict[str, Any]:
        self._require_owner()
        self.validate_relation(record['project_id'], record.get('stage_id'))
        value = dict(record)
        with open_database(self.data_root) as db:
            with db:
                db.execute(
                    'INSERT INTO notes(id, project_id, stage_id, updated_at, payload_json) VALUES(?,?,?,?,?)',
                    (value['id'], value['project_id'], value.get('stage_id'), value.get('updated_at'), _json(value)),
                )
        return value

    def update(self, note_id: str, patch: Mapping[str, Any]) -> dict[str, Any]:
        self._require_owner()
        if not isinstance(patch, Mapping):
            raise TypeError('note patch must be an object')
        mutable_fields = {
            'title', 'content', 'content_format', 'checklist', 'color',
            'pinned', 'archived', 'sort_order', 'tags', 'source_map_id',
            'updated_at', 'revision', 'metadata',
        }
        unknown = set(patch) - mutable_fields
        if unknown:
            raise ValueError(f'cannot update note identity field: {sorted(unknown)[0]}')
        with open_database(self.data_root) as db:
            with db:
                row = db.execute('SELECT * FROM notes WHERE id = ?', (note_id,)).fetchone()
                if row is None:
                    raise NotFoundError('Заметка больше не существует.')
                value = self._row(row)
                value.update(deepcopy(dict(patch)))
                value['updated_at'] = value.get('updated_at') or _now_iso()
                db.execute(
                    'UPDATE notes SET updated_at = ?, payload_json = ? WHERE id = ?',
                    (value['updated_at'], _json(value), note_id),
                )
        return value

    def delete(self, note_id: str, *, project_id: str | None = None) -> bool:
        self._require_owner()
        with open_database(self.data_root) as db:
            with db:
                query = 'DELETE FROM notes WHERE id = ?'
                params: list[Any] = [note_id]
                if project_id is not None:
                    query += ' AND project_id = ?'
                    params.append(project_id)
                db.execute(query, params)
                return db.execute('SELECT changes()').fetchone()[0] == 1

    def delete_for_project(self, project_id: str) -> None:
        self._require_owner()
        with open_database(self.data_root) as db:
            with db:
                db.execute('DELETE FROM notes WHERE project_id = ?', (project_id,))

    def delete_for_stage(self, project_id: str, stage_id: str) -> None:
        self._require_owner()
        with open_database(self.data_root) as db:
            with db:
                db.execute('DELETE FROM notes WHERE project_id = ? AND stage_id = ?', (project_id, stage_id))

    def reorder(self, ordered_ids: list[str]) -> None:
        self._require_owner()
        with open_database(self.data_root) as db:
            with db:
                now = _now_iso()
                for index, note_id in enumerate(ordered_ids):
                    db.execute(
                        "UPDATE notes SET updated_at = ?, payload_json = json_set(payload_json, '$.sort_order', ?, '$.revision', json_extract(payload_json, '$.revision') + 1, '$.updated_at', ?) WHERE id = ?",
                        (now, index, now, note_id),
                    )


def cutover_notes(data_root: str | Path, legacy_projects: Mapping[str, Any]) -> None:
    """Import all legacy Notes and switch ownership in one SQLite transaction."""
    root = Path(data_root).expanduser().resolve()
    expected = canonical_notes_from_projects(legacy_projects)
    expected_by_id = {item['id']: item for item in expected}
    with open_database(root) as db:
        with db:
            owner = db.execute(
                'SELECT owner FROM storage_ownership WHERE subsystem = ?',
                (Subsystem.NOTES.value,),
            ).fetchone()
            if owner is None:
                raise RuntimeError('missing storage ownership for notes')
            if owner['owner'] == StorageOwner.SQLITE.value:
                return
            db.execute('DELETE FROM notes')
            db.executemany(
                'INSERT INTO notes(id, project_id, stage_id, updated_at, payload_json) VALUES(?,?,?,?,?)',
                [(
                    item['id'], item['project_id'], item['stage_id'],
                    item['updated_at'], _json(item),
                ) for item in expected],
            )
            actual = {
                row['id']: _json_object(row['payload_json'])
                for row in db.execute('SELECT id, payload_json FROM notes')
            }
            if actual != expected_by_id:
                raise RuntimeError('notes SQLite parity verification failed')
            db.execute(
                "UPDATE storage_ownership SET owner = ?, updated_at = datetime('now') WHERE subsystem = ?",
                (StorageOwner.SQLITE.value, Subsystem.NOTES.value),
            )


__all__ = ['SQLiteNotesRepository', 'canonical_notes_from_projects', 'cutover_notes']
