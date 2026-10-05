"""Bounded production-routing and deferred-state guard audits for C18.5."""
import json
import re
import sqlite3
from pathlib import Path

import pytest
from nfprogress.core.sqlite.schema import apply_migrations

ROOT=Path(__file__).resolve().parents[1]


def rust_functions(source,names=None):
    # Preserve offsets while removing comments/literals before matching balanced
    # function bodies. Command strings are extracted separately from production TS.
    code=re.sub(r'''//[^\n]*|/\*[\s\S]*?\*/|r\#"[\s\S]*?"\#|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])' ''',lambda m:' '*len(m[0]),source,flags=re.VERBOSE)
    result={}
    for m in re.finditer(r'\bfn\s+(\w+)\s*(?:<[^{}]*>)?\s*\(',code):
        if names is not None and m[1] not in names:continue
        start=code.find('{',m.end());depth=1;end=start+1
        while depth:
            assert end<len(code),m[1]
            depth+=(code[end]=='{')-(code[end]=='}');end+=1
        result[m[1]]=(source[m.start():start],code[start:end],source[start:end])
    return result


def test_game_mutation_routes_reach_the_classified_sqlite_boundary():
    """Discover today's AND future command names from the real desktop API.

    This is a call-graph boundary guard, not a manually copied command-name list.
    A new mutating method or a direct game_state write outside the two audited
    transactional sinks fails even if its API string was never listed in a test.
    """
    api=(ROOT/'frontend/src/api/game.ts').read_text()
    routes=set(re.findall(r"(?:nativeCommand|nativeGame\s*<\s*GameCommandResponse\s*>)\s*\(\s*['\"]([^'\"]+)['\"]",api))
    assert len(routes)>25
    lib=rust_functions((ROOT/'frontend/src-tauri/src/lib.rs').read_text(),routes)
    service=rust_functions((ROOT/'frontend/src-tauri/src/game.rs').read_text().split('#[cfg(test)]\nmod tests',1)[0])
    def guarded(name,seen=frozenset()):
        if name in {'mutate_portable_sqlite','process_pending_events'}:
            return True
        if name in seen or name not in service:
            return False
        calls=re.findall(r'Self\s*::\s*(\w+)\s*(?:\(|::)',service[name][1])
        return any(guarded(call,seen|{name}) for call in calls)
    for route in routes:
        assert route in lib,route
        calls=re.findall(r'GameApplicationService\s*::\s*(\w+)',lib[route][1])
        assert calls,route
        # Preview returns the ordinary command DTO but has no mutation. Prove
        # that its production implementation neither persists nor calls mutate.
        for call in calls:
            if call=='preview_bank_product':
                assert not re.search(r'Self::mutate|\.execute\(',service[call][1])
            else:
                assert guarded(call),(route,call)
    sinks={name for name,(_,_,raw) in service.items() if re.search(r'(?:UPDATE|INSERT INTO) game_state',raw)}
    assert sinks=={'process_pending_events','mutate_portable_sqlite'}
    guard=(ROOT/'nfprogress/core/sqlite/migrations/037_game_action_ledgers.sql').read_text()
    assert 'AFTER UPDATE OF payload_json ON game_state' in guard
    assert 'INSERT INTO cloud_game_local_mutations' in guard


@pytest.mark.parametrize('family,path,value',[
    ('streak','global_streak',{'global_streaks':['2026-10-04']}),
    ('project_streak','project_game_state',{'project:local':{'streaks':['2026-10-04']}}),
    ('freeze','gamer.items',{'Другие предметы':{'Заморозка серии':0}}),
    ('bank','gamer.bank_account',{'deposit':{'amount':99}}),
    ('quest','gamer.quests',{'quest':{'status':'done'}}),
    ('daily_challenge','gamer.daily_challenge',{'progress':3}),
    ('weekly_challenge','gamer.weekly_challenge',{'progress':4}),
    ('specialization','gamer.specialization','writer'),
    ('skill','gamer.skills',{'productivity':2}),
    ('custom_award','gamer.custom_awards',{'award':{'text':'private'}}),
    ('item_effect','gamer.buffs',{'effect':{'duration':60}}),
    ('unknown_extension','extensions',{'future_private':{'value':42}}),
    ('future_gamer_field','gamer.future_mutation',{'private':'retained'}),
])
def test_deferred_portable_changes_are_lossless_blocked_and_restart_safe(tmp_path,family,path,value):
    file=tmp_path/(family+'.db');db=sqlite3.connect(file);apply_migrations(db)
    db.execute("INSERT INTO cloud_sync_state VALUES('a','123e4567-e89b-42d3-a456-426614174001',0,0,'now','now')")
    event='123e4567-e89b-42d3-a456-426614174002';frame=b'WORTA-C1'+b'x'*20
    db.execute("INSERT INTO cloud_game_events(account_id,event_id,scope,owner_key,entity_id,canonical_frame,parents_json,revision,state,server_sequence) VALUES('a',?,'account','account','game-state',?,'[]',1,'applied',1)",(event,frame))
    db.execute("INSERT INTO cloud_game_apply_ledger VALUES('a',?,1,'applied',?,?,?)",(event,b'n'*24,b'c'*16,frame))
    db.execute("INSERT INTO cloud_game_migrations VALUES('a','account','candidate','active',NULL)")
    before={'gamer':{'coins':50},'notifications':{'read':[]}}
    after=json.loads(json.dumps(before));target=after
    keys=path.split('.')
    for key in keys[:-1]:target=target.setdefault(key,{})
    target[keys[-1]]=value
    db.execute('INSERT INTO game_state VALUES(1,2,?,?)',(json.dumps(before),'before'))
    db.execute('UPDATE game_state SET payload_json=?,updated_at=?',(json.dumps(after),'after'));db.commit();db.close()
    with sqlite3.connect(file) as db:
        old,new=db.execute('SELECT prior_payload_json,payload_json FROM cloud_game_local_mutations').fetchone()
        assert json.loads(old)==before and json.loads(new)==after
        assert json.loads(db.execute('SELECT payload_json FROM game_state').fetchone()[0])==after
        assert db.execute('SELECT lifecycle,blocker FROM cloud_game_migrations').fetchone()==('blocked','game_unsupported_local_mutation')
        assert db.execute('SELECT count(*) FROM cloud_game_rewards').fetchone()==(0,)
        assert db.execute('SELECT count(*) FROM cloud_sync_outbox').fetchone()==(0,)
