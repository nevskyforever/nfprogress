"""Mandatory real PostgreSQL, production TS C11 and two file SQLite progress acceptance."""
import json, os, sqlite3
import pytest
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy import text
from nfprogress.core.sqlite.connection import register_remote_apply_authorization_guard
from test_cloud_auth import cloud_client, migrated_database, create_user, login
from test_cloud_c18_content_note_gate import capabilities
from test_cloud_c18_authority_cross_runtime import provision, bootstrap, native, publish, sync
from test_cloud_c15_headless_cross_runtime import PROJECT_ID, _crypto_bridge, _native_bridge, _headers
NOW='2026-10-03T00:00:00.000000Z'
def progress(tmp,path,identity,user,step,**values):
    return _native_bridge(tmp,dict(action='progress',database_path=str(path),local_account_id=identity['local_account_id'],device_id=identity['device_id'],canonical_user_id=user,project_id=PROJECT_ID,step=step,**values))
def support(client,headers,device):
    assert client.put('/api/v3/sync/encrypted/note-reader-capabilities',headers=headers,json=capabilities(device)).status_code==204
    for kind,codec in [('map',9),('document',10),('progress',11)]:
        r=client.put(f'/api/v3/sync/encrypted/{kind}-reader-capabilities',headers=headers,json=dict(device_id=device,frame_version=1,codec_id=codec,codec_version=1,reader_version=1,compression_zero=True));assert r.status_code==204,r.text
def emit(client,tmp,token,path,identity,user,amk,lose=False):
    sent=[]
    for item in progress(tmp,path,identity,user,'pending'):
        h=item['event']['header'];sealed=_crypto_bridge(tmp,dict(action='progress_seal',frame=item['frame'],amk=amk))
        assert progress(tmp,path,identity,user,'seal',event_id=h['event_id'],frame=item['frame'],nonce=sealed['nonce'],ciphertext=sealed['ciphertext']) is True
        wire={k:h[k] for k in ('event_id','project_id','entity_id','revision','updated_at')};wire.update(entity_type='progress',operation='event',deleted_at=None)
        request=dict(protocol_version=3,encrypted_sync_version=3,device_id=identity['device_id'],items=[dict(event=wire,object=sealed['object'])])
        response=client.post('/api/v3/sync/encrypted/push',headers=_headers(token),json=request);assert response.status_code==200,response.text
        replay=client.post('/api/v3/sync/encrypted/push',headers=_headers(token),json=request);assert replay.status_code==200 and replay.json()['results'][0]['duplicate'];assert replay.json()['results'][0]['server_sequence']==response.json()['results'][0]['server_sequence']
        if not lose:
            r=response.json()['results'][0];progress(tmp,path,identity,user,'receipt',event_id=h['event_id'],server_sequence=r['server_sequence'],duplicate=r['duplicate'])
        else:
            frozen=next(x for x in progress(tmp,path,identity,user,'pending',sealed=True) if x['event']['header']['event_id']==h['event_id']);assert frozen['nonce']==sealed['nonce'] and frozen['ciphertext']==sealed['ciphertext'] and frozen['frame']==item['frame']
        sent.append(request)
    return sent

def receive(client,tmp,token,path,identity,user,amk):
    with sqlite3.connect(path) as db:cursor=db.execute('SELECT pull_cursor FROM cloud_sync_state').fetchone()[0]
    response=client.get('/api/v3/sync/encrypted/pull',headers=_headers(token),params=dict(device_id=identity['device_id'],since=cursor,limit=100,protocol_version=3,encrypted_sync_version=3));assert response.status_code==200,response.text
    outcomes=[]
    for item in response.json()['items']:
        assert item['event']['entity_type']=='progress'
        opened=_crypto_bridge(tmp,dict(action='progress_open',canonical_user_id=user,amk=amk,item=item))
        row=dict(item['event']);row['source_device_id']=row.pop('device_id');row['envelope']=item['object'];row['updated_at']=datetime.fromisoformat(row['updated_at'].replace('Z','+00:00')).astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z')
        command=dict(account_id=identity['local_account_id'],device_id=identity['device_id'],canonical_user_id=user,expected_cursor=cursor,next_cursor=row['server_sequence'],has_more=False,items=[row])
        outcomes.append(progress(tmp,path,identity,user,'receive',command=command,opened=opened));cursor=row['server_sequence']
    return outcomes

def owner(tmp,path,identity,user):return progress(tmp,path,identity,user,'view')['owners'][0]
def totals(path):
    with sqlite3.connect(path) as db:
        payload=json.loads(db.execute('SELECT payload_json FROM projects').fetchone()[0]);entries=[json.loads(row[0]) for row in db.execute('SELECT e.payload_json FROM progress_entries e JOIN progress_order o ON o.entry_id=e.id ORDER BY o.position')]
        return payload['total'],payload['progress'],entries

def test_progress_two_devices_causal_rebase_delete_and_derived_rebuild(cloud_client,tmp_path):
    client,engine=cloud_client;user=str(create_user(engine));token=login(client).json()['access_token'];headers=_headers(token)
    a,ia=provision(tmp_path,'progress-A',user,True);b,ib=provision(tmp_path,'progress-B',user,False)
    for identity in (ia,ib):assert client.put(f"/api/v1/sync/devices/{identity['device_id']}",headers=headers).status_code==200
    with sqlite3.connect(a) as db:
        register_remote_apply_authorization_guard(db);db.execute("UPDATE projects SET goal=1000,infinite=0,payload_json=json_set(payload_json,'$.total',100,'$.progress_entries',json('[]'))")
    boot=bootstrap(tmp_path,a,ia,'bootstrap_prepare')['bootstrap_id'];assert client.post(f'/api/v1/cloud/projects/{PROJECT_ID}/bootstrap',headers=headers,json=dict(bootstrap_id=boot,device_id=ia['device_id'])).status_code==200
    bootstrap(tmp_path,a,ia,'bootstrap_prepare_capture',bootstrap_id=boot,remote_high_water=0)
    assert client.post(f'/api/v1/cloud/projects/{PROJECT_ID}/bootstrap/complete',headers=headers,json=dict(bootstrap_id=boot,device_id=ia['device_id'],initial_event_count=0,initial_max_server_sequence=0)).status_code==200
    bootstrap(tmp_path,a,ia,'bootstrap_confirm_active',bootstrap_id=boot,remote_high_water=0)
    assert client.post('/api/v2/sync/encrypted/cutover',headers=headers,json=dict(expected_cutover_epoch=0)).status_code==200
    for identity in (ia,ib):assert client.post('/api/v3/sync/encrypted/reader-ready',headers=headers,json=dict(device_id=identity['device_id'],reader_transport_version=3)).status_code==204
    assert client.post('/api/v3/sync/encrypted/cutover',headers=headers,json=dict(expected_cutover_epoch=1)).status_code==200
    native(tmp_path,a,ia,user,'begin');amk=list(os.urandom(32));meta,_=publish(client,tmp_path,token,a,ia,user,amk);assert sync(client,tmp_path,token,a,ia,user,amk)['view']['state']=='active'
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
    base=owner(tmp_path,a,ia,user)['tips']
    ids=[]
    for path,identity,total,delta in ((a,ia,120,20),(b,ib,130,30),(b,ib,140,10)):
        o=owner(tmp_path,path,identity,user);eid=str(uuid4());ids.append(eid)
        entry=dict(id=eid,new_total=total,new_total_symbols=total,added=delta,added_symbols=delta,added_progress=delta/10,created_at=NOW)
        assert progress(tmp_path,path,identity,user,'append',expected=o['tips'],entry=entry) is True
    requests+=emit(client,tmp_path,token,a,ia,user,amk);requests+=emit(client,tmp_path,token,b,ib,user,amk)
    for path,identity in ((a,ia),(b,ib)):
        outcomes=receive(client,tmp_path,token,path,identity,user,amk);assert 'conflict_preserved' in outcomes,outcomes
        assert owner(tmp_path,path,identity,user)['state']=='conflict';assert totals(path)[0] in (120,140)
    o=owner(tmp_path,a,ia,user);chosen=next(v for v in o['versions'] if v['chain']['entries'][-1]['entry_id']==ids[0])
    decision=dict(project_id=PROJECT_ID,stage_id=None,expected_tips=o['tips'],expected_local=o['local'],selected_event_id=chosen['event_id'],operation='rebase',target_entry_id=None,rebased_from=ids[1:],corrected_delta=None)
    result=progress(tmp_path,a,ia,user,'decide',decision=decision);assert isinstance(result,str),result
    requests+=emit(client,tmp_path,token,a,ia,user,amk)
    for path,identity in ((a,ia),(b,ib)):assert receive(client,tmp_path,token,path,identity,user,amk)==['applied']
    assert totals(a)==totals(b);assert totals(a)[:2]==(160.0,16.0);assert [e['new_total_symbols'] for e in totals(a)[2]]==[120,150,160]
    o=owner(tmp_path,a,ia,user);decision.update(expected_tips=o['tips'],expected_local=o['local'],selected_event_id=o['tips'][0],operation='tombstone',target_entry_id=ids[0],rebased_from=[])
    assert progress(tmp_path,a,ia,user,'decide',decision=decision)['error']=='progress_descendant_rebase_required'
    decision['rebased_from']=[e['id'] for e in totals(a)[2]][1:];assert isinstance(progress(tmp_path,a,ia,user,'decide',decision=decision),str)
    requests+=emit(client,tmp_path,token,a,ia,user,amk)
    for path,identity in ((a,ia),(b,ib)):assert receive(client,tmp_path,token,path,identity,user,amk)==['applied']
    assert totals(a)==totals(b);assert totals(a)[:2]==pytest.approx((140.0,14.0))
    for path,identity in ((a,ia),(b,ib)):
        day=progress(tmp_path,path,identity,user,'writing_day')
        with sqlite3.connect(path) as db:
            payload=json.loads(db.execute('SELECT payload_json FROM projects').fetchone()[0])
            assert payload['remaining']==860
            assert payload['added_today']==sum(e['added_symbols'] for e in totals(path)[2] if e['writing_day']==day)
            assert all(e['added_progress']==pytest.approx(e['added_symbols']/10) for e in totals(path)[2])

    for path,identity in ((a,ia),(b,ib)):
        with sqlite3.connect(path) as db:
            assert db.execute("SELECT count(*) FROM domain_events WHERE event_type='ProgressAdded'").fetchone()[0]==0
            assert db.execute('SELECT count(*) FROM cloud_progress_events').fetchone()[0]==6
        ack=progress(tmp_path,path,identity,user,'ack');assert ack['candidate_cursor']>0
    with sqlite3.connect(b) as db:
        register_remote_apply_authorization_guard(db)
        db.execute('DROP TRIGGER projects_progress_projection_guard');db.execute("UPDATE projects SET payload_json=json_set(payload_json,'$.total',999)")
    assert progress(tmp_path,b,ib,user,'rebuild') is True;assert totals(a)==totals(b)
    with engine.connect() as db:
        assert db.execute(text("SELECT count(*) FROM sync_events WHERE entity_type='progress'")).scalar()==6
        columns=[r[0] for r in db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='sync_events'"))]
        assert not set(['new_total','delta','unit','writing_day']).intersection(columns)

    # Activate the Stage metadata model through its ordinary authenticated writer.
    with sqlite3.connect(a) as db:proposed=json.loads(db.execute('SELECT payload_json FROM projects').fetchone()[0])
    proposed['stages_enabled']=True
    native(tmp_path,a,ia,user,'normal_edit',proposed=proposed);meta,_=publish(client,tmp_path,token,a,ia,user,amk)
    for path,identity in ((a,ia),(b,ib)):assert sync(client,tmp_path,token,path,identity,user,amk)['view']['state']=='active'
    # A Stage has its own genesis/head; root progress is never reused as its base.
    from test_cloud_c18_structural_cross_runtime import event,structural,structural_publish,structural_sync
    e=event(ia,user,boot,meta['header']['event_id'],entity='S1');stage=e['stage'];stage.update(unit='symbols',goal=1000,infinite=False,work_method='manual')
    with sqlite3.connect(a) as db:
        register_remote_apply_authorization_guard(db)
        db.execute('INSERT INTO stages(id,project_id,name,goal,infinite,unit,status,created_at,payload_json) VALUES(?,?,?,?,?,?,?,?,?)',('S1',PROJECT_ID,stage['name'],1000,0,'symbols',stage['status'],stage['created_at'],json.dumps({**stage,'total':50,'progress_entries':[]})))
        db.execute('INSERT INTO stage_order VALUES(?,?,0)',('S1',PROJECT_ID))
    structural(tmp_path,a,ia,user,'capture',stage_id='S1');structural_publish(client,tmp_path,token,a,ia,user,amk,e)
    for path,identity in ((a,ia),(b,ib)):structural_sync(client,tmp_path,token,path,identity,user,amk)
    order=event(ia,user,boot,meta['header']['event_id'],order=['S1'],heads={'S1':[e['header']['event_id']]});structural_publish(client,tmp_path,token,a,ia,user,amk,order)
    for path,identity in ((a,ia),(b,ib)):structural_sync(client,tmp_path,token,path,identity,user,amk)
    with sqlite3.connect(b) as db:
        register_remote_apply_authorization_guard(db);db.execute("UPDATE stages SET payload_json=json_set(payload_json,'$.total',0,'$.progress_entries',json('[]')) WHERE id='S1'")
    result=progress(tmp_path,a,ia,user,'begin');assert any(o['stage_id']=='S1' for o in result['owners'])
    emit(client,tmp_path,token,a,ia,user,amk)
    for path,identity in ((a,ia),(b,ib)):assert receive(client,tmp_path,token,path,identity,user,amk)==['applied']
    o=next(o for o in progress(tmp_path,a,ia,user,'view')['owners'] if o['stage_id']=='S1');stage_head=o['tips']
    result=progress(tmp_path,a,ia,user,'manual',stage_id='S1',total=60,expected=stage_head);assert 'error' not in result,result
    assert progress(tmp_path,a,ia,user,'manual',stage_id='S1',total=70,expected=stage_head)['error']=='progress_expected_head_stale'
    emit(client,tmp_path,token,a,ia,user,amk)
    for path,identity in ((a,ia),(b,ib)):assert receive(client,tmp_path,token,path,identity,user,amk)==['applied']
    assert totals(a)==totals(b);assert totals(a)[0]==60
    with sqlite3.connect(a) as db:assert db.execute("SELECT count(*) FROM domain_events WHERE event_type='ProgressAdded'").fetchone()[0]==1
    with sqlite3.connect(b) as db:assert db.execute("SELECT count(*) FROM domain_events WHERE event_type='ProgressAdded'").fetchone()[0]==0
    with sqlite3.connect(a) as db:stage_proposed=json.loads(db.execute("SELECT payload_json FROM stages WHERE id='S1'").fetchone()[0])
    stage_proposed['work_method']='app';assert structural(tmp_path,a,ia,user,'edit',stage_id='S1',proposed=stage_proposed)
    from test_cloud_c18_structural_integration import publish_pending,pull_structure
    publish_pending(client,tmp_path,token,a,ia,user,amk)
    for path,identity in ((a,ia),(b,ib)):pull_structure(client,tmp_path,token,path,identity,user,amk)
    from test_cloud_c18_document_acceptance import document,content
    for path,identity in ((a,ia),(b,ib)):document(tmp_path,path,identity,user,'init')
    saved=document(tmp_path,a,ia,user,'save',stage_id='S1',content=content('x'*90));assert 'error' not in saved,saved
    recorded=progress(tmp_path,a,ia,user,'document_progress',stage_id='S1');assert recorded.get('changed') is True,recorded
    assert progress(tmp_path,a,ia,user,'document_progress',stage_id='S1')['changed'] is False
    assert len(progress(tmp_path,a,ia,user,'pending'))==1
    emit(client,tmp_path,token,a,ia,user,amk)
    for path,identity in ((a,ia),(b,ib)):assert receive(client,tmp_path,token,path,identity,user,amk)==['applied']
    assert totals(a)==totals(b);assert totals(a)[0]==90
    # Real external Word writer reuses the same causal writer and durable source dedup.
    with sqlite3.connect(a) as db:stage_proposed=json.loads(db.execute("SELECT payload_json FROM stages WHERE id='S1'").fetchone()[0])
    stage_proposed['work_method']='sync';assert structural(tmp_path,a,ia,user,'edit',stage_id='S1',proposed=stage_proposed)
    publish_pending(client,tmp_path,token,a,ia,user,amk)
    for path,identity in ((a,ia),(b,ib)):pull_structure(client,tmp_path,token,path,identity,user,amk)
    import zipfile
    external=tmp_path/'isolated-external.docx'
    with zipfile.ZipFile(external,'w') as z:z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>'+('y'*100)+'</w:t></w:r></w:p></w:body></w:document>')
    with sqlite3.connect(a) as db:
        db.execute("INSERT INTO document_bindings(id,document_id,binding_type,external_path,last_synced_revision,sync_state,payload_json) VALUES(?, ?, 'word', ?, (SELECT revision FROM documents WHERE id=?), 'external_changed', '{}')",('isolated-progress-binding',saved['document_id'],str(external),saved['document_id']))
    result=progress(tmp_path,a,ia,user,'external_sync',stage_id='S1');assert result.get('changed') is True,result
    assert progress(tmp_path,a,ia,user,'external_sync',stage_id='S1')['changed'] is False
    assert len(progress(tmp_path,a,ia,user,'pending'))==1
    emit(client,tmp_path,token,a,ia,user,amk)
    for path,identity in ((a,ia),(b,ib)):assert receive(client,tmp_path,token,path,identity,user,amk)==['applied']
    assert totals(a)==totals(b);assert totals(a)[0]==100;assert external.exists()
    for path,identity in ((a,ia),(b,ib)):
        day=progress(tmp_path,path,identity,user,'writing_day')
        with sqlite3.connect(path) as db:
            p=json.loads(db.execute('SELECT payload_json FROM projects').fetchone()[0]);s=json.loads(db.execute("SELECT payload_json FROM stages WHERE id='S1'").fetchone()[0])
            assert p['remaining']==s['remaining']==900 and p['progress']==s['progress']==10
            assert p['added_today']==s['added_today']==sum(e['added_symbols'] for e in s['progress_entries'] if e['writing_day']==day)

    with sqlite3.connect(a) as db:assert db.execute("SELECT count(*) FROM domain_events WHERE event_type='ProgressAdded'").fetchone()[0]==3
    with sqlite3.connect(b) as db:assert db.execute("SELECT count(*) FROM domain_events WHERE event_type='ProgressAdded'").fetchone()[0]==0
    with sqlite3.connect(a) as db:stage_proposed=json.loads(db.execute("SELECT payload_json FROM stages WHERE id='S1'").fetchone()[0])
    stage_proposed['work_method']='app';assert structural(tmp_path,a,ia,user,'edit',stage_id='S1',proposed=stage_proposed)
    publish_pending(client,tmp_path,token,a,ia,user,amk)
    for path,identity in ((a,ia),(b,ib)):pull_structure(client,tmp_path,token,path,identity,user,amk)
    # Missing parent at N retains bytes and blocks the prefix while Document N+1 applies.
    import copy
    pending_owner=next(o for o in progress(tmp_path,a,ia,user,'view')['owners'] if o['stage_id']=='S1')
    with sqlite3.connect(a) as db:
        parent=json.loads(bytes(db.execute('SELECT canonical_frame FROM cloud_progress_events WHERE event_id=?',(pending_owner['tips'][0],)).fetchone()[0])[20:])
    def next_event(parent,total):
        e=copy.deepcopy(parent);e['header'].update(event_id=str(uuid4()),parents=[parent['header']['event_id']],operation='append',revision=parent['header']['revision']+1,generation=parent['header']['generation']+1)
        e.update(migration=None,base_total=None,selected_event_id=parent['header']['event_id'],target_entry_id=None,rebased_from=[])
        f=copy.deepcopy(parent['entries'][-1]);f.update(entry_id=str(uuid4()),new_total=f'{total}.000000',delta='10.000000');e['entries']=[f];return e
    d=next_event(parent,110);child=next_event(d,120)
    def push_event(e):
        sealed=_crypto_bridge(tmp_path,dict(action='progress_event_seal',payload=e,amk=amk));h=e['header'];wire={k:h[k] for k in ('event_id','project_id','entity_id','revision','updated_at')};wire.update(entity_type='progress',operation='event',deleted_at=None)
        r=client.post('/api/v3/sync/encrypted/push',headers=headers,json=dict(protocol_version=3,encrypted_sync_version=3,device_id=ia['device_id'],items=[dict(event=wire,object=sealed['object'])]));assert r.status_code==200,r.text;return r.json()['results'][0]['server_sequence']
    blocked_seq=push_event(child)
    assert receive(client,tmp_path,token,b,ib,user,amk)==['waiting']
    from test_cloud_c18_document_acceptance import document,content,emit as emit_document,receive as receive_document
    for path,identity in ((a,ia),(b,ib)):document(tmp_path,path,identity,user,'init')
    saved=document(tmp_path,a,ia,user,'save',stage_id='S1',content=content('Independent document'));assert 'error' not in saved,saved
    document(tmp_path,a,ia,user,'begin');emit_document(client,tmp_path,token,a,ia,user,amk)
    assert receive_document(client,tmp_path,token,b,ib,user,amk)==['applied']
    assert progress(tmp_path,b,ib,user,'ack')['candidate_cursor']<blocked_seq
    push_event(d);assert receive(client,tmp_path,token,b,ib,user,amk)==['applied']
    with sqlite3.connect(b) as db:
        register_remote_apply_authorization_guard(db)
        assert db.execute('SELECT state FROM cloud_sync_inbox WHERE event_id=?',(child['header']['event_id'],)).fetchone()[0]=='orphan'
    # Retry retained authenticated bytes through the production native apply bridge.
    opened=_crypto_bridge(tmp_path,dict(action='progress_event_seal',payload=child,amk=amk))
    with sqlite3.connect(b) as db:
        nonce,cipher=db.execute('SELECT nonce,ciphertext FROM cloud_sync_event_objects WHERE event_id=?',(child['header']['event_id'],)).fetchone()
    assert progress(tmp_path,b,ib,user,'apply',frame=opened['frame'],nonce=list(nonce),ciphertext=list(cipher))=='applied'
    assert progress(tmp_path,b,ib,user,'ack')['candidate_cursor']>blocked_seq
