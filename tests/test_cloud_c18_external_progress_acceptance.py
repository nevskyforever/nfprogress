"""C18.6.02: real PostgreSQL/native local source boundary; no cloud binding API."""
import io,json,sqlite3,zipfile,os
from uuid import uuid4
from sqlalchemy import text
from nfprogress.core.sqlite.connection import register_remote_apply_authorization_guard
from test_cloud_auth import cloud_client,migrated_database,create_user,login
from test_cloud_c18_authority_cross_runtime import provision,bootstrap,native,publish,sync
from test_cloud_c15_headless_cross_runtime import PROJECT_ID,_headers,_crypto_bridge
from test_cloud_c18_progress_acceptance import progress,support,emit,receive,owner,totals
from test_cloud_c18_document_acceptance import document

def test_external_progress_word_scrivener_revalidation_and_no_path_transport(cloud_client,tmp_path):
    client,engine=cloud_client;user=str(create_user(engine));token=login(client).json()['access_token'];headers=_headers(token)
    a,ia=provision(tmp_path,'progress-A',user,True);b,ib=provision(tmp_path,'progress-B',user,False)
    for identity in (ia,ib):assert client.put(f"/api/v1/sync/devices/{identity['device_id']}",headers=headers).status_code==200
    with sqlite3.connect(a) as db:
        register_remote_apply_authorization_guard(db);db.execute("UPDATE projects SET goal=1000,infinite=0,payload_json=json_set(payload_json,'$.work_method','sync','$.total',100,'$.progress_entries',json('[]'))")
    with sqlite3.connect(a) as db:
        register_remote_apply_authorization_guard(db)
        db.execute("UPDATE projects SET payload_json=json_set(payload_json,'$.synch',json(?),'$.last_synch',?)",(json.dumps({'path':'/Users/C18_SECRET_PATH/book-private.docx','source_id':'SOURCE-ID-C18-LOCAL-ONLY'}),'local-clock-only'))
        db.execute("INSERT INTO project_bindings(id,project_id,binding_type,external_path,source_id,payload_json) VALUES('legacy-local',?,'word',?,'SOURCE-ID-C18-LOCAL-ONLY','{\"unknown_local\":true}')",(PROJECT_ID,'/Users/C18_SECRET_PATH/book-private.docx'))
    boot=bootstrap(tmp_path,a,ia,'bootstrap_prepare')['bootstrap_id'];assert client.post(f'/api/v1/cloud/projects/{PROJECT_ID}/bootstrap',headers=headers,json=dict(bootstrap_id=boot,device_id=ia['device_id'])).status_code==200
    bootstrap(tmp_path,a,ia,'bootstrap_prepare_capture',bootstrap_id=boot,remote_high_water=0)
    assert client.post(f'/api/v1/cloud/projects/{PROJECT_ID}/bootstrap/complete',headers=headers,json=dict(bootstrap_id=boot,device_id=ia['device_id'],initial_event_count=0,initial_max_server_sequence=0)).status_code==200
    bootstrap(tmp_path,a,ia,'bootstrap_confirm_active',bootstrap_id=boot,remote_high_water=0)
    assert client.post('/api/v2/sync/encrypted/cutover',headers=headers,json=dict(expected_cutover_epoch=0)).status_code==200
    for identity in (ia,ib):assert client.post('/api/v3/sync/encrypted/reader-ready',headers=headers,json=dict(device_id=identity['device_id'],reader_transport_version=3)).status_code==204
    assert client.post('/api/v3/sync/encrypted/cutover',headers=headers,json=dict(expected_cutover_epoch=1)).status_code==200
    native(tmp_path,a,ia,user,'begin');amk=list(os.urandom(32));meta,_=publish(client,tmp_path,token,a,ia,user,amk);assert sync(client,tmp_path,token,a,ia,user,amk)['view']['state']=='active'
    assert 'C18_SECRET_PATH' not in json.dumps(meta) and 'SOURCE-ID-C18-LOCAL-ONLY' not in json.dumps(meta)
    bootstrap(tmp_path,b,ib,'bootstrap_import',bootstrap_id=boot,remote_high_water=1,display_name=meta['metadata']['name'],authenticated_metadata=meta['metadata']);assert sync(client,tmp_path,token,b,ib,user,amk)['view']['state']=='active'

    with sqlite3.connect(b) as db:
        register_remote_apply_authorization_guard(db);db.execute("UPDATE projects SET payload_json=json_set(payload_json,'$.total',0,'$.progress_entries',json('[]'))")
    for identity in (ia,ib):support(client,headers,identity['device_id'])
    assert progress(tmp_path,a,ia,user,'pending')==[]
    third=str(uuid4());assert client.put(f'/api/v1/sync/devices/{third}',headers=headers).status_code==200
    assert client.post('/api/v3/sync/encrypted/reader-ready',headers=headers,json=dict(device_id=third,reader_transport_version=3)).status_code==204
    assert client.get('/api/v3/sync/encrypted/progress-reader-capabilities',headers=headers).json()==dict(ready=False,missing_devices=1)
    captured=progress(tmp_path,a,ia,user,'begin');assert captured['owners'][0]['state']=='publication_pending',captured
    item=progress(tmp_path,a,ia,user,'pending')[0];h=item['event']['header'];sealed=_crypto_bridge(tmp_path,dict(action='progress_seal',frame=item['frame'],amk=amk));wire={k:h[k] for k in ('event_id','project_id','entity_id','revision','updated_at')};wire.update(entity_type='progress',operation='event',deleted_at=None)
    denied=client.post('/api/v3/sync/encrypted/push',headers=headers,json=dict(protocol_version=3,encrypted_sync_version=3,device_id=ia['device_id'],items=[dict(event=wire,object=sealed['object'])]));assert denied.status_code==409,denied.text
    support(client,headers,third);assert client.get('/api/v3/sync/encrypted/progress-reader-capabilities',headers=headers).json()==dict(ready=True,missing_devices=0)
    requests=emit(client,tmp_path,token,a,ia,user,amk,lose=True)
    revoked=dict(device_id=third,frame_version=0,codec_id=11,codec_version=0,reader_version=0,compression_zero=False)
    assert client.put('/api/v3/sync/encrypted/progress-reader-capabilities',headers=headers,json=revoked).status_code==204
    denied_pull=client.get('/api/v3/sync/encrypted/pull',headers=headers,params=dict(device_id=third,since=0,limit=100,protocol_version=3,encrypted_sync_version=3))
    assert denied_pull.status_code==409 and 'progress_reader_required' in denied_pull.text
    support(client,headers,third)

    for path,identity in ((a,ia),(b,ib)):assert receive(client,tmp_path,token,path,identity,user,amk)==['applied']
    assert totals(a)==totals(b);assert totals(a)[:2]==(100.0,10.0)

    assert document(tmp_path,b,ib,user,'background')['checked']==0
    def word_bytes(n):
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,'w') as z:z.writestr('word/document.xml',f'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>{"x"*n}</w:t></w:r></w:p></w:body></w:document>')
        return buf.getvalue()
    source=tmp_path/'C18_SECRET_PATH_B.docx';source.write_bytes(word_bytes(100))
    before=owner(tmp_path,b,ib,user)['tips'];assert document(tmp_path,b,ib,user,'configure_source',source_type='word',source_path=str(source))['configured']
    assert owner(tmp_path,b,ib,user)['tips']==before
    assert document(tmp_path,b,ib,user,'prepare_progress')['changed'] is False
    assert progress(tmp_path,b,ib,user,'pending')==[]
    with sqlite3.connect(a) as db:assert db.execute('SELECT count(*) FROM project_bindings').fetchone()[0]==1
    source.write_bytes(word_bytes(150));prepared=document(tmp_path,b,ib,user,'refresh_progress');assert prepared['sync']['proposal_pending'] is True,prepared
    assert totals(b)[0]==100 and progress(tmp_path,b,ib,user,'pending')==[]
    source.write_bytes(word_bytes(160));assert document(tmp_path,b,ib,user,'confirm_progress')['error']=='external_progress_proposal_stale';assert totals(b)[0]==100
    document(tmp_path,b,ib,user,'refresh_progress');confirmed=document(tmp_path,b,ib,user,'confirm_progress');assert confirmed['changed'] is True,confirmed
    pending=progress(tmp_path,b,ib,user,'pending');assert len(pending)==1
    for row in pending:assert 'C18_SECRET_PATH' not in bytes(row['frame']).decode('utf8',errors='ignore')
    requests=emit(client,tmp_path,token,b,ib,user,amk);assert 'C18_SECRET_PATH' not in json.dumps(requests)
    for path,identity in ((a,ia),(b,ib)):assert receive(client,tmp_path,token,path,identity,user,amk)==['applied']
    assert totals(a)==totals(b) and totals(b)[0]==160
    assert document(tmp_path,b,ib,user,'background')['changed']==0
    source.rename(source.with_suffix('.moved.docx'));assert document(tmp_path,b,ib,user,'prepare_progress')['error']=='sync_source_missing';assert totals(b)[0]==160
    root=tmp_path/'C18_SECRET_PATH.scriv';root.mkdir();item='SOURCE-ID-C18-LOCAL-ONLY';(root/'Files'/'Data'/item).mkdir(parents=True)
    binder=root/'project.scrivx';binder.write_text(f'<ScrivenerProject><Binder><BinderItem UUID="{item}" Type="Text"><Title>Local only</Title></BinderItem></Binder></ScrivenerProject>')
    (root/'Files'/'Data'/item/'content.rtf').write_text('{\\rtf1 '+('s'*170)+'}')
    configured=document(tmp_path,b,ib,user,'configure_source',source_type='scrivener',source_path=str(root),item_id=item);assert configured.get('configured'),configured
    assert 'error' in document(tmp_path,b,ib,user,'configure_source',source_type='scrivener',source_path=str(root),item_id='unknown')
    proposal=document(tmp_path,b,ib,user,'refresh_progress');assert proposal['sync']['proposal_pending'],proposal
    binder.write_text('<ScrivenerProject><Binder /></ScrivenerProject>')
    assert document(tmp_path,b,ib,user,'prepare_progress')['error']=='sync_source_stale';assert totals(b)[0]==160
    with sqlite3.connect(a) as db:assert db.execute('SELECT count(*) FROM project_bindings').fetchone()[0]==1
    with engine.connect() as db:
        for table in ('sync_events','encrypted_objects','sync_devices','cloud_projects'):
            rows=db.execute(text(f'SELECT row_to_json(t)::text FROM {table} t')).scalars().all();assert not any('C18_SECRET_PATH' in r or item in r for r in rows)
