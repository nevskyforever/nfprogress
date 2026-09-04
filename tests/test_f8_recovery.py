from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from nfprogress.core.migration import MigrationBundle, import_projects_bundle
from nfprogress.core.recovery import (
    RecoveryError,
    create_application_backup,
    restore_application_backup,
    sha256_file,
    source_fingerprint,
    validate_backup,
    validate_migration_bundle,
    validate_sqlite_file,
)
from nfprogress.core.sqlite.connection import open_database
from nfprogress.core.sqlite.schema import CURRENT_SCHEMA_VERSION, MIGRATIONS_DIR


def _seed_database(root: Path, *, marker: str = "source") -> None:
    with open_database(root) as db:
        db.execute(
            "INSERT INTO projects(id,name,goal,infinite,unit,status,payload_json) "
            "VALUES(?,?,?,?,?,?,?)",
            ("project-1", marker, 100, 0, "symbols", "активен", json.dumps({"name": marker})),
        )
        db.execute(
            "INSERT INTO project_order(project_id,position) VALUES('project-1',0)"
        )
        db.execute(
            "INSERT INTO documents(id,scope_key,project_id,title,content_json,content_format,extensions_json) "
            "VALUES('document-1','project-1:project','project-1','Текст',?,'tiptap-json/v1','{}')",
            (json.dumps({"type": "doc", "content": [{"type": "paragraph"}]}),),
        )
        db.execute(
            "INSERT INTO document_bindings(id,document_id,binding_type,external_path,sync_state,payload_json) "
            "VALUES('binding-1','document-1','word',?,'synced','{}')",
            (str(root / "missing.docx"),),
        )
        db.commit()


def test_application_backup_is_sealed_and_keeps_external_files_as_references(tmp_path):
    _seed_database(tmp_path)
    (tmp_path / "data.pkl").write_bytes(b"legacy recovery source")
    backup = create_application_backup(tmp_path)

    manifest = validate_backup(backup)
    assert manifest["manifest_version"] == 1
    assert manifest["schema_version"] == CURRENT_SCHEMA_VERSION
    assert manifest["external_files_are_references"] is True
    assert {item["path"] for item in manifest["files"]} == {
        "data.pkl", "external_file_manifest.json", "nfprogress.db",
    }
    for item in manifest["files"]:
        assert item["sha256"] == sha256_file(backup / item["path"])
    external = json.loads((backup / "external_file_manifest.json").read_text())
    assert external[0]["exists"] is False
    assert (tmp_path / "data.pkl").read_bytes() == b"legacy recovery source"
    assert not list((tmp_path / "backups").glob(".*"))


def test_backup_source_fingerprint_changes_when_source_changes(tmp_path):
    (tmp_path / "data.pkl").write_bytes(b"one")
    first = source_fingerprint(tmp_path)
    (tmp_path / "data.pkl").write_bytes(b"two")
    assert source_fingerprint(tmp_path) != first


def test_restore_validates_before_activation_and_keeps_previous_profile(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "profile"
    _seed_database(source, marker="restored")
    backup = create_application_backup(source)
    _seed_database(target, marker="current")

    rollback = restore_application_backup(backup, target)

    with open_database(target) as db:
        assert db.execute("SELECT name FROM projects WHERE id='project-1'").fetchone()[0] == "restored"
        assert db.execute("SELECT schema_version FROM schema_info").fetchone()[0] == CURRENT_SCHEMA_VERSION
    assert rollback.is_dir()
    with open_database(rollback) as db:
        assert db.execute("SELECT name FROM projects WHERE id='project-1'").fetchone()[0] == "current"


def test_corrupt_backup_is_rejected_without_overwriting_current_profile(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "profile"
    _seed_database(source, marker="restored")
    backup = create_application_backup(source)
    _seed_database(target, marker="current")
    corrupt = tmp_path / "corrupt-backup"
    shutil.copytree(backup, corrupt)
    with (corrupt / "nfprogress.db").open("ab") as stream:
        stream.write(b"truncated-corruption")

    with pytest.raises(RecoveryError, match="(size|checksum) mismatch"):
        restore_application_backup(corrupt, target)
    with open_database(target) as db:
        assert db.execute("SELECT name FROM projects WHERE id='project-1'").fetchone()[0] == "current"


def test_sqlite_validation_rejects_missing_tables_and_invalid_header(tmp_path):
    invalid = tmp_path / "invalid.db"
    invalid.write_bytes(b"not sqlite")
    with pytest.raises(RecoveryError, match="corrupt_sqlite"):
        validate_sqlite_file(invalid)

    missing_table = tmp_path / "missing-table.db"
    connection = sqlite3.connect(missing_table)
    connection.execute("CREATE TABLE schema_info(schema_version INTEGER NOT NULL)")
    connection.execute("INSERT INTO schema_info VALUES(6)")
    connection.commit()
    connection.close()
    with pytest.raises(RecoveryError, match="required table"):
        validate_sqlite_file(missing_table)


@pytest.mark.parametrize("version", range(1, CURRENT_SCHEMA_VERSION + 1))
def test_each_supported_sqlite_schema_upgrades_to_latest(tmp_path, version):
    database = tmp_path / f"v{version}.db"
    connection = sqlite3.connect(database)
    migration_files = {
        1: "001_initial.sql",
        2: "002_storage_ownership.sql",
        3: "003_project_order.sql",
        4: "004_projects_authority.sql",
        5: "005_game_authority.sql",
        6: "006_documents_authority.sql",
    }
    for migration_version in range(1, version + 1):
        connection.executescript(
            (MIGRATIONS_DIR / migration_files[migration_version]).read_text()
        )
    connection.execute("CREATE TABLE schema_info(schema_version INTEGER NOT NULL)")
    connection.execute("INSERT INTO schema_info VALUES(?)", (version,))
    connection.commit()
    connection.close()
    root = tmp_path / f"root-{version}"
    root.mkdir()
    database.replace(root / "nfprogress.db")
    assert validate_sqlite_file(root / "nfprogress.db") == version
    with open_database(root) as db:
        assert db.execute("SELECT schema_version FROM schema_info").fetchone()[0] == CURRENT_SCHEMA_VERSION


def _minimal_bundle(**overrides):
    values = {
        "projects": [{
            "id": "project-1",
            "payload": {"id": "project-1", "name": "Проект", "progress_entries": [], "folder_id": None},
            "stages": [],
            "extra_fields": {},
            "progress_extra_fields": {},
            "binding": None,
        }],
        "project_order": ["project-1"],
        "folders": [],
        "project_metadata": {},
        "root_extensions": {},
        "source_manifest": {},
    }
    values.update(overrides)
    return MigrationBundle(**values)


def test_bundle_validation_rejects_duplicate_ids_and_broken_relationships():
    duplicate = _minimal_bundle(projects=[
        {"id": "project-1", "payload": {}, "stages": [], "extra_fields": {}, "progress_extra_fields": {}, "binding": None},
        {"id": "project-1", "payload": {}, "stages": [], "extra_fields": {}, "progress_extra_fields": {}, "binding": None},
    ], project_order=["project-1", "project-1"])
    with pytest.raises(RecoveryError, match="duplicate project"):
        validate_migration_bundle(duplicate)

    broken = _minimal_bundle(projects=[{
        "id": "project-1",
        "payload": {"id": "project-1", "progress_entries": []},
        "stages": [{"id": "stage-1", "project_id": "other", "payload": {"id": "stage-1", "progress_entries": []}}],
        "extra_fields": {},
        "progress_extra_fields": {},
        "binding": None,
    }])
    with pytest.raises(RecoveryError, match="wrong project owner"):
        validate_migration_bundle(broken)


def test_bundle_json_rejects_unknown_and_future_versions():
    value = _minimal_bundle().to_dict()
    value["future_field"] = True
    with pytest.raises(ValueError, match="unknown migration DTO fields"):
        MigrationBundle.from_json(json.dumps(value))

    value = _minimal_bundle().to_dict()
    value["dto_version"] = 2
    with pytest.raises(ValueError, match="unsupported migration DTO version"):
        MigrationBundle.from_json(json.dumps(value))


def test_backup_rejects_path_traversal_before_restore(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "profile"
    _seed_database(source)
    backup = create_application_backup(source)
    _seed_database(target, marker="current")
    manifest_path = backup / "backup_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"][0]["path"] = "../outside"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(RecoveryError, match="unsafe backup path"):
        restore_application_backup(backup, target)
    with open_database(target) as db:
        assert db.execute("SELECT name FROM projects WHERE id='project-1'").fetchone()[0] == "current"


def test_bundle_import_rejects_before_mutating_existing_database(tmp_path):
    _seed_database(tmp_path, marker="current")
    invalid = _minimal_bundle(project_order=[])
    with pytest.raises(Exception, match="project_order"):
        import_projects_bundle(invalid, tmp_path)
    with open_database(tmp_path) as db:
        assert db.execute("SELECT name FROM projects WHERE id='project-1'").fetchone()[0] == "current"


def test_bounded_large_unicode_and_date_fixture_validates_and_imports(tmp_path):
    projects = []
    order = []
    for index in range(250):
        project_id = f"project-{index:03d}"
        order.append(project_id)
        projects.append({
            "id": project_id,
            "payload": {
                "id": project_id,
                "name": f"Проект Ω {index} 📚",
                "goal": 100_000,
                "unit": "symbols",
                "status": "активен",
                "created_at": "2025-12-31T23:59:59+04:00",
                "progress_entries": [{
                    "id": f"progress-{index:03d}",
                    "created_at": "2026-01-01T00:00:00+04:00",
                    "added_symbols": 100 + index,
                    "added_progress": 100 + index,
                    "text": "Кириллица / 日本語 / العربية / emoji 🚀",
                }],
                "folder_id": None,
            },
            "stages": [],
            "extra_fields": {"future": {"index": index}},
            "progress_extra_fields": {},
            "binding": None,
        })
    bundle = _minimal_bundle(projects=projects, project_order=order)

    validate_migration_bundle(bundle)
    import_projects_bundle(bundle, tmp_path)

    with open_database(tmp_path) as db:
        assert db.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 250
        assert db.execute("SELECT COUNT(*) FROM progress_entries").fetchone()[0] == 250
        assert "🚀" in db.execute(
            "SELECT payload_json FROM progress_entries WHERE id='progress-249'"
        ).fetchone()[0]
