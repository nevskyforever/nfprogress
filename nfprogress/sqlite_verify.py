"""Compare canonical PKL projections with the SQLite shadow mirror."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping

import engine
from nfprogress.core.serialization import serialize_project
from nfprogress.core.sqlite.connection import open_database
from nfprogress.core.sqlite.ownership import StorageOwner, StorageOwnershipRepository, Subsystem
from nfprogress.core.sqlite.repository import SQLiteMirrorRepository, _legacy_json
from nfprogress.core.storage import PickleRepository


def _expected(repository, owners):
    needs_projects = (
        owners[Subsystem.PROJECTS] == StorageOwner.PICKLE
        or owners[Subsystem.NOTES] == StorageOwner.PICKLE
    )
    with repository.locked():
        data = engine.load_data() if needs_projects else {}
        settings = engine.load_settings() if owners[Subsystem.SETTINGS] == StorageOwner.PICKLE else {}
        gamer = (__import__('game').load_game()
                 if owners[Subsystem.GAME] == StorageOwner.PICKLE else None)
    projects = data.get('projects', {}) if isinstance(data, dict) else {}
    entities = [entity for project in projects.values() for entity in [project, *getattr(project, 'stages', [])]]
    return {
        'projects': {p.project_id: serialize_project(p) for p in projects.values()} if needs_projects else {},
        'stages': {stage.stage_id: serialize_project(stage) for project in projects.values() for stage in getattr(project, 'stages', [])} if needs_projects else {},
        'progress': {entry['id']: entry for entity in entities for entry in serialize_project(entity).get('progress_entries', [])} if needs_projects else {},
        'notes': {note['id']: note for entity in entities for note in serialize_project(entity).get('project_notes', []) if note.get('id')} if needs_projects else {},
        'settings': {str(key): _legacy_json(value) for key, value in settings.items()},
        'game': _legacy_json(vars(gamer)) if gamer is not None else None,
        'project_order': SQLiteMirrorRepository._normalized_project_order(
            data, [project.project_id for project in projects.values()],
        ) if needs_projects else [],
    }


def _actual(repository):
    with open_database(repository.base_dir) as db:
        projects = {row['id']: json.loads(row['payload_json']) for row in db.execute('SELECT * FROM projects')}
        stages = {row['id']: json.loads(row['payload_json']) for row in db.execute('SELECT * FROM stages')}
        progress = {row['id']: json.loads(row['payload_json']) for row in db.execute('SELECT * FROM progress_entries')}
        notes = {row['id']: json.loads(row['payload_json']) for row in db.execute('SELECT * FROM notes')}
        settings = {row['key']: json.loads(row['value_json']) for row in db.execute('SELECT * FROM settings')}
        row = db.execute('SELECT payload_json FROM game_state WHERE id=1').fetchone()
        game = json.loads(row['payload_json']) if row else None
        order_rows = db.execute(
            'SELECT project_id, position FROM project_order ORDER BY position, project_id',
        ).fetchall()
        project_order = (
            [row['project_id'] for row in order_rows]
            if [row['position'] for row in order_rows] == list(range(len(order_rows)))
            else None
        )
    return {'projects': projects, 'stages': stages, 'progress': progress, 'notes': notes, 'settings': settings, 'game': game, 'project_order': project_order}


def verify(data_dir: str) -> tuple[bool, list[str]]:
    repository = PickleRepository(data_dir)
    owners = StorageOwnershipRepository(data_dir).owners()
    expected, actual = _expected(repository, owners), _actual(repository)
    domains = {
        Subsystem.PROJECTS: (('projects', 'Projects'), ('stages', 'Stages'), ('progress', 'Progress')),
        Subsystem.NOTES: (('notes', 'Notes'),),
        Subsystem.SETTINGS: (('settings', 'Settings'),),
        Subsystem.GAME: (('game', 'Game state'),),
    }
    domains[Subsystem.PROJECTS] += (('project_order', 'Project order'),)
    labels = [item for subsystem in domains for item in domains[subsystem] if owners[subsystem] == StorageOwner.PICKLE]
    messages, consistent = [], True
    for key, label in labels:
        expected_value, actual_value = expected[key], actual[key]
        if key in {'projects', 'stages'}:
            # These are display projections and contain date-relative fields.
            # They must not make a mirror look dirty merely because a new day
            # started after the last write.
            def stable(payload):
                def clean(value):
                    if isinstance(value, dict):
                        return {
                            field: clean(item) for field, item in value.items()
                            if field not in {'planning_date', 'today_goal', 'added_today', 'remaining'}
                        }
                    if isinstance(value, list):
                        return [clean(item) for item in value]
                    return value
                return {
                    entity_id: clean(entity)
                    for entity_id, entity in payload.items()
                }
            expected_value, actual_value = stable(expected_value), stable(actual_value)
        if key == 'game':
            # Legacy migration intentionally refreshes an old session clock on
            # every load. The persistent session content remains comparable.
            def clean_session(value, path=()):
                if isinstance(value, dict):
                    return {
                        field: clean_session(item, (*path, field)) for field, item in value.items()
                        if not (path == ('writing_session',) and field == 'started_at')
                    }
                if isinstance(value, list):
                    return [clean_session(item, path) for item in value]
                return value
            expected_value, actual_value = clean_session(expected_value), clean_session(actual_value)
            if isinstance(expected_value, dict) and isinstance(actual_value, dict):
                # Gamer() initializes this runtime health timestamp on every
                # load when no gamer.pkl exists; it is not user progress.
                expected_value.pop('last_health_recovery_at', None)
                actual_value.pop('last_health_recovery_at', None)
        if expected_value == actual_value:
            messages.append(f'{label}: OK')
            continue
        consistent = False
        missing = set(expected_value) - set(actual_value) if isinstance(expected_value, Mapping) else set()
        extra = set(actual_value) - set(expected_value) if isinstance(actual_value, Mapping) else set()
        changed = (
            set(expected_value) & set(actual_value)
            if isinstance(expected_value, Mapping) and isinstance(actual_value, Mapping)
            else set()
        )
        changed = {entity_id for entity_id in changed if expected_value[entity_id] != actual_value[entity_id]}
        detail = (
            f' (missing: {next(iter(missing))})' if missing
            else f' (unexpected: {next(iter(extra))})' if extra
            else f' (changed: {next(iter(changed))})' if changed else ''
        )
        messages.append(f'{label}: MISMATCH{detail}')
    messages.append('SQLite mirror is consistent.' if consistent else 'SQLite mirror is inconsistent.')
    return consistent, messages


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', required=True)
    args = parser.parse_args(argv)
    try:
        consistent, messages = verify(args.data_dir)
    except Exception as error:
        print(f'Verification error: {error}', file=sys.stderr)
        return 2
    print('\n'.join(messages))
    return 0 if consistent else 1


if __name__ == '__main__':
    raise SystemExit(main())
