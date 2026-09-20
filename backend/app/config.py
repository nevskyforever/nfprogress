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
    public_web_url: str | None = None
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_username: str | None = None
    smtp_password: str | None = field(default=None, repr=False)
    smtp_from_email: str | None = None
    smtp_from_name: str | None = None
    smtp_security: str | None = None

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
        smtp_values = (self.smtp_host, self.smtp_port, self.smtp_username,
                       self.smtp_password, self.smtp_from_email, self.smtp_security)
        if any(value is not None for value in smtp_values):
            if not all(value is not None for value in smtp_values):
                raise ValueError('SMTP configuration must be complete when enabled.')
            if self.smtp_security not in {'starttls', 'implicit_tls'}:
                raise ValueError('NFPROGRESS_SMTP_SECURITY must be starttls or implicit_tls.')
            if self.smtp_port is None or not 1 <= self.smtp_port <= 65535:
                raise ValueError('NFPROGRESS_SMTP_PORT must be a valid TCP port.')
            if self.public_web_url is None or urlsplit(self.public_web_url).scheme != 'https':
                raise ValueError('NFPROGRESS_PUBLIC_WEB_URL must use HTTPS when SMTP is enabled.')

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
            public_web_url=os.environ.get('NFPROGRESS_PUBLIC_WEB_URL') or None,
            smtp_host=os.environ.get('NFPROGRESS_SMTP_HOST') or None,
            smtp_port=int(os.environ['NFPROGRESS_SMTP_PORT']) if os.environ.get('NFPROGRESS_SMTP_PORT') else None,
            smtp_username=os.environ.get('NFPROGRESS_SMTP_USERNAME') or None,
            smtp_password=os.environ.get('NFPROGRESS_SMTP_PASSWORD') or None,
            smtp_from_email=os.environ.get('NFPROGRESS_SMTP_FROM_EMAIL') or None,
            smtp_from_name=os.environ.get('NFPROGRESS_SMTP_FROM_NAME') or None,
            smtp_security=os.environ.get('NFPROGRESS_SMTP_SECURITY') or None,
        )
