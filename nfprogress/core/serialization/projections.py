"""Convert legacy Python models into transport-safe dictionaries."""

from __future__ import annotations

import math
import uuid
from collections.abc import Mapping
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

import engine


def to_json_safe(value: Any) -> Any:
    """Return a value accepted by strict JSON encoders.

    Non-finite floats deliberately become ``None``.  Entity serializers expose
    a separate semantic flag where infinity is meaningful (currently goals).
    """
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Decimal):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, (Path, uuid.UUID)):
        return str(value)
    if isinstance(value, Enum):
        return to_json_safe(value.value)
    if isinstance(value, Mapping):
        return {
            str(key): to_json_safe(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [to_json_safe(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return [to_json_safe(item) for item in sorted(value, key=repr)]
    raise TypeError(f'value of type {type(value).__name__} is not JSON-safe')


def serialize_note(note: Any, unit: str = 'symbols') -> dict[str, Any]:
    """Project one legacy :class:`engine.Note` into a progress entry."""
    entry_id = getattr(note, 'entry_id', None)
    if not isinstance(entry_id, str) or not entry_id:
        seed = ':'.join((
            str(getattr(note, 'date_create', None)),
            str(getattr(note, 'new_total', None)),
            str(getattr(note, 'added_symbols', None)),
            str(getattr(note, 'added_progress', None)),
        ))
        entry_id = uuid.uuid5(
            uuid.NAMESPACE_URL,
            f'nfprogress-progress-entry:{seed}',
        ).hex

    new_total_symbols = getattr(note, 'new_total', 0)
    added_symbols = getattr(note, 'added_symbols', 0)
    return {
        'id': entry_id,
        'new_total': to_json_safe(
            engine.unit_converter('symbols', new_total_symbols, unit),
        ),
        'new_total_symbols': to_json_safe(new_total_symbols),
        'added': to_json_safe(
            engine.unit_converter('symbols', added_symbols, unit),
        ),
        'added_symbols': to_json_safe(added_symbols),
        'added_progress': to_json_safe(getattr(note, 'added_progress', 0)),
        'created_at': to_json_safe(getattr(note, 'date_create', None)),
    }


def serialize_project_note(note: Mapping[str, Any]) -> dict[str, Any]:
    """Copy a normalized project-note record into strict JSON values."""
    payload = to_json_safe(note)
    if not isinstance(payload, dict):  # Defensive for custom Mapping types.
        raise TypeError('project note must serialize to an object')
    return payload


def serialize_project(project: Any) -> dict[str, Any]:
    """Project a legacy Project or Stage without leaking Python objects."""
    if isinstance(project, engine.Stage) or getattr(project, 'is_stage', False):
        return serialize_stage(project)
    return _serialize_entity(project, kind='project')


def serialize_stage(stage: Any) -> dict[str, Any]:
    """Project a legacy Stage using its stable stage identifier."""
    return _serialize_entity(stage, kind='stage')


def _serialize_entity(entity: Any, *, kind: str) -> dict[str, Any]:
    goal = entity.goal
    infinite = isinstance(goal, (int, float)) and math.isinf(goal)
    entity_id = (
        getattr(entity, 'stage_id', None)
        if kind == 'stage'
        else getattr(entity, 'project_id', None)
    )
    project_notes = engine.normalize_project_note_records(
        getattr(entity, 'project_notes', []),
    )
    mindmap = engine.normalize_mindmap_data(getattr(entity, 'mindmap_data', None))
    stages = getattr(entity, 'stages', []) if kind == 'project' else []
    today_goal = _today_goal_for_display(entity, kind=kind, infinite=infinite)

    payload = {
        'id': entity_id,
        'name': entity.name,
        'goal': None if infinite else to_json_safe(goal),
        'infinite': infinite,
        'total': to_json_safe(entity.total_units),
        'progress': to_json_safe(entity.progress),
        'deadline': _serialize_deadline(entity.deadline),
        'status': entity.status,
        'unit': entity.unit,
        'created_at': to_json_safe(getattr(entity, 'create_date', None)),
        'updated_at': to_json_safe(getattr(entity, 'edit_date', None)),
        'completed_at': to_json_safe(getattr(entity, 'complete_date', None)),
        'personal_goal': to_json_safe(
            getattr(entity, 'personal_goal_for_the_day', 0),
        ),
        'today_goal': to_json_safe(today_goal),
        'streak_enabled': getattr(entity, 'streak_status', 'No') != 'Off',
        'streak_status': str(getattr(entity, 'streak_status', 'No')),
        'streak_length': engine.streak_length(
            getattr(entity, 'streaks', []),
        ),
        'max_streak': int(getattr(entity, 'max_streak', 0) or 0),
        'auto_freeze': bool(getattr(entity, 'auto_freeze', True)),
        'progress_entries': [
            serialize_note(note, entity.unit)
            for note in getattr(entity, 'notes', [])
        ],
        'project_notes': [serialize_project_note(note) for note in project_notes],
        'mindmap': to_json_safe(mindmap),
        'stages': [serialize_stage(stage) for stage in stages],
        'stages_enabled': bool(
            kind == 'project' and getattr(entity, 'enable_stages', False)
        ),
        'combine_stage_mindmaps': bool(
            kind == 'project'
            and getattr(entity, 'combine_stage_mindmaps', False)
        ),
    }
    if kind == 'stage':
        payload['parent_project_name'] = getattr(entity, 'parent_project_name', None)
    return to_json_safe(payload)


def _serialize_deadline(value: Any) -> Any:
    if value in (None, '', 'Нет'):
        return None
    return to_json_safe(value)


def _today_goal_for_display(entity: Any, *, kind: str, infinite: bool) -> float | None:
    """Expose the same cumulative today target shown by the legacy workspace."""
    if infinite:
        return None

    deadline = getattr(entity, 'deadline', 'Нет')
    if kind == 'project':
        value = entity.get_today_display_goal_in_unit()
        has_stage_goal = bool(getattr(entity, 'has_stages', lambda: False)()) and value > 0
        return value if deadline != 'Нет' or has_stage_goal else None

    # A legacy stage uses its own daily target when it has a deadline.
    return entity.get_today_goal_in_unit() if deadline != 'Нет' else None
