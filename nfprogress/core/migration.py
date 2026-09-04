"""Canonical, JSON-safe input and importer for the Projects F1 migration.

The legacy pickle reader is intentionally kept outside the desktop runtime.
This module is the migration-only Python fallback: it turns already-loaded
legacy objects into a versioned data-transfer object, after which all writes
are parameterized SQLite operations.  Unknown entity attributes live in
``extra_fields`` and are never reconstructed from the normalized columns.
"""

from __future__ import annotations

import json
import hashlib
import math
import pickle
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

import engine

from nfprogress.core.serialization import serialize_project, to_json_safe
from nfprogress.core.sqlite.connection import open_database


GAME_MIGRATION_DTO_VERSION = 1


MIGRATION_DTO_VERSION = 1
BUNDLE_FIELDS = frozenset({
    'dto_version', 'projects', 'project_order', 'folders', 'project_metadata',
    'root_extensions', 'source_manifest', 'game', 'documents',
    'document_bindings', 'external_file_manifest',
})
_ROOT_PROJECT_FIELDS = frozenset({
    'projects', 'project_order', 'project_folders', 'last',
    'notifications', 'global_streaks', 'global_streak_status',
    'max_global_streak', 'last_global_streak_bonus',
    'last_global_streak_lost_date', 'last_global_streak_lose_len',
})
_ENTITY_FIELDS = frozenset({
    '_name', '_goal', 'project_id', 'stage_id', 'create_date', 'edit_date',
    'complete_date', '_total_symbols', '_progress', '_deadline', '_status',
    'notes', 'streaks', 'max_streak', 'streak_status', 'unit', 'synch',
    'last_synch', 'work_method', 'last_streak_bonus', 'last_streak_lost_date',
    'freezes', 'auto_freeze', 'deadline_set_date', 'personal_goal_for_the_day',
    'project_plan', 'enable_stages', 'stages', 'is_stage', 'mindmap_data',
    'mindmap_updated_at', 'combine_stage_mindmaps', 'project_notes',
    'notes_updated_at', 'cover_image', 'folder_id', 'parent_project_name',
})


def _safe(value: Any, seen: set[int] | None = None) -> Any:
    """Convert legacy values to strict JSON without executing object hooks."""
    if seen is None:
        seen = set()
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _safe(item, seen) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe(item, seen) for item in value]
    if isinstance(value, (set, frozenset)):
        return [_safe(item, seen) for item in sorted(value, key=repr)]
    if hasattr(value, '__dict__'):
        marker = id(value)
        if marker in seen:
            return None
        seen.add(marker)
        result = {str(key): _safe(item, seen) for key, item in vars(value).items()}
        seen.remove(marker)
        return result
    try:
        return to_json_safe(value)
    except TypeError:
        return None


def _json(value: Any) -> str:
    return json.dumps(_safe(value), ensure_ascii=False, allow_nan=False, sort_keys=True)


def _binding(entity: Any, project_id: str, stage_id: str | None) -> dict[str, Any] | None:
    value = getattr(entity, 'synch', None)
    if value is None:
        return None
    if isinstance(value, str):
        value = {'type': 'word', 'path': value}
    if not isinstance(value, Mapping):
        value = {'value': value}
    payload = dict(value)
    last_synced_at = _safe(getattr(entity, 'last_synch', None))
    seed = f'nfprogress-binding:{project_id}:{stage_id or "project"}:{_json(payload)}'
    return {
        'id': uuid.uuid5(uuid.NAMESPACE_URL, seed).hex,
        'project_id': project_id,
        'stage_id': stage_id,
        'binding_type': str(payload.get('type') or payload.get('kind') or 'unknown'),
        'external_path': payload.get('path') or payload.get('external_path'),
        'source_id': payload.get('file_id') or payload.get('source_id') or payload.get('item_id'),
        'content_hash': payload.get('hash') or payload.get('content_hash'),
        'last_synced_at': last_synced_at,
        'payload': _safe(payload),
    }


def _entity_dto(entity: Any, kind: str) -> dict[str, Any]:
    entity_id = getattr(entity, 'stage_id', None) if kind == 'stage' else getattr(entity, 'project_id', None)
    if not isinstance(entity_id, str) or not entity_id:
        raise ValueError(f'{kind} has no stable identifier')
    raw = _safe(vars(entity)) if hasattr(entity, '__dict__') else {}
    extras = {key: value for key, value in raw.items() if key not in _ENTITY_FIELDS}
    payload = serialize_project(entity)
    return {
        'id': entity_id,
        'kind': kind,
        'payload': payload,
        'extra_fields': extras,
        'progress_extra_fields': _progress_extra_fields(entity),
        'binding': _binding(entity, entity_id if kind == 'project' else '', None),
    }


def _progress_extra_fields(entity: Any) -> dict[str, Any]:
    known = {'entry_id', 'new_total', 'added_symbols', 'added_progress', 'date_create', 'writing_day'}
    result = {}
    for note in getattr(entity, 'notes', []):
        entry_id = getattr(note, 'entry_id', None)
        if not isinstance(entry_id, str) or not entry_id:
            continue
        raw = _safe(vars(note)) if hasattr(note, '__dict__') else {}
        result[entry_id] = {key: value for key, value in raw.items() if key not in known}
    return result


def _stage_dto(stage: Any, project_id: str) -> dict[str, Any]:
    result = _entity_dto(stage, 'stage')
    result['binding'] = _binding(stage, project_id, result['id'])
    result['project_id'] = project_id
    return result


@dataclass(slots=True)
class MigrationBundle:
    """Versioned Projects aggregate accepted by both import implementations."""

    projects: list[dict[str, Any]] = field(default_factory=list)
    project_order: list[str] = field(default_factory=list)
    folders: list[dict[str, Any]] = field(default_factory=list)
    project_metadata: dict[str, Any] = field(default_factory=dict)
    root_extensions: dict[str, Any] = field(default_factory=dict)
    source_manifest: dict[str, Any] = field(default_factory=dict)
    # Optional so v1 Projects bundles remain valid for Web/legacy tooling.
    game: dict[str, Any] | None = None
    # F6 document data is optional for backward-compatible Projects bundles.
    documents: list[dict[str, Any]] = field(default_factory=list)
    document_bindings: list[dict[str, Any]] = field(default_factory=list)
    external_file_manifest: list[dict[str, Any]] = field(default_factory=list)
    dto_version: int = MIGRATION_DTO_VERSION

    @classmethod
    def from_legacy(cls, envelope: Mapping[str, Any]) -> 'MigrationBundle':
        project_map = envelope.get('projects', {})
        if not isinstance(project_map, Mapping):
            raise ValueError('legacy projects envelope must contain a mapping')
        projects: list[dict[str, Any]] = []
        for project in project_map.values():
            dto = _entity_dto(project, 'project')
            project_id = dto['id']
            dto['stages'] = [
                _stage_dto(stage, project_id)
                for stage in getattr(project, 'stages', [])
            ]
            dto['progress'] = [
                _safe(serialize_project(project).get('progress_entries', [])),
            ][0]
            dto['stage_progress'] = {
                stage['id']: _safe(stage.get('payload', {}).get('progress_entries', []))
                for stage in dto['stages']
            }
            projects.append(dto)
        project_ids = [item['id'] for item in projects]
        raw_order = envelope.get('project_order', [])
        order = []
        if isinstance(raw_order, list):
            for project_id in raw_order:
                if project_id in project_ids and project_id not in order:
                    order.append(project_id)
        order.extend(project_id for project_id in project_ids if project_id not in order)
        raw_folders = envelope.get('project_folders', [])
        folders = _normalized_folders(raw_folders)
        root_extensions = {
            key: _safe(value) for key, value in envelope.items()
            if key not in _ROOT_PROJECT_FIELDS
        }
        metadata = {'project_last': _safe(envelope.get('last'))}
        return cls(
            projects=projects,
            project_order=order,
            folders=folders,
            project_metadata=metadata,
            root_extensions=root_extensions,
        )

    @classmethod
    def from_json(cls, value: str | bytes) -> 'MigrationBundle':
        raw = json.loads(value)
        if not isinstance(raw, Mapping):
            raise ValueError('migration DTO must be an object')
        unknown = set(raw) - BUNDLE_FIELDS
        if unknown:
            raise ValueError(f'unknown migration DTO fields: {sorted(unknown)!r}')
        dto_version = raw.get('dto_version', MIGRATION_DTO_VERSION)
        if dto_version != MIGRATION_DTO_VERSION:
            raise ValueError(f'unsupported migration DTO version: {dto_version!r}')
        return cls(**{key: raw.get(key, getattr(cls(), key)) for key in (
            'projects', 'project_order', 'folders', 'project_metadata',
            'root_extensions', 'source_manifest', 'dto_version',
            'game', 'documents', 'document_bindings', 'external_file_manifest',
        )})

    def to_dict(self) -> dict[str, Any]:
        result = _safe({
            'dto_version': self.dto_version,
            'projects': self.projects,
            'project_order': self.project_order,
            'folders': self.folders,
            'project_metadata': self.project_metadata,
            'root_extensions': self.root_extensions,
            'source_manifest': self.source_manifest,
            'documents': self.documents,
            'document_bindings': self.document_bindings,
            'external_file_manifest': self.external_file_manifest,
        })
        if self.game is not None:
            result['game'] = _safe(self.game)
        json.dumps(result, ensure_ascii=False, allow_nan=False)
        return result

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, allow_nan=False, sort_keys=True)


def load_legacy_projects_bundle(data_root: str | Path) -> MigrationBundle:
    """Build a DTO and source manifest from an explicit legacy data root."""
    from nfprogress.core.storage import PickleRepository

    repository = PickleRepository(data_root)
    with repository.locked():
        import engine
        with engine.data_directory_context(data_root):
            envelope = engine.load_data()
    bundle = MigrationBundle.from_legacy(envelope)
    documents_path = Path(data_root).expanduser().resolve() / 'documents.json'
    if documents_path.is_file():
        try:
            raw_documents = json.loads(documents_path.read_text(encoding='utf-8'))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError('documents.json cannot be converted to the migration DTO') from error
        if not isinstance(raw_documents, Mapping):
            raise ValueError('documents.json must contain an object')
        known = frozenset({
            'document_id', 'id', 'project_id', 'stage_id', 'title', 'content',
            'content_format', 'created_at', 'updated_at', 'exists', 'docx_path',
            'sync_state', 'last_synced_hash', 'last_synced_at', 'local_dirty',
            'word_dirty', 'symbols', 'has_content',
        })
        for source_key, raw_record in raw_documents.items():
            if not isinstance(raw_record, Mapping):
                continue
            project_id = raw_record.get('project_id')
            stage_id = raw_record.get('stage_id')
            if not isinstance(project_id, str) or not project_id:
                continue
            scope = f'{project_id}:{stage_id or "project"}'
            document_id = raw_record.get('document_id') or raw_record.get('id')
            if not isinstance(document_id, str) or not document_id:
                document_id = f'document-{hashlib.sha256(scope.encode()).hexdigest()[:40]}'
            record = dict(raw_record)
            record['document_id'] = document_id
            record['project_id'] = project_id
            record['stage_id'] = stage_id
            record['extensions'] = {
                str(key): _safe(value) for key, value in raw_record.items()
                if key not in known
            }
            bundle.documents.append(_safe(record))
            external_path = raw_record.get('docx_path')
            if isinstance(external_path, str) and external_path:
                binding = {
                    'id': uuid.uuid5(uuid.NAMESPACE_URL, f'nfprogress-document-binding:{document_id}').hex,
                    'document_id': document_id,
                    'project_id': project_id,
                    'stage_id': stage_id,
                    'binding_type': 'word',
                    'external_path': external_path,
                    'source_id': None,
                    'content_hash': raw_record.get('last_synced_hash'),
                    'last_synced_at': raw_record.get('last_synced_at'),
                    'payload': {'legacy_source_key': source_key},
                }
                bundle.document_bindings.append(_safe(binding))
                bundle.external_file_manifest.append(_safe({
                    'document_id': document_id,
                    'external_path': external_path,
                    'content_hash': raw_record.get('last_synced_hash'),
                }))
        bundle.source_manifest['documents.json'] = {
            'source_format': 'legacy-json',
            'source_schema_version': 'legacy',
            'checksum': f'sha256:{hashlib.sha256(documents_path.read_bytes()).hexdigest()}',
            'size_bytes': documents_path.stat().st_size,
        }
    source = Path(data_root).expanduser().resolve() / 'data.pkl'
    if source.is_file():
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        stat = source.stat()
        bundle.source_manifest['data.pkl'] = {
            'source_format': 'pickle',
            'source_schema_version': 'legacy',
            'checksum': f'sha256:{digest}',
            'size_bytes': stat.st_size,
        }
    return bundle


class MigrationImportError(RuntimeError):
    """Raised when a canonical bundle cannot be imported without data loss."""


@dataclass(slots=True)
class GameMigrationBundle:
    """Canonical Game payload accepted by the SQLite importer.

    ``payload`` is intentionally a JSON document with typed object tags for
    legacy compatibility objects.  Unknown Gamer fields and unknown envelope
    fields remain under ``extensions`` in that document.
    """

    payload: dict[str, Any]
    source_manifest: dict[str, Any] = field(default_factory=dict)
    dto_version: int = GAME_MIGRATION_DTO_VERSION

    def to_dict(self) -> dict[str, Any]:
        value = {
            'dto_version': self.dto_version,
            'payload': self.payload,
            'source_manifest': self.source_manifest,
        }
        json.dumps(value, ensure_ascii=False, allow_nan=False)
        return value

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, allow_nan=False, sort_keys=True)


def cutover_projects(data_root: str | Path) -> MigrationBundle:
    """Import legacy Projects and switch ownership only after verification."""
    from nfprogress.core.sqlite.ownership import StorageOwner, StorageOwnershipRepository, Subsystem
    from nfprogress.core.storage import PickleRepository

    root = Path(data_root).expanduser().resolve()
    ownership = StorageOwnershipRepository(root)
    if ownership.get_owner(Subsystem.PROJECTS) == StorageOwner.SQLITE:
        return MigrationBundle()
    bundle = load_legacy_projects_bundle(root)
    PickleRepository(root).create_backup(('data',))
    import_projects_bundle(bundle, root)
    verified, errors = verify_projects_bundle(bundle, root)
    if not verified:
        raise MigrationImportError(
            'Projects SQLite parity verification failed: ' + ', '.join(errors),
        )
    with open_database(root) as db:
        with db:
            owner = db.execute(
                'SELECT owner FROM storage_ownership WHERE subsystem = ?',
                (Subsystem.PROJECTS.value,),
            ).fetchone()
            if owner is None or owner['owner'] != StorageOwner.PICKLE.value:
                raise MigrationImportError('Projects owner changed during cutover')
            db.execute(
                "UPDATE storage_ownership SET owner = ?, updated_at = datetime('now') "
                'WHERE subsystem = ?',
                (StorageOwner.SQLITE.value, Subsystem.PROJECTS.value),
            )
            db.execute(
                "UPDATE mirror_state SET source_format='migration_bundle', "
                "sync_status='healthy', last_error=NULL WHERE id=1",
            )
    return bundle


def load_legacy_game_bundle(data_root: str | Path) -> GameMigrationBundle:
    """Decode legacy Game files only in migration tooling, never at runtime."""
    from nfprogress.core.game_state import _game_payload
    from nfprogress.core.storage import PickleRepository
    from nfprogress.core.sqlite.ownership import (
        StorageOwner, StorageOwnershipRepository, Subsystem,
    )

    root = Path(data_root).expanduser().resolve()
    repository = PickleRepository(root)
    with repository.locked():
        with engine.data_directory_context(root):
            envelope = engine.load_data()
            gamer_path = root / 'gamer.pkl'
            if gamer_path.is_file():
                with gamer_path.open('rb') as stream:
                    gamer = pickle.load(stream)
            else:
                import game
                gamer = game.Gamer()
    # F2 may already have switched Projects while data.pkl remains a stale
    # recovery artifact.  Capture project-linked Game fields from the current
    # SQLite Projects read model, while retaining legacy envelope-only Game
    # fields (notifications/global markers) from data.pkl.
    if StorageOwnershipRepository(root).get_owner(Subsystem.PROJECTS) == StorageOwner.SQLITE:
        from nfprogress.core.game_state import SQLiteGameRepository
        current_projects = SQLiteGameRepository(root).read_projects()
        if isinstance(current_projects.get('projects'), Mapping):
            envelope = dict(envelope)
            envelope['projects'] = current_projects['projects']
    payload = _game_payload(gamer, envelope)
    manifest: dict[str, Any] = {}
    for name in ('data.pkl', 'gamer.pkl'):
        source = root / name
        if source.is_file():
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            manifest[name] = {
                'source_format': 'pickle', 'source_schema_version': 'legacy',
                'checksum': f'sha256:{digest}', 'size_bytes': source.stat().st_size,
            }
    return GameMigrationBundle(payload=payload, source_manifest=manifest)


def import_game_bundle(bundle: GameMigrationBundle, data_root: str | Path) -> None:
    """Import Game state transactionally without changing ownership."""
    if not isinstance(bundle, GameMigrationBundle):
        raise TypeError('bundle must be a GameMigrationBundle')
    bundle.to_dict()
    with open_database(data_root) as db:
        with db:
            encoded = json.dumps(bundle.payload, ensure_ascii=False, allow_nan=False, sort_keys=True)
            db.execute(
                'INSERT INTO game_state(id,schema_version,payload_json,updated_at) VALUES(1,2,?,datetime(\'now\')) '
                'ON CONFLICT(id) DO UPDATE SET schema_version=excluded.schema_version,payload_json=excluded.payload_json,updated_at=excluded.updated_at',
                (encoded,),
            )
            db.execute('DELETE FROM game_metadata')
            db.executemany(
                'INSERT INTO game_metadata(key, value_json) VALUES(?, ?)',
                [
                    ('dto_version', json.dumps(bundle.dto_version)),
                    ('source_manifest', json.dumps(bundle.source_manifest, ensure_ascii=False, sort_keys=True)),
                ],
            )


def verify_game_bundle(bundle: GameMigrationBundle, data_root: str | Path) -> tuple[bool, list[str]]:
    with open_database(data_root) as db:
        row = db.execute('SELECT schema_version, payload_json FROM game_state WHERE id=1').fetchone()
    if row is None:
        return False, ['game_state row is missing']
    try:
        actual = json.loads(row['payload_json'])
    except json.JSONDecodeError:
        return False, ['game_state payload is not valid JSON']
    errors: list[str] = []
    if int(row['schema_version']) != 2:
        errors.append('unexpected game state schema version')
    if actual != bundle.payload:
        errors.append('canonical Game payload mismatch')
    return not errors, errors


def cutover_game(data_root: str | Path) -> GameMigrationBundle:
    """Switch Game ownership only after import and semantic verification."""
    from nfprogress.core.sqlite.ownership import StorageOwner, StorageOwnershipRepository, Subsystem
    from nfprogress.core.storage import PickleRepository

    root = Path(data_root).expanduser().resolve()
    ownership = StorageOwnershipRepository(root)
    if ownership.get_owner(Subsystem.GAME) == StorageOwner.SQLITE:
        return GameMigrationBundle(payload={})
    bundle = load_legacy_game_bundle(root)
    PickleRepository(root).create_backup(('data', 'gamer'))
    import_game_bundle(bundle, root)
    verified, errors = verify_game_bundle(bundle, root)
    if not verified:
        raise MigrationImportError('Game SQLite parity verification failed: ' + ', '.join(errors))
    with open_database(root) as db:
        with db:
            owner = db.execute(
                'SELECT owner FROM storage_ownership WHERE subsystem=?',
                (Subsystem.GAME.value,),
            ).fetchone()
            if owner is None or owner['owner'] != StorageOwner.PICKLE.value:
                raise MigrationImportError('Game owner changed during cutover')
            db.execute(
                "UPDATE storage_ownership SET owner='sqlite', updated_at=datetime('now') WHERE subsystem='game'",
            )
            db.execute(
                "INSERT INTO game_metadata(key,value_json) VALUES('owner_switched_at',datetime('now')) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json",
            )
    return bundle


def import_projects_bundle(bundle: MigrationBundle, data_root: str | Path) -> None:
    """Atomically replace only the Projects storage representation.

    Settings, Game and SQLite-owned Notes are not touched.  Notes are copied
    within the transaction solely because RESTRICT FKs prevent deleting their
    parent rows; a failed import rolls the copy and every project write back.
    """
    if not isinstance(bundle, MigrationBundle):
        raise TypeError('bundle must be a MigrationBundle')
    bundle.to_dict()
    try:
        from nfprogress.core.recovery import validate_migration_bundle

        validate_migration_bundle(bundle)
    except Exception as error:
        if isinstance(error, MigrationImportError):
            raise
        raise MigrationImportError(f'invalid migration bundle: {error}') from error
    project_ids = {item['id'] for item in bundle.projects}
    if len(project_ids) != len(bundle.projects) or set(bundle.project_order) != project_ids or len(bundle.project_order) != len(project_ids):
        raise MigrationImportError('project_order must contain every project exactly once')
    stage_ids = {
        stage['id'] for project in bundle.projects for stage in project.get('stages', [])
    }
    if len(stage_ids) != sum(len(project.get('stages', [])) for project in bundle.projects):
        raise MigrationImportError('stage identifiers must be unique')
    with open_database(data_root) as db:
        with db:
            notes = db.execute(
                'SELECT id, project_id, stage_id, updated_at, payload_json FROM notes',
            ).fetchall()
            if any(
                row['project_id'] not in project_ids
                or (row['stage_id'] is not None and row['stage_id'] not in stage_ids)
                for row in notes
            ):
                raise MigrationImportError('Notes reference an aggregate absent from the migration bundle')
            db.execute('DELETE FROM notes')
            for table in (
                'progress_order', 'progress_entries', 'project_bindings',
                'project_extensions', 'project_folder_members', 'project_folders', 'project_metadata',
                'migration_sources',
                'project_order', 'stage_order', 'stages', 'projects',
            ):
                db.execute(f'DELETE FROM {table}')

            progress_position = 0
            for project in bundle.projects:
                payload = project['payload']
                _insert_entity(db, 'projects', project['id'], payload)
                _insert_extension(db, 'project', project['id'], project.get('extra_fields', {}))
                _insert_binding(db, project.get('binding'))
                for stage_position, stage in enumerate(project.get('stages', [])):
                    stage_payload = stage['payload']
                    _insert_entity(db, 'stages', stage['id'], stage_payload, project['id'])
                    db.execute(
                        'INSERT INTO stage_order(stage_id, project_id, position) VALUES(?, ?, ?)',
                        (stage['id'], project['id'], stage_position),
                    )
                    _insert_extension(db, 'stage', stage['id'], stage.get('extra_fields', {}))
                    _insert_binding(db, stage.get('binding'))
                    for entry in stage.get('payload', {}).get('progress_entries', []):
                        progress_position = _insert_progress(db, entry, project['id'], stage['id'], progress_position)
                        _insert_extension(
                            db, 'progress', entry['id'],
                            stage.get('progress_extra_fields', {}).get(entry['id'], {}),
                        )
                for entry in payload.get('progress_entries', []):
                    progress_position = _insert_progress(db, entry, project['id'], None, progress_position)
                    _insert_extension(
                        db, 'progress', entry['id'],
                        project.get('progress_extra_fields', {}).get(entry['id'], {}),
                    )
            for position, project_id in enumerate(bundle.project_order):
                db.execute('INSERT INTO project_order(project_id, position) VALUES(?, ?)', (project_id, position))
            for position, folder in enumerate(bundle.folders):
                folder_id = folder.get('id')
                name = folder.get('name')
                if isinstance(folder_id, str) and folder_id and isinstance(name, str) and name.strip():
                    db.execute(
                        'INSERT INTO project_folders(id, name, position, payload_json) VALUES(?, ?, ?, ?)',
                        (folder_id, name.strip()[:120], position, _json(folder)),
                    )
            folder_ids = {
                row['id'] for row in db.execute('SELECT id FROM project_folders')
            }
            for project in bundle.projects:
                folder_id = project.get('payload', {}).get('folder_id')
                if isinstance(folder_id, str) and folder_id in folder_ids:
                    db.execute(
                        'INSERT INTO project_folder_members(project_id, folder_id) VALUES(?, ?)',
                        (project['id'], folder_id),
                    )
            metadata = dict(bundle.project_metadata)
            metadata['root_extensions'] = bundle.root_extensions
            db.executemany(
                'INSERT INTO project_metadata(key, value_json) VALUES(?, ?)',
                [(str(key), _json(value)) for key, value in metadata.items()],
            )
            db.executemany(
                'INSERT INTO migration_sources(name, source_format, source_schema_version, checksum, size_bytes, captured_at, metadata_json) VALUES(?, ?, ?, ?, ?, ?, ?)',
                [
                    (
                        str(name), str(details.get('source_format', 'legacy')),
                        details.get('source_schema_version'), details.get('checksum'),
                        details.get('size_bytes'), details.get('captured_at'),
                        _json(details),
                    )
                    for name, details in bundle.source_manifest.items()
                    if isinstance(details, Mapping)
                ],
            )
            db.executemany(
                'INSERT INTO notes(id, project_id, stage_id, updated_at, payload_json) VALUES(?, ?, ?, ?, ?)',
                [tuple(row) for row in notes],
            )
            db.execute(
                "UPDATE mirror_state SET source_format='migration_bundle', sync_status='healthy', last_error=NULL WHERE id=1",
            )


def read_projects_storage(data_root: str | Path) -> dict[str, Any]:
    """Read the complete F1 Projects representation for verification tooling."""
    with open_database(data_root) as db:
        tables = {
            'projects': db.execute('SELECT id, payload_json FROM projects').fetchall(),
            'stages': db.execute('SELECT id, project_id, payload_json FROM stages').fetchall(),
            'stage_order': db.execute('SELECT project_id, stage_id FROM stage_order ORDER BY project_id, position').fetchall(),
            'progress': db.execute('SELECT p.id, p.project_id, p.stage_id, p.payload_json FROM progress_entries p JOIN progress_order o ON o.entry_id = p.id ORDER BY o.position',).fetchall()
            if _has_progress_position(db) else db.execute('SELECT id, project_id, stage_id, payload_json FROM progress_entries ORDER BY rowid').fetchall(),
            'folders': db.execute('SELECT id, payload_json FROM project_folders ORDER BY position, id').fetchall(),
            'folder_members': db.execute('SELECT project_id, folder_id FROM project_folder_members ORDER BY project_id').fetchall(),
            'bindings': db.execute('SELECT id, project_id, stage_id, payload_json FROM project_bindings ORDER BY id').fetchall(),
            'extensions': db.execute('SELECT entity_type, entity_id, payload_json FROM project_extensions ORDER BY entity_type, entity_id').fetchall(),
            'metadata': db.execute('SELECT key, value_json FROM project_metadata ORDER BY key').fetchall(),
            'sources': db.execute('SELECT name, metadata_json FROM migration_sources ORDER BY name').fetchall(),
            'order': db.execute('SELECT project_id FROM project_order ORDER BY position').fetchall(),
        }
    return {
        'projects': {row['id']: json.loads(row['payload_json']) for row in tables['projects']},
        'stages': {row['id']: json.loads(row['payload_json']) for row in tables['stages']},
        'stage_order': {
            project_id: [
                stage['stage_id'] for stage in tables['stage_order']
                if stage['project_id'] == project_id
            ]
            for project_id in (row['id'] for row in tables['projects'])
        },
        'progress': {row['id']: json.loads(row['payload_json']) for row in tables['progress']},
        'folders': {row['id']: json.loads(row['payload_json']) for row in tables['folders']},
        'folder_members': {row['project_id']: row['folder_id'] for row in tables['folder_members']},
        'bindings': {row['id']: json.loads(row['payload_json']) for row in tables['bindings']},
        'extensions': {
            (row['entity_type'], row['entity_id']): json.loads(row['payload_json'])
            for row in tables['extensions']
        },
        'metadata': {row['key']: json.loads(row['value_json']) for row in tables['metadata']},
        'source_manifest': {row['name']: json.loads(row['metadata_json']) for row in tables['sources']},
        'project_order': [row['project_id'] for row in tables['order']],
    }


def _has_progress_position(db: Any) -> bool:
    return db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='progress_order'",
    ).fetchone() is not None


def verify_projects_bundle(bundle: MigrationBundle, data_root: str | Path) -> tuple[bool, list[str]]:
    """Compare meaningful canonical state, not pickle bytes, after import."""
    actual = read_projects_storage(data_root)
    expected_projects = {item['id']: item['payload'] for item in bundle.projects}
    expected_stages = {
        stage['id']: stage['payload']
        for project in bundle.projects for stage in project.get('stages', [])
    }
    expected_stage_order = {
        project['id']: [stage['id'] for stage in project.get('stages', [])]
        for project in bundle.projects
    }
    expected_progress = {
        entry['id']: entry
        for project in bundle.projects
        for entry in (
            project.get('payload', {}).get('progress_entries', [])
            + [entry for stage in project.get('stages', []) for entry in stage.get('payload', {}).get('progress_entries', [])]
        )
    }
    expected_extensions = {
        ('project', project['id']): project.get('extra_fields', {})
        for project in bundle.projects
    } | {
        ('stage', stage['id']): stage.get('extra_fields', {})
        for project in bundle.projects for stage in project.get('stages', [])
    } | {
        ('progress', entry_id): extra_fields
        for project in bundle.projects
        for entry_id, extra_fields in project.get('progress_extra_fields', {}).items()
    } | {
        ('progress', entry_id): extra_fields
        for project in bundle.projects
        for stage in project.get('stages', [])
        for entry_id, extra_fields in stage.get('progress_extra_fields', {}).items()
    }
    expected_bindings = {
        binding['id']: binding['payload']
        for project in bundle.projects
        for binding in ([project.get('binding')] + [stage.get('binding') for stage in project.get('stages', [])])
        if binding
    }
    expected_folders = {folder['id']: folder for folder in bundle.folders if isinstance(folder.get('id'), str)}
    expected_folder_members = {
        project['id']: project.get('payload', {}).get('folder_id')
        for project in bundle.projects
        if project.get('payload', {}).get('folder_id') in expected_folders
    }
    expected_metadata = dict(bundle.project_metadata)
    expected_metadata['root_extensions'] = bundle.root_extensions
    checks = {
        'projects': (expected_projects, actual['projects']),
        'stages': (expected_stages, actual['stages']),
        'stage_order': (expected_stage_order, actual['stage_order']),
        'progress': (expected_progress, actual['progress']),
        'folders': (expected_folders, actual['folders']),
        'folder_members': (expected_folder_members, actual['folder_members']),
        'bindings': (expected_bindings, actual['bindings']),
        'extensions': (expected_extensions, actual['extensions']),
        'metadata': (expected_metadata, actual['metadata']),
        'source_manifest': (bundle.source_manifest, actual['source_manifest']),
        'project_order': (bundle.project_order, actual['project_order']),
    }
    errors = [f'{name} mismatch' for name, (expected, value) in checks.items() if expected != value]
    return not errors, errors


verify_bundle = verify_projects_bundle


def _normalized_folders(raw_folders: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_folders, list):
        return []
    result = []
    seen: set[str] = set()
    for item in raw_folders:
        if not isinstance(item, Mapping):
            continue
        folder_id, name = item.get('id'), item.get('name')
        if not isinstance(folder_id, str) or not folder_id or folder_id in seen:
            continue
        if not isinstance(name, str) or not name.strip():
            continue
        seen.add(folder_id)
        result.append(dict(_safe(item)))
    return result


def _insert_entity(db: Any, table: str, entity_id: str, payload: Mapping[str, Any], project_id: str | None = None) -> None:
    values = (
        entity_id, *( [project_id] if project_id is not None else [] ),
        payload.get('name'), payload.get('goal'), int(bool(payload.get('infinite'))),
        payload.get('unit', 'symbols'), payload.get('status', 'активен'),
        payload.get('created_at'), payload.get('updated_at'), _json(payload),
    )
    columns = 'id, project_id, name, goal, infinite, unit, status, created_at, updated_at, payload_json' if project_id is not None else 'id, name, goal, infinite, unit, status, created_at, updated_at, payload_json'
    placeholders = ', '.join('?' for _ in values)
    db.execute(f'INSERT INTO {table}({columns}) VALUES({placeholders})', values)


def _insert_progress(db: Any, entry: Mapping[str, Any], project_id: str, stage_id: str | None, position: int) -> int:
    entry_id = entry.get('id')
    if not isinstance(entry_id, str) or not entry_id:
        raise MigrationImportError('progress entry has no stable id')
    db.execute(
        'INSERT INTO progress_entries(id, project_id, stage_id, created_at, added_symbols, added_progress, payload_json) VALUES(?, ?, ?, ?, ?, ?, ?)',
        (entry_id, project_id, stage_id, entry.get('created_at'), entry.get('added_symbols'), entry.get('added_progress'), _json(entry)),
    )
    db.execute('INSERT INTO progress_order(entry_id, position) VALUES(?, ?)', (entry_id, position))
    return position + 1


def _insert_extension(db: Any, entity_type: str, entity_id: str, value: Any) -> None:
    db.execute(
        'INSERT INTO project_extensions(entity_type, entity_id, payload_json) VALUES(?, ?, ?)',
        (entity_type, entity_id, _json(value)),
    )


def _insert_binding(db: Any, binding: Mapping[str, Any] | None) -> None:
    if not binding:
        return
    db.execute(
        'INSERT INTO project_bindings(id, project_id, stage_id, binding_type, external_path, source_id, content_hash, last_synced_at, payload_json) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (
            binding['id'], binding['project_id'], binding.get('stage_id'),
            binding['binding_type'], binding.get('external_path'), binding.get('source_id'),
            binding.get('content_hash'), binding.get('last_synced_at'), _json(binding['payload']),
        ),
    )
