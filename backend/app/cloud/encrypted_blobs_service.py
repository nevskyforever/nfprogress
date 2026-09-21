from __future__ import annotations

import hashlib
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from .blob_store import BlobAlreadyExists, BlobMissing, BlobStoreError, FileSystemBlobStore
from .repositories import CloudProjectRepository, EncryptedBlobRepository


PROJECT_COVER_KIND = 'project_cover'
MAX_COVER_PLAINTEXT_BYTES = 2 * 1024 * 1024
MAX_COVER_CIPHERTEXT_BYTES = MAX_COVER_PLAINTEXT_BYTES + 16


class EncryptedBlobError(Exception):
    def __init__(self, code: str, status_code: int) -> None:
        self.code = code
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class BlobMetadata:
    project_id: str
    blob_id: UUID
    crypto_version: int
    aad_version: int
    nonce: bytes


def _lock_key(user_id: UUID, blob_id: UUID) -> int:
    # PostgreSQL advisory lock collisions only serialize unrelated uploads; they
    # cannot allow an immutable identity to be overwritten.
    return int.from_bytes(hashlib.sha256(user_id.bytes + blob_id.bytes).digest()[:8], 'big', signed=True)


class EncryptedBlobService:
    def __init__(self, store: FileSystemBlobStore) -> None:
        self._store = store
        self._blobs = EncryptedBlobRepository()
        self._projects = CloudProjectRepository()

    @staticmethod
    def _matches(row, metadata: BlobMetadata, ciphertext: bytes, digest: bytes) -> bool:
        return (row.project_id == metadata.project_id and row.kind == PROJECT_COVER_KIND
                and row.crypto_version == metadata.crypto_version and row.aad_version == metadata.aad_version
                and row.nonce == metadata.nonce and row.ciphertext_size == len(ciphertext)
                and row.ciphertext_sha256 == digest)

    def upload(self, session: Session, user_id: UUID, metadata: BlobMetadata, ciphertext: bytes) -> bool:
        digest = hashlib.sha256(ciphertext).digest()
        created = False
        try:
            session.commit()
            with session.begin():
                session.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': _lock_key(user_id, metadata.blob_id)})
                existing = self._blobs.get(session, user_id, metadata.blob_id)
                if existing is not None:
                    if not self._matches(existing, metadata, ciphertext, digest):
                        raise EncryptedBlobError('encrypted_blob_id_conflict', 409)
                    try:
                        self._store.read_verified(user_id, metadata.blob_id, existing.ciphertext_size, existing.ciphertext_sha256)
                    except BlobMissing as error:
                        raise EncryptedBlobError('encrypted_blob_unavailable', 503) from error
                    except BlobStoreError as error:
                        raise EncryptedBlobError('encrypted_blob_corrupt', 503) from error
                    return True
                if self._projects.get(session, user_id, metadata.project_id) is None:
                    raise EncryptedBlobError('cloud_project_not_enabled', 409)
                try:
                    self._store.create(user_id, metadata.blob_id, ciphertext)
                    created = True
                except BlobAlreadyExists as error:
                    raise EncryptedBlobError('encrypted_blob_id_conflict', 409) from error
                except BlobStoreError as error:
                    raise EncryptedBlobError('encrypted_blob_unavailable', 503) from error
                self._blobs.add(session, user_id=user_id, blob_id=metadata.blob_id,
                                project_id=metadata.project_id, kind=PROJECT_COVER_KIND,
                                crypto_version=metadata.crypto_version, aad_version=metadata.aad_version,
                                nonce=metadata.nonce, ciphertext_size=len(ciphertext), ciphertext_sha256=digest)
                session.flush()
            return False
        except Exception:
            session.rollback()
            if created:
                self._store.remove_if_present(user_id, metadata.blob_id)
            raise

    def download(self, session: Session, user_id: UUID, project_id: str, blob_id: UUID):
        row = self._blobs.get(session, user_id, blob_id)
        if row is None or row.project_id != project_id:
            raise EncryptedBlobError('encrypted_blob_unavailable', 404)
        try:
            ciphertext = self._store.read_verified(user_id, blob_id, row.ciphertext_size, row.ciphertext_sha256)
        except BlobMissing as error:
            raise EncryptedBlobError('encrypted_blob_unavailable', 503) from error
        except BlobStoreError as error:
            raise EncryptedBlobError('encrypted_blob_corrupt', 503) from error
        return row, ciphertext
