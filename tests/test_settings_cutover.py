import engine
import pytest

from nfprogress.core.sqlite import (
    SQLiteSettingsRepository,
    StorageOwner,
    StorageOwnershipRepository,
    Subsystem,
    cutover_settings,
)
from nfprogress.core.sqlite.connection import open_database
from nfprogress.core.storage import PickleRepository


def _legacy_settings(root, values):
    with engine.data_directory_context(root):
        engine.atomic_pickle_save(values, engine.get_data_file_path('settings'))


def test_startup_cutover_imports_complete_pickle_state_and_switches_owner(tmp_path):
    values = {
        'language': 'ru', 'enabled': True, 'count': 4, 'ratio': 1.25,
        'nothing': None, 'items': ['Ω', 2], 'nested': {'ключ': 'значение'},
    }
    _legacy_settings(tmp_path, values)
    with open_database(tmp_path) as db:
        db.execute("INSERT INTO settings(key, value_json) VALUES('language', 'null')")
        db.commit()

    cutover_settings(tmp_path, values)

    assert StorageOwnershipRepository(tmp_path).get_owner(Subsystem.SETTINGS) == StorageOwner.SQLITE
    assert SQLiteSettingsRepository(tmp_path).get_all() == values
    assert PickleRepository(tmp_path).read_settings() == values


def test_cutover_failure_keeps_pickle_owner_and_data(tmp_path, monkeypatch):
    values = {'language': 'ru', 'marker': 'legacy'}
    _legacy_settings(tmp_path, values)

    def fail(*_args, **_kwargs):
        raise OSError('disk full')

    monkeypatch.setattr(SQLiteSettingsRepository, '_write_in_transaction', fail)
    with pytest.raises(OSError, match='disk full'):
        cutover_settings(tmp_path, values)

    assert StorageOwnershipRepository(tmp_path).get_owner(Subsystem.SETTINGS) == StorageOwner.PICKLE
    assert PickleRepository(tmp_path).read_settings() == values


def test_successful_cutover_is_idempotent_and_pkl_is_ignored(tmp_path):
    old_values = {'language': 'ru', 'marker': 'legacy'}
    _legacy_settings(tmp_path, old_values)
    cutover_settings(tmp_path, old_values)
    SQLiteSettingsRepository(tmp_path).set_all({'language': 'fr', 'marker': 'sqlite'})
    _legacy_settings(tmp_path, old_values)

    cutover_settings(tmp_path, old_values)

    assert PickleRepository(tmp_path).read_settings() == {'language': 'fr', 'marker': 'sqlite'}


def test_engine_runtime_ignores_legacy_pickle_after_cutover(tmp_path):
    _legacy_settings(tmp_path, {'language': 'ru'})
    cutover_settings(tmp_path, {'language': 'ru'})
    _legacy_settings(tmp_path, {'language': 'de'})

    with engine.data_directory_context(tmp_path):
        assert engine.load_settings() == {'language': 'ru'}


def test_pickle_mirror_rebuild_does_not_overwrite_sqlite_settings(tmp_path):
    repository = PickleRepository(tmp_path)
    values = {'language': 'ru'}
    repository.write_settings(values)
    cutover_settings(tmp_path, values)
    SQLiteSettingsRepository(tmp_path).set('language', 'fr')

    repository.write_projects({'projects': {}, 'last': None})

    assert SQLiteSettingsRepository(tmp_path).get_all()['language'] == 'fr'
