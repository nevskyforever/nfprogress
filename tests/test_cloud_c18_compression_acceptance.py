"""Mixed production compression selection/crypto -> native file-backed apply and PostgreSQL."""
import os
import sqlite3
from uuid import uuid4
from sqlalchemy import text
from nfprogress.core.sqlite.connection import register_remote_apply_authorization_guard
from test_cloud_auth import cloud_client, migrated_database, create_user, login
from test_cloud_c15_headless_cross_runtime import PROJECT_ID, _crypto_bridge, _headers
from test_cloud_c18_authority_cross_runtime import provision, bootstrap, native, publish, sync
from test_cloud_c18_content_note_gate import capabilities
from test_cloud_c18_document_acceptance import document, content, support, receive, stored, heads
from test_cloud_c18_compression_gate import declare, AUTHORIZE


def emit_compressed(client,tmp,token,path,identity,user,amk,ready):
    headers=_headers(token);sent=[]
    for item in document(tmp,path,identity,user,'pending'):
        # Native owns canonical capture/framing; TS owns opportunistic compression
        # admission, AEAD, and final sealing. The same selector is used by runtime.
        assert item['frame'][11]==0
        h=item['event']['header']
        sealed=_crypto_bridge(tmp,dict(action='document_seal',frame=item['frame'],amk=amk,compression_ready=ready))
        assert sealed['frame'][11]==int(ready)
        document(tmp,path,identity,user,'seal',event_id=h['event_id'],frame=sealed['frame'],nonce=sealed['nonce'],ciphertext=sealed['ciphertext'])
        # Reopen/retry reads immutable envelope, never recompresses/re-encrypts.
        frozen=document(tmp,path,identity,user,'pending',sealed=True)[0]
        assert frozen['nonce']==sealed['nonce'] and frozen['ciphertext']==sealed['ciphertext']
        wire={k:h[k] for k in ('event_id','project_id','entity_id','revision','updated_at')}
        wire.update(entity_type='document',operation='event',deleted_at=None)
        request=dict(protocol_version=3,encrypted_sync_version=3,device_id=identity['device_id'],items=[dict(event=wire,object=sealed['object'])])
        r=client.post('/api/v3/sync/encrypted/push',headers=headers,json=request);assert r.status_code==200,r.text
        # Lose the first receipt; retry exact encrypted object and event.
        r=client.post('/api/v3/sync/encrypted/push',headers=headers,json=request);assert r.status_code==200,r.text
        receipt=r.json()['results'][0];assert receipt['duplicate'] is True
        document(tmp,path,identity,user,'receipt',event_id=h['event_id'],server_sequence=receipt['server_sequence'],duplicate=True)
        sent.append((h['event_id'],sealed['frame'][11],sealed['object']))
    return sent


def test_mixed_id0_id1_two_devices_upgrade_late_legacy_and_exact_retry(cloud_client,tmp_path):
    client,engine=cloud_client;user=str(create_user(engine));token=login(client).json()['access_token'];headers=_headers(token)
    a,ia=provision(tmp_path,'compressed-A',user,True);b,ib=provision(tmp_path,'compressed-B',user,False)
    for path,identity in ((a,ia),(b,ib)):
        assert client.put(f"/api/v1/sync/devices/{identity['device_id']}",headers=headers).status_code==200
        document(tmp_path,path,identity,user,'init')
    with sqlite3.connect(a) as db:
        register_remote_apply_authorization_guard(db)
        db.execute("UPDATE projects SET payload_json=json_set(payload_json,'$.work_method','app')")
    boot=bootstrap(tmp_path,a,ia,'bootstrap_prepare')['bootstrap_id']
    assert client.post(f'/api/v1/cloud/projects/{PROJECT_ID}/bootstrap',headers=headers,json=dict(bootstrap_id=boot,device_id=ia['device_id'])).status_code==200
    bootstrap(tmp_path,a,ia,'bootstrap_prepare_capture',bootstrap_id=boot,remote_high_water=0)
    assert client.post(f'/api/v1/cloud/projects/{PROJECT_ID}/bootstrap/complete',headers=headers,json=dict(bootstrap_id=boot,device_id=ia['device_id'],initial_event_count=0,initial_max_server_sequence=0)).status_code==200
    bootstrap(tmp_path,a,ia,'bootstrap_confirm_active',bootstrap_id=boot,remote_high_water=0)
    assert client.post('/api/v2/sync/encrypted/cutover',headers=headers,json=dict(expected_cutover_epoch=0)).status_code==200
    for identity in (ia,ib):
        assert client.post('/api/v3/sync/encrypted/reader-ready',headers=headers,json=dict(device_id=identity['device_id'],reader_transport_version=3)).status_code==204
        assert client.put('/api/v3/sync/encrypted/note-reader-capabilities',headers=headers,json=capabilities(identity['device_id'])).status_code==204
        support(client,headers,identity['device_id'])
    assert client.post('/api/v3/sync/encrypted/cutover',headers=headers,json=dict(expected_cutover_epoch=1)).status_code==200
    native(tmp_path,a,ia,user,'begin');amk=list(os.urandom(32));meta,_=publish(client,tmp_path,token,a,ia,user,amk)
    assert sync(client,tmp_path,token,a,ia,user,amk)['view']['state']=='active'
    bootstrap(tmp_path,b,ib,'bootstrap_import',bootstrap_id=boot,remote_high_water=1,display_name=meta['metadata']['name'],authenticated_metadata=meta['metadata'])
    assert sync(client,tmp_path,token,b,ib,user,amk)['view']['state']=='active'
    p=document(tmp_path,a,ia,user,'save',content=content('First portable manuscript paragraph. '*100));pid=p['document_id']
    document(tmp_path,a,ia,user,'begin')
    assert declare(client,headers,ia['device_id']).status_code==204
    authorize=lambda: client.post(AUTHORIZE,headers=headers,json=dict(device_id=ia['device_id'])).json()['ready']
    assert authorize() is False # B absent capability => ID0
    history=emit_compressed(client,tmp_path,token,a,ia,user,amk,False)
    for path,identity in ((a,ia),(b,ib)):assert receive(client,tmp_path,token,path,identity,user,amk)==['applied']
    assert declare(client,headers,ib['device_id']).status_code==204
    assert authorize() is True
    changed=content('New compressed portable manuscript paragraph. '*100)
    assert 'error' not in document(tmp_path,a,ia,user,'save',content=changed,expected=heads(tmp_path,a,ia,user,pid))
    history+=emit_compressed(client,tmp_path,token,a,ia,user,amk,True)
    for path,identity in ((a,ia),(b,ib)):
        assert receive(client,tmp_path,token,path,identity,user,amk)==['applied']
        assert stored(path,pid)['content_json']==changed
    # Joining a capable device preserves eligibility once it declares explicitly.
    c=str(uuid4());assert client.put(f'/api/v1/sync/devices/{c}',headers=headers).status_code==200
    assert client.post('/api/v3/sync/encrypted/reader-ready',headers=headers,json=dict(device_id=c,reader_transport_version=3)).status_code==204
    assert client.put('/api/v3/sync/encrypted/note-reader-capabilities',headers=headers,json=capabilities(c)).status_code==204
    support(client,headers,c)
    assert authorize() is False
    assert declare(client,headers,c).status_code==204;assert authorize() is True
    # Legacy reader joins after ID1 history. New writes are ID0; it cannot pull history.
    d=str(uuid4());assert client.put(f'/api/v1/sync/devices/{d}',headers=headers).status_code==200
    assert client.post('/api/v3/sync/encrypted/reader-ready',headers=headers,json=dict(device_id=d,reader_transport_version=3)).status_code==204
    assert client.put('/api/v3/sync/encrypted/note-reader-capabilities',headers=headers,json=capabilities(d)).status_code==204
    support(client,headers,d)
    assert authorize() is False
    rejected=client.get('/api/v3/sync/encrypted/pull',headers=headers,params=dict(device_id=d,since=0,limit=100,protocol_version=3,encrypted_sync_version=3))
    assert rejected.status_code==409 and rejected.json()['detail']['code']=='compression_reader_required'
    final=content('Later ID0 manuscript paragraph. '*100)
    assert 'error' not in document(tmp_path,a,ia,user,'save',content=final,expected=heads(tmp_path,a,ia,user,pid))
    history+=emit_compressed(client,tmp_path,token,a,ia,user,amk,False)
    for path,identity in ((a,ia),(b,ib)):
        assert receive(client,tmp_path,token,path,identity,user,amk)==['applied']
        assert stored(path,pid)['content_json']==final
        assert receive(client,tmp_path,token,path,identity,user,amk)==[]
        with sqlite3.connect(path) as db:
            assert db.execute('SELECT COUNT(*) FROM cloud_document_apply_ledger').fetchone()[0]==3
            assert db.execute('SELECT COUNT(*) FROM cloud_document_events WHERE state!=\'applied\'').fetchone()[0]==0
            assert db.execute('SELECT pull_cursor FROM cloud_sync_state').fetchone()[0]==4
    assert [i[1] for i in history]==[0,1,0]
    from base64 import urlsafe_b64decode
    with engine.connect() as db:
        for id,_,obj in history:
            row=db.execute(text('SELECT nonce,ciphertext FROM encrypted_objects WHERE event_id=:id'),dict(id=id)).one()
            decode=lambda value:urlsafe_b64decode(value+'='*(-len(value)%4))
            assert bytes(row.nonce)==decode(obj['nonce']) and bytes(row.ciphertext)==decode(obj['ciphertext'])
            assert b'portable manuscript paragraph' not in bytes(row.ciphertext)
        assert db.execute(text('SELECT COUNT(*) FROM sync_events')).scalar_one()==4 # codec1 ID0 + codec10 ID0/1/0
