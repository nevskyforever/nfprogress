from __future__ import annotations

import argparse
import ipaddress
import os
import threading
import time
from pathlib import Path

import uvicorn

import engine

from .config import RuntimeConfig
from .main import create_app


def _positive_pid(value: str) -> int:
    pid = int(value)
    if pid <= 0:
        raise argparse.ArgumentTypeError('parent PID must be positive')
    return pid


def _process_is_running(pid: int) -> bool:
    """Return whether a process exists without sending it a terminating signal."""
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes

        process_query_limited_information = 0x1000
        still_active = 259
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        handle = kernel32.OpenProcess(
            process_query_limited_information, False, pid,
        )
        if not handle:
            return False
        try:
            exit_code = wintypes.DWORD()
            return bool(kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))) \
                and exit_code.value == still_active
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _watch_parent_process(
        parent_pid: int,
        *,
        interval: float = 0.5,
        exit_process=os._exit,
) -> None:
    while _process_is_running(parent_pid):
        time.sleep(interval)
    exit_process(0)


def _start_parent_watchdog(parent_pid: int) -> None:
    threading.Thread(
        target=_watch_parent_process,
        args=(parent_pid,),
        name='nfprogress-parent-watchdog',
        daemon=True,
    ).start()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Run the nfprogress API backend.')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', default=8000, type=int)
    parser.add_argument('--data-dir', type=Path)
    parser.add_argument(
        '--dev-data',
        action='store_true',
        help=(
            'Use the same synchronized test_data directory as the source '
            'PySide6 developer mode.'
        ),
    )
    parser.add_argument(
        '--prepare-dev-data',
        action='store_true',
        help='Refresh the canonical test_data profile through the Tauri migration contract and exit.',
    )
    parser.add_argument(
        '--parent-pid',
        type=_positive_pid,
        help='Exit automatically if the owning Tauri process disappears.',
    )
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
    if args.prepare_dev_data:
        if args.dev_data or args.data_dir is not None:
            raise SystemExit('--prepare-dev-data cannot be combined with --dev-data or --data-dir.')
        report = engine.refresh_test_data()
        print(
            f'Prepared Tauri dev data: {report.preview.projects} projects, '
            f'{report.preview.stages} stages, {report.preview.progress_entries} progress entries.'
        )
        return 0
    if args.dev_data and args.data_dir is not None:
        raise SystemExit('--dev-data cannot be combined with --data-dir.')
    environment = RuntimeConfig.from_env()
    developer_mode = args.dev_data or environment.developer_mode
    # The Tauri sidecar is packaged, so the legacy import-time check cannot
    # distinguish its explicitly requested development data from a release run.
    # Keep the legacy test-clock and developer safeguards enabled in that mode.
    if developer_mode:
        engine.dev_mode = True
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
    development_data_dir = None
    if args.dev_data:
        # Keep the new local clients aligned with ``python main_UI.py``:
        # refresh the safe developer copy from the real stores, then let all
        # requests use that copy. The source files are never overwritten.
        engine.refresh_test_data()
        development_data_dir = engine.get_test_data_dir()
    config = RuntimeConfig(
        data_dir=development_data_dir or args.data_dir or environment.data_dir,
        session_token=session_token,
        allowed_origins=environment.allowed_origins,
        platform=platform,
        allow_local_files=(platform == 'desktop'),
        developer_mode=developer_mode,
    )
    if args.parent_pid is not None:
        _start_parent_watchdog(args.parent_pid)
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
