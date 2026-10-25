from __future__ import annotations

from threading import BoundedSemaphore, Lock

from pwdlib import PasswordHash


MIN_PASSWORD_LENGTH = 15
MAX_PASSWORD_LENGTH = 1024
ARGON2_CONCURRENT_OPERATIONS = 1
ARGON2_WAIT_TIMEOUT_SECONDS = 2


class PasswordCapacityError(RuntimeError):
    """The process is already performing its permitted Argon2 work."""


class PasswordService:
    """Argon2id password handling; plaintext never leaves this boundary."""

    _slots = BoundedSemaphore(ARGON2_CONCURRENT_OPERATIONS)
    _dummy_lock = Lock()
    _shared_dummy_hash: str | None = None

    def __init__(self) -> None:
        self._password_hash = PasswordHash.recommended()
        with self._dummy_lock:
            if type(self)._shared_dummy_hash is None:
                type(self)._shared_dummy_hash = self._run_limited(
                    self._password_hash.hash, 'nfprogress-dummy-password')
        self._dummy_hash = type(self)._shared_dummy_hash

    @classmethod
    def _run_limited(cls, operation, *args):
        if not cls._slots.acquire(timeout=ARGON2_WAIT_TIMEOUT_SECONDS):
            raise PasswordCapacityError('Password processing capacity is unavailable.')
        try:
            return operation(*args)
        finally:
            cls._slots.release()

    def validate_new_password(self, password: str) -> None:
        length = len(password)
        if not MIN_PASSWORD_LENGTH <= length <= MAX_PASSWORD_LENGTH:
            raise ValueError('Password does not satisfy the length policy.')

    def hash(self, password: str) -> str:
        self.validate_new_password(password)
        return self._run_limited(self._password_hash.hash, password)

    def verify(self, password: str, password_hash: str) -> tuple[bool, str | None]:
        return self._run_limited(self._password_hash.verify_and_update, password, password_hash)

    def verify_dummy(self, password: str) -> None:
        self._run_limited(self._password_hash.verify, password, self._dummy_hash)
