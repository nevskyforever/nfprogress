"""Production TS cover crypto + PostgreSQL cover API + two file-backed native databases."""
import base64
import json
import os
import sqlite3
from uuid import uuid4
from datetime import datetime, timezone
from dataclasses import replace

from sqlalchemy import text, select
from backend.app.cloud.models import EncryptedBlob
from nfprogress.core.sqlite.connection import register_remote_apply_authorization_guard
from test_cloud_auth import cloud_client, migrated_database, create_user, login
from test_cloud_c18_authority_cross_runtime import provision, bootstrap, native, publish, sync
from test_cloud_c15_headless_cross_runtime import PROJECT_ID, _crypto_bridge, _native_bridge, _headers
from test_cloud_c18_cover_gate import declaration

JPEG = base64.b64decode("/9j/4AAQSkZJRgABAQAAGQAZAAD/4QCARXhpZgAATU0AKgAAAAgABAEaAAUAAAABAAAAPgEbAAUAAAABAAAARgEoAAMAAAABAAIAAIdpAAQAAAABAAAATgAAAAAAAAAZAAAAAQAAABkAAAABAAOgAQADAAAAAQABAACgAgAEAAAAAQAAAASgAwAEAAAAAQAAAAQAAAAA/+0AOFBob3Rvc2hvcCAzLjAAOEJJTQQEAAAAAAAAOEJJTQQlAAAAAAAQ1B2M2Y8AsgTpgAmY7PhCfv/AABEIAAQABAMBIgACEQEDEQH/xAAfAAABBQEBAQEBAQAAAAAAAAAAAQIDBAUGBwgJCgv/xAC1EAACAQMDAgQDBQUEBAAAAX0BAgMABBEFEiExQQYTUWEHInEUMoGRoQgjQrHBFVLR8CQzYnKCCQoWFxgZGiUmJygpKjQ1Njc4OTpDREVGR0hJSlNUVVZXWFlaY2RlZmdoaWpzdHV2d3h5eoOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4eLj5OXm5+jp6vHy8/T19vf4+fr/xAAfAQADAQEBAQEBAQEBAAAAAAAAAQIDBAUGBwgJCgv/xAC1EQACAQIEBAMEBwUEBAABAncAAQIDEQQFITEGEkFRB2FxEyIygQgUQpGhscEJIzNS8BVictEKFiQ04SXxFxgZGiYnKCkqNTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqCg4SFhoeIiYqSk5SVlpeYmZqio6Slpqeoqaqys7S1tre4ubrCw8TFxsfIycrS09TV1tfY2dri4+Tl5ufo6ery8/T19vf4+fr/2wBDAAICAgICAgMCAgMFAwMDBQYFBQUFBggGBgYGBggKCAgICAgICgoKCgoKCgoMDAwMDAwODg4ODg8PDw8PDw8PDw//2wBDAQICAgQEBAcEBAcQCwkLEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBD/3QAEAAH/2gAMAwEAAhEDEQA/AP3UooorjND/2Q==")


JPEG2 = base64.b64decode('/9j/4AAQSkZJRgABAQAAGQAZAAD/4QCARXhpZgAATU0AKgAAAAgABAEaAAUAAAABAAAAPgEbAAUAAAABAAAARgEoAAMAAAABAAIAAIdpAAQAAAABAAAATgAAAAAAAAAZAAAAAQAAABkAAAABAAOgAQADAAAAAQABAACgAgAEAAAAAQAAAASgAwAEAAAAAQAAAAQAAAAA/+0AOFBob3Rvc2hvcCAzLjAAOEJJTQQEAAAAAAAAOEJJTQQlAAAAAAAQ1B2M2Y8AsgTpgAmY7PhCfv/AABEIAAQABAMBIgACEQEDEQH/xAAfAAABBQEBAQEBAQAAAAAAAAAAAQIDBAUGBwgJCgv/xAC1EAACAQMDAgQDBQUEBAAAAX0BAgMABBEFEiExQQYTUWEHInEUMoGRoQgjQrHBFVLR8CQzYnKCCQoWFxgZGiUmJygpKjQ1Njc4OTpDREVGR0hJSlNUVVZXWFlaY2RlZmdoaWpzdHV2d3h5eoOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4eLj5OXm5+jp6vHy8/T19vf4+fr/xAAfAQADAQEBAQEBAQEBAAAAAAAAAQIDBAUGBwgJCgv/xAC1EQACAQIEBAMEBwUEBAABAncAAQIDEQQFITEGEkFRB2FxEyIygQgUQpGhscEJIzNS8BVictEKFiQ04SXxFxgZGiYnKCkqNTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqCg4SFhoeIiYqSk5SVlpeYmZqio6Slpqeoqaqys7S1tre4ubrCw8TFxsfIycrS09TV1tfY2dri4+Tl5ufo6ery8/T19vf4+fr/2wBDAAICAgICAgMCAgMFAwMDBQYFBQUFBggGBgYGBggKCAgICAgICgoKCgoKCgoMDAwMDAwODg4ODg8PDw8PDw8PDw//2wBDAQICAgQEBAcEBAcQCwkLEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBD/3QAEAAH/2gAMAwEAAhEDEQA/APxnooooOc//2Q==')


def cover(tmp, path, identity, user, step, **data):
    return _native_bridge(tmp, dict(action='cover', database_path=str(path),
        local_account_id=identity['local_account_id'], device_id=identity['device_id'],
        canonical_user_id=user, project_id=PROJECT_ID, step=step, data=data))


def upload(client, headers, candidate):
    ref = candidate['reference']
    url = f"/api/v1/cloud/projects/{PROJECT_ID}/covers/{ref['blob_id']}"
    h = {**headers, 'Content-Type': 'application/octet-stream',
         'X-WORTA-Crypto-Version': '1', 'X-WORTA-AAD-Version': '1',
         'X-WORTA-Nonce': candidate['object']['nonce']}
    response = client.put(url, headers=h, content=bytes(candidate['ciphertext']))
    assert response.status_code == 200, response.text
    replay = client.put(url, headers=h, content=bytes(candidate['ciphertext']))
    assert replay.status_code == 200 and replay.json()['duplicate'] is True, replay.text
    assert {k:v for k,v in replay.json().items() if k!='duplicate'} == {k:v for k,v in response.json().items() if k!='duplicate'}
    changed = bytearray(candidate['ciphertext']); changed[0] ^= 1
    denied = client.put(url, headers=h, content=bytes(changed))
    assert denied.status_code == 409 and denied.json()['detail']['code'] == 'encrypted_blob_id_conflict'
    return url


def fetched(client, headers, candidate, tmp, amk, user):
    ref = candidate['reference']
    response = client.get(f"/api/v1/cloud/projects/{PROJECT_ID}/covers/{ref['blob_id']}", headers=headers)
    assert response.status_code == 200, response.text
    obj = dict(crypto_version=int(response.headers['X-WORTA-Crypto-Version']),
               aad_version=int(response.headers['X-WORTA-AAD-Version']),
               nonce=response.headers['X-WORTA-Nonce'],
               ciphertext=base64.urlsafe_b64encode(response.content).decode().rstrip('='))
    opened = _crypto_bridge(tmp, dict(action='cover_open', amk=amk,
        identity=dict(userId=user, projectId=PROJECT_ID, blobId=ref['blob_id']), reference=ref, object=obj))
    assert bytes(opened['jpeg']) in (JPEG,JPEG2)
    return opened


def prepare(tmp, client, headers, path, identity, user, amk, initial=False, remove=False, jpeg=JPEG, name=None):
    source = None if remove else 'data:image/jpeg;base64,' + base64.b64encode(jpeg).decode()
    if initial:
        with sqlite3.connect(path) as db:
            register_remote_apply_authorization_guard(db)
            db.execute("UPDATE projects SET payload_json=json_set(payload_json,'$.cover_image',?)", (source,))
        assert cover(tmp,path,identity,user,'pending') is None
        intent = cover(tmp,path,identity,user,'capture')
    else:
        proposed = native(tmp,path,identity,user,'read')['view']['local']
        proposed['cover_image'] = source
        if name is not None: proposed['name']=name
        native(tmp,path,identity,user,'normal_edit',proposed=proposed)
        intent = cover(tmp,path,identity,user,'pending')['intent_id']
    pending = cover(tmp,path,identity,user,'pending')
    assert pending['state'] == 'captured' and pending['source_cover'] == source
    if remove:
        candidate = dict(reference=None)
        assert cover(tmp,path,identity,user,'seal',intent_id=intent,**candidate) is True
    else:
        candidate = _crypto_bridge(tmp, dict(action='cover_seal', amk=amk,
            identity=dict(userId=user,projectId=PROJECT_ID,blobId=str(uuid4())),jpeg=list(jpeg)))
        assert cover(tmp,path,identity,user,'seal',intent_id=intent,**candidate) is True
        # Reopen before upload: exact sealed candidate remains recoverable.
        restarted = cover(tmp,path,identity,user,'pending')
        assert restarted['nonce'] == candidate['nonce'] and restarted['ciphertext'] == candidate['ciphertext']
        assert 'error' in cover(tmp,path,identity,user,'prepare',intent_id=intent)
        upload(client,headers,candidate)
        verified = fetched(client,headers,candidate,tmp,amk,user)
        assert cover(tmp,path,identity,user,'material',**verified) is True
        assert cover(tmp,path,identity,user,'uploaded',intent_id=intent) is True
    event_id = cover(tmp,path,identity,user,'prepare',intent_id=intent)
    assert cover(tmp,path,identity,user,'prepare',intent_id=intent) == event_id
    return candidate


def publish_cover(client,tmp,headers,path,identity,user,amk):
    event = native(tmp,path,identity,user,'read')['unsealed'][0]
    assert event['version'] == 2
    sealed = _crypto_bridge(tmp, dict(action='metadata_seal', payload=event, amk=amk))
    native(tmp,path,identity,user,'seal',event_id=event['header']['event_id'],
           nonce=sealed['nonce'],ciphertext=sealed['ciphertext'])
    h = event['header']
    wire = {k:h[k] for k in ('event_id','project_id','entity_id','revision','updated_at')}
    wire.update(entity_type='project_metadata',operation='upsert',deleted_at=None)
    request = dict(protocol_version=3, encrypted_sync_version=3, device_id=identity['device_id'],
                   items=[dict(event=wire,object=sealed['object'])])
    endpoint = '/api/v3/sync/encrypted/cover-metadata/push'
    first = client.post(endpoint,headers=headers,json=request)
    assert first.status_code == 200, first.text
    replay = client.post(endpoint,headers=headers,json=request)
    assert replay.status_code == 200 and replay.json()['results'][0]['duplicate']
    assert replay.json()['results'][0]['server_sequence'] == first.json()['results'][0]['server_sequence']
    return event


def sync_covers(client,tmp,headers,token,path,identity,user,amk):
    with sqlite3.connect(path) as db:
        cursor = db.execute('SELECT pull_cursor FROM cloud_sync_state').fetchone()[0]
    response = client.get('/api/v3/sync/encrypted/pull',headers=headers,params=dict(
        device_id=identity['device_id'],since=cursor,limit=100,protocol_version=3,encrypted_sync_version=3))
    assert response.status_code == 200, response.text
    for item in response.json()['items']:
        opened = _crypto_bridge(tmp,dict(action='metadata_open',canonical_user_id=user,amk=amk,item=item))
        ref = opened['decoded']['metadata'].get('cover_reference')
        if ref:
            material = fetched(client,headers,dict(reference=ref),tmp,amk,user)
            assert cover(tmp,path,identity,user,'material',**material) is True
    return sync(client,tmp,token,path,identity,user,amk)


def test_cover_explicit_migration_restart_replacement_remove_two_devices(cloud_client,tmp_path):
    client, engine = cloud_client
    client.app.state.runtime_config = replace(client.app.state.runtime_config,cloud_blob_dir=tmp_path/'encrypted-blobs')
    user = str(create_user(engine)); token = login(client).json()['access_token']; headers = _headers(token)
    a, ia = provision(tmp_path,'cover-A',user,True)
    b, ib = provision(tmp_path,'cover-B',user,False)
    for identity in (ia,ib):
        assert client.put(f"/api/v1/sync/devices/{identity['device_id']}",headers=headers).status_code == 200
    boot = bootstrap(tmp_path,a,ia,'bootstrap_prepare')['bootstrap_id']
    assert client.post(f'/api/v1/cloud/projects/{PROJECT_ID}/bootstrap',headers=headers,
        json=dict(bootstrap_id=boot,device_id=ia['device_id'])).status_code == 200
    bootstrap(tmp_path,a,ia,'bootstrap_prepare_capture',bootstrap_id=boot,remote_high_water=0)
    assert client.post(f'/api/v1/cloud/projects/{PROJECT_ID}/bootstrap/complete',headers=headers,
        json=dict(bootstrap_id=boot,device_id=ia['device_id'],initial_event_count=0,initial_max_server_sequence=0)).status_code == 200
    bootstrap(tmp_path,a,ia,'bootstrap_confirm_active',bootstrap_id=boot,remote_high_water=0)
    assert client.post('/api/v2/sync/encrypted/cutover',headers=headers,json=dict(expected_cutover_epoch=0)).status_code == 200
    for identity in (ia,ib):
        assert client.post('/api/v3/sync/encrypted/reader-ready',headers=headers,
            json=dict(device_id=identity['device_id'],reader_transport_version=3)).status_code == 204
    assert client.post('/api/v3/sync/encrypted/cutover',headers=headers,json=dict(expected_cutover_epoch=1)).status_code == 200
    amk = list(os.urandom(32)); native(tmp_path,a,ia,user,'begin')
    genesis,_ = publish(client,tmp_path,token,a,ia,user,amk)
    assert sync(client,tmp_path,token,a,ia,user,amk)['view']['state'] == 'active'
    bootstrap(tmp_path,b,ib,'bootstrap_import',bootstrap_id=boot,remote_high_water=1,
        display_name=genesis['metadata']['name'],authenticated_metadata=genesis['metadata'])
    assert sync(client,tmp_path,token,b,ib,user,amk)['view']['state'] == 'active'
    for identity in (ia,ib):
        assert client.put('/api/v3/sync/encrypted/cover-reader-capabilities',headers=headers,
                          json=declaration(identity['device_id'])).status_code == 204
    first = prepare(tmp_path,client,headers,a,ia,user,amk,initial=True)
    event = publish_cover(client,tmp_path,headers,a,ia,user,amk)
    assert event['header']['parent_event_ids'] == [genesis['header']['event_id']]
    for path, identity in ((a,ia),(b,ib)):
        view = sync_covers(client,tmp_path,headers,token,path,identity,user,amk)['view']
        assert view['state'] == 'active' and view['authenticated']['cover_reference'] == first['reference']
        with sqlite3.connect(path) as db:
            source = json.loads(db.execute('SELECT payload_json FROM projects').fetchone()[0])['cover_image']
            assert base64.b64decode(source.split(',',1)[1]) == JPEG
    assert cover(tmp_path,a,ia,user,'pending') is None
    second = prepare(tmp_path,client,headers,a,ia,user,amk,jpeg=JPEG2)
    publish_cover(client,tmp_path,headers,a,ia,user,amk)
    sync_covers(client,tmp_path,headers,token,a,ia,user,amk)
    # Exact authenticated reference retained while the real API returns 404.
    pulled = client.get('/api/v3/sync/encrypted/pull',headers=headers,params=dict(
        device_id=ib['device_id'],since=2,limit=100,protocol_version=3,encrypted_sync_version=3)).json()
    item = pulled['items'][0]
    opened = _crypto_bridge(tmp_path,dict(action='metadata_open',canonical_user_id=user,amk=amk,item=item))
    row = dict(item['event']);row['source_device_id']=row.pop('device_id');row['envelope']=item['object']
    row['updated_at']=datetime.fromisoformat(row['updated_at'].replace('Z','+00:00')).astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z')
    cmd=dict(account_id=ib['local_account_id'],device_id=ib['device_id'],canonical_user_id=user,
        expected_cursor=2,next_cursor=item['event']['server_sequence'],has_more=False,items=[row])
    _native_bridge(tmp_path,dict(action='structural',database_path=str(b),local_account_id=ib['local_account_id'],device_id=ib['device_id'],canonical_user_id=user,project_id=PROJECT_ID,step='persist',command=cmd))
    blob_id = __import__('uuid').UUID(second['reference']['blob_id'])
    with engine.begin() as db:
        stored = dict(db.execute(select(EncryptedBlob.__table__).where(EncryptedBlob.blob_id==blob_id)).mappings().one())
        db.execute(EncryptedBlob.__table__.delete().where(EncryptedBlob.blob_id==blob_id))
    absent = client.get(f'/api/v1/cloud/projects/{PROJECT_ID}/covers/{blob_id}',headers=headers)
    assert absent.status_code == 404
    assert cover(tmp_path,b,ib,user,'block',event_id=row['event_id'],reference=second['reference'],code='cover_blob_missing') is True
    assert cover(tmp_path,b,ib,user,'status')['blockers'] == ['cover_blob_missing']
    ack_request=dict(action='structural',database_path=str(b),local_account_id=ib['local_account_id'],device_id=ib['device_id'],canonical_user_id=user,project_id=PROJECT_ID,step='ack')
    assert _native_bridge(tmp_path,ack_request)['candidate_cursor'] == 2
    with sqlite3.connect(b) as db:
        assert json.loads(db.execute('SELECT payload_json FROM projects').fetchone()[0])['cover_image'] == 'data:image/jpeg;base64,'+base64.b64encode(JPEG).decode()
        assert db.execute('SELECT state FROM cloud_sync_inbox WHERE event_id=?',(row['event_id'],)).fetchone() == ('received',)
    with engine.begin() as db:
        db.execute(EncryptedBlob.__table__.insert().values(**stored))
    material = fetched(client,headers,second,tmp_path,amk,user)
    assert cover(tmp_path,b,ib,user,'material',**material) is True
    assert native(tmp_path,b,ib,user,'apply',opened=opened)['result'] == 'applied'
    assert cover(tmp_path,b,ib,user,'status')['blockers'] == []
    assert _native_bridge(tmp_path,ack_request)['candidate_cursor'] == 3
    # B returns after A's publication; it only downloads and never creates a writer.
    assert sync_covers(client,tmp_path,headers,token,b,ib,user,amk)['view']['authenticated']['cover_reference'] == second['reference']
    assert cover(tmp_path,b,ib,user,'pending') is None
    prepare(tmp_path,client,headers,a,ia,user,amk,remove=True)
    publish_cover(client,tmp_path,headers,a,ia,user,amk)
    for path,identity in ((a,ia),(b,ib)):
        assert sync_covers(client,tmp_path,headers,token,path,identity,user,amk)['view']['authenticated']['cover_reference'] is None
        with sqlite3.connect(path) as db:
            assert json.loads(db.execute('SELECT payload_json FROM projects').fetchone()[0])['cover_image'] is None
    for candidate in (first,second):
        response = client.get(f"/api/v1/cloud/projects/{PROJECT_ID}/covers/{candidate['reference']['blob_id']}",headers=headers)
        assert response.status_code == 200 and response.content != JPEG
    with engine.connect() as db:
        assert db.execute(text('SELECT count(*) FROM encrypted_blobs')).scalar_one() == 2

    # Both devices freeze the same complete metadata parent while offline.
    candidates = [prepare(tmp_path,client,headers,a,ia,user,amk,jpeg=JPEG),
                  prepare(tmp_path,client,headers,b,ib,user,amk,jpeg=JPEG2)]
    tips = [publish_cover(client,tmp_path,headers,path,identity,user,amk)
            for path,identity in ((a,ia),(b,ib))]
    assert tips[0]['header']['parent_event_ids'] == tips[1]['header']['parent_event_ids']
    for path,identity in ((a,ia),(b,ib)):
        view=sync_covers(client,tmp_path,headers,token,path,identity,user,amk)['view']
        assert view['state'] == 'metadata_conflict'
        assert {v['metadata']['cover_reference']['blob_id'] for v in view['branches']} == {c['reference']['blob_id'] for c in candidates}
    native(tmp_path,a,ia,user,'change',kind='choose_branch',selected=tips[1]['header']['event_id'])
    resolution=publish_cover(client,tmp_path,headers,a,ia,user,amk)
    assert resolution['header']['parent_event_ids'] == sorted(t['header']['event_id'] for t in tips)
    for path,identity in ((a,ia),(b,ib)):
        assert sync_covers(client,tmp_path,headers,token,path,identity,user,amk)['view']['state'] == 'active'
    prepare(tmp_path,client,headers,a,ia,user,amk,remove=True)
    retained=prepare(tmp_path,client,headers,b,ib,user,amk,jpeg=JPEG)
    removed=publish_cover(client,tmp_path,headers,a,ia,user,amk)
    replaced=publish_cover(client,tmp_path,headers,b,ib,user,amk)
    assert removed['metadata']['cover_reference'] is None and replaced['metadata']['cover_reference'] == retained['reference']
    for path,identity in ((a,ia),(b,ib)):
        assert sync_covers(client,tmp_path,headers,token,path,identity,user,amk)['view']['state'] == 'metadata_conflict'
    native(tmp_path,a,ia,user,'change',kind='choose_branch',selected=removed['header']['event_id'])
    publish_cover(client,tmp_path,headers,a,ia,user,amk)
    for path,identity in ((a,ia),(b,ib)):
        view=sync_covers(client,tmp_path,headers,token,path,identity,user,amk)['view']
        assert view['state'] == 'active' and view['authenticated']['cover_reference'] is None
    for candidate in (first,second,*candidates,retained):
        assert client.get(f"/api/v1/cloud/projects/{PROJECT_ID}/covers/{candidate['reference']['blob_id']}",headers=headers).status_code == 200
    # Local-only editing cannot capture an intent or create a binding.
    local,il=provision(tmp_path,'cover-local-only',user,True)
    proposed=native(tmp_path,local,il,user,'read')['view']['local']
    proposed['cover_image']='data:image/jpeg;base64,'+base64.b64encode(JPEG).decode()
    assert native(tmp_path,local,il,user,'normal_edit',proposed=proposed)['result'] is False
    assert 'error' in cover(tmp_path,local,il,user,'capture')
    with sqlite3.connect(local) as db:
        assert db.execute('SELECT count(*) FROM cloud_cover_intents').fetchone() == (0,)
        assert db.execute('SELECT count(*) FROM cloud_sync_project_bindings').fetchone() == (0,)
    create_user(engine,username='OtherCoverUser',email='other-cover@example.test')
    other=_headers(login(client,'OtherCoverUser').json()['access_token'])
    url=f"/api/v1/cloud/projects/{PROJECT_ID}/covers/{first['reference']['blob_id']}"
    assert client.get(url,headers=other).status_code in (403,404)
    assert client.get(url).status_code == 401
    assert client.get(f"/api/v1/cloud/projects/other-project/covers/{first['reference']['blob_id']}",headers=headers).status_code in (403,404)
    # Server storage contains only ciphertext; no pixels, source paths or Data URLs.
    for file in (tmp_path/'encrypted-blobs').rglob('*.blob'):
        data=file.read_bytes()
        assert JPEG not in data and JPEG2 not in data and b'data:image/' not in data
    with engine.connect() as db:
        columns={c['name'] for c in __import__('sqlalchemy').inspect(db).get_columns('encrypted_blobs')}
        assert not columns.intersection({'jpeg','pixels','plaintext_hash','filename','local_path','cover_image'})
    # A later Note8 using B's previously authenticated Metadata head can apply
    # while a newer cover reference is missing; account ACK cannot skip the hole.
    from test_cloud_c18_content_note_acceptance import content, note, emit, receive
    from test_cloud_c18_content_note_gate import capabilities
    for identity in (ia,ib):
        assert client.put('/api/v3/sync/encrypted/note-reader-capabilities',headers=headers,
                          json=capabilities(identity['device_id'])).status_code == 204
    later_cover=prepare(tmp_path,client,headers,a,ia,user,amk,jpeg=JPEG2,name='Cover and name edit together')
    publish_cover(client,tmp_path,headers,a,ia,user,amk)
    sync_covers(client,tmp_path,headers,token,a,ia,user,amk)
    with sqlite3.connect(b) as db:
        before_cursor=db.execute('SELECT pull_cursor FROM cloud_sync_state').fetchone()[0]
    page=client.get('/api/v3/sync/encrypted/pull',headers=headers,params=dict(
        device_id=ib['device_id'],since=before_cursor,limit=100,protocol_version=3,encrypted_sync_version=3)).json()
    item=page['items'][0];sequence=item['event']['server_sequence']
    opened=_crypto_bridge(tmp_path,dict(action='metadata_open',canonical_user_id=user,amk=amk,item=item))
    row=dict(item['event']);row['source_device_id']=row.pop('device_id');row['envelope']=item['object']
    row['updated_at']=datetime.fromisoformat(row['updated_at'].replace('Z','+00:00')).astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z')
    cmd=dict(account_id=ib['local_account_id'],device_id=ib['device_id'],canonical_user_id=user,
             expected_cursor=before_cursor,next_cursor=sequence,has_more=False,items=[row])
    _native_bridge(tmp_path,dict(action='structural',database_path=str(b),local_account_id=ib['local_account_id'],device_id=ib['device_id'],canonical_user_id=user,project_id=PROJECT_ID,step='persist',command=cmd))
    blob_id=__import__('uuid').UUID(later_cover['reference']['blob_id'])
    with engine.begin() as db:
        stored=dict(db.execute(select(EncryptedBlob.__table__).where(EncryptedBlob.blob_id==blob_id)).mappings().one())
        db.execute(EncryptedBlob.__table__.delete().where(EncryptedBlob.blob_id==blob_id))
    assert client.get(f'/api/v1/cloud/projects/{PROJECT_ID}/covers/{blob_id}',headers=headers).status_code == 404
    cover(tmp_path,b,ib,user,'block',event_id=row['event_id'],reference=later_cover['reference'],code='cover_blob_missing')
    later_note=note('cover-hole-unrelated-note')
    later_note['content']='Later Note survives missing encrypted cover'
    with sqlite3.connect(b) as db:
        register_remote_apply_authorization_guard(db)
        db.execute('INSERT INTO notes(id,project_id,updated_at,payload_json) VALUES(?,?,?,?)',
                   (later_note['id'],PROJECT_ID,'2026-10-06T00:00:00.000000Z',json.dumps(later_note)))
    content(tmp_path,b,ib,user,'begin')
    assert len(emit(client,tmp_path,token,b,ib,user,amk)) == 1
    assert len(receive(client,tmp_path,token,b,ib,user,amk)) == 1
    assert len(receive(client,tmp_path,token,a,ia,user,amk)) == 1
    assert _native_bridge(tmp_path,ack_request)['candidate_cursor'] == sequence-1
    with sqlite3.connect(b) as db:
        assert db.execute('SELECT state FROM cloud_sync_inbox WHERE server_sequence=?',(sequence+1,)).fetchone() == ('applied',)
    with engine.begin() as db:
        db.execute(EncryptedBlob.__table__.insert().values(**stored))
    material=fetched(client,headers,later_cover,tmp_path,amk,user)
    cover(tmp_path,b,ib,user,'material',**material)
    assert native(tmp_path,b,ib,user,'apply',opened=opened)['result'] == 'applied'
    assert _native_bridge(tmp_path,ack_request)['candidate_cursor'] == sequence+1
    assert cover(tmp_path,b,ib,user,'status')['blockers'] == []
    for path,identity in ((a,ia),(b,ib)):
        candidate=_native_bridge(tmp_path,dict(action='structural',database_path=str(path),local_account_id=identity['local_account_id'],device_id=identity['device_id'],canonical_user_id=user,project_id=PROJECT_ID,step='ack'))
        assert candidate['candidate_cursor'] == sequence+1
        response=client.post('/api/v3/sync/encrypted/ack',headers=headers,json=dict(
            protocol_version=3,encrypted_sync_version=3,device_id=identity['device_id'],cursor=sequence+1))
        assert response.status_code == 204,response.text
        committed=_native_bridge(tmp_path,dict(action='commit_ack',database_path=str(path),local_account_id=identity['local_account_id'],device_id=identity['device_id'],canonical_user_id=user,project_id=PROJECT_ID,expected_old_ack_cursor=candidate['current_ack_cursor'],acknowledged_cursor=sequence+1))
        assert committed['ack_cursor'] == committed['pull_cursor'] == sequence+1
    with engine.connect() as db:
        assert db.execute(text('SELECT last_ack_sequence FROM sync_devices WHERE user_id=:user ORDER BY device_id'),dict(user=user)).scalars().all() == [sequence+1,sequence+1]
