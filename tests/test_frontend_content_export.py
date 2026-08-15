from scripts.export_frontend_content import build_payloads


def test_frontend_content_export_has_all_languages_and_stable_help_keys():
    payloads = build_payloads()
    manifest = payloads['manifest.json']

    assert manifest['languages'] == ['ru', 'en', 'es', 'de', 'fr', 'pt_BR']
    assert manifest['translation_key_count'] > 1000
    for language in manifest['languages']:
        locale = payloads[f'locales/{language}.json']
        help_sections = payloads[f'help/{language}.json']
        assert len(locale) == manifest['translation_key_count']
        assert help_sections[0]['key'] == 'quick_start'
        assert help_sections[0]['content'].startswith('<html>')
