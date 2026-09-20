"""Relational shadow mirror populated from the authoritative pickle stores."""

from __future__ import annotations

import json
import hashlib
import logging
import math
import uuid
from collections.abc import Mapping
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

from nfprogress.core.serialization import serialize_project, to_json_safe
from nfprogress.core.sqlite.connection import database_path, open_database
from nfprogress.core.sqlite.ordering import validate_order_invariants
from nfprogress.core.sqlite.ownership import (
    StorageOwner,
    StorageOwnershipRepository,
    Subsystem,
)


LOGGER = logging.getLogger(__name__)


def _legacy_json(value: Any, seen: set[int] | None = None) -> Any:
    """Serialize legacy objects as data, never as Python-specific metadata."""
    if seen is None:
        seen = set()
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _legacy_json(item, seen) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_legacy_json(item, seen) for item in value]
    if isinstance(value, (set, frozenset)):
        return [_legacy_json(item, seen) for item in sorted(value, key=repr)]
    if hasattr(value, '__dict__'):
        marker = id(value)
        if marker in seen:
            return None
        seen.add(marker)
        result = {str(key): _legacy_json(item, seen) for key, item in vars(value).items()}
        seen.remove(marker)
        return result
    try:
        return to_json_safe(value)
    except TypeError:
        return None


def _json(value: Any) -> str:
    return json.dumps(_legacy_json(value), ensure_ascii=False, allow_nan=False, sort_keys=True)


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec='seconds')


def _canonical_game_payload(gamer: Any, projects: Mapping[str, Any]) -> dict[str, Any]:
    # Lazy import avoids a package-initialization cycle through sqlite.__init__.
    from nfprogress.core.game_state import _game_payload

    return _game_payload(gamer, projects)


class SQLiteMirrorRepository:
    """Write-only/read-for-verification SQLite representation of PKL state."""

    def __init__(self, data_root: str | Path) -> None:
        self.data_root = Path(data_root).expanduser().resolve()
        self.ownership = StorageOwnershipRepository(self.data_root)

    @property
    def path(self) -> Path:
        return database_path(self.data_root)

    def set_status(self, status: str, error: str | None = None) -> None:
        with open_database(self.data_root) as db:
            db.execute(
                "INSERT INTO mirror_state(id, source_format, source_schema_version, "
                "sync_status, last_error) VALUES(1, 'pickle', 'legacy', ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET sync_status=excluded.sync_status, "
                "last_error=excluded.last_error",
                (status, error),
            )

    def rebuild(
            self, projects: dict[str, Any], settings: dict[str, Any], gamer: Any,
            documents: Mapping[str, Any] | None = None,
    ) -> None:
        """Synchronize only domains whose authoritative source is pickle.

        Each domain commits independently. This keeps a failed domain from
        rolling back successful domains and, importantly, never writes a
        SQLite-owned domain.
        """
        owners = self.ownership.owners()
        now = _now()
        if owners[Subsystem.PROJECTS] == StorageOwner.PICKLE:
            self.sync_projects(projects)
        if owners[Subsystem.SETTINGS] == StorageOwner.PICKLE:
            self.sync_settings(settings)
        if owners[Subsystem.NOTES] == StorageOwner.PICKLE:
            self.sync_notes(projects)
        if owners[Subsystem.GAME] == StorageOwner.PICKLE:
            self.sync_game(projects, gamer)
        self.sync_documents(projects, documents or {})

        with open_database(self.data_root) as db:
            self._verify(db, projects, settings, gamer, documents or {}, owners)
            with db:
                db.execute(
                    "INSERT INTO mirror_state(id,source_format,source_schema_version,last_full_sync_at,last_successful_sync_at,sync_status,last_error) "
                    "VALUES(1,'pickle','legacy',?,?, 'healthy',NULL) ON CONFLICT(id) DO UPDATE SET "
                    "last_full_sync_at=excluded.last_full_sync_at,last_successful_sync_at=excluded.last_successful_sync_at,"
                    "sync_status='healthy',last_error=NULL",
                    (now, now),
                )

    def sync_projects(self, projects: dict[str, Any]) -> None:
        """Synchronize the projects domain: projects, stages and progress."""
        project_rows: list[tuple[Any, ...]] = []
        stage_rows: list[tuple[Any, ...]] = []
        stage_order_rows: list[tuple[str, str, int]] = []
        stage_positions: dict[str, int] = {}
        progress_rows: list[tuple[Any, ...]] = []
        progress_order_rows: list[tuple[str, int]] = []
        binding_rows: list[tuple[Any, ...]] = []
        extension_rows: list[tuple[str, str, str]] = []
        project_map = projects.get('projects', {}) if isinstance(projects, dict) else {}
        progress_position = 0
        for project in project_map.values() if isinstance(project_map, Mapping) else []:
            payload = serialize_project(project)
            project_id = payload['id']
            project_rows.append(self._entity_row(project_id, payload))
            extension_rows.append(self._extension_row('project', project_id, project))
            binding_rows.extend(self._binding_rows(project, project_id, None))
            for stage in payload.get('stages', []):
                stage_rows.append(self._entity_row(stage['id'], stage, project_id))
                stage_position = stage_positions.get(project_id, 0)
                stage_order_rows.append((stage['id'], project_id, stage_position))
                stage_positions[project_id] = stage_position + 1
                stage_object = next(
                    (item for item in getattr(project, 'stages', [])
                     if getattr(item, 'stage_id', None) == stage['id']),
                    None,
                )
                if stage_object is not None:
                    extension_rows.append(self._extension_row('stage', stage['id'], stage_object))
                    extension_rows.extend(self._progress_extension_rows(stage_object))
                    binding_rows.extend(self._binding_rows(stage_object, project_id, stage['id']))
                progress_position = self._rows_for_entity(
                    progress_rows, progress_order_rows, stage, project_id,
                    stage['id'], progress_position,
                )
            progress_position = self._rows_for_entity(
                progress_rows, progress_order_rows, payload, project_id, None,
                progress_position,
            )
            extension_rows.extend(self._progress_extension_rows(project))

        project_ids = [row[0] for row in project_rows]
        order_rows = [
            (project_id, position)
            for position, project_id in enumerate(
                self._normalized_project_order(projects, project_ids),
            )
        ]

        folders = self._folder_rows(projects)
        folder_ids = {row[0] for row in folders}
        folder_members = [
            (project.project_id, project.folder_id)
            for project in (project_map.values() if isinstance(project_map, Mapping) else [])
            if isinstance(getattr(project, 'folder_id', None), str)
            and project.folder_id in folder_ids
        ]
        root_fields = {
            'projects', 'project_order', 'project_folders', 'last',
            'notifications', 'global_streaks', 'global_streak_status',
            'max_global_streak', 'last_global_streak_bonus',
            'last_global_streak_lost_date', 'last_global_streak_lose_len',
        }
        root_extensions = {
            key: value for key, value in projects.items()
            if key not in root_fields
        } if isinstance(projects, Mapping) else {}
        metadata_rows = [
            ('project_last', _json(projects.get('last'))),
            ('root_extensions', _json(root_extensions)),
        ]

        preserve_notes = self.ownership.get_owner(Subsystem.NOTES) == StorageOwner.SQLITE
        with open_database(self.data_root) as db:
            with db:
                preserved_notes = (
                    db.execute(
                        'SELECT id, project_id, stage_id, updated_at, payload_json FROM notes',
                    ).fetchall()
                    if preserve_notes else []
                )
                if preserve_notes:
                    valid_projects = {row[0] for row in project_rows}
                    valid_stages = {row[0] for row in stage_rows}
                    if any(
                        row['project_id'] not in valid_projects
                        or (row['stage_id'] is not None and row['stage_id'] not in valid_stages)
                        for row in preserved_notes
                    ):
                        raise RuntimeError(
                            'SQLite-owned Notes reference a project aggregate that cannot be rebuilt safely',
                        )
                    # Notes are copied inside this same transaction.  The
                    # explicit delete is required by RESTRICT FKs and is
                    # rolled back together with the rebuild on any failure.
                    db.execute('DELETE FROM notes')
                else:
                    db.execute('DELETE FROM notes')
                db.execute('DELETE FROM progress_entries')
                db.execute('DELETE FROM progress_order')
                db.execute('DELETE FROM project_bindings')
                db.execute('DELETE FROM project_extensions')
                db.execute('DELETE FROM project_folder_members')
                db.execute('DELETE FROM project_folders')
                db.execute('DELETE FROM project_metadata')
                db.execute('DELETE FROM project_order')
                db.execute('DELETE FROM stage_order')
                db.execute('DELETE FROM stages')
                db.execute('DELETE FROM projects')
                db.executemany(
                    'INSERT INTO projects(id,name,goal,infinite,unit,status,created_at,updated_at,payload_json) VALUES(?,?,?,?,?,?,?,?,?)',
                    project_rows,
                )
                db.executemany(
                    'INSERT INTO stages(id,project_id,name,goal,infinite,unit,status,created_at,updated_at,payload_json) VALUES(?,?,?,?,?,?,?,?,?,?)',
                    stage_rows,
                )
                db.executemany(
                    'INSERT INTO stage_order(stage_id,project_id,position) VALUES(?,?,?)',
                    stage_order_rows,
                )
                db.executemany(
                    'INSERT INTO progress_entries(id,project_id,stage_id,created_at,added_symbols,added_progress,payload_json) VALUES(?,?,?,?,?,?,?)',
                    progress_rows,
                )
                db.executemany(
                    'INSERT INTO progress_order(entry_id,position) VALUES(?,?)',
                    progress_order_rows,
                )
                db.executemany(
                    'INSERT INTO project_order(project_id,position) VALUES(?,?)',
                    order_rows,
                )
                validate_order_invariants(db)
                db.executemany(
                    'INSERT INTO project_folders(id,name,position,payload_json) VALUES(?,?,?,?)',
                    folders,
                )
                db.executemany(
                    'INSERT INTO project_folder_members(project_id,folder_id) VALUES(?,?)',
                    folder_members,
                )
                db.executemany(
                    'INSERT INTO project_bindings(id,project_id,stage_id,binding_type,external_path,source_id,content_hash,last_synced_at,payload_json) VALUES(?,?,?,?,?,?,?,?,?)',
                    binding_rows,
                )
                db.executemany(
                    'INSERT INTO project_extensions(entity_type,entity_id,payload_json) VALUES(?,?,?)',
                    extension_rows,
                )
                db.executemany(
                    'INSERT INTO project_metadata(key,value_json) VALUES(?,?)',
                    metadata_rows,
                )
                if preserve_notes and preserved_notes:
                    db.executemany(
                        'INSERT INTO notes(id,project_id,stage_id,updated_at,payload_json) VALUES(?,?,?,?,?)',
                        [tuple(row) for row in preserved_notes],
                    )

    @staticmethod
    def _normalized_project_order(
            projects: Mapping[str, Any], project_ids: list[str],
    ) -> list[str]:
        """Return a complete, deterministic projection of legacy order.

        Unknown and duplicate legacy IDs are discarded; projects missing from
        the legacy list are appended in the pickle mapping's order.  This only
        normalizes the mirror and never changes authoritative PKL data.
        """
        saved_order = projects.get('project_order') if isinstance(projects, Mapping) else None
        known = set(project_ids)
        result: list[str] = []
        if isinstance(saved_order, list):
            for project_id in saved_order:
                if isinstance(project_id, str) and project_id in known and project_id not in result:
                    result.append(project_id)
        result.extend(project_id for project_id in project_ids if project_id not in result)
        return result

    def sync_notes(self, projects: dict[str, Any]) -> None:
        """Synchronize only the notes table, leaving parent rows untouched."""
        note_rows: list[tuple[Any, ...]] = []
        project_map = projects.get('projects', {}) if isinstance(projects, dict) else {}
        for project in project_map.values() if isinstance(project_map, Mapping) else []:
            payload = serialize_project(project)
            project_id = payload['id']
            for stage in payload.get('stages', []):
                self._rows_for_notes(note_rows, stage, project_id, stage['id'])
            self._rows_for_notes(note_rows, payload, project_id, None)
        with open_database(self.data_root) as db:
            with db:
                db.execute('DELETE FROM notes')
                db.executemany(
                    'INSERT INTO notes(id,project_id,stage_id,updated_at,payload_json) VALUES(?,?,?,?,?)',
                    note_rows,
                )

    def sync_settings(self, settings: dict[str, Any]) -> None:
        with open_database(self.data_root) as db:
            with db:
                db.execute('DELETE FROM settings')
                db.executemany(
                    'INSERT INTO settings(key,value_json) VALUES(?,?)',
                    [(str(key), _json(value)) for key, value in settings.items()],
                )

    def sync_game(self, projects: Mapping[str, Any], gamer: Any) -> None:
        payload = _canonical_game_payload(gamer, projects)
        with open_database(self.data_root) as db:
            with db:
                db.execute(
                    'INSERT INTO game_state(id,schema_version,payload_json,updated_at) VALUES(1,2,?,?) '
                    'ON CONFLICT(id) DO UPDATE SET schema_version=excluded.schema_version, '
                    'payload_json=excluded.payload_json, updated_at=excluded.updated_at',
                    (_json(payload), _now()),
                )

    def sync_documents(
            self, projects: Mapping[str, Any], documents: Mapping[str, Any],
    ) -> None:
        document_rows, binding_rows = self._document_rows(projects, documents)
        source_path = self.data_root / 'documents.json'
        checksum = (
            f'sha256:{hashlib.sha256(source_path.read_bytes()).hexdigest()}'
            if source_path.is_file() else None
        )
        with open_database(self.data_root) as db:
            with db:
                db.execute('DELETE FROM document_bindings')
                db.execute('DELETE FROM documents')
                db.execute('DELETE FROM document_migration_orphans')
                db.executemany(
                    'INSERT INTO documents(id,scope_key,project_id,stage_id,title,content_json,'
                    'content_format,created_at,updated_at,revision,extensions_json) '
                    'VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                    document_rows,
                )
                db.executemany(
                    'INSERT INTO document_bindings(id,document_id,binding_type,external_path,'
                    'source_id,last_external_hash,last_synced_revision,last_synced_hash,'
                    'last_synced_at,sync_state,expected_external_hash,payload_json) '
                    'VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                    binding_rows,
                )
                db.execute(
                    "INSERT INTO document_metadata(key,value_json) "
                    "VALUES('documents_json_migration',?) ON CONFLICT(key) DO UPDATE SET "
                    'value_json=excluded.value_json',
                    (_json({'status': 'complete', 'source_checksum': checksum}),),
                )

    def _verify(
            self, db: Any, projects: Mapping[str, Any], settings: Mapping[str, Any],
            gamer: Any, documents: Mapping[str, Any],
            owners: Mapping[Subsystem, StorageOwner],
    ) -> None:
        validate_order_invariants(db)
        integrity = db.execute('PRAGMA integrity_check').fetchall()
        if [row[0] for row in integrity] != ['ok']:
            raise RuntimeError(f'SQLite integrity_check failed: {[row[0] for row in integrity]!r}')
        foreign_keys = db.execute('PRAGMA foreign_key_check').fetchall()
        if foreign_keys:
            raise RuntimeError(f'SQLite foreign_key_check failed: {len(foreign_keys)} violation(s)')

        expected_projects, expected_stages, expected_progress, expected_notes = self._expected_entities(projects)
        comparisons = {
            'projects': (expected_projects, self._payload_map(db, 'projects')),
            'stages': (expected_stages, self._payload_map(db, 'stages')),
            'progress': (expected_progress, self._payload_map(db, 'progress_entries')),
            'notes': (expected_notes, self._payload_map(db, 'notes')),
        }
        if owners[Subsystem.SETTINGS] == StorageOwner.PICKLE:
            actual_settings = {
                row['key']: json.loads(row['value_json'])
                for row in db.execute('SELECT key,value_json FROM settings')
            }
            comparisons['settings'] = (
                {str(key): _legacy_json(value) for key, value in settings.items()},
                actual_settings,
            )
        if owners[Subsystem.GAME] == StorageOwner.PICKLE:
            row = db.execute(
                'SELECT schema_version,payload_json FROM game_state WHERE id=1',
            ).fetchone()
            actual_game = json.loads(row['payload_json']) if row else None
            comparisons['game'] = (
                _legacy_json(_canonical_game_payload(gamer, projects)), actual_game,
            )

        expected_documents, expected_bindings = self._document_rows(projects, documents)
        actual_documents = [tuple(row) for row in db.execute(
            'SELECT id,scope_key,project_id,stage_id,title,content_json,content_format,'
            'created_at,updated_at,revision,extensions_json FROM documents ORDER BY id',
        )]
        actual_bindings = [tuple(row) for row in db.execute(
            'SELECT id,document_id,binding_type,external_path,source_id,last_external_hash,'
            'last_synced_revision,last_synced_hash,last_synced_at,sync_state,'
            'expected_external_hash,payload_json FROM document_bindings ORDER BY id',
        )]
        comparisons['documents'] = (sorted(expected_documents), actual_documents)
        comparisons['document bindings'] = (sorted(expected_bindings), actual_bindings)
        mismatches = [name for name, (expected, actual) in comparisons.items() if expected != actual]
        if mismatches:
            raise RuntimeError(f'SQLite semantic verification failed: {", ".join(mismatches)}')

        marker = db.execute(
            "SELECT value_json FROM document_metadata WHERE key='documents_json_migration'",
        ).fetchone()
        if not marker or json.loads(marker['value_json']).get('status') != 'complete':
            raise RuntimeError('documents migration marker is incomplete')

    @staticmethod
    def _payload_map(db: Any, table: str) -> dict[str, Any]:
        return {
            row['id']: json.loads(row['payload_json'])
            for row in db.execute(f'SELECT id,payload_json FROM {table}')
        }

    def _expected_entities(
            self, projects: Mapping[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
        expected_projects: dict[str, Any] = {}
        expected_stages: dict[str, Any] = {}
        expected_progress: dict[str, Any] = {}
        expected_notes: dict[str, Any] = {}
        project_map = projects.get('projects', {}) if isinstance(projects, Mapping) else {}
        for project in project_map.values() if isinstance(project_map, Mapping) else []:
            payload = serialize_project(project)
            expected_projects[payload['id']] = _legacy_json(payload)
            for stage in payload.get('stages', []):
                expected_stages[stage['id']] = _legacy_json(stage)
                expected_progress.update(
                    (entry['id'], _legacy_json(entry))
                    for entry in stage.get('progress_entries', [])
                )
                expected_notes.update(
                    (note['id'], _legacy_json(note))
                    for note in stage.get('project_notes', []) if note.get('id')
                )
            expected_progress.update(
                (entry['id'], _legacy_json(entry))
                for entry in payload.get('progress_entries', [])
            )
            expected_notes.update(
                (note['id'], _legacy_json(note))
                for note in payload.get('project_notes', []) if note.get('id')
            )
        return expected_projects, expected_stages, expected_progress, expected_notes

    @staticmethod
    def _document_rows(
            projects: Mapping[str, Any], documents: Mapping[str, Any],
    ) -> tuple[list[tuple[Any, ...]], list[tuple[Any, ...]]]:
        project_map = projects.get('projects', {}) if isinstance(projects, Mapping) else {}
        project_ids = {
            getattr(project, 'project_id', None)
            for project in project_map.values() if isinstance(project_map, Mapping)
        }
        stage_ids = {
            getattr(stage, 'stage_id', None)
            for project in project_map.values() if isinstance(project_map, Mapping)
            for stage in getattr(project, 'stages', [])
        }
        known = {
            'document_id', 'id', 'project_id', 'stage_id', 'title', 'content',
            'content_format', 'created_at', 'updated_at', 'exists', 'docx_path',
            'sync_state', 'last_synced_hash', 'last_synced_at', 'local_dirty',
            'word_dirty', 'symbols', 'has_content',
        }
        document_rows: list[tuple[Any, ...]] = []
        binding_rows: list[tuple[Any, ...]] = []
        seen_documents: set[str] = set()
        seen_scopes: set[str] = set()
        for source_key, item in documents.items():
            if not isinstance(item, Mapping):
                raise ValueError(f'documents.json record {source_key!r} is not an object')
            project_id = item.get('project_id')
            if not isinstance(project_id, str) or not project_id:
                candidate = str(source_key).removesuffix(':project')
                project_id = candidate if candidate in project_ids else None
            stage_id = item.get('stage_id')
            if project_id not in project_ids or (stage_id is not None and stage_id not in stage_ids):
                raise ValueError(f'document {source_key!r} has a broken project/stage relation')
            content = item.get('content', {'type': 'doc', 'content': [{'type': 'paragraph'}]})
            if not isinstance(content, Mapping) or content.get('type') != 'doc':
                raise ValueError(f'document {source_key!r} has invalid Tiptap content')
            scope = f'{project_id}:{stage_id or "project"}'
            document_id = item.get('document_id') or item.get('id')
            if not isinstance(document_id, str) or not document_id:
                document_id = f'document-{hashlib.sha256(scope.encode()).hexdigest()[:40]}'
            if document_id in seen_documents or scope in seen_scopes:
                raise ValueError(f'duplicate document identity for {source_key!r}')
            seen_documents.add(document_id)
            seen_scopes.add(scope)
            extensions = {str(key): item[key] for key in item if key not in known}
            document_rows.append((
                document_id, scope, project_id, stage_id, item.get('title', 'Текст'),
                _json(dict(content)), item.get('content_format', 'tiptap-json/v1'),
                item.get('created_at'), item.get('updated_at'),
                int(item.get('revision', 0) or 0), _json(extensions),
            ))
            external_path = item.get('docx_path')
            if isinstance(external_path, str) and external_path:
                binding_id = uuid.uuid5(
                    uuid.NAMESPACE_URL, f'nfprogress-document-binding:{document_id}',
                ).hex
                sync_state = item.get('sync_state', 'unlinked')
                if not Path(external_path).expanduser().is_file():
                    sync_state = 'missing_external'
                binding_rows.append((
                    binding_id, document_id, 'word', external_path, None,
                    item.get('last_synced_hash'), 0, item.get('last_synced_hash'),
                    item.get('last_synced_at'), sync_state, None,
                    _json({'legacy_source_key': str(source_key)}),
                ))
        return sorted(document_rows), sorted(binding_rows)

    @staticmethod
    def _entity_row(entity_id: str, payload: Mapping[str, Any], project_id: str | None = None) -> tuple[Any, ...]:
        return (
            entity_id, *( [project_id] if project_id is not None else [] ),
            payload.get('name'), payload.get('goal'), int(bool(payload.get('infinite'))),
            payload.get('unit', 'symbols'), payload.get('status', 'активен'),
            payload.get('created_at'), payload.get('updated_at'), _json(payload),
        )

    @staticmethod
    def _rows_for_entity(
            progress_rows, order_rows, payload, project_id, stage_id, position,
    ) -> int:
        for entry in payload.get('progress_entries', []):
            progress_rows.append((entry['id'], project_id, stage_id, entry.get('created_at'), entry.get('added_symbols'), entry.get('added_progress'), _json(entry)))
            order_rows.append((entry['id'], position))
            position += 1
        return position

    @staticmethod
    def _extension_row(entity_type: str, entity_id: str, entity: Any) -> tuple[str, str, str]:
        known = {
            '_name', '_goal', 'project_id', 'stage_id', 'create_date', 'edit_date',
            'complete_date', '_total_symbols', '_progress', '_deadline', '_status',
            'notes', 'streaks', 'max_streak', 'streak_status', 'unit', 'synch',
            'last_synch', 'work_method', 'last_streak_bonus', 'last_streak_lost_date',
            'freezes', 'auto_freeze', 'deadline_set_date', 'personal_goal_for_the_day',
            'project_plan', 'enable_stages', 'stages', 'is_stage', 'mindmap_data',
            'mindmap_updated_at', 'combine_stage_mindmaps', 'project_notes',
            'notes_updated_at', 'cover_image', 'folder_id', 'parent_project_name',
        }
        extras = {
            key: value for key, value in vars(entity).items() if key not in known
        } if hasattr(entity, '__dict__') else {}
        return entity_type, entity_id, _json(extras)

    @staticmethod
    def _progress_extension_rows(entity: Any) -> list[tuple[str, str, str]]:
        known = {
            'entry_id', 'new_total', 'added_symbols', 'added_progress',
            'date_create', 'writing_day',
        }
        rows = []
        for note in getattr(entity, 'notes', []):
            entry_id = getattr(note, 'entry_id', None)
            if not isinstance(entry_id, str) or not entry_id:
                continue
            raw = _legacy_json(vars(note)) if hasattr(note, '__dict__') else {}
            extras = {key: value for key, value in raw.items() if key not in known}
            rows.append(('progress', entry_id, _json(extras)))
        return rows

    @staticmethod
    def _binding_rows(entity: Any, project_id: str, stage_id: str | None) -> list[tuple[Any, ...]]:
        binding = getattr(entity, 'synch', None)
        if binding is None:
            return []
        if isinstance(binding, str):
            binding = {'type': 'word', 'path': binding}
        if not isinstance(binding, Mapping):
            binding = {'value': binding}
        payload = dict(binding)
        binding_type = str(payload.get('type') or payload.get('kind') or 'unknown')
        external_path = payload.get('path') or payload.get('external_path')
        source_id = payload.get('file_id') or payload.get('source_id') or payload.get('item_id')
        content_hash = payload.get('hash') or payload.get('content_hash')
        last_synced = getattr(entity, 'last_synch', None)
        if isinstance(last_synced, (datetime, date)):
            last_synced = last_synced.isoformat()
        seed = f'nfprogress-binding:{project_id}:{stage_id or "project"}:{_json(payload)}'
        binding_id = uuid.uuid5(uuid.NAMESPACE_URL, seed).hex
        return [(
            binding_id, project_id, stage_id, binding_type,
            str(external_path) if external_path is not None else None,
            str(source_id) if source_id is not None else None,
            str(content_hash) if content_hash is not None else None,
            last_synced, _json(payload),
        )]

    @staticmethod
    def _folder_rows(projects: Mapping[str, Any]) -> list[tuple[Any, ...]]:
        raw = projects.get('project_folders', [])
        if not isinstance(raw, list):
            return []
        rows = []
        seen: set[str] = set()
        for folder in raw:
            if not isinstance(folder, Mapping):
                continue
            folder_id, name = folder.get('id'), folder.get('name')
            if not isinstance(folder_id, str) or not folder_id or folder_id in seen:
                continue
            if not isinstance(name, str) or not name.strip():
                continue
            seen.add(folder_id)
            rows.append((folder_id, name.strip()[:120], len(rows), _json(folder)))
        return rows

    @staticmethod
    def _rows_for_notes(note_rows, payload, project_id, stage_id):
        for note in payload.get('project_notes', []):
            note_id = note.get('id')
            if note_id:
                note_rows.append((note_id, project_id, stage_id, note.get('updated_at'), _json(note)))

    def mark_dirty(self, error: Exception) -> None:
        LOGGER.exception('SQLite mirror synchronization failed')
        try:
            self.set_status('dirty', str(error))
        except Exception:
            LOGGER.exception('Could not mark SQLite mirror dirty')
