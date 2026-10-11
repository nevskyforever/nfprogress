"""One real account stream: three native files, production writers/AEAD/appliers.

This is orchestration of the existing headless bridges, not a second sync engine.
Every bridge invocation reopens its file; shared ACK comes only from native proof.
"""
import base64
import json
import sqlite3
from copy import deepcopy
from dataclasses import replace
from uuid import UUID

import pytest
from sqlalchemy import select, text
from backend.app.cloud.models import EncryptedBlob
from nfprogress.core.sqlite.connection import register_remote_apply_authorization_guard
from test_cloud_auth import cloud_client, migrated_database, create_user, login
from test_cloud_c15_headless_cross_runtime import PROJECT_ID, ROOT, _crypto_bridge, _native_bridge, _headers
from test_cloud_c16_bootstrap_cross_runtime import _note
from test_cloud_c18_authority_cross_runtime import provision, bootstrap, native, publish
from test_cloud_c18_structural_cross_runtime import event, structural, structural_publish
from test_cloud_c18_content_action_integration import retained, timestamp
from test_cloud_c18_content_note_acceptance import content as notes, emit as emit_notes
from test_cloud_c18_document_acceptance import document, content, heads, owner as doc_owner, choose
from test_cloud_c18_map_acceptance import maps, change, emit as emit_maps, stored as map_source
from test_cloud_c18_progress_acceptance import progress, support, emit as emit_progress
from test_cloud_c18_game_acceptance import game, command, emit_game, projections, NOW
from test_cloud_c18_game_gate import declaration as game_capability
from test_cloud_c18_cover_gate import declaration as cover_capability
from test_cloud_c18_cover_acceptance import cover, prepare, publish_cover, fetched, JPEG
from test_cloud_c18_catalog_integration import native as catalog, push as emit_catalog, decision as catalog_choice
from test_cloud_c18_compression_gate import declare, AUTHORIZE

SENTINEL = 'LOCAL_ONLY_C18_8_SENTINEL'
LOCAL_PROJECT = 'c188-local-project'
LEDGERS = ('cloud_sync_metadata_apply_ledger', 'cloud_sync_structural_apply_ledger',
           'cloud_content_note_receipts', 'cloud_map_apply_ledger',
           'cloud_document_apply_ledger', 'cloud_progress_apply_ledger',
           'cloud_game_apply_ledger', 'cloud_catalog_apply_ledger')
TIP_TABLES = ('cloud_sync_metadata_tips', 'cloud_sync_structural_tips', 'cloud_map_tips',
              'cloud_document_tips', 'cloud_progress_tips', 'cloud_game_tips', 'cloud_catalog_tips')


class CompleteProject:
    def __init__(self, client, engine, tmp):
        self.client, self.engine, self.tmp = client, engine, tmp
        client.app.state.runtime_config = replace(client.app.state.runtime_config, cloud_blob_dir=tmp/'blobs')
        self.user = str(create_user(engine)); self.token = login(client).json()['access_token']
        self.headers = _headers(self.token); self.amk = list(range(32)) # synthetic fixture key only
        self.devices = [provision(tmp, 'device-'+label, self.user, label == 'A') for label in 'ABC']
        self.a, self.b, self.c = self.devices
        assert len({p.resolve() for p, _ in self.devices}) == 3
        assert len({i['device_id'] for _, i in self.devices}) == 3
        self.requests = []; self.compression = []
        client.event_hooks['request'].append(self.no_http_leak)
        for path, identity in self.devices:
            assert client.put(f"/api/v1/sync/devices/{identity['device_id']}", headers=self.headers).status_code == 200
            document(tmp, path, identity, self.user, 'init'); game(tmp, path, identity, self.user, 'init')
            support(client, self.headers, identity['device_id'])
            for kind, body in [('game',game_capability(identity['device_id'])),('cover',cover_capability(identity['device_id']))]:
                assert client.put(f'/api/v3/sync/encrypted/{kind}-reader-capabilities', headers=self.headers, json=body).status_code == 204
            assert declare(client,self.headers,identity['device_id']).status_code == 204
        a, ia = self.a
        legacy = _note('legacy-html', 'Legacy HTML manuscript Note')
        with sqlite3.connect(a) as db:
            register_remote_apply_authorization_guard(db)
            db.execute("UPDATE projects SET name='Complete portable manuscript',goal=2000,infinite=0,payload_json=json_set(payload_json,'$.deadline','2026-12-31','$.personal_goal',400,'$.auto_freeze',json('true'),'$.stages_enabled',json('true'),'$.combine_stage_mindmaps',json('false'),'$.work_method','app','$.total',0,'$.progress_entries',json('[]'),'$.synch',json(?),'$.last_synch',?)", (json.dumps({'type':'Word','path':'/'+SENTINEL+'/source.docx','item_id':SENTINEL}), SENTINEL))
            db.execute('INSERT INTO notes(id,project_id,updated_at,payload_json) VALUES(?,?,?,?)', ('legacy-html',PROJECT_ID,legacy['updated_at'],json.dumps(legacy)))
            db.execute("INSERT INTO projects(id,name,infinite,unit,status,payload_json) VALUES(?, 'Local manuscript',1,'symbols','active','{}')",(LOCAL_PROJECT,))
            db.execute('INSERT INTO project_order VALUES(?,1)',(LOCAL_PROJECT,))
            db.execute('INSERT INTO project_bindings(id,project_id,binding_type,external_path,source_id,payload_json) VALUES(?,?,?,?,?,?)',('local-source',LOCAL_PROJECT,'Word','/'+SENTINEL+'/source.docx',SENTINEL,json.dumps({'path':SENTINEL})))
        self.boot = bootstrap(tmp,a,ia,'bootstrap_prepare')['bootstrap_id']
        assert client.post(f'/api/v1/cloud/projects/{PROJECT_ID}/bootstrap',headers=self.headers,json=dict(bootstrap_id=self.boot,device_id=ia['device_id'])).status_code == 200
        cohort = bootstrap(tmp,a,ia,'bootstrap_prepare_capture',bootstrap_id=self.boot,remote_high_water=0)
        assert len(cohort['events']) == 1
        e=cohort['events'][0]; wire={k:e[k] for k in ('event_id','project_id','entity_id','entity_type','operation','revision','updated_at','deleted_at')}
        sealed=self.crypto(action='seal',canonical_user_id=self.user,device_id=ia['device_id'],event=wire,note={k:v for k,v in e['note'].items() if k!='revision'})
        response=client.post('/api/v1/sync/encrypted/push',headers=self.headers,json=sealed['push']);assert response.status_code==200,response.text
        bootstrap(tmp,a,ia,'bootstrap_commit_upload',bootstrap_id=self.boot,accepted=[dict(event_id=e['event_id'],mutation_generation=e['mutation_generation'],object=sealed['push']['items'][0]['object'],server_sequence=response.json()['results'][0]['server_sequence'])])
        assert client.post(f'/api/v1/cloud/projects/{PROJECT_ID}/bootstrap/complete',headers=self.headers,json=dict(bootstrap_id=self.boot,device_id=ia['device_id'],initial_event_count=1,initial_max_server_sequence=1)).status_code==200
        bootstrap(tmp,a,ia,'bootstrap_confirm_active',bootstrap_id=self.boot,remote_high_water=1)
        assert client.post('/api/v2/sync/encrypted/cutover',headers=self.headers,json=dict(expected_cutover_epoch=0)).status_code==200
        for _, identity in self.devices:
            assert client.post('/api/v3/sync/encrypted/reader-ready',headers=self.headers,json=dict(device_id=identity['device_id'],reader_transport_version=3)).status_code==204
        assert client.post('/api/v3/sync/encrypted/cutover',headers=self.headers,json=dict(expected_cutover_epoch=1)).status_code==200
        native(tmp,a,ia,self.user,'begin'); self.metadata,_=publish(client,tmp,self.token,a,ia,self.user,self.amk)
        for path, identity in (self.b,self.c):
            bootstrap(tmp,path,identity,'bootstrap_import',bootstrap_id=self.boot,remote_high_water=2,display_name=self.metadata['metadata']['name'],authenticated_metadata=self.metadata['metadata'])
        self.converge(self.devices)

    def no_http_leak(self, request):
        assert SENTINEL.encode() not in request.content, 'Class C sentinel in HTTP request'
        self.requests.append((request.url.path,request.content))

    def crypto(self, **request):
        request['amk']=self.amk
        for name in ('frame','payload','note'):
            if name in request:
                raw=bytes(request[name]) if name=='frame' else json.dumps(request[name]).encode()
                assert SENTINEL.encode() not in raw, 'Class C sentinel before encryption'
        return _crypto_bridge(self.tmp,request)

    def native(self, device, action, **values):
        path, identity=device
        return _native_bridge(self.tmp,dict(action=action,database_path=str(path),local_account_id=identity['local_account_id'],device_id=identity['device_id'],canonical_user_id=self.user,project_id=PROJECT_ID,**values))

    def high(self):
        with self.engine.connect() as db:return db.execute(text('SELECT current_sequence FROM sync_user_state')).scalar_one()

    def pull(self, device):
        path, identity=device
        with sqlite3.connect(path) as db:cursor=db.execute('SELECT pull_cursor FROM cloud_sync_state').fetchone()[0]
        response=self.client.get('/api/v3/sync/encrypted/pull',headers=self.headers,params=dict(device_id=identity['device_id'],since=cursor,limit=100,protocol_version=3,encrypted_sync_version=3));assert response.status_code==200,response.text
        page=response.json();rows=[]
        for item in page['items']:
            row=dict(item['event']);row['source_device_id']=row.pop('device_id');row['envelope']=item['object']
            for key in ('updated_at','deleted_at'):
                if row.get(key):row[key]=timestamp(row[key])
            rows.append(row)
        assert game(self.tmp,path,identity,self.user,'receive',command=dict(account_id=identity['local_account_id'],device_id=identity['device_id'],canonical_user_id=self.user,expected_cursor=cursor,next_cursor=page['next_cursor'],has_more=page['has_more'],items=rows)) is True
        return page

    def apply(self, device):
        path, identity=device; outcomes=[]
        for item in retained(path,pending=True):
            e=item['event'];kind=e['entity_type']
            if kind=='project_game':continue
            if kind=='note' and e['entity_id']=='legacy-html':
                opened=self.crypto(action='open',canonical_user_id=self.user,item=item)
                result=game(self.tmp,path,identity,self.user,'note_apply',event=e,opened=opened)
            else:
                action=dict(project_metadata='metadata_open',stage='structural_open',stage_order='structural_open',note='content_note_open',map='map_open',document='document_open',progress='progress_open')[kind]
                opened=self.crypto(action=action,canonical_user_id=self.user,item=item)
                if kind=='project_metadata':
                    ref=opened['decoded']['metadata'].get('cover_reference')
                    if ref:
                        response=self.client.get(f"/api/v1/cloud/projects/{PROJECT_ID}/covers/{ref['blob_id']}",headers=self.headers)
                        if response.status_code==404:
                            cover(self.tmp,path,identity,self.user,'block',event_id=e['event_id'],reference=ref,code='cover_blob_missing');outcomes.append('cover_blob_missing');continue
                        material=fetched(self.client,self.headers,dict(reference=ref),self.tmp,self.amk,self.user)
                        assert cover(self.tmp,path,identity,self.user,'material',**material) is True
                    result=native(self.tmp,path,identity,self.user,'apply',opened=opened)['result']
                elif kind in ('stage','stage_order'):result=structural(self.tmp,path,identity,self.user,'apply',event_id=e['event_id'],opened=opened)
                elif kind=='note':result=game(self.tmp,path,identity,self.user,'content_note_apply',event=e,opened=opened)
                elif kind=='map':result=maps(self.tmp,path,identity,self.user,'apply',opened=opened)
                else:
                    fn=document if kind=='document' else progress
                    result=fn(self.tmp,path,identity,self.user,'apply',**{k:opened[k] for k in ('frame','nonce','ciphertext')})
            assert not isinstance(result,dict) or 'error' not in result,result
            outcomes.append(result)
        # Account catalog is retained in its existing account inbox, never a new cursor.
        with sqlite3.connect(path) as db:
            rows=db.execute("SELECT i.event_id,i.entity_id,i.entity_type,i.nonce,i.ciphertext FROM cloud_sync_account_inbox i LEFT JOIN cloud_catalog_apply_ledger l USING(account_id,event_id) WHERE i.entity_type!='account_game' AND l.event_id IS NULL ORDER BY i.server_sequence").fetchall()
        for id,entity,kind,nonce,cipher in rows:
            item=dict(event=dict(event_id=id,entity_id=entity,entity_type=kind),object=dict(crypto_version=2,aad_version=2,nonce=base64.urlsafe_b64encode(nonce).decode().rstrip('='),ciphertext=base64.urlsafe_b64encode(cipher).decode().rstrip('=')))
            opened=self.crypto(action='catalog_open',canonical_user_id=self.user,item=item)
            outcomes.append(catalog(self.tmp,path,identity,self.user,step='apply',event_id=id,opened=opened))
        for _ in range(2):
            for row in command(self.tmp,path,identity,self.user,'received',limit=32):
                account=row['scope']=='account'
                e=dict(event_id=row['event_id'],device_id=row['source_device_id'],entity_id=row['entity_id'],revision=row['revision'],updated_at=row['updated_at'],deleted_at=None,server_sequence=row['server_sequence'])
                e.update(dict(scope='account',canonical_user_id=self.user,entity_type='account_game',operation='upsert') if account else dict(project_id=PROJECT_ID,entity_type='project_game',operation='event'))
                item=dict(event=e,object=dict(crypto_version=2 if account else 1,aad_version=2 if account else 1,nonce=base64.urlsafe_b64encode(bytes(row['nonce'])).decode().rstrip('='),ciphertext=base64.urlsafe_b64encode(bytes(row['ciphertext'])).decode().rstrip('=')))
                opened=self.crypto(action='game_open',scope=row['scope'],canonical_user_id=self.user,item=item)
                outcomes.append(command(self.tmp,path,identity,self.user,'apply',project=not account,**{k:opened[k] for k in ('frame','nonce','ciphertext')}))
        return outcomes

    def ack(self, device, lost=False):
        path, identity=device
        proof=progress(self.tmp,path,identity,self.user,'ack')
        cursor=proof['candidate_cursor']
        for attempt in range(2 if lost else 1):
            if attempt:
                reopened=progress(self.tmp,path,identity,self.user,'ack')
                assert reopened==proof # actual file reopen after lost server response
            response=self.client.post('/api/v3/sync/encrypted/ack',headers=self.headers,json=dict(device_id=identity['device_id'],protocol_version=3,encrypted_sync_version=3,cursor=cursor));assert response.status_code==204,response.text
        result=self.native(device,'commit_ack',expected_old_ack_cursor=proof['current_ack_cursor'],acknowledged_cursor=cursor)
        assert result['ack_cursor']==cursor
        return cursor

    def converge(self, devices):
        for device in devices:
            self.pull(device);self.apply(device)
            self.ack(device)

    def emit_documents(self, device, lose=False):
        path, identity=device
        for item in document(self.tmp,path,identity,self.user,'pending'):
            h=item['event']['header']
            ready=self.client.post(AUTHORIZE,headers=self.headers,json=dict(device_id=identity['device_id'])).json()['ready'];assert ready is True
            sealed=self.crypto(action='document_seal',frame=item['frame'],compression_ready=ready)
            self.compression.append(sealed['frame'][11])
            document(self.tmp,path,identity,self.user,'seal',event_id=h['event_id'],frame=sealed['frame'],nonce=sealed['nonce'],ciphertext=sealed['ciphertext'])
        result=[]
        for item in document(self.tmp,path,identity,self.user,'pending',sealed=True):
            h=item['event']['header'];b64=lambda b:base64.urlsafe_b64encode(bytes(b)).decode().rstrip('=')
            obj=dict(crypto_version=1,aad_version=1,nonce=b64(item['nonce']),ciphertext=b64(item['ciphertext']))
            e={k:h[k] for k in ('event_id','project_id','entity_id','revision','updated_at')};e.update(entity_type='document',operation='event',deleted_at=None)
            body=dict(protocol_version=3,encrypted_sync_version=3,device_id=identity['device_id'],items=[dict(event=e,object=obj)])
            response=self.client.post('/api/v3/sync/encrypted/push',headers=self.headers,json=body);assert response.status_code==200,response.text
            if lose:
                assert item in document(self.tmp,path,identity,self.user,'pending',sealed=True)
            else:
                replay=self.client.post('/api/v3/sync/encrypted/push',headers=self.headers,json=body);assert replay.json()['results'][0]['duplicate']
                receipt=replay.json()['results'][0]
                document(self.tmp,path,identity,self.user,'receipt',event_id=h['event_id'],server_sequence=receipt['server_sequence'],duplicate=True)
            result.append(body)
        return result

    def seed(self):
        a,ia=self.a;meta=self.metadata['header']['event_id']
        stages=[]
        for id in ('S1','S2'):
            e=event(ia,self.user,self.boot,meta,entity=id);s=e['stage'];s.update(name='Stage '+id,work_method='app',infinite=True,goal=None)
            with sqlite3.connect(a) as db:
                register_remote_apply_authorization_guard(db)
                db.execute('INSERT INTO stages(id,project_id,name,infinite,unit,status,created_at,payload_json) VALUES(?,?,?,1,?,?,?,?)',(id,PROJECT_ID,s['name'],s['unit'],s['status'],s['created_at'],json.dumps({**s,'total':0,'progress_entries':[]})))
                db.execute('INSERT INTO stage_order VALUES(?,?,?)',(id,PROJECT_ID,len(stages)))
            structural(self.tmp,a,ia,self.user,'capture',stage_id=id)
            structural_publish(self.client,self.tmp,self.token,a,ia,self.user,self.amk,e);stages.append(e)
        self.converge(self.devices)
        e=event(ia,self.user,self.boot,meta,order=['S1','S2'],heads={e['header']['entity_id']:[e['header']['event_id']] for e in stages})
        structural_publish(self.client,self.tmp,self.token,a,ia,self.user,self.amk,e);self.converge(self.devices)
        for id,stage,fmt in [('project-plain',None,'plain'),('stage-plain','S1','plain'),('stage-html','S1','html')]:
            notes(self.tmp,a,ia,self.user,'create',note_id=id,stage_id=stage,content_format=fmt)
            notes(self.tmp,a,ia,self.user,'edit',note_id=id,stage_id=stage,patch=dict(content='<p>Stage HTML body</p>' if fmt=='html' else 'Portable '+id))
        fixture=json.loads((ROOT/'frontend/src/cloud/__fixtures__/mapCodecV1.json').read_text())['examples'][2]['event']['map']['data']
        for stage in (None,'S1'):
            data=json.loads(json.dumps(fixture).replace('root-1','stage-root' if stage else 'root-1').replace('note-1','stage-node' if stage else 'note-1'))
            assert change(self.tmp,a,ia,self.user,stage,data) is True
        with sqlite3.connect(a) as db:
            derived=db.execute("SELECT id FROM notes WHERE json_extract(payload_json,'$.source_type')='mindmap' AND json_extract(payload_json,'$.stage_id') IS NULL ORDER BY id LIMIT 1").fetchone()[0]
            count=db.execute("SELECT count(*) FROM cloud_sync_outbox WHERE entity_type='note'").fetchone()[0]
        maps(self.tmp,a,ia,self.user,'note_edit',note_id=derived,patch=dict(title='Integrated map annotation',tags=['continuity'],checklist=[dict(id='continuity',text='Check continuity',checked=True)],pinned=True))
        with sqlite3.connect(a) as db:assert db.execute("SELECT count(*) FROM cloud_sync_outbox WHERE entity_type='note'").fetchone()[0]==count
        self.doc=document(self.tmp,a,ia,self.user,'save',stage_id='S1',content=content('Complete portable manuscript paragraph. '*120))['document_id']
        self.stage_doc=document(self.tmp,a,ia,self.user,'save',stage_id='S2',content=content('Stage manuscript paragraph. '*80))['document_id']
        document(self.tmp,a,ia,self.user,'rename',stage_id='S1',title='Complete manuscript',expected=heads(self.tmp,a,ia,self.user,self.doc))
        with sqlite3.connect(a) as db:
            db.execute('INSERT INTO document_bindings(id,document_id,binding_type,external_path,source_id,sync_state,expected_external_hash,payload_json) VALUES(?,?,?,?,?,?,?,?)',('device-word',self.doc,'docx','/'+SENTINEL+'/book.docx',SENTINEL,'conflict',SENTINEL,json.dumps({'proposal':SENTINEL})))
            db.execute('INSERT INTO project_folders VALUES(?,?,?,?)',('F1','Portable writing folder',0,json.dumps({'id':'F1','name':'Portable writing folder'})))
            db.execute('INSERT INTO project_folder_members VALUES(?,?)',(PROJECT_ID,'F1'))
        for fn in (notes,maps,document,progress):fn(self.tmp,a,ia,self.user,'begin')
        emit_notes(self.client,self.tmp,self.token,a,ia,self.user,self.amk);emit_maps(self.client,self.tmp,self.token,a,ia,self.user,self.amk)
        first=self.emit_documents(self.a,lose=True); assert self.emit_documents(self.a)==first # reopen/exact retry, no reseal
        emit_progress(self.client,self.tmp,self.token,a,ia,self.user,self.amk)
        self.converge(self.devices)
        command(self.tmp,a,ia,self.user,'begin',now=NOW);emit_game(self.client,self.tmp,self.token,a,ia,self.user,self.amk,lose=True)
        self.converge(self.devices)
        for total in (50,80):
            o=next(o for o in progress(self.tmp,a,ia,self.user,'view')['owners'] if o['stage_id']=='S1')
            result=progress(self.tmp,a,ia,self.user,'manual',stage_id='S1',expected=o['tips'],total=total)
            assert 'entry' in result,result
            emit_progress(self.client,self.tmp,self.token,a,ia,self.user,self.amk)
            game(self.tmp,a,ia,self.user,'process');emit_game(self.client,self.tmp,self.token,a,ia,self.user,self.amk)
            self.converge(self.devices)
        catalog(self.tmp,a,ia,self.user,step='begin')
        for _ in range(3):
            emit_catalog(self.tmp,self.client,self.token,a,ia,self.user,self.amk,lost=True);self.converge(self.devices)
        candidate=prepare(self.tmp,self.client,self.headers,a,ia,self.user,self.amk,initial=True)
        self.cover=candidate;publish_cover(self.client,self.tmp,self.headers,a,ia,self.user,self.amk)
        # Blob uploaded before reference; simulate temporary loss of availability.
        blob=UUID(candidate['reference']['blob_id'])
        with self.engine.begin() as db:
            stored=dict(db.execute(select(EncryptedBlob.__table__).where(EncryptedBlob.blob_id==blob)).mappings().one());db.execute(EncryptedBlob.__table__.delete().where(EncryptedBlob.blob_id==blob))
        self.pull(self.b);assert 'cover_blob_missing' in self.apply(self.b)
        seq=self.high();assert self.ack(self.b)==seq-1
        b,ib=self.b
        assert cover(self.tmp,b,ib,self.user,'status')['blockers']
        # A later safe child of already-proven metadata remains processable.
        notes(self.tmp,b,ib,self.user,'edit',note_id='project-plain',patch=dict(content='Safe Note beyond cover hole'))
        assert len(emit_notes(self.client,self.tmp,self.token,b,ib,self.user,self.amk))==1
        self.pull(self.b);self.apply(self.b);assert self.ack(self.b)==seq-1
        with sqlite3.connect(b) as db:
            assert json.loads(db.execute("SELECT payload_json FROM notes WHERE id='project-plain'").fetchone()[0])['content']=='Safe Note beyond cover hole'
            assert db.execute('SELECT state FROM cloud_sync_inbox WHERE server_sequence=?',(seq,)).fetchone()[0]!='applied'
        with self.engine.begin() as db:db.execute(EncryptedBlob.__table__.insert().values(**stored))
        self.converge(self.devices)
        assert self.ack(self.b,lost=True)==self.high()

    def snapshot(self, device):
        path,identity=device;result={}
        with sqlite3.connect(path) as db:
            assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
            for table in LEDGERS:
                cols=[r[1] for r in db.execute('PRAGMA table_info('+table+')')]
                assert cols,table
                selected=[c for c in ('event_id','canonical_frame','canonical_payload') if c in cols]
                result[table]=db.execute('SELECT '+','.join(selected)+' FROM '+table+' ORDER BY event_id').fetchall()
            for table in ('cloud_sync_structural_events','cloud_map_events','cloud_document_events','cloud_progress_events','cloud_game_events','cloud_catalog_events'):
                result[table]=db.execute('SELECT event_id,canonical_frame FROM '+table+' ORDER BY event_id').fetchall()
            result['note_heads']=db.execute("SELECT entity_id,head_event_id,head_sync_revision FROM cloud_sync_entities WHERE entity_type='note' ORDER BY entity_id").fetchall()
            # A historical branch may be projected on one peer and preserved as
            # a conflict on another. Both need real native ACK proof; their
            # immutable canonical event/receipt bytes and final tips agree.
            result['inbox_proof']=db.execute("SELECT event_id,server_sequence,entity_type,CASE WHEN state IN ('applied','conflict','conflict_preserved') THEN 'proven' ELSE state END FROM cloud_sync_inbox ORDER BY server_sequence").fetchall()
            for table in TIP_TABLES:
                cols=[r[1] for r in db.execute('PRAGMA table_info('+table+')')]
                selected=[c for c in ('project_id','entity_type','entity_id','owner_key','event_id') if c in cols]
                result[table]=db.execute('SELECT '+','.join(selected)+' FROM '+table+' ORDER BY event_id').fetchall()
            result['cover']=db.execute('SELECT blob_id,reference_json,nonce,ciphertext,jpeg,remote_verified FROM cloud_cover_material ORDER BY blob_id').fetchall()
            result['metadata']=db.execute('SELECT event_id,payload_json,parent_event_ids_json,generation,revision,operation,deleted_at FROM cloud_sync_metadata_events ORDER BY event_id').fetchall()
            result['document']=db.execute('SELECT id,project_id,stage_id,title,content_json,extensions_json FROM documents ORDER BY id').fetchall()
            result['order']=db.execute('SELECT stage_id,position FROM stage_order ORDER BY position').fetchall()
            result['folders']=db.execute('SELECT id,name,position FROM project_folders ORDER BY id').fetchall()
            result['membership']=db.execute('SELECT project_id,folder_id FROM project_folder_members WHERE project_id=?',(PROJECT_ID,)).fetchall()
            result['notes']=[]
            for id,raw in db.execute('SELECT id,payload_json FROM notes ORDER BY id'):
                value=json.loads(raw);value.pop('revision',None)
                for k in ('created_at','updated_at'):
                    if value.get(k):value[k]=timestamp(value[k])
                result['notes'].append((id,value))
            result['progress']=db.execute('SELECT entity_id,snapshot_json FROM cloud_progress_projection ORDER BY entity_id').fetchall()
            result['rewards']=db.execute('SELECT reward_id,project_action_id,canonical_frame FROM cloud_game_rewards ORDER BY reward_id').fetchall()
            assert SENTINEL not in str(result) and LOCAL_PROJECT not in str(result),'Class C data entered portable history/projection'
        result['maps']=[map_source(path)['mindmap'],map_source(path,'S1')['mindmap']]
        result['game']=projections(path)
        return result

    def equal(self):
        snapshots=[self.snapshot(d) for d in self.devices]
        for name in snapshots[0]:assert snapshots[0][name]==snapshots[1][name]==snapshots[2][name],name
        for d in self.devices:assert self.ack(d)==self.high()
        return snapshots[0]

    def stored_history(self):
        with self.engine.connect() as db:return {str(id):(bytes(n),bytes(c)) for id,n,c in db.execute(text('SELECT event_id,nonce,ciphertext FROM encrypted_objects'))}

    def folder_conflict_evidence(self, path):
        # Read-only preservation proof when the account view is correctly
        # blocked by unresolved Project Metadata. Never a replacement applier.
        with sqlite3.connect(path) as db:
            return db.execute("SELECT t.event_id,e.canonical_frame FROM cloud_catalog_tips t JOIN cloud_catalog_events e USING(account_id,event_id) WHERE t.entity_type='folder' AND t.entity_id='F1' ORDER BY t.event_id").fetchall()


def test_complete_project_three_devices_all_authorities_and_causal_convergence(cloud_client,tmp_path):
    client,engine=cloud_client;h=CompleteProject(client,engine,tmp_path);h.seed()
    initial=h.equal();frozen=h.stored_history()
    assert any(n['title']=='Integrated map annotation' and n['checklist'][0]['checked'] for _,n in initial['notes'])
    assert 1 in h.compression # natural compression gate/threshold selection
    assert initial['cloud_sync_metadata_apply_ledger'] and initial['cloud_catalog_apply_ledger']
    assert len(initial['cover'])==1 and initial['cover'][0][-2:]==(JPEG,1)
    assert set(e['entity_type'] for e in catalog(tmp_path,h.a[0],h.a[1],h.user)['entities'])=={'folder','folder_order','folder_membership','project_order'}
    assert initial['rewards'] and {n[0] for n in initial['notes']} >= {'legacy-html','project-plain','stage-plain','stage-html'}
    with sqlite3.connect(h.a[0]) as db:
        frames=db.execute('SELECT canonical_frame FROM cloud_sync_structural_events').fetchall()
        assert frames and all(bytes(row[0])[11]==0 for row in frames)
        assert db.execute('SELECT count(*) FROM cloud_sync_project_bindings WHERE project_id=?',(LOCAL_PROJECT,)).fetchone()[0]==0
    offline_cursor=h.ack(h.c);active=(h.a,h.b)
    # Concurrent categories coexist. C remains at its durable old cursor.
    for device,label,total in ((h.a,'A',100),(h.b,'B',110)):
        path,identity=device
        assert 'error' not in document(tmp_path,path,identity,h.user,'save',stage_id='S1',content=content(label+' concurrent manuscript'),expected=heads(tmp_path,path,identity,h.user,h.doc))
        catalog(tmp_path,path,identity,h.user,step='normal',entity_type='folder',entity_id='F1',payload=dict(name='Concurrent folder '+label))
        o=next(o for o in progress(tmp_path,path,identity,h.user,'view')['owners'] if o['stage_id']=='S1')
        result=progress(tmp_path,path,identity,h.user,'manual',stage_id='S1',expected=o['tips'],total=total)
        assert 'entry' in result,result
        if label=='A':
            assert 'error' not in document(tmp_path,path,identity,h.user,'save',stage_id='S2',content=content('Surviving Stage manuscript'),expected=heads(tmp_path,path,identity,h.user,h.stage_doc))
        else:assert document(tmp_path,path,identity,h.user,'delete',document_id=h.stage_doc,expected=heads(tmp_path,path,identity,h.user,h.stage_doc)) is True
    for device in active:
        path,identity=device
        h.emit_documents(device)
        emit_catalog(tmp_path,client,h.token,path,identity,h.user,h.amk)
        emit_progress(client,tmp_path,h.token,path,identity,h.user,h.amk)
    # Preserve child conflicts while their Metadata authority is still proven.
    # Pending/conflicting Metadata deliberately blocks child apply/writers; it
    # must not be bypassed merely to manufacture simultaneous conflict tips.
    h.converge(active)
    catalog_evidence={}
    for path,identity in active:
        for id in (h.doc,h.stage_doc):
            owner=doc_owner(tmp_path,path,identity,h.user,id)
            assert owner['state']=='conflict' and len(owner['tips'])==2
        owner=next(o for o in progress(tmp_path,path,identity,h.user,'view')['owners'] if o['stage_id']=='S1')
        assert owner['state']=='conflict' and len(owner['tips'])==2
        assert catalog(tmp_path,path,identity,h.user)['state']=='conflict'
        catalog_evidence[path]=h.folder_conflict_evidence(path)
        assert len(catalog_evidence[path])==2
    for device,label in ((h.a,'A'),(h.b,'B')):
        path,identity=device
        proposed=native(tmp_path,path,identity,h.user,'read')['payload']
        proposed['name']='Concurrent complete project '+label;proposed['combine_stage_mindmaps']=True
        native(tmp_path,path,identity,h.user,'normal_edit',proposed=proposed)
        publish_cover(client,tmp_path,h.headers,path,identity,h.user,h.amk)
    h.converge(active)
    saved_conflicts={}
    for path,identity in active:
        m=native(tmp_path,path,identity,h.user,'read')['view'];assert m['state']=='metadata_conflict' and len(m['branches'])==2
        d=doc_owner(tmp_path,path,identity,h.user,h.doc);deleted=doc_owner(tmp_path,path,identity,h.user,h.stage_doc)
        assert len(d['tips'])==len(deleted['tips'])==2
        assert all(o['state']=='blocked' and o['blocker']=='project_metadata_authority_unresolved' for o in (d,deleted))
        assert {v['document'] is None for v in deleted['versions']}=={True,False}
        assert h.folder_conflict_evidence(path)==catalog_evidence[path]
        p=next(o for o in progress(tmp_path,path,identity,h.user,'view')['owners'] if o['stage_id']=='S1');assert p['state']=='conflict' and len(p['tips'])==2
        saved_conflicts[path]=(sorted(b['event_id'] for b in m['branches']),sorted(d['tips']),sorted(deleted['tips']),sorted(p['tips']))
        # Native complete conflict preservation is ACK-safe, not full convergence.
        assert h.ack((path,identity))==h.high()
    assert saved_conflicts[h.a[0]]==saved_conflicts[h.b[0]]
    a,ia=h.a
    metadata=native(tmp_path,a,ia,h.user,'read')['view']
    native(tmp_path,a,ia,h.user,'change',kind='choose_branch',selected=metadata['branches'][0]['event_id'])
    resolution=publish_cover(client,tmp_path,h.headers,a,ia,h.user,h.amk)
    assert sorted(resolution['header']['parent_event_ids'])==saved_conflicts[a][0]
    h.converge(active)
    assert sorted(doc_owner(tmp_path,a,ia,h.user,h.doc)['tips'])==saved_conflicts[a][1]
    assert all(doc_owner(tmp_path,a,ia,h.user,id)['state']=='conflict' for id in (h.doc,h.stage_doc))
    assert catalog(tmp_path,a,ia,h.user)['state']=='conflict'
    assert h.folder_conflict_evidence(a)==catalog_evidence[a]
    for id in (h.doc,h.stage_doc):
        o=doc_owner(tmp_path,a,ia,h.user,id)
        selected=next(v['event_id'] for v in o['versions'] if v['document'] is not None)
        resolution_id=choose(tmp_path,a,ia,h.user,id,selected);assert isinstance(resolution_id,str)
        with sqlite3.connect(a) as db:assert json.loads(db.execute('SELECT parents_json FROM cloud_document_events WHERE event_id=?',(resolution_id,)).fetchone()[0])==sorted(o['tips'])
    h.emit_documents(h.a)
    folder=next(e for e in catalog(tmp_path,a,ia,h.user)['entities'] if e['entity_type']=='folder' and e['entity_id']=='F1')
    catalog_choice(tmp_path,a,ia,h.user,'folder','F1',selected=folder['tips'][0]);emit_catalog(tmp_path,client,h.token,a,ia,h.user,h.amk)
    p=next(o for o in progress(tmp_path,a,ia,h.user,'view')['owners'] if o['stage_id']=='S1')
    selected=next(v for v in p['versions'] if float(v['chain']['entries'][-1]['new_total'])==100)
    other=next(v for v in p['versions'] if v['event_id']!=selected['event_id'])
    rebased=[e['entry_id'] for e in other['chain']['entries'] if e['entry_id'] not in {e['entry_id'] for e in selected['chain']['entries']}]
    assert isinstance(progress(tmp_path,a,ia,h.user,'decide',decision=dict(project_id=PROJECT_ID,stage_id='S1',expected_tips=p['tips'],expected_local=p['local'],selected_event_id=selected['event_id'],operation='rebase',target_entry_id=None,rebased_from=rebased,corrected_delta=None)),str)
    emit_progress(client,tmp_path,h.token,a,ia,h.user,h.amk);h.converge(active)
    # Ordinary edits descend from explicit resolutions/current tips on A and B.
    for device,label in ((h.a,'A'),(h.b,'B')):
        path,identity=device
        before=heads(tmp_path,path,identity,h.user,h.doc)
        assert 'error' not in document(tmp_path,path,identity,h.user,'save',stage_id='S1',content=content('Post-resolution '+label+' manuscript. '*80),expected=before)
        pending=document(tmp_path,path,identity,h.user,'pending');assert pending[0]['event']['header']['parents']==before['tips']
        h.emit_documents(device);h.converge(active)
    b,ib=h.b
    notes(tmp_path,b,ib,h.user,'delete',note_id='project-plain');emit_notes(client,tmp_path,h.token,b,ib,h.user,h.amk)
    assert document(tmp_path,b,ib,h.user,'delete',document_id=h.stage_doc,expected=heads(tmp_path,b,ib,h.user,h.stage_doc)) is True
    h.emit_documents(h.b)
    catalog(tmp_path,b,ib,h.user,step='normal',entity_type='folder_membership',entity_id=PROJECT_ID,payload=dict(folder_id=None));emit_catalog(tmp_path,client,h.token,b,ib,h.user,h.amk)
    h.converge(active)
    proposed=native(tmp_path,b,ib,h.user,'read')['payload'];proposed['cover_image']=None
    native(tmp_path,b,ib,h.user,'normal_edit',proposed=proposed)
    intent=cover(tmp_path,b,ib,h.user,'pending')['intent_id']
    assert cover(tmp_path,b,ib,h.user,'seal',intent_id=intent,reference=None) is True
    cover(tmp_path,b,ib,h.user,'prepare',intent_id=intent)
    publish_cover(client,tmp_path,h.headers,b,ib,h.user,h.amk)
    h.converge(active)
    # A structural mutation preserves parent/children/order identities.
    stage=h.native(h.b,'structural',step='authority')['entities']
    s=next(e for e in stage if e['entity_id']=='S1')['local'];s['name']='Accepted Stage continuation'
    structural(tmp_path,b,ib,h.user,'edit',stage_id='S1',proposed=s)
    from test_cloud_c18_structural_integration import publish_pending
    publish_pending(client,tmp_path,h.token,b,ib,h.user,h.amk)
    h.converge(active)
    with sqlite3.connect(h.c[0]) as db:assert db.execute('SELECT ack_cursor FROM cloud_sync_state').fetchone()[0]==offline_cursor
    h.converge((h.c,));final=h.equal()
    assert all(n[0]!='project-plain' for n in final['notes'])
    assert all(d[0]!=h.stage_doc for d in final['document'])
    assert final['membership']==[]
    for path,identity in h.devices:
        assert native(tmp_path,path,identity,h.user,'read')['view']['state']=='active'
        assert all(o['state']=='active' for o in document(tmp_path,path,identity,h.user,'view')['owners'])
        assert all(o['state']=='active' for o in progress(tmp_path,path,identity,h.user,'view')['owners'])
        assert catalog(tmp_path,path,identity,h.user)['state']=='active'
        assert cover(tmp_path,path,identity,h.user,'status')['blockers']==[]
        with sqlite3.connect(path) as db:
            assert json.loads(db.execute('SELECT payload_json FROM projects WHERE id=?',(PROJECT_ID,)).fetchone()[0]).get('cover_image') is None
            assert db.execute('SELECT count(*) FROM cloud_game_rewards').fetchone()[0]==len(initial['rewards'])
            assert db.execute("SELECT count(*) FROM cloud_sync_inbox WHERE state NOT IN ('applied','conflict','conflict_preserved')").fetchone()[0]==0
            if path!=a:
                assert db.execute('SELECT count(*) FROM document_bindings').fetchone()[0]==0
                assert db.execute('SELECT count(*) FROM project_bindings').fetchone()[0]==0
                assert db.execute('SELECT count(*) FROM projects WHERE id=?',(LOCAL_PROJECT,)).fetchone()[0]==0
    after=h.stored_history();assert all(after[id]==obj for id,obj in frozen.items())
    with engine.connect() as db:
        assert db.execute(text('SELECT count(*) FROM encrypted_blobs')).scalar_one()==1
        assert db.execute(text('SELECT last_ack_sequence FROM sync_devices ORDER BY device_id')).scalars().all()==[h.high()]*3
        assert db.execute(text('SELECT count(*) FROM cloud_projects')).scalar_one()==1
        for table in ('encrypted_objects','sync_events','sync_devices','cloud_projects','encrypted_blobs'):
            rows=db.execute(text('SELECT row_to_json(t)::text FROM '+table+' t')).scalars().all()
            assert not any(SENTINEL in r or 'Complete portable manuscript' in r or 'portable manuscript paragraph' in r for r in rows)
    for path,identity in h.devices:
        before=h.snapshot((path,identity));h.converge(((path,identity),));assert h.snapshot((path,identity))==before
    # Account ciphertext cannot be authenticated in a project crypto/AAD scope.
    page=client.get('/api/v3/sync/encrypted/pull',headers=h.headers,params=dict(device_id=ia['device_id'],since=0,limit=100,protocol_version=3,encrypted_sync_version=3)).json()
    account=next(i for i in page['items'] if i['event']['entity_type']=='folder')
    wrong=deepcopy(account);wrong['event'].update(project_id=PROJECT_ID,entity_id=PROJECT_ID)
    with pytest.raises(AssertionError,match='crypto bridge failed'):
        h.crypto(action='metadata_open',canonical_user_id=h.user,item=wrong)
    assert all(SENTINEL.encode() not in body for _,body in h.requests)


def test_complete_project_unsupported_document_extension_retained_blocks_ack(cloud_client,tmp_path):
    client,engine=cloud_client;h=CompleteProject(client,engine,tmp_path)
    a,ia=h.a;b,ib=h.b
    id=document(tmp_path,a,ia,h.user,'save',content=content('Supported content for negative complete-project case'))['document_id']
    with sqlite3.connect(a) as source,sqlite3.connect(b) as target:
        register_remote_apply_authorization_guard(target)
        row=source.execute('SELECT id,scope_key,project_id,title,content_json,content_format,created_at,updated_at FROM documents WHERE id=?',(id,)).fetchone()
        target.execute('INSERT INTO documents(id,scope_key,project_id,title,content_json,content_format,created_at,updated_at,extensions_json) VALUES(?,?,?,?,?,?,?,?,?)',(*row,json.dumps({'deferred_F':'UNSUPPORTED_C188_BYTES'})))
    document(tmp_path,a,ia,h.user,'begin');h.emit_documents(h.a)
    h.pull(h.b);high=h.high();h.apply(h.b)
    for _ in range(2):
        view=document(tmp_path,b,ib,h.user,'view');assert any(o['state']=='blocked' for o in view['owners'])
        assert 'document_unsupported_extension' in json.dumps(view)
        assert h.ack(h.b)<high
        with sqlite3.connect(b) as db:
            assert json.loads(db.execute('SELECT extensions_json FROM documents WHERE id=?',(id,)).fetchone()[0])=={'deferred_F':'UNSUPPORTED_C188_BYTES'}
            assert db.execute('SELECT count(*) FROM cloud_document_apply_ledger').fetchone()[0]==0
            assert db.execute('SELECT state FROM cloud_sync_inbox WHERE server_sequence=?',(high,)).fetchone()[0]=='orphan'
        h.apply(h.b) # durable reopened retry cannot turn an incomplete copy into proof
