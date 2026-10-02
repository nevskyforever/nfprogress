"""One bounded real PG / production TS v2 / two file-backed native device proof."""
from __future__ import annotations
import base64
import json
import os
import sqlite3
from datetime import datetime, timezone
from test_cloud_auth import cloud_client, create_user, login, migrated_database
from test_cloud_c15_headless_cross_runtime import _crypto_bridge, _native_bridge, _headers
from test_cloud_c18_authority_cross_runtime import provision

NOW = '2026-10-02T00:00:00.000000Z'


def native(tmp, path, identity, user, action='catalog', step='authority', **values):
    return _native_bridge(tmp, dict(action=action, step=step, database_path=str(path),
        local_account_id=identity['local_account_id'], device_id=identity['device_id'],
        canonical_user_id=user, **values))


def push(tmp, client, token, path, identity, user, amk, lost=False):
    ready = native(tmp, path, identity, user, step='pending', sealed=False)
    for row in ready:
        e = row['event']; sealed = _crypto_bridge(tmp, dict(action='catalog_seal', payload=e, amk=amk))
        native(tmp, path, identity, user, step='seal', event_id=e['header']['event_id'],
            **{k:sealed[k] for k in ('frame','nonce','ciphertext')})
    rows = native(tmp, path, identity, user, step='pending', sealed=True)
    for row in rows:
        e = row['event']; h = e['header']
        wire = {k:h[k] for k in ('event_id','entity_id','entity_type','revision','updated_at')}
        wire.update(canonical_user_id=user, scope='account', operation='delete' if e['deleted_at'] else 'upsert', deleted_at=e['deleted_at'])
        b64 = lambda b: base64.urlsafe_b64encode(bytes(b)).decode().rstrip('=')
        body = dict(protocol_version=3, encrypted_sync_version=3, device_id=identity['device_id'],
            items=[dict(event=wire, object=dict(crypto_version=2,aad_version=2,nonce=b64(row['nonce']),ciphertext=b64(row['ciphertext'])))])
        response=client.post('/api/v3/sync/encrypted/account/push',headers=_headers(token),json=body)
        assert response.status_code==200,response.text
        if lost:
            assert row in native(tmp,path,identity,user,step='pending',sealed=True)
            response=client.post('/api/v3/sync/encrypted/account/push',headers=_headers(token),json=body)
            assert response.status_code==200 and response.json()['results'][0]['duplicate']
        native(tmp,path,identity,user,step='receipt',event_id=h['event_id'],server_sequence=response.json()['results'][0]['server_sequence'])
    return [row['event'] for row in rows]


def pull(tmp,client,token,path,identity,user,amk):
    with sqlite3.connect(path) as db: cursor=db.execute('SELECT pull_cursor FROM cloud_sync_state').fetchone()[0]
    response=client.get('/api/v3/sync/encrypted/pull',headers=_headers(token),params=dict(device_id=identity['device_id'],since=cursor,limit=100,protocol_version=3,encrypted_sync_version=3))
    assert response.status_code==200,response.text
    page=response.json(); rows=[]
    for item in page['items']:
        row=dict(item['event']);row['source_device_id']=row.pop('device_id');row['envelope']=item['object']
        for key in ('updated_at','deleted_at'):
            if row[key] is not None:row[key]=datetime.fromisoformat(row[key].replace('Z','+00:00')).astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z')
        rows.append(row)
    native(tmp,path,identity,user,step='persist',command=dict(account_id=identity['local_account_id'],device_id=identity['device_id'],canonical_user_id=user,expected_cursor=cursor,next_cursor=page['next_cursor'],has_more=page['has_more'],items=rows))
    outcomes=[]
    for item in page['items']:
        opened=_crypto_bridge(tmp,dict(action='catalog_open',canonical_user_id=user,amk=amk,item=item))
        outcomes.append(native(tmp,path,identity,user,step='apply',event_id=item['event']['event_id'],opened=opened))
        # Duplicate authenticated apply reopens again and produces the same proof.
        assert native(tmp,path,identity,user,step='apply',event_id=item['event']['event_id'],opened=opened)==outcomes[-1]
    return outcomes


def decision(tmp,path,identity,user,t,id,selected=None,proposed=None):
    v=native(tmp,path,identity,user);entity=next(e for e in v['entities'] if e['entity_type']==t and e['entity_id']==id)
    return native(tmp,path,identity,user,step='decide',decision=dict(entity_type=t,entity_id=id,expected_tips=sorted(entity['tips']),expected_local=entity['local'],proposed=proposed if proposed is not None else entity['local'],selected_event_id=selected))


def test_account_catalog_explicit_migration_two_native_devices_v2_postgresql(cloud_client,tmp_path):
    client,engine=cloud_client;user=str(create_user(engine));token=login(client).json()['access_token'];headers=_headers(token)
    a,ia=provision(tmp_path,'catalog-A',user,False);b,ib=provision(tmp_path,'catalog-B',user,False)
    for identity in (ia,ib):assert client.put(f"/api/v1/sync/devices/{identity['device_id']}",headers=headers).status_code==200
    with sqlite3.connect(a) as db:
        for i,p in enumerate(('L1','C1','C2')):
            db.execute("INSERT INTO projects(id,name,infinite,unit,status,payload_json) VALUES(?,?,1,'symbols','active','{}')",(p,p))
            db.execute('INSERT INTO project_order VALUES(?,?)',(p,i))
    boots={}
    for p in ('C1','C2'):
        boots[p]=native(tmp_path,a,ia,user,action='bootstrap_prepare',project_id=p)['bootstrap_id']
        assert client.post(f'/api/v1/cloud/projects/{p}/bootstrap',headers=headers,json=dict(bootstrap_id=boots[p],device_id=ia['device_id'])).status_code==200
        native(tmp_path,a,ia,user,action='bootstrap_prepare_capture',project_id=p,bootstrap_id=boots[p],remote_high_water=0)
        assert client.post(f'/api/v1/cloud/projects/{p}/bootstrap/complete',headers=headers,json=dict(bootstrap_id=boots[p],device_id=ia['device_id'],initial_event_count=0,initial_max_server_sequence=0)).status_code==200
        native(tmp_path,a,ia,user,action='bootstrap_confirm_active',project_id=p,bootstrap_id=boots[p],remote_high_water=0)
    assert client.post('/api/v2/sync/encrypted/cutover',headers=headers,json=dict(expected_cutover_epoch=0)).status_code==200
    for i in (ia,ib):assert client.post('/api/v3/sync/encrypted/reader-ready',headers=headers,json=dict(device_id=i['device_id'],reader_transport_version=3)).status_code==204
    assert client.post('/api/v3/sync/encrypted/cutover',headers=headers,json=dict(expected_cutover_epoch=1)).status_code==200
    amk=list(os.urandom(32));metadata=[]
    for p in ('C1','C2'):
        native(tmp_path,a,ia,user,action='metadata_authority',project_id=p,step='begin')
        e=native(tmp_path,a,ia,user,action='metadata_authority',project_id=p,step='read')['unsealed'][0]
        o=_crypto_bridge(tmp_path,dict(action='metadata_seal',payload=e,amk=amk));native(tmp_path,a,ia,user,action='metadata_authority',project_id=p,step='seal',event_id=e['header']['event_id'],nonce=o['nonce'],ciphertext=o['ciphertext'])
        h=e['header'];wire={k:h[k] for k in ('event_id','project_id','entity_id','revision','updated_at')};wire.update(entity_type='project_metadata',operation='upsert',deleted_at=None)
        assert client.post('/api/v3/sync/encrypted/push',headers=headers,json=dict(protocol_version=3,encrypted_sync_version=3,device_id=ia['device_id'],items=[dict(event=wire,object=o['object'])])).status_code==200
        metadata.append(e)
        native(tmp_path,b,ib,user,action='bootstrap_import',project_id=p,bootstrap_id=boots[p],remote_high_water=len(metadata),display_name=p,authenticated_metadata=e['metadata'])
    for path,i in ((a,ia),(b,ib)):
        page=client.get('/api/v3/sync/encrypted/pull',headers=headers,params=dict(device_id=i['device_id'],since=0,limit=100,protocol_version=3,encrypted_sync_version=3)).json();cursor=0
        for item in page['items']:
            row=dict(item['event']);row['source_device_id']=row.pop('device_id');row['envelope']=item['object'];row['updated_at']=metadata[0]['header']['updated_at']
            opened=_crypto_bridge(tmp_path,dict(action='metadata_open',canonical_user_id=user,amk=amk,item=item))
            native(tmp_path,path,i,user,action='metadata_authority',project_id=row['project_id'],step='receive',command=dict(account_id=i['local_account_id'],device_id=i['device_id'],canonical_user_id=user,expected_cursor=cursor,next_cursor=row['server_sequence'],has_more=False,items=[row]),opened=opened)
            cursor=row['server_sequence']
    with sqlite3.connect(a) as db:
        for pos,(f,n) in enumerate((('F1','Work'),('F2','Archive'))):db.execute('INSERT INTO project_folders VALUES(?,?,?,?)',(f,n,pos,json.dumps(dict(id=f,name=n))))
        for p,f in (('C1','F1'),('L1','F1'),('C2','F2')):db.execute('INSERT INTO project_folder_members VALUES(?,?)',(p,f))
    assert native(tmp_path,a,ia,user)['state']=='catalog_local'
    assert native(tmp_path,a,ia,user,step='pending',sealed=False)==[]
    assert native(tmp_path,a,ia,user,step='begin')['state']=='captured'
    events=[]
    for _ in range(3):
        events+=push(tmp_path,client,token,a,ia,user,amk,lost=True)
        for path,i in ((a,ia),(b,ib)):assert all(o=='applied' for o in pull(tmp_path,client,token,path,i,user,amk))
    assert len(events)==6 and 'L1' not in json.dumps(events)
    assert next(e for e in events if e['header']['entity_type']=='project_order')['payload']['ids']==['C1','C2']
    for path,i in ((a,ia),(b,ib)):assert native(tmp_path,path,i,user)['state']=='active'
    for t,id,pa,pb in (
        ('folder','F1',dict(name='Work A'),dict(name='Work B')),
        ('folder_membership','C1',dict(folder_id='F2'),dict(folder_id=None)),
        ('project_order','project_order',dict(ids=['C2','C1']),dict(ids=['C1','C2'])),
    ):
        assert native(tmp_path,a,ia,user,step='normal',entity_type=t,entity_id=id,payload=pa)
        if t=='project_order':decision(tmp_path,b,ib,user,t,id,proposed=pb)
        else:assert native(tmp_path,b,ib,user,step='normal',entity_type=t,entity_id=id,payload=pb)
        edits=push(tmp_path,client,token,a,ia,user,amk)+push(tmp_path,client,token,b,ib,user,amk)
        assert len(edits)==2
        for path,i in ((a,ia),(b,ib)):
            pull(tmp_path,client,token,path,i,user,amk);assert native(tmp_path,path,i,user)['state']=='conflict'
        decision(tmp_path,a,ia,user,t,id,selected=edits[0]['header']['event_id'])
        resolution=push(tmp_path,client,token,a,ia,user,amk,lost=True)[0]
        assert resolution['header']['parent_event_ids']==sorted(e['header']['event_id'] for e in edits)
        for path,i in ((a,ia),(b,ib)):
            pull(tmp_path,client,token,path,i,user,amk);assert native(tmp_path,path,i,user)['state']=='active'
    assert native(tmp_path,a,ia,user,step='normal',entity_type='folder',entity_id='F2',payload=None)
    push(tmp_path,client,token,a,ia,user,amk,lost=True)
    for path,i in ((a,ia),(b,ib)):
        assert pull(tmp_path,client,token,path,i,user,amk)==['catalog_folder_has_members']
        assert native(tmp_path,path,i,user)['state']=='blocked'
        with sqlite3.connect(path) as db:
            assert db.execute("SELECT folder_id FROM project_folder_members WHERE project_id='C2'").fetchone()==('F2',)
            latest=db.execute('SELECT pull_cursor FROM cloud_sync_state').fetchone()[0]
        assert native(tmp_path,path,i,user,step='ack')['candidate_cursor']==latest-1
    with sqlite3.connect(a) as db:
        assert db.execute("SELECT folder_id FROM project_folder_members WHERE project_id='L1'").fetchone()==('F1',)
        assert db.execute("SELECT project_id FROM project_order ORDER BY position").fetchall()==[('L1',),('C2',),('C1',)]
        assert db.execute('SELECT count(*) FROM cloud_sync_project_bindings').fetchone()[0]==2
