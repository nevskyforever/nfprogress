"""Mandatory real PostgreSQL / C11 TS crypto / two native file-backed SQLite map acceptance."""
from __future__ import annotations
import json, os, sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import pytest
from nfprogress.core.sqlite.connection import register_remote_apply_authorization_guard
from test_cloud_auth import cloud_client, migrated_database, create_user, login
from test_cloud_c18_content_note_gate import capabilities
from test_cloud_c18_map_gate import map_capabilities
from test_cloud_c18_authority_cross_runtime import provision, bootstrap, native, publish, sync
from test_cloud_c18_structural_cross_runtime import event, structural, structural_publish, structural_sync
from test_cloud_c15_headless_cross_runtime import PROJECT_ID, _crypto_bridge, _native_bridge, _headers
ROOT=Path(__file__).resolve().parents[1]
NOW='2026-10-03T00:00:00.000000Z'

def maps(tmp,path,identity,user,step,**values):
    return _native_bridge(tmp,dict(action='map',database_path=str(path),local_account_id=identity['local_account_id'],device_id=identity['device_id'],canonical_user_id=user,project_id=PROJECT_ID,step=step,**values))

def emit(client,tmp,token,path,identity,user,amk,lose=False):
    sent=[]
    for item in maps(tmp,path,identity,user,'pending'):
        h=item['event']['header'];sealed=_crypto_bridge(tmp,dict(action='map_seal',frame=item['frame'],amk=amk))
        maps(tmp,path,identity,user,'seal',event_id=h['event_id'],frame=item['frame'],nonce=sealed['nonce'],ciphertext=sealed['ciphertext'])
        wire={k:h[k] for k in ('event_id','project_id','entity_id','revision','updated_at')};wire.update(entity_type='map',operation='event',deleted_at=None)
        request=dict(protocol_version=3,encrypted_sync_version=3,device_id=identity['device_id'],items=[dict(event=wire,object=sealed['object'])])
        response=client.post('/api/v3/sync/encrypted/push',headers=_headers(token),json=request)
        assert response.status_code==200,response.text
        if lose:
            replay=client.post('/api/v3/sync/encrypted/push',headers=_headers(token),json=request)
            assert replay.status_code==200 and replay.json()['results'][0]['duplicate']
            assert replay.json()['results'][0]['server_sequence']==response.json()['results'][0]['server_sequence']
            frozen=next(x for x in maps(tmp,path,identity,user,'pending',sealed=True) if x['event']['header']['event_id']==h['event_id'])
            assert frozen['frame']==item['frame'] and frozen['nonce']==sealed['nonce'] and frozen['ciphertext']==sealed['ciphertext']
            # No local receipt: authenticated self echo must recover it after reopen.
        else:
            r=response.json()['results'][0];maps(tmp,path,identity,user,'receipt',event_id=h['event_id'],server_sequence=r['server_sequence'],duplicate=r['duplicate'])
        sent.append(request)
    return sent

def receive(client,tmp,token,path,identity,user,amk):
    with sqlite3.connect(path) as db:cursor=db.execute('SELECT pull_cursor FROM cloud_sync_state').fetchone()[0]
    response=client.get('/api/v3/sync/encrypted/pull',headers=_headers(token),params=dict(device_id=identity['device_id'],since=cursor,limit=100,protocol_version=3,encrypted_sync_version=3))
    assert response.status_code==200,response.text
    outcomes=[]
    for item in response.json()['items']:
        if item['event']['entity_type']=='note':
            opened=_crypto_bridge(tmp,dict(action='open',canonical_user_id=user,amk=amk,item=item))
            result=_native_bridge(tmp,dict(action='receive_apply_prepare',database_path=str(path),local_account_id=identity['local_account_id'],device_id=identity['device_id'],canonical_user_id=user,item=item,expected_cursor=cursor,next_cursor=item['event']['server_sequence'],opened=opened))
            outcomes.append(result['apply_result']);cursor=item['event']['server_sequence'];continue
        assert item['event']['entity_type']=='map'
        opened=_crypto_bridge(tmp,dict(action='map_open',canonical_user_id=user,amk=amk,item=item))
        row=dict(item['event']);row['source_device_id']=row.pop('device_id');row['envelope']=item['object']
        row['updated_at']=datetime.fromisoformat(row['updated_at'].replace('Z','+00:00')).astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z')
        command=dict(account_id=identity['local_account_id'],device_id=identity['device_id'],canonical_user_id=user,expected_cursor=cursor,next_cursor=row['server_sequence'],has_more=False,items=[row])
        outcomes.append(maps(tmp,path,identity,user,'receive',command=command,opened=opened));cursor=row['server_sequence']
    return outcomes

def stored(path,stage=None):
    with sqlite3.connect(path) as db:
        raw=db.execute('SELECT payload_json FROM stages WHERE id=?',('S1',)).fetchone()[0] if stage else db.execute('SELECT payload_json FROM projects WHERE id=?',(PROJECT_ID,)).fetchone()[0]
        return json.loads(raw)

def change(tmp,path,identity,user,stage,data,expected=None):
    if expected is None:expected=maps(tmp,path,identity,user,'expected',stage_id=stage)
    return maps(tmp,path,identity,user,'edit',stage_id=stage,data=data,expected=expected)

def decision(owner,selected):
    return dict(project_id=PROJECT_ID,stage_id=owner['stage_id'],expected_tips=owner['tips'],expected_local=owner['local'],selected_event_id=selected)

def test_maps_explicit_migration_annotation_writers_conflicts_two_devices(cloud_client,tmp_path):
    client,engine=cloud_client;user=str(create_user(engine));token=login(client).json()['access_token'];headers=_headers(token)
    a,ia=provision(tmp_path,'notes-A',user,True);b,ib=provision(tmp_path,'notes-B',user,False)
    for identity in (ia,ib):assert client.put(f"/api/v1/sync/devices/{identity['device_id']}",headers=headers).status_code==200
    boot=bootstrap(tmp_path,a,ia,'bootstrap_prepare')['bootstrap_id']
    assert client.post(f'/api/v1/cloud/projects/{PROJECT_ID}/bootstrap',headers=headers,json=dict(bootstrap_id=boot,device_id=ia['device_id'])).status_code==200
    bootstrap(tmp_path,a,ia,'bootstrap_prepare_capture',bootstrap_id=boot,remote_high_water=0)
    assert client.post(f'/api/v1/cloud/projects/{PROJECT_ID}/bootstrap/complete',headers=headers,json=dict(bootstrap_id=boot,device_id=ia['device_id'],initial_event_count=0,initial_max_server_sequence=0)).status_code==200
    bootstrap(tmp_path,a,ia,'bootstrap_confirm_active',bootstrap_id=boot,remote_high_water=0)
    assert client.post('/api/v2/sync/encrypted/cutover',headers=headers,json=dict(expected_cutover_epoch=0)).status_code==200
    for identity in (ia,ib):assert client.post('/api/v3/sync/encrypted/reader-ready',headers=headers,json=dict(device_id=identity['device_id'],reader_transport_version=3)).status_code==204
    assert client.post('/api/v3/sync/encrypted/cutover',headers=headers,json=dict(expected_cutover_epoch=1)).status_code==200
    native(tmp_path,a,ia,user,'begin');amk=list(os.urandom(32));meta,_=publish(client,tmp_path,token,a,ia,user,amk)
    assert sync(client,tmp_path,token,a,ia,user,amk)['view']['state']=='active'
    bootstrap(tmp_path,b,ib,'bootstrap_import',bootstrap_id=boot,remote_high_water=1,display_name=meta['metadata']['name'],authenticated_metadata=meta['metadata'])
    assert sync(client,tmp_path,token,b,ib,user,amk)['view']['state']=='active'
    s=event(ia,user,boot,meta['header']['event_id']);stage=s['stage']
    with sqlite3.connect(a) as db:
        db.execute('INSERT INTO stages(id,project_id,name,goal,infinite,unit,status,created_at,payload_json) VALUES(?,?,?,?,?,?,?,?,?)',('S1',PROJECT_ID,stage['name'],stage['goal'],int(stage['infinite']),stage['unit'],stage['status'],stage['created_at'],json.dumps(stage)))
        db.execute('INSERT INTO stage_order VALUES(?,?,0)',('S1',PROJECT_ID))
    structural(tmp_path,a,ia,user,'capture',stage_id='S1');structural_publish(client,tmp_path,token,a,ia,user,amk,s)
    for path,identity in ((a,ia),(b,ib)):structural_sync(client,tmp_path,token,path,identity,user,amk)
    c=str(uuid4());assert client.put(f'/api/v1/sync/devices/{c}',headers=headers).status_code==200
    for device in (ia['device_id'],ib['device_id'],c):
        assert client.put('/api/v3/sync/encrypted/note-reader-capabilities',headers=headers,json=capabilities(device)).status_code==204
    for identity in (ia,ib):
        assert client.put('/api/v3/sync/encrypted/map-reader-capabilities',headers=headers,json=map_capabilities(identity['device_id'])).status_code==204
    assert client.get('/api/v3/sync/encrypted/map-reader-capabilities',headers=headers).json()==dict(ready=False,missing_devices=1)
    fixture=json.loads((ROOT/'frontend/src/cloud/__fixtures__/mapCodecV1.json').read_text())['examples'][2]['event']['map']
    project_map=fixture['data'];stage_map=json.loads(json.dumps(project_map).replace('root-1','stage-root').replace('note-1','stage-note'))
    assert change(tmp_path,a,ia,user,None,project_map) is True
    assert change(tmp_path,a,ia,user,'S1',stage_map) is True
    assert maps(tmp_path,a,ia,user,'pending')==[] # No implicit admission on ordinary save.
    with sqlite3.connect(a) as db:
        ids=db.execute("SELECT id FROM notes WHERE json_extract(payload_json,'$.source_type')='mindmap'").fetchall()
    note_id=next(i[0] for i in ids if json.loads(sqlite3.connect(a).execute('SELECT payload_json FROM notes WHERE id=?',(i[0],)).fetchone()[0])['stage_id'] is None)
    maps(tmp_path,a,ia,user,'note_edit',note_id=note_id,patch=dict(title='Portable map annotation',tags=['alpha'],checklist=[dict(id='check',text='Portable task',checked=True)],color='coral',pinned=True,archived=True))
    before=stored(a)
    # B has an unrelated preexisting map; remote import must preserve its complete candidate.
    local_b=json.loads(json.dumps(project_map));local_b['nodeData']['topic']='B retained local map'
    assert change(tmp_path,b,ib,user,None,local_b) is True
    view=maps(tmp_path,a,ia,user,'begin');assert len(view['owners'])==2
    frozen=maps(tmp_path,a,ia,user,'pending')
    first=frozen[0];h=first['event']['header'];sealed=_crypto_bridge(tmp_path,dict(action='map_seal',frame=first['frame'],amk=amk))
    wire={k:h[k] for k in ('event_id','project_id','entity_id','revision','updated_at')};wire.update(entity_type='map',operation='event',deleted_at=None)
    blocked=client.post('/api/v3/sync/encrypted/push',headers=headers,json=dict(protocol_version=3,encrypted_sync_version=3,device_id=ia['device_id'],items=[dict(event=wire,object=sealed['object'])]))
    assert blocked.status_code==409 and 'map_readers_not_ready' in blocked.text
    assert client.put('/api/v3/sync/encrypted/map-reader-capabilities',headers=headers,json=map_capabilities(c)).status_code==204
    assert len(emit(client,tmp_path,token,a,ia,user,amk,lose=True))==2
    assert all(o['state']=='self_echo_pending' for o in maps(tmp_path,a,ia,user,'view')['owners'])
    assert receive(client,tmp_path,token,a,ia,user,amk)==['applied','applied']
    assert 'conflict_preserved' in receive(client,tmp_path,token,b,ib,user,amk)
    assert stored(b)['mindmap']['nodeData']['topic']=='B retained local map'
    owner=next(o for o in maps(tmp_path,b,ib,user,'view')['owners'] if o['stage_id'] is None)
    assert owner['state']=='conflict' and len(owner['tips'])==1
    maps(tmp_path,b,ib,user,'import',decision=decision(owner,owner['tips'][0]),keep_local=False)
    with sqlite3.connect(b) as db:
        n=json.loads(db.execute('SELECT payload_json FROM notes WHERE id=?',(note_id,)).fetchone()[0])
        assert n['title']=='Portable map annotation' and n['tags']==['alpha'] and n['pinned'] and n['archived'] and n['checklist'][0]['checked']
        assert db.execute('SELECT COUNT(*) FROM cloud_map_local_candidates').fetchone()[0]==1
    # An ordinary initialized connection cannot gain private remote-apply rights.
    with sqlite3.connect(b) as db:
        register_remote_apply_authorization_guard(db)
        assert db.execute("SELECT note_sync_remote_apply_authorized(?)", ('untrusted',)).fetchone() == (0,)
        original_map = db.execute('SELECT payload_json FROM projects WHERE id=?', (PROJECT_ID,)).fetchone()[0]
        original_note = db.execute('SELECT payload_json FROM notes WHERE id=?', (note_id,)).fetchone()[0]
        with pytest.raises(sqlite3.IntegrityError, match='map_mutation_requires_matching_intent'):
            db.execute("UPDATE projects SET payload_json=json_set(payload_json,'$.mindmap.nodeData.topic','unauthorized') WHERE id=?", (PROJECT_ID,))
        with pytest.raises(sqlite3.IntegrityError, match='derived_note_requires_owning_map_intent'):
            db.execute('DELETE FROM notes WHERE id=?', (note_id,))
        assert db.execute('SELECT payload_json FROM projects WHERE id=?', (PROJECT_ID,)).fetchone()[0] == original_map
        assert db.execute('SELECT payload_json FROM notes WHERE id=?', (note_id,)).fetchone()[0] == original_note
    # Ordinary map and derived Note writers both produce complete maps only.
    old_expected=maps(tmp_path,a,ia,user,'expected',stage_id='S1')
    for path,identity,text in ((a,ia,'A branch'),(b,ib,'B branch')):
        data=stored(path,'S1')['mindmap'];data['nodeData']['topic']=text
        assert change(tmp_path,path,identity,user,'S1',data) is True
        assert len(emit(client,tmp_path,token,path,identity,user,amk))==1
    for path,identity in ((a,ia),(b,ib)):assert 'conflict_preserved' in receive(client,tmp_path,token,path,identity,user,amk)
    assert change(tmp_path,a,ia,user,'S1',stage_map,old_expected)['error']=='map_combined_stale_heads'
    owner=next(o for o in maps(tmp_path,a,ia,user,'view')['owners'] if o['stage_id']=='S1')
    assert len(owner['tips'])==2
    d=decision(owner,owner['tips'][0]);resolution=maps(tmp_path,a,ia,user,'decide',decision=d)
    events=maps(tmp_path,a,ia,user,'pending');r=next(e['event'] for e in events if e['event']['header']['event_id']==resolution)
    assert sorted(r['header']['parents'])==sorted(owner['tips']) and r['header']['revision']==3
    assert len(emit(client,tmp_path,token,a,ia,user,amk))==1
    for path,identity in ((a,ia),(b,ib)):assert receive(client,tmp_path,token,path,identity,user,amk)==['applied']
    assert maps(tmp_path,a,ia,user,'decide',decision=d)['error']=='map_resolution_stale'
    maps(tmp_path,a,ia,user,'note_edit',note_id=note_id,patch=dict(content='Changed via production Note writer',tags=['new'],pinned=False))
    assert len(emit(client,tmp_path,token,a,ia,user,amk))==1
    for path,identity in ((a,ia),(b,ib)):receive(client,tmp_path,token,path,identity,user,amk)
    assert stored(b)['mindmap']['freeNodes'][0]['topic']=='Changed via production Note writer'
    maps(tmp_path,a,ia,user,'note_delete',note_id=note_id)
    assert len(emit(client,tmp_path,token,a,ia,user,amk))==1
    for path,identity in ((a,ia),(b,ib)):
        receive(client,tmp_path,token,path,identity,user,amk)
        with sqlite3.connect(path) as db:
            assert db.execute('SELECT count(*) FROM notes WHERE id=?',(note_id,)).fetchone()[0]==0
            assert db.execute("SELECT count(*) FROM cloud_sync_outbox WHERE entity_type='note'").fetchone()[0]==0
            assert db.execute("SELECT count(*) FROM cloud_sync_inbox WHERE entity_type='note'").fetchone()[0]==0
            assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
        ack=maps(tmp_path,path,identity,user,'ack')
        with sqlite3.connect(path) as db:cursor=db.execute('SELECT pull_cursor FROM cloud_sync_state').fetchone()[0]
        assert ack['candidate_cursor']==cursor
    # Enable combined view through the established metadata production writer.
    proposed=stored(a);proposed.update(combine_stage_mindmaps=True,stages_enabled=True)
    native(tmp_path,a,ia,user,'normal_edit',proposed=proposed)
    publish(client,tmp_path,token,a,ia,user,amk)
    for path,identity in ((a,ia),(b,ib)):sync(client,tmp_path,token,path,identity,user,amk)
    rendered=maps(tmp_path,a,ia,user,'combined');combined=rendered['data'];combined['nodeData']['topic']='Combined project change'
    before_project=stored(a);before_stage=stored(a,'S1')
    with sqlite3.connect(a) as db:
        count=db.execute('SELECT count(*) FROM cloud_sync_outbox').fetchone()[0]
        groups=db.execute('SELECT count(*) FROM cloud_map_combined_groups').fetchone()[0]
        db.execute("CREATE TRIGGER acceptance_crash_last_owner BEFORE UPDATE ON stages BEGIN SELECT RAISE(ABORT,'isolated crash'); END")
    failed=change(tmp_path,a,ia,user,None,combined,rendered['expected']);assert 'error' in failed
    assert stored(a)==before_project and stored(a,'S1')==before_stage
    with sqlite3.connect(a) as db:
        assert db.execute('SELECT count(*) FROM cloud_sync_outbox').fetchone()[0]==count
        assert db.execute('SELECT count(*) FROM cloud_map_combined_groups').fetchone()[0]==groups
        db.execute('DROP TRIGGER acceptance_crash_last_owner')
    assert change(tmp_path,a,ia,user,None,combined,rendered['expected']) is True
    # Both canonical owners are in the same local commit; no combined entity.
    with sqlite3.connect(a) as db:
        assert db.execute('SELECT count(*) FROM cloud_map_combined_groups').fetchone()[0]==groups+1
        assert db.execute("SELECT count(*) FROM cloud_sync_outbox WHERE entity_id='combined-map'").fetchone()[0]==0
    assert len(emit(client,tmp_path,token,a,ia,user,amk))==2
    for path,identity in ((a,ia),(b,ib)):assert receive(client,tmp_path,token,path,identity,user,amk)==['applied','applied']
    assert stored(b)['mindmap']['nodeData']['topic']=='Combined project change'
    assert change(tmp_path,a,ia,user,None,combined,rendered['expected'])['error']=='map_combined_stale_heads'
    # A Stage rename is accepted ancestry, without republishing map history.
    renamed=json.loads(json.dumps(s['stage']));renamed['name']='Renamed Stage'
    rename=event(ia,user,boot,meta['header']['event_id'],parent=s,stage=renamed)
    structural_publish(client,tmp_path,token,a,ia,user,amk,rename)
    for path,identity in ((a,ia),(b,ib)):structural_sync(client,tmp_path,token,path,identity,user,amk)
    # Out-of-order retained Stage ancestry: shared ACK cannot cross a blocked
    # map even when a later independent legacy Note has already applied.
    with sqlite3.connect(a) as db:
        frame=db.execute("SELECT canonical_frame FROM cloud_map_events WHERE stage_id='S1' AND state='applied' ORDER BY revision DESC LIMIT 1").fetchone()[0]
    parent=json.loads(bytes(frame)[20:]);parent['header'].update(event_id=str(uuid4()),parents=[parent['header']['event_id']],revision=parent['header']['revision']+1,generation=parent['header']['generation']+1,operation='update',updated_at=NOW)
    parent['map']['data']['nodeData']['topic']='Missing parent delivered later'
    child=json.loads(json.dumps(parent));child['header'].update(event_id=str(uuid4()),parents=[parent['header']['event_id']],revision=parent['header']['revision']+1,generation=parent['header']['generation']+1)
    child['map']['data']['nodeData']['topic']='Child waits for authenticated parent'
    def push_event(e):
        # JSON serialization must use the production TS canonical codec.
        sealed=_crypto_bridge(tmp_path,dict(action='map_event_seal',payload=e,amk=amk))
        h=e['header'];wire={k:h[k] for k in ('event_id','project_id','entity_id','revision','updated_at')};wire.update(entity_type='map',operation='event',deleted_at=None)
        response=client.post('/api/v3/sync/encrypted/push',headers=headers,json=dict(protocol_version=3,encrypted_sync_version=3,device_id=ia['device_id'],items=[dict(event=wire,object=sealed['object'])]))
        assert response.status_code==200,response.text
        return sealed,response.json()['results'][0]['server_sequence']
    child_opened,blocked_sequence=push_event(child)
    from test_cloud_c18_content_note_acceptance import note
    control=note('independent-control',fmt='html');control.pop('revision');control['updated_at']=NOW
    sealed=_crypto_bridge(tmp_path,dict(action='seal',canonical_user_id=user,device_id=ia['device_id'],event=dict(event_id=str(uuid4()),project_id=PROJECT_ID,entity_id='independent-control',entity_type='note',operation='upsert',revision=1,updated_at=NOW,deleted_at=None),note=control,amk=amk))
    request=sealed['push'];request.update(protocol_version=3,encrypted_sync_version=3)
    assert client.post('/api/v3/sync/encrypted/push',headers=headers,json=request).status_code==200
    push_event(parent)
    for path,identity in ((a,ia),(b,ib)):
        outcomes=receive(client,tmp_path,token,path,identity,user,amk)
        assert outcomes==['waiting','applied','applied']
        assert maps(tmp_path,path,identity,user,'ack')['candidate_cursor']<blocked_sequence
        assert maps(tmp_path,path,identity,user,'apply',opened=child_opened)=='applied'
        with sqlite3.connect(path) as db:cursor=db.execute('SELECT pull_cursor FROM cloud_sync_state').fetchone()[0]
        assert maps(tmp_path,path,identity,user,'ack')['candidate_cursor']==cursor
        assert stored(path,'S1')['mindmap']['nodeData']['topic']=='Child waits for authenticated parent'
