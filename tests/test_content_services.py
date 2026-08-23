import pytest

import engine
from nfprogress.core.errors import ValidationError
from nfprogress.core.repositories.storage import PickleRepository
from nfprogress.core.services.content import ContentService
from nfprogress.core.services.settings import SettingsService


def test_help_uses_canonical_tree_and_explicit_language():
    service = ContentService()
    russian = service.help('ru')
    english = service.help('en')

    assert russian[0]['key'] == english[0]['key'] == 'quick_start'
    assert russian[0]['title'] == 'Быстрый старт'
    assert english[0]['title'] == 'Quick start'
    assert '<html>' in english[0]['content'].lower()


def test_locale_api_uses_the_shared_catalog_terminology():
    service = ContentService()

    assert service.locale('ru')['Исследователь'] == 'Исследователь'
    assert service.locale('en')['Исследователь'] == 'Explorer'
    assert service.locale('de')['Редактор'] == 'Lektor'


def test_agreement_uses_russian_source_and_shared_english_version():
    service = ContentService()

    russian = service.agreement('ru')
    english = service.agreement('en')
    french = service.agreement('fr')

    assert russian['id'] == english['id'] == french['id']
    assert 'ДОПОЛНИТЕЛЬНЫЕ УСЛОВИЯ' in russian['html']
    assert 'ADDITIONAL TERMS OF USE' in english['html']
    assert french['html'] == english['html']


def test_settings_are_platform_aware_and_persisted(tmp_path):
    repository = PickleRepository(tmp_path)
    web = SettingsService(repository, platform='web')

    updated = web.update({
        'language': 'fr',
        'frontend_theme': 'dark',
        'frontend_motion': 'reduced',
        'frontend_project_filter': 'all',
        'frontend_project_sort': 'updated',
    })

    assert updated['values']['language'] == 'fr'
    assert updated['values']['frontend_theme'] == 'dark'
    assert updated['values']['frontend_motion'] == 'reduced'
    assert updated['values']['frontend_project_filter'] == 'all'
    assert updated['values']['frontend_project_sort'] == 'updated'
    assert updated['capabilities']['local_file_sync'] is False
    assert 'background_synch' not in updated['editable_keys']

    fresh = SettingsService(PickleRepository(tmp_path / 'fresh'), platform='web')
    assert fresh.get()['values']['frontend_motion'] == 'full'


def test_notification_duration_preserves_the_legacy_range(tmp_path):
    service = SettingsService(PickleRepository(tmp_path), platform='web')

    updated = service.update({'notification_display_time': 3600})

    assert updated['values']['notification_display_time'] == 3600
    with pytest.raises(ValidationError, match='от 1 до 3600'):
        service.update({'notification_display_time': 3601})


def test_agreement_acceptance_keeps_the_legacy_boolean(tmp_path):
    from nfprogress.core.agreement import AGREEMENT_ID

    repository = PickleRepository(tmp_path)
    service = SettingsService(repository, platform='web')

    response = service.accept_user_agreement(AGREEMENT_ID)

    assert response['values']['user_agreement'] is True
    assert repository.read_settings()['user_agreement'] is True

    with pytest.raises(ValidationError):
        service.accept_user_agreement('stale-agreement')

@pytest.mark.parametrize('patch', [
    {'game_mode': 'false'},
    {'notification_display_time': True},
    {'start_day_time': 'not-a-time'},
    {'project_sort': 'unknown'},
    {'frontend_project_filter': 'unknown'},
    {'frontend_motion': 'unknown'},
])
def test_settings_reject_values_that_change_legacy_truthiness(patch, tmp_path):
    service = SettingsService(PickleRepository(tmp_path), platform='web')

    with pytest.raises(ValidationError):
        service.update(patch)


def test_project_settings_apply_legacy_side_effects_with_backup(tmp_path):
    repository = PickleRepository(tmp_path)
    service = SettingsService(repository, platform='web')

    enabled = service.update({'inf_project': True, 'global_streak': True})
    assert enabled['values']['inf_project'] is True
    projects = repository.read_projects()
    infinite = projects['projects']['Общий проект']
    infinite.streaks = [engine.today_for_test()]
    projects['global_streaks'] = [engine.today_for_test()]
    projects['last_global_streak_bonus'] = engine.today_for_test()
    repository.write_projects(projects)

    disabled = service.update({'inf_project': False, 'global_streak': False})

    assert disabled['values']['inf_project'] is False
    saved = repository.read_projects()
    assert 'Общий проект' not in saved['projects']
    assert saved['global_streaks'] == []
    assert saved['last_global_streak_bonus'] is None
    assert any((tmp_path / 'backups').iterdir())
