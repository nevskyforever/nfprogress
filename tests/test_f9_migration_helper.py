from __future__ import annotations

import json
import os
import pickle
import shutil
import sqlite3
from pathlib import Path

import engine
import game
import pytest
import nfprogress.migration_helper as migration_helper

from nfprogress.core.legacy_decoder import (
    FORBIDDEN_OPCODES,
    LegacyDecodeError,
    UnsupportedLegacyObject,
    load_legacy_pickle,
)
from nfprogress.core.sqlite.connection import open_database
from nfprogress.core import recovery
from nfprogress.migration_helper import (
    HelperError,
    OUTCOME_DESTINATION_INVALID,
    OUTCOME_MIGRATION_VERIFIED,
    OUTCOME_UNSUPPORTED_SOURCE,
    build_bundle,
    inspect_source,
    prepare,
    verify_prepared_profile,
)


def _write_pickle(root: Path, name: str, value: object) -> None:
    (root / name).write_bytes(pickle.dumps(value, protocol=4))


def _fixture(root: Path, *, documents: bool = True, game_file: bool = True) -> tuple[engine.Project, dict]:
    project = engine.Project("Проект Юникод 🚀", 10_000)
    project.folder_id = "folder-1"
    project.custom_extension = {"future": ["значение", 7]}
    project.mindmap_data = {
        "nodeData": {"id": "map-root", "topic": "Корень", "children": []},
    }
    project.project_notes = [{
        "id": "note-1", "title": "Идея", "content": "Текст #карта",
        "tags": ["#карта", "важное"], "source_type": "project",
        "updated_at": "2026-01-01T00:00:00+00:00", "unknown_note": True,
    }]
    project.synch = {"type": "word", "path": str(root / "missing.docx"), "source_id": "w-1"}
    project.notes.append(engine.Note(100, 100, 100, entry_id="progress-1"))
    stage = engine.Stage("Глава", 5_000, stage_id="stage-1", parent_project_name=project.name)
    stage.project_notes = [{"id": "note-2", "title": "Глава", "content": "Сцена"}]
    stage.notes.append(engine.Note(50, 50, 50, entry_id="stage-progress-1"))
    project.stages = [stage]
    project.enable_stages = True
    state = {
        "projects": {project.name: project}, "project_order": [project.project_id],
        "project_folders": [{"id": "folder-1", "name": "Черновики", "future": {"color": "blue"}}],
        "last": project.name, "future_root": {"keep": True},
    }
    _write_pickle(root, "data.pkl", state)
    _write_pickle(root, "settings.pkl", {"game_mode": True, "unknown_setting": {"x": 1}})
    if game_file:
        gamer = game.Gamer(level=4, exp=321, coins=99)
        gamer.future_game_field = {"preserve": "да"}
        _write_pickle(root, "gamer.pkl", gamer)
    if documents:
        (root / "documents.json").write_text(json.dumps({
            "project:project": {
                "project_id": project.project_id, "title": "Документ 🚀",
                "content": {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Привет"}]}]},
                "docx_path": str(root / "missing.docx"), "local_dirty": True,
                "unknown_document": {"keep": True},
            },
            "chapter": {
                "project_id": project.project_id, "stage_id": "stage-1",
                "content": {"type": "doc", "content": [{"type": "paragraph"}]},
            },
        }, ensure_ascii=False), encoding="utf-8")
    return project, state


def test_detection_is_read_only_and_distinguishes_fresh_and_pkl_profiles(tmp_path):
    fresh = inspect_source(tmp_path)
    assert fresh.source_profile == "fresh_install"
    assert fresh.supported
    _write_pickle(tmp_path, "data.pkl", {"projects": {}})
    detected = inspect_source(tmp_path)
    assert detected.source_profile == "A_pkl_only"
    assert not (tmp_path / "nfprogress.db").exists()


@pytest.mark.parametrize(("game_file", "documents", "profile"), [
    (False, False, "A_pkl_only"), (True, False, "B_pkl_game"),
    (False, True, "C_pkl_documents"), (True, True, "D_pkl_game_documents"),
])
def test_pkl_source_profiles_are_explicit(tmp_path, game_file, documents, profile):
    _fixture(tmp_path, game_file=game_file, documents=documents)
    assert inspect_source(tmp_path).source_profile == profile


@pytest.mark.parametrize(("version", "profile", "owners", "supported"), [
    (3, "E_sqlite_v3_pkl_authority", {"projects": "pickle"}, True),
    (4, "F_sqlite_v4_mixed", {"projects": "sqlite", "settings": "pickle"}, True),
    (5, "G_sqlite_v5_game_incomplete", {"game": "pickle"}, True),
    (6, "H_sqlite_v6_ownership_incomplete", {"projects": "sqlite", "settings": "sqlite", "notes": "sqlite", "game": "sqlite"}, False),
])
def test_sqlite_transition_profiles_are_detected_and_ambiguous_v6_is_rejected(
    tmp_path, version, profile, owners, supported
):
    _fixture(tmp_path)
    with open_database(tmp_path) as db:
        db.execute("UPDATE schema_info SET schema_version=?", (version,))
        for subsystem, owner in owners.items():
            db.execute("UPDATE storage_ownership SET owner=? WHERE subsystem=?", (owner, subsystem))
        db.commit()
    inspection = inspect_source(tmp_path)
    assert inspection.source_profile == profile
    assert inspection.supported is supported


def test_complete_fixture_migrates_bundle_domains_and_keeps_legacy_sources(tmp_path):
    project, _state = _fixture(tmp_path)
    before = {name: (tmp_path / name).read_bytes() for name in ("data.pkl", "settings.pkl", "gamer.pkl", "documents.json")}
    report = prepare(tmp_path)
    assert report.outcome == OUTCOME_MIGRATION_VERIFIED
    assert report.preview.to_dict() == {
        "projects": 1, "stages": 1, "progress_entries": 2, "notes": 2,
        "game": True, "maps": 1, "documents": 2, "external_bindings": 2,
        "warnings": [f"missing external file: {tmp_path / 'missing.docx'}"],
    }
    assert verify_prepared_profile(tmp_path) == (True, [])
    with sqlite3.connect(tmp_path / "nfprogress.db") as db:
        assert db.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM stages").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM progress_entries").fetchone()[0] == 2
        assert db.execute("SELECT COUNT(*) FROM notes").fetchone()[0] == 2
        assert db.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 2
        assert db.execute("SELECT COUNT(*) FROM document_bindings").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM project_bindings").fetchone()[0] == 1
        assert db.execute("SELECT owner FROM storage_ownership WHERE subsystem='game'").fetchone()[0] == "sqlite"
        assert json.loads(db.execute("SELECT payload_json FROM project_extensions WHERE entity_id=?", (project.project_id,)).fetchone()[0])["custom_extension"]["future"][0] == "значение"
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        assert db.execute("SELECT sync_state FROM document_bindings ORDER BY id LIMIT 1").fetchone()[0] == "missing_external"
    assert (tmp_path / "backups").is_dir()
    assert (tmp_path / "nfprogress-migration.json").is_file()
    assert {name: (tmp_path / name).read_bytes() for name in before} == before
    assert not (tmp_path / "missing.docx").exists()


def test_large_legacy_fixture_migrates_through_helper(tmp_path):
    projects = {}
    for index in range(250):
        project = engine.Project(f"Большой проект Ω {index} 🚀", 100_000)
        project.project_id = f"large-project-{index:03d}"
        project.notes.append(engine.Note(100 + index, 100 + index, 100 + index, entry_id=f"large-progress-{index:03d}"))
        project.future_extension = {"index": index}
        projects[project.name] = project
    _write_pickle(tmp_path, "data.pkl", {"projects": projects, "project_order": [project.project_id for project in projects.values()]})

    report = prepare(tmp_path)

    assert report.preview.projects == 250
    assert report.preview.progress_entries == 250
    with sqlite3.connect(tmp_path / "nfprogress.db") as db:
        assert db.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 250
        assert db.execute("SELECT COUNT(*) FROM progress_entries").fetchone()[0] == 250
        assert "🚀" in db.execute(
            "SELECT payload_json FROM projects WHERE id='large-project-249'"
        ).fetchone()[0]


def test_prepare_windows_path_skips_unsupported_directory_fsync_and_keeps_recovery(tmp_path, monkeypatch):
    """Windows prepare must not fsync a directory descriptor (Errno 9)."""
    _fixture(tmp_path)
    monkeypatch.setattr(recovery, "_directory_fsync_supported", lambda: False)
    report = prepare(tmp_path)

    assert report.outcome == OUTCOME_MIGRATION_VERIFIED
    assert verify_prepared_profile(tmp_path) == (True, [])
    assert (tmp_path / "nfprogress.db").is_file()
    assert (tmp_path / "backups").is_dir()
    assert (tmp_path / "data.pkl").is_file()

    def unexpected_directory_open(*_args, **_kwargs):
        raise AssertionError("Windows prepare must not open a directory for fsync")

    monkeypatch.setattr(recovery.os, "open", unexpected_directory_open)
    recovery._fsync_directory(tmp_path)


def test_directory_fsync_support_is_posix_only(monkeypatch):
    monkeypatch.setattr(recovery.os, "name", "nt")
    assert recovery._directory_fsync_supported() is False


def test_fsync_file_uses_writable_descriptor_for_windows(monkeypatch, tmp_path):
    path = tmp_path / "generated-manifest.json"
    path.write_text("{}\n", encoding="utf-8")
    modes = []
    original_open = Path.open

    def tracking_open(self, mode="r", *args, **kwargs):
        modes.append(mode)
        return original_open(self, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", tracking_open)
    recovery._fsync_file(path)
    assert modes == ["r+b"]


def test_prepare_closes_all_staging_sqlite_connections_before_activation(tmp_path, monkeypatch):
    """The Windows replace must never race a still-open staging DB handle."""
    _fixture(tmp_path)
    real_connect = sqlite3.connect
    connections = []

    class TrackingConnection(sqlite3.Connection):
        def __init__(self, *args, **kwargs):
            self.database_target = str(args[0]) if args else ""
            self.closed_by_code = False
            super().__init__(*args, **kwargs)
            connections.append(self)

        def close(self):
            self.closed_by_code = True
            return super().close()

    def tracking_connect(*args, **kwargs):
        kwargs["factory"] = TrackingConnection
        return real_connect(*args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", tracking_connect)
    original_activate = migration_helper._activate
    observed = {}

    def activation_with_handle_assertion(staging, destination):
        staging_db = str((Path(staging) / "nfprogress.db").resolve()).replace("\\", "/")
        leaked = [
            connection.database_target
            for connection in connections
            if staging_db in connection.database_target.replace("\\", "/")
            and not connection.closed_by_code
        ]
        observed["leaked"] = leaked
        assert not leaked, f"staging SQLite handles remain open: {leaked!r}"
        return original_activate(staging, destination)

    monkeypatch.setattr(migration_helper, "_activate", activation_with_handle_assertion)
    report = prepare(tmp_path)

    assert report.outcome == OUTCOME_MIGRATION_VERIFIED
    assert observed["leaked"] == []
    assert not (tmp_path / "nfprogress.db-wal").exists()
    assert not (tmp_path / "nfprogress.db-shm").exists()


def test_deterministic_ids_and_fingerprint_for_same_source(tmp_path):
    _fixture(tmp_path)
    copy = tmp_path.parent / "same-source-copy"
    shutil.copytree(tmp_path, copy)
    first = inspect_source(tmp_path)
    second = inspect_source(copy)
    assert first.fingerprint == second.fingerprint
    b1, _ = build_bundle(first, tmp_path)
    b2, _ = build_bundle(second, copy)
    ids = lambda bundle: ([p["id"] for p in bundle.projects], [s["id"] for p in bundle.projects for s in p["stages"]], [n["id"] for n in bundle.notes or []])
    assert ids(b1) == ids(b2)


def test_dry_run_has_no_mutations(tmp_path):
    _fixture(tmp_path)
    before = sorted(path.name for path in tmp_path.iterdir())
    report = prepare(tmp_path, dry_run=True)
    assert report.outcome == OUTCOME_MIGRATION_VERIFIED
    assert sorted(path.name for path in tmp_path.iterdir()) == before
    assert not (tmp_path / "nfprogress.db").exists()


def test_retry_is_idempotent_and_stale_pkl_is_ignored(tmp_path):
    _fixture(tmp_path)
    prepare(tmp_path)
    with sqlite3.connect(tmp_path / "nfprogress.db") as db:
        count = db.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    (tmp_path / "data.pkl").write_bytes(b"stale and unreadable")
    (tmp_path / "documents.json").write_text("stale and unreadable", encoding="utf-8")
    assert prepare(tmp_path).details == ["already prepared; SQLite remains authoritative"]
    with sqlite3.connect(tmp_path / "nfprogress.db") as db:
        assert db.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == count
    assert verify_prepared_profile(tmp_path) == (True, [])


def test_unknown_class_truncated_and_unexpected_global_are_rejected(tmp_path):
    unknown = tmp_path / "unknown.pkl"
    unknown.write_bytes(pickle.dumps(os.system, protocol=4))
    with pytest.raises(UnsupportedLegacyObject, match="unsupported_legacy_object"):
        load_legacy_pickle(unknown)
    unknown.write_bytes(pickle.dumps({"x": 1}, protocol=4)[:-2])
    with pytest.raises(LegacyDecodeError):
        load_legacy_pickle(unknown)
    assert "NEWOBJ_EX" in FORBIDDEN_OPCODES
    unknown.write_bytes(b"\x80\x04\x92.")
    with pytest.raises(LegacyDecodeError, match="unsupported pickle opcode"):
        load_legacy_pickle(unknown)


def test_corrupt_documents_and_partial_sqlite_are_explicit_failures(tmp_path):
    _fixture(tmp_path)
    (tmp_path / "documents.json").write_text("{broken", encoding="utf-8")
    with pytest.raises(HelperError, match="documents.json is invalid"):
        prepare(tmp_path, dry_run=True)
    _fixture(tmp_path)
    # A present DB with an incomplete marker/table is ambiguous, even with a
    # readable PKL fallback.
    (tmp_path / "nfprogress.db").write_bytes(b"not sqlite")
    inspection = inspect_source(tmp_path)
    assert inspection.source_profile == "J_corrupt_or_ambiguous"
    assert not inspection.supported
    with pytest.raises(HelperError) as error:
        prepare(tmp_path, dry_run=True)
    assert error.value.code == OUTCOME_UNSUPPORTED_SOURCE


def test_non_empty_destination_requires_explicit_replace(tmp_path):
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.mkdir(); destination.mkdir()
    _fixture(source)
    (destination / "nfprogress.db").write_bytes(b"existing")
    with pytest.raises(HelperError) as error:
        prepare(source, destination)
    assert error.value.code == OUTCOME_DESTINATION_INVALID
