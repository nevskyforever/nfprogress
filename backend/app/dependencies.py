from __future__ import annotations

import secrets
from dataclasses import dataclass

from fastapi import Header, HTTPException, Request, status


@dataclass(slots=True)
class Services:
    repository: object
    projects: object
    notes_class: type
    game: object
    settings: object
    content: object
    integrations: object
    documents: object


def get_services(request: Request) -> Services:
    return request.app.state.services


def require_session(
        request: Request,
        token: str | None = Header(default=None, alias='X-NFProgress-Token'),
) -> None:
    expected = request.app.state.runtime_config.session_token
    if expected is None:
        return
    if token is None or not secrets.compare_digest(token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={'code': 'invalid_session', 'message': 'Недействительная сессия.'},
        )
