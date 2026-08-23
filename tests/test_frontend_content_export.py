from scripts.export_frontend_content import build_payloads, export
from scripts.generate_translations import source_strings, translation_preserves_structure
from translations_catalog import AGREEMENT_SOURCE, TRANSLATIONS


def test_frontend_content_export_has_all_languages_and_stable_help_keys():
    payloads = build_payloads()
    manifest = payloads['manifest.json']

    assert manifest['languages'] == ['ru', 'en', 'es', 'de', 'fr', 'pt_BR']
    assert manifest['translation_key_count'] > 1000
    assert set(payloads['locales/ru.json']) == set(TRANSLATIONS['ru'])
    current_sources, _ = source_strings()
    for language in manifest['languages']:
        locale = payloads[f'locales/{language}.json']
        help_sections = payloads[f'help/{language}.json']
        assert len(locale) == manifest['translation_key_count']
        assert help_sections[0]['key'] == 'quick_start'
        assert help_sections[0]['content'].startswith('<html>')
        if language != 'ru':
            malformed = [
                source for source in current_sources
                if source != AGREEMENT_SOURCE
                and not translation_preserves_structure(source, locale[source])
            ]
            assert not malformed, f'{language}: malformed {malformed[:5]!r}'


def test_frontend_content_export_is_deterministic(tmp_path):
    changed = export(tmp_path)

    assert changed
    assert export(tmp_path, check=True) == []
