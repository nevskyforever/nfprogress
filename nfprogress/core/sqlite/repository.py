"""Relational shadow mirror populated from the authoritative pickle stores."""

from __future__ import annotations

import json
import logging
import math
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
        progress_rows: list[tuple[Any, ...]] = []
        project_map = projects.get('projects', {}) if isinstance(projects, dict) else {}
        for project in project_map.values() if isinstance(project_map, Mapping) else []:
            payload = serialize_project(project)
            project_id = payload['id']
            project_rows.append(self._entity_row(project_id, payload))
            for stage in payload.get('stages', []):
                stage_rows.append(self._entity_row(stage['id'], stage, project_id))
                self._rows_for_entity(progress_rows, stage, project_id, stage['id'])
            self._rows_for_entity(progress_rows, payload, project_id, None)

        with open_database(self.data_root) as db:
            with db:
                db.execute('DELETE FROM progress_entries')
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
                    'INSERT INTO progress_entries(id,project_id,stage_id,created_at,added_symbols,added_progress,payload_json) VALUES(?,?,?,?,?,?,?)',
                    progress_rows,
                )

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
    def _rows_for_entity(progress_rows, payload, project_id, stage_id):
        for entry in payload.get('progress_entries', []):
            progress_rows.append((entry['id'], project_id, stage_id, entry.get('created_at'), entry.get('added_symbols'), entry.get('added_progress'), _json(entry)))

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
