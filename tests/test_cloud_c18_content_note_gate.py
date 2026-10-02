"""Blind mode3 transport learns only the explicit Note event route."""
from uuid import uuid4
import base64
import pytest
from sqlalchemy.orm import Session
from backend.app.cloud.models import EncryptedObject, SyncEvent
from backend.app.cloud.schemas import V3EncryptedSyncPushRequest
from test_cloud_auth import cloud_client, create_user, login, migrated_database
from test_cloud_c18_metadata import _headers,_event,_request,_object


def test_content_note_descriptor_strict_gate():
    device=str(uuid4());event=_event(entity_id='N',entity_type='note',operation='event')
    V3EncryptedSyncPushRequest.model_validate(_request(device,event))
    for changes in [{'entity_type':'stage'},{'entity_type':'project_metadata'},{'deleted_at':'2026-10-02T00:00:00Z'},{'title':'plaintext'}]:
        with pytest.raises(ValueError):V3EncryptedSyncPushRequest.model_validate(_request(device,{**event,**changes}))


def test_content_note_transport_mode3_opaque_replay_and_exact_pull(cloud_client):
    client,engine=cloud_client;user=create_user(engine);headers=_headers(login(client).json()['access_token']);device=str(uuid4())
    assert client.put(f'/api/v1/sync/devices/{device}',headers=headers).status_code==200
    assert client.post('/api/v1/cloud/projects/project-1',headers=headers).status_code==200
    event=_event(entity_id='N',entity_type='note',operation='event');obj=_object();request=_request(device,event,obj);path='/api/v3/sync/encrypted/push'
    assert client.post(path,headers=headers,json=request).status_code==409
    for version in [1,2]:
        body={**request,'protocol_version':version,'encrypted_sync_version':version}
        assert client.post(f'/api/v{version}/sync/encrypted/push',headers=headers,json=body).status_code==422
    assert client.post('/api/v2/sync/encrypted/cutover',headers=headers,json={'expected_cutover_epoch':0}).status_code==200
    assert client.post('/api/v3/sync/encrypted/reader-ready',headers=headers,json={'device_id':device,'reader_transport_version':3}).status_code==204
    assert client.post('/api/v3/sync/encrypted/cutover',headers=headers,json={'expected_cutover_epoch':1}).status_code==200
    first=client.post(path,headers=headers,json=request);assert first.status_code==200,first.text
    assert first.json()['results'][0]['duplicate'] is False
    assert client.post(path,headers=headers,json=request).json()['results'][0]['duplicate'] is True
    altered=_request(device,event,{**obj,'nonce':base64.urlsafe_b64encode(b'x'*24).decode().rstrip('=')})
    assert client.post(path,headers=headers,json=altered).status_code==409
    assert client.post(path,headers=headers,json=_request(str(uuid4()),event,obj)).status_code==409
    assert client.post(path,headers=headers,json=_request(device,_event(project_id='foreign',entity_id='N',entity_type='note',operation='event'),obj)).status_code==409
    pull=client.get('/api/v3/sync/encrypted/pull',headers=headers,params={'device_id':device,'since':0,'protocol_version':3,'encrypted_sync_version':3})
    assert pull.status_code==200,pull.text
    item=pull.json()['items'][0];assert item['event']['operation']=='event';assert item['object']==obj
    with Session(engine) as session:
        row=session.query(SyncEvent).filter_by(user_id=user,event_id=event['event_id']).one();assert row.entity_type=='note' and row.operation=='event'
        encrypted=session.query(EncryptedObject).filter_by(user_id=user,event_id=event['event_id']).one()
        assert encrypted.ciphertext==base64.urlsafe_b64decode(obj['ciphertext']+'='*(-len(obj['ciphertext'])%4))
