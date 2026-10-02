"""One bounded production structural integration proof across real PostgreSQL and reopened SQLite devices."""
from __future__ import annotations
import os
import sqlite3
from copy import deepcopy
from datetime import datetime, timezone
from test_cloud_auth import cloud_client, migrated_database, create_user, login
from test_cloud_c15_headless_cross_runtime import PROJECT_ID, _crypto_bridge, _headers
from test_cloud_c18_authority_cross_runtime import provision, bootstrap, native, publish, sync
from test_cloud_c18_structural_cross_runtime import structural, event


def publish_pending(client,tmp,token,path,identity,user,amk,lose_response=False,project_id=PROJECT_ID):
    def scoped(step, **values):
        return structural(tmp,path,identity,user,step,project_id=project_id,**values)
    for pending in scoped('pending'):
        e=pending['event'];h=e['header']
        sealed=_crypto_bridge(tmp,dict(action='structural_seal',payload=e,amk=amk))
        scoped('seal',event_id=h['event_id'],frame=sealed['frame'],nonce=sealed['nonce'],ciphertext=sealed['ciphertext'])
    pending=scoped('pending',sealed=True)
    for row in pending:
        e=row['event'];h=e['header']
        # Production sealed list survives native process restart and exact replay.
        assert row in scoped('pending',sealed=True)
        import base64
        b64=lambda value:base64.urlsafe_b64encode(bytes(value)).decode().rstrip('=')
        wire={k:h[k] for k in ('event_id','project_id','entity_id','entity_type','revision','updated_at')}
        wire.update(operation='delete' if h['operation']=='delete' else 'upsert',deleted_at=e['deleted_at'])
        body=dict(protocol_version=3,encrypted_sync_version=3,device_id=identity['device_id'],items=[dict(event=wire,object=dict(crypto_version=1,aad_version=1,nonce=b64(row['nonce']),ciphertext=b64(row['ciphertext'])))])
        response=client.post('/api/v3/sync/encrypted/push',headers=_headers(token),json=body);assert response.status_code==200,response.text
        if lose_response:
            # Server persisted the object; local receipt is deliberately absent.
            replay=client.post('/api/v3/sync/encrypted/push',headers=_headers(token),json=body);assert replay.status_code==200 and replay.json()['results'][0]['duplicate']
            assert row in scoped('pending',sealed=True)
            receipt=replay.json()['results'][0]
        else:receipt=response.json()['results'][0]
        scoped('receipt',event_id=h['event_id'],server_sequence=receipt['server_sequence'],duplicate=receipt['duplicate'])
    return [row['event'] for row in pending]


def pull_structure(client,tmp,token,path,identity,user,amk):
    with sqlite3.connect(path) as db:cursor=db.execute('SELECT pull_cursor FROM cloud_sync_state').fetchone()[0]
    response=client.get('/api/v3/sync/encrypted/pull',headers=_headers(token),params=dict(device_id=identity['device_id'],since=cursor,limit=100,protocol_version=3,encrypted_sync_version=3));assert response.status_code==200,response.text
    page=response.json();rows=[]
    for item in page['items']:
        row=dict(item['event']);row['source_device_id']=row.pop('device_id');row['envelope']=item['object']
        for key in ('updated_at','deleted_at'):
            if row[key] is not None:row[key]=datetime.fromisoformat(row[key].replace('Z','+00:00')).astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z')
        rows.append(row)
    structural(tmp,path,identity,user,'persist',command=dict(account_id=identity['local_account_id'],device_id=identity['device_id'],canonical_user_id=user,expected_cursor=cursor,next_cursor=page['next_cursor'],has_more=page['has_more'],items=rows))
    # Every arrival is persisted with its ciphertext before decrypt/apply; each
    # bridge invocation reopens the file-backed database in a separate process.
    for item in page['items']:
        opened=_crypto_bridge(tmp,dict(action='structural_open',canonical_user_id=user,amk=amk,item=item))
        structural(tmp,path,identity,user,'apply',event_id=item['event']['event_id'],opened=opened)
    structural(tmp,path,identity,user,'retry')
    structural(tmp,path,identity,user,'advance')
    return structural(tmp,path,identity,user,'authority')


def resolve(tmp,path,identity,user,entity_type,entity_id,select):
    view=structural(tmp,path,identity,user,'authority')
    entity=next(e for e in view['entities'] if e['entity_type']==entity_type and e['entity_id']==entity_id)
    return structural(tmp,path,identity,user,'decide',decision=dict(entity_type=entity_type,entity_id=entity_id,expected_tips=sorted(entity['tips']),expected_local=entity['local'],selected_event_id=select,proposed=None))


def test_explicit_structural_integration_two_devices_and_conflict_decisions(cloud_client,tmp_path):
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

    stages=[]
    for i in (1,2):
        e=event(ia,user,boot,genesis['header']['event_id'],entity=f'S{i}');stages.append(e);s=e['stage']
        with sqlite3.connect(a) as db:
            db.execute('INSERT INTO stages(id,project_id,name,goal,infinite,unit,status,created_at,payload_json) VALUES(?,?,?,?,?,?,?,?,?)',(f'S{i}',PROJECT_ID,s['name'],s['goal'],int(s['infinite']),s['unit'],s['status'],s['created_at'],__import__('json').dumps(s)))
            db.execute('INSERT INTO stage_order VALUES(?,?,?)',(f'S{i}',PROJECT_ID,i-1))
    assert structural(tmp_path,a,ia,user,'authority')['state']=='structural_local'
    begun=structural(tmp_path,a,ia,user,'begin')
    assert structural(tmp_path,a,ia,user,'begin')['migration_id']==begun['migration_id']
    migrated=publish_pending(client,tmp_path,token,a,ia,user,amk,True)
    assert len(migrated)==2 and all(e['header']['entity_type']=='stage' for e in migrated)
    for path,identity in ((a,ia),(b,ib)):pull_structure(client,tmp_path,token,path,identity,user,amk)
    order=publish_pending(client,tmp_path,token,a,ia,user,amk)[0]
    assert order['stage_ids']==['S1','S2']
    for path,identity in ((a,ia),(b,ib)):assert pull_structure(client,tmp_path,token,path,identity,user,amk)['state']=='active'
    edits=[]
    for path,identity,name in ((a,ia,'Stage Beta'),(b,ib,'Stage Gamma')):
        proposed=deepcopy(stages[0]['stage']);proposed['name']=name
        assert structural(tmp_path,path,identity,user,'edit',stage_id='S1',proposed=proposed)
        edits+=publish_pending(client,tmp_path,token,path,identity,user,amk)
    for path,identity in ((a,ia),(b,ib)):assert pull_structure(client,tmp_path,token,path,identity,user,amk)['state']=='conflict'
    r=resolve(tmp_path,a,ia,user,'stage','S1',edits[0]['header']['event_id'])
    resolution=publish_pending(client,tmp_path,token,a,ia,user,amk)[0]
    assert resolution['version']==2 and resolution['header']['event_id']==r
    assert resolution['header']['parent_event_ids']==sorted(e['header']['event_id'] for e in edits)
    for path,identity in ((a,ia),(b,ib)):
        assert pull_structure(client,tmp_path,token,path,identity,user,amk)['state']=='active'
        with sqlite3.connect(path) as db:assert db.execute("SELECT name FROM stages WHERE id='S1'").fetchone()[0]=='Stage Beta'
    orders=[]
    for path,identity,ids in ((a,ia,['S2','S1']),(b,ib,['S1','S2'])):
        assert structural(tmp_path,path,identity,user,'order',stage_ids=ids)
        orders+=publish_pending(client,tmp_path,token,path,identity,user,amk)
    for path,identity in ((a,ia),(b,ib)):assert pull_structure(client,tmp_path,token,path,identity,user,amk)['state']=='conflict'
    resolve(tmp_path,a,ia,user,'stage_order','stage_order',orders[0]['header']['event_id'])
    publish_pending(client,tmp_path,token,a,ia,user,amk)
    for path,identity in ((a,ia),(b,ib)):
        assert pull_structure(client,tmp_path,token,path,identity,user,amk)['state']=='active'
        with sqlite3.connect(path) as db:
            assert db.execute('SELECT stage_id FROM stage_order ORDER BY position').fetchall()==[('S2',),('S1',)]
            assert db.execute('SELECT count(*) FROM stages').fetchone()[0]==2
            assert db.execute('SELECT count(*) FROM notes').fetchone()[0]==0
        ack=structural(tmp_path,path,identity,user,'ack');assert ack['candidate_cursor']==10
        assert client.post('/api/v3/sync/encrypted/ack',headers=headers,json=dict(protocol_version=3,encrypted_sync_version=3,device_id=identity['device_id'],cursor=10)).status_code==204
