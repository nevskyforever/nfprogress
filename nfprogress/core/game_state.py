"""SQLite authority for the Game aggregate and its project event consumer.

The legacy ``Gamer`` object is used here only as a compatibility façade for
the transitional HTTP API.  Its persisted representation is a versioned JSON
document in SQLite; no pickle is read or written after the Game ownership
switch.  Domain rules remain in the service/rules layer, while this module is
responsible for encoding, transactions and durable event state.
"""

from __future__ import annotations

import json
import math
import uuid
from collections.abc import Mapping
from contextlib import contextmanager
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Iterator

import engine
import game as legacy_game
import game_data

from nfprogress.core.sqlite.connection import open_database


GAME_DTO_VERSION = 1
GAME_STATE_SCHEMA_VERSION = 2
GAME_EVENT_CONTEXT_VERSION = 1

_ROOT_GAME_FIELDS = frozenset({
    'projects', 'project_order', 'project_folders', 'last',
    'notifications', 'global_streaks', 'global_streak_status',
    'max_global_streak', 'last_global_streak_bonus',
    'last_global_streak_lost_date', 'last_global_streak_lose_len',
})


def _json_safe(value: Any, seen: set[int] | None = None) -> Any:
    """Encode legacy values without invoking arbitrary pickle behavior."""
    if seen is None:
        seen = set()
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (datetime, date, time)):
        return {'__type__': 'datetime' if isinstance(value, datetime) else 'date', 'value': value.isoformat()}
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item, seen) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe(item, seen) for item in value]
    if callable(value):
        return {
            '__type__': 'callable',
            'module': getattr(value, '__module__', ''),
            'name': getattr(value, '__name__', ''),
        }
    if hasattr(value, '__dict__'):
        marker = id(value)
        if marker in seen:
            return None
        seen.add(marker)
        result = {
            '__type__': f'{type(value).__module__}.{type(value).__name__}',
            'fields': {str(key): _json_safe(item, seen) for key, item in vars(value).items()},
        }
        seen.remove(marker)
        return result
    return str(value)


def _dump(value: Any) -> str:
    return json.dumps(_json_safe(value), ensure_ascii=False, allow_nan=False, sort_keys=True)


def _decode(value: Any) -> Any:
    if isinstance(value, list):
        return [_decode(item) for item in value]
    if not isinstance(value, dict):
        return value
    kind = value.get('__type__')
    if kind == 'datetime':
        try:
            return datetime.fromisoformat(str(value['value']))
        except (KeyError, TypeError, ValueError):
            return None
    if kind == 'date':
        try:
            return date.fromisoformat(str(value['value']))
        except (KeyError, TypeError, ValueError):
            return None
    if kind == 'callable':
        return value.get('name') or None
    if isinstance(value.get('fields'), dict) and isinstance(kind, str):
        fields = {key: _decode(item) for key, item in value['fields'].items()}
        if kind == 'game_data.Buff':
            return game_data.Buff(
                fields.get('name', ''), fields.get('description', ''),
                fields.get('buff_type', game_data.Buff.POSITIVE),
                fields.get('target_cf', 'coins'), fields.get('value', 0),
                fields.get('duration_minutes'), fields.get('start_time'),
                fields.get('end_time'), fields.get('source'),
                fields.get('stackable', False),
            )
        if kind == 'game.Quest':
            quest = legacy_game.Quest(
                fields.get('quest_id', ''), fields.get('name', ''),
                fields.get('description', ''), fields.get('reward_coins', 0),
                fields.get('reward_exp', 0), fields.get('reward_items', []),
                fields.get('reward_buffs', []), fields.get('level', 1),
                fields.get('status', legacy_game.Quest.AVAILABLE),
                fields.get('quest_func'), fields.get('start_date'),
                fields.get('end_date'),
            )
            if 'reward_items_received' in fields:
                quest.reward_items_received = fields['reward_items_received']
            return quest
        if kind == 'engine.Notification':
            notification = engine.Notification(
                fields.get('text', ''), fields.get('tag'),
                fields.get('date_create'), fields.get('status', 'New'),
            )
            for key, item in fields.items():
                setattr(notification, key, item)
            return notification
        known_types = {
            'game_data.BankAccount': game_data.BankAccount,
            'game_data.Credit': game_data.Credit,
            'game_data.Deposit': game_data.Deposit,
            'game_data.Item': game_data.Item,
            'game_data.FuncItem': game_data.FuncItem,
        }
        cls = known_types.get(kind)
        if cls is not None:
            instance = cls.__new__(cls)
            for key, item in fields.items():
                setattr(instance, key, item)
            return instance
        # Unknown objects deliberately remain a tagged JSON extension.  They
        # are not silently discarded and can be re-exported by migration code.
        return {'__legacy_type__': kind, 'fields': fields}
    return {str(key): _decode(item) for key, item in value.items()}


def encode_gamer(gamer: legacy_game.Gamer) -> dict[str, Any]:
    return _json_safe(vars(gamer))


def decode_gamer(payload: Mapping[str, Any] | None) -> legacy_game.Gamer:
    gamer = legacy_game.Gamer()
    if isinstance(payload, Mapping):
        decoded = _decode(dict(payload))
        if isinstance(decoded, Mapping):
            for key, value in decoded.items():
                setattr(gamer, key, value)
    # Do not call Gamer.migrate(): legacy migration may invoke Gamer.save(),
    # which would reintroduce a PKL write after ownership has switched.  The
    # same normalization primitives are safe in-memory operations here.
    gamer.normalize_coins()
    gamer.normalize_skills()
    gamer.normalize_cf()
    gamer.normalize_motivation()
    gamer.normalize_inventory_item_names()
    gamer.update_max_health()
    gamer.update_cf()
    if not isinstance(getattr(gamer, 'bank_account', None), game_data.BankAccount):
        gamer.bank_account = game_data.BankAccount()
    gamer.bank_account.normalize()
    return gamer


def _project_game_state(data: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    projects = data.get('projects', {})
    if not isinstance(projects, Mapping):
        return result
    for stored_name, project in projects.items():
        project_id = getattr(project, 'project_id', None)
        if not isinstance(project_id, str) or not project_id:
            continue
        result[f'project:{project_id}'] = _json_safe({
            'name': getattr(project, 'name', stored_name),
            'streaks': getattr(project, 'streaks', []),
            'max_streak': getattr(project, 'max_streak', 0),
            'streak_status': getattr(project, 'streak_status', 'No'),
            'last_streak_bonus': getattr(project, 'last_streak_bonus', None),
            'last_streak_lost_date': getattr(project, 'last_streak_lost_date', None),
            'freezes': getattr(project, 'freezes', 0),
        })
        for stage in getattr(project, 'stages', []):
            stage_id = getattr(stage, 'stage_id', None)
            if not isinstance(stage_id, str) or not stage_id:
                continue
            result[f'stage:{project_id}:{stage_id}'] = _json_safe({
                'name': getattr(stage, 'name', stage_id),
                'streaks': getattr(stage, 'streaks', []),
                'max_streak': getattr(stage, 'max_streak', 0),
                'streak_status': getattr(stage, 'streak_status', 'No'),
                'last_streak_bonus': getattr(stage, 'last_streak_bonus', None),
                'last_streak_lost_date': getattr(stage, 'last_streak_lost_date', None),
                'freezes': getattr(stage, 'freezes', 0),
            })
    return result


def _game_payload(gamer: legacy_game.Gamer, data: Mapping[str, Any]) -> dict[str, Any]:
    known = {
        'dto_version': GAME_DTO_VERSION,
        'state_schema_version': GAME_STATE_SCHEMA_VERSION,
        'gamer': encode_gamer(gamer),
        'notifications': _json_safe(data.get('notifications', {'new': [], 'read': []})),
        'global_streak': _json_safe({
            key: data.get(key)
            for key in (
                'global_streaks', 'global_streak_status', 'max_global_streak',
                'last_global_streak_bonus', 'last_global_streak_lost_date',
                'last_global_streak_lose_len',
            )
            if key in data
        }),
        'project_game_state': _project_game_state(data),
    }
    known['extensions'] = {
        str(key): _json_safe(value)
        for key, value in data.items()
        if key not in _ROOT_GAME_FIELDS
    }
    return known


def _game_now() -> str:
    return datetime.now().astimezone().isoformat(timespec='seconds')


class SQLiteGameRepository:
    """Transactional persistence for the canonical Game aggregate."""

    def __init__(self, data_root: str | Path) -> None:
        self.data_root = Path(data_root).expanduser().resolve()

    @contextmanager
    def transaction(self) -> Iterator[Any]:
        with open_database(self.data_root) as db:
            with db:
                yield db

    def read_payload(self, db: Any | None = None) -> dict[str, Any]:
        owns_connection = db is None
        connection = db or open_database(self.data_root)
        try:
            row = connection.execute(
                'SELECT payload_json FROM game_state WHERE id=1',
            ).fetchone()
            if row is None:
                return {
                    'dto_version': GAME_DTO_VERSION,
                    'state_schema_version': GAME_STATE_SCHEMA_VERSION,
                    'gamer': encode_gamer(legacy_game.Gamer()),
                    'notifications': {'new': [], 'read': []},
                    'global_streak': {}, 'project_game_state': {}, 'extensions': {},
                }
            raw = json.loads(row['payload_json'])
            if isinstance(raw, dict) and 'gamer' in raw:
                return raw
            # Upgrade the old broad mirror format without treating it as a
            # pickle source.  It contains only JSON-safe Gamer fields.
            return {
                'dto_version': GAME_DTO_VERSION,
                'state_schema_version': GAME_STATE_SCHEMA_VERSION,
                'gamer': raw if isinstance(raw, dict) else {},
                'notifications': {'new': [], 'read': []},
                'global_streak': {}, 'project_game_state': {}, 'extensions': {},
            }
        finally:
            if owns_connection:
                connection.close()

    @staticmethod
    def _settings_from_connection(db: Any) -> dict[str, Any]:
        settings: dict[str, Any] = {}
        for row in db.execute('SELECT key, value_json FROM settings'):
            try:
                settings[str(row['key'])] = json.loads(row['value_json'])
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
        return settings

    def read_gamer(self, db: Any | None = None) -> legacy_game.Gamer:
        owns_connection = db is None
        connection = db or open_database(self.data_root)
        try:
            settings = self._settings_from_connection(connection)
            with legacy_game.runtime_data_context(None, settings):
                return decode_gamer(self.read_payload(connection).get('gamer'))
        finally:
            if owns_connection:
                connection.close()

    def write_gamer(self, gamer: legacy_game.Gamer, data: Mapping[str, Any] | None = None, db: Any | None = None) -> None:
        payload = self.read_payload(db)
        payload['gamer'] = encode_gamer(gamer)
        if data is not None:
            payload.update(_game_payload(gamer, data))
        self._write_payload(payload, db)

    def write_data(self, data: Mapping[str, Any], gamer: legacy_game.Gamer | None = None, db: Any | None = None) -> None:
        payload = self.read_payload(db)
        payload.update(_game_payload(gamer or self.read_gamer(db), data))
        self._write_payload(payload, db)

    def _write_payload(self, payload: Mapping[str, Any], db: Any | None = None) -> None:
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False, sort_keys=True)
        if db is not None:
            db.execute(
                'INSERT INTO game_state(id,schema_version,payload_json,updated_at) VALUES(1,?,?,?) '
                'ON CONFLICT(id) DO UPDATE SET schema_version=excluded.schema_version,payload_json=excluded.payload_json,updated_at=excluded.updated_at',
                (GAME_STATE_SCHEMA_VERSION, encoded, _game_now()),
            )
            return
        with open_database(self.data_root) as connection:
            with connection:
                connection.execute(
                    'INSERT INTO game_state(id,schema_version,payload_json,updated_at) VALUES(1,?,?,?) '
                    'ON CONFLICT(id) DO UPDATE SET schema_version=excluded.schema_version,payload_json=excluded.payload_json,updated_at=excluded.updated_at',
                    (GAME_STATE_SCHEMA_VERSION, encoded, _game_now()),
                )

    def read_game_data(self, db: Any | None = None) -> dict[str, Any]:
        payload = self.read_payload(db)
        result: dict[str, Any] = {}
        result['notifications'] = _decode(payload.get('notifications', {'new': [], 'read': []}))
        global_streak = _decode(payload.get('global_streak', {}))
        if isinstance(global_streak, Mapping):
            result.update(global_streak)
        result['_project_game_state'] = _decode(payload.get('project_game_state', {}))
        return result

    def read_projects(self, db: Any | None = None) -> dict[str, Any]:
        """Build the legacy service's read model from SQLite Projects rows.

        This adapter is deliberately read-only with respect to Projects. Game
        owned streak markers are overlaid from the Game aggregate, while the
        Projects repository remains the sole writer for project content.
        """
        owns_connection = db is None
        connection = db or open_database(self.data_root)
        runtime_context = legacy_game.runtime_data_context(
            None, self._settings_from_connection(connection),
        )
        runtime_context.__enter__()
        try:
            rows = connection.execute(
                'SELECT p.payload_json, p.id FROM projects p '
                'JOIN project_order o ON o.project_id=p.id ORDER BY o.position',
            ).fetchall()
            stage_rows = connection.execute(
                'SELECT payload_json, id, project_id FROM stages '
                'ORDER BY project_id, COALESCE((SELECT position FROM stage_order WHERE stage_id=stages.id), rowid)',
            ).fetchall()
            progress_rows = connection.execute(
                'SELECT payload_json, id, project_id, stage_id FROM progress_entries '
                'ORDER BY COALESCE((SELECT position FROM progress_order WHERE entry_id=progress_entries.id), rowid)',
            ).fetchall()
            game_data = self.read_game_data(connection)
            project_by_id: dict[str, Any] = {}
            projects: dict[str, Any] = {}
            for row in rows:
                payload = json.loads(row['payload_json'])
                project = _project_from_payload(payload, row['id'])
                project_by_id[row['id']] = project
                projects[project.name] = project
            stages_by_id: dict[str, Any] = {}
            for row in stage_rows:
                project = project_by_id.get(row['project_id'])
                if project is None:
                    continue
                stage = _stage_from_payload(json.loads(row['payload_json']), row['id'], project.name)
                stages_by_id[row['id']] = stage
                project.stages.append(stage)
                project.enable_stages = True
            for row in progress_rows:
                owner = stages_by_id.get(row['stage_id']) if row['stage_id'] else project_by_id.get(row['project_id'])
                if owner is not None:
                    owner.notes.append(_note_from_payload(json.loads(row['payload_json'])))
            for key, values in (game_data.get('_project_game_state') or {}).items():
                if not isinstance(values, Mapping):
                    continue
                owner = _project_owner_by_key(project_by_id, stages_by_id, key)
                if owner is not None:
                    for field in ('streaks', 'max_streak', 'streak_status', 'last_streak_bonus', 'last_streak_lost_date', 'freezes'):
                        if field in values:
                            setattr(owner, field, values[field])
            result = {'projects': projects}
            result.update({key: value for key, value in game_data.items() if not key.startswith('_')})
            result['_project_game_state'] = game_data.get('_project_game_state', {})
            return result
        finally:
            runtime_context.__exit__(None, None, None)
            if owns_connection:
                connection.close()

    def write_game_data(self, data: Mapping[str, Any], db: Any | None = None) -> None:
        payload = self.read_payload(db)
        if 'notifications' in data:
            payload['notifications'] = _json_safe(data['notifications'])
        payload['global_streak'] = _json_safe({
            key: data[key] for key in (
                'global_streaks', 'global_streak_status', 'max_global_streak',
                'last_global_streak_bonus', 'last_global_streak_lost_date',
                'last_global_streak_lose_len',
            ) if key in data
        })
        if '_project_game_state' in data:
            payload['project_game_state'] = _json_safe(data['_project_game_state'])
        self._write_payload(payload, db)

    def pending_events(self, db: Any | None = None) -> list[Any]:
        connection = db or open_database(self.data_root)
        try:
            return connection.execute(
                "SELECT * FROM domain_events WHERE consumer='game' AND processed_at IS NULL "
                "AND COALESCE(status, 'pending') != 'failed' ORDER BY created_at, event_id",
            ).fetchall()
        finally:
            if db is None:
                connection.close()


def _numeric(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _gamer_cf(gamer: Mapping[str, Any], key: str, default: float = 1.0) -> float:
    coefficients = gamer.get('cf')
    if not isinstance(coefficients, Mapping):
        return default
    value = coefficients.get(key, default)
    if isinstance(value, Mapping):
        value = value.get('value', default)
    return _numeric(value, default)


def _rounded_increment(value: float) -> float:
    return round(math.ceil((value - 1e-9) * 10) / 10, 1)


class GameEventConsumer:
    """Apply F2 events exactly once in the same transaction as Game state."""

    def __init__(self, data_root: str | Path, *, rules: Any | None = None) -> None:
        self.repository = SQLiteGameRepository(data_root)
        self.rules = rules or DeterministicGameRules()

    def process_pending(self, *, limit: int = 100) -> dict[str, int]:
        processed = failed = 0
        with self.repository.transaction() as db:
            rows = db.execute(
                "SELECT * FROM domain_events WHERE consumer='game' AND processed_at IS NULL "
                "AND COALESCE(status, 'pending') != 'failed' ORDER BY created_at, event_id LIMIT ?",
                (max(1, int(limit)),),
            ).fetchall()
            for row in rows:
                try:
                    payload = json.loads(row['context_json'])
                    if not isinstance(payload, dict):
                        raise ValueError('event context must be an object')
                    if int(row['version'] or 1) != GAME_EVENT_CONTEXT_VERSION:
                        raise ValueError(f"unsupported event version: {row['version']}")
                    state = self.repository.read_payload(db)
                    state = self.rules.apply(state, row, payload)
                    self.repository._write_payload(state, db)
                    db.execute(
                        "UPDATE domain_events SET processed_at=strftime('%Y-%m-%dT%H:%M:%SZ','now'), status='processed', last_error=NULL WHERE event_id=? AND processed_at IS NULL",
                        (row['event_id'],),
                    )
                    processed += 1
                except Exception as error:
                    attempt = int(row['attempt_count'] or 0) + 1
                    poison = attempt >= 3
                    db.execute(
                        "UPDATE domain_events SET attempt_count=?, last_error=?, failed_at=CASE WHEN ? THEN strftime('%Y-%m-%dT%H:%M:%SZ','now') ELSE failed_at END, status=CASE WHEN ? THEN 'failed' ELSE 'pending' END WHERE event_id=?",
                        (attempt, str(error)[:1000], int(poison), int(poison), row['event_id']),
                    )
                    failed += 1
        return {'processed': processed, 'failed': failed}


class DeterministicGameRules:
    """Small, pure event rules; catalogs and UI orchestration stay elsewhere."""

    def apply(self, state: Mapping[str, Any], event: Any, context: Mapping[str, Any]) -> dict[str, Any]:
        result = json.loads(json.dumps(state, ensure_ascii=False, allow_nan=False))
        gamer = result.setdefault('gamer', {})
        if not isinstance(gamer, dict):
            raise ValueError('canonical gamer payload is not an object')
        event_type = str(event['event_type'])
        delta = _numeric(event['delta_symbols'])
        if event_type == 'ProgressAdded' and delta > 0:
            multiplier = (
                1 + _numeric(gamer.get('inspiration')) / legacy_game.MAX_INSPIRATION * 0.1
            ) * (1 + _numeric(gamer.get('writing_reward_bonus')))
            exp_reward = _rounded_increment(
                delta / 100 * game_data.base_exp_bonus
                * _gamer_cf(gamer, 'exp') * multiplier
            )
            coin_reward = _rounded_increment(
                delta / 100 * game_data.base_coin_bonus
                * _gamer_cf(gamer, 'coins') * multiplier
            )
            gamer['exp'] = _numeric(gamer.get('exp')) + exp_reward
            gamer['coins'] = _rounded_increment(_numeric(gamer.get('coins')) + coin_reward)
            gamer['writing_reward_bonus'] = 0.0
        elif event_type == 'ProgressDeleted':
            # Legacy semantics are intentionally non-reversible: deletion is
            # recorded for audit but does not claw back an already granted reward.
            result.setdefault('extensions', {}).setdefault('progress_deletions', []).append(
                str(event['event_id']),
            )
        elif event_type in {'ProjectCompleted', 'StageCompleted'}:
            key = str(context.get('key') or event['project_id'])
            claimed = gamer.setdefault('complete_bonus_projects', [])
            if key not in claimed:
                claimed.append(key)
                total = max(0.0, _numeric(context.get('total_symbols')))
                multiplier = 0.25 if event_type == 'StageCompleted' else 1.0
                reward = round(total / 1000 + 0.5) * 100 * multiplier
                gamer['coins'] = _numeric(gamer.get('coins')) + reward
                gamer['exp'] = _numeric(gamer.get('exp')) + reward * 100
        elif event_type in {'ProjectStatusChanged', 'ProjectDeleted'}:
            # Lifecycle events can be safely observed without deleting earned
            # rewards. Project references remain historical Game evidence.
            result.setdefault('extensions', {}).setdefault('lifecycle_events', []).append(
                str(event['event_id']),
            )
        else:
            raise ValueError(f'unsupported game event type: {event_type}')
        return result


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _note_from_payload(payload: Mapping[str, Any]) -> Any:
    created = _parse_datetime(payload.get('created_at')) or datetime.now()
    note = engine.Note(
        payload.get('new_total_symbols', payload.get('new_total', 0)),
        payload.get('added_symbols', payload.get('added', 0)),
        payload.get('added_progress', 0),
        date_create=created,
        entry_id=payload.get('id'),
    )
    return note


def _project_from_payload(payload: Mapping[str, Any], project_id: str) -> Any:
    goal = float('inf') if payload.get('infinite') else payload.get('goal')
    project = engine.Project(
        name=str(payload.get('name') or project_id), goal=goal,
        total_symbols=payload.get('total', 0), progress=payload.get('progress', 0),
        unit=str(payload.get('unit') or 'symbols'),
        status=str(payload.get('status') or 'активен'),
        deadline=payload.get('deadline') or 'Нет',
    )
    project.project_id = project_id
    project._name = str(payload.get('name') or project_id)
    project._goal = goal
    project._total_symbols = payload.get('total', 0)
    project._progress = payload.get('progress', 0)
    project.streak_status = str(payload.get('streak_status') or 'No')
    project.max_streak = int(payload.get('max_streak') or 0)
    project.personal_goal_for_the_day = payload.get('personal_goal', 0)
    project.enable_stages = bool(payload.get('stages_enabled', False))
    project.combine_stage_mindmaps = bool(payload.get('combine_stage_mindmaps', False))
    project.folder_id = payload.get('folder_id')
    project.project_notes = payload.get('project_notes', []) if isinstance(payload.get('project_notes'), list) else []
    project.notes = [_note_from_payload(entry) for entry in payload.get('progress_entries', []) if isinstance(entry, Mapping)]
    return project


def _stage_from_payload(payload: Mapping[str, Any], stage_id: str, parent_name: str) -> Any:
    stage = engine.Stage(
        name=str(payload.get('name') or stage_id),
        goal=float('inf') if payload.get('infinite') else payload.get('goal'),
        total_symbols=payload.get('total', 0), progress=payload.get('progress', 0),
        unit=str(payload.get('unit') or 'symbols'),
        status=str(payload.get('status') or 'активен'),
        deadline=payload.get('deadline') or 'Нет',
        parent_project_name=parent_name,
        stage_id=stage_id,
    )
    stage._name = str(payload.get('name') or stage_id)
    stage._goal = float('inf') if payload.get('infinite') else payload.get('goal')
    stage._total_symbols = payload.get('total', 0)
    stage._progress = payload.get('progress', 0)
    stage.streak_status = str(payload.get('streak_status') or 'No')
    stage.max_streak = int(payload.get('max_streak') or 0)
    stage.personal_goal_for_the_day = payload.get('personal_goal', 0)
    stage.project_notes = payload.get('project_notes', []) if isinstance(payload.get('project_notes'), list) else []
    stage.notes = [_note_from_payload(entry) for entry in payload.get('progress_entries', []) if isinstance(entry, Mapping)]
    return stage


def _project_owner_by_key(projects: Mapping[str, Any], stages: Mapping[str, Any], key: str) -> Any | None:
    if key in projects:
        return projects[key]
    if key in stages:
        return stages[key]
    return None


__all__ = [
    'GAME_DTO_VERSION', 'GAME_STATE_SCHEMA_VERSION', 'GameEventConsumer',
    'SQLiteGameRepository', 'DeterministicGameRules', 'encode_gamer',
    'decode_gamer',
]
