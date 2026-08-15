import pytest

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


def test_settings_are_platform_aware_and_persisted(tmp_path):
    repository = PickleRepository(tmp_path)
    web = SettingsService(repository, platform='web')

    updated = web.update({'language': 'fr', 'frontend_theme': 'dark'})

    assert updated['values']['language'] == 'fr'
    assert updated['values']['frontend_theme'] == 'dark'
    assert updated['capabilities']['local_file_sync'] is False
    assert 'background_synch' not in updated['editable_keys']


@pytest.mark.parametrize('patch', [
    {'game_mode': 'false'},
    {'notification_display_time': True},
    {'start_day_time': 'not-a-time'},
    {'project_sort': 'unknown'},
])
def test_settings_reject_values_that_change_legacy_truthiness(patch, tmp_path):
    service = SettingsService(PickleRepository(tmp_path), platform='web')

    with pytest.raises(ValidationError):
        service.update(patch)
