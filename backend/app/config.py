from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit


DEFAULT_ORIGINS = (
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'tauri://localhost',
    'http://tauri.localhost',
    'https://tauri.localhost',
    'capacitor://localhost',
    'http://localhost',
    'https://localhost',
)

RUNTIME_ENVIRONMENTS = frozenset({'development', 'test', 'production'})
POSTGRESQL_URL_SCHEME = 'postgresql+psycopg'


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    data_dir: Path | None = None
    session_token: str | None = None
    allowed_origins: tuple[str, ...] = DEFAULT_ORIGINS
    platform: str = 'web'
    allow_local_files: bool = False
    developer_mode: bool = False
    environment: str = 'development'
    database_url: str | None = field(default=None, repr=False)
    auth_secret: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.environment not in RUNTIME_ENVIRONMENTS:
            allowed = ', '.join(sorted(RUNTIME_ENVIRONMENTS))
            raise ValueError(f'NFPROGRESS_ENV must be one of: {allowed}.')
        if self.database_url is not None:
            self._validate_database_url(self.database_url)
        if self.environment == 'production' and self.database_url is None:
            raise ValueError(
                'NFPROGRESS_DATABASE_URL is required in production.',
            )
        if self.environment == 'production' and self.auth_secret is None:
            raise ValueError('NFPROGRESS_AUTH_SECRET is required in production.')
        if self.auth_secret is not None and len(self.auth_secret) < 32:
            raise ValueError('NFPROGRESS_AUTH_SECRET must contain at least 32 characters.')

    @staticmethod
    def _validate_database_url(database_url: str) -> None:
        if not database_url.strip():
            raise ValueError('NFPROGRESS_DATABASE_URL must not be empty.')
        if urlsplit(database_url).scheme != POSTGRESQL_URL_SCHEME:
            raise ValueError(
                'NFPROGRESS_DATABASE_URL must use a PostgreSQL psycopg URL.',
            )

    def require_database_url(self) -> str:
        """Return the configured cloud PostgreSQL URL without exposing it in errors."""
        if self.database_url is None:
            raise RuntimeError('NFPROGRESS_DATABASE_URL is not configured.')
        return self.database_url

    def require_auth_secret(self) -> str:
        if self.auth_secret is None:
            raise RuntimeError('NFPROGRESS_AUTH_SECRET is not configured.')
        return self.auth_secret

    @classmethod
    def from_env(cls) -> 'RuntimeConfig':
        raw_data_dir = os.environ.get('NFPROGRESS_DATA_DIR')
        raw_origins = os.environ.get('NFPROGRESS_ALLOWED_ORIGINS')
        platform = os.environ.get('NFPROGRESS_PLATFORM', 'web').lower()
        environment = os.environ.get('NFPROGRESS_ENV', 'development').lower()
        return cls(
            data_dir=Path(raw_data_dir).expanduser() if raw_data_dir else None,
            session_token=os.environ.get('NFPROGRESS_SESSION_TOKEN') or None,
            allowed_origins=(
                tuple(origin.strip() for origin in raw_origins.split(',') if origin.strip())
                if raw_origins else DEFAULT_ORIGINS
            ),
            platform=platform,
            allow_local_files=(
                platform == 'desktop'
                or os.environ.get('NFPROGRESS_ALLOW_LOCAL_FILES') == '1'
            ),
            developer_mode=os.environ.get('NFPROGRESS_DEVELOPER_MODE') == '1',
            environment=environment,
            database_url=os.environ.get('NFPROGRESS_DATABASE_URL') or None,
            auth_secret=os.environ.get('NFPROGRESS_AUTH_SECRET') or None,
        )
