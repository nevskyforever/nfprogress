import argparse
import os
import sys
from pathlib import Path

from updater_core import UpdateError, configure_logging, install_update


def _default_log_path() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    base_dir = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
    return base_dir / "nfprogress" / "logs" / "updater.log"


def _show_error(message: str) -> None:
    if os.name != "nt":
        return
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, message, "Обновление NFProgress", 0x10)
    except (AttributeError, OSError) as error:
        print(f"Не удалось показать системное сообщение: {error}", file=sys.stderr)


def _desktop_directory() -> Path:
    if os.name == "nt":
        try:
            import ctypes

            buffer = ctypes.create_unicode_buffer(260)
            if ctypes.windll.shell32.SHGetFolderPathW(None, 0x10, None, 0, buffer) == 0:
                return Path(buffer.value)
        except (AttributeError, OSError):
            return Path.home() / "Desktop"
    return Path.home() / "Desktop"


def _create_desktop_shortcut(executable: Path) -> Path:
    desktop = _desktop_directory()
    desktop.mkdir(parents=True, exist_ok=True)
    shortcut = desktop / "NFProgress.url"
    shortcut.write_text(
        "[InternetShortcut]\n"
        f"URL={executable.resolve().as_uri()}\n"
        f"IconFile={executable.resolve()}\n"
        "IconIndex=0\n",
        encoding="utf-8",
        newline="\r\n",
    )
    return shortcut


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Безопасное обновление NFProgress")
    parser.add_argument("--app-dir", required=True, type=Path)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--pid", required=True, type=int)
    parser.add_argument("--current-version", required=True)
    parser.add_argument("--new-version", required=True)
    parser.add_argument("--legacy-executable", type=Path)
    parser.add_argument("--create-shortcut", action="store_true")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    logger = configure_logging(_default_log_path())
    logger.info(
        "Запуск обновления NFProgress %s -> %s; app_dir=%s",
        args.current_version,
        args.new_version,
        args.app_dir,
    )
    print(f"NFProgress обновляется: {args.current_version} → {args.new_version}", flush=True)
    print("Не закрывайте это окно до завершения обновления.", flush=True)
    try:
        install_update(args.app_dir, args.archive, args.sha256, args.pid, logger)
    except (OSError, UpdateError, ValueError) as error:
        logger.exception("Обновление завершилось ошибкой")
        message = f"Не удалось обновить NFProgress.\n\n{error}\n\nПодробности: {_default_log_path()}"
        print(message, file=sys.stderr, flush=True)
        _show_error(message)
        return 1

    logger.info("Обновление успешно завершено")
    args.archive.unlink(missing_ok=True)
    if args.create_shortcut:
        try:
            shortcut = _create_desktop_shortcut(args.app_dir / "nfprogress.exe")
            logger.info("Создан ярлык %s", shortcut)
        except OSError as error:
            logger.warning("Не удалось создать ярлык: %s", error)
    if args.legacy_executable:
        message = (
            "Новая standalone-версия установлена и запущена.\n\n"
            f"Старый файл можно удалить вручную:\n{args.legacy_executable}"
        )
        print(message, flush=True)
        if os.name == "nt":
            try:
                import ctypes

                ctypes.windll.user32.MessageBoxW(None, message, "Обновление NFProgress", 0x40)
            except (AttributeError, OSError) as error:
                logger.warning("Не удалось показать сообщение о миграции: %s", error)
    else:
        print("Обновление установлено. NFProgress запущен.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
