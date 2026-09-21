from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from uuid import UUID


class BlobStoreError(Exception):
    pass


class BlobAlreadyExists(BlobStoreError):
    pass


class BlobMissing(BlobStoreError):
    pass


class FileSystemBlobStore:
    """Raw immutable ciphertext files addressed only by validated UUIDs."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def path_for(self, user_id: UUID, blob_id: UUID) -> Path:
        return self._root / user_id.hex / f'{blob_id.hex}.blob'

    def create(self, user_id: UUID, blob_id: UUID, ciphertext: bytes) -> None:
        target = self.path_for(user_id, blob_id)
        directory = target.parent
        try:
            directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            descriptor, temporary_name = tempfile.mkstemp(prefix='.upload-', dir=directory)
            temporary = Path(temporary_name)
            try:
                with os.fdopen(descriptor, 'wb') as output:
                    output.write(ciphertext)
                    output.flush()
                    os.fsync(output.fileno())
                try:
                    os.link(temporary, target)
                except FileExistsError as error:
                    raise BlobAlreadyExists() from error
            finally:
                temporary.unlink(missing_ok=True)
        except BlobAlreadyExists:
            raise
        except OSError as error:
            raise BlobStoreError() from error

    def read_verified(self, user_id: UUID, blob_id: UUID, size: int, digest: bytes) -> bytes:
        target = self.path_for(user_id, blob_id)
        try:
            with target.open('rb') as source:
                data = source.read(size + 1)
        except FileNotFoundError as error:
            raise BlobMissing() from error
        except OSError as error:
            raise BlobStoreError() from error
        if len(data) != size or hashlib.sha256(data).digest() != digest:
            raise BlobStoreError()
        return data

    def remove_if_present(self, user_id: UUID, blob_id: UUID) -> None:
        try:
            self.path_for(user_id, blob_id).unlink(missing_ok=True)
        except OSError:
            pass
