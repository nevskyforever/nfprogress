"""Convert legacy Python models into transport-safe dictionaries."""

from __future__ import annotations

import math
import uuid
from collections.abc import Mapping
from datetime import date, datetime, time, timezone
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


def _timestamp_key(value: str) -> datetime:
    """Parse stored date/timestamps consistently for latest-resource fields."""
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _latest_timestamp(*values: Any) -> str | None:
    candidates: list[str] = []
    for value in values:
        try:
            safe_value = to_json_safe(value)
        except TypeError:
            continue
        if isinstance(safe_value, str) and safe_value:
            candidates.append(safe_value)
    return max(candidates, key=_timestamp_key, default=None)


def _entity_mindmap_timestamp(entity: Any, mindmap: dict | None) -> str | None:
    timestamp = getattr(entity, 'mindmap_updated_at', None)
    if timestamp in (None, '') and mindmap is not None:
        # Legacy saves predate the dedicated timestamp. The edit date is the
        # best available lower-resolution indication for an existing map.
        timestamp = getattr(entity, 'edit_date', None)
    return _latest_timestamp(timestamp)


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
    serialized_stages = [serialize_stage(stage) for stage in stages]
    notes_updated_at = _latest_timestamp(
        getattr(entity, 'notes_updated_at', None),
        *(note.get('updated_at') for note in project_notes),
        *(
            stage.get('notes_updated_at')
            for stage in serialized_stages
        ),
    )
    mindmap_updated_at = _latest_timestamp(
        _entity_mindmap_timestamp(entity, mindmap),
        *(
            stage.get('mindmap_updated_at')
            for stage in serialized_stages
        ),
    )
    today_goal = _today_goal_for_display(entity, kind=kind, infinite=infinite)
    plan = getattr(entity, 'project_plan', {})
    daily_goal_symbols = plan.get('daily_goal_symbols') if isinstance(plan, dict) else None

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
        'notes_updated_at': notes_updated_at,
        'mindmap_updated_at': mindmap_updated_at,
        'completed_at': to_json_safe(getattr(entity, 'complete_date', None)),
        'personal_goal': to_json_safe(
            getattr(entity, 'personal_goal_for_the_day', 0),
        ),
        'today_goal': to_json_safe(today_goal),
        'planning_date': engine.today_for_test().isoformat(),
        'plan_daily_goal': to_json_safe(
            engine.unit_converter('symbols', daily_goal_symbols, entity.unit)
            if isinstance(daily_goal_symbols, (int, float)) else None
        ),
        'added_today': to_json_safe(entity.get_added_today_in_unit()),
        'remaining': None if infinite else to_json_safe(entity.get_need_write_in_unit()),
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
        'stages': serialized_stages,
        'stages_enabled': bool(
            kind == 'project' and getattr(entity, 'enable_stages', False)
        ),
        'combine_stage_mindmaps': bool(
            kind == 'project'
            and getattr(entity, 'combine_stage_mindmaps', False)
        ),
        'cover_image': (
            engine.normalize_project_cover_image(getattr(entity, 'cover_image', None))
            if kind == 'project' else None
        ),
        'folder_id': (
            getattr(entity, 'folder_id', None) if kind == 'project' else None
        ),
        'sync_available': bool(
            getattr(entity, 'synch', None)
            or (kind == 'project' and any(getattr(stage, 'synch', None) for stage in stages))
        ),
        'work_method': getattr(entity, 'work_method', 'sync' if getattr(entity, 'synch', None) is not None else 'manual'),
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

    # A stage can have a fixed daily goal without a deadline too.
    has_personal_goal = bool(getattr(entity, 'personal_goal_for_the_day', 0))
    return entity.get_today_goal_in_unit() if deadline != 'Нет' or has_personal_goal else None
