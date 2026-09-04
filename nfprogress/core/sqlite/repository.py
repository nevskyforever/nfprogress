"""Relational shadow mirror populated from the authoritative pickle stores."""

from __future__ import annotations

import json
import logging
import math
import uuid
from collections.abc import Mapping
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

from nfprogress.core.serialization import serialize_project, to_json_safe
from nfprogress.core.sqlite.connection import database_path, open_database
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

    def rebuild(self, projects: dict[str, Any], settings: dict[str, Any], gamer: Any) -> None:
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
            self.sync_game(gamer)

        with open_database(self.data_root) as db:
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
        project_ids = [
            project.project_id
            for project in project_map.values()
            if hasattr(project, 'project_id')
        ] if isinstance(project_map, Mapping) else []
        order_rows = [
            (project_id, position)
            for position, project_id in enumerate(
                self._normalized_project_order(projects, project_ids),
            )
        ]
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

    def sync_game(self, gamer: Any) -> None:
        with open_database(self.data_root) as db:
            with db:
                db.execute(
                    'INSERT INTO game_state(id,schema_version,payload_json,updated_at) VALUES(1,1,?,?) '
                    'ON CONFLICT(id) DO UPDATE SET schema_version=excluded.schema_version, '
                    'payload_json=excluded.payload_json, updated_at=excluded.updated_at',
                    (_json(vars(gamer)) if gamer is not None else _json(None), _now()),
                )

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
