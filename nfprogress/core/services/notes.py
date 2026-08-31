"""Qt-independent project notes and Mind Elixir application service.

The legacy application stores project and stage objects in a pickle envelope.
This module deliberately works through a repository boundary and projects only
JSON-safe dictionaries.  Mind-map text remains canonical in ``mindmap_data``;
the note record stores only the stable link and card metadata.
"""

from __future__ import annotations

import hashlib
import html
import re
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Callable, Protocol
from urllib.parse import urlparse

import engine

from nfprogress.core.errors import ConflictError, NotFoundError, ValidationError


SYSTEM_MAP_TAG = 'карта'
MAX_TITLE_LENGTH = 500
MAX_CONTENT_LENGTH = 300_000
MAX_CHECKLIST_ITEM_LENGTH = 2_000
ALLOWED_LINK_SCHEMES = {'http', 'https', 'mailto'}
ALLOWED_HTML_TAGS = {
    'a', 'b', 'br', 'div', 'em', 'i', 'li', 'ol', 'p', 's', 'strike',
    'strong', 'u', 'ul',
}


class ProjectsRepository(Protocol):
    """Small persistence contract required by :class:`ProjectNotesService`."""

    def read_projects(self) -> dict[str, Any]: ...

    def write_projects(self, data: dict[str, Any]) -> None: ...

    def update_projects(
            self,
            mutator: Callable[[dict[str, Any]], Any],
    ) -> Any: ...


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
    """Small allow-list sanitizer for rich note text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag not in ALLOWED_HTML_TAGS:
            return
        if tag == 'a':
            href = next(
                (value for name, value in attrs if name.lower() == 'href'),
                None,
            )
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
        if tag in ALLOWED_HTML_TAGS and tag != 'br':
            self.parts.append(f'</{tag}>')

    def handle_data(self, data: str) -> None:
        self.parts.append(html.escape(data))


def sanitize_note_html(value: object) -> str:
    """Return safe, length-bounded HTML for a regular project note."""
    source = value if isinstance(value, str) else str(value or '')
    sanitizer = _NoteHtmlSanitizer()
    try:
        sanitizer.feed(source[:MAX_CONTENT_LENGTH])
        sanitizer.close()
    except (TypeError, ValueError):
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
    """Convert note HTML to bounded plain text for search and previews."""
    source = value if isinstance(value, str) else str(value or '')
    parser = _PlainTextExtractor()
    try:
        parser.feed(source[:MAX_CONTENT_LENGTH])
        parser.close()
    except (TypeError, ValueError):
        return source[:MAX_CONTENT_LENGTH]
    text = ''.join(parser.parts).replace('\x00', '')
    return re.sub(r'\n{3,}', '\n\n', text).strip()


def _walk_native_map_notes(nodes: object) -> list[dict[str, str]]:
    notes: list[dict[str, str]] = []
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


def extract_mindmap_notes(mindmap_data: object) -> list[dict[str, str]]:
    """Extract native and legacy floating notes without mutating input."""
    normalized = engine.normalize_mindmap_data(mindmap_data)
    if normalized is None:
        return []

    notes_by_id: dict[str, dict[str, str]] = {}
    for item in normalized.get('nfprogressFloatingItems', []):
        if item.get('kind') == 'note':
            notes_by_id[item['id']] = {
                'id': item['id'],
                'text': item['text'],
            }
    for note in _walk_native_map_notes(normalized.get('freeNodes', [])):
        notes_by_id[note['id']] = note
    return list(notes_by_id.values())


def _find_native_note(nodes: object, node_id: str) -> dict | None:
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
    """Update a linked map note and return a normalized map copy."""
    normalized = engine.normalize_mindmap_data(mindmap_data)
    if normalized is None:
        return None
    clean_text = str(text).replace('\x00', '')[:MAX_CONTENT_LENGTH]
    native_note = _find_native_note(
        normalized.get('freeNodes', []),
        source_node_id,
    )
    if native_note is not None:
        native_note['topic'] = clean_text
        return normalized
    for item in normalized.get('nfprogressFloatingItems', []):
        if item.get('id') == source_node_id and item.get('kind') == 'note':
            item['text'] = clean_text
            return normalized
    return None


def _collect_node_ids(node: dict) -> set[str]:
    identifiers: set[str] = set()
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
    """Remove a linked note and map relationships owned by its subtree."""
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


def _normalize_tags(value: object) -> list[str]:
    tags: list[str] = []
    seen: set[str] = set()
    for raw_tag in value if isinstance(value, list) else []:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.replace('\x00', '').strip().lstrip('#').strip()[:64]
        key = tag.casefold()
        if not tag or key == SYSTEM_MAP_TAG or key in seen:
            continue
        seen.add(key)
        tags.append(tag)
    return tags


def _normalize_checklist(value: object) -> list[dict]:
    checklist: list[dict] = []
    seen_ids: set[str] = set()
    for raw_item in value if isinstance(value, list) else []:
        if not isinstance(raw_item, dict):
            continue
        item_id = raw_item.get('id')
        if not isinstance(item_id, str) or not item_id or item_id in seen_ids:
            item_id = uuid.uuid4().hex
        item_text = raw_item.get('text', '')
        checklist.append({
            'id': item_id,
            'text': str(item_text).replace('\x00', '')[
                :MAX_CHECKLIST_ITEM_LENGTH
            ],
            'checked': bool(raw_item.get('checked', False)),
        })
        seen_ids.add(item_id)
    return checklist[:500]


def _is_stage(entity: object) -> bool:
    return bool(getattr(entity, 'is_stage', False))


def _has_stages(project: object) -> bool:
    has_stages = getattr(project, 'has_stages', None)
    if callable(has_stages):
        return bool(has_stages())
    return bool(
        getattr(project, 'enable_stages', False)
        and getattr(project, 'stages', [])
    )


def _map_root_id(entity: object) -> str | None:
    normalized = engine.normalize_mindmap_data(
        getattr(entity, 'mindmap_data', None),
    )
    return normalized['nodeData']['id'] if normalized is not None else None


def _derived_map_title(text: str) -> str:
    first_line = next(
        (line.strip() for line in text.splitlines() if line.strip()),
        '',
    )
    return first_line[:100] or 'Заметка карты'


class ProjectNotesService:
    """Synchronize project-note records and Mind Elixir data.

    ``project_id`` always identifies the parent project.  Passing ``stage_id``
    narrows the service to that stage; omitting it produces the project view,
    including aggregate stage cards when the project has stages.
    """

    def __init__(
            self,
            repository: ProjectsRepository,
            project_id: str,
            stage_id: str | None = None,
            *,
            developer_mode: bool = False,
    ) -> None:
        if not isinstance(project_id, str) or not project_id:
            raise ValidationError('Некорректный идентификатор проекта.')
        if stage_id is not None and (
                not isinstance(stage_id, str) or not stage_id
        ):
            raise ValidationError('Некорректный идентификатор этапа.')
        self.repository = repository
        self.project_id = project_id
        self.stage_id = stage_id
        self.developer_mode = bool(developer_mode)
        self._cache: dict[str, dict] = {}
        self._map_commands: list[dict[str, str]] = []

    @property
    def entity_key(self) -> tuple[str, str]:
        if self.stage_id is not None:
            return 'stage', self.stage_id
        return 'project', self.project_id

    @property
    def last_map_command(self) -> dict[str, str] | None:
        return deepcopy(self._map_commands[-1]) if self._map_commands else None

    def consume_map_commands(self) -> list[dict[str, str]]:
        """Return and clear UI synchronization commands produced by CRUD."""
        commands = deepcopy(self._map_commands)
        self._map_commands.clear()
        return commands

    def _resolve(self, data: dict[str, Any]) -> tuple[object, object]:
        projects = data.get('projects', {}) if isinstance(data, dict) else {}
        if not isinstance(projects, dict):
            raise ValidationError('Хранилище проектов повреждено.')
        project = next(
            (
                item for item in projects.values()
                if getattr(item, 'project_id', None) == self.project_id
            ),
            None,
        )
        if project is None:
            raise NotFoundError('Проект больше не существует.')
        if self.stage_id is None:
            return project, project
        stage = next(
            (
                item for item in getattr(project, 'stages', [])
                if getattr(item, 'stage_id', None) == self.stage_id
            ),
            None,
        )
        if stage is None:
            raise NotFoundError('Этап больше не существует.')
        return project, stage

    def project_scope_id(self) -> str:
        data = self.repository.read_projects()
        project, _ = self._resolve(data)
        return str(project.project_id)

    def _is_aggregate_view(self, project: object, entity: object) -> bool:
        return entity is project and _has_stages(project)

    def _view_entities(
            self,
            project: object,
            entity: object,
    ) -> list[tuple[object, str | None]]:
        owners: list[tuple[object, str | None]] = [(entity, None)]
        if self._is_aggregate_view(project, entity):
            owners.extend(
                (stage, str(stage.name))
                for stage in getattr(project, 'stages', [])
            )
        return owners

    @staticmethod
    def _owner_identity(entity: object) -> tuple[str, str | None]:
        if _is_stage(entity):
            return 'stage', getattr(entity, 'stage_id', None)
        return 'project', getattr(entity, 'project_id', None)

    def _view_note_id(
            self,
            entity: object,
            record_id: str,
            aggregate: bool,
    ) -> str:
        if not aggregate:
            return record_id
        owner_type, owner_id = self._owner_identity(entity)
        return f'{owner_type}:{owner_id}:{record_id}'

    def _is_read_only(self, entity: object) -> bool:
        if getattr(entity, 'status', None) != 'завершен':
            return False
        return _is_stage(entity) or not self.developer_mode

    def _require_writable(self, entity: object) -> None:
        if self._is_read_only(entity):
            raise ValidationError(
                'Заметки завершённого проекта доступны только для просмотра.'
            )

    def _new_map_record(
            self,
            source_node_id: str,
            map_id: str | None,
            order: int,
    ) -> dict:
        digest = hashlib.sha256(
            source_node_id.encode('utf-8'),
        ).hexdigest()[:28]
        now = _now_iso()
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
            'created_at': now,
            'updated_at': now,
            'revision': 0,
        }

    def _reconcile(
            self,
            entity: object,
            *,
            aggregate: bool,
            detect_cached_changes: bool = True,
    ) -> bool:
        records = engine.normalize_project_note_records(
            getattr(entity, 'project_notes', []),
        )
        map_notes = {
            note['id']: note['text']
            for note in extract_mindmap_notes(
                getattr(entity, 'mindmap_data', None),
            )
        }
        map_id = _map_root_id(entity)
        by_source = {
            record['source_node_id']: record
            for record in records
            if record['source_type'] == 'mindmap'
        }
        changed = records != getattr(entity, 'project_notes', [])
        next_order = max(
            (record['sort_order'] for record in records),
            default=-1,
        ) + 1
        for source_node_id, text in map_notes.items():
            record = by_source.get(source_node_id)
            if record is None:
                record = self._new_map_record(
                    source_node_id,
                    map_id,
                    next_order,
                )
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
            if (
                    detect_cached_changes
                    and cached is not None
                    and cached.get('content') != text
            ):
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
        if changed:
            self._touch_notes(entity)
        return changed

    def _reconcile_view(self, project: object, entity: object) -> bool:
        aggregate = self._is_aggregate_view(project, entity)
        changed = False
        for owner, _stage_name in self._view_entities(project, entity):
            if self._reconcile(owner, aggregate=aggregate):
                changed = True
        return changed

    def _project_note(
            self,
            entity: object,
            record: dict,
            *,
            aggregate: bool,
            stage_name: str | None = None,
            owner_order: int = 0,
            map_notes: dict[str, str] | None = None,
    ) -> dict:
        result = deepcopy(record)
        result['id'] = self._view_note_id(entity, record['id'], aggregate)
        owner_type, owner_id = self._owner_identity(entity)
        result['owner_type'] = owner_type
        result['owner_id'] = owner_id
        result['owner_order'] = owner_order
        result['stage_name'] = stage_name if aggregate else None
        if record['source_type'] == 'mindmap':
            if map_notes is None:
                map_notes = {
                    note['id']: note['text']
                    for note in extract_mindmap_notes(
                        getattr(entity, 'mindmap_data', None),
                    )
                }
            result['content'] = map_notes.get(record['source_node_id'], '')
            result['display_title'] = (
                record['title'] or _derived_map_title(result['content'])
            )
            result['system_tags'] = [SYSTEM_MAP_TAG]
        else:
            result['content'] = sanitize_note_html(record['content'])
            result['display_title'] = record['title']
            result['system_tags'] = []
        result['read_only'] = self._is_read_only(entity)
        return result

    def _project_all(self, project: object, entity: object) -> list[dict]:
        aggregate = self._is_aggregate_view(project, entity)
        projected: list[tuple[int, dict]] = []
        for owner_index, (owner, stage_name) in enumerate(
                self._view_entities(project, entity)
        ):
            map_notes: dict[str, str] = {}
            if any(
                    record['source_type'] == 'mindmap'
                    for record in getattr(owner, 'project_notes', [])
            ):
                map_notes = {
                    note['id']: note['text']
                    for note in extract_mindmap_notes(
                        getattr(owner, 'mindmap_data', None),
                    )
                }
            projected.extend(
                (
                    owner_index,
                    self._project_note(
                        owner,
                        record,
                        aggregate=aggregate,
                        stage_name=stage_name,
                        owner_order=owner_index,
                        map_notes=map_notes,
                    ),
                )
                for record in getattr(owner, 'project_notes', [])
            )
        projected.sort(key=lambda item: (
            item[1]['archived'],
            not item[1]['pinned'],
            item[1]['sort_order'],
            item[1]['created_at'],
            item[0],
        ))
        return [note for _owner_index, note in projected]

    def _remember(self, notes: list[dict]) -> None:
        self._cache = {note['id']: deepcopy(note) for note in notes}

    def _load_reconciled(self) -> tuple[object, object]:
        def reconcile(data: dict[str, Any]) -> tuple[object, object]:
            project, entity = self._resolve(data)
            self._reconcile_view(project, entity)
            return project, entity

        # Reconciliation may normalize stored note/map links. Keep that read,
        # mutation, and write in one repository transaction so an ordinary GET
        # cannot overwrite a concurrent progress or project update.
        return self.repository.update_projects(reconcile)

    def view_context(self) -> dict:
        data = self.repository.read_projects()
        project, entity = self._resolve(data)
        if not self._is_aggregate_view(project, entity):
            return {'hasStages': False, 'stages': []}
        stages = [
            {'id': str(stage.stage_id), 'name': str(stage.name)}
            for stage in getattr(project, 'stages', [])
            if getattr(stage, 'stage_id', None)
        ]
        return {'hasStages': bool(stages), 'stages': stages}

    def load_notes(self) -> dict:
        project, entity = self._load_reconciled()
        notes = self._project_all(project, entity)
        self._remember(notes)
        return {
            'notes': notes,
            'read_only': self._is_read_only(entity),
            'context': self._view_context_for(project, entity),
        }

    def list_notes(self) -> dict:
        return self.load_notes()

    def refresh_from_storage(self, origin: str = 'database') -> dict:
        # ``origin`` remains accepted for callers shared with the legacy bridge.
        del origin
        return self.load_notes()

    def _view_context_for(self, project: object, entity: object) -> dict:
        if not self._is_aggregate_view(project, entity):
            return {'hasStages': False, 'stages': []}
        stages = [
            {'id': str(stage.stage_id), 'name': str(stage.name)}
            for stage in getattr(project, 'stages', [])
            if getattr(stage, 'stage_id', None)
        ]
        return {'hasStages': bool(stages), 'stages': stages}

    def _find_record(
            self,
            project: object,
            entity: object,
            note_id: str,
    ) -> tuple[object | None, dict | None, str | None]:
        aggregate = self._is_aggregate_view(project, entity)
        for owner, stage_name in self._view_entities(project, entity):
            for record in getattr(owner, 'project_notes', []):
                if self._view_note_id(owner, record['id'], aggregate) == note_id:
                    return owner, record, stage_name
        return None, None, None

    def get_note(self, note_id: str) -> dict | None:
        project, entity = self._load_reconciled()
        owner, record, stage_name = self._find_record(
            project,
            entity,
            note_id,
        )
        if owner is None or record is None:
            return None
        return self._project_note(
            owner,
            record,
            aggregate=self._is_aggregate_view(project, entity),
            stage_name=stage_name,
        )

    def get_map_target(self, note_id: str) -> dict | None:
        project, entity = self._load_reconciled()
        owner, record, _stage_name = self._find_record(
            project,
            entity,
            note_id,
        )
        if (
                owner is None
                or record is None
                or record['source_type'] != 'mindmap'
        ):
            return None
        return {
            'project_id': str(project.project_id),
            'stage_id': (
                str(owner.stage_id) if _is_stage(owner) else None
            ),
            'node_id': record['source_node_id'],
        }

    def create_note(self) -> dict:
        self._map_commands.clear()

        def mutate(data: dict[str, Any]) -> dict:
            project, entity = self._resolve(data)
            self._require_writable(entity)
            self._reconcile_view(project, entity)
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
                        for owner, _stage_name in self._view_entities(
                            project,
                            entity,
                        )
                        for item in getattr(owner, 'project_notes', [])
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
            self._touch_notes(entity)
            notes = self._project_all(project, entity)
            view_id = self._view_note_id(
                entity,
                record['id'],
                self._is_aggregate_view(project, entity),
            )
            self._remember(notes)
            return next(note for note in notes if note['id'] == view_id)

        return self.repository.update_projects(mutate)

    def update_note(self, note_id: str, patch: object) -> dict:
        if not isinstance(patch, dict):
            raise ValidationError('Некорректные данные заметки.')
        self._map_commands.clear()

        def mutate(data: dict[str, Any]) -> dict:
            project, entity = self._resolve(data)
            self._reconcile_view(project, entity)
            owner, record, stage_name = self._find_record(
                project,
                entity,
                note_id,
            )
            if owner is None or record is None:
                raise NotFoundError('Заметка больше не существует.')
            self._require_writable(owner)

            changed = False
            map_text_changed = False
            if 'title' in patch:
                title = str(patch.get('title') or '').replace(
                    '\x00',
                    '',
                )[:MAX_TITLE_LENGTH]
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
                    text = str(patch.get('content') or '').replace(
                        '\x00',
                        '',
                    )[:MAX_CONTENT_LENGTH]
                    current = next(
                        (
                            note['text']
                            for note in extract_mindmap_notes(
                                getattr(owner, 'mindmap_data', None),
                            )
                            if note['id'] == record['source_node_id']
                        ),
                        None,
                    )
                    if current is None:
                        raise ConflictError(
                            'Связанная заметка карты больше не существует.'
                        )
                    if text != current:
                        updated_map = set_mindmap_note_text(
                            owner.mindmap_data,
                            record['source_node_id'],
                            text,
                        )
                        if updated_map is None:
                            raise ConflictError(
                                'Не удалось обновить заметку карты.'
                            )
                        owner.mindmap_data = updated_map
                        self._touch_mindmap(owner)
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
                self._touch_notes(owner)
            note = self._project_note(
                owner,
                record,
                aggregate=self._is_aggregate_view(project, entity),
                stage_name=stage_name,
            )
            if map_text_changed:
                self._map_commands.append({
                    'command': 'update',
                    'node_id': record['source_node_id'],
                    'text': note['content'],
                })
            self._remember(self._project_all(project, entity))
            return note

        return self.repository.update_projects(mutate)

    def delete_note(self, note_id: str) -> dict:
        self._map_commands.clear()

        def mutate(data: dict[str, Any]) -> dict:
            project, entity = self._resolve(data)
            self._reconcile_view(project, entity)
            owner, record, _stage_name = self._find_record(
                project,
                entity,
                note_id,
            )
            if owner is None or record is None:
                notes = self._project_all(project, entity)
                self._remember(notes)
                return {'deleted': False, 'id': note_id, 'notes': notes}
            self._require_writable(owner)
            self._touch_notes(owner)
            source_node_id = record['source_node_id']
            if record['source_type'] == 'mindmap':
                updated_map = remove_mindmap_note(
                    owner.mindmap_data,
                    source_node_id,
                )
                if updated_map is None:
                    raise ConflictError(
                        'Связанная заметка карты больше не существует.'
                    )
                owner.mindmap_data = updated_map
                self._touch_mindmap(owner)
            owner.project_notes = [
                item for item in owner.project_notes
                if item['id'] != record['id']
            ]
            if source_node_id:
                self._map_commands.append({
                    'command': 'delete',
                    'node_id': source_node_id,
                    'text': '',
                })
            notes = self._project_all(project, entity)
            self._remember(notes)
            return {'deleted': True, 'id': note_id, 'notes': notes}

        return self.repository.update_projects(mutate)

    def update_order(self, note_ids: object) -> dict:
        if not isinstance(note_ids, list):
            return {'changed': False, 'notes': self.load_notes()['notes']}

        def mutate(data: dict[str, Any]) -> dict:
            project, entity = self._resolve(data)
            self._require_writable(entity)
            self._reconcile_view(project, entity)
            order_by_id = {
                note_id: index
                for index, note_id in enumerate(note_ids)
                if isinstance(note_id, str)
            }
            aggregate = self._is_aggregate_view(project, entity)
            changed = False
            for owner, _stage_name in self._view_entities(project, entity):
                if self._is_read_only(owner):
                    continue
                for record in owner.project_notes:
                    view_id = self._view_note_id(
                        owner,
                        record['id'],
                        aggregate,
                    )
                    if view_id not in order_by_id:
                        continue
                    order = order_by_id[view_id]
                    if record['sort_order'] != order:
                        record['sort_order'] = order
                        record['updated_at'] = _now_iso()
                        record['revision'] += 1
                        self._touch_notes(owner)
                        changed = True
            notes = self._project_all(project, entity)
            self._remember(notes)
            return {'changed': changed, 'notes': notes}

        return self.repository.update_projects(mutate)

    def _mindmap_payload(self, project: object, entity: object) -> dict:
        combined = bool(
            entity is project
            and _has_stages(project)
            and getattr(project, 'combine_stage_mindmaps', False)
        )
        map_data = (
            engine.compose_project_mindmap(project)
            if combined
            else engine.normalize_mindmap_data(
                getattr(entity, 'mindmap_data', None),
            )
        )
        return {
            'project_id': str(project.project_id),
            'stage_id': (
                str(entity.stage_id) if _is_stage(entity) else None
            ),
            'name': str(entity.name),
            'data': deepcopy(map_data),
            'combined': combined,
            'read_only': self._is_read_only(entity),
            'has_empty_completed_stage_map': bool(
                combined
                and any(
                    getattr(stage, 'status', None) == 'завершен'
                    and not engine.mindmap_has_content(
                        getattr(stage, 'mindmap_data', None),
                        str(stage.name),
                    )
                    for stage in getattr(project, 'stages', [])
                )
            ),
        }

    def get_mindmap(self) -> dict:
        data = self.repository.read_projects()
        project, entity = self._resolve(data)
        return self._mindmap_payload(project, entity)

    @staticmethod
    def _bump_map_record_revisions(
            entity: object,
            old_notes: dict[str, str],
    ) -> None:
        new_notes = {
            note['id']: note['text']
            for note in extract_mindmap_notes(
                getattr(entity, 'mindmap_data', None),
            )
        }
        now = _now_iso()
        for record in getattr(entity, 'project_notes', []):
            if record.get('source_type') != 'mindmap':
                continue
            source_id = record.get('source_node_id')
            if (
                    source_id in old_notes
                    and source_id in new_notes
                    and old_notes[source_id] != new_notes[source_id]
            ):
                record['updated_at'] = now
                record['revision'] += 1

    @staticmethod
    def _touch_mindmap(entity: object) -> None:
        """Remember the last successful modification of an entity's map."""
        entity.mindmap_updated_at = _now_iso()

    @staticmethod
    def _touch_notes(entity: object) -> None:
        """Remember note changes even when the last note is deleted."""
        entity.notes_updated_at = _now_iso()

    def update_mindmap(self, mindmap_data: object) -> dict:
        """Validate and persist a map, then reconcile its linked note cards."""
        normalized = engine.normalize_mindmap_data(mindmap_data)
        if normalized is None:
            raise ValidationError('Редактор вернул повреждённые данные карты.')
        self._map_commands.clear()

        def mutate(data: dict[str, Any]) -> dict:
            project, entity = self._resolve(data)
            self._require_writable(entity)
            combined = bool(
                entity is project
                and _has_stages(project)
                and getattr(project, 'combine_stage_mindmaps', False)
            )
            affected = [entity]
            old_maps_by_owner = {
                id(entity): engine.normalize_mindmap_data(
                    getattr(entity, 'mindmap_data', None),
                ),
            }
            old_notes_by_owner = {
                id(entity): {
                    note['id']: note['text']
                    for note in extract_mindmap_notes(
                        getattr(entity, 'mindmap_data', None),
                    )
                },
            }
            if combined:
                try:
                    project_map, stage_maps = (
                        engine.split_combined_project_mindmap(
                            project,
                            normalized,
                        )
                    )
                except ValueError as error:
                    raise ValidationError(
                        'Редактор вернул повреждённые данные карты.'
                    ) from error
                project.mindmap_data = project_map
                affected = [project]
                for stage in getattr(project, 'stages', []):
                    stage_map = stage_maps.get(getattr(stage, 'stage_id', None))
                    if stage_map is None or self._is_read_only(stage):
                        continue
                    old_maps_by_owner[id(stage)] = engine.normalize_mindmap_data(
                        getattr(stage, 'mindmap_data', None),
                    )
                    old_notes_by_owner[id(stage)] = {
                        note['id']: note['text']
                        for note in extract_mindmap_notes(
                            getattr(stage, 'mindmap_data', None),
                        )
                    }
                    stage.mindmap_data = stage_map
                    affected.append(stage)
            else:
                entity.mindmap_data = normalized

            aggregate = self._is_aggregate_view(project, entity)
            for owner in affected:
                new_map = engine.normalize_mindmap_data(
                    getattr(owner, 'mindmap_data', None),
                )
                if old_maps_by_owner.get(id(owner)) != new_map:
                    self._touch_mindmap(owner)
                self._bump_map_record_revisions(
                    owner,
                    old_notes_by_owner.get(id(owner), {}),
                )
                self._reconcile(
                    owner,
                    aggregate=aggregate,
                    detect_cached_changes=False,
                )
            notes = self._project_all(project, entity)
            self._remember(notes)
            result = self._mindmap_payload(project, entity)
            result['notes'] = notes
            return result

        return self.repository.update_projects(mutate)

    def save_mindmap(self, mindmap_data: object) -> dict:
        return self.update_mindmap(mindmap_data)

    def update_map(self, mindmap_data: object) -> dict:
        """API-friendly alias for :meth:`update_mindmap`."""
        return self.update_mindmap(mindmap_data)


__all__ = [
    'ProjectNotesService',
    'ProjectsRepository',
    'extract_mindmap_notes',
    'note_html_to_plain_text',
    'remove_mindmap_note',
    'sanitize_note_html',
    'set_mindmap_note_text',
]
