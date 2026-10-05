"""One account stream, real PostgreSQL, production crypto, native SQLite files.

The existing acceptance bridges invoke ordinary writers and protected appliers.
This test intentionally mixes their output in one retained inbox and ACK prefix.
"""
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text
from test_cloud_auth import cloud_client, migrated_database, create_user, login
from test_cloud_c15_headless_cross_runtime import PROJECT_ID, _crypto_bridge, _headers
from test_cloud_c18_authority_cross_runtime import provision, bootstrap, native, publish, sync
from test_cloud_c18_structural_cross_runtime import event, structural, structural_publish
from test_cloud_c18_content_note_acceptance import content as notes, emit as emit_notes
from test_cloud_c18_map_acceptance import maps, change, emit as emit_maps, stored as map_source
from test_cloud_c18_document_acceptance import document, content as document_text, emit as emit_documents, heads
from test_cloud_c18_progress_acceptance import progress, support, emit as emit_progress
from test_cloud_c18_game_acceptance import game, command, emit_game, projections, NOW
from test_cloud_c18_game_gate import declaration
from test_cloud_c18_content_note_gate import capabilities
from nfprogress.core.sqlite.connection import register_remote_apply_authorization_guard

ROOT = Path(__file__).resolve().parents[1]


def upgrade(client, headers, device, kind, codec):
    body=capabilities(device) if kind=='note' else dict(device_id=device,frame_version=1,
        codec_id=codec,codec_version=1,reader_version=1,compression_zero=True)
    assert client.put(f'/api/v3/sync/encrypted/{kind}-reader-capabilities',headers=headers,json=body).status_code == 204


def frozen_gate(client,tmp,token,path,identity,user,amk,third,kind,codec):
    """Block one real ordinary sealed candidate, then upload the exact body."""
    fn={'note':notes,'map':maps,'document':document,'progress':progress}[kind]
    item=fn(tmp,path,identity,user,'pending')[0]
    frame=item['frame']
    h=json.loads(bytes(frame)[20:])['event']['header'] if kind=='note' else item['event']['header']
    action={'note':'content_note_seal','map':'map_seal','document':'document_seal','progress':'progress_seal'}[kind]
    sealed=_crypto_bridge(tmp,dict(action=action,frame=frame,amk=amk))
    if kind=='note':
        fn(tmp,path,identity,user,'seal',event_id=h['event_id'],frame=frame,envelope=sealed['object'])
    else:
        fn(tmp,path,identity,user,'seal',event_id=h['event_id'],frame=frame,nonce=sealed['nonce'],ciphertext=sealed['ciphertext'])
    wire={k:h[k] for k in ('event_id','project_id','entity_id','revision','updated_at')}
    wire.update(entity_type=kind,operation='event',deleted_at=None)
    body=dict(protocol_version=3,encrypted_sync_version=3,device_id=identity['device_id'],items=[dict(event=wire,object=sealed['object'])])
    encoded=json.dumps(body,sort_keys=True)
    rejected=client.post('/api/v3/sync/encrypted/push',headers=_headers(token),json=body)
    assert rejected.status_code==409 and f'{"content_note" if kind=="note" else kind}_readers_not_ready' in rejected.text,rejected.text
    upgrade(client,_headers(token),third,kind,codec)
    accepted=client.post('/api/v3/sync/encrypted/push',headers=_headers(token),json=body)
    assert accepted.status_code==200,accepted.text
    replay=client.post('/api/v3/sync/encrypted/push',headers=_headers(token),json=body)
    assert replay.status_code==200 and replay.json()['results'][0]['duplicate']
    assert replay.json()['results'][0]['server_sequence']==accepted.json()['results'][0]['server_sequence']
    assert json.dumps(body,sort_keys=True)==encoded
    return body


def timestamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')


def pull(client, tmp, token, path, identity, user):
    with sqlite3.connect(path) as db:
        cursor = db.execute('SELECT pull_cursor FROM cloud_sync_state').fetchone()[0]
    response = client.get('/api/v3/sync/encrypted/pull', headers=_headers(token), params=dict(
        device_id=identity['device_id'], since=cursor, limit=100, protocol_version=3, encrypted_sync_version=3))
    assert response.status_code == 200, response.text
    page = response.json()
    rows = []
    for item in page['items']:
        row = dict(item['event']); row['source_device_id'] = row.pop('device_id'); row['envelope'] = item['object']
        row['updated_at'] = timestamp(row['updated_at'])
        if row.get('deleted_at') is not None:
            row['deleted_at'] = timestamp(row['deleted_at'])
        rows.append(row)
    assert game(tmp, path, identity, user, 'receive', command=dict(account_id=identity['local_account_id'],
        device_id=identity['device_id'], canonical_user_id=user, expected_cursor=cursor,
        next_cursor=page['next_cursor'], has_more=page['has_more'], items=rows)) is True
    return page


def retained(path, pending=False):
    """Reopen without network: exact received bytes, not a second pull cursor."""
    from base64 import urlsafe_b64encode
    with sqlite3.connect(path) as db:
        rows = db.execute("SELECT i.event_id,i.server_sequence,i.device_id,i.project_id,i.entity_id,i.entity_type,i.operation,i.sync_revision,i.updated_at,i.deleted_at,o.crypto_version,o.aad_version,o.nonce,o.ciphertext FROM cloud_sync_inbox i JOIN cloud_sync_event_objects o USING(account_id,event_id) " + (" WHERE i.state IN ('received','orphan')" if pending else "") + " ORDER BY i.server_sequence").fetchall()
    result = []
    for r in rows:
        e = dict(zip(('event_id','server_sequence','device_id','project_id','entity_id','entity_type','operation','revision','updated_at','deleted_at'), r[:10]))
        result.append(dict(event=e, object=dict(crypto_version=r[10], aad_version=r[11],
            nonce=urlsafe_b64encode(r[12]).decode().rstrip('='), ciphertext=urlsafe_b64encode(r[13]).decode().rstrip('='))))
    return result


def apply_all(tmp, path, identity, user, amk, hold_progress=False):
    outcomes = []
    for item in retained(path, pending=True):
        e = item['event']; kind = e['entity_type']
        if kind == 'project_game' or kind == 'progress' and hold_progress:
            continue
        action = dict(project_metadata='metadata_open', stage='structural_open', stage_order='structural_open',
            note='content_note_open', map='map_open', document='document_open', progress='progress_open')[kind]
        opened = _crypto_bridge(tmp, dict(action=action, canonical_user_id=user, amk=amk, item=item))
        if kind == 'project_metadata':
            result = native(tmp, path, identity, user, 'apply', opened=opened)['view']['state']
        elif kind in ('stage','stage_order'):
            result = structural(tmp, path, identity, user, 'apply', event_id=e['event_id'], opened=opened)
        elif kind == 'note':
            result = game(tmp, path, identity, user, 'content_note_apply', event=e, opened=opened)
        elif kind == 'map':
            result = maps(tmp, path, identity, user, 'apply', opened=opened)
        else:
            fn = document if kind == 'document' else progress
            result = fn(tmp, path, identity, user, 'apply', **{k:opened[k] for k in ('frame','nonce','ciphertext')})
        assert not isinstance(result, dict) or 'error' not in result, result
        outcomes.append((e['server_sequence'], kind, result))
    # Account rewards can precede their project source. Retry retained encrypted
    # rows, not a page-local list; every invocation reopens the native database.
    for _ in range(3):
        for row in command(tmp, path, identity, user, 'received', limit=32):
            from base64 import urlsafe_b64encode
            account = row['scope'] == 'account'
            e = dict(event_id=row['event_id'], device_id=row['source_device_id'], entity_id=row['entity_id'],
                revision=row['revision'], updated_at=row['updated_at'], deleted_at=None, server_sequence=row['server_sequence'])
            e.update(dict(scope='account', canonical_user_id=user, entity_type='account_game', operation='upsert') if account
                else dict(project_id=row['project_id'], entity_type='project_game', operation='event'))
            obj = dict(crypto_version=2 if account else 1, aad_version=2 if account else 1,
                nonce=urlsafe_b64encode(bytes(row['nonce'])).decode().rstrip('='),
                ciphertext=urlsafe_b64encode(bytes(row['ciphertext'])).decode().rstrip('='))
            opened = _crypto_bridge(tmp, dict(action='game_open', scope=row['scope'], canonical_user_id=user, amk=amk, item=dict(event=e,object=obj)))
            result = command(tmp, path, identity, user, 'apply', project=not account,
                **{k:opened[k] for k in ('frame','nonce','ciphertext')})
            outcomes.append((row['server_sequence'], e['entity_type'], result))
    return outcomes


def converge(client, tmp, token, devices, user, amk):
    for path, identity in devices:
        pull(client, tmp, token, path, identity, user)
        apply_all(tmp, path, identity, user, amk)


def portable(path):
    with sqlite3.connect(path) as db:
        notes_rows = []
        for id,raw in db.execute("SELECT id,payload_json FROM notes WHERE id IN ('ordinary-project','ordinary-stage') OR json_extract(payload_json,'$.source_type')='mindmap' ORDER BY id"):
            note=json.loads(raw)
            # SQLite revision is a device-local write counter; authority uses
            # immutable event revisions. Timestamp spellings have frozen equivalence.
            note.pop('revision',None)
            for key in ('created_at','updated_at'):
                if note.get(key):note[key]=timestamp(note[key])
            notes_rows.append((id,note))
        docs = db.execute('SELECT id,project_id,stage_id,title,content_json,extensions_json FROM documents ORDER BY id').fetchall()
        tips = db.execute('SELECT owner_key,event_id FROM cloud_game_tips ORDER BY owner_key,event_id').fetchall()
        proof = db.execute('SELECT reward_id,project_action_id,canonical_frame FROM cloud_game_rewards ORDER BY reward_id').fetchall()
        totals = db.execute('SELECT entity_id,snapshot_json FROM cloud_progress_projection ORDER BY entity_id').fetchall()
    return notes_rows, docs, tips, proof, totals, projections(path), map_source(path)['mindmap'], map_source(path,'S1')['mindmap']


def test_complete_content_action_mixed_stream_reopen_conflicts_and_reward_once(cloud_client, tmp_path):
    client, engine = cloud_client; user = str(create_user(engine)); token = login(client).json()['access_token']; headers = _headers(token)
    a, ia = provision(tmp_path,'mixed-A',user,True); b, ib = provision(tmp_path,'mixed-B',user,False)
    devices = ((a,ia),(b,ib)); amk = list(os.urandom(32))
    for path, identity in devices:
        assert client.put(f"/api/v1/sync/devices/{identity['device_id']}",headers=headers).status_code == 200
        document(tmp_path,path,identity,user,'init'); game(tmp_path,path,identity,user,'init')
        support(client,headers,identity['device_id'])
        assert client.put('/api/v3/sync/encrypted/game-reader-capabilities',headers=headers,json=declaration(identity['device_id'])).status_code == 204
    with sqlite3.connect(a) as db:
        register_remote_apply_authorization_guard(db)
        db.execute("UPDATE projects SET payload_json=json_set(payload_json,'$.stages_enabled',json('true'),'$.work_method','app','$.total',0,'$.progress_entries',json('[]'))")
    boot = bootstrap(tmp_path,a,ia,'bootstrap_prepare')['bootstrap_id']
    assert client.post(f'/api/v1/cloud/projects/{PROJECT_ID}/bootstrap',headers=headers,json=dict(bootstrap_id=boot,device_id=ia['device_id'])).status_code == 200
    bootstrap(tmp_path,a,ia,'bootstrap_prepare_capture',bootstrap_id=boot,remote_high_water=0)
    assert client.post(f'/api/v1/cloud/projects/{PROJECT_ID}/bootstrap/complete',headers=headers,json=dict(bootstrap_id=boot,device_id=ia['device_id'],initial_event_count=0,initial_max_server_sequence=0)).status_code == 200
    bootstrap(tmp_path,a,ia,'bootstrap_confirm_active',bootstrap_id=boot,remote_high_water=0)
    assert client.post('/api/v2/sync/encrypted/cutover',headers=headers,json=dict(expected_cutover_epoch=0)).status_code == 200
    for _, identity in devices:
        assert client.post('/api/v3/sync/encrypted/reader-ready',headers=headers,json=dict(device_id=identity['device_id'],reader_transport_version=3)).status_code == 204
    assert client.post('/api/v3/sync/encrypted/cutover',headers=headers,json=dict(expected_cutover_epoch=1)).status_code == 200
    native(tmp_path,a,ia,user,'begin'); meta,_ = publish(client,tmp_path,token,a,ia,user,amk)
    sync(client,tmp_path,token,a,ia,user,amk)
    bootstrap(tmp_path,b,ib,'bootstrap_import',bootstrap_id=boot,remote_high_water=1,display_name=meta['metadata']['name'],authenticated_metadata=meta['metadata'])
    sync(client,tmp_path,token,b,ib,user,amk)
    saved=document(tmp_path,a,ia,user,'save',content=document_text('Private project manuscript'))
    assert 'document_id' in saved,saved
    pdoc=saved['document_id']
    s = event(ia,user,boot,meta['header']['event_id']); stage=s['stage']; stage.update(work_method='app',infinite=True,goal=None)
    with sqlite3.connect(a) as db:
        register_remote_apply_authorization_guard(db)
        db.execute('INSERT INTO stages(id,project_id,name,goal,infinite,unit,status,created_at,payload_json) VALUES(?,?,?,?,?,?,?,?,?)',('S1',PROJECT_ID,stage['name'],None,1,stage['unit'],stage['status'],stage['created_at'],json.dumps({**stage,'total':0,'progress_entries':[]})))
        db.execute('INSERT INTO stage_order VALUES(?,?,0)',('S1',PROJECT_ID))
    structural(tmp_path,a,ia,user,'capture',stage_id='S1'); structural_publish(client,tmp_path,token,a,ia,user,amk,s)
    converge(client,tmp_path,token,devices,user,amk)
    order=event(ia,user,boot,meta['header']['event_id'],order=['S1'],heads={'S1':[s['header']['event_id']]})
    structural_publish(client,tmp_path,token,a,ia,user,amk,order);converge(client,tmp_path,token,devices,user,amk)
    for id, stage_id in (('ordinary-project',None),('ordinary-stage','S1')):
        notes(tmp_path,a,ia,user,'create',note_id=id,stage_id=stage_id,content_format='plain')
        notes(tmp_path,a,ia,user,'edit',note_id=id,stage_id=stage_id,patch=dict(content='Secret '+id))
    fixture=json.loads((ROOT/'frontend/src/cloud/__fixtures__/mapCodecV1.json').read_text())['examples'][2]['event']['map']['data']
    for stage_id in (None,'S1'):
        data=json.loads(json.dumps(fixture).replace('root-1','stage-root' if stage_id else 'root-1').replace('note-1','stage-node' if stage_id else 'note-1'))
        assert change(tmp_path,a,ia,user,stage_id,data) is True
    sdoc=document(tmp_path,a,ia,user,'save',stage_id='S1',content=document_text('Private Stage manuscript'))['document_id']
    # Ordinary saves before consent create no new content authority.
    assert notes(tmp_path,a,ia,user,'pending') == []
    assert maps(tmp_path,a,ia,user,'pending') == []
    assert document(tmp_path,a,ia,user,'pending') == []
    notes(tmp_path,a,ia,user,'begin'); maps(tmp_path,a,ia,user,'begin'); document(tmp_path,a,ia,user,'begin'); progress(tmp_path,a,ia,user,'begin')
    emit_notes(client,tmp_path,token,a,ia,user,amk); emit_maps(client,tmp_path,token,a,ia,user,amk)
    emit_documents(client,tmp_path,token,a,ia,user,amk,lose=True); emit_progress(client,tmp_path,token,a,ia,user,amk)
    converge(client,tmp_path,token,devices,user,amk)
    command(tmp_path,a,ia,user,'begin',now=NOW); emit_game(client,tmp_path,token,a,ia,user,amk,lose=True)
    converge(client,tmp_path,token,devices,user,amk)
    assert portable(a) == portable(b)
    c,ic=provision(tmp_path,'mixed-C',user,False)
    assert client.put(f"/api/v1/sync/devices/{ic['device_id']}",headers=headers).status_code==200
    assert client.post('/api/v3/sync/encrypted/reader-ready',headers=headers,json=dict(device_id=ic['device_id'],reader_transport_version=3)).status_code==204
    # Ordinary mixed change: Note8, Map9, Document10, Progress11, G12/R13,
    # then a safe Stage Note beyond the deliberately withheld Progress proof.
    notes(tmp_path,a,ia,user,'edit',note_id='ordinary-project',patch=dict(content='A changed ordinary Note'))
    frozen_gate(client,tmp_path,token,a,ia,user,amk,ic['device_id'],'note',8)
    with sqlite3.connect(a) as db:
        derived=db.execute("SELECT id FROM notes WHERE json_extract(payload_json,'$.source_type')='mindmap' AND json_extract(payload_json,'$.stage_id') IS NULL").fetchone()[0]
        count=db.execute("SELECT count(*) FROM cloud_sync_outbox WHERE entity_type='note'").fetchone()[0]
    maps(tmp_path,a,ia,user,'note_edit',note_id=derived,patch=dict(content='A map owns this annotation'))
    frozen_gate(client,tmp_path,token,a,ia,user,amk,ic['device_id'],'map',9)
    with sqlite3.connect(a) as db:
        assert db.execute("SELECT count(*) FROM cloud_sync_outbox WHERE entity_type='note'").fetchone()[0] == count
    document(tmp_path,a,ia,user,'save',stage_id='S1',content=document_text('A revised Stage manuscript'),expected=heads(tmp_path,a,ia,user,sdoc))
    frozen_gate(client,tmp_path,token,a,ia,user,amk,ic['device_id'],'document',10)
    result=progress(tmp_path,a,ia,user,'document_progress',stage_id='S1')
    assert result['changed'] is True,result
    assert game(tmp_path,a,ia,user,'process')['processed'] == 1
    frozen_gate(client,tmp_path,token,a,ia,user,amk,ic['device_id'],'progress',11)
    blocked_game=emit_game(client,tmp_path,token,a,ia,user,amk,expected_status=409)
    assert len(blocked_game)==2
    assert {endpoint for endpoint,_ in blocked_game}=={'/api/v3/sync/encrypted/push','/api/v3/sync/encrypted/account/push'}
    frozen=command(tmp_path,a,ia,user,'pending',sealed=True)
    assert client.put('/api/v3/sync/encrypted/game-reader-capabilities',headers=headers,json=declaration(ic['device_id'])).status_code==204
    assert command(tmp_path,a,ia,user,'pending',sealed=True)==frozen
    emit_game(client,tmp_path,token,a,ia,user,amk,lose=True)
    notes(tmp_path,a,ia,user,'edit',note_id='ordinary-stage',stage_id='S1',patch=dict(content='Later safe Stage Note'))
    emit_notes(client,tmp_path,token,a,ia,user,amk)
    page=pull(client,tmp_path,token,b,ib,user)
    seq=min(i['event']['server_sequence'] for i in page['items'] if i['event']['entity_type']=='progress')
    outcomes=apply_all(tmp_path,b,ib,user,amk,hold_progress=True)
    assert any(n>seq and kind=='note' for n,kind,_ in outcomes)
    assert any(kind=='account_game' and outcome=='waiting' for _,kind,outcome in outcomes)
    assert progress(tmp_path,b,ib,user,'ack')['candidate_cursor'] < seq
    with sqlite3.connect(b) as db:
        assert json.loads(db.execute("SELECT payload_json FROM notes WHERE id='ordinary-stage'").fetchone()[0])['content'] == 'Later safe Stage Note'
        assert db.execute('SELECT count(*) FROM cloud_game_rewards').fetchone()[0] == 0
    # No network: retained immutable Progress proof unlocks the same G/R after reopen.
    apply_all(tmp_path,b,ib,user,amk)
    assert progress(tmp_path,b,ib,user,'ack')['candidate_cursor'] == page['next_cursor']
    converge(client,tmp_path,token,devices,user,amk)
    assert portable(a) == portable(b)
    assert progress(tmp_path,b,ib,user,'document_progress',stage_id='S1')['changed'] is False
    assert game(tmp_path,b,ib,user,'process')['processed'] == 0
    # C joins the mixed retained history after its staged reader upgrade.
    document(tmp_path,c,ic,user,'init');game(tmp_path,c,ic,user,'init')
    bootstrap(tmp_path,c,ic,'bootstrap_import',bootstrap_id=boot,remote_high_water=1,
        display_name=meta['metadata']['name'],authenticated_metadata=meta['metadata'])
    converge(client,tmp_path,token,((c,ic),),user,amk)
    assert portable(c)==portable(a)
    # Deleting the derived Note while ordinary Note8 sync is active is also
    # a Map mutation, with no second canonical Note writer/tombstone.
    with sqlite3.connect(a) as db:
        before=db.execute("SELECT count(*) FROM cloud_sync_outbox WHERE entity_type='note'").fetchone()[0]
    assert maps(tmp_path,a,ia,user,'note_delete',note_id=derived) is True
    with sqlite3.connect(a) as db:
        assert db.execute("SELECT count(*) FROM cloud_sync_outbox WHERE entity_type='note'").fetchone()[0]==before
        assert db.execute('SELECT count(*) FROM notes WHERE id=?',(derived,)).fetchone()[0]==0
    emit_maps(client,tmp_path,token,a,ia,user,amk)
    converge(client,tmp_path,token,(*devices,(c,ic)),user,amk)
    assert portable(c)==portable(a)==portable(b)
    # B changes multiple families and continues the same causal histories.
    notes(tmp_path,b,ib,user,'edit',note_id='ordinary-project',patch=dict(content='B continuation'))
    data=map_source(b,'S1')['mindmap'];data['nodeData']['topic']='B Stage map'
    assert change(tmp_path,b,ib,user,'S1',data) is True
    document(tmp_path,b,ib,user,'save',stage_id='S1',content=document_text('B manuscript'),expected=heads(tmp_path,b,ib,user,sdoc))
    emit_notes(client,tmp_path,token,b,ib,user,amk);emit_maps(client,tmp_path,token,b,ib,user,amk);emit_documents(client,tmp_path,token,b,ib,user,amk)
    converge(client,tmp_path,token,devices,user,amk);assert portable(a) == portable(b)
    # Simultaneous independent Note and Map conflicts. Resolving Map cannot
    # erase Note versions or contaminate its tips.
    for path,identity,label in ((a,ia,'A'),(b,ib,'B')):
        notes(tmp_path,path,identity,user,'edit',note_id='ordinary-stage',stage_id='S1',patch=dict(content=label+' Note branch'))
        data=map_source(path,'S1')['mindmap'];data['nodeData']['topic']=label+' Map branch'
        change(tmp_path,path,identity,user,'S1',data)
        emit_notes(client,tmp_path,token,path,identity,user,amk);emit_maps(client,tmp_path,token,path,identity,user,amk)
    converge(client,tmp_path,token,devices,user,amk)
    before=notes(tmp_path,a,ia,user,'conflicts');assert before
    owner=next(o for o in maps(tmp_path,a,ia,user,'view')['owners'] if o['stage_id']=='S1');assert len(owner['tips']) == 2
    maps(tmp_path,a,ia,user,'decide',decision=dict(project_id=PROJECT_ID,stage_id='S1',expected_tips=owner['tips'],expected_local=owner['local'],selected_event_id=owner['tips'][0]))
    emit_maps(client,tmp_path,token,a,ia,user,amk);converge(client,tmp_path,token,devices,user,amk)
    assert notes(tmp_path,a,ia,user,'conflicts') == before
    for path,identity in devices:
        with sqlite3.connect(path) as db:
            assert db.execute('SELECT count(*) FROM cloud_game_rewards').fetchone()[0] == 1
            assert db.execute('PRAGMA foreign_key_check').fetchall() == []
        assert progress(tmp_path,path,identity,user,'ack')['candidate_cursor'] == max(r['event']['server_sequence'] for r in retained(path))
    # Stage deletion is blocked while authenticated child histories exist.
    # Reopen every family before/after the tombstone; no blind cascade occurs.
    from test_cloud_c18_structural_integration import publish_pending
    with sqlite3.connect(a) as db:
        old=json.loads(bytes(db.execute("SELECT e.canonical_frame FROM cloud_sync_structural_tips t JOIN cloud_sync_structural_events e USING(account_id,event_id) WHERE t.entity_type='stage' AND t.entity_id='S1'").fetchone()[0])[20:])
    tombstone=json.loads(json.dumps(old));h=tombstone['header']
    h.update(event_id=str(uuid4()),parent_event_ids=[old['header']['event_id']],revision=h['revision']+1,
        generation=h['generation']+1,operation='delete',updated_at=NOW)
    tombstone.update(stage=None,deleted_at=NOW)
    def child_history(path):
        with sqlite3.connect(path) as db:
            return tuple(db.execute('SELECT count(*) FROM '+table).fetchone()[0] for table in
                ('notes','documents','cloud_content_note_writer_events','cloud_content_note_receipts','cloud_map_events','cloud_document_events','cloud_progress_events','cloud_game_events','cloud_game_rewards'))
    counts={path:child_history(path) for path,_ in devices}
    structural(tmp_path,a,ia,user,'prepare',event=tombstone,expected_tips=h['parent_event_ids'])
    publish_pending(client,tmp_path,token,a,ia,user,amk)
    converge(client,tmp_path,token,devices,user,amk)
    for path,identity in devices:
        assert child_history(path)==counts[path]
        with sqlite3.connect(path) as db:
            assert db.execute('SELECT state FROM cloud_sync_structural_events WHERE event_id=?',(h['event_id'],)).fetchone()[0]=='tombstone_blocked'
            assert db.execute("SELECT count(*) FROM stages WHERE id='S1'").fetchone()[0]==1
        owner=next(o for o in progress(tmp_path,path,identity,user,'view')['owners'] if o['stage_id']=='S1')
        rejected=progress(tmp_path,path,identity,user,'manual',stage_id='S1',expected=owner['tips'],total=60)
        assert rejected['error']=='stage_tombstone_child_manifest_incomplete',rejected
        assert child_history(path)==counts[path]
    with engine.connect() as db:
        types=set(db.execute(text('SELECT DISTINCT entity_type FROM sync_events')).scalars())
        assert {'note','map','document','progress','project_game','account_game','stage','stage_order','project_metadata'} <= types
        columns=set(db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='sync_events'")).scalars())
        assert not columns & {'content','title','node_text','coins','experience','inventory','reward_id','total_symbols','external_path'}
        # No semantic text appears in any serialized routing descriptor.
        descriptors=db.execute(text('SELECT project_id,entity_id,entity_type,operation FROM sync_events')).fetchall()
        assert 'Private' not in repr(descriptors) and 'manuscript' not in repr(descriptors)
