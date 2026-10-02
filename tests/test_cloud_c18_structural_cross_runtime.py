"""Bounded production TS crypto -> PostgreSQL -> file-backed native structural apply."""
from __future__ import annotations
import json
import os
import sqlite3
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from test_cloud_auth import cloud_client, create_user, login, migrated_database
from test_cloud_c15_headless_cross_runtime import PROJECT_ID, _crypto_bridge, _native_bridge, _headers
from test_cloud_c18_authority_cross_runtime import provision, bootstrap, native, publish, sync

ROOT=Path(__file__).resolve().parents[1]

def structural(tmp,path,identity,user,step,**values):
    project_id = values.pop('project_id', PROJECT_ID)
    return _native_bridge(tmp,dict(action='structural',database_path=str(path),
        local_account_id=identity['local_account_id'],device_id=identity['device_id'],
        canonical_user_id=user,project_id=project_id,step=step,**values))


def event(identity,user,boot,meta,entity='S1',parent=None,stage=None,order=None,heads=None):
    source=json.loads((ROOT/'frontend/src/cloud/__fixtures__/stageCodecV1.json').read_text())['event']
    h=source['header'];h.update(account_id=user,project_id=PROJECT_ID,bootstrap_id=boot,
        device_id=identity['device_id'],entity_id=entity,event_id=str(uuid4()),metadata_event_id=meta)
    if parent:h.update(operation='update',parent_event_ids=[parent['header']['event_id']],revision=parent['header']['revision']+1,generation=parent['header']['generation']+1)
    if order is not None:
        h['entity_type']='stage_order';h['entity_id']='stage_order';source.update(stage=None,stage_ids=order,stage_heads=heads)
    elif stage is not None:source['stage']=stage
    return source


def structural_publish(client,tmp,token,path,identity,user,amk,e):
    frame=structural(tmp,path,identity,user,'prepare',event=e,expected_tips=e['header']['parent_event_ids'])
    assert structural(tmp,path,identity,user,'prepare',event=e,expected_tips=e['header']['parent_event_ids'])==frame
    sealed=_crypto_bridge(tmp,dict(action='structural_seal',payload=e,amk=amk))
    assert sealed['frame']==frame  # full cross-runtime deterministic frame equality
    structural(tmp,path,identity,user,'seal',event_id=e['header']['event_id'],frame=frame,nonce=sealed['nonce'],ciphertext=sealed['ciphertext'])
    h=e['header'];wire={k:h[k] for k in ('event_id','project_id','entity_id','entity_type','revision','updated_at')};wire.update(operation='upsert',deleted_at=None)
    request=dict(protocol_version=3,encrypted_sync_version=3,device_id=identity['device_id'],items=[dict(event=wire,object=sealed['object'])])
    response=client.post('/api/v3/sync/encrypted/push',headers=_headers(token),json=request);assert response.status_code==200,response.text
    replay=client.post('/api/v3/sync/encrypted/push',headers=_headers(token),json=request);assert replay.status_code==200 and replay.json()['results'][0]['duplicate']
    return request


def structural_sync(client,tmp,token,path,identity,user,amk):
    with sqlite3.connect(path) as db:cursor=db.execute('SELECT pull_cursor FROM cloud_sync_state').fetchone()[0]
    response=client.get('/api/v3/sync/encrypted/pull',headers=_headers(token),params=dict(device_id=identity['device_id'],since=cursor,limit=100,protocol_version=3,encrypted_sync_version=3))
    assert response.status_code==200,response.text
    for item in response.json()['items']:
        opened=_crypto_bridge(tmp,dict(action='structural_open',canonical_user_id=user,amk=amk,item=item))
        row=dict(item['event']);row['source_device_id']=row.pop('device_id');row['envelope']=item['object']
        row['updated_at']=datetime.fromisoformat(row['updated_at'].replace('Z','+00:00')).astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z')
        cmd=dict(account_id=identity['local_account_id'],device_id=identity['device_id'],canonical_user_id=user,expected_cursor=cursor,next_cursor=row['server_sequence'],has_more=False,items=[row])
        structural(tmp,path,identity,user,'receive',command=cmd,opened=opened);cursor=row['server_sequence']
    return structural(tmp,path,identity,user,'read')


def test_structural_multidevice_conflicts_order_and_restart(cloud_client,tmp_path):
    client,engine=cloud_client;user=str(create_user(engine));token=login(client).json()['access_token'];headers=_headers(token)
    a,ia=provision(tmp_path,'A',user,True);b,ib=provision(tmp_path,'B',user,False)
    for identity in (ia,ib):assert client.put(f"/api/v1/sync/devices/{identity['device_id']}",headers=headers).status_code==200
    boot=bootstrap(tmp_path,a,ia,'bootstrap_prepare')['bootstrap_id']
    assert client.post(f'/api/v1/cloud/projects/{PROJECT_ID}/bootstrap',headers=headers,json=dict(bootstrap_id=boot,device_id=ia['device_id'])).status_code==200
    bootstrap(tmp_path,a,ia,'bootstrap_prepare_capture',bootstrap_id=boot,remote_high_water=0)
    assert client.post(f'/api/v1/cloud/projects/{PROJECT_ID}/bootstrap/complete',headers=headers,json=dict(bootstrap_id=boot,device_id=ia['device_id'],initial_event_count=0,initial_max_server_sequence=0)).status_code==200
    bootstrap(tmp_path,a,ia,'bootstrap_confirm_active',bootstrap_id=boot,remote_high_water=0)
    assert client.post('/api/v2/sync/encrypted/cutover',headers=headers,json=dict(expected_cutover_epoch=0)).status_code==200
    for identity in (ia,ib):assert client.post('/api/v3/sync/encrypted/reader-ready',headers=headers,json=dict(device_id=identity['device_id'],reader_transport_version=3)).status_code==204
    assert client.post('/api/v3/sync/encrypted/cutover',headers=headers,json=dict(expected_cutover_epoch=1)).status_code==200
    native(tmp_path,a,ia,user,'begin');amk=list(os.urandom(32));genesis,_=publish(client,tmp_path,token,a,ia,user,amk)
    assert sync(client,tmp_path,token,a,ia,user,amk)['view']['state']=='active'
    bootstrap(tmp_path,b,ib,'bootstrap_import',bootstrap_id=boot,remote_high_water=1,display_name=genesis['metadata']['name'],authenticated_metadata=genesis['metadata'])
    assert sync(client,tmp_path,token,b,ib,user,amk)['view']['state']=='active'
    meta=genesis['header']['event_id'];stages=[]
    for i in (1,2):
        e=event(ia,user,boot,meta,entity=f'S{i}');stages.append(e);s=e['stage']
        with sqlite3.connect(a) as db:
            db.execute('INSERT INTO stages(id,project_id,name,goal,infinite,unit,status,created_at,payload_json) VALUES(?,?,?,?,?,?,?,?,?)',(f'S{i}',PROJECT_ID,s['name'],s['goal'],int(s['infinite']),s['unit'],s['status'],s['created_at'],json.dumps(s)))
            db.execute('INSERT INTO stage_order VALUES(?,?,?)',(f'S{i}',PROJECT_ID,i-1))
        cid=structural(tmp_path,a,ia,user,'capture',stage_id=f'S{i}')
        assert structural(tmp_path,a,ia,user,'capture',stage_id=f'S{i}')==cid
        structural_publish(client,tmp_path,token,a,ia,user,amk,e)
    for path,identity in ((a,ia),(b,ib)):structural_sync(client,tmp_path,token,path,identity,user,amk)
    heads={e['header']['entity_id']:[e['header']['event_id']] for e in stages}
    base=event(ia,user,boot,meta,order=['S1','S2'],heads=heads);structural_publish(client,tmp_path,token,a,ia,user,amk,base)
    for path,identity in ((a,ia),(b,ib)):
        structural_sync(client,tmp_path,token,path,identity,user,amk)
        with sqlite3.connect(path) as db:assert db.execute('SELECT stage_id FROM stage_order ORDER BY position').fetchall()==[('S1',),('S2',)]
    edits=[]
    for path,identity,name in ((a,ia,'Stage Beta'),(b,ib,'Stage Gamma')):
        payload=deepcopy(stages[0]['stage']);payload['name']=name
        edit=event(identity,user,boot,meta,parent=stages[0],stage=payload);edits.append(edit)
        structural_publish(client,tmp_path,token,path,identity,user,amk,edit)
    for path,identity in ((a,ia),(b,ib)):structural_sync(client,tmp_path,token,path,identity,user,amk)
    heads['S1']=sorted(e['header']['event_id'] for e in edits)
    # With two stages both devices can independently emit the same changed
    # permutation; distinct concurrent full-unit events still require a conflict.
    orders=[]
    for path,identity in ((a,ia),(b,ib)):
        reorder=event(identity,user,boot,meta,parent=base,order=['S2','S1'],heads=heads);orders.append(reorder)
        structural_publish(client,tmp_path,token,path,identity,user,amk,reorder)
    for path,identity in ((a,ia),(b,ib)):
        structural_sync(client,tmp_path,token,path,identity,user,amk)
        ack=structural(tmp_path,path,identity,user,'ack')
        assert ack['candidate_cursor']==8
        assert client.post('/api/v3/sync/encrypted/ack',headers=headers,json=dict(protocol_version=3,encrypted_sync_version=3,device_id=identity['device_id'],cursor=8)).status_code==204
        _native_bridge(tmp_path,dict(action='commit_ack',project_id=PROJECT_ID,database_path=str(path),local_account_id=identity['local_account_id'],device_id=identity['device_id'],canonical_user_id=user,expected_old_ack_cursor=0,acknowledged_cursor=8))
        first=structural(tmp_path,path,identity,user,'read');assert structural(tmp_path,path,identity,user,'read')==first
        with sqlite3.connect(path) as db:
            for kind,entity,branches in [('stage','S1',edits),('stage_order','stage_order',orders)]:
                tips={r[0] for r in db.execute('SELECT event_id FROM cloud_sync_structural_tips WHERE entity_type=? AND entity_id=?',(kind,entity))}
                assert tips=={e['header']['event_id'] for e in branches}
                frames=[json.loads(bytes(r[0])[20:]) for r in db.execute('SELECT canonical_frame FROM cloud_sync_structural_events WHERE event_id IN (?,?)',tuple(tips))]
                assert len(frames)==2
                assert db.execute('SELECT count(*) FROM cloud_sync_structural_projection WHERE entity_type=? AND entity_id=?',(kind,entity)).fetchone()[0]==0
            assert db.execute('SELECT count(*) FROM cloud_sync_structural_apply_ledger').fetchone()[0]==7
            assert db.execute('SELECT ack_cursor FROM cloud_sync_state').fetchone()[0]==8
            assert db.execute('SELECT count(*) FROM stages').fetchone()[0]==2
            assert db.execute('SELECT count(*) FROM notes').fetchone()[0]==0
