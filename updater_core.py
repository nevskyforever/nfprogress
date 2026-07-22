import hashlib
import logging
import os
import shutil
import stat
import subprocess
import sys
import time
import zipfile
from pathlib import Path, PurePosixPath


APP_DIR_NAME = "nfprogress"
MAIN_EXECUTABLE = "nfprogress.exe"
UPDATER_EXECUTABLE = "nfprogress-updater.exe"
ARCHIVE_ROOT = APP_DIR_NAME
MAX_ARCHIVE_FILES = 20_000
MAX_EXTRACTED_SIZE = 2 * 1024 * 1024 * 1024
MIN_FREE_SPACE_MARGIN = 100 * 1024 * 1024
PROCESS_EXIT_TIMEOUT = 180.0
STARTUP_CHECK_SECONDS = 3.0


class UpdateError(RuntimeError):
    pass


def configure_logging(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("nfprogress.updater")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    return logger


def calculate_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def verify_sha256(path: Path, expected_sha256: str) -> None:
    expected = str(expected_sha256).strip().lower()
    if len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected):
        raise UpdateError("Ожидаемый SHA-256 имеет неверный формат.")
    actual = calculate_sha256(path)
    if actual != expected:
        raise UpdateError(f"SHA-256 архива не совпадает: ожидался {expected}, получен {actual}.")


def _safe_member_path(member_name: str, destination: Path) -> Path:
    if not member_name or "\\" in member_name:
        raise UpdateError(f"Недопустимый путь в архиве: {member_name!r}.")

    archive_path = PurePosixPath(member_name)
    if archive_path.is_absolute() or ".." in archive_path.parts:
        raise UpdateError(f"Недопустимый путь в архиве: {member_name!r}.")
    if not archive_path.parts or archive_path.parts[0] != ARCHIVE_ROOT:
        raise UpdateError("ZIP должен содержать единственную корневую папку nfprogress/.")
    reserved_names = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
    for part in archive_path.parts:
        stem = part.split(".", 1)[0].upper()
        if not part or ":" in part or part.endswith((" ", ".")) or stem in reserved_names:
            raise UpdateError(f"Недопустимый Windows-путь в архиве: {member_name!r}.")

    target = (destination / Path(*archive_path.parts)).resolve()
    destination_resolved = destination.resolve()
    try:
        target.relative_to(destination_resolved)
    except ValueError as error:
        raise UpdateError(f"Файл выходит за пределы папки распаковки: {member_name!r}.") from error
    return target


def inspect_archive(
    archive_path: Path,
    destination: Path,
    *,
    max_files: int = MAX_ARCHIVE_FILES,
    max_extracted_size: int = MAX_EXTRACTED_SIZE,
) -> tuple[list[tuple[zipfile.ZipInfo, Path]], int]:
    try:
        archive = zipfile.ZipFile(archive_path)
    except (OSError, zipfile.BadZipFile) as error:
        raise UpdateError("Архив обновления повреждён или не является ZIP-файлом.") from error

    with archive:
        members = archive.infolist()
        if not members:
            raise UpdateError("Архив обновления пуст.")
        if len(members) > max_files:
            raise UpdateError(f"В архиве слишком много файлов: {len(members)} (лимит {max_files}).")

        checked: list[tuple[zipfile.ZipInfo, Path]] = []
        total_size = 0
        roots = set()
        seen_paths = set()
        for member in members:
            target = _safe_member_path(member.filename, destination)
            parts = PurePosixPath(member.filename).parts
            roots.add(parts[0])

            normalized_name = PurePosixPath(member.filename).as_posix().rstrip("/").casefold()
            if normalized_name in seen_paths:
                raise UpdateError(f"Повторяющийся путь в архиве: {member.filename!r}.")
            seen_paths.add(normalized_name)
            if member.flag_bits & 0x1:
                raise UpdateError(f"Зашифрованные файлы в архиве запрещены: {member.filename!r}.")

            unix_mode = member.external_attr >> 16
            if stat.S_ISLNK(unix_mode):
                raise UpdateError(f"Символические ссылки в архиве запрещены: {member.filename!r}.")

            if not member.is_dir():
                total_size += member.file_size
                if total_size > max_extracted_size:
                    raise UpdateError(
                        f"Распакованный размер превышает лимит {max_extracted_size} байт."
                    )
            checked.append((member, target))

        if roots != {ARCHIVE_ROOT}:
            raise UpdateError("ZIP должен содержать единственную корневую папку nfprogress/.")

        names = {PurePosixPath(member.filename).as_posix().rstrip("/") for member in members}
        required = {
            f"{ARCHIVE_ROOT}/{MAIN_EXECUTABLE}",
            f"{ARCHIVE_ROOT}/{UPDATER_EXECUTABLE}",
            f"{ARCHIVE_ROOT}/updater-runtime/{UPDATER_EXECUTABLE}",
        }
        missing = sorted(required - names)
        if missing:
            raise UpdateError(f"В архиве отсутствуют обязательные файлы: {', '.join(missing)}.")
        return checked, total_size


def extract_archive_safely(archive_path: Path, destination: Path) -> Path:
    checked, total_size = inspect_archive(archive_path, destination)
    free_space = shutil.disk_usage(destination.parent).free
    required_space = total_size + MIN_FREE_SPACE_MARGIN
    if free_space < required_space:
        raise UpdateError(
            f"Недостаточно места для обновления: требуется не менее {required_space} байт, "
            f"доступно {free_space}."
        )

    destination.mkdir(parents=True, exist_ok=False)
    try:
        with zipfile.ZipFile(archive_path) as archive:
            for member, target in checked:
                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member, "r") as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output, length=1024 * 1024)
        extracted_root = destination / ARCHIVE_ROOT
        if not (extracted_root / MAIN_EXECUTABLE).is_file():
            raise UpdateError(f"После распаковки не найден {MAIN_EXECUTABLE}.")
        if not (extracted_root / UPDATER_EXECUTABLE).is_file():
            raise UpdateError(f"После распаковки не найден {UPDATER_EXECUTABLE}.")
        return extracted_root
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise


def _pid_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        process_query_limited_information = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(process_query_limited_information, False, pid)
        if not handle:
            return False
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def wait_for_process_exit(pid: int, timeout: float = PROCESS_EXIT_TIMEOUT) -> None:
    deadline = time.monotonic() + timeout
    while _pid_exists(pid):
        if time.monotonic() >= deadline:
            raise UpdateError(f"Приложение с PID {pid} не завершилось за {timeout:.0f} секунд.")
        time.sleep(0.25)


def validate_paths(app_dir: Path, archive_path: Path) -> tuple[Path, Path]:
    app_dir = app_dir.expanduser().resolve()
    archive_path = archive_path.expanduser().resolve()
    if not archive_path.is_file():
        raise UpdateError(f"Архив обновления не найден: {archive_path}.")
    if app_dir == Path(app_dir.anchor):
        raise UpdateError("Корень диска нельзя использовать как папку приложения.")
    if app_dir.name.casefold() != APP_DIR_NAME.casefold():
        raise UpdateError(f"Папка приложения должна называться {APP_DIR_NAME}.")
    if archive_path.name != "nfprogress-update.zip":
        raise UpdateError("Архив должен иметь предсказуемое имя nfprogress-update.zip.")
    if not app_dir.parent.is_dir():
        raise UpdateError(f"Родительская папка установки не существует: {app_dir.parent}.")
    try:
        archive_path.relative_to(app_dir)
    except ValueError:
        pass
    else:
        raise UpdateError("Архив обновления должен находиться вне заменяемой папки приложения.")
    return app_dir, archive_path


def launch_application(executable: Path) -> subprocess.Popen:
    return subprocess.Popen([str(executable)], cwd=str(executable.parent))


def _verify_started(process: subprocess.Popen, seconds: float | None = None) -> None:
    if seconds is None:
        seconds = STARTUP_CHECK_SECONDS
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        return_code = process.poll()
        if return_code is not None:
            raise UpdateError(f"Новая версия завершилась сразу после запуска (код {return_code}).")
        time.sleep(0.1)


def install_update(
    app_dir: Path,
    archive_path: Path,
    expected_sha256: str,
    parent_pid: int,
    logger: logging.Logger,
    *,
    process_timeout: float = PROCESS_EXIT_TIMEOUT,
    launcher=launch_application,
) -> None:
    app_dir, archive_path = validate_paths(app_dir, archive_path)
    updater_path = Path(sys.executable).resolve()
    try:
        updater_path.relative_to(app_dir)
    except ValueError:
        pass
    else:
        raise UpdateError("Updater нельзя запускать из заменяемой папки приложения.")

    logger.info("Проверка SHA-256 архива %s", archive_path)
    verify_sha256(archive_path, expected_sha256)
    logger.info("Ожидание завершения основного процесса PID=%s", parent_pid)
    wait_for_process_exit(parent_pid, process_timeout)

    staging_dir = app_dir.parent / f".{APP_DIR_NAME}-update-staging"
    backup_dir = app_dir.parent / f".{APP_DIR_NAME}-backup"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    if backup_dir.exists():
        if app_dir.exists() and (app_dir / MAIN_EXECUTABLE).is_file():
            shutil.rmtree(backup_dir)
        elif not app_dir.exists():
            logger.warning("Восстановление оставшейся резервной копии %s", backup_dir)
            backup_dir.replace(app_dir)

    logger.info("Безопасная распаковка в %s", staging_dir)
    extracted_root = extract_archive_safely(archive_path, staging_dir)
    moved_old = False
    installed_new = False
    try:
        if app_dir.exists():
            logger.info("Перемещение текущей версии в %s", backup_dir)
            app_dir.replace(backup_dir)
            moved_old = True

        logger.info("Установка подготовленной версии в %s", app_dir)
        extracted_root.replace(app_dir)
        installed_new = True
        executable = app_dir / MAIN_EXECUTABLE
        if not executable.is_file():
            raise UpdateError(f"После установки не найден {executable}.")

        logger.info("Запуск новой версии %s", executable)
        process = launcher(executable)
        _verify_started(process)
        logger.info("Новая версия успешно запущена, PID=%s", getattr(process, "pid", "unknown"))
    except Exception:
        logger.exception("Установка не удалась, выполняется откат")
        if installed_new and app_dir.exists():
            failed_dir = app_dir.parent / f".{APP_DIR_NAME}-failed"
            if failed_dir.exists():
                shutil.rmtree(failed_dir, ignore_errors=True)
            try:
                app_dir.replace(failed_dir)
            except OSError:
                shutil.rmtree(app_dir, ignore_errors=True)
        if moved_old and backup_dir.exists() and not app_dir.exists():
            backup_dir.replace(app_dir)
        raise
    else:
        if backup_dir.exists():
            try:
                shutil.rmtree(backup_dir)
            except OSError as error:
                logger.warning("Не удалось удалить резервную папку %s: %s", backup_dir, error)
        failed_dir = app_dir.parent / f".{APP_DIR_NAME}-failed"
        if failed_dir.exists():
            shutil.rmtree(failed_dir, ignore_errors=True)
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)
