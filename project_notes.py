"""Project notes repository, Mind Elixir synchronization, and local WebView UI."""

from __future__ import annotations

import hashlib
import html
import json
import re
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

from PySide6.QtCore import QEvent, QObject, QTimer, QUrl, Qt, Signal
from PySide6.QtGui import QCloseEvent, QDesktopServices
from PySide6.QtWidgets import QDialog

import engine
from localization import (
    LocalizedMessageBox as QMessageBox,
    current_language,
    tr,
)
from mindmap import NativeWebView
from UI_fiiles.project_notes_dialog import Ui_project_notes_dialog


SYSTEM_MAP_TAG = 'карта'
MAX_TITLE_LENGTH = 500
MAX_CONTENT_LENGTH = 300_000
MAX_CHECKLIST_ITEM_LENGTH = 2_000
ALLOWED_LINK_SCHEMES = {'http', 'https', 'mailto'}
ALLOWED_HTML_TAGS = {
    'a', 'b', 'br', 'div', 'em', 'i', 'li', 'ol', 'p', 's', 'strike',
    'strong', 'u', 'ul',
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _safe_external_url(value: object) -> str | None:
    if not isinstance(value, str) or len(value) > 8_192:
        return None
    parsed = urlparse(value.strip())
    if parsed.scheme.lower() not in ALLOWED_LINK_SCHEMES:
        return None
    if parsed.scheme.lower() in {'http', 'https'} and not parsed.netloc:
        return None
    if parsed.scheme.lower() == 'mailto' and not parsed.path:
        return None
    return value.strip()


class _NoteHtmlSanitizer(HTMLParser):
    """Small allow-list sanitizer for contenteditable output."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag not in ALLOWED_HTML_TAGS:
            return
        if tag == 'a':
            href = next((value for name, value in attrs if name.lower() == 'href'), None)
            safe_href = _safe_external_url(href)
            if safe_href is None:
                return
            self.parts.append(
                '<a href="{}" rel="noopener noreferrer">'.format(
                    html.escape(safe_href, quote=True),
                )
            )
            return
        self.parts.append(f'<{tag}>')

    def handle_startendtag(self, tag: str, attrs) -> None:
        if tag.lower() == 'br':
            self.parts.append('<br>')

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in ALLOWED_HTML_TAGS and tag not in {'br'}:
            self.parts.append(f'</{tag}>')

    def handle_data(self, data: str) -> None:
        self.parts.append(html.escape(data))


def sanitize_note_html(value: object) -> str:
    source = value if isinstance(value, str) else str(value or '')
    sanitizer = _NoteHtmlSanitizer()
    try:
        sanitizer.feed(source[:MAX_CONTENT_LENGTH])
        sanitizer.close()
    except (ValueError, TypeError):
        return html.escape(source[:MAX_CONTENT_LENGTH])
    return ''.join(sanitizer.parts)


class _PlainTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() in {'br', 'div', 'li', 'p'} and self.parts:
            self.parts.append('\n')

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {'div', 'li', 'p'}:
            self.parts.append('\n')

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def note_html_to_plain_text(value: object) -> str:
    source = value if isinstance(value, str) else str(value or '')
    parser = _PlainTextExtractor()
    try:
        parser.feed(source[:MAX_CONTENT_LENGTH])
        parser.close()
    except (ValueError, TypeError):
        return source[:MAX_CONTENT_LENGTH]
    text = ''.join(parser.parts).replace('\x00', '')
    return re.sub(r'\n{3,}', '\n\n', text).strip()


def _walk_native_map_notes(nodes) -> list[dict]:
    notes = []
    for node in nodes if isinstance(nodes, list) else []:
        if not isinstance(node, dict):
            continue
        if (
            node.get('nfprogressNote') is True
            and isinstance(node.get('id'), str)
            and node['id']
            and isinstance(node.get('topic'), str)
        ):
            notes.append({'id': node['id'], 'text': node['topic']})
        notes.extend(_walk_native_map_notes(node.get('children', [])))
    return notes


def extract_mindmap_notes(mindmap_data: object) -> list[dict]:
    """Extract old and current custom notes without mutating the map JSON."""
    normalized = engine.normalize_mindmap_data(mindmap_data)
    if normalized is None:
        return []

    notes_by_id: dict[str, dict] = {}
    for item in normalized.get('nfprogressFloatingItems', []):
        if item.get('kind') == 'note':
            notes_by_id[item['id']] = {'id': item['id'], 'text': item['text']}
    for note in _walk_native_map_notes(normalized.get('freeNodes', [])):
        notes_by_id[note['id']] = note
    return list(notes_by_id.values())


def _find_native_note(nodes, node_id: str) -> dict | None:
    for node in nodes if isinstance(nodes, list) else []:
        if not isinstance(node, dict):
            continue
        if node.get('id') == node_id and node.get('nfprogressNote') is True:
            return node
        found = _find_native_note(node.get('children', []), node_id)
        if found is not None:
            return found
    return None


def set_mindmap_note_text(
        mindmap_data: object,
        source_node_id: str,
        text: str,
) -> dict | None:
    normalized = engine.normalize_mindmap_data(mindmap_data)
    if normalized is None:
        return None
    text = str(text).replace('\x00', '')[:MAX_CONTENT_LENGTH]
    native_note = _find_native_note(normalized.get('freeNodes', []), source_node_id)
    if native_note is not None:
        native_note['topic'] = text
        return normalized
    for item in normalized.get('nfprogressFloatingItems', []):
        if item.get('id') == source_node_id and item.get('kind') == 'note':
            item['text'] = text
            return normalized
    return None


def _collect_node_ids(node: dict) -> set[str]:
    identifiers = set()
    node_id = node.get('id')
    if isinstance(node_id, str) and node_id:
        identifiers.add(node_id)
    for child in node.get('children', []):
        if isinstance(child, dict):
            identifiers.update(_collect_node_ids(child))
    return identifiers


def _remove_native_note(nodes: list, node_id: str) -> set[str]:
    for index, node in enumerate(list(nodes)):
        if not isinstance(node, dict):
            continue
        if node.get('id') == node_id and node.get('nfprogressNote') is True:
            removed_ids = _collect_node_ids(node)
            del nodes[index]
            return removed_ids
        removed_ids = _remove_native_note(node.get('children', []), node_id)
        if removed_ids:
            return removed_ids
    return set()


def remove_mindmap_note(
        mindmap_data: object,
        source_node_id: str,
) -> dict | None:
    normalized = engine.normalize_mindmap_data(mindmap_data)
    if normalized is None:
        return None

    removed_ids = _remove_native_note(
        normalized.setdefault('freeNodes', []),
        source_node_id,
    )
    legacy_items = normalized.get('nfprogressFloatingItems', [])
    legacy_removed = any(
        item.get('id') == source_node_id and item.get('kind') == 'note'
        for item in legacy_items
        if isinstance(item, dict)
    )
    if legacy_removed:
        normalized['nfprogressFloatingItems'] = [
            item for item in legacy_items
            if not (
                isinstance(item, dict)
                and item.get('id') == source_node_id
                and item.get('kind') == 'note'
            )
        ]
        removed_ids.add(source_node_id)
    if not removed_ids:
        return None

    normalized['arrows'] = [
        arrow for arrow in normalized.get('arrows', [])
        if not (
            isinstance(arrow, dict)
            and (arrow.get('from') in removed_ids or arrow.get('to') in removed_ids)
        )
    ]
    normalized['summaries'] = [
        summary for summary in normalized.get('summaries', [])
        if not (
            isinstance(summary, dict)
            and summary.get('parent') in removed_ids
        )
    ]
    normalized['nfprogressFloatingLinks'] = [
        link for link in normalized.get('nfprogressFloatingLinks', [])
        if not (
            isinstance(link, dict)
            and (link.get('from') in removed_ids or link.get('to') in removed_ids)
        )
    ]
    return normalized


def _map_root_id(entity) -> str | None:
    normalized = engine.normalize_mindmap_data(
        getattr(entity, 'mindmap_data', None),
    )
    if normalized is None:
        return None
    return normalized['nodeData']['id']


def _derived_map_title(text: str) -> str:
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), '')
    return first_line[:100] or tr('Заметка карты')


def project_notes_reference(entity) -> dict:
    if isinstance(entity, engine.Stage) or getattr(entity, 'is_stage', False):
        return {
            'kind': 'stage',
            'stage_id': getattr(entity, 'stage_id', None),
            'parent_project_name': getattr(entity, 'parent_project_name', None),
        }
    return {
        'kind': 'project',
        'project_id': getattr(entity, 'project_id', None),
        'project_name': entity.name,
    }


def _resolve_entity(data: dict, reference: dict):
    projects = data.get('projects', {})
    if reference.get('kind') == 'stage':
        stage_id = reference.get('stage_id')
        preferred_parent = projects.get(reference.get('parent_project_name'))
        candidates = [preferred_parent] if preferred_parent is not None else []
        candidates.extend(
            project for project in projects.values()
            if project is not preferred_parent
        )
        for parent in candidates:
            for stage in getattr(parent, 'stages', []):
                if getattr(stage, 'stage_id', None) == stage_id:
                    stage.parent_project_name = parent.name
                    return parent, stage
        return None, None

    project_id = reference.get('project_id')
    for project in projects.values():
        if getattr(project, 'project_id', None) == project_id:
            return project, project
    if isinstance(project_id, str) and project_id:
        return None, None
    project = projects.get(reference.get('project_name'))
    return (project, project) if project is not None else (None, None)


def _normalize_tags(value: object) -> list[str]:
    tags = []
    seen = set()
    for raw_tag in value if isinstance(value, list) else []:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lstrip('#').strip()[:64]
        key = tag.casefold()
        if not tag or key == SYSTEM_MAP_TAG or key in seen:
            continue
        seen.add(key)
        tags.append(tag)
    return tags


def _normalize_checklist(value: object) -> list[dict]:
    checklist = []
    seen_ids = set()
    for raw_item in value if isinstance(value, list) else []:
        if not isinstance(raw_item, dict):
            continue
        item_id = raw_item.get('id')
        if not isinstance(item_id, str) or not item_id or item_id in seen_ids:
            item_id = uuid.uuid4().hex
        item_text = raw_item.get('text', '')
        checklist.append({
            'id': item_id,
            'text': str(item_text).replace('\x00', '')[:MAX_CHECKLIST_ITEM_LENGTH],
            'checked': bool(raw_item.get('checked', False)),
        })
        seen_ids.add(item_id)
    return checklist[:500]


class ProjectNotesService(QObject):
    """Single Python synchronization layer for project and Mind Elixir notes."""

    event_emitted = Signal(str, object, str, int)
    map_command = Signal(str, str, str)
    storage_changed = Signal(str)

    def __init__(self, entity, parent=None):
        super().__init__(parent)
        self.reference = project_notes_reference(entity)
        self.bound_entity = entity
        self._cache: dict[str, dict] = {}
        self._event_revision = 0

    @property
    def entity_key(self) -> tuple:
        if self.reference['kind'] == 'stage':
            return ('stage', self.reference.get('stage_id'))
        return ('project', self.reference.get('project_id'))

    def _load(self):
        data = engine.load_data()
        parent, entity = _resolve_entity(data, self.reference)
        if entity is None:
            raise ValueError(tr('Проект больше не существует.'))
        return data, parent, entity

    def project_scope_id(self) -> str | None:
        """Return the parent project id shared by project and stage views."""
        _, parent, entity = self._load()
        return getattr(parent or entity, 'project_id', None)

    def _is_aggregate_view(self, entity) -> bool:
        return (
            self.reference.get('kind') == 'project'
            and bool(getattr(entity, 'has_stages', lambda: False)())
        )

    def _view_entities(self, entity) -> list[tuple[object, str | None]]:
        owners = [(entity, None)]
        if self._is_aggregate_view(entity):
            owners.extend(
                (stage, stage.name)
                for stage in getattr(entity, 'stages', [])
            )
        return owners

    @staticmethod
    def _owner_identity(entity) -> tuple[str, str | None]:
        if isinstance(entity, engine.Stage) or getattr(entity, 'is_stage', False):
            return 'stage', getattr(entity, 'stage_id', None)
        return 'project', getattr(entity, 'project_id', None)

    def _view_note_id(self, entity, record_id: str, aggregate: bool) -> str:
        if not aggregate:
            return record_id
        owner_type, owner_id = self._owner_identity(entity)
        return f'{owner_type}:{owner_id}:{record_id}'

    @staticmethod
    def _copy_note_state(source, target) -> None:
        target.project_notes = deepcopy(source.project_notes)
        target.mindmap_data = deepcopy(source.mindmap_data)
        target.project_id = source.project_id

    def _copy_to_bound_entity(self, entity) -> None:
        self._copy_note_state(entity, self.bound_entity)
        if not self._is_aggregate_view(entity):
            return
        bound_stages = {
            getattr(stage, 'stage_id', None): stage
            for stage in getattr(self.bound_entity, 'stages', [])
        }
        for stage in getattr(entity, 'stages', []):
            bound_stage = bound_stages.get(getattr(stage, 'stage_id', None))
            if bound_stage is not None:
                self._copy_note_state(stage, bound_stage)

    def _save(self, data: dict, entity) -> None:
        engine.save_data(data)
        self._copy_to_bound_entity(entity)

    def _is_read_only(self, entity) -> bool:
        if getattr(entity, 'status', None) != 'завершен':
            return False
        if isinstance(entity, engine.Stage) or getattr(entity, 'is_stage', False):
            return True
        return not engine.dev_mode

    def _require_writable(self, entity) -> None:
        if self._is_read_only(entity):
            raise PermissionError(tr(
                'Заметки завершённого проекта доступны только для просмотра.'
            ))

    def _new_map_record(self, source_node_id: str, map_id: str | None, order: int) -> dict:
        digest = hashlib.sha256(source_node_id.encode('utf-8')).hexdigest()[:28]
        return {
            'id': f'mindmap-{digest}',
            'title': '',
            'content': '',
            'content_format': 'plain',
            'checklist': [],
            'color': 'default',
            'pinned': False,
            'archived': False,
            'sort_order': order,
            'tags': [],
            'source_type': 'mindmap',
            'source_map_id': map_id,
            'source_node_id': source_node_id,
            'created_at': _now_iso(),
            'updated_at': _now_iso(),
            'revision': 0,
        }

    def _reconcile(self, entity, aggregate: bool = False) -> bool:
        records = engine.normalize_project_note_records(
            getattr(entity, 'project_notes', []),
        )
        notes = extract_mindmap_notes(getattr(entity, 'mindmap_data', None))
        map_notes = {note['id']: note['text'] for note in notes}
        map_id = _map_root_id(entity)
        by_source = {
            record['source_node_id']: record
            for record in records
            if record['source_type'] == 'mindmap'
        }
        changed = records != getattr(entity, 'project_notes', [])
        next_order = max((record['sort_order'] for record in records), default=-1) + 1
        for source_node_id, text in map_notes.items():
            record = by_source.get(source_node_id)
            if record is None:
                record = self._new_map_record(source_node_id, map_id, next_order)
                while any(item['id'] == record['id'] for item in records):
                    record['id'] = f'mindmap-{uuid.uuid4().hex}'
                records.append(record)
                by_source[source_node_id] = record
                next_order += 1
                changed = True
            if record.get('source_map_id') != map_id:
                record['source_map_id'] = map_id
                changed = True
            cached = self._cache.get(
                self._view_note_id(entity, record['id'], aggregate)
            )
            if cached is not None and cached.get('content') != text:
                record['updated_at'] = _now_iso()
                record['revision'] += 1
                changed = True

        reconciled = [
            record for record in records
            if record['source_type'] != 'mindmap'
            or record['source_node_id'] in map_notes
        ]
        if len(reconciled) != len(records):
            changed = True
        entity.project_notes = reconciled
        return changed

    def _reconcile_view(self, entity) -> bool:
        aggregate = self._is_aggregate_view(entity)
        changed = False
        for owner, _stage_name in self._view_entities(entity):
            if self._reconcile(owner, aggregate):
                changed = True
        return changed

    def _project_note(
            self,
            entity,
            record: dict,
            map_notes: dict[str, str] | None = None,
            *,
            aggregate: bool = False,
            stage_name: str | None = None,
    ) -> dict:
        result = deepcopy(record)
        result['id'] = self._view_note_id(entity, record['id'], aggregate)
        owner_type, owner_id = self._owner_identity(entity)
        result['owner_type'] = owner_type
        result['owner_id'] = owner_id
        result['stage_name'] = stage_name if aggregate else None
        if record['source_type'] == 'mindmap':
            if map_notes is None:
                map_notes = {
                    note['id']: note['text']
                    for note in extract_mindmap_notes(entity.mindmap_data)
                }
            result['content'] = map_notes.get(record['source_node_id'], '')
            result['display_title'] = record['title'] or _derived_map_title(result['content'])
            result['system_tags'] = [SYSTEM_MAP_TAG]
        else:
            result['content'] = sanitize_note_html(record['content'])
            result['display_title'] = record['title'] or tr('Без заголовка')
            result['system_tags'] = []
        result['read_only'] = self._is_read_only(entity)
        return result

    def _project_all(self, entity) -> list[dict]:
        aggregate = self._is_aggregate_view(entity)
        projected = []
        for owner_index, (owner, stage_name) in enumerate(
                self._view_entities(entity)
        ):
            map_notes = {}
            if any(
                    record['source_type'] == 'mindmap'
                    for record in owner.project_notes
            ):
                map_notes = {
                    note['id']: note['text']
                    for note in extract_mindmap_notes(owner.mindmap_data)
                }
            projected.extend(
                (
                    owner_index,
                    self._project_note(
                        owner,
                        record,
                        map_notes,
                        aggregate=aggregate,
                        stage_name=stage_name,
                    ),
                )
                for record in owner.project_notes
            )
        projected.sort(key=lambda item: (
            item[1]['archived'],
            not item[1]['pinned'],
            item[1]['sort_order'],
            item[0],
            item[1]['created_at'],
        ))
        return [note for _owner_index, note in projected]

    def _emit_diff(self, notes: list[dict], origin: str) -> bool:
        current = {note['id']: note for note in notes}
        changed = current != self._cache
        for note_id in self._cache.keys() - current.keys():
            self._event_revision += 1
            self.event_emitted.emit('noteDeleted', note_id, origin, self._event_revision)
        for note_id in current.keys() - self._cache.keys():
            self._event_revision += 1
            self.event_emitted.emit(
                'noteCreated', current[note_id], origin, self._event_revision,
            )
        for note_id in current.keys() & self._cache.keys():
            if current[note_id] != self._cache[note_id]:
                self._event_revision += 1
                self.event_emitted.emit(
                    'noteUpdated', current[note_id], origin, self._event_revision,
                )
        self._cache = deepcopy(current)
        return changed

    def _emit_entity(self, entity, origin: str) -> list[dict]:
        notes = self._project_all(entity)
        changed = self._emit_diff(notes, origin)
        if changed and origin in {'mindmap', 'notes'}:
            self.storage_changed.emit(origin)
        return notes

    def load_notes(self) -> tuple[list[dict], bool]:
        data, _, entity = self._load()
        if self._reconcile_view(entity):
            self._save(data, entity)
        else:
            self._copy_to_bound_entity(entity)
        notes = self._project_all(entity)
        self._cache = {note['id']: deepcopy(note) for note in notes}
        return notes, self._is_read_only(entity)

    def refresh_from_storage(self, origin: str = 'database') -> list[dict]:
        data, _, entity = self._load()
        if self._reconcile_view(entity):
            self._save(data, entity)
        else:
            self._copy_to_bound_entity(entity)
        notes = self._project_all(entity)
        changed = self._emit_diff(notes, origin)
        if changed and origin in {'mindmap', 'notes'}:
            self.storage_changed.emit(origin)
        return notes

    def _find_record(self, entity, note_id: str):
        aggregate = self._is_aggregate_view(entity)
        for owner, stage_name in self._view_entities(entity):
            for record in owner.project_notes:
                if self._view_note_id(owner, record['id'], aggregate) == note_id:
                    return owner, record, stage_name
        return None, None, None

    def get_note(self, note_id: str) -> dict | None:
        data, _, entity = self._load()
        if self._reconcile_view(entity):
            self._save(data, entity)
        owner, record, stage_name = self._find_record(entity, note_id)
        if record is None:
            return None
        return self._project_note(
            owner,
            record,
            aggregate=self._is_aggregate_view(entity),
            stage_name=stage_name,
        )

    def get_map_target(self, note_id: str):
        data, _, entity = self._load()
        if self._reconcile_view(entity):
            self._save(data, entity)
        owner, record, _stage_name = self._find_record(entity, note_id)
        if record is None or record['source_type'] != 'mindmap':
            return None
        return owner, record['source_node_id']

    def create_note(self) -> dict:
        data, _, entity = self._load()
        self._require_writable(entity)
        self._reconcile_view(entity)
        now = _now_iso()
        record = {
            'id': uuid.uuid4().hex,
            'title': '',
            'content': '',
            'content_format': 'html',
            'checklist': [],
            'color': 'default',
            'pinned': False,
            'archived': False,
            'sort_order': max(
                (
                    item['sort_order']
                    for owner, _stage_name in self._view_entities(entity)
                    for item in owner.project_notes
                ),
                default=-1,
            ) + 1,
            'tags': [],
            'source_type': 'project',
            'source_map_id': None,
            'source_node_id': None,
            'created_at': now,
            'updated_at': now,
            'revision': 0,
        }
        entity.project_notes.append(record)
        view_id = self._view_note_id(
            entity,
            record['id'],
            self._is_aggregate_view(entity),
        )
        self._save(data, entity)
        notes = self._emit_entity(entity, 'notes')
        return next(note for note in notes if note['id'] == view_id)

    def update_note(self, note_id: str, patch: object) -> dict:
        if not isinstance(patch, dict):
            raise ValueError(tr('Некорректные данные заметки.'))
        data, _, entity = self._load()
        self._reconcile_view(entity)
        owner, record, stage_name = self._find_record(entity, note_id)
        if record is None:
            raise ValueError(tr('Заметка больше не существует.'))
        self._require_writable(owner)

        changed = False
        map_text_changed = False
        if 'title' in patch:
            title = str(patch.get('title') or '').replace('\x00', '')[:MAX_TITLE_LENGTH]
            if title != record['title']:
                record['title'] = title
                changed = True
        if 'tags' in patch:
            tags = _normalize_tags(patch['tags'])
            if tags != record['tags']:
                record['tags'] = tags
                changed = True
        if 'color' in patch:
            requested_color = patch['color']
            color = (
                requested_color
                if isinstance(requested_color, str)
                and requested_color in engine.PROJECT_NOTE_COLORS
                else 'default'
            )
            if color != record['color']:
                record['color'] = color
                changed = True
        for field in ('pinned', 'archived'):
            if field in patch:
                value = bool(patch[field])
                if value != record[field]:
                    record[field] = value
                    changed = True

        if record['source_type'] == 'mindmap':
            if 'content' in patch:
                text = str(patch.get('content') or '').replace('\x00', '')[:MAX_CONTENT_LENGTH]
                current = next(
                    (
                        note['text'] for note in extract_mindmap_notes(owner.mindmap_data)
                        if note['id'] == record['source_node_id']
                    ),
                    None,
                )
                if current is None:
                    raise ValueError(tr(
                        'Связанная заметка карты больше не существует.'
                    ))
                if text != current:
                    updated_map = set_mindmap_note_text(
                        owner.mindmap_data,
                        record['source_node_id'],
                        text,
                    )
                    if updated_map is None:
                        raise ValueError(tr('Не удалось обновить заметку карты.'))
                    owner.mindmap_data = updated_map
                    map_text_changed = True
                    changed = True
        else:
            if 'content' in patch:
                content = sanitize_note_html(patch['content'])
                if content != record['content']:
                    record['content'] = content
                    changed = True
            if 'checklist' in patch:
                checklist = _normalize_checklist(patch['checklist'])
                if checklist != record['checklist']:
                    record['checklist'] = checklist
                    changed = True

        if changed:
            record['updated_at'] = _now_iso()
            record['revision'] += 1
            self._save(data, entity)
            if map_text_changed:
                self.map_command.emit(
                    'update',
                    record['source_node_id'],
                    next(
                        note['text'] for note in extract_mindmap_notes(owner.mindmap_data)
                        if note['id'] == record['source_node_id']
                    ),
                )
            notes = self._emit_entity(entity, 'notes')
            return next(note for note in notes if note['id'] == note_id)
        return self._project_note(
            owner,
            record,
            aggregate=self._is_aggregate_view(entity),
            stage_name=stage_name,
        )

    def delete_note(self, note_id: str) -> None:
        data, _, entity = self._load()
        self._reconcile_view(entity)
        owner, record, _stage_name = self._find_record(entity, note_id)
        if record is None:
            return
        self._require_writable(owner)
        source_node_id = record['source_node_id']
        if record['source_type'] == 'mindmap':
            updated_map = remove_mindmap_note(owner.mindmap_data, source_node_id)
            if updated_map is None:
                raise ValueError(tr(
                    'Связанная заметка карты больше не существует.'
                ))
            owner.mindmap_data = updated_map
        owner.project_notes = [
            item for item in owner.project_notes if item['id'] != record['id']
        ]
        self._save(data, entity)
        if source_node_id:
            self.map_command.emit('delete', source_node_id, '')
        self._emit_entity(entity, 'notes')

    def update_order(self, note_ids: object) -> None:
        if not isinstance(note_ids, list):
            return
        data, _, entity = self._load()
        self._require_writable(entity)
        self._reconcile_view(entity)
        order_by_id = {
            note_id: index
            for index, note_id in enumerate(note_ids)
            if isinstance(note_id, str)
        }
        aggregate = self._is_aggregate_view(entity)
        changed = False
        for owner, _stage_name in self._view_entities(entity):
            if self._is_read_only(owner):
                continue
            for record in owner.project_notes:
                view_id = self._view_note_id(owner, record['id'], aggregate)
                if view_id not in order_by_id:
                    continue
                order = order_by_id[view_id]
                if record['sort_order'] != order:
                    record['sort_order'] = order
                    record['updated_at'] = _now_iso()
                    record['revision'] += 1
                    changed = True
        if changed:
            self._save(data, entity)
            self._emit_entity(entity, 'notes')


def _standalone_notes_html(assets_path: Path) -> str:
    index_html = (assets_path / 'index.html').read_text(encoding='utf-8')
    styles = (assets_path / 'styles.css').read_text(encoding='utf-8')
    muuri = (assets_path / 'vendor' / 'muuri.min.js').read_text(encoding='utf-8')
    application = (assets_path / 'app.js').read_text(encoding='utf-8')
    index_html = index_html.replace(
        '<link rel="stylesheet" href="styles.css">',
        f'<style>{styles}</style>',
    )
    index_html = index_html.replace(
        '<script src="vendor/muuri.min.js"></script>',
        f'<script>{muuri}</script>',
    )
    return index_html.replace(
        '<script src="app.js"></script>',
        f'<script>{application}</script>',
    )


def _palette_payload(widget) -> dict:
    palette = widget.palette()
    colors = {
        'window': palette.window().color().name(),
        'surface': palette.base().color().name(),
        'surfaceAlt': palette.alternateBase().color().name(),
        'text': palette.text().color().name(),
        'muted': palette.placeholderText().color().name(),
        'border': palette.mid().color().name(),
        'accent': palette.highlight().color().name(),
        'accentText': palette.highlightedText().color().name(),
    }
    background = palette.window().color()
    colors['dark'] = background.lightnessF() < 0.5
    return colors


class ProjectNotesDialog(QDialog, Ui_project_notes_dialog):
    """Modeless Keep-like notes window using the same native WebView as Mind Elixir."""

    def __init__(self, service: ProjectNotesService, open_map_callback, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.service = service
        self.open_map_callback = open_map_callback
        self._ready = False
        self._poll_in_flight = False
        self._closing_after_flush = False
        self._close_flush_in_flight = False
        self._allow_close = False
        self._resize_update_timer = QTimer(self)
        self._resize_update_timer.setSingleShot(True)
        self._resize_update_timer.setInterval(80)
        self._resize_update_timer.timeout.connect(self._notify_viewport_changed)

        entity_name = service.bound_entity.name
        self.setWindowTitle(f"{tr('Заметки проекта')} — {entity_name}")
        self.notes_title_label.setText(f"{tr('Заметки проекта')}: {entity_name}")
        self.close_button.clicked.connect(self.close)

        qml_path = Path(engine.resource_path('mindmap_assets/WebViewHost.qml'))
        try:
            self.web_view = NativeWebView(qml_path, self.notes_container)
        except RuntimeError as error:
            self.status_label.setText(tr('Не удалось загрузить заметки проекта.'))
            self.status_label.setToolTip(str(error))
            return
        self.web_view.setAccessibleName(tr('Редактор заметок проекта'))
        self.web_view.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.notes_layout.addWidget(self.web_view)
        self.web_view.loadFinished.connect(self._on_page_loaded)

        self.service.event_emitted.connect(self._on_service_event)
        self._event_timer = QTimer(self)
        self._event_timer.setInterval(100)
        self._event_timer.timeout.connect(self._poll_events)

        assets_path = Path(engine.resource_path('notes_assets'))
        try:
            page_html = _standalone_notes_html(assets_path)
        except OSError as error:
            self.status_label.setText(tr('Не найдены файлы редактора заметок.'))
            self.status_label.setToolTip(str(error))
            return
        self.web_view.loadHtml(page_html)

    def _labels(self) -> dict:
        return {
            'newNote': tr('Новая заметка'),
            'documentTitle': tr('Заметки проекта'),
            'skipToNotes': tr('К заметкам'),
            'notesActions': tr('Действия с заметками'),
            'searchPlaceholder': tr('Поиск по заметкам'),
            'tags': tr('Теги'),
            'archive': tr('Архив'),
            'activeNotes': tr('Активные заметки'),
            'pinned': tr('Закреплённые'),
            'others': tr('Остальные'),
            'empty': tr('Заметок пока нет.'),
            'emptyArchive': tr('В архиве пока нет заметок.'),
            'titlePlaceholder': tr('Заголовок'),
            'contentPlaceholder': tr('Текст заметки'),
            'mapNote': tr('Заметка карты'),
            'openOnMap': tr('Открыть на карте'),
            'pin': tr('Закрепить'),
            'unpin': tr('Открепить'),
            'archiveAction': tr('Переместить в архив'),
            'restore': tr('Восстановить из архива'),
            'delete': tr('Удалить заметку'),
            'color': tr('Цвет заметки'),
            'drag': tr('Перетащить заметку'),
            'bold': tr('Полужирный'),
            'italic': tr('Курсив'),
            'strike': tr('Зачёркнутый'),
            'unorderedList': tr('Маркированный список'),
            'orderedList': tr('Нумерованный список'),
            'link': tr('Добавить ссылку'),
            'linkPrompt': tr('Введите адрес ссылки'),
            'checklist': tr('Чек-лист'),
            'addChecklistItem': tr('Добавить пункт'),
            'removeChecklistItem': tr('Удалить пункт'),
            'tagsPlaceholder': tr('Теги через запятую'),
            'stage': tr('Этап'),
            'mapTag': '#карта',
            'allTags': tr('Все теги'),
            'plainMapNote': tr(
                'Текст заметки карты хранится без форматирования.'
            ),
            'readOnly': tr('Заметки доступны только для просмотра.'),
            'savePending': tr('Сохранение…'),
            'saved': tr('Все изменения сохранены.'),
            'error': tr('Не удалось сохранить заметку.'),
            'colors': {
                'default': tr('По умолчанию'),
                'coral': tr('Коралловый'),
                'orange': tr('Оранжевый'),
                'yellow': tr('Жёлтый'),
                'green': tr('Зелёный'),
                'teal': tr('Бирюзовый'),
                'blue': tr('Синий'),
                'purple': tr('Фиолетовый'),
                'pink': tr('Розовый'),
                'brown': tr('Коричневый'),
                'gray': tr('Серый'),
            },
        }

    def _initial_payload(self) -> str:
        notes, read_only = self.service.load_notes()
        return json.dumps(
            {
                'notes': notes,
                'labels': self._labels(),
                'locale': current_language(),
                'readOnly': read_only,
                'theme': _palette_payload(self),
            },
            ensure_ascii=False,
        )

    def _on_page_loaded(self, successful, error_text=''):
        if not successful:
            self.status_label.setText(tr('Не удалось загрузить заметки проекта.'))
            self.status_label.setToolTip(str(error_text))
            return
        try:
            payload = self._initial_payload()
        except (OSError, ValueError) as error:
            self.status_label.setText(tr('Не удалось загрузить заметки проекта.'))
            self.status_label.setToolTip(str(error))
            return
        script = (
            '(() => {'
            'if (!window.nfprogressNotes) return false;'
            f'window.nfprogressNotes.initialize(JSON.parse({json.dumps(payload)}));'
            'return true;'
            '})()'
        )
        self.web_view.runJavaScript(script, self._on_initialized)

    def _on_initialized(self, initialized):
        if not initialized:
            self.status_label.setText(tr('Не удалось загрузить заметки проекта.'))
            return
        self._ready = True
        self._event_timer.start()
        self.status_label.setText(tr('Все изменения сохранены.'))
        self._poll_events()

    def _poll_events(self):
        if not self._ready or self._poll_in_flight:
            return
        self._poll_in_flight = True
        self.web_view.runJavaScript(
            'window.nfprogressNotes.takeEvents()',
            self._process_events,
        )

    def _process_events(self, payload):
        self._poll_in_flight = False
        if not isinstance(payload, str):
            return False
        try:
            events = json.loads(payload)
        except (TypeError, ValueError):
            return False
        successful = True
        for event in events if isinstance(events, list) else []:
            try:
                self._process_event(event)
            except (PermissionError, TypeError, ValueError, OSError) as error:
                successful = False
                self.status_label.setText(tr('Не удалось сохранить заметку.'))
                self.status_label.setToolTip(str(error))
                self._send_error(str(error))
            else:
                if isinstance(event, dict) and event.get('type') in {
                    'createNote', 'updateNote', 'deleteNote', 'updateOrder',
                }:
                    self.status_label.setText(tr('Все изменения сохранены.'))
                    self.status_label.setToolTip('')
        return successful

    def _process_event(self, event: object) -> None:
        if not isinstance(event, dict):
            return
        event_type = event.get('type')
        if event_type == 'ready':
            return
        if event_type == 'createNote':
            self.status_label.setText(tr('Сохранение…'))
            self.service.create_note()
        elif event_type == 'updateNote':
            self.status_label.setText(tr('Сохранение…'))
            self.service.update_note(event.get('id'), event.get('patch'))
        elif event_type == 'deleteNote':
            note = self.service.get_note(event.get('id'))
            if note is None:
                return
            if note['source_type'] == 'mindmap':
                answer = QMessageBox.question(
                    self,
                    'Удаление заметки',
                    'Эта заметка связана с элементом интеллект-карты. '
                    'Она также будет удалена из карты.',
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if answer != QMessageBox.Yes:
                    return
            self.status_label.setText(tr('Сохранение…'))
            self.service.delete_note(note['id'])
        elif event_type == 'updateOrder':
            self.service.update_order(event.get('ids'))
        elif event_type == 'openMindMapNode':
            target = self.service.get_map_target(event.get('id'))
            if target is not None:
                self.open_map_callback(*target)
        elif event_type == 'openExternalLink':
            safe_url = _safe_external_url(event.get('url'))
            if safe_url is not None:
                QDesktopServices.openUrl(QUrl(safe_url))

    def _send_error(self, message: str) -> None:
        if not self._ready:
            return
        payload = json.dumps({'message': message}, ensure_ascii=True)
        self.web_view.runJavaScript(
            f'window.nfprogressNotes.showError({payload})',
        )

    def _on_service_event(self, event_type, payload, origin, revision):
        if not self._ready or self._closing_after_flush:
            return
        event = json.dumps(
            {
                'type': event_type,
                'payload': payload,
                'origin': origin,
                'revision': revision,
            },
            ensure_ascii=True,
        )
        self.web_view.runJavaScript(
            f'window.nfprogressNotes.applyEvent({event})',
        )
        self.status_label.setText(tr('Все изменения сохранены.'))
        self.status_label.setToolTip('')

    def refresh_translations(self) -> None:
        entity_name = self.service.bound_entity.name
        self.retranslateUi(self)
        self.setWindowTitle(f"{tr('Заметки проекта')} — {entity_name}")
        self.notes_title_label.setText(f"{tr('Заметки проекта')}: {entity_name}")
        if not self._ready:
            return
        self.service.refresh_from_storage('database')
        payload = json.dumps(
            {'labels': self._labels(), 'locale': current_language()},
            ensure_ascii=True,
        )
        self.web_view.runJavaScript(
            f'window.nfprogressNotes.updateTranslations({payload})',
        )
        self.web_view.setAccessibleName(tr('Редактор заметок проекта'))
        self.status_label.setText(tr('Все изменения сохранены.'))

    def refresh_from_storage(self, origin: str = 'database') -> None:
        self.service.refresh_from_storage(origin)

    def event(self, event: QEvent) -> bool:
        result = super().event(event)
        if (
            event.type() in {
                QEvent.Type.ApplicationPaletteChange,
                QEvent.Type.PaletteChange,
            }
            and getattr(self, '_ready', False)
        ):
            theme = json.dumps(_palette_payload(self))
            QTimer.singleShot(
                0,
                lambda: self.web_view.runJavaScript(
                    f'window.nfprogressNotes.themeChanged({theme})',
                ),
            )
        return result

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if getattr(self, '_ready', False):
            self._resize_update_timer.start()

    def _notify_viewport_changed(self) -> None:
        if self._ready:
            self.web_view.runJavaScript(
                'window.nfprogressNotes.viewportChanged()',
            )

    def _finish_close_flush(self, payload=None) -> None:
        if (
            self._allow_close
            or not self._closing_after_flush
            or (
                payload is None
                and not self._close_flush_in_flight
            )
        ):
            return
        self._close_flush_in_flight = False
        if not self._process_events(payload):
            self._closing_after_flush = False
            self.status_label.setText(tr('Не удалось сохранить заметку.'))
            self._event_timer.start()
            return
        self._ready = False
        self._allow_close = True
        QTimer.singleShot(0, self.close)

    def _request_close_flush(self) -> None:
        if self._allow_close or self._close_flush_in_flight:
            return
        if self._poll_in_flight:
            QTimer.singleShot(20, self._request_close_flush)
            return
        self._close_flush_in_flight = True
        self.web_view.runJavaScript(
            'window.nfprogressNotes.flushAndTakeEvents()',
            self._finish_close_flush,
        )
        QTimer.singleShot(1500, self._finish_close_flush)

    def closeEvent(self, event: QCloseEvent):
        if (
            self._ready
            and not self._allow_close
            and hasattr(self, 'web_view')
        ):
            event.ignore()
            if self._closing_after_flush:
                return
            self._closing_after_flush = True
            self._event_timer.stop()
            self._request_close_flush()
            return

        if hasattr(self, '_event_timer'):
            self._event_timer.stop()
        if hasattr(self, 'web_view'):
            self.web_view.shutdown()
        super().closeEvent(event)
