from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..dependencies import AuthenticatedUser, get_cloud_session, get_current_user
from .blob_store import FileSystemBlobStore
from .encrypted_blobs_service import (BlobMetadata, EncryptedBlobError,
                                      EncryptedBlobService, MAX_COVER_CIPHERTEXT_BYTES)
from .schemas import decode_canonical_base64url


router = APIRouter(prefix='/api/v1/cloud/projects', tags=['encrypted cover blobs'])


def _error(error: EncryptedBlobError) -> HTTPException:
    return HTTPException(status_code=error.status_code, detail={
        'code': error.code, 'message': 'Encrypted blob request could not be completed.',
    })


def _store(request: Request) -> FileSystemBlobStore:
    root = request.app.state.runtime_config.cloud_blob_dir
    if root is None:
        raise HTTPException(status_code=503, detail={
            'code': 'blob_storage_unavailable', 'message': 'Blob storage is unavailable.',
        })
    return FileSystemBlobStore(Path(root))


def _metadata(project_id: str, blob_id: UUID, crypto_version: str | None,
              aad_version: str | None, nonce: str | None) -> BlobMetadata:
    if not project_id or len(project_id) > 512:
        raise HTTPException(status_code=422, detail={'code': 'invalid_encrypted_blob', 'message': 'Invalid encrypted blob.'})
    try:
        crypto = int(crypto_version or '')
        aad = int(aad_version or '')
        decoded_nonce = decode_canonical_base64url(nonce or '', expected_length=24)
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail={'code': 'invalid_encrypted_blob', 'message': 'Invalid encrypted blob.'}) from None
    if crypto != 1 or aad != 1:
        raise HTTPException(status_code=422, detail={'code': 'invalid_encrypted_blob', 'message': 'Invalid encrypted blob.'})
    return BlobMetadata(project_id, blob_id, crypto, aad, decoded_nonce)


async def _ciphertext(request: Request) -> bytes:
    content_length = request.headers.get('content-length')
    if content_length is not None:
        try:
            if int(content_length) > MAX_COVER_CIPHERTEXT_BYTES:
                raise HTTPException(status_code=413, detail={'code': 'encrypted_blob_too_large', 'message': 'Encrypted blob is too large.'})
        except ValueError:
            raise HTTPException(status_code=422, detail={'code': 'invalid_encrypted_blob', 'message': 'Invalid encrypted blob.'}) from None
    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > MAX_COVER_CIPHERTEXT_BYTES:
            raise HTTPException(status_code=413, detail={'code': 'encrypted_blob_too_large', 'message': 'Encrypted blob is too large.'})
        chunks.append(chunk)
    value = b''.join(chunks)
    if len(value) < 16:
        raise HTTPException(status_code=422, detail={'code': 'invalid_encrypted_blob', 'message': 'Invalid encrypted blob.'})
    return value


@router.put('/{project_id}/covers/{blob_id}')
async def upload_cover(project_id: str, blob_id: UUID, request: Request,
                       current: AuthenticatedUser = Depends(get_current_user),
                       session: Session = Depends(get_cloud_session)) -> dict[str, object]:
    if request.headers.get('content-type', '').split(';', 1)[0].strip().lower() != 'application/octet-stream':
        raise HTTPException(status_code=422, detail={'code': 'invalid_encrypted_blob', 'message': 'Invalid encrypted blob.'})
    metadata = _metadata(project_id, blob_id, request.headers.get('X-WORTA-Crypto-Version'),
                         request.headers.get('X-WORTA-AAD-Version'), request.headers.get('X-WORTA-Nonce'))
    ciphertext = await _ciphertext(request)
    try:
        duplicate = EncryptedBlobService(_store(request)).upload(session, current.user.id, metadata, ciphertext)
    except EncryptedBlobError as error:
        raise _error(error) from None
    return {'blob_id': str(blob_id), 'project_id': project_id, 'kind': 'project_cover',
            'size_bytes': len(ciphertext), 'duplicate': duplicate}


@router.get('/{project_id}/covers/{blob_id}')
def download_cover(project_id: str, blob_id: UUID, request: Request,
                   current: AuthenticatedUser = Depends(get_current_user),
                   session: Session = Depends(get_cloud_session)) -> Response:
    try:
        row, ciphertext = EncryptedBlobService(_store(request)).download(session, current.user.id, project_id, blob_id)
    except EncryptedBlobError as error:
        raise _error(error) from None
    return Response(content=ciphertext, media_type='application/octet-stream', headers={
        'X-WORTA-Crypto-Version': str(row.crypto_version), 'X-WORTA-AAD-Version': str(row.aad_version),
        'X-WORTA-Nonce': __import__('base64').urlsafe_b64encode(row.nonce).decode('ascii').rstrip('='),
        'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff',
    })
