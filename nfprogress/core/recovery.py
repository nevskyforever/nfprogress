"""Bounded local backup and restore primitives for migration tooling.

This module is intentionally not imported by the Tauri runtime.  It is the
trusted side of a separately packaged migration/recovery helper: it validates
inputs before activation, keeps the previous profile, and never treats legacy
pickle files as a SQLite fallback.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

from nfprogress.core.sqlite.schema import CURRENT_SCHEMA_VERSION


BACKUP_MANIFEST = "backup_manifest.json"
BACKUP_MANIFEST_VERSION = 1
BACKUP_FILE_LIMIT = 32
BACKUP_MANIFEST_LIMIT = 16 * 1024 * 1024
MIGRATION_JSON_LIMIT = 100 * 1024 * 1024
MIGRATION_MAX_DEPTH = 64
MIGRATION_MAX_ENTITIES = 100_000
MIGRATION_MAX_STRING = 1_000_000
KNOWN_PROFILE_FILES = frozenset({
    "nfprogress.db",
    "data.pkl",
    "settings.pkl",
    "gamer.pkl",
    "documents.json",
    "external_file_manifest.json",
})


class RecoveryError(RuntimeError):
    """A backup, database, or migration input cannot be trusted."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json_loads(value: str | bytes, *, label: str) -> Any:
    try:
        return json.loads(value, parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"non-finite JSON constant: {token}")
        ))
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise RecoveryError(f"{label} is not valid JSON") from error


def _safe_relative_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise RecoveryError(f"unsafe backup path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.parts != (path.name,):
        raise RecoveryError(f"unsafe backup path: {value!r}")
    if value not in KNOWN_PROFILE_FILES:
        raise RecoveryError(f"unknown backup file: {value!r}")
    return value


def _fsync_file(path: Path) -> None:
    with path.open("rb") as stream:
        os.fsync(stream.fileno())


def _directory_fsync_supported() -> bool:
    """Return whether this platform supports fsync on an opened directory."""
    return os.name == "posix"


def _fsync_directory(path: Path) -> None:
    # POSIX directory descriptors provide the durability barrier for renames.
    # Windows does not expose a fsync-able directory descriptor: os.open may
    # succeed, but os.fsync then raises [Errno 9] Bad file descriptor. Windows
    # keeps the file fsyncs above and relies on os.replace/MoveFileEx for the
    # atomic rename; a failed replace remains fail-closed and preserves source.
    if not _directory_fsync_supported():
        return
    try:
        flags = os.O_RDONLY
        if hasattr(os, "O_DIRECTORY"):
            flags |= os.O_DIRECTORY
        descriptor = os.open(path, flags)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_copy(source: Path, destination: Path) -> None:
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.unlink(missing_ok=True)
    try:
        with source.open("rb") as input_stream, temporary.open("xb") as output_stream:
            shutil.copyfileobj(input_stream, output_stream, length=1024 * 1024)
            output_stream.flush()
            os.fsync(output_stream.fileno())
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _external_manifest(root: Path) -> list[dict[str, Any]]:
    database = root / "nfprogress.db"
    if not database.is_file():
        return []
    try:
        connection = sqlite3.connect(database)
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT document_id, binding_type, external_path, source_id, "
            "last_external_hash, last_synced_revision, last_synced_hash, "
            "last_synced_at, sync_state FROM document_bindings ORDER BY document_id"
        ).fetchall()
    except sqlite3.Error:
        return []
    finally:
        try:
            connection.close()
        except UnboundLocalError:
            pass
    return [
        {
            **dict(row),
            "exists": bool(row["external_path"] and Path(row["external_path"]).is_file()),
        }
        for row in rows
    ]


def _profile_files(root: Path, names: Iterable[str] | None) -> list[Path]:
    requested = set(names) if names is not None else {"data.pkl", "settings.pkl", "gamer.pkl"}
    # The reference manifest is a source artifact when a bridge/helper has
    # already recorded external bindings.  It is intentionally not a scan of
    # arbitrary user files.
    selected = {"nfprogress.db", "documents.json", "external_file_manifest.json", *requested}
    unknown = selected - KNOWN_PROFILE_FILES
    if unknown:
        raise RecoveryError(f"unknown profile files: {sorted(unknown)!r}")
    return sorted((root / name for name in selected if (root / name).is_file()), key=lambda p: p.name)


def source_fingerprint(root: str | Path) -> str:
    """Return a stable fingerprint of the available profile inputs."""
    base = Path(root).expanduser().resolve()
    digest = hashlib.sha256()
    for path in _profile_files(base, None):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(sha256_file(path)))
        digest.update(b"\0")
    return digest.hexdigest()


def create_application_backup(
    root: str | Path,
    names: Iterable[str] | None = None,
) -> Path:
    """Create a sealed application-state snapshot without exposing a partial dir."""
    base = Path(root).expanduser().resolve()
    base.mkdir(parents=True, exist_ok=True)
    files = _profile_files(base, names)
    backups = base / "backups"
    backups.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    destination = backups / timestamp
    suffix = 1
    while destination.exists():
        destination = backups / f"{timestamp}-{suffix}"
        suffix += 1
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}-", dir=backups))
    try:
        manifest_files: list[dict[str, Any]] = []
        for source in files:
            target = staging / source.name
            _atomic_copy(source, target)
            manifest_files.append({
                "path": source.name,
                "size": target.stat().st_size,
                "sha256": sha256_file(target),
            })
        external = _external_manifest(base)
        if (base / "nfprogress.db").is_file():
            external_path = staging / "external_file_manifest.json"
            external_path.write_text(
                json.dumps(external, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                encoding="utf-8",
            )
            _fsync_file(external_path)
            existing = next((item for item in manifest_files if item["path"] == external_path.name), None)
            if existing is None:
                manifest_files.append({
                    "path": external_path.name,
                    "size": external_path.stat().st_size,
                    "sha256": sha256_file(external_path),
                })
            else:
                existing.update(size=external_path.stat().st_size, sha256=sha256_file(external_path))
        database = base / "nfprogress.db"
        schema_version: int | None = None
        if database.is_file():
            try:
                with sqlite3.connect(database) as connection:
                    schema_version = connection.execute(
                        "SELECT schema_version FROM schema_info LIMIT 1"
                    ).fetchone()[0]
            except (sqlite3.Error, TypeError, IndexError):
                # A corrupt DB is still preserved as a recovery artifact. It
                # is rejected by validate_sqlite_file before any restore.
                schema_version = None
        manifest = {
            "manifest_version": BACKUP_MANIFEST_VERSION,
            "kind": "application-state",
            "created_at": _utc_now(),
            "app_version": _app_version(),
            "schema_version": schema_version,
            "source_fingerprint": source_fingerprint(base),
            "external_files_are_references": True,
            "files": sorted(manifest_files, key=lambda item: item["path"]),
        }
        manifest_path = staging / BACKUP_MANIFEST
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        _fsync_file(manifest_path)
        _fsync_directory(staging)
        staging.replace(destination)
        _fsync_directory(backups)
        return destination
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _app_version() -> str:
    try:
        import engine

        return str(engine.version)
    except (ImportError, AttributeError):
        return "unknown"


def _read_backup_manifest(backup: Path) -> dict[str, Any]:
    manifest_path = backup / BACKUP_MANIFEST
    if not manifest_path.is_file():
        return {"manifest_version": 0, "legacy_unsealed": True, "files": []}
    if manifest_path.stat().st_size > BACKUP_MANIFEST_LIMIT:
        raise RecoveryError("backup manifest is too large")
    value = _json_loads(manifest_path.read_bytes(), label="backup manifest")
    if not isinstance(value, dict) or value.get("manifest_version") != BACKUP_MANIFEST_VERSION:
        raise RecoveryError("unsupported backup manifest version")
    return value


def validate_sqlite_file(path: str | Path, *, allow_versions: Iterable[int] | None = None) -> int:
    """Validate SQLite without applying migrations or consulting legacy files."""
    database = Path(path).expanduser().resolve()
    if not database.is_file():
        raise RecoveryError("missing_sqlite")
    uri = f"file:{database.as_posix()}?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True)
        connection.row_factory = sqlite3.Row
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RecoveryError(f"corrupt_sqlite: integrity_check={integrity}")
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise RecoveryError("corrupt_sqlite: foreign_key_check failed")
        rows = connection.execute("SELECT schema_version FROM schema_info").fetchall()
        if len(rows) != 1:
            raise RecoveryError("corrupt_sqlite: schema marker is not singular")
        version = int(rows[0][0])
        supported = set(allow_versions or range(1, CURRENT_SCHEMA_VERSION + 1))
        if version not in supported:
            raise RecoveryError(f"unsupported_sqlite_schema: {version}")
        _validate_sqlite_semantics(connection, version)
        return version
    except RecoveryError:
        raise
    except (sqlite3.DatabaseError, OSError, ValueError) as error:
        raise RecoveryError("corrupt_sqlite") from error
    finally:
        try:
            connection.close()
        except UnboundLocalError:
            pass


def _validate_sqlite_semantics(connection: sqlite3.Connection, version: int) -> None:
    required = {"projects", "stages", "progress_entries", "notes", "settings", "game_state", "mirror_state"}
    available = {
        row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    if not required.issubset(available):
        raise RecoveryError("corrupt_sqlite: required table is missing")
    if version >= 4:
        required_v4 = {
            "project_metadata", "project_folders", "project_folder_members",
            "stage_order", "project_bindings", "project_extensions",
            "progress_order", "migration_sources",
        }
        if not required_v4.issubset(available):
            raise RecoveryError("corrupt_sqlite: required v4 table is missing")
    if version >= 5 and "game_metadata" not in available:
        raise RecoveryError("corrupt_sqlite: required game metadata table is missing")
    if version >= 6:
        required_v6 = {"documents", "document_bindings", "document_metadata", "document_migration_orphans"}
        if not required_v6.issubset(available):
            raise RecoveryError("corrupt_sqlite: required v6 table is missing")
    for table in ("projects", "stages", "progress_entries", "notes", "settings", "game_state"):
        column = "value_json" if table == "settings" else "payload_json"
        for row in connection.execute(f"SELECT {column} FROM {table}"):
            _json_loads(row[0], label=f"{table} payload")
    if version >= 3 and "project_order" in available:
        positions = [row[0] for row in connection.execute(
            "SELECT position FROM project_order ORDER BY position"
        )]
        if positions != list(range(len(positions))):
            raise RecoveryError("corrupt_sqlite: project order is not contiguous")
    if version >= 5 and "storage_ownership" in available:
        owners = [row[0] for row in connection.execute(
            "SELECT subsystem FROM storage_ownership"
        )]
        if len(set(owners)) != len(owners):
            raise RecoveryError("corrupt_sqlite: duplicate ownership rows")
        if set(owners) != {"projects", "settings", "notes", "game"}:
            raise RecoveryError("corrupt_sqlite: incomplete ownership markers")


def validate_backup(backup_dir: str | Path) -> dict[str, Any]:
    """Validate every sealed file before it can be used for restore."""
    backup = Path(backup_dir).expanduser().resolve()
    if not backup.is_dir() or backup.is_symlink():
        raise RecoveryError("backup_not_found")
    manifest = _read_backup_manifest(backup)
    entries = manifest.get("files", [])
    if manifest.get("legacy_unsealed"):
        entries = [
            {"path": path.name, "size": path.stat().st_size, "sha256": None}
            for path in sorted(backup.iterdir())
            if path.is_file() and path.name in KNOWN_PROFILE_FILES
        ]
    if not isinstance(entries, list) or len(entries) > BACKUP_FILE_LIMIT:
        raise RecoveryError("backup file manifest is invalid")
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise RecoveryError("backup file manifest entry is invalid")
        name = _safe_relative_path(entry.get("path"))
        if name in seen:
            raise RecoveryError(f"duplicate backup file: {name}")
        seen.add(name)
        path = backup / name
        if not path.is_file() or path.is_symlink():
            raise RecoveryError(f"backup file is missing: {name}")
        if path.stat().st_size != entry.get("size"):
            raise RecoveryError(f"backup file size mismatch: {name}")
        expected = entry.get("sha256")
        if expected is not None and sha256_file(path) != expected:
            raise RecoveryError(f"backup checksum mismatch: {name}")
    database = backup / "nfprogress.db"
    if database.is_file():
        version = validate_sqlite_file(database)
        declared = manifest.get("schema_version")
        if declared is not None and int(declared) != version:
            raise RecoveryError("backup schema version mismatch")
    return manifest


def restore_application_backup(
    backup_dir: str | Path,
    target_root: str | Path,
) -> Path:
    """Validate, stage, verify, and atomically activate a profile restore."""
    backup = Path(backup_dir).expanduser().resolve()
    target = Path(target_root).expanduser().resolve()
    if backup == target or backup in target.parents:
        raise RecoveryError("restore target must be outside backup")
    manifest = validate_backup(backup)
    entries = manifest.get("files", [])
    if manifest.get("legacy_unsealed"):
        entries = [
            {"path": path.name}
            for path in sorted(backup.iterdir())
            if path.is_file() and path.name in KNOWN_PROFILE_FILES
        ]
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}-restore-", dir=target.parent))
    try:
        for entry in entries:
            name = _safe_relative_path(entry["path"])
            _atomic_copy(backup / name, staging / name)
        database = staging / "nfprogress.db"
        if database.is_file():
            # The upgrade happens only in the invisible staging profile.
            from nfprogress.core.sqlite.connection import open_database

            with open_database(staging):
                pass
            validate_sqlite_file(database)
        rollback = target.parent / f".{target.name}-restore-rollback-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')}"
        if target.exists():
            target.replace(rollback)
        try:
            staging.replace(target)
        except Exception:
            if target.exists():
                failed = target.parent / f".{target.name}-restore-failed"
                shutil.rmtree(failed, ignore_errors=True)
                target.replace(failed)
            if rollback.exists():
                rollback.replace(target)
            raise
        _fsync_directory(target.parent)
        return rollback if rollback.exists() else target
    except Exception:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        raise


def _walk_json(value: Any, *, depth: int = 0) -> int:
    if depth > MIGRATION_MAX_DEPTH:
        raise RecoveryError("migration bundle JSON is too deeply nested")
    if isinstance(value, str):
        if len(value) > MIGRATION_MAX_STRING:
            raise RecoveryError("migration bundle string is too long")
        return 1
    if isinstance(value, Mapping):
        return 1 + sum(_walk_json(key, depth=depth + 1) + _walk_json(item, depth=depth + 1) for key, item in value.items())
    if isinstance(value, list):
        return 1 + sum(_walk_json(item, depth=depth + 1) for item in value)
    return 1


def validate_migration_bundle(bundle: Any) -> None:
    """Validate the complete v1 DTO before any SQLite mutation."""
    from nfprogress.core.migration import MigrationBundle

    if not isinstance(bundle, MigrationBundle):
        raise RecoveryError("migration bundle has an invalid type")
    if bundle.dto_version != 1:
        raise RecoveryError("unsupported_newer_bundle_version")
    payload = bundle.to_dict()
    if len(json.dumps(payload, ensure_ascii=False).encode("utf-8")) > MIGRATION_JSON_LIMIT:
        raise RecoveryError("migration bundle is too large")
    if _walk_json(payload) > MIGRATION_MAX_ENTITIES:
        raise RecoveryError("migration bundle contains too many entities")
    project_ids = [item.get("id") for item in bundle.projects]
    _require_ids(project_ids, "project")
    if len(bundle.project_order) != len(project_ids) or set(bundle.project_order) != set(project_ids):
        raise RecoveryError("project_order must contain every project exactly once")
    stage_ids: list[str] = []
    progress_ids: list[str] = []
    for project in bundle.projects:
        _require_id(project.get("id"), "project")
        if not isinstance(project.get("payload"), Mapping):
            raise RecoveryError("project payload must be an object")
        for stage in project.get("stages", []):
            stage_ids.append(stage.get("id"))
            if stage.get("project_id", project["id"]) != project["id"]:
                raise RecoveryError("stage has the wrong project owner")
            if not isinstance(stage.get("payload"), Mapping):
                raise RecoveryError("stage payload must be an object")
            progress_ids.extend(_progress_ids(stage.get("payload", {}).get("progress_entries", [])))
        progress_ids.extend(_progress_ids(project.get("payload", {}).get("progress_entries", [])))
    _require_ids(stage_ids, "stage")
    _require_ids(progress_ids, "progress")
    _validate_folders(bundle.folders, project_ids)
    folder_ids = {folder["id"] for folder in bundle.folders}
    for project in bundle.projects:
        folder_id = project.get("payload", {}).get("folder_id")
        if folder_id is not None and folder_id not in folder_ids:
            raise RecoveryError("project has an unknown folder owner")
    _validate_bindings(bundle, set(project_ids), set(stage_ids))
    _validate_documents(bundle, set(project_ids), set(stage_ids))
    if bundle.settings is not None and not isinstance(bundle.settings, Mapping):
        raise RecoveryError("settings section must be an object")
    if bundle.notes is not None:
        if not isinstance(bundle.notes, list):
            raise RecoveryError("notes section must be a list")
        note_ids = [item.get("id") if isinstance(item, Mapping) else None for item in bundle.notes]
        _require_ids(note_ids, "note")
        for note in bundle.notes:
            if note.get("project_id") not in set(project_ids):
                raise RecoveryError("note has an unknown project owner")
            if note.get("stage_id") is not None and note.get("stage_id") not in set(stage_ids):
                raise RecoveryError("note has an unknown stage owner")
            if note.get("source_type") == "mindmap":
                if not isinstance(note.get("source_node_id"), str) or not note["source_node_id"]:
                    raise RecoveryError("mindmap note has no source node")
    if not isinstance(bundle.bundle_manifest, Mapping):
        raise RecoveryError("bundle_manifest must be an object")
    declared_checksum = bundle.bundle_manifest.get("bundle_checksum")
    if declared_checksum is not None:
        if not isinstance(declared_checksum, str) or len(declared_checksum) != 64:
            raise RecoveryError("bundle checksum is invalid")
        from nfprogress.core.migration import bundle_checksum
        if declared_checksum != bundle_checksum(bundle):
            raise RecoveryError("bundle checksum mismatch")
    if not isinstance(bundle.source_manifest, Mapping):
        raise RecoveryError("source_manifest must be an object")


def _require_id(value: Any, kind: str) -> None:
    if not isinstance(value, str) or not value or len(value) > 256:
        raise RecoveryError(f"{kind} has an invalid stable identifier")


def _require_ids(values: Iterable[Any], kind: str) -> None:
    materialized = list(values)
    for value in materialized:
        _require_id(value, kind)
    if len(set(materialized)) != len(materialized):
        raise RecoveryError(f"duplicate {kind} identifier")


def _progress_ids(entries: Any) -> list[str]:
    if not isinstance(entries, list):
        raise RecoveryError("progress_entries must be a list")
    return [entry.get("id") if isinstance(entry, Mapping) else None for entry in entries]


def _validate_folders(folders: Any, project_ids: list[str]) -> None:
    if not isinstance(folders, list):
        raise RecoveryError("folders must be a list")
    folder_ids = [folder.get("id") if isinstance(folder, Mapping) else None for folder in folders]
    _require_ids(folder_ids, "folder")
    for folder in folders:
        if not isinstance(folder.get("name"), str) or not folder["name"].strip():
            raise RecoveryError("folder has an invalid name")
    del project_ids  # membership is validated from project payloads.


def _validate_bindings(bundle: Any, project_ids: set[str], stage_ids: set[str]) -> None:
    bindings = []
    for project in bundle.projects:
        bindings.append(project.get("binding"))
        bindings.extend(stage.get("binding") for stage in project.get("stages", []))
    bindings.extend(bundle.document_bindings)
    bindings = [item for item in bindings if item]
    ids = [item.get("id") if isinstance(item, Mapping) else None for item in bindings]
    _require_ids(ids, "binding")
    for binding in bindings:
        if binding.get("project_id") not in project_ids:
            raise RecoveryError("binding has an unknown project owner")
        if binding.get("stage_id") is not None and binding.get("stage_id") not in stage_ids:
            raise RecoveryError("binding has an unknown stage owner")
        if not isinstance(binding.get("binding_type"), str) or not binding["binding_type"]:
            raise RecoveryError("binding has no type")


def _validate_documents(bundle: Any, project_ids: set[str], stage_ids: set[str]) -> None:
    if not isinstance(bundle.documents, list) or not isinstance(bundle.external_file_manifest, list):
        raise RecoveryError("document sections must be lists")
    ids = [item.get("document_id") if isinstance(item, Mapping) else None for item in bundle.documents]
    _require_ids(ids, "document")
    for document in bundle.documents:
        if document.get("project_id") not in project_ids:
            raise RecoveryError("document has an unknown project owner")
        if document.get("stage_id") is not None and document.get("stage_id") not in stage_ids:
            raise RecoveryError("document has an unknown stage owner")
        if not isinstance(document.get("content", {}), Mapping):
            raise RecoveryError("document content must be an object")
        if document.get("content", {}).get("type") != "doc":
            raise RecoveryError("document content is not Tiptap JSON")
