from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


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


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    data_dir: Path | None = None
    session_token: str | None = None
    allowed_origins: tuple[str, ...] = DEFAULT_ORIGINS
    platform: str = 'web'
    allow_local_files: bool = False

    @classmethod
    def from_env(cls) -> 'RuntimeConfig':
        raw_data_dir = os.environ.get('NFPROGRESS_DATA_DIR')
        raw_origins = os.environ.get('NFPROGRESS_ALLOWED_ORIGINS')
        platform = os.environ.get('NFPROGRESS_PLATFORM', 'web').lower()
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
        )
