"""Mode-3 stage descriptors stay opaque and fail closed across older modes."""
from __future__ import annotations
import pytest
import base64
from uuid import uuid4
from test_cloud_auth import cloud_client, create_user, login, migrated_database
from test_cloud_c18_metadata import _event, _object, _request, _headers
from backend.app.cloud.schemas import V3EncryptedSyncPushRequest
from backend.app.cloud.models import EncryptedObject, SyncEvent
from sqlalchemy.orm import Session

@pytest.mark.parametrize('kind,entity', [('stage','S1'),('stage_order','stage_order')])
def test_structural_descriptor_exact_schema(kind,entity):
    request=_request(str(uuid4()),_event(entity_type=kind,entity_id=entity))
    V3EncryptedSyncPushRequest.model_validate(request)
    for key in ('name','stage_ids','stage_heads','metadata_event_id'):
        bad=_request(str(uuid4()),_event(entity_type=kind,entity_id=entity,**{key:'plaintext'}))
        with pytest.raises(ValueError):V3EncryptedSyncPushRequest.model_validate(bad)
    bad=_request(str(uuid4()),_event(entity_type=kind,entity_id=entity,operation='resolution',revision=2))
    with pytest.raises(ValueError):V3EncryptedSyncPushRequest.model_validate(bad)


def test_structural_mode3_opaque_replay_authorization_and_old_mode_rejection(cloud_client):
    client,engine=cloud_client; user=create_user(engine);token=login(client).json()['access_token'];headers=_headers(token)
    device=str(uuid4());assert client.put(f'/api/v1/sync/devices/{device}',headers=headers).status_code==200
    assert client.post('/api/v1/cloud/projects/project-1',headers=headers).status_code==200
    assert client.post('/api/v2/sync/encrypted/cutover',headers=headers,json={'expected_cutover_epoch':0}).status_code==200
    assert client.post('/api/v3/sync/encrypted/reader-ready',headers=headers,json={'device_id':device,'reader_transport_version':3}).status_code==204
    assert client.post('/api/v3/sync/encrypted/cutover',headers=headers,json={'expected_cutover_epoch':1}).status_code==200
    events=[]
    for kind,entity in [('stage','S1'),('stage_order','stage_order')]:
        event=_event(entity_type=kind,entity_id=entity);events.append(event)
        request=_request(device,event)
        response=client.post('/api/v3/sync/encrypted/push',headers=headers,json=request)
        assert response.status_code==200,response.text
        replay=client.post('/api/v3/sync/encrypted/push',headers=headers,json=request)
        assert replay.status_code==200 and replay.json()['results'][0]['duplicate']
        changed=_request(device,event,{**_object(),'nonce':base64.urlsafe_b64encode(b'x'*24).decode().rstrip('=')})
        assert client.post('/api/v3/sync/encrypted/push',headers=headers,json=changed).status_code in (409,422)
        assert client.post('/api/v3/sync/encrypted/push',json=request).status_code==401
        for version in (1,2):
            old={**request,'protocol_version':version,'encrypted_sync_version':version}
            assert client.post(f'/api/v{version}/sync/encrypted/push',headers=headers,json=old).status_code in (409,422)
    page=client.get('/api/v3/sync/encrypted/pull',headers=headers,params={'device_id':device,'since':0,'protocol_version':3,'encrypted_sync_version':3})
    assert page.status_code==200 and len(page.json()['items'])==2
    assert [r['event']['entity_type'] for r in page.json()['items']]==['stage','stage_order']
    assert all(r['object']==_object() for r in page.json()['items'])
    for event in [_event(entity_type='stage_order',entity_id='other'),_event(entity_type='folder',entity_id='folder'),_event(entity_type='stage',entity_id='S1',project_id='missing')]:
        assert client.post('/api/v3/sync/encrypted/push',headers=headers,json=_request(device,event)).status_code in (409,422)
    with Session(engine) as session:
        assert session.query(SyncEvent).filter_by(user_id=user).count()==2
        assert {r.ciphertext for r in session.query(EncryptedObject).filter_by(user_id=user)}=={b'opaque project metadata ciphertext'}
