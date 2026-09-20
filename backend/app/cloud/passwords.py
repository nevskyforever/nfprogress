from __future__ import annotations

from pwdlib import PasswordHash


MIN_PASSWORD_LENGTH = 15
MAX_PASSWORD_LENGTH = 1024


class PasswordService:
    """Argon2id password handling; plaintext never leaves this boundary."""

    def __init__(self) -> None:
        self._password_hash = PasswordHash.recommended()
        self._dummy_hash = self._password_hash.hash('nfprogress-dummy-password')

    def validate_new_password(self, password: str) -> None:
        length = len(password)
        if not MIN_PASSWORD_LENGTH <= length <= MAX_PASSWORD_LENGTH:
            raise ValueError('Password does not satisfy the length policy.')

    def hash(self, password: str) -> str:
        self.validate_new_password(password)
        return self._password_hash.hash(password)

    def verify(self, password: str, password_hash: str) -> tuple[bool, str | None]:
        return self._password_hash.verify_and_update(password, password_hash)

    def verify_dummy(self, password: str) -> None:
        self._password_hash.verify(password, self._dummy_hash)
