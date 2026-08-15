"""Domain-level errors shared by services and transport adapters."""

from __future__ import annotations


class DomainError(Exception):
    """An expected application error with a stable machine-readable code."""

    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code

    def as_dict(self) -> dict[str, str]:
        return {'code': self.code, 'message': self.message}


class NotFoundError(DomainError):
    def __init__(
        self,
        code: str,
        message: str | None = None,
        status_code: int = 404,
    ) -> None:
        if message is None:
            message, code = code, 'not_found'
        super().__init__(code, message, status_code)


class ConflictError(DomainError):
    def __init__(
        self,
        code: str,
        message: str | None = None,
        status_code: int = 409,
    ) -> None:
        if message is None:
            message, code = code, 'conflict'
        super().__init__(code, message, status_code)


class ValidationError(DomainError):
    def __init__(
        self,
        code: str,
        message: str | None = None,
        status_code: int = 422,
    ) -> None:
        if message is None:
            message, code = code, 'validation_error'
        super().__init__(code, message, status_code)


__all__ = [
    'ConflictError',
    'DomainError',
    'NotFoundError',
    'ValidationError',
]
