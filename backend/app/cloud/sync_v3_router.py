"""C18 mode-3 opaque project and account transport with one shared sequence."""
from __future__ import annotations

from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from ..dependencies import AuthenticatedUser, get_cloud_session, get_current_user
from .schemas import (CompressionReaderCapability, CompressionWriterRequest,ProjectCoverReaderCapabilities, ObjectEnvelopeDto, SyncPushResult, V3EncryptedSyncPushRequest,
                      V3EncryptedSyncPushResponse, V3EncryptedSyncPullItem,
                      V3EncryptedSyncPullResponse, V3EncryptedSyncAckRequest,
                      DocumentReaderCapabilities,
    GameReaderCapabilities, ProgressReaderCapabilities, MapReaderCapabilities, ContentNoteReaderCapabilities, ContentNoteCapabilityGate, V3ReaderReadyRequest, V3CutoverRequest, V3CutoverResponse, V3SyncPullEvent,
                      encode_canonical_base64url, AccountEncryptedPushRequest, AccountSyncPullEvent)
from .services import SyncProtocolError, SyncService
from .sync_router import _error, _inline_json_schema, _read_encrypted_push_body

router = APIRouter(prefix='/api/v3/sync/encrypted', tags=['cloud sync v3'])
_PUSH_SCHEMA = _inline_json_schema(V3EncryptedSyncPushRequest)
_ACCOUNT_PUSH_SCHEMA = _inline_json_schema(AccountEncryptedPushRequest)


@router.post('/reader-ready', status_code=status.HTTP_204_NO_CONTENT)
def reader_ready(request: V3ReaderReadyRequest,
                 current: AuthenticatedUser = Depends(get_current_user),
                 session: Session = Depends(get_cloud_session)) -> None:
    try:
        SyncService().declare_v3_reader_ready(session, current.user.id, request.device_id)
    except SyncProtocolError as error:
        raise _error(error) from None


@router.post('/cutover', response_model=V3CutoverResponse)
def cutover(request: V3CutoverRequest,
            current: AuthenticatedUser = Depends(get_current_user),
            session: Session = Depends(get_cloud_session)) -> V3CutoverResponse:
    try:
        mode, epoch = SyncService().cutover_to_v3(session, current.user.id, request.expected_cutover_epoch)
    except SyncProtocolError as error:
        raise _error(error) from None
    return V3CutoverResponse(writer_transport_version=mode, cutover_epoch=epoch)


@router.post('/push', response_model=V3EncryptedSyncPushResponse, openapi_extra={
    'requestBody': {'required': True, 'content': {'application/json': {'schema': _PUSH_SCHEMA}}},
})
async def encrypted_push(http_request: Request,
                         current: AuthenticatedUser = Depends(get_current_user),
                         session: Session = Depends(get_cloud_session)) -> V3EncryptedSyncPushResponse:
    body = await _read_encrypted_push_body(http_request)
    try:
        request = V3EncryptedSyncPushRequest.model_validate_json(body)
    except ValidationError as error:
        raise RequestValidationError(error.errors()) from None
    try:
        results, cursor = await run_in_threadpool(
            SyncService().push_encrypted, session, current.user.id, request.device_id,
            request.items, transport_version=3,
        )
    except SyncProtocolError as error:
        raise _error(error) from None
    return V3EncryptedSyncPushResponse(
        results=[SyncPushResult(event_id=row.event_id, server_sequence=row.server_sequence,
                                duplicate=row.duplicate) for row in results],
        current_cursor=cursor,
    )


@router.get('/pull', response_model=V3EncryptedSyncPullResponse)
def encrypted_pull(device_id: UUID, since: int = Query(ge=0, le=9_007_199_254_740_991),
                   limit: int = Query(default=200, ge=1, le=500),
                   protocol_version: int = Query(...), encrypted_sync_version: int = Query(...),
                   current: AuthenticatedUser = Depends(get_current_user),
                   session: Session = Depends(get_cloud_session)) -> V3EncryptedSyncPullResponse:
    if protocol_version != 3 or encrypted_sync_version != 3:
        raise _error(SyncProtocolError('encrypted_sync_version_unsupported', 'Unsupported encrypted sync version.', 422))
    try:
        rows, next_cursor, has_more, _ = SyncService().pull_encrypted_v3(
            session, current.user.id, device_id, since, limit,
        )
    except SyncProtocolError as error:
        raise _error(error) from None
    return V3EncryptedSyncPullResponse(items=[V3EncryptedSyncPullItem(
        event=AccountSyncPullEvent(
            event_id=event.event_id, device_id=event.device_id, canonical_user_id=current.user.id, scope='account',
            entity_id=event.entity_id, entity_type=event.entity_type, operation=event.operation,
            revision=event.revision, updated_at=event.updated_at, deleted_at=event.deleted_at, server_sequence=event.server_sequence,
        ) if event.project_id is None else V3SyncPullEvent(
            event_id=event.event_id, device_id=event.device_id, project_id=event.project_id,
            entity_id=event.entity_id, entity_type=event.entity_type, operation=event.operation,
            revision=event.revision, updated_at=event.updated_at, deleted_at=event.deleted_at,
            server_sequence=event.server_sequence,
        ),
        object=ObjectEnvelopeDto(
            crypto_version=encrypted.crypto_version, aad_version=encrypted.aad_version,
            nonce=encode_canonical_base64url(encrypted.nonce), ciphertext=encode_canonical_base64url(encrypted.ciphertext),
        ),
    ) for event, encrypted in rows], next_cursor=next_cursor, has_more=has_more)


@router.post('/ack', status_code=status.HTTP_204_NO_CONTENT)
def ack(request: V3EncryptedSyncAckRequest,
        current: AuthenticatedUser = Depends(get_current_user),
        session: Session = Depends(get_cloud_session)) -> None:
    try:
        SyncService().ack(session, current.user.id, request.device_id, request.cursor, transport_version=3)
    except SyncProtocolError as error:
        raise _error(error) from None


@router.post('/account/push', response_model=V3EncryptedSyncPushResponse, openapi_extra={
    'requestBody': {'required': True, 'content': {'application/json': {'schema': _ACCOUNT_PUSH_SCHEMA}}},
})
async def account_push(http_request: Request,
                       current: AuthenticatedUser = Depends(get_current_user),
                       session: Session = Depends(get_cloud_session)) -> V3EncryptedSyncPushResponse:
    body = await _read_encrypted_push_body(http_request)
    try:
        request = AccountEncryptedPushRequest.model_validate_json(body)
    except ValidationError as error:
        raise RequestValidationError(error.errors()) from None
    try:
        results, cursor = await run_in_threadpool(SyncService().push_encrypted, session,
            current.user.id, request.device_id, request.items, transport_version=3)
    except SyncProtocolError as error:
        raise _error(error) from None
    return V3EncryptedSyncPushResponse(results=[SyncPushResult(event_id=row.event_id,
        server_sequence=row.server_sequence, duplicate=row.duplicate) for row in results], current_cursor=cursor)


@router.put('/note-reader-capabilities', status_code=status.HTTP_204_NO_CONTENT)
def note_reader_capabilities(request: ContentNoteReaderCapabilities,
                             current: AuthenticatedUser = Depends(get_current_user),
                             session: Session = Depends(get_cloud_session)) -> None:
    try:
        SyncService().declare_content_note_reader(session, current.user.id, request)
    except SyncProtocolError as error:
        raise _error(error) from None


@router.get('/note-reader-capabilities', response_model=ContentNoteCapabilityGate)
def note_reader_gate(current: AuthenticatedUser = Depends(get_current_user),
                     session: Session = Depends(get_cloud_session)) -> ContentNoteCapabilityGate:
    ready, missing = SyncService().content_note_gate(session, current.user.id)
    return ContentNoteCapabilityGate(ready=ready, missing_devices=missing)


@router.put('/map-reader-capabilities', status_code=status.HTTP_204_NO_CONTENT)
def map_reader_capabilities(request: MapReaderCapabilities,
                            current: AuthenticatedUser = Depends(get_current_user),
                            session: Session = Depends(get_cloud_session)) -> None:
    try:
        SyncService().declare_map_reader(session, current.user.id, request)
    except SyncProtocolError as error:
        raise _error(error) from None


@router.get('/map-reader-capabilities', response_model=ContentNoteCapabilityGate)
def map_reader_gate(current: AuthenticatedUser = Depends(get_current_user),
                    session: Session = Depends(get_cloud_session)) -> ContentNoteCapabilityGate:
    ready, missing = SyncService().map_gate(session, current.user.id)
    return ContentNoteCapabilityGate(ready=ready, missing_devices=missing)


@router.put('/document-reader-capabilities', status_code=status.HTTP_204_NO_CONTENT)
def document_reader_capabilities(request: DocumentReaderCapabilities,
                            current: AuthenticatedUser = Depends(get_current_user),
                            session: Session = Depends(get_cloud_session)) -> None:
    try:
        SyncService().declare_document_reader(session, current.user.id, request)
    except SyncProtocolError as error:
        raise _error(error) from None


@router.get('/document-reader-capabilities', response_model=ContentNoteCapabilityGate)
def document_reader_gate(current: AuthenticatedUser = Depends(get_current_user),
                    session: Session = Depends(get_cloud_session)) -> ContentNoteCapabilityGate:
    ready, missing = SyncService().document_gate(session, current.user.id)
    return ContentNoteCapabilityGate(ready=ready, missing_devices=missing)

@router.put('/progress-reader-capabilities', status_code=status.HTTP_204_NO_CONTENT)
def progress_reader_capabilities(request: ProgressReaderCapabilities,
                            current: AuthenticatedUser = Depends(get_current_user),
                            session: Session = Depends(get_cloud_session)) -> None:
    try:
        SyncService().declare_progress_reader(session, current.user.id, request)
    except SyncProtocolError as error:
        raise _error(error) from None


@router.get('/progress-reader-capabilities', response_model=ContentNoteCapabilityGate)
def progress_reader_gate(current: AuthenticatedUser = Depends(get_current_user),
                    session: Session = Depends(get_cloud_session)) -> ContentNoteCapabilityGate:
    ready, missing = SyncService().progress_gate(session, current.user.id)
    return ContentNoteCapabilityGate(ready=ready, missing_devices=missing)


@router.put('/game-reader-capabilities', status_code=status.HTTP_204_NO_CONTENT)
def game_reader_capabilities(request: GameReaderCapabilities,
                             current: AuthenticatedUser = Depends(get_current_user),
                             session: Session = Depends(get_cloud_session)) -> None:
    try:
        SyncService().declare_game_reader(session, current.user.id, request)
    except SyncProtocolError as error:
        raise _error(error) from None


@router.get('/game-reader-capabilities', response_model=ContentNoteCapabilityGate)
def game_reader_gate(current: AuthenticatedUser = Depends(get_current_user),
                     session: Session = Depends(get_cloud_session)) -> ContentNoteCapabilityGate:
    ready, missing = SyncService().game_gate(session, current.user.id)
    return ContentNoteCapabilityGate(ready=ready, missing_devices=missing)


@router.put('/cover-reader-capabilities', status_code=status.HTTP_204_NO_CONTENT)
def declare_cover_reader(request: ProjectCoverReaderCapabilities,
                         current: AuthenticatedUser = Depends(get_current_user),
                         session: Session = Depends(get_cloud_session)) -> None:
    try:
        SyncService().declare_cover_reader(session, current.user.id, request)
    except SyncProtocolError as error:
        raise _error(error) from None


@router.get('/cover-reader-capabilities', response_model=ContentNoteCapabilityGate)
def cover_reader_gate(current: AuthenticatedUser = Depends(get_current_user),
                      session: Session = Depends(get_cloud_session)) -> ContentNoteCapabilityGate:
    ready, missing = SyncService().cover_gate(session, current.user.id)
    return ContentNoteCapabilityGate(ready=ready, missing_devices=missing)


@router.post('/cover-metadata/push', response_model=V3EncryptedSyncPushResponse, openapi_extra={
    'requestBody': {'required': True, 'content': {'application/json': {'schema': _PUSH_SCHEMA}}},
})
async def cover_metadata_push(http_request: Request,
                         current: AuthenticatedUser = Depends(get_current_user),
                         session: Session = Depends(get_cloud_session)) -> V3EncryptedSyncPushResponse:
    body = await _read_encrypted_push_body(http_request)
    try:
        request = V3EncryptedSyncPushRequest.model_validate_json(body)
    except ValidationError as error:
        raise RequestValidationError(error.errors()) from None
    try:
        results, cursor = await run_in_threadpool(
            SyncService().push_encrypted, session, current.user.id, request.device_id,
            request.items, transport_version=3, metadata_cover=True,
        )
    except SyncProtocolError as error:
        raise _error(error) from None
    return V3EncryptedSyncPushResponse(
        results=[SyncPushResult(event_id=row.event_id, server_sequence=row.server_sequence,
                                duplicate=row.duplicate) for row in results],
        current_cursor=cursor,
    )


@router.put('/compression-reader-capabilities', status_code=status.HTTP_204_NO_CONTENT)
def compression_reader(request: CompressionReaderCapability,
                       current: AuthenticatedUser = Depends(get_current_user),
                       session: Session = Depends(get_cloud_session)) -> None:
    try:
        SyncService().declare_compression_reader(session, current.user.id, request)
    except SyncProtocolError as error:
        raise _error(error) from None


@router.get('/compression-reader-capabilities', response_model=ContentNoteCapabilityGate)
def compression_gate(current: AuthenticatedUser = Depends(get_current_user),
                     session: Session = Depends(get_cloud_session)) -> ContentNoteCapabilityGate:
    ready, missing = SyncService().compression_gate(session, current.user.id)
    return ContentNoteCapabilityGate(ready=ready, missing_devices=missing)


@router.post('/compression-writer', response_model=ContentNoteCapabilityGate)
def compression_writer(request: CompressionWriterRequest,
                       current: AuthenticatedUser = Depends(get_current_user),
                       session: Session = Depends(get_cloud_session)) -> ContentNoteCapabilityGate:
    try:
        ready, missing = SyncService().authorize_compressed_seal(session, current.user.id, request.device_id)
    except SyncProtocolError as error:
        raise _error(error) from None
    return ContentNoteCapabilityGate(ready=ready, missing_devices=missing)
