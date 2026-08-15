from __future__ import annotations

import argparse
import ipaddress
import os
from pathlib import Path

import uvicorn

from .config import RuntimeConfig
from .main import create_app


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Run the nfprogress API backend.')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', default=8000, type=int)
    parser.add_argument('--data-dir', type=Path)
    parser.add_argument(
        '--platform', choices=('web', 'desktop', 'ios', 'android'), default=None,
    )
    parser.add_argument(
        '--allow-remote',
        action='store_true',
        help=(
            'Explicitly allow an unauthenticated non-loopback bind for a '
            'deployment protected by an external HTTPS/authentication layer.'
        ),
    )
    parser.add_argument('--log-level', default='info')
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    environment = RuntimeConfig.from_env()
    platform = args.platform or environment.platform
    session_token = environment.session_token
    try:
        loopback_host = ipaddress.ip_address(args.host).is_loopback
    except ValueError:
        loopback_host = args.host.casefold() == 'localhost'
    if not loopback_host:
        if session_token or platform == 'desktop':
            raise SystemExit(
                'A desktop session-token backend must listen on loopback only.',
            )
        if not args.allow_remote:
            raise SystemExit(
                'A non-loopback bind requires the explicit --allow-remote flag '
                'and an external HTTPS/authentication layer.',
            )
    config = RuntimeConfig(
        data_dir=args.data_dir or environment.data_dir,
        session_token=session_token,
        allowed_origins=environment.allowed_origins,
        platform=platform,
        allow_local_files=(platform == 'desktop'),
    )
    uvicorn.run(
        create_app(config),
        host=args.host,
        port=args.port,
        log_level=args.log_level,
        access_log=os.environ.get('NFPROGRESS_ACCESS_LOG') == '1',
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
