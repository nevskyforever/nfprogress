"""One bounded PostgreSQL + production TS C11 + two file-backed native SQLite run."""
from __future__ import annotations
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from test_cloud_auth import cloud_client, migrated_database, create_user, login
from test_cloud_c18_content_note_gate import capabilities
from test_cloud_c18_authority_cross_runtime import provision, bootstrap, native, publish, sync
from test_cloud_c18_structural_cross_runtime import event, structural, structural_publish, structural_sync
from test_cloud_c15_headless_cross_runtime import PROJECT_ID, _crypto_bridge, _native_bridge, _headers

ROOT = Path(__file__).resolve().parents[1]
NOW = '2026-10-02T00:00:00.000000Z'


def content(tmp,path,identity,user,step,**values):
    return _native_bridge(tmp,dict(action='content_note',database_path=str(path),
        local_account_id=identity['local_account_id'],device_id=identity['device_id'],
        canonical_user_id=user,project_id=PROJECT_ID,step=step,**values))


def note(note_id,stage=None,fmt='plain',source='project'):
    n=json.loads((ROOT/'frontend/src/cloud/__fixtures__/contentNoteCodecV1.json').read_text())['examples'][0]['event']['event']['note']
    n.update(id=note_id,project_id=PROJECT_ID,stage_id=stage,content_format=fmt,source_type=source,revision=0)
    if source=='mindmap':n.update(source_map_id='future-map',source_node_id='future-node')
    return n


def emit(client,tmp,token,path,identity,user,amk,lose=False):
    pending=content(tmp,path,identity,user,'pending')
    sent=[]
    for item in pending:
        opened=json.loads(bytes(item['frame'][20:]));h=opened['event']['header']
        sealed=_crypto_bridge(tmp,dict(action='content_note_seal',frame=item['frame'],amk=amk))
        content(tmp,path,identity,user,'seal',event_id=item['event_id'],frame=item['frame'],envelope=sealed['object'])
        wire={k:h[k] for k in ('event_id','project_id','entity_id','revision','updated_at')}
        wire.update(entity_type='note',operation='event',deleted_at=None)
        request=dict(protocol_version=3,encrypted_sync_version=3,device_id=identity['device_id'],items=[dict(event=wire,object=sealed['object'])])
        response=client.post('/api/v3/sync/encrypted/push',headers=_headers(token),json=request)
        assert response.status_code==200,response.text
        if lose:
            frozen=next(x for x in content(tmp,path,identity,user,'pending',sealed=True) if x['event_id']==item['event_id'])
            assert frozen['frame']==item['frame'] and frozen['nonce']==sealed['nonce'] and frozen['ciphertext']==sealed['ciphertext']
            response2=client.post('/api/v3/sync/encrypted/push',headers=_headers(token),json=request)
            assert response2.json()['results'][0]['duplicate'] is True
            assert response2.json()['results'][0]['server_sequence']==response.json()['results'][0]['server_sequence']
            response=response2;lose=False
        receipt=response.json()['results'][0]
        content(tmp,path,identity,user,'receipt',event_id=item['event_id'],server_sequence=receipt['server_sequence'],duplicate=receipt['duplicate'])
        sent.append(request)
    return sent


def receive(client,tmp,token,path,identity,user,amk):
    with sqlite3.connect(path) as db:cursor=db.execute('SELECT pull_cursor FROM cloud_sync_state').fetchone()[0]
    page=client.get('/api/v3/sync/encrypted/pull',headers=_headers(token),params=dict(device_id=identity['device_id'],since=cursor,protocol_version=3,encrypted_sync_version=3,limit=100))
    assert page.status_code==200,page.text
    outcomes=[]
    for item in page.json()['items']:
        opened=_crypto_bridge(tmp,dict(action='content_note_open',canonical_user_id=user,amk=amk,item=item))
        row=dict(item['event']);row['source_device_id']=row.pop('device_id');row['envelope']=item['object']
        row['updated_at']=datetime.fromisoformat(row['updated_at'].replace('Z','+00:00')).astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z')
        command=dict(account_id=identity['local_account_id'],device_id=identity['device_id'],canonical_user_id=user,expected_cursor=cursor,next_cursor=row['server_sequence'],has_more=False,items=[row])
        outcomes.append(content(tmp,path,identity,user,'receive',command=command,opened=opened));cursor=row['server_sequence']
    return outcomes


def test_stage_plain_explicit_notes_two_devices_and_missing_third_reader(cloud_client,tmp_path):
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
    for identity in (ia,ib):assert client.put('/api/v3/sync/encrypted/note-reader-capabilities',headers=headers,json=capabilities(identity['device_id'])).status_code==204
    c=str(uuid4());assert client.put(f'/api/v1/sync/devices/{c}',headers=headers).status_code==200
    assert client.get('/api/v3/sync/encrypted/note-reader-capabilities',headers=headers).json()==dict(ready=False,missing_devices=1)
    assert client.put('/api/v3/sync/encrypted/note-reader-capabilities',headers=headers,json=capabilities(c)).status_code==204
    # Real retained legacy v1 object; no codec8 duplicate genesis on migration.
    h=note('H1',fmt='html');h.pop('revision')
    legacy=_crypto_bridge(tmp_path,dict(action='seal',canonical_user_id=user,device_id=ia['device_id'],event=dict(event_id=str(uuid4()),project_id=PROJECT_ID,entity_id='H1',entity_type='note',operation='upsert',revision=1,updated_at=NOW,deleted_at=None),note=h,amk=amk))
    request=legacy['push'];request.update(protocol_version=2,encrypted_sync_version=2)
    assert client.post('/api/v2/sync/encrypted/push',headers=headers,json=request).status_code==200
    for path,identity in ((a,ia),(b,ib)):
        item=client.get('/api/v3/sync/encrypted/pull',headers=headers,params=dict(device_id=identity['device_id'],since=2,protocol_version=3,encrypted_sync_version=3)).json()['items'][0]
        opened=_crypto_bridge(tmp_path,dict(action='open',canonical_user_id=user,amk=amk,item=item))
        result=_native_bridge(tmp_path,dict(action='receive_apply_prepare',database_path=str(path),local_account_id=identity['local_account_id'],device_id=identity['device_id'],canonical_user_id=user,item=item,expected_cursor=2,next_cursor=3,opened=opened))
        assert result['apply_result']=='applied'
    with sqlite3.connect(a) as db:
        db.create_function('note_sync_remote_apply_authorized',1,lambda _:0)
        for n in (note('P1'),note('S1-note','S1'),note('S2-note','S1','html'),note('M1',source='mindmap')):
            db.execute('INSERT INTO notes(id,project_id,stage_id,updated_at,payload_json) VALUES(?,?,?,?,?)',(n['id'],PROJECT_ID,n['stage_id'],NOW,json.dumps(n)))
    local_b=note('P1');local_b['content']='Unauthenticated local candidate on B'
    with sqlite3.connect(b) as db:
        db.create_function('note_sync_remote_apply_authorized',1,lambda _:0)
        db.execute('INSERT INTO notes(id,project_id,stage_id,updated_at,payload_json) VALUES(?,?,?,?,?)',('P1',PROJECT_ID,None,NOW,json.dumps(local_b)))
    assert content(tmp_path,a,ia,user,'view')['state']=='content_local'
    assert content(tmp_path,a,ia,user,'begin')['state']=='publication_pending'
    requests=emit(client,tmp_path,token,a,ia,user,amk,lose=True)
    assert len(requests)==3
    assert content(tmp_path,a,ia,user,'view')['state']=='published_self_echo_pending'
    for path,identity in ((a,ia),(b,ib)):assert len(receive(client,tmp_path,token,path,identity,user,amk))==3
    groups=content(tmp_path,b,ib,user,'conflicts')
    assert len(groups)==1 and groups[0]['kind']=='import'
    with sqlite3.connect(b) as db:
        assert json.loads(db.execute("SELECT payload_json FROM notes WHERE id='P1'").fetchone()[0])['content']==local_b['content']
        assert db.execute("SELECT COUNT(*) FROM cloud_content_note_local_candidates").fetchone()[0]==1
    # A preserved, blocked genesis prevents ACK from crossing this prefix.
    assert content(tmp_path,b,ib,user,'ack')['candidate_cursor']<6
    assert content(tmp_path,b,ib,user,'import_choice',decision=groups[0],selected='local',now=NOW)=='applied'
    assert len(emit(client,tmp_path,token,b,ib,user,amk))==1
    for path,identity in ((a,ia),(b,ib)):receive(client,tmp_path,token,path,identity,user,amk)
    assert content(tmp_path,a,ia,user,'view')['state']=='active'
    with sqlite3.connect(a) as db:
        assert db.execute("SELECT COUNT(*) FROM cloud_sync_outbox WHERE entity_id IN ('H1','M1')").fetchone()[0]==0
        assert db.execute("SELECT COUNT(*) FROM notes WHERE id='M1'").fetchone()[0]==1
    with sqlite3.connect(b) as db:
        assert db.execute('SELECT id,stage_id FROM notes ORDER BY id').fetchall()==[('H1',None),('P1',None),('S1-note','S1'),('S2-note','S1')]
    # Ordinary production creation and metadata edits after activation.
    for note_id,stage_id,fmt in (('P2',None,'plain'),('S3','S1','plain'),('S4','S1','html')):
        content(tmp_path,a,ia,user,'create',note_id=note_id,stage_id=stage_id,content_format=fmt)
    assert len(emit(client,tmp_path,token,a,ia,user,amk))==3
    for path,identity in ((a,ia),(b,ib)):receive(client,tmp_path,token,path,identity,user,amk)
    content(tmp_path,a,ia,user,'edit',note_id='P2',patch=dict(title='Portable title',tags=['tag'],checklist=[dict(id='item',text='Check',checked=True)],color='coral',pinned=True,archived=True))
    assert len(emit(client,tmp_path,token,a,ia,user,amk))==1
    for path,identity in ((a,ia),(b,ib)):receive(client,tmp_path,token,path,identity,user,amk)
    with sqlite3.connect(b) as db:
        changed=json.loads(db.execute("SELECT payload_json FROM notes WHERE id='P2'").fetchone()[0])
        assert changed['title']=='Portable title' and changed['pinned'] and changed['archived'] and changed['tags']==['tag']
    content(tmp_path,a,ia,user,'delete',note_id='S4',stage_id='S1')
    assert len(emit(client,tmp_path,token,a,ia,user,amk))==1
    for path,identity in ((a,ia),(b,ib)):
        receive(client,tmp_path,token,path,identity,user,amk)
        with sqlite3.connect(path) as db:assert db.execute("SELECT COUNT(*) FROM notes WHERE id='S4'").fetchone()[0]==0
    for path,identity,text in ((a,ia,'A concurrent edit'),(b,ib,'B concurrent edit')):
        content(tmp_path,path,identity,user,'edit',note_id='S1-note',stage_id='S1',patch=dict(content=text))
        assert len(emit(client,tmp_path,token,path,identity,user,amk))==1
    for path,identity in ((a,ia),(b,ib)):
        receive(client,tmp_path,token,path,identity,user,amk)
        with sqlite3.connect(path) as db:assert db.execute("SELECT COUNT(*) FROM cloud_sync_note_conflict_groups WHERE entity_id='S1-note' AND lifecycle='open'").fetchone()[0]==1

    decision=content(tmp_path,a,ia,user,'conflicts')[0]
    selected=decision['versions'][0]['event_id']
    # A later C branch invalidates the rendered A/B decision and joins all tips.
    with sqlite3.connect(a) as db:
        frame=bytes(db.execute("SELECT canonical_frame FROM cloud_content_note_writer_events WHERE event_id=?",(selected,)).fetchone()[0]) if db.execute("SELECT 1 FROM cloud_content_note_writer_events WHERE event_id=?",(selected,)).fetchone() else bytes(db.execute("SELECT canonical_frame FROM cloud_content_note_receipts WHERE event_id=?",(selected,)).fetchone()[0])
    later=json.loads(frame[20:]);later['device_id']=c
    later['event']['header']['event_id']=str(uuid4());later['event']['header']['updated_at']=NOW
    later['event']['note']['content']='Later C branch';later['event']['note']['updated_at']=NOW
    raw=json.dumps(later,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
    frame=list(b'WORTA-C1'+bytes([1,8,1,0])+len(raw).to_bytes(4,'big')*2+raw)
    sealed=_crypto_bridge(tmp_path,dict(action='content_note_seal',frame=frame,amk=amk))
    h=later['event']['header'];wire={k:h[k] for k in ('event_id','project_id','entity_id','revision','updated_at')}
    wire.update(entity_type='note',operation='event',deleted_at=None)
    response=client.post('/api/v3/sync/encrypted/push',headers=headers,json=dict(protocol_version=3,encrypted_sync_version=3,device_id=c,items=[dict(event=wire,object=sealed['object'])]))
    assert response.status_code==200,response.text
    for path,identity in ((a,ia),(b,ib)):receive(client,tmp_path,token,path,identity,user,amk)
    assert content(tmp_path,a,ia,user,'choose',decision=decision,selected=selected,now=NOW)==dict(error='stale_note_resolution')
    decision=content(tmp_path,a,ia,user,'conflicts')[0];assert len(decision['versions'])==3
    selected=decision['versions'][0]['event_id']
    stale=dict(decision,generation=decision['generation']-1)
    assert content(tmp_path,a,ia,user,'choose',decision=stale,selected=selected,now=NOW)==dict(error='stale_note_resolution')
    assert content(tmp_path,a,ia,user,'choose',decision=decision,selected=selected,now=NOW)=='Applied'
    assert len(emit(client,tmp_path,token,a,ia,user,amk))==1
    for path,identity in ((a,ia),(b,ib)):
        receive(client,tmp_path,token,path,identity,user,amk)
        assert content(tmp_path,path,identity,user,'conflicts')==[]
    # Delete/edit is another full-tip decision and never an automatic deletion.
    content(tmp_path,a,ia,user,'delete',note_id='P1')
    content(tmp_path,b,ib,user,'edit',note_id='P1',patch=dict(content='Keep this edited version'))
    for path,identity in ((a,ia),(b,ib)):assert len(emit(client,tmp_path,token,path,identity,user,amk))==1
    for path,identity in ((a,ia),(b,ib)):
        receive(client,tmp_path,token,path,identity,user,amk)
        groups=content(tmp_path,path,identity,user,'conflicts')
        assert len(groups)==1
        assert {v['operation'] for v in groups[0]['versions']}=={'upsert','delete'}
    decision=content(tmp_path,b,ib,user,'conflicts')[0]
    selected=next(v['event_id'] for v in decision['versions'] if v['operation']=='upsert')
    assert content(tmp_path,b,ib,user,'choose',decision=decision,selected=selected,now=NOW)=='Applied'
    assert len(emit(client,tmp_path,token,b,ib,user,amk))==1
    for path,identity in ((a,ia),(b,ib)):
        receive(client,tmp_path,token,path,identity,user,amk)
        assert content(tmp_path,path,identity,user,'conflicts')==[]
        assert content(tmp_path,path,identity,user,'view')['state']=='active'
        with sqlite3.connect(path) as db:
            assert json.loads(db.execute("SELECT payload_json FROM notes WHERE id='P1'").fetchone()[0])['content']=='Keep this edited version'
        ack=content(tmp_path,path,identity,user,'ack')
        with sqlite3.connect(path) as db:high=db.execute('SELECT pull_cursor FROM cloud_sync_state').fetchone()[0]
        assert ack['candidate_cursor']==high
        assert client.post('/api/v3/sync/encrypted/ack',headers=headers,json=dict(protocol_version=3,encrypted_sync_version=3,device_id=identity['device_id'],cursor=high)).status_code==204
        _native_bridge(tmp_path,dict(action='commit_ack',project_id=PROJECT_ID,database_path=str(path),local_account_id=identity['local_account_id'],device_id=identity['device_id'],canonical_user_id=user,expected_old_ack_cursor=ack['current_ack_cursor'],acknowledged_cursor=high))
        with sqlite3.connect(path) as db:assert db.execute('SELECT ack_cursor FROM cloud_sync_state').fetchone()[0]==high
