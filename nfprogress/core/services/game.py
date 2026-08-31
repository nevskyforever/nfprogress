"""Qt-free application service for the legacy nfprogress game domain.

The service deliberately delegates reward calculations and state transitions to
``game.Gamer``.  It adds three boundaries that the legacy widget controller did
not provide: repository-scoped transactions, JSON-safe projections, and
server-side resolution of every catalogue key and price.
"""

from __future__ import annotations

import math
import pickle
import uuid
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from threading import RLock
from typing import Any

import engine
import game as legacy_game
import game_data

from nfprogress.core.errors import ConflictError, NotFoundError, ValidationError


JSONDict = dict[str, Any]
_LEGACY_GAME_LOCK = RLock()
_MAX_ITEM_COMMAND_COUNT = 10_000
_FREEZE_CATEGORY = 'Предметы'
_FREEZE_ITEM_KEY = 'Заморозка'


def _iso(value: Any) -> str | None:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if value is None:
        return None
    return str(value)


def _json_value(value: Any) -> Any:
    """Return a recursively JSON-safe representation of legacy values."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_value(item) for item in value]
    return str(value)


def serialize_profile(gamer: legacy_game.Gamer) -> JSONDict:
    level = max(1, int(getattr(gamer, 'level', 1)))
    next_level_exp = (
        game_data.levels[level]
        if level < len(game_data.levels) - 1 else None
    )
    return {
        'level': level,
        'experience': float(getattr(gamer, 'exp', 0)),
        'next_level_experience': next_level_exp,
        'coins': float(gamer.get_coins()),
        'inflation': float(gamer.calculate_inflation()),
        'health': float(getattr(gamer, 'health', 0)),
        'max_health': float(gamer.get_max_health()),
        'inspiration': float(getattr(gamer, 'inspiration', 0)),
        'max_inspiration': legacy_game.MAX_INSPIRATION,
        'writing_session_streak': int(gamer.writing_session_streak),
        'session_streak_shields': int(gamer.session_streak_shields),
        'session_grade_boosts': int(gamer.session_grade_boosts),
        'pending_bonuses': {
            'writing': float(gamer.writing_reward_bonus),
            'session': float(gamer.session_reward_bonus),
            'challenge': float(gamer.challenge_reward_bonus),
            'manuscript': float(gamer.manuscript_reward_bonus),
        },
    }


def serialize_skills(gamer: legacy_game.Gamer) -> JSONDict:
    return {
        'available_points': int(gamer.available_skill_points),
        'points_per_level': legacy_game.SKILL_POINTS_PER_LEVEL,
        'items': [
            {
                'key': key,
                'name': meta['name'],
                'points': int(gamer.skills.get(key, 0)),
                'target': meta['target_cf'],
                'bonus': float(gamer.get_skill_bonus(key)),
            }
            for key, meta in legacy_game.SKILL_META.items()
        ],
        'coefficients': [
            {
                'key': key,
                'name': value.get('name', key),
                'description': gamer.get_cf_description(key),
                'value': float(value.get('value', 0)),
                'base_value': float(value.get('base_value', 0)),
            }
            for key, value in gamer.cf.items()
            if isinstance(value, dict)
        ],
    }


def serialize_buff(
        buff: game_data.Buff,
        *,
        stacks: int = 1,
        now: datetime | None = None,
) -> JSONDict:
    now = now or legacy_game.get_effective_now()
    remaining = buff.remaining_time(now)
    return {
        'name': str(buff.name),
        'description': str(buff.description),
        'type': str(buff.buff_type),
        'target': str(buff.target_cf),
        'value': float(buff.value),
        'stacks': max(1, int(stacks)),
        'duration_minutes': buff.duration_minutes,
        'started_at': _iso(buff.start_time),
        'expires_at': _iso(buff.end_time),
        'remaining_seconds': (
            None if remaining is None else max(0, math.ceil(remaining.total_seconds()))
        ),
        'source': _iso(buff.source),
        'stackable': bool(buff.stackable),
    }


def serialize_buffs(gamer: legacy_game.Gamer) -> JSONDict:
    now = legacy_game.get_effective_now()
    return {
        'server_time': now.isoformat(),
        'positive': [
            serialize_buff(buff, stacks=stacks, now=now)
            for buff, stacks in gamer.get_all_buffs(positive=True)
        ],
        'negative': [
            serialize_buff(buff, stacks=stacks, now=now)
            for buff, stacks in gamer.get_all_buffs(positive=False)
        ],
    }


def _registry_item_payload(
        gamer: legacy_game.Gamer,
        category: str,
        key: str,
        item: game_data.Item,
        *,
        include_count: bool,
) -> JSONDict:
    price = gamer.round_money(item.price)
    sell_price = gamer.round_money(item.sell_price)
    category_items = gamer.items.get(category, {})
    count = int(category_items.get(key, 0)) if isinstance(category_items, dict) else 0
    maximum = getattr(item, 'maximum_quantity_in_stock', None)
    effect = None
    item_function = getattr(item, '_func', None)
    if callable(item_function):
        try:
            effect = item_function('?')
        except Exception:
            effect = None
    usable = bool(getattr(item, 'usable', False))
    payload: JSONDict = {
        'id': f'{category}:{key}',
        'key': key,
        'category': category,
        'name': str(item.name),
        'description': str(item.description),
        'effect': str(effect) if effect else None,
        'level': int(getattr(item, 'level', 1)),
        'price': float(price),
        'sell_price': float(sell_price),
        'sellable': bool(getattr(item, 'sellable', True)),
        'credit_allowed': bool(getattr(item, 'credit_allowed', True)),
        'usable': usable,
        'buy': bool(getattr(item, 'Buy', False)),
        'maximum_quantity': maximum,
        'available_for_level': gamer.level >= getattr(item, 'level', 1),
        'buffs': [
            serialize_buff(buff)
            for buff in item.get_buffs()
            if buff is not None
        ],
    }
    if include_count:
        payload['count'] = max(0, count)
    payload['can_buy'] = bool(
        payload['buy']
        and
        payload['available_for_level']
        and gamer.coins >= price
        and (maximum is None or count < maximum)
    )
    return payload


def serialize_inventory(gamer: legacy_game.Gamer) -> JSONDict:
    categories: list[JSONDict] = []
    known_categories = list(game_data.ITEM_REGISTRY)
    extra_categories = [
        str(category) for category in gamer.items
        if category not in game_data.ITEM_REGISTRY
    ]
    for category in [*known_categories, *extra_categories]:
        raw_items = gamer.items.get(category, {})
        if not isinstance(raw_items, dict):
            raw_items = {}
        item_payloads: list[JSONDict] = []
        for key, raw_count in raw_items.items():
            try:
                count = max(0, int(raw_count))
            except (TypeError, ValueError):
                count = 0
            if count <= 0:
                continue
            registry_key, item = game_data.find_registry_item(category, key)
            if item is not None and registry_key is not None:
                payload = _registry_item_payload(
                    gamer, category, registry_key, item, include_count=True,
                )
                payload['count'] = count
            else:
                payload = {
                    'id': f'{category}:{key}',
                    'key': str(key),
                    'category': category,
                    'name': str(key),
                    'description': None,
                    'count': count,
                    'known': False,
                    'usable': False,
                    'buy': False,
                    'sellable': False,
                }
            payload.setdefault('known', True)
            item_payloads.append(payload)
        categories.append({'key': category, 'name': category, 'items': item_payloads})
    return {'categories': categories}


def _notification_value(notification: Any, key: str, default: Any = None) -> Any:
    if isinstance(notification, Mapping):
        return notification.get(key, default)
    return getattr(notification, key, default)


def _notification_buckets(projects: JSONDict) -> dict[str, list[Any]]:
    """Read both historical notification layouts without modifying a save."""
    raw = projects.get('notifications')
    if isinstance(raw, Mapping):
        new = raw.get('new', [])
        read = raw.get('read', [])
        return {
            'new': list(new) if isinstance(new, list) else [],
            'read': list(read) if isinstance(read, list) else [],
        }
    # Very old data used a plain notification list. Preserve it as unread
    # rather than dropping a user-visible event during the UI migration.
    return {'new': list(raw) if isinstance(raw, list) else [], 'read': []}


def _notification_id(notification: Any, bucket: str, index: int) -> str:
    existing = _notification_value(notification, 'notification_id')
    if not isinstance(existing, str) or not existing:
        existing = _notification_value(notification, 'id')
    if isinstance(existing, str) and existing:
        return existing
    seed = '\x1f'.join((
        bucket,
        str(index),
        str(_notification_value(notification, 'text', notification)),
        str(_notification_value(notification, 'tag', '')),
        str(_notification_value(notification, 'date_create', '')),
    ))
    return uuid.uuid5(
        uuid.NAMESPACE_URL, f'nfprogress-notification:{seed}',
    ).hex


def _serialize_notification(
        notification: Any, *, bucket: str, index: int,
) -> JSONDict:
    text = _notification_value(notification, 'text', notification)
    tag = _notification_value(notification, 'tag')
    created_at = _notification_value(notification, 'date_create')
    return {
        'id': _notification_id(notification, bucket, index),
        'text': str(text),
        'tag': str(tag) if tag is not None else None,
        'created_at': _iso(created_at),
        'status': bucket,
    }


def serialize_notifications(projects: JSONDict) -> JSONDict:
    buckets = _notification_buckets(projects)
    unread = [
        _serialize_notification(notification, bucket='new', index=index)
        for index, notification in enumerate(buckets['new'])
    ]
    read = [
        _serialize_notification(notification, bucket='read', index=index)
        for index, notification in enumerate(buckets['read'])
    ]
    return {
        'unread': unread,
        'read': read,
        'unread_count': len(unread),
    }


def _append_game_notifications(projects: JSONDict, messages: list[str]) -> bool:
    """Store command outcomes in the shared notification history once."""
    messages = [message.strip() for message in messages if isinstance(message, str) and message.strip()]
    if not messages:
        return False
    buckets = _notification_buckets(projects)
    existing = {
        str(_notification_value(notification, 'text', notification))
        for notification in buckets['new']
    }
    changed = False
    for message in messages:
        # Bank operations already write their own persistent event inside the
        # transaction; avoid making a second identical record for it.
        if message in existing:
            continue
        # Keep a bank handler's transaction event as the newest record; it is
        # produced while the command runs and can carry richer bank metadata.
        buckets['new'].insert(0, engine.Notification(message, tag='game'))
        existing.add(message)
        changed = True
    if changed:
        projects['notifications'] = buckets
    return changed


def _set_notification_identifier(
        notification: Any,
        notification_id: str,
        *,
        bucket: str,
) -> tuple[Any, bool]:
    """Attach a stable API identifier without changing legacy message text."""
    if isinstance(notification, dict):
        if notification.get('notification_id') == notification_id:
            return notification, False
        notification['notification_id'] = notification_id
        return notification, True
    if isinstance(notification, Mapping):
        updated = dict(notification)
        updated['notification_id'] = notification_id
        return updated, True
    if hasattr(notification, '__dict__'):
        if getattr(notification, 'notification_id', None) == notification_id:
            return notification, False
        setattr(notification, 'notification_id', notification_id)
        return notification, True

    # A very old save may contain a plain string.  Keep its visible text and
    # turn it into the legacy notification object only when a stable ID is
    # needed for an API action.
    legacy_notification = engine.Notification(
        str(notification),
        status='Read' if bucket == 'read' else 'New',
    )
    legacy_notification.notification_id = notification_id
    return legacy_notification, True


def _ensure_notification_ids(projects: JSONDict) -> bool:
    """Persist IDs for legacy notification records before exposing them to UI.

    The old Qt application did not store identifiers.  A generated UUID is
    saved once, so moving a notification from ``new`` to ``read`` never makes
    the frontend's identifier depend on a list position.
    """
    raw = projects.get('notifications')
    buckets = _notification_buckets(projects)
    has_notifications = bool(buckets['new'] or buckets['read'])
    if not has_notifications:
        return False

    changed = False
    for bucket, entries in buckets.items():
        for index, notification in enumerate(entries):
            existing = _notification_value(notification, 'notification_id')
            if not isinstance(existing, str) or not existing:
                existing = _notification_value(notification, 'id')
            if isinstance(existing, str) and existing:
                continue
            entries[index], item_changed = _set_notification_identifier(
                notification,
                uuid.uuid4().hex,
                bucket=bucket,
            )
            changed = changed or item_changed

    # Convert a non-dictionary historical envelope only when it contains a
    # real event.  Empty default lists keep their exact legacy representation.
    if changed and not isinstance(raw, Mapping):
        projects['notifications'] = buckets
    elif changed and isinstance(raw, dict):
        raw['new'] = buckets['new']
        raw['read'] = buckets['read']
    elif changed:
        projects['notifications'] = {**dict(raw), **buckets}
    return changed


def _mark_notification_read(notification: Any, notification_id: str) -> Any:
    if isinstance(notification, dict):
        notification['notification_id'] = notification_id
        notification['status'] = 'Read'
        return notification
    if isinstance(notification, Mapping):
        updated = dict(notification)
        updated['notification_id'] = notification_id
        updated['status'] = 'Read'
        return updated
    if not hasattr(notification, '__dict__'):
        notification = engine.Notification(str(notification), status='Read')
    if hasattr(notification, 'set_status'):
        notification.set_status('Read')
    else:
        setattr(notification, 'status', 'Read')
    setattr(notification, 'notification_id', notification_id)
    return notification


def _freeze_inventory_count(gamer: legacy_game.Gamer) -> int:
    category_items = gamer.items.get(_FREEZE_CATEGORY, {})
    if not isinstance(category_items, Mapping):
        return 0
    try:
        return max(0, int(category_items.get(_FREEZE_ITEM_KEY, 0)))
    except (TypeError, ValueError):
        return 0


def serialize_streak_freezes(
        gamer: legacy_game.Gamer,
        projects: JSONDict,
) -> JSONDict:
    """Describe the freeze targets without exposing legacy project objects."""
    today = engine.today_for_test()
    inventory_count = _freeze_inventory_count(gamer)
    project_options: list[JSONDict] = []
    raw_projects = projects.get('projects', {})
    if isinstance(raw_projects, Mapping):
        for stored_name, project in raw_projects.items():
            if not isinstance(project, engine.Project):
                continue
            project_id = getattr(project, 'project_id', None)
            if not project_id:
                continue
            sources = engine.get_project_freeze_sources(project, today)
            if not sources:
                continue
            source_payloads = []
            for source in sources:
                is_stage = isinstance(source, engine.Stage)
                source_id = getattr(source, 'stage_id', None) if is_stage else project_id
                source_payloads.append({
                    'id': str(source_id),
                    'name': str(getattr(source, 'name', '')),
                    'is_stage': is_stage,
                    'streak_length': int(engine.streak_length(source.streaks)),
                })
            project_options.append({
                'project_id': str(project_id),
                'name': str(getattr(project, 'name', stored_name)),
                'source_count': len(source_payloads),
                'max_streak': max(
                    source['streak_length'] for source in source_payloads
                ),
                'sources': source_payloads,
            })
    return {
        'date': today.isoformat(),
        'inventory_count': inventory_count,
        'global_available': bool(
            inventory_count > 0
            and engine.can_freeze_global_streak(projects, today)
        ),
        'projects': project_options if inventory_count > 0 else [],
    }


def serialize_quest(quest: legacy_game.Quest) -> JSONDict:
    return {
        'id': str(quest.quest_id),
        'name': str(quest.name),
        'description': str(quest.description),
        'status': str(quest.status),
        'required_level': int(quest.level),
        'started_at': _iso(quest.start_date),
        'finished_at': _iso(quest.end_date),
        'reward': {
            'coins': float(quest.reward_coins),
            'experience': float(quest.reward_exp),
            'items': _json_value(quest.reward_items),
            'buffs': [serialize_buff(buff) for buff in quest.reward_buffs if buff],
        },
    }


def serialize_quests(gamer: legacy_game.Gamer) -> JSONDict:
    quests = [serialize_quest(quest) for quest in gamer.quests]
    return {
        'items': quests,
        'by_status': {
            status: [quest for quest in quests if quest['status'] == status]
            for status in (
                legacy_game.Quest.AVAILABLE,
                legacy_game.Quest.ACTIVE,
                legacy_game.Quest.COMPLETED,
            )
        },
    }


def _daily_option_payload(option: Mapping[str, Any]) -> JSONDict:
    challenge_type = str(option.get('type', 'symbols'))
    difficulty = str(option.get('difficulty', 'normal'))
    type_meta = legacy_game.DAILY_CHALLENGE_TYPES.get(challenge_type, {})
    difficulty_meta = legacy_game.DAILY_CHALLENGE_DIFFICULTIES.get(difficulty, {})
    return {
        'option_id': str(option.get('option_id', f'{challenge_type}:{difficulty}')),
        'date': str(option.get('date', '')),
        'type': challenge_type,
        'name': type_meta.get('name', challenge_type),
        'description': type_meta.get('description', ''),
        'difficulty': difficulty,
        'difficulty_name': difficulty_meta.get('name', difficulty),
        'target': int(option.get('target', 0)),
        'progress': int(option.get('progress', 0)),
        'completed': bool(option.get('completed', False)),
        'reward': {
            'coins': float(option.get('reward_coins', 0)),
            'experience': float(option.get('reward_exp', 0)),
            'inspiration': 10,
        },
    }


def serialize_daily_challenge(gamer: legacy_game.Gamer) -> JSONDict:
    return {
        'change_cost': legacy_game.DAILY_CHALLENGE_CHANGE_COST,
        'current': (
            _daily_option_payload(gamer.daily_challenge)
            if gamer.daily_challenge else None
        ),
        'options': [
            _daily_option_payload(option)
            for option in gamer.daily_challenge_options
        ],
        'history': list(gamer.daily_challenge_history),
    }


def serialize_weekly_challenge(gamer: legacy_game.Gamer) -> JSONDict:
    current = None
    if gamer.weekly_challenge:
        challenge = gamer.weekly_challenge
        key = str(challenge.get('key', ''))
        meta = legacy_game.WEEKLY_CHALLENGES.get(key)
        if meta:
            current = {
                'key': key,
                'name': meta['name'],
                'description': meta['description'],
                'week_start': str(challenge.get('week_start', '')),
                'target': int(meta['target']),
                'progress': int(challenge.get('progress', 0)),
                'writing_days': [str(day) for day in challenge.get('writing_days', [])],
                'completed': bool(challenge.get('completed', False)),
                'reward': {
                    'coins': float(meta['reward_coins']),
                    'experience': float(meta['reward_exp']),
                    'inspiration': 20,
                },
            }
    return {
        'current': current,
        'catalog': [
            {
                'key': key,
                'name': meta['name'],
                'description': meta['description'],
                'target': int(meta['target']),
                'reward': {
                    'coins': float(meta['reward_coins']),
                    'experience': float(meta['reward_exp']),
                    'inspiration': 20,
                },
            }
            for key, meta in legacy_game.WEEKLY_CHALLENGES.items()
        ],
    }


def serialize_writing_session(gamer: legacy_game.Gamer) -> JSONDict:
    server_time = legacy_game.get_session_now()
    active = None
    if gamer.writing_session:
        session = gamer.writing_session
        started_at = session.get('started_at')
        duration_minutes = int(session.get('duration_minutes', 0))
        active = {
            'started_at': _iso(started_at),
            'ends_at': (
                (started_at + timedelta(minutes=duration_minutes)).isoformat()
                if isinstance(started_at, datetime) else None
            ),
            'duration_minutes': duration_minutes,
            'target_symbols': int(session.get('target_symbols', 0)),
            'progress': int(session.get('progress', 0)),
            'intention': str(session.get('intention', '')),
            'mode': str(session.get('mode', 'flow')),
            'remaining_seconds': int(gamer.writing_session_remaining_seconds()),
        }
    return {
        'server_time': server_time.isoformat(),
        'active': active,
        'streak': int(gamer.writing_session_streak),
        'history': _json_value(gamer.writing_session_history),
        'modes': [
            {'key': key, **_json_value(meta)}
            for key, meta in legacy_game.WRITING_SESSION_MODES.items()
        ],
        'grades': [
            {
                'key': key,
                'name': name,
                'target_ratio': ratio,
                'reward_multiplier': multiplier,
            }
            for key, name, ratio, multiplier in legacy_game.WRITING_SESSION_GRADES
        ],
        'allowed_durations_minutes': [15, 25, 45, 60],
    }


def serialize_specializations(gamer: legacy_game.Gamer) -> JSONDict:
    return {
        'selected': gamer.specialization,
        'unlocks_at_level': legacy_game.SPECIALIZATION_LEVEL,
        'change_cooldown_days': legacy_game.SPECIALIZATION_CHANGE_COOLDOWN_DAYS,
        'change_days_remaining': gamer.specialization_change_days_remaining(),
        'mastery_thresholds': list(legacy_game.SPECIALIZATION_MASTERY_THRESHOLDS),
        'items': [
            {
                'key': key,
                'name': meta['name'],
                'description': meta['description'],
                'selected': key == gamer.specialization,
                'mastery_experience': int(gamer.specialization_mastery.get(key, 0)),
                'mastery_rank': int(gamer.specialization_mastery_rank(key)),
                'passive_bonus': float(gamer.get_specialization_bonus(key)),
                'ability': {
                    'name': legacy_game.SPECIALIZATION_ABILITIES[key]['name'],
                    'description': legacy_game.SPECIALIZATION_ABILITIES[key]['description'],
                    'cooldown_hours': legacy_game.SPECIALIZATION_ABILITY_COOLDOWN_HOURS,
                    'remaining_seconds': int(
                        gamer.specialization_ability_remaining_seconds(key)
                    ),
                    'pending': bool(gamer.specialization_ability_effects.get(key)),
                },
            }
            for key, meta in legacy_game.SPECIALIZATIONS.items()
        ],
    }


def serialize_manuscripts_and_cabinet(
        gamer: legacy_game.Gamer,
        owner_labels: Mapping[str, str],
) -> JSONDict:
    journeys = [
        {
            'owner_key': key,
            'owner_name': owner_labels.get(key),
            'received_milestones': list(values),
        }
        for key, values in sorted(gamer.manuscript_journeys.items())
    ]
    relics = []
    for key, meta in legacy_game.CABINET_RELICS.items():
        unlocked = key in gamer.cabinet_relics
        current, required = gamer.cabinet_relic_progress(key)
        relics.append({
            'key': key,
            'unlocked': unlocked,
            'name': meta['name'] if unlocked else None,
            'description': meta['description'] if unlocked else None,
            'condition': meta['condition'],
            'progress': current,
            'required': required,
            'effect_type': meta['effect_type'] if unlocked else None,
            'bonus': float(meta['bonus']) if unlocked else None,
            'effect_description': meta['effect_description'] if unlocked else None,
        })
    unlocked_sets = set(gamer.get_unlocked_cabinet_sets())
    cabinet_sets = [
        {
            'key': key,
            'name': meta['name'],
            'description': meta['description'],
            'relics': list(meta['relics']),
            'unlocked': key in unlocked_sets,
            'effect_type': meta['effect_type'],
            'bonus': float(meta['bonus']),
        }
        for key, meta in legacy_game.CABINET_SETS.items()
    ]
    return {
        'journeys': journeys,
        'milestones': _json_value(legacy_game.MANUSCRIPT_MILESTONES),
        'cabinet': {'relics': relics, 'sets': cabinet_sets},
    }


def serialize_bank_summary(gamer: legacy_game.Gamer) -> JSONDict:
    account = gamer.bank_account
    if account is None:
        return {'credit_score': None, 'credit': None, 'deposit': None}
    account.normalize()
    credit = account.get_credit()
    deposit = account.get_deposit()
    credit_payload = None
    if credit is not None:
        credit.normalize()
        credit_payload = {
            'principal': float(credit.get_sum()),
            'interest_rate': float(credit.get_interest_rate()),
            'interest': float(credit.get_interest()),
            'total': float(credit.get_total_sum()),
            'remaining': float(credit.get_remaining_sum()),
            'daily_payment': float(credit.get_daily_payment()),
            'status': credit.get_status(),
            'opened_at': _iso(credit.take_date),
            'return_date': _iso(credit.get_return_date()),
            'paid_amount': float(credit.paid_amount),
            'overdue_days': int(credit.total_overdue_days),
        }
    deposit_payload = None
    if deposit is not None:
        deposit.normalize()
        deposit_payload = {
            'principal': float(deposit.get_sum()),
            'interest_rate': float(deposit.interest_rate_on_deposit),
            'interest': float(deposit.get_interest()),
            'total': float(deposit.get_total_sum()),
            'available_interest': float(deposit.get_available_interest()),
            'allow_interest_withdrawal': bool(deposit.allow_interest_withdrawal),
            'status': deposit.get_status(),
            'opened_at': _iso(deposit.give_date),
            'return_date': _iso(deposit.get_return_date()),
        }
    credit_score = account.calculate_credit_score(gamer)
    credit_limit = account.get_credit_limit(gamer)
    credit_rate = account.get_credit_rate(gamer)
    deposit_rate = account.get_deposit_rate(gamer)
    income = account.estimate_daily_income_details(gamer)
    return {
        'credit_score': int(credit_score),
        'credit_limit': float(credit_limit),
        'max_credit_days': int(account.get_max_credit_days()),
        'credit_rate': float(credit_rate),
        'deposit_rate': float(deposit_rate),
        'estimated_daily_income': _json_value(income),
        'can_open_credit': bool(gamer.level >= 3 and credit is None),
        'can_open_deposit': bool(deposit is None and gamer.get_coins() > 0),
        'credit': credit_payload,
        'deposit': deposit_payload,
        'credit_history_count': len(account.credit_history),
        'deposit_history_count': len(account.deposit_history),
        'overdue_days_total': int(account.overdue_days_total),
    }


def serialize_custom_award(
        gamer: legacy_game.Gamer, award: game_data.Item,
) -> JSONDict:
    award_id = str(getattr(award, 'award_id', ''))
    count = 0
    inventory = getattr(gamer, 'custom_awards_inventory', {})
    if isinstance(inventory, dict):
        try:
            count = max(0, int(inventory.get(award.name, 0)))
        except (TypeError, ValueError):
            count = 0
    price = gamer.round_money(award.price)
    sell_price = gamer.round_money(award.sell_price)
    available = bool(getattr(award, 'available_in_shop', True))
    sellable = bool(getattr(award, 'sellable', True))
    return {
        'id': award_id,
        'name': str(award.name),
        'description': str(
            getattr(award, 'description', 'Кастомная награда без эффекта')
        ),
        'price': float(price),
        'sell_price': float(sell_price),
        'count': count,
        'available_in_shop': available,
        'sellable': sellable,
        'usable': True,
        'can_buy': bool(available and gamer.get_coins() >= price),
    }


def serialize_custom_awards(gamer: legacy_game.Gamer) -> JSONDict:
    awards = getattr(gamer, 'custom_awards', [])
    if not isinstance(awards, list):
        awards = []
    return {
        'items': [
            serialize_custom_award(gamer, award)
            for award in awards
            if isinstance(award, game_data.Item)
        ],
    }


def serialize_shop_catalog(gamer: legacy_game.Gamer) -> JSONDict:
    return {
        'categories': [
            {
                'key': category,
                'name': category,
                'items': [
                    _registry_item_payload(
                        gamer, category, key, item, include_count=True,
                    )
                    for key, item in items.items()
                ],
            }
            for category, items in game_data.ITEM_REGISTRY.items()
        ],
        'custom_awards': serialize_custom_awards(gamer),
    }


def serialize_inspiration(gamer: legacy_game.Gamer) -> JSONDict:
    pending_key = gamer.pending_creative_event
    pending_meta = legacy_game.CREATIVE_EVENTS.get(pending_key)
    return {
        'abilities': [
            {
                'key': key,
                'name': meta['name'],
                'description': meta['description'],
                'cost': meta['cost'],
                'bonus': meta['bonus'],
                'active': bool(getattr(gamer, meta['bonus_field'], 0)),
            }
            for key, meta in legacy_game.INSPIRATION_ABILITIES.items()
        ],
        'creative_event': (
            {'key': pending_key, **_json_value(pending_meta)}
            if pending_meta else None
        ),
        'creative_event_history': _json_value(gamer.creative_event_history),
    }


@contextmanager
def _bind_legacy_gamer(gamer: legacy_game.Gamer) -> Iterator[None]:
    """Make legacy item handlers operate on the transaction's gamer object."""
    with _LEGACY_GAME_LOCK:
        original_loader = legacy_game.load_game
        had_instance_save = 'save' in gamer.__dict__
        original_instance_save = gamer.__dict__.get('save')
        legacy_game.load_game = lambda: gamer
        gamer.save = lambda: None
        try:
            yield
        finally:
            legacy_game.load_game = original_loader
            if had_instance_save:
                gamer.__dict__['save'] = original_instance_save
            else:
                gamer.__dict__.pop('save', None)


@contextmanager
def _bind_bank_notifications(
        gamer: legacy_game.Gamer,
        projects: JSONDict,
) -> Iterator[dict[str, Any]]:
    """Keep legacy bank notifications inside the service transaction.

    ``BankAccount`` normally reloads and saves ``data.pkl`` for every
    notification.  Commands already hold the repository transaction and have
    the authoritative project envelope in memory, so redirect those writes to
    that envelope and let :meth:`GameService._command` persist it once.
    """
    changed: dict[str, Any] = {'value': False, 'messages': []}
    account = getattr(gamer, 'bank_account', None)
    if account is None:
        yield changed
        return

    had_instance_handler = '_add_notification' in account.__dict__
    original_handler = account.__dict__.get('_add_notification')

    def add_notification(text: Any) -> None:
        notifications = projects.get('notifications')
        if not isinstance(notifications, dict):
            notifications = {'new': [], 'read': []}
        new_notifications = notifications.get('new')
        read_notifications = notifications.get('read')
        if not isinstance(new_notifications, list):
            new_notifications = []
        if not isinstance(read_notifications, list):
            read_notifications = []
        notification = engine.Notification(str(text), tag='bank')
        notification.notification_id = uuid.uuid4().hex
        new_notifications.append(notification)
        notifications['new'] = new_notifications
        notifications['read'] = read_notifications
        projects['notifications'] = notifications
        changed['value'] = True
        changed['messages'].append(str(text))

    account._add_notification = add_notification
    try:
        yield changed
    finally:
        if had_instance_handler:
            account.__dict__['_add_notification'] = original_handler
        else:
            account.__dict__.pop('_add_notification', None)


class GameService:
    """Application boundary for game reads and commands."""

    def __init__(self, repository: Any, *, developer_mode: bool = False) -> None:
        self.repository = repository
        self.developer_mode = developer_mode
        self._lock = RLock()

    def _require_developer_mode(self) -> None:
        if not self.developer_mode:
            raise ConflictError(
                'developer_mode_disabled', 'Режим разработчика недоступен.',
            )

    def get_developer_state(self) -> JSONDict:
        """Return the legacy developer controls without exposing them in releases."""
        self._require_developer_mode()
        state = self.get_state()
        with self._repository_context():
            settings = self.repository.read_settings()
        test_datetime = settings.get('today_for_test_datetime')
        return {
            'state': state,
            'test_date_enabled': bool(settings.get('today_for_test_mode', False)),
            'test_datetime': _iso(test_datetime) if test_datetime is not None else None,
        }

    def update_developer_profile(
            self,
            level: int,
            health: float,
            coins: float,
            exp: float,
            test_date_enabled: bool = False,
            test_datetime: datetime | None = None,
    ) -> JSONDict:
        self._require_developer_mode()
        if test_date_enabled and test_datetime is None:
            raise ValidationError(
                'developer_test_datetime_required',
                'Укажите дату и время для тестового режима.',
            )
        if not all(math.isfinite(float(value)) for value in (health, coins, exp)):
            raise ValidationError(
                'developer_profile_invalid', 'Значения режима разработчика некорректны.',
            )
        with self._repository_context():
            gamer = self._read_gamer()
            projects = self._read_projects()
            bounded_level = min(len(game_data.levels) - 1, max(1, int(level)))
            gamer.level = bounded_level
            gamer.exp = max(0.0, float(exp))
            gamer.coins = gamer.round_money(max(0.0, float(coins)))
            gamer.update_max_health()
            gamer.health = round(
                min(gamer.get_max_health(), max(0.0, float(health))), 1,
            )
            settings = self.repository.read_settings()
            settings['today_for_test_mode'] = test_date_enabled
            settings['today_for_test_datetime'] = test_datetime if test_date_enabled else None
            settings['today_for_test_date'] = (
                test_datetime.date() if test_date_enabled and test_datetime else None
            )
            # Persist the test clock before serializing so ``server_time`` and
            # daily state in the response already reflect the chosen date.
            self.repository.write_settings(settings)
            # The legacy developer dialog refreshes projects immediately after
            # saving a test date.  Apply the same date-dependent streak rules
            # before returning the API state, rather than waiting for the
            # desktop minute timer.
            engine.refresh_project_streak_statuses(projects)
            engine.global_streak_status(projects)
            self._prepare_gamer(gamer, projects, ensure_daily=self._game_mode_enabled())
            state = self._serialize_state(
                gamer, projects, enabled=self._game_mode_enabled(),
            )
            self.repository.write_gamer(gamer)
            self.repository.write_projects(projects)
        return {
            'ok': True,
            'message': 'Настройки режима разработчика сохранены.',
            'messages': ['Настройки режима разработчика сохранены.'],
            'result': None,
            'state': state,
        }

    def grant_developer_inventory_item(
            self, category: str, item_id: str, count: int = 1,
    ) -> JSONDict:
        self._require_developer_mode()
        count = self._positive_count(count, maximum=9999)
        with self._repository_context():
            gamer = self._read_gamer()
            projects = self._read_projects()
            key, item = self._registry_item(category, item_id)
            inventory = gamer.items.setdefault(category, {})
            inventory[key] = max(0, int(inventory.get(key, 0))) + count
            gamer.normalize_inventory_item_names()
            gamer.update_cf()
            self._prepare_gamer(gamer, projects, ensure_daily=self._game_mode_enabled())
            state = self._serialize_state(
                gamer, projects, enabled=self._game_mode_enabled(),
            )
            self.repository.write_gamer(gamer)
        message = f'Получено: {item.name} x{count}.'
        return {
            'ok': True,
            'message': message,
            'messages': [message],
            'result': {'category': category, 'item_key': key, 'count': count},
            'state': state,
        }

    def _backup_notification_migration(self) -> None:
        """Preserve the source pickle before adding notification IDs to it."""
        create_backup = getattr(self.repository, 'create_backup', None)
        if callable(create_backup):
            create_backup('data')

    @contextmanager
    def _repository_context(self) -> Iterator[None]:
        # The legacy item functions resolve the gamer through a module global.
        # Holding this process-wide lock for the complete read/mutate/write cycle
        # prevents another GameService instance from observing that temporary
        # binding while it loads its own repository.
        with self._lock:
            locked = getattr(self.repository, 'locked', None)
            if callable(locked):
                with locked():
                    with _LEGACY_GAME_LOCK:
                        yield
                return
            storage_context = getattr(self.repository, 'storage_context', None)
            if callable(storage_context):
                with storage_context():
                    with _LEGACY_GAME_LOCK:
                        yield
                return
            with _LEGACY_GAME_LOCK:
                yield

    def get_state(self) -> JSONDict:
        with self._repository_context():
            gamer = self._read_gamer()
            projects = self._read_projects()
            enabled = self._game_mode_enabled()
            notification_ids_changed = _ensure_notification_ids(projects)
            projects_changed = False
            with _bind_legacy_gamer(gamer):
                changed = self._prepare_gamer(gamer, projects, ensure_daily=enabled)
                if (
                        enabled
                        and gamer.writing_session is not None
                        and gamer.writing_session_remaining_seconds() <= 0
                ):
                    with _bind_bank_notifications(
                            gamer, projects,
                    ) as bank_notifications:
                        _successful, message = gamer.finish_writing_session(
                            save=False,
                        )
                        reward_messages = self._settle_rewards(gamer)
                    bank_messages = list(bank_notifications['messages'])
                    projects_changed = bank_notifications['value']
                    projects_changed = _append_game_notifications(
                        projects,
                        self._command_messages(
                            message, reward_messages, bank_messages,
                        ),
                    ) or projects_changed
                    self._prepare_gamer(gamer, projects, ensure_daily=True)
                    changed = True
                prepared_snapshot = self._preparation_snapshot(gamer)
                state = self._serialize_state(gamer, projects, enabled=enabled)
                changed = changed or prepared_snapshot != self._preparation_snapshot(gamer)
            notification_ids_changed = (
                _ensure_notification_ids(projects) or notification_ids_changed
            )
            projects_changed = projects_changed or notification_ids_changed
            if projects_changed and notification_ids_changed:
                self._backup_notification_migration()
            if projects_changed:
                self.repository.write_projects(projects)
            if changed:
                self.repository.write_gamer(gamer)
            return state

    def get_notifications(self) -> JSONDict:
        """Expose persisted streak and bank events independently of game mode."""
        with self._repository_context():
            projects = self._read_projects()
            if _ensure_notification_ids(projects):
                self._backup_notification_migration()
                self.repository.write_projects(projects)
            return serialize_notifications(projects)

    def mark_notification_read(self, notification_id: str) -> JSONDict:
        if not isinstance(notification_id, str) or not notification_id:
            raise ValidationError(
                'notification_id_invalid', 'Идентификатор уведомления некорректен.',
            )
        with self._repository_context():
            projects = self._read_projects()
            migrated = _ensure_notification_ids(projects)
            buckets = _notification_buckets(projects)
            for index, notification in enumerate(buckets['new']):
                if _notification_id(notification, 'new', index) != notification_id:
                    continue
                moved = _mark_notification_read(notification, notification_id)
                buckets['new'].pop(index)
                buckets['read'].insert(0, moved)
                projects['notifications'] = buckets
                if migrated:
                    self._backup_notification_migration()
                self.repository.write_projects(projects)
                return serialize_notifications(projects)
        raise NotFoundError('notification_not_found', 'Уведомление не найдено.')

    def mark_all_notifications_read(self) -> JSONDict:
        with self._repository_context():
            projects = self._read_projects()
            migrated = _ensure_notification_ids(projects)
            buckets = _notification_buckets(projects)
            if not buckets['new']:
                if migrated:
                    self._backup_notification_migration()
                    self.repository.write_projects(projects)
                return serialize_notifications(projects)
            moved = [
                _mark_notification_read(
                    notification,
                    _notification_id(notification, 'new', index),
                )
                for index, notification in enumerate(buckets['new'])
            ]
            buckets['new'] = []
            buckets['read'] = [*reversed(moved), *buckets['read']]
            projects['notifications'] = buckets
            if migrated:
                self._backup_notification_migration()
            self.repository.write_projects(projects)
            return serialize_notifications(projects)

    def get_shop_catalog(self) -> JSONDict:
        with self._repository_context():
            gamer = self._read_gamer()
            projects = self._read_projects()
            enabled = self._game_mode_enabled()
            with _bind_legacy_gamer(gamer):
                changed = self._prepare_gamer(
                    gamer, projects, ensure_daily=False,
                )
                catalog = {'enabled': enabled, **serialize_shop_catalog(gamer)}
            if changed:
                self.repository.write_gamer(gamer)
            return catalog

    get_game_state = get_state

    def start_writing_session(
            self,
            duration_minutes: int,
            target_symbols: int,
            intention: str,
            mode_key: str = 'flow',
    ) -> JSONDict:
        def mutate(gamer: legacy_game.Gamer, _projects: JSONDict) -> JSONDict:
            ok, message = gamer.start_writing_session(
                duration_minutes,
                target_symbols,
                intention,
                mode_key=mode_key,
                save=False,
            )
            if not ok:
                raise ConflictError('writing_session_not_started', message)
            return {'message': message}

        return self._command(mutate)

    def finish_writing_session(self) -> JSONDict:
        def mutate(gamer: legacy_game.Gamer, _projects: JSONDict) -> JSONDict:
            if gamer.writing_session is None:
                raise ConflictError(
                    'writing_session_not_active',
                    'Нет активной писательской сессии.',
                )
            successful, message = gamer.finish_writing_session(save=False)
            return {
                'message': message,
                'result': {'successful': bool(successful)},
            }

        return self._command(mutate, settle_rewards=True)

    def cancel_writing_session(self) -> JSONDict:
        def mutate(gamer: legacy_game.Gamer, _projects: JSONDict) -> JSONDict:
            ok, message = gamer.cancel_writing_session(save=False)
            if not ok:
                raise ConflictError('writing_session_not_active', message)
            return {'message': message}

        return self._command(mutate)

    def select_daily_challenge(self, option_id: str) -> JSONDict:
        def mutate(gamer: legacy_game.Gamer, _projects: JSONDict) -> JSONDict:
            option_index = next(
                (
                    index for index, option in enumerate(gamer.daily_challenge_options)
                    if option.get('option_id') == option_id
                ),
                None,
            )
            if option_index is None:
                raise ValidationError(
                    'daily_challenge_option_not_found',
                    'Неизвестный вариант цели дня.',
                )
            ok, message = gamer.select_daily_challenge_option(
                option_index, free=False, save=False,
            )
            if not ok:
                raise ConflictError('daily_challenge_not_changed', message)
            return {'message': message}

        return self._command(mutate)

    def start_weekly_challenge(self, challenge_key: str) -> JSONDict:
        def mutate(gamer: legacy_game.Gamer, _projects: JSONDict) -> JSONDict:
            if challenge_key not in legacy_game.WEEKLY_CHALLENGES:
                raise ValidationError(
                    'weekly_challenge_not_found',
                    'Неизвестное недельное испытание.',
                )
            ok, message = gamer.select_weekly_challenge(challenge_key, save=False)
            if not ok:
                raise ConflictError('weekly_challenge_not_started', message)
            return {'message': message}

        return self._command(mutate)

    select_daily_challenge_option = select_daily_challenge
    select_weekly_challenge = start_weekly_challenge

    def activate_inspiration_ability(self, ability_key: str) -> JSONDict:
        def mutate(gamer: legacy_game.Gamer, _projects: JSONDict) -> JSONDict:
            if ability_key not in legacy_game.INSPIRATION_ABILITIES:
                raise ValidationError(
                    'inspiration_ability_not_found',
                    'Неизвестная способность вдохновения.',
                )
            ok, message = gamer.activate_inspiration_ability(ability_key, save=False)
            if not ok:
                raise ConflictError('inspiration_ability_not_activated', message)
            return {'message': message}

        return self._command(mutate)

    def resolve_creative_event(self, choice: str) -> JSONDict:
        if choice not in {'safe', 'risk'}:
            raise ValidationError(
                'creative_event_choice_invalid',
                'Неизвестный выбор творческого события.',
            )

        def mutate(gamer: legacy_game.Gamer, _projects: JSONDict) -> JSONDict:
            ok, message = gamer.resolve_creative_event(choice, save=False)
            if not ok:
                raise ConflictError('creative_event_not_resolved', message)
            return {'message': message}

        return self._command(mutate, settle_rewards=True)

    def select_specialization(self, specialization_key: str) -> JSONDict:
        def mutate(gamer: legacy_game.Gamer, _projects: JSONDict) -> JSONDict:
            if specialization_key not in legacy_game.SPECIALIZATIONS:
                raise ValidationError(
                    'specialization_not_found', 'Неизвестная специализация.',
                )
            ok, message = gamer.select_specialization(
                specialization_key, save=False,
            )
            if not ok:
                raise ConflictError('specialization_not_selected', message)
            return {'message': message}

        return self._command(mutate)

    def activate_specialization_ability(self) -> JSONDict:
        def mutate(gamer: legacy_game.Gamer, _projects: JSONDict) -> JSONDict:
            ok, message = gamer.activate_specialization_ability(save=False)
            if not ok:
                raise ConflictError('specialization_ability_not_activated', message)
            return {'message': message}

        return self._command(mutate)

    def increase_skill(self, skill_key: str, points: int = 1) -> JSONDict:
        points = self._positive_count(points, maximum=1_000)

        def mutate(gamer: legacy_game.Gamer, _projects: JSONDict) -> JSONDict:
            if skill_key not in legacy_game.SKILL_META:
                raise ValidationError('skill_not_found', 'Неизвестное умение.')
            ok, message = gamer.increase_skill(skill_key, points, save=False)
            if not ok:
                raise ConflictError('skill_not_increased', message)
            return {'message': message}

        return self._command(mutate)

    def start_quest(self, quest_id: str) -> JSONDict:
        def mutate(gamer: legacy_game.Gamer, _projects: JSONDict) -> JSONDict:
            if gamer.get_quest(quest_id) is None:
                raise NotFoundError('quest_not_found', 'Квест не найден.')
            ok, message = gamer.start_quest(quest_id)
            if not ok:
                raise ConflictError('quest_not_started', message)
            return {'message': message}

        return self._command(mutate)

    def abandon_quest(self, quest_id: str) -> JSONDict:
        def mutate(gamer: legacy_game.Gamer, _projects: JSONDict) -> JSONDict:
            if gamer.get_quest(quest_id) is None:
                raise NotFoundError('quest_not_found', 'Квест не найден.')
            ok, message = gamer.abandon_quest(quest_id)
            if not ok:
                raise ConflictError('quest_not_abandoned', message)
            return {'message': message}

        return self._command(mutate)

    def buy_registry_item(
            self, category: str, item_key: str, count: int = 1,
    ) -> JSONDict:
        count = self._positive_count(count)

        def mutate(gamer: legacy_game.Gamer, _projects: JSONDict) -> JSONDict:
            key, item = self._registry_item(category, item_key)
            if not getattr(item, 'Buy', False):
                raise ConflictError(
                    'item_not_buyable', 'Этот предмет нельзя купить.',
                )
            if gamer.level < item.level:
                raise ConflictError(
                    'item_level_too_low',
                    f'Предмет доступен с {item.level} уровня.',
                )
            inventory = gamer.items.setdefault(category, {})
            current_count = int(inventory.get(key, 0))
            limit_message = item.get_purchase_limit_message(current_count, count)
            if limit_message:
                raise ConflictError('item_inventory_limit', limit_message)
            unit_price = gamer.round_money(item.price)
            total_price = gamer.round_money(unit_price * count)
            if gamer.get_coins() < total_price:
                raise ConflictError('not_enough_coins', 'Недостаточно монет!')
            gamer.remove_coins(
                total_price, process_bank_events=False, save=False,
            )
            inventory[key] = current_count + count
            gamer.normalize_inventory_item_names()
            gamer.update_cf()
            return {
                'message': f'Куплено: {item.name} x{count}.',
                'result': {
                    'category': category,
                    'item_key': key,
                    'count': count,
                    'unit_price': unit_price,
                    'total_price': total_price,
                },
            }

        return self._command(mutate, settle_rewards=True)

    def sell_registry_item(
            self, category: str, item_key: str, count: int = 1,
    ) -> JSONDict:
        count = self._positive_count(count)

        def mutate(gamer: legacy_game.Gamer, _projects: JSONDict) -> JSONDict:
            key, item = self._registry_item(category, item_key)
            if not getattr(item, 'sellable', True):
                raise ConflictError(
                    'item_not_sellable', 'Этот предмет нельзя продать.',
                )
            inventory = gamer.items.setdefault(category, {})
            available = int(inventory.get(key, 0))
            if available < count:
                raise ConflictError(
                    'item_not_enough_in_inventory',
                    f'В инвентаре только {available} шт.',
                )
            inventory[key] = available - count
            if inventory[key] <= 0:
                inventory.pop(key, None)
            unit_price = gamer.round_money(item.sell_price)
            total_price = gamer.round_money(unit_price * count)
            gamer.set_coins(
                total_price, process_bank_events=False, save=False,
            )
            gamer.update_cf()
            return {
                'message': f'Продано: {item.name} x{count}.',
                'result': {
                    'category': category,
                    'item_key': key,
                    'count': count,
                    'unit_price': unit_price,
                    'total_price': total_price,
                },
            }

        return self._command(mutate, settle_rewards=True)

    def use_registry_item(
            self, category: str, item_key: str, count: int = 1,
    ) -> JSONDict:
        count = self._positive_count(count)

        def mutate(gamer: legacy_game.Gamer, _projects: JSONDict) -> JSONDict:
            key, item = self._registry_item(category, item_key)
            item_function = getattr(item, '_func', None)
            if not isinstance(item, game_data.FuncItem) or not (
                    callable(item_function) or getattr(item, 'buff', None) is not None
            ):
                raise ConflictError(
                    'item_not_usable',
                    'Этот предмет нельзя использовать напрямую.',
                )
            inventory = gamer.items.setdefault(category, {})
            available = int(inventory.get(key, 0))
            if available < count:
                raise ConflictError(
                    'item_not_enough_in_inventory',
                    f'В инвентаре только {available} шт.',
                )
            messages: list[str] = []
            lottery_draws: list[JSONDict] = []
            for _ in range(count):
                try:
                    if key == 'Лотерейный билет':
                        draw = game_data.prepare_lottery_ticket_draw()
                        result = game_data.complete_lottery_ticket_draw(draw)
                        lottery_draws.append(draw)
                    else:
                        result = item.use()
                except ValueError as error:
                    raise ConflictError('item_use_rejected', str(error)) from error
                inventory[key] -= 1
                messages.append(str(result or 'Предмет использован.'))
            if inventory[key] <= 0:
                inventory.pop(key, None)
            gamer.normalize_inventory_item_names()
            gamer.update_cf()
            result: JSONDict = {
                'category': category,
                'item_key': key,
                'count': count,
            }
            if lottery_draws:
                result['lottery_draws'] = lottery_draws
            return {
                'message': '\n'.join(messages),
                'result': result,
            }

        return self._command(mutate, settle_rewards=True)

    # Concise aliases used by transport adapters.
    buy_item = buy_registry_item
    sell_item = sell_registry_item
    use_item = use_registry_item

    def apply_streak_freeze(
            self,
            target: str,
            *,
            project_id: str | None = None,
    ) -> JSONDict:
        target = str(target).strip().casefold()
        if target not in {'global', 'project'}:
            raise ValidationError(
                'streak_freeze_target_invalid',
                    'Неизвестная цель заморозки стрика.',
            )
        normalized_project_id = (
            str(project_id).strip() if project_id is not None else None
        )
        if target == 'project' and not normalized_project_id:
            raise ValidationError(
                'streak_freeze_project_required',
                'Выберите проект для заморозки.',
            )
        if target == 'global' and normalized_project_id:
            raise ValidationError(
                'streak_freeze_project_unexpected',
                    'Для глобального стрика проект не указывается.',
            )

        def mutate(gamer: legacy_game.Gamer, projects: JSONDict) -> JSONDict:
            if _freeze_inventory_count(gamer) <= 0:
                raise ConflictError(
                    'streak_freeze_not_in_inventory',
                    'В инвентаре нет заморозки.',
                )
            today = engine.today_for_test()
            if target == 'global':
                if not engine.can_freeze_global_streak(projects, today):
                    raise ConflictError(
                        'global_streak_freeze_unavailable',
                        'Глобальную серию сейчас нельзя заморозить.',
                    )
                if not engine.apply_global_streak_freeze(
                        projects, today, gamer=gamer, save_gamer=False,
                ):
                    raise ConflictError(
                        'global_streak_freeze_failed',
                        'Не удалось применить заморозку.',
                    )
                return {
                    'message': 'Глобальный стрик заморожен!',
                    'result': {'target': 'global', 'date': today.isoformat()},
                    '_projects_changed': True,
                }

            project, is_stage = self._resolve_project_entity(
                projects, f'project:{normalized_project_id}',
            )
            if is_stage:
                raise ValidationError(
                    'streak_freeze_project_invalid',
                    'Заморозка выбирается для проекта целиком.',
                )
            freeze_sources = engine.get_project_freeze_sources(project, today)
            if not freeze_sources:
                raise ConflictError(
                    'project_streak_freeze_unavailable',
                    'Серию этого проекта сейчас нельзя заморозить.',
                )
            if not engine.apply_project_freeze_group(
                    project, today, gamer=gamer, save_gamer=False,
            ):
                raise ConflictError(
                    'project_streak_freeze_failed',
                    'Не удалось применить заморозку.',
                )
            global_streaks = projects.get('global_streaks')
            if not isinstance(global_streaks, list):
                global_streaks = []
                projects['global_streaks'] = global_streaks
            if engine.streak_last_day(global_streaks) == today - timedelta(days=1):
                global_streaks.append(engine.STREAK_FREEZE_MARKER)
            projects['global_streak_status'] = 'Freeze'
            project_name = str(getattr(project, 'name', ''))
            return {
                'message': f'Проект "{project_name}" заморожен!',
                'result': {
                    'target': 'project',
                    'project_id': normalized_project_id,
                    'date': today.isoformat(),
                    'source_count': len(freeze_sources),
                },
                '_projects_changed': True,
            }

        return self._command(mutate)

    def create_custom_award(self, name: str, price: Any) -> JSONDict:
        name = self._custom_award_name(name)
        price = self._positive_money(
            price,
            code='custom_award_price_invalid',
            label='Цена награды',
        )

        def mutate(gamer: legacy_game.Gamer, _projects: JSONDict) -> JSONDict:
            self._ensure_custom_award_name_available(gamer, name)
            award = game_data.Item(
                name=name,
                price=price,
                item_type='Награды',
                description='Кастомная награда без эффекта',
            )
            award.award_id = uuid.uuid4().hex
            award.count = 0
            award.available_in_shop = True
            gamer.custom_awards.append(award)
            gamer.custom_awards_inventory.setdefault(name, 0)
            return {
                'message': 'Награда создана.',
                'result': {'award': serialize_custom_award(gamer, award)},
            }

        return self._command(mutate)

    def update_custom_award(
            self,
            award_id: str,
            *,
            name: str | None = None,
            price: Any | None = None,
    ) -> JSONDict:
        if name is None and price is None:
            raise ValidationError(
                'custom_award_update_empty',
                'Укажите новое название или цену награды.',
            )
        normalized_name = self._custom_award_name(name) if name is not None else None
        normalized_price = (
            self._positive_money(
                price,
                code='custom_award_price_invalid',
                label='Цена награды',
            )
            if price is not None else None
        )

        def mutate(gamer: legacy_game.Gamer, _projects: JSONDict) -> JSONDict:
            award = self._custom_award(gamer, award_id)
            old_name = str(award.name)
            if normalized_name is not None and normalized_name != old_name:
                self._ensure_custom_award_name_available(
                    gamer, normalized_name, current=award,
                )
                destination_count = gamer.custom_awards_inventory.get(
                    normalized_name, 0,
                )
                if destination_count:
                    raise ConflictError(
                        'custom_award_name_conflict',
                        'Награда с таким названием уже существует.',
                    )
                count = gamer.custom_awards_inventory.pop(old_name, 0)
                gamer.custom_awards_inventory[normalized_name] = count
                legacy_inventory = gamer.items.get('Награды', {})
                if isinstance(legacy_inventory, dict) and old_name in legacy_inventory:
                    legacy_inventory[normalized_name] = legacy_inventory.pop(old_name)
                award.name = normalized_name
            if normalized_price is not None:
                award._price = normalized_price
            award.item_type = 'Награды'
            if not getattr(award, 'description', None):
                award.description = 'Кастомная награда без эффекта'
            return {
                'message': 'Награда изменена.',
                'result': {'award': serialize_custom_award(gamer, award)},
            }

        return self._command(mutate)

    def delete_custom_award(self, award_id: str) -> JSONDict:
        def mutate(gamer: legacy_game.Gamer, _projects: JSONDict) -> JSONDict:
            award = self._custom_award(gamer, award_id)
            award.available_in_shop = False
            count = self._custom_award_count(gamer, award)
            removed = self._cleanup_custom_award(gamer, award)
            return {
                'message': 'Награда удалена из магазина.',
                'result': {
                    'award_id': str(getattr(award, 'award_id')),
                    'inventory_count': count,
                    'definition_removed': removed,
                },
            }

        return self._command(mutate)

    def buy_custom_award(self, award_id: str, count: int = 1) -> JSONDict:
        count = self._positive_count(count)

        def mutate(gamer: legacy_game.Gamer, _projects: JSONDict) -> JSONDict:
            award = self._custom_award(gamer, award_id)
            if not bool(getattr(award, 'available_in_shop', True)):
                raise ConflictError(
                    'custom_award_not_available',
                    'Награда больше не доступна в магазине.',
                )
            unit_price = gamer.round_money(award.price)
            total_price = gamer.round_money(unit_price * count)
            if gamer.get_coins() < total_price:
                raise ConflictError('not_enough_coins', 'Недостаточно монет!')
            gamer.remove_coins(
                total_price, process_bank_events=False, save=False,
            )
            current_count = self._custom_award_count(gamer, award)
            gamer.custom_awards_inventory[award.name] = current_count + count
            return {
                'message': f'Куплено: {award.name} x{count}.',
                'result': {
                    'award_id': str(award.award_id),
                    'count': count,
                    'unit_price': unit_price,
                    'total_price': total_price,
                    'award': serialize_custom_award(gamer, award),
                },
            }

        return self._command(mutate, settle_rewards=True)

    def sell_custom_award(self, award_id: str, count: int = 1) -> JSONDict:
        count = self._positive_count(count)

        def mutate(gamer: legacy_game.Gamer, _projects: JSONDict) -> JSONDict:
            award = self._custom_award(gamer, award_id)
            if not bool(getattr(award, 'sellable', True)):
                raise ConflictError(
                    'custom_award_not_sellable',
                    'Эту награду нельзя продать.',
                )
            available = self._custom_award_count(gamer, award)
            if available < count:
                raise ConflictError(
                    'custom_award_not_enough_in_inventory',
                    f'В инвентаре только {available} шт.',
                )
            remaining = available - count
            gamer.custom_awards_inventory[award.name] = remaining
            unit_price = gamer.round_money(award.sell_price)
            total_price = gamer.round_money(unit_price * count)
            gamer.set_coins(
                total_price, process_bank_events=False, save=False,
            )
            removed = self._cleanup_custom_award(gamer, award)
            return {
                'message': f'Продано: {award.name} x{count}.',
                'result': {
                    'award_id': str(award.award_id),
                    'count': count,
                    'unit_price': unit_price,
                    'total_price': total_price,
                    'remaining': remaining,
                    'definition_removed': removed,
                },
            }

        return self._command(mutate, settle_rewards=True)

    def use_custom_award(self, award_id: str, count: int = 1) -> JSONDict:
        count = self._positive_count(count)

        def mutate(gamer: legacy_game.Gamer, _projects: JSONDict) -> JSONDict:
            award = self._custom_award(gamer, award_id)
            available = self._custom_award_count(gamer, award)
            if available < count:
                raise ConflictError(
                    'custom_award_not_enough_in_inventory',
                    f'В инвентаре только {available} шт.',
                )
            remaining = available - count
            gamer.custom_awards_inventory[award.name] = remaining
            removed = self._cleanup_custom_award(gamer, award)
            return {
                'message': f'Использовано: {award.name} x{count}. Эффекта нет.',
                'result': {
                    'award_id': str(award.award_id),
                    'count': count,
                    'remaining': remaining,
                    'definition_removed': removed,
                },
            }

        return self._command(mutate, settle_rewards=True)

    def preview_bank_product(
            self,
            product_type: str,
            amount: Any,
            days: Any,
            *,
            allow_interest_withdrawal: bool = False,
    ) -> JSONDict:
        product_type = self._bank_product_type(product_type)
        amount = self._positive_money(amount)
        days = self._positive_days(days)
        allow_interest_withdrawal = self._boolean_option(
            allow_interest_withdrawal, 'allow_interest_withdrawal',
        )

        def mutate(gamer: legacy_game.Gamer, _projects: JSONDict) -> JSONDict:
            account = self._bank_account(gamer)
            self._validate_new_bank_product(
                gamer, account, product_type, amount, days,
            )
            preview = account.preview_product(
                gamer,
                product_type,
                amount,
                days,
                allow_interest_withdrawal=allow_interest_withdrawal,
            )
            return {
                'message': None,
                'result': {
                    'product_type': product_type,
                    'amount': amount,
                    'days': days,
                    'allow_interest_withdrawal': allow_interest_withdrawal,
                    **_json_value(preview),
                },
            }

        return self._command(mutate)

    def open_bank_credit(self, amount: Any, days: Any) -> JSONDict:
        amount = self._positive_money(amount)
        days = self._positive_days(days)

        def mutate(gamer: legacy_game.Gamer, _projects: JSONDict) -> JSONDict:
            account = self._bank_account(gamer)
            self._validate_new_bank_product(
                gamer, account, 'credit', amount, days,
            )
            preview = account.preview_product(gamer, 'credit', amount, days)
            ok, message = account.open_credit(gamer, amount, days)
            if not ok:
                raise ConflictError('bank_credit_not_opened', message)
            return {
                'message': message,
                'result': {
                    'product_type': 'credit',
                    'amount': amount,
                    'days': days,
                    **_json_value(preview),
                },
            }

        return self._command(mutate, settle_rewards=True)

    def open_bank_deposit(
            self,
            amount: Any,
            days: Any,
            *,
            allow_interest_withdrawal: bool = False,
    ) -> JSONDict:
        amount = self._positive_money(amount)
        days = self._positive_days(days)
        allow_interest_withdrawal = self._boolean_option(
            allow_interest_withdrawal, 'allow_interest_withdrawal',
        )

        def mutate(gamer: legacy_game.Gamer, _projects: JSONDict) -> JSONDict:
            account = self._bank_account(gamer)
            self._validate_new_bank_product(
                gamer, account, 'deposit', amount, days,
            )
            preview = account.preview_product(
                gamer,
                'deposit',
                amount,
                days,
                allow_interest_withdrawal=allow_interest_withdrawal,
            )
            ok, message = account.open_deposit(
                gamer,
                amount,
                days,
                allow_interest_withdrawal=allow_interest_withdrawal,
            )
            if not ok:
                raise ConflictError('bank_deposit_not_opened', message)
            return {
                'message': message,
                'result': {
                    'product_type': 'deposit',
                    'amount': amount,
                    'days': days,
                    'allow_interest_withdrawal': allow_interest_withdrawal,
                    **_json_value(preview),
                },
            }

        return self._command(mutate, settle_rewards=True)

    def process_bank_events(self, *, auto_pay: bool = True) -> JSONDict:
        auto_pay = self._boolean_option(auto_pay, 'auto_pay')

        def mutate(gamer: legacy_game.Gamer, _projects: JSONDict) -> JSONDict:
            messages = self._bank_account(gamer).process_daily_events(
                gamer, auto_pay=auto_pay, notify=True, save=False,
            )
            return {
                'message': '\n'.join(messages) if messages else None,
                'result': {
                    'processed_count': len(messages),
                    'events': [str(message) for message in messages],
                },
            }

        return self._command(mutate, settle_rewards=True)

    def make_bank_loan_payment(self) -> JSONDict:
        def mutate(gamer: legacy_game.Gamer, _projects: JSONDict) -> JSONDict:
            account = self._bank_account(gamer)
            credit = account.get_credit()
            if credit is None:
                raise ConflictError('bank_credit_not_active', 'Нет активного кредита.')
            today = engine.today_for_test()
            if today < credit.get_first_payment_date():
                raise ConflictError(
                    'bank_payment_not_due',
                    f'Первый платеж будет доступен '
                    f'{credit.get_first_payment_date().strftime("%d.%m.%Y")}.',
                )
            if credit.last_payment_date == today:
                raise ConflictError(
                    'bank_payment_already_made',
                    'Платеж по кредиту сегодня уже внесен.',
                )
            coins_before = gamer.get_coins()
            message = account.make_loan_payment(gamer)
            return {
                'message': message,
                'result': {
                    'paid': bool(
                        account.get_credit() is None
                        or gamer.get_coins() < coins_before
                    ),
                    'credit_closed': account.get_credit() is None,
                },
            }

        return self._command(mutate, settle_rewards=True)

    def partially_repay_bank_credit(self, amount: Any) -> JSONDict:
        amount = self._positive_money(amount)

        def mutate(gamer: legacy_game.Gamer, _projects: JSONDict) -> JSONDict:
            account = self._bank_account(gamer)
            if account.get_credit() is None:
                raise ConflictError('bank_credit_not_active', 'Нет активного кредита.')
            if gamer.get_coins() < amount:
                raise ConflictError(
                    'not_enough_coins', f'Недостаточно монет. Нужно: {amount}',
                )
            coins_before = gamer.get_coins()
            message = account.partial_repay_credit(gamer, amount)
            paid_amount = gamer.round_money(coins_before - gamer.get_coins())
            return {
                'message': message,
                'result': {
                    'requested_amount': amount,
                    'paid_amount': paid_amount,
                    'credit_closed': account.get_credit() is None,
                },
            }

        return self._command(mutate, settle_rewards=True)

    def repay_bank_credit(self) -> JSONDict:
        def mutate(gamer: legacy_game.Gamer, _projects: JSONDict) -> JSONDict:
            account = self._bank_account(gamer)
            if account.get_credit() is None:
                raise ConflictError('bank_credit_not_active', 'Нет активного кредита.')
            coins_before = gamer.get_coins()
            message = account.return_credit(gamer)
            paid_amount = gamer.round_money(coins_before - gamer.get_coins())
            return {
                'message': message,
                'result': {
                    'repaid': account.get_credit() is None,
                    'paid_amount': max(0.0, paid_amount),
                },
            }

        return self._command(mutate, settle_rewards=True)

    def top_up_bank_deposit(self, amount: Any) -> JSONDict:
        amount = self._positive_money(amount)

        def mutate(gamer: legacy_game.Gamer, _projects: JSONDict) -> JSONDict:
            account = self._bank_account(gamer)
            if account.get_deposit() is None:
                raise ConflictError('bank_deposit_not_active', 'Нет активного вклада.')
            if gamer.get_coins() < amount:
                raise ConflictError(
                    'not_enough_coins', f'Недостаточно монет. Нужно: {amount}',
                )
            message = account.top_up_deposit(gamer, amount)
            return {
                'message': message,
                'result': {'amount': amount},
            }

        return self._command(mutate, settle_rewards=True)

    def withdraw_bank_deposit(self, *, allow_early: bool = False) -> JSONDict:
        allow_early = self._boolean_option(allow_early, 'allow_early')

        def mutate(gamer: legacy_game.Gamer, _projects: JSONDict) -> JSONDict:
            account = self._bank_account(gamer)
            deposit = account.get_deposit()
            if deposit is None:
                raise ConflictError('bank_deposit_not_active', 'Нет активного вклада.')
            early = deposit.get_return_date() > engine.today_for_test()
            if early and not allow_early:
                raise ConflictError(
                    'bank_deposit_not_mature',
                    'Срок вклада еще не наступил; требуется подтверждение досрочного снятия.',
                )
            coins_before = gamer.get_coins()
            message = account.return_deposit(gamer, early=early)
            return {
                'message': message,
                'result': {
                    'early': early,
                    'received': gamer.round_money(gamer.get_coins() - coins_before),
                },
            }

        return self._command(mutate, settle_rewards=True)

    def withdraw_bank_deposit_interest(self) -> JSONDict:
        def mutate(gamer: legacy_game.Gamer, _projects: JSONDict) -> JSONDict:
            account = self._bank_account(gamer)
            deposit = account.get_deposit()
            if deposit is None:
                raise ConflictError('bank_deposit_not_active', 'Нет активного вклада.')
            can_withdraw, reason = deposit.can_withdraw_interest()
            if not can_withdraw:
                raise ConflictError('bank_interest_not_available', reason)
            coins_before = gamer.get_coins()
            message = account.withdraw_deposit_interest(gamer)
            return {
                'message': message,
                'result': {
                    'amount': gamer.round_money(gamer.get_coins() - coins_before),
                },
            }

        return self._command(mutate, settle_rewards=True)

    # Concise aliases for route and non-HTTP adapters.
    open_credit = open_bank_credit
    open_deposit = open_bank_deposit
    make_loan_payment = make_bank_loan_payment
    partial_repay_credit = partially_repay_bank_credit
    return_credit = repay_bank_credit
    top_up_deposit = top_up_bank_deposit
    return_deposit = withdraw_bank_deposit
    withdraw_deposit_interest = withdraw_bank_deposit_interest

    def record_project_progress(
            self,
            *,
            added_symbols: int,
            project_key: str,
            project_progress: float,
            streak_events: list[dict[str, Any]] | None = None,
    ) -> JSONDict:
        try:
            added_symbols = int(added_symbols)
        except (TypeError, ValueError) as error:
            raise ValidationError(
                'progress_delta_invalid', 'Изменение прогресса должно быть целым числом.',
            ) from error

        if streak_events is not None and not isinstance(streak_events, list):
            raise ValidationError(
                'streak_events_invalid', 'События стрика имеют неверный формат.',
            )
        streak_events = list(streak_events or [])

        def mutate(gamer: legacy_game.Gamer, projects: JSONDict) -> JSONDict:
            if added_symbols == 0:
                return {
                    'message': None,
                    'result': {
                        'added_symbols': 0,
                        'processed_symbols': 0,
                        'rewarded': False,
                        'streak_rewards': 0,
                    },
                }
            authoritative_progress = self._resolve_project_progress(
                projects, project_key, project_progress,
            )
            if added_symbols > 0:
                message = gamer.give_symbol_bonus(
                    added_symbols,
                    project_key=project_key,
                    project_progress=authoritative_progress,
                )
                streak_messages, projects_changed = self._apply_streak_events(
                    gamer, projects, streak_events, default_key=project_key,
                )
                if streak_messages:
                    message = '\n'.join([message, *streak_messages])
                return {
                    'message': message,
                    'result': {
                        'added_symbols': added_symbols,
                        'processed_symbols': added_symbols,
                        'rewarded': True,
                        'streak_rewards': len(streak_messages),
                    },
                    '_projects_changed': projects_changed,
                }
            if added_symbols < 0:
                processed = gamer.record_editing_progress(added_symbols)
                return {
                    'message': (
                        f'Учтено отредактированных символов: {processed}.'
                        if processed else None
                    ),
                    'result': {
                        'added_symbols': added_symbols,
                        'processed_symbols': processed,
                        'rewarded': False,
                        'streak_rewards': 0,
                    },
                }
            raise AssertionError('unreachable progress delta branch')

        return self._command(
            mutate,
            settle_rewards=added_symbols > 0,
            disabled_payload={
                'message': None,
                'result': {
                    'added_symbols': added_symbols,
                    'processed_symbols': 0,
                    'rewarded': False,
                    'streak_rewards': 0,
                    'skipped': 'game_mode_disabled',
                },
            },
        )

    def record_completions(self, completions: list[dict[str, Any]]) -> JSONDict:
        if not isinstance(completions, list):
            raise ValidationError(
                'completions_invalid', 'Список завершений имеет неверный формат.',
            )
        completion_events = list(completions)

        def mutate(gamer: legacy_game.Gamer, projects: JSONDict) -> JSONDict:
            messages: list[str] = []
            applied: list[JSONDict] = []
            for event in completion_events:
                if not isinstance(event, dict):
                    raise ValidationError(
                        'completion_invalid', 'Завершение имеет неверный формат.',
                    )
                key = str(event.get('key', ''))
                entity, actual_is_stage = self._resolve_project_entity(projects, key)
                if getattr(entity, 'status', None) != 'завершен':
                    raise ConflictError(
                        'completion_not_finished',
                        'Награда доступна только после завершения проекта или этапа.',
                    )
                total_symbols = max(0.0, float(entity.get_total_symbols()))
                streak_length = self._nonnegative_integer(
                    event.get('streak_length', 0), maximum=1_000_000,
                )
                streak_status = str(event.get('streak_status', ''))
                if (
                        streak_length > 0
                        and streak_status.casefold() not in {'', 'no', 'off', 'false'}
                ):
                    streak_message = gamer.give_streak_bonus(
                        'Complete', 'Local', streak_length, project_name=key,
                    )
                    if streak_message:
                        messages.append(streak_message)
                multiplier = (
                    game_data.STAGE_COMPLETION_BONUS_MULTIPLIER
                    if actual_is_stage else 1.0
                )
                completion_message = gamer.give_complete_bonus(
                    getattr(entity, 'status', 'завершен'),
                    total_symbols,
                    project_name=key,
                    bonus_multiplier=multiplier,
                )
                if completion_message:
                    messages.append(completion_message)
                applied.append({
                    'key': key,
                    'is_stage': actual_is_stage,
                    'total_symbols': total_symbols,
                    'rewarded': bool(completion_message),
                })
            return {
                'message': '\n'.join(messages) if messages else None,
                'result': {'completions': applied},
            }

        return self._command(
            mutate,
            settle_rewards=True,
            disabled_payload={
                'message': None,
                'result': {
                    'completions': [],
                    'skipped': 'game_mode_disabled',
                },
            },
        )

    def _command(
            self,
            mutation: Callable[[legacy_game.Gamer, JSONDict], JSONDict],
            *,
            settle_rewards: bool = False,
            disabled_payload: JSONDict | None = None,
    ) -> JSONDict:
        with self._repository_context():
            gamer = self._read_gamer()
            projects = self._read_projects()
            enabled = self._game_mode_enabled()
            if not enabled and disabled_payload is None:
                raise ConflictError(
                    'game_mode_disabled', 'Игровой режим отключён.',
                )
            command_messages: list[str] = []
            with _bind_legacy_gamer(gamer):
                self._prepare_gamer(gamer, projects, ensure_daily=enabled)
                with _bind_bank_notifications(
                        gamer, projects,
                ) as bank_notifications:
                    projects_changed = False
                    if enabled:
                        payload = mutation(gamer, projects)
                        projects_changed = bool(
                            payload.pop('_projects_changed', False)
                        )
                        reward_messages = (
                            self._settle_rewards(gamer) if settle_rewards else []
                        )
                    else:
                        payload = dict(disabled_payload or {})
                        reward_messages = []
                    projects_changed = (
                        projects_changed or bank_notifications['value']
                    )
                    bank_messages = list(bank_notifications['messages'])
                    command_messages = self._command_messages(
                        payload.get('message'), reward_messages, bank_messages,
                    )
                if enabled:
                    projects_changed = _append_game_notifications(
                        projects, command_messages,
                    ) or projects_changed
                if enabled:
                    self._prepare_gamer(gamer, projects, ensure_daily=True)
                notification_ids_changed = _ensure_notification_ids(projects)
                projects_changed = projects_changed or notification_ids_changed
                state = self._serialize_state(gamer, projects, enabled=enabled)
            if enabled:
                self.repository.write_gamer(gamer)
            if projects_changed:
                if notification_ids_changed:
                    self._backup_notification_migration()
                self.repository.write_projects(projects)
        return {
            'ok': True,
            **payload,
            'messages': command_messages,
            'state': state,
        }

    @staticmethod
    def _command_messages(
            message: Any,
            reward_messages: list[str],
            bank_messages: list[str],
    ) -> list[str]:
        """Return each user-facing event once and keep bank events separate."""
        messages: list[str] = []
        if isinstance(message, str) and message.strip():
            if not bank_messages or message.strip() != '\n'.join(bank_messages):
                messages.append(message)
        messages.extend(
            item for item in reward_messages
            if isinstance(item, str) and item.strip()
        )
        messages.extend(
            item for item in bank_messages
            if isinstance(item, str) and item.strip()
        )
        return messages

    def _read_gamer(self) -> legacy_game.Gamer:
        gamer = self.repository.read_gamer()
        return gamer if isinstance(gamer, legacy_game.Gamer) else legacy_game.Gamer()

    def _read_projects(self) -> JSONDict:
        data = self.repository.read_projects()
        return data if isinstance(data, dict) else {'projects': {}}

    def _game_mode_enabled(self) -> bool:
        settings = self.repository.read_settings()
        return bool(settings.get('game_mode', False))

    def _prepare_gamer(
            self,
            gamer: legacy_game.Gamer,
            projects: JSONDict,
            *,
            ensure_daily: bool,
    ) -> bool:
        before = self._preparation_snapshot(gamer)
        try:
            gamer.level = min(
                len(game_data.levels) - 1, max(1, int(gamer.level)),
            )
        except (TypeError, ValueError):
            gamer.level = 1
        gamer.normalize_coins()
        gamer.normalize_skills()
        gamer.normalize_cf()
        gamer.normalize_motivation()
        gamer.normalize_inventory_item_names()
        custom_awards_changed = self._normalize_custom_awards(gamer)
        gamer.sync_quests()
        gamer.update_max_health()
        gamer.update_cf()
        if gamer.bank_account is None:
            gamer.bank_account = game_data.BankAccount()
        gamer.bank_account.normalize()
        self._migrate_manuscript_journey_keys(gamer, projects)
        if ensure_daily:
            self._install_authoritative_daily_challenges(gamer, projects)
        return (
            custom_awards_changed
            or before != self._preparation_snapshot(gamer)
        )

    @staticmethod
    def _preparation_snapshot(gamer: legacy_game.Gamer) -> Any:
        return pickle.dumps((
            getattr(gamer, 'level', None),
            getattr(gamer, 'coins', None),
            getattr(gamer, 'skills', None),
            getattr(gamer, 'available_skill_points', None),
            getattr(gamer, 'daily_challenge', None),
            getattr(gamer, 'daily_challenge_options', None),
            getattr(gamer, 'weekly_challenge', None),
            getattr(gamer, 'writing_session', None),
            getattr(gamer, 'manuscript_journeys', None),
            getattr(gamer, 'cabinet_relics', None),
            getattr(gamer, 'complete_bonus_projects', None),
            getattr(gamer, 'api_streak_reward_days', None),
            getattr(gamer, 'items', None),
            getattr(gamer, 'cf', None),
            getattr(gamer, 'buffs', None),
            getattr(gamer, 'debuffs', None),
            getattr(gamer, 'bank_account', None),
            [
                (getattr(quest, 'quest_id', None), getattr(quest, 'status', None))
                for quest in getattr(gamer, 'quests', [])
            ],
        ), protocol=4)

    @staticmethod
    def _projects_mapping(projects: JSONDict) -> Mapping[str, Any]:
        value = projects.get('projects', {})
        return value if isinstance(value, Mapping) else {}

    def _install_authoritative_daily_challenges(
            self, gamer: legacy_game.Gamer, projects: JSONDict,
    ) -> None:
        target = gamer.calculate_adaptive_daily_target(data=projects)
        generated = gamer.generate_daily_challenge_options(target=target)
        generated_by_id = {option['option_id']: option for option in generated}
        saved_options = {
            option.get('option_id'): option
            for option in gamer.daily_challenge_options
            if isinstance(option, dict)
        }
        normalized_options = []
        for option in generated:
            saved = saved_options.get(option['option_id'], {})
            authoritative = dict(option)
            authoritative['progress'] = max(0, int(saved.get('progress', 0)))
            authoritative['completed'] = bool(saved.get('completed', False))
            normalized_options.append(authoritative)
        gamer.daily_challenge_options = normalized_options

        current = gamer.daily_challenge
        current_id = current.get('option_id') if isinstance(current, dict) else None
        authoritative = generated_by_id.get(current_id)
        if authoritative is None:
            gamer.daily_challenge = dict(normalized_options[0])
            return
        normalized_current = dict(authoritative)
        normalized_current['progress'] = max(0, int(current.get('progress', 0)))
        normalized_current['completed'] = bool(current.get('completed', False))
        gamer.daily_challenge = normalized_current
        for index, option in enumerate(gamer.daily_challenge_options):
            if option['option_id'] == current_id:
                gamer.daily_challenge_options[index] = dict(normalized_current)
                break

    def _migrate_manuscript_journey_keys(
            self, gamer: legacy_game.Gamer, projects: JSONDict,
    ) -> bool:
        aliases: dict[str, set[str]] = {}
        for stored_name, project in self._projects_mapping(projects).items():
            project_id = getattr(project, 'project_id', None)
            if not project_id:
                continue
            project_key = f'project:{project_id}'
            project_name = str(getattr(project, 'name', stored_name))
            for alias in {str(stored_name), project_name}:
                aliases.setdefault(alias, set()).add(project_key)
            for stage in getattr(project, 'stages', []):
                stage_id = getattr(stage, 'stage_id', None)
                if not stage_id:
                    continue
                stage_key = f'stage:{project_id}:{stage_id}'
                stage_name = str(getattr(stage, 'name', ''))
                for alias in {
                    stage_name,
                    f'stage:{project_name}:{stage_id}',
                    f'stage:{stored_name}:{stage_id}',
                }:
                    if alias:
                        aliases.setdefault(alias, set()).add(stage_key)

        changed = False
        journeys = gamer.manuscript_journeys
        for alias, stable_keys in aliases.items():
            if len(stable_keys) != 1 or alias not in journeys:
                continue
            stable_key = next(iter(stable_keys))
            if alias == stable_key:
                continue
            old_values = journeys.pop(alias, [])
            merged = sorted(set(journeys.get(stable_key, [])) | set(old_values))
            journeys[stable_key] = merged
            changed = True
        if changed:
            gamer.unlock_cabinet_relics()
        completed = getattr(gamer, 'complete_bonus_projects', [])
        if isinstance(completed, list):
            migrated_completed: list[str] = []
            for value in completed:
                stable_keys = aliases.get(str(value), set())
                migrated_value = (
                    next(iter(stable_keys)) if len(stable_keys) == 1 else str(value)
                )
                if migrated_value not in migrated_completed:
                    migrated_completed.append(migrated_value)
            if completed != migrated_completed:
                gamer.complete_bonus_projects = migrated_completed
                changed = True
        return changed

    def _serialize_state(
            self,
            gamer: legacy_game.Gamer,
            projects: JSONDict,
            *,
            enabled: bool,
    ) -> JSONDict:
        labels = self._owner_labels(projects)
        return {
            'enabled': enabled,
            'server_time': legacy_game.get_effective_now().isoformat(),
            'profile': serialize_profile(gamer),
            'skills': serialize_skills(gamer),
            'buffs': serialize_buffs(gamer),
            'inventory': serialize_inventory(gamer),
            'notifications': serialize_notifications(projects),
            'streak_freezes': serialize_streak_freezes(gamer, projects),
            'quests': serialize_quests(gamer),
            'daily_challenge': serialize_daily_challenge(gamer),
            'weekly_challenge': serialize_weekly_challenge(gamer),
            'writing_session': serialize_writing_session(gamer),
            'inspiration': serialize_inspiration(gamer),
            'specializations': serialize_specializations(gamer),
            'manuscripts': serialize_manuscripts_and_cabinet(gamer, labels),
            'bank': serialize_bank_summary(gamer),
            'custom_awards': serialize_custom_awards(gamer),
            'shop': serialize_shop_catalog(gamer),
        }

    def _owner_labels(self, projects: JSONDict) -> dict[str, str]:
        labels: dict[str, str] = {}
        for stored_name, project in self._projects_mapping(projects).items():
            project_id = getattr(project, 'project_id', None)
            if not project_id:
                continue
            name = str(getattr(project, 'name', stored_name))
            labels[f'project:{project_id}'] = name
            for stage in getattr(project, 'stages', []):
                stage_id = getattr(stage, 'stage_id', None)
                if stage_id:
                    labels[f'stage:{project_id}:{stage_id}'] = (
                        f'{name} — {getattr(stage, "name", stage_id)}'
                    )
        return labels

    def _resolve_project_progress(
            self,
            projects: JSONDict,
            project_key: str,
            fallback_progress: float,
    ) -> float:
        entity, _is_stage = self._resolve_project_entity(projects, project_key)
        return self._bounded_progress(getattr(entity, 'progress', fallback_progress))

    def _resolve_project_entity(
            self, projects: JSONDict, project_key: str,
    ) -> tuple[Any, bool]:
        for project in self._projects_mapping(projects).values():
            project_id = getattr(project, 'project_id', None)
            if project_key == f'project:{project_id}':
                return project, False
            for stage in getattr(project, 'stages', []):
                if project_key == f'stage:{project_id}:{getattr(stage, "stage_id", None)}':
                    return stage, True
        raise NotFoundError(
            'game_project_not_found',
            'Проект для игрового прогресса не найден.',
        )

    def _apply_streak_events(
            self,
            gamer: legacy_game.Gamer,
            projects: JSONDict,
            events: list[dict[str, Any]],
            *,
            default_key: str,
    ) -> tuple[list[str], bool]:
        messages: list[str] = []
        projects_changed = False
        today = engine.today_for_test()
        for event in events:
            if not isinstance(event, dict):
                raise ValidationError(
                    'streak_event_invalid', 'Событие стрика имеет неверный формат.',
                )
            streak_type = str(event.get('type', event.get('streak_type', '')))
            if streak_type not in {'Local', 'Global'}:
                raise ValidationError(
                    'streak_type_invalid', 'Неизвестный тип стрика.',
                )
            status = event.get('status')
            if not isinstance(status, str) or not status.strip():
                raise ValidationError(
                    'streak_status_invalid', 'Статус стрика имеет неверный формат.',
                )
            length = self._nonnegative_integer(
                event.get('length', event.get('streak_length', 0)),
                maximum=1_000_000,
            )
            event_key = str(
                event.get('key', event.get('project_key', default_key))
            )
            if streak_type == 'Local':
                streak_owner, _is_stage = self._resolve_project_entity(
                    projects, event_key,
                )
                last_bonus_day = getattr(streak_owner, 'last_streak_bonus', None)
                reward_marker_key = f'local:{event_key}'
            else:
                streak_owner = None
                last_bonus_day = projects.get('last_global_streak_bonus')
                reward_marker_key = 'global'
            gamer_bonus_day = gamer.api_streak_reward_days.get(reward_marker_key)
            legacy_bonus_is_due = engine.streak_bonus_is_due(last_bonus_day, today)
            gamer_bonus_is_due = engine.streak_bonus_is_due(gamer_bonus_day, today)
            if not legacy_bonus_is_due or not gamer_bonus_is_due:
                # The gamer marker is committed in the same pickle as the
                # reward. It acts as a tiny recovery journal if writing the
                # compatibility marker in data.pkl failed after gamer.pkl.
                gamer.api_streak_reward_days[reward_marker_key] = today
                if legacy_bonus_is_due:
                    if streak_owner is not None:
                        streak_owner.last_streak_bonus = today
                    else:
                        projects['last_global_streak_bonus'] = today
                    projects_changed = True
                continue
            message = gamer.give_streak_bonus(
                status,
                streak_type,
                length,
                project_name=event_key if streak_type == 'Local' else None,
            )
            if message:
                messages.append(message)
                gamer.api_streak_reward_days[reward_marker_key] = today
                if streak_owner is not None:
                    streak_owner.last_streak_bonus = today
                else:
                    projects['last_global_streak_bonus'] = today
                projects_changed = True
        return messages, projects_changed

    @staticmethod
    def _bounded_progress(value: Any) -> float:
        try:
            return min(100.0, max(0.0, float(value)))
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _normalize_custom_awards(gamer: legacy_game.Gamer) -> bool:
        changed = False
        raw_awards = getattr(gamer, 'custom_awards', [])
        if not isinstance(raw_awards, list):
            raw_awards = list(raw_awards) if isinstance(raw_awards, tuple) else []
            gamer.custom_awards = raw_awards
            changed = True

        raw_inventory = getattr(gamer, 'custom_awards_inventory', {})
        if not isinstance(raw_inventory, dict):
            raw_inventory = {}
            changed = True
        normalized_inventory: dict[str, int] = {}
        for raw_name, raw_count in raw_inventory.items():
            inventory_name = str(raw_name)
            try:
                inventory_count = int(raw_count)
            except (TypeError, ValueError):
                inventory_count = 0
            if isinstance(raw_count, bool):
                inventory_count = 0
            inventory_count = max(0, inventory_count)
            normalized_inventory[inventory_name] = (
                normalized_inventory.get(inventory_name, 0) + inventory_count
            )
            if inventory_name != raw_name or inventory_count != raw_count:
                changed = True
        if normalized_inventory != raw_inventory:
            changed = True
        gamer.custom_awards_inventory = normalized_inventory

        seen_ids: set[str] = set()
        legacy_inventory = gamer.items.setdefault('Награды', {})
        if not isinstance(legacy_inventory, dict):
            legacy_inventory = {}
            gamer.items['Награды'] = legacy_inventory
            changed = True

        for award in raw_awards:
            if not isinstance(award, game_data.Item):
                continue

            award_id = ''
            for attribute in ('award_id', 'custom_award_id', 'id'):
                candidate = getattr(award, attribute, None)
                if candidate is not None and str(candidate).strip():
                    award_id = str(candidate).strip()
                    break
            if not award_id or award_id in seen_ids:
                award_id = uuid.uuid4().hex
                changed = True
            seen_ids.add(award_id)
            if getattr(award, 'award_id', None) != award_id:
                award.award_id = award_id
                changed = True

            raw_name = getattr(award, 'name', '')
            name = str(raw_name).strip()
            if not name:
                name = f'Награда {award_id[:8]}'
            if raw_name != name:
                award.name = name
                changed = True

            try:
                raw_price = float(getattr(award, '_price', 0))
            except (TypeError, ValueError):
                raw_price = 0.0
            if not math.isfinite(raw_price) or raw_price <= 0:
                raw_price = 1.0
            normalized_price = gamer.round_money(raw_price)
            if getattr(award, '_price', None) != normalized_price:
                award._price = normalized_price
                changed = True

            defaults = {
                'item_type': 'Награды',
                'level': 1,
                'description': 'Кастомная награда без эффекта',
                'available_in_shop': True,
                'sellable': True,
            }
            for attribute, default in defaults.items():
                current = getattr(award, attribute, None)
                if attribute == 'description':
                    needs_default = not current
                elif attribute == 'item_type':
                    needs_default = current != default
                else:
                    needs_default = not hasattr(award, attribute)
                if needs_default:
                    setattr(award, attribute, default)
                    changed = True

            try:
                old_count = max(0, int(getattr(award, 'count', 0)))
            except (TypeError, ValueError):
                old_count = 0
            if old_count:
                gamer.custom_awards_inventory[name] = (
                    gamer.custom_awards_inventory.get(name, 0) + old_count
                )
                changed = True
            if getattr(award, 'count', None) != 0:
                award.count = 0
                changed = True

            try:
                migrated_count = max(0, int(legacy_inventory.get(name, 0)))
            except (TypeError, ValueError):
                migrated_count = 0
            if migrated_count:
                gamer.custom_awards_inventory[name] = (
                    gamer.custom_awards_inventory.get(name, 0) + migrated_count
                )
                legacy_inventory.pop(name, None)
                changed = True
        return changed

    @staticmethod
    def _custom_award_name(value: Any) -> str:
        if not isinstance(value, str):
            raise ValidationError(
                'custom_award_name_invalid',
                'Название награды должно быть непустой строкой.',
            )
        name = value.strip()
        if (
                not name
                or len(name) > 200
                or any(ord(character) < 32 for character in name)
        ):
            raise ValidationError(
                'custom_award_name_invalid',
                'Название награды должно содержать от 1 до 200 символов.',
            )
        return name

    @staticmethod
    def _custom_award(
            gamer: legacy_game.Gamer, award_id: str,
    ) -> game_data.Item:
        award_id = str(award_id).strip()
        for award in getattr(gamer, 'custom_awards', []):
            if (
                    isinstance(award, game_data.Item)
                    and str(getattr(award, 'award_id', '')) == award_id
            ):
                return award
        raise NotFoundError(
            'custom_award_not_found', 'Кастомная награда не найдена.',
        )

    @staticmethod
    def _ensure_custom_award_name_available(
            gamer: legacy_game.Gamer,
            name: str,
            *,
            current: game_data.Item | None = None,
    ) -> None:
        for award in getattr(gamer, 'custom_awards', []):
            if award is not current and getattr(award, 'name', None) == name:
                raise ConflictError(
                    'custom_award_name_conflict',
                    'Награда с таким названием уже существует.',
                )
        registered = game_data.ITEM_REGISTRY.get('Награды', {}).get(name)
        if registered is not None and registered is not current:
            raise ConflictError(
                'custom_award_name_conflict',
                'Награда с таким названием уже существует.',
            )

    @staticmethod
    def _custom_award_count(
            gamer: legacy_game.Gamer, award: game_data.Item,
    ) -> int:
        try:
            return max(0, int(gamer.custom_awards_inventory.get(award.name, 0)))
        except (TypeError, ValueError):
            return 0

    @classmethod
    def _cleanup_custom_award(
            cls, gamer: legacy_game.Gamer, award: game_data.Item,
    ) -> bool:
        if (
                bool(getattr(award, 'available_in_shop', True))
                or cls._custom_award_count(gamer, award) > 0
        ):
            return False
        gamer.custom_awards = [
            candidate
            for candidate in gamer.custom_awards
            if candidate is not award
        ]
        gamer.custom_awards_inventory.pop(award.name, None)
        return True

    @staticmethod
    def _positive_money(
            value: Any,
            *,
            code: str = 'bank_amount_invalid',
            label: str = 'Сумма',
    ) -> float:
        if isinstance(value, bool):
            raise ValidationError(code, f'{label} должна быть больше 0.')
        try:
            amount = float(value)
        except (TypeError, ValueError) as error:
            raise ValidationError(code, f'{label} должна быть числом.') from error
        if not math.isfinite(amount) or amount <= 0 or amount > 1_000_000_000_000:
            raise ValidationError(
                code,
                f'{label} должна быть больше 0 и не превышать 1000000000000.',
            )
        amount = legacy_game.Gamer.round_money(amount)
        if amount <= 0:
            raise ValidationError(code, f'{label} должна быть больше 0.')
        return amount

    @staticmethod
    def _positive_days(value: Any) -> int:
        if isinstance(value, bool):
            raise ValidationError(
                'bank_days_invalid', 'Срок должен быть положительным целым числом.',
            )
        try:
            days = int(value)
        except (TypeError, ValueError) as error:
            raise ValidationError(
                'bank_days_invalid', 'Срок должен быть положительным целым числом.',
            ) from error
        if days <= 0 or days > 36_500 or str(value).strip() != str(days):
            raise ValidationError(
                'bank_days_invalid',
                'Срок должен быть целым числом от 1 до 36500 дней.',
            )
        return days

    @staticmethod
    def _boolean_option(value: Any, name: str) -> bool:
        if not isinstance(value, bool):
            raise ValidationError(
                'boolean_option_invalid',
                f'Параметр {name} должен быть логическим значением.',
            )
        return value

    @staticmethod
    def _bank_product_type(value: Any) -> str:
        product_type = str(value).strip().casefold()
        if product_type not in {'credit', 'deposit'}:
            raise ValidationError(
                'bank_product_type_invalid',
                'Неизвестный банковский продукт.',
            )
        return product_type

    @staticmethod
    def _bank_account(gamer: legacy_game.Gamer) -> game_data.BankAccount:
        account = getattr(gamer, 'bank_account', None)
        if not isinstance(account, game_data.BankAccount):
            account = game_data.BankAccount()
            gamer.bank_account = account
        account.normalize()
        return account

    @staticmethod
    def _validate_new_bank_product(
            gamer: legacy_game.Gamer,
            account: game_data.BankAccount,
            product_type: str,
            amount: float,
            days: int,
    ) -> None:
        if product_type == 'credit':
            if account.get_credit() is not None:
                raise ConflictError(
                    'bank_credit_already_active',
                    'У вас уже есть активный кредит.',
                )
            if gamer.level < 3:
                raise ConflictError(
                    'bank_credit_level_too_low',
                    'Кредиты доступны с 3 уровня.',
                )
            limit = account.get_credit_limit(gamer)
            if amount > limit:
                raise ConflictError(
                    'bank_credit_limit_exceeded',
                    f'Сумма выше кредитного лимита: {limit} монет.',
                )
            maximum_days = account.get_max_credit_days()
            if days > maximum_days:
                raise ValidationError(
                    'bank_credit_days_exceeded',
                    f'Максимальный срок кредита: {maximum_days} дн.',
                )
            return
        if account.get_deposit() is not None:
            raise ConflictError(
                'bank_deposit_already_active',
                'У вас уже есть активный вклад.',
            )
        if gamer.get_coins() < amount:
            raise ConflictError(
                'not_enough_coins',
                f'Недостаточно монет. Нужно: {amount}',
            )

    @staticmethod
    def _registry_item(
            category: str, item_key: str,
    ) -> tuple[str, game_data.Item]:
        registry = game_data.ITEM_REGISTRY.get(category)
        if not isinstance(registry, dict) or item_key not in registry:
            raise NotFoundError('shop_item_not_found', 'Предмет не найден.')
        return item_key, registry[item_key]

    @staticmethod
    def _positive_count(value: Any, *, maximum: int = _MAX_ITEM_COMMAND_COUNT) -> int:
        if isinstance(value, bool):
            raise ValidationError(
                'item_count_invalid', 'Количество должно быть положительным целым числом.',
            )
        try:
            count = int(value)
        except (TypeError, ValueError) as error:
            raise ValidationError(
                'item_count_invalid', 'Количество должно быть положительным целым числом.',
            ) from error
        if count <= 0 or count > maximum or str(value).strip() != str(count):
            raise ValidationError(
                'item_count_invalid',
                f'Количество должно быть целым числом от 1 до {maximum}.',
            )
        return count

    @staticmethod
    def _nonnegative_integer(value: Any, *, maximum: int) -> int:
        if isinstance(value, bool):
            raise ValidationError(
                'integer_invalid', 'Значение должно быть целым неотрицательным числом.',
            )
        try:
            result = int(value)
        except (TypeError, ValueError) as error:
            raise ValidationError(
                'integer_invalid', 'Значение должно быть целым неотрицательным числом.',
            ) from error
        if result < 0 or result > maximum or str(value).strip() != str(result):
            raise ValidationError(
                'integer_invalid',
                f'Значение должно быть целым числом от 0 до {maximum}.',
            )
        return result

    @staticmethod
    def _settle_rewards(gamer: legacy_game.Gamer) -> list[str]:
        messages: list[str] = []
        level_message = gamer.level_up()
        if level_message:
            messages.append(level_message)
        messages.extend(gamer.update_quests(save=False))
        level_message = gamer.level_up()
        if level_message:
            messages.append(level_message)
        return messages


__all__ = [
    'GameService',
    'serialize_bank_summary',
    'serialize_buff',
    'serialize_buffs',
    'serialize_custom_award',
    'serialize_custom_awards',
    'serialize_daily_challenge',
    'serialize_inspiration',
    'serialize_inventory',
    'serialize_manuscripts_and_cabinet',
    'serialize_profile',
    'serialize_quest',
    'serialize_quests',
    'serialize_shop_catalog',
    'serialize_skills',
    'serialize_specializations',
    'serialize_weekly_challenge',
    'serialize_writing_session',
]
