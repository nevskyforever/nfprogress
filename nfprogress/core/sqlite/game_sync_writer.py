"""Typed Python domain consumer writer for already-activated native Game history.

This never captures legacy state, binds projects, encrypts, or imports events.
The paired native readers remain the authenticated apply/ACK authority. Python
v1 keeps its historical raw-XP and round-to-even completion behavior.
"""
from __future__ import annotations

import hashlib
import json
import math
import struct
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID


class GameWriterError(ValueError):
    pass


def canonical(value: Any) -> str:
    if isinstance(value, dict):
        return '{' + ','.join(json.dumps(k, ensure_ascii=False) + ':' + canonical(value[k])
            for k in sorted(value, key=lambda k: k.encode('utf-16-be'))) + '}'
    if isinstance(value, list):
        return '[' + ','.join(map(canonical, value)) + ']'
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':'))


def stable_id(user: str, kind: str, source: Any) -> str:
    raw = bytearray(hashlib.sha256(canonical(['WORTA/C18/game/action/1', user, kind, source]).encode()).digest()[:16])
    raw[6] = raw[6] & 15 | 80
    raw[8] = raw[8] & 63 | 128
    return str(UUID(bytes=bytes(raw)))


def fixed(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or abs(value) > 1e12:
        raise GameWriterError('game_resource_limit')
    raw = f'{value:.6f}'
    if float(raw) != value:
        raise GameWriterError('game_invalid_rule')
    return raw


def frame(event: dict[str, Any]) -> bytes:
    body = canonical(event).encode('utf-8')
    if len(body) + 20 > 1048576:
        raise GameWriterError('game_resource_limit')
    codec = 12 if event['header']['scope'] == 'project' else 13
    return b'WORTA-C1' + bytes((1, codec, 1, 0)) + struct.pack('>II', len(body), len(body)) + body


def streak_base(source: dict[str, Any], *, global_streak: bool = False) -> dict[str, Any]:
    prefix = 'global_' if global_streak else ''
    def day(value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, dict) and value.get('__type__') in {'date', 'datetime'}:
            value = value.get('value')
        if not isinstance(value, str):
            raise GameWriterError('game_legacy_local_conflict')
        try:
            return date.fromisoformat(value[:10]).isoformat()
        except ValueError as error:
            raise GameWriterError('game_legacy_local_conflict') from error
    history = []
    for entry in source.get(prefix + 'streaks', []):
        frozen = entry == 'freeze'
        if frozen and not history:
            raise GameWriterError('game_legacy_local_conflict')
        writing_day = (date.fromisoformat(history[-1]['day']) + timedelta(days=1)).isoformat() if frozen else day(entry)
        history.append(dict(day=writing_day, frozen=frozen))
    return dict(history=history, maximum=source.get('max_' + prefix + 'streak', len(history)),
        freezes=sum(entry['frozen'] for entry in history) if global_streak else source.get('freezes',0),
        enabled=source.get(prefix + 'streak_status') != 'Off',
        last_reward_day=day(source.get('last_' + prefix + 'streak_bonus')),
        lost_day=day(source.get('last_' + prefix + 'streak_lost_date')),
        lost_length=source.get('last_' + prefix + 'streak_lose_len', 0))


def recorded(db: Any, event: Any) -> bool:
    row = db.execute("SELECT b.account_id FROM cloud_sync_project_bindings b WHERE b.project_id=?", (event['project_id'],)).fetchone()
    if row is None:
        return False
    owner = canonical([event['project_id'], event['stage_id']])
    return bool(db.execute("SELECT EXISTS(SELECT 1 FROM cloud_game_sources s JOIN cloud_game_events g ON g.account_id=s.account_id AND g.event_id=s.project_action_id WHERE s.account_id=? AND g.owner_key=? AND (s.source_key=? OR (? IS NOT NULL AND json_extract(CAST(substr(g.canonical_frame,21) AS TEXT),'$.action.kind')='writing' AND json_extract(CAST(substr(g.canonical_frame,21) AS TEXT),'$.action.fact.entry_id')=? AND json_extract(CAST(substr(g.canonical_frame,21) AS TEXT),'$.action.fact.delta')=?)))",
        (row[0], owner, event['event_id'], event['progress_id'], event['progress_id'], f"{event['delta_symbols'] or 0:.6f}")).fetchone()[0])


def capture_local(db: Any, event: Any, context: dict[str, Any], before: dict[str, Any], after: dict[str, Any]) -> bool:
    p, stage, kind = event['project_id'], event['stage_id'], event['event_type']
    owner = canonical([p, stage])
    scope = db.execute("SELECT b.account_id,u.canonical_user_id,s.device_id FROM cloud_sync_project_bindings b JOIN cloud_account_bindings u ON u.local_account_id=b.account_id JOIN cloud_sync_state s ON s.account_id=b.account_id WHERE b.project_id=?", (p,)).fetchone()
    if scope is None:
        return False
    account, user, device = scope
    active = db.execute("SELECT count(*) FROM cloud_game_migrations WHERE account_id=? AND owner_key IN ('account',?) AND lifecycle='active'", (account, owner)).fetchone()[0]
    if active != 2 or not (kind == 'ProgressAdded' and (event['delta_symbols'] or 0) > 0 or kind in {'ProjectCompleted', 'StageCompleted'}):
        return False
    if before == after:
        return False
    db.execute('SAVEPOINT python_game_writer')
    try:
        _capture(db, event, context, before, after, account, user, device, owner)
    except GameWriterError as error:
        db.execute('ROLLBACK TO python_game_writer')
        db.execute('RELEASE python_game_writer')
        code = str(error)
        db.execute("INSERT INTO cloud_game_blockers VALUES(?,'account','',?) ON CONFLICT(account_id,owner_key,event_id) DO UPDATE SET code=excluded.code", (account, code))
        db.execute("UPDATE cloud_game_migrations SET lifecycle='blocked',blocker=? WHERE account_id=?", (code, account))
        return False
    except Exception:
        db.execute('ROLLBACK TO python_game_writer')
        db.execute('RELEASE python_game_writer')
        raise
    db.execute('RELEASE python_game_writer')
    return True


def _capture(db: Any, event: Any, context: dict[str, Any], before: dict[str, Any], after: dict[str, Any], account: str, user: str, device: str, owner: str) -> None:
    from nfprogress.core.game_state import DeterministicGameRules, _gamer_cf
    if DeterministicGameRules().apply(before, event, context) != after:
        raise GameWriterError('game_unsupported_local_mutation')
    raw = db.execute('SELECT payload_json FROM game_state WHERE id=1').fetchone()[0]
    if json.loads(raw) != before:
        raise GameWriterError('game_legacy_local_conflict')
    parents = {}
    snapshots = {}
    for key in (owner, 'account'):
        heads = [r[0] for r in db.execute('SELECT event_id FROM cloud_game_tips WHERE account_id=? AND owner_key=? ORDER BY event_id', (account, key))]
        if len(heads) != 1:
            raise GameWriterError('game_noncommutative_conflict')
        parents[key] = heads
        row = db.execute('SELECT head_event_id,snapshot_json FROM cloud_game_projection WHERE account_id=? AND owner_key=?', (account, key)).fetchone()
        if row is None or row[0] != heads[0]:
            raise GameWriterError('game_legacy_local_conflict')
        snapshots[key] = json.loads(row[1])
    base = snapshots['account'];gamer = before['gamer']
    fields = dict(coins='coins', experience='exp', inspiration='inspiration', writing_bonus='writing_reward_bonus', health='health', max_health='max_health')
    if any(fixed(gamer.get(source, 0)) != base[target] for target, source in fields.items()):
        raise GameWriterError('game_legacy_local_conflict')
    for key in ('level', 'available_skill_points', 'skill_points_awarded_for_level', 'skills'):
        if gamer.get(key) != base[key]:
            raise GameWriterError('game_legacy_local_conflict')
    for target, key in (('coin_coefficient', 'coins'), ('experience_coefficient', 'exp'), ('health_recovery_coefficient', 'health_recovery')):
        if fixed(_gamer_cf(gamer, key)) != base[target]:
            raise GameWriterError('game_legacy_local_conflict')
    inventory = [dict(category=category,item_id=item,count=count)
        for category, items in gamer.get('items', {}).items()
        for item, count in items.items() if count > 0]
    inventory.sort(key=lambda item: (item['category']+'\0'+item['item_id']).encode('utf-16-be'))
    pending = 'absent' if 'pending_creative_event' not in gamer else 'none' if gamer['pending_creative_event'] is None else gamer['pending_creative_event']
    claims = sorted(set(gamer.get('complete_bonus_projects', [])),key=lambda s:s.encode('utf-16-be'))
    if (inventory != base['inventory'] or claims != base['completion_claims']
            or gamer.get('productive_actions_since_event', 0) != base['productive_actions']
            or pending != base['creative_event_pending']
            or streak_base(before.get('global_streak', {}),global_streak=True) != base['global_streak']):
        raise GameWriterError('game_legacy_local_conflict')
    p, stage, kind = event['project_id'], event['stage_id'], event['event_type']
    metadata = db.execute("SELECT p.head_event_id,b.bootstrap_id FROM cloud_sync_metadata_projection p JOIN cloud_sync_metadata_events e ON e.account_id=p.account_id AND e.event_id=p.head_event_id JOIN cloud_sync_metadata_reconciliation r ON r.account_id=p.account_id AND r.project_id=p.project_id AND r.head_event_id=p.head_event_id JOIN cloud_sync_project_bootstraps b ON b.account_id=p.account_id AND b.project_id=p.project_id WHERE p.account_id=? AND p.project_id=? AND e.state='applied' AND e.deleted_at IS NULL AND (SELECT count(*) FROM cloud_sync_metadata_tips t WHERE t.account_id=p.account_id AND t.project_id=p.project_id)=1", (account, p)).fetchone()
    if metadata is None:
        raise GameWriterError('game_project_authority_unresolved')
    refs = [r[0] for r in db.execute("SELECT t.event_id FROM cloud_sync_structural_tips t JOIN cloud_sync_structural_events e USING(account_id,event_id) WHERE t.account_id=? AND t.project_id=? AND t.entity_type='stage' AND t.entity_id=? AND e.state='applied' AND e.operation!='delete' ORDER BY t.event_id", (account, p, stage))] if stage else []
    if stage and len(refs) != 1:
        raise GameWriterError('game_stage_authority_unresolved')
    entity = f'stage:{stage}' if stage else 'project'
    if kind == 'ProgressAdded':
        rows = db.execute("SELECT e.canonical_frame FROM cloud_progress_events e JOIN cloud_sync_outbox o USING(account_id,event_id) WHERE e.account_id=? AND e.project_id=? AND e.entity_id=? AND o.entity_type='progress' AND o.operation='event' AND json_extract(CAST(substr(e.canonical_frame,21) AS TEXT),'$.header.operation')='append' AND json_extract(CAST(substr(e.canonical_frame,21) AS TEXT),'$.entries[0].entry_id')=? LIMIT 2", (account, p, entity, event['progress_id'])).fetchall()
        if len(rows) != 1:
            raise GameWriterError('game_dependency_progress_missing')
        progress = json.loads(bytes(rows[0][0])[20:]);fact = progress['entries'][0]
        if progress['header']['account_id'] != user or progress['header']['stage_id'] != stage or fact['delta'] != fixed(event['delta_symbols']):
            raise GameWriterError('game_scope_mismatch')
        gid = stable_id(user, 'writing', [p, stage, progress['header']['event_id'], fact['entry_id']])
        action = dict(kind='writing', progress_event_id=progress['header']['event_id'], progress_entity_id=entity, fact=fact,
            inspiration=base['inspiration'], writing_bonus=base['writing_bonus'], coin_coefficient=base['coin_coefficient'], experience_coefficient=base['experience_coefficient'])
    else:
        # Completion requires an authenticated, finished structural source. A
        # compatibility-only status change cannot manufacture cloud authority.
        row = db.execute('SELECT head_event_id,snapshot_json FROM cloud_progress_projection WHERE account_id=? AND project_id=? AND entity_id=?', (account, p, entity)).fetchone()
        if row is None:
            raise GameWriterError('game_dependency_progress_missing')
        total = fixed(context.get('total_symbols', 0))
        chain = json.loads(row[1]);chain = chain.get('chain', chain)
        historical = chain['entries'][-1]['new_total'] if chain['entries'] else chain['base_total']
        if historical != total:
            raise GameWriterError('game_dependency_progress_missing')
        if stage:
            source = json.loads(bytes(db.execute('SELECT canonical_frame FROM cloud_sync_structural_events WHERE account_id=? AND event_id=?', (account, refs[0])).fetchone()[0])[20:])['stage']
        else:
            source = json.loads(db.execute('SELECT payload_json FROM cloud_sync_metadata_events WHERE account_id=? AND event_id=?', (account, metadata[0])).fetchone()[0])
        if source['status'] != 'завершен':
            raise GameWriterError('game_project_authority_unresolved')
        cid = 'completion:' + owner
        gid = stable_id(user, 'completion', [p, stage, cid])
        action = dict(kind='completion', completion_id=cid, progress_event_id=row[0], progress_entity_id=entity, total_symbols=total)
    next_base = json.loads(canonical(base));next_project = json.loads(canonical(snapshots[owner]))
    reward_coins = after['gamer']['coins'] - gamer['coins']
    # Writing rounds the *final balance*, so freeze the rule's grant rather than
    # incorrectly treating that rounded balance difference as the reward input.
    if kind == 'ProgressAdded':
        delta = float(action['fact']['delta']);multiplier = (1 + float(base['inspiration']) / 100 * .1) * (1 + float(base['writing_bonus']))
        reward_coins = math.ceil((delta / 100 * 10 * float(base['coin_coefficient']) * multiplier - 1e-9) * 10) / 10
    reward = dict(coins=fixed(reward_coins), experience=fixed(after['gamer']['exp'] - gamer['exp']))
    action['reward'] = reward
    next_base.update(coins=fixed(after['gamer']['coins']), experience=fixed(after['gamer']['exp']), writing_bonus=fixed(after['gamer'].get('writing_reward_bonus', 0)))
    if kind != 'ProgressAdded':
        next_base['completion_claims'] = sorted(after['gamer']['complete_bonus_projects'], key=lambda s: s.encode('utf-16-be'))
        next_project['completion_claimed'] = True
    now = datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')
    def header(key: str, eid: str) -> dict[str, Any]:
        revision = db.execute('SELECT revision FROM cloud_game_events WHERE account_id=? AND event_id=?', (account, parents[key][0])).fetchone()[0] + 1
        return dict(account_id=user, device_id=device, event_id=eid, entity_id='game:' + eid, parents=parents[key], revision=revision, updated_at=now, rule='python-game-v1', scope='account', entity_type='account_game')
    gh = header(owner, gid);gh.pop('entity_type');gh.update(scope='project', project_id=p, stage_id=stage,
        entity_id=f'game:stage:{stage}:{gid}' if stage else f'game:project:{gid}', bootstrap_id=metadata[1], metadata_event_id=metadata[0], stage_event_ids=refs)
    rid = stable_id(user, 'reward', gid)
    g = dict(version=1, header=gh, action=action)
    r = dict(version=1, header=header('account', rid), action=dict(kind='reward', reward_id='reward:' + gid, project_id=p, project_action_id=gid, reward=reward))
    for key, e, snapshot in ((owner, g, next_project), ('account', r, next_base)):
        h = e['header'];encoded = frame(e)
        db.execute("INSERT INTO cloud_game_events(account_id,event_id,scope,owner_key,project_id,stage_id,entity_id,canonical_frame,parents_json,revision,state) VALUES(?,?,?,?,?,?,?,?,?,?,'unsealed')", (account,h['event_id'],h['scope'],key,h.get('project_id'),h.get('stage_id'),h['entity_id'],encoded,canonical(h['parents']),h['revision']))
        db.execute('DELETE FROM cloud_game_tips WHERE account_id=? AND owner_key=?', (account,key))
        db.execute('INSERT INTO cloud_game_tips VALUES(?,?,?)', (account,key,h['event_id']))
        db.execute('UPDATE cloud_game_projection SET head_event_id=?,snapshot_json=?,generation=? WHERE account_id=? AND owner_key=?', (h['event_id'],canonical(snapshot),h['revision'],account,key))
    db.execute('INSERT INTO cloud_game_rewards(account_id,reward_id,event_id,project_action_id,canonical_frame) VALUES(?,?,?,?,?)', (account,'reward:'+gid,rid,gid,frame(r)))
    db.execute('INSERT INTO cloud_game_sources VALUES(?,?,?,?)', (account,event['event_id'],gid,rid))
    db.execute("INSERT INTO cloud_sync_outbox(event_id,account_id,device_id,project_id,entity_id,entity_type,operation,revision,updated_at,created_at,parent_event_id,local_ordinal,lifecycle) VALUES(?,?,?,?,?,'project_game','event',?,?,?,?,(SELECT COALESCE(MAX(local_ordinal),0)+1 FROM cloud_sync_outbox WHERE account_id=?),'unsealed')", (gid,account,device,p,gh['entity_id'],gh['revision'],now,now,gh['parents'][0],account))
    encoded_after=json.dumps(after,ensure_ascii=False,allow_nan=False,sort_keys=True)
    db.execute('INSERT INTO cloud_game_write_intents(account_id,event_id,payload_json,prior_payload_json) VALUES(?,?,?,?)', (account,rid,encoded_after,raw))
