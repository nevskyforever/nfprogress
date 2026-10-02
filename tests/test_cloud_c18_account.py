from uuid import uuid4
import pytest
from sqlalchemy.orm import Session
from backend.app.cloud.models import SyncEvent, EncryptedObject, CloudProject
from backend.app.cloud.schemas import AccountEncryptedPushRequest
from test_cloud_auth import cloud_client, migrated_database, create_user, login
from test_cloud_c18_metadata import _headers, _object, _event, _request


def account_request(user, device):
    return _request(device, {**{k:v for k,v in _event().items() if k!='project_id'},
        'canonical_user_id':str(user),'scope':'account','entity_id':'каталог/📁','entity_type':'folder'},
        {**_object(),'crypto_version':2,'aad_version':2})


def test_account_descriptor_closed_schema_and_versions():
    request=account_request(uuid4(),str(uuid4()))
    AccountEncryptedPushRequest.model_validate(request)
    for changes in [{'scope':'project'},{'project_id':'fake'},{'entity_type':'note'},{'entity_id':'😀'*129},{'entity_id':'\ud800'},{'name':'plaintext'}]:
        bad=account_request(uuid4(),str(uuid4()));bad['items'][0]['event'].update(changes)
        with pytest.raises(ValueError): AccountEncryptedPushRequest.model_validate(bad)
    for key in ['crypto_version','aad_version']:
        bad=account_request(uuid4(),str(uuid4()));bad['items'][0]['object'][key]=1
        with pytest.raises(ValueError): AccountEncryptedPushRequest.model_validate(bad)


def test_account_opaque_shared_stream_ownership_replay_and_fairness(cloud_client):
    client,engine=cloud_client; user=create_user(engine); token=login(client).json()['access_token']; h=_headers(token); device=str(uuid4())
    assert client.put(f'/api/v1/sync/devices/{device}',headers=h).status_code==200
    assert client.post('/api/v2/sync/encrypted/cutover',headers=h,json={'expected_cutover_epoch':0}).status_code==200
    assert client.post('/api/v3/sync/encrypted/reader-ready',headers=h,json={'device_id':device,'reader_transport_version':3}).status_code==204
    assert client.post('/api/v3/sync/encrypted/cutover',headers=h,json={'expected_cutover_epoch':1}).status_code==200
    request=account_request(user,device);path='/api/v3/sync/encrypted/account/push'
    assert client.post(path,json=request).status_code==401
    assert client.post('/api/v3/sync/encrypted/push',headers=h,json=request).status_code==422
    assert client.post(path,headers=h,json=_request(device,_event())).status_code==422
    bad=account_request(uuid4(),device)
    assert client.post(path,headers=h,json=bad).status_code==403
    for change in [{'scope':'project'},{'entity_type':'note'}]:
        bad=account_request(user,device);bad['items'][0]['event'].update(change)
        assert client.post(path,headers=h,json=bad).status_code==422
    for version in ['crypto_version','aad_version']:
        bad=account_request(user,device);bad['items'][0]['object'][version]=1
        assert client.post(path,headers=h,json=bad).status_code==422
    first=client.post(path,headers=h,json=request);assert first.status_code==200,first.text
    assert first.json()['results'][0]['server_sequence']==1
    assert client.post(path,headers=h,json=request).json()['results'][0]['duplicate'] is True
    for field,value in [('entity_id','changed'),('entity_type','folder_order')]:
        bad={**request,'items':[{'event':{**request['items'][0]['event'],field:value},'object':request['items'][0]['object']}]}
        assert client.post(path,headers=h,json=bad).status_code==409
    bad={**request,'items':[{'event':request['items'][0]['event'],'object':{**request['items'][0]['object'],'ciphertext':'eA'*16}}]}
    assert client.post(path,headers=h,json=bad).status_code in (409,422)
    # Catalog bytes never register any project, including a local-only reference.
    with Session(engine) as session:
        assert session.query(CloudProject).count()==0
        event=session.query(SyncEvent).one();assert event.project_id is None
        assert session.query(EncryptedObject).one().ciphertext==b'opaque project metadata ciphertext'
    assert client.post('/api/v1/cloud/projects/project-1',headers=h).status_code==200
    project=client.post('/api/v3/sync/encrypted/push',headers=h,json=_request(device,_event()))
    assert project.status_code==200,project.text
    assert project.json()['results'][0]['server_sequence']==2
    request2=account_request(user,device);request2['items'][0]['event']['entity_type']='project_order'
    assert client.post(path,headers=h,json=request2).json()['results'][0]['server_sequence']==3
    cursor=0;types=[]
    for _ in range(3):
        pull=client.get('/api/v3/sync/encrypted/pull',headers=h,params={'device_id':device,'since':cursor,'limit':1,'protocol_version':3,'encrypted_sync_version':3})
        assert pull.status_code==200,pull.text
        page=pull.json();row=page['items'][0];types.append(row['event']['entity_type']);cursor=page['next_cursor']
        if 'scope' in row['event']:
            assert 'project_id' not in row['event'];assert row['event']['canonical_user_id']==str(user);assert row['object']['crypto_version']==2
    assert types==['folder','project_metadata','project_order'];assert cursor==3
    other=create_user(engine,username='Other',email='other@example.test');other_h=_headers(login(client,username='Other').json()['access_token'])
    assert client.post(path,headers=other_h,json=request).status_code==403

    other_device=str(uuid4())
    assert client.put(f'/api/v1/sync/devices/{other_device}',headers=other_h).status_code==200
    assert client.post('/api/v2/sync/encrypted/cutover',headers=other_h,json={'expected_cutover_epoch':0}).status_code==200
    assert client.post('/api/v3/sync/encrypted/reader-ready',headers=other_h,json={'device_id':other_device,'reader_transport_version':3}).status_code==204
    assert client.post('/api/v3/sync/encrypted/cutover',headers=other_h,json={'expected_cutover_epoch':1}).status_code==200
    pull=client.get('/api/v3/sync/encrypted/pull',headers=other_h,params={'device_id':other_device,'since':0,'protocol_version':3,'encrypted_sync_version':3})
    assert pull.status_code==200 and pull.json()['items']==[]
