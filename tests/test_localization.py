import re

import game_data
from game_UI import (
    localized_game_description,
    localized_game_name,
    localized_item_result,
)
from localization import (
    ENGLISH_AGREEMENT_HTML,
    localized_unit_name,
    normalize_language,
    tr,
)
from translations_catalog import AGREEMENT_SOURCE, TRANSLATIONS


TARGET_LANGUAGES = ("en", "es", "de", "fr", "pt_BR")


def test_language_normalization_and_fallback():
    assert normalize_language("ru_RU") == "ru"
    assert normalize_language("pt-BR") == "pt_BR"
    assert normalize_language("it_IT") == "en"


def test_all_catalogs_cover_the_same_sources():
    russian_sources = set(TRANSLATIONS["ru"])
    assert russian_sources
    for language in TARGET_LANGUAGES:
        assert set(TRANSLATIONS[language]) == russian_sources


def test_interface_translations_do_not_retain_cyrillic():
    cyrillic = re.compile(r"[А-Яа-яЁё]")
    for language in TARGET_LANGUAGES:
        assert not cyrillic.search(tr("Настройки", language))
        assert not cyrillic.search(tr("Выберите проект", language))
        assert not cyrillic.search(tr("Ошибка", language))


def test_formatted_messages_preserve_runtime_values():
    source = 'Проект "Черновик" уже существует!'
    assert tr(source, "en") == 'Project "Черновик" already exists!'
    assert tr(source, "de") == 'Projekt „Черновик“ existiert bereits!'


def test_specialization_terms_and_cooldown_are_localized():
    assert tr('Исследователь', 'en') == 'Explorer'
    assert tr('Редактор', 'de') == 'Lektor'
    assert tr('Марафонец', 'es') == 'Maratonista'
    assert tr('Смена будет доступна через 9 дн.', 'fr') == (
        'La spécialisation pourra être changée dans 9 jours.'
    )


def test_non_russian_languages_share_the_english_agreement():
    for language in TARGET_LANGUAGES:
        assert tr(AGREEMENT_SOURCE, language) == ENGLISH_AGREEMENT_HTML
    assert tr(AGREEMENT_SOURCE, "ru") == AGREEMENT_SOURCE


def test_project_note_units_are_localized():
    assert localized_unit_name("symbols", 1, "de") == "Zeichen"
    assert localized_unit_name("symbols", 67780, "de") == "Zeichen"
    assert localized_unit_name("author_list", 2, "de") == "Autorenblätter"
    assert localized_unit_name("symbols", 1, "es") == "carácter"
    assert localized_unit_name("symbols", 2, "es") == "caracteres"


def test_inventory_and_buff_display_names_keep_canonical_registry_keys():
    cyrillic = re.compile(r"[А-Яа-яЁё]")
    canonical_names = {
        category: {
            key: item.name
            for key, item in items.items()
        }
        for category, items in game_data.ITEM_REGISTRY.items()
    }

    for language in TARGET_LANGUAGES:
        for category, items in game_data.ITEM_REGISTRY.items():
            for key, item in items.items():
                assert not cyrillic.search(localized_game_name(item.name, language))
                for buff in item.get_buffs():
                    assert not cyrillic.search(
                        localized_game_name(buff.name, language)
                    )
                    assert not cyrillic.search(
                        localized_game_description(buff.description, language)
                    )
                    assert not cyrillic.search(
                        localized_item_result(
                            f"Получен эффект: {buff.name}",
                            item,
                            language,
                        )
                    )

                registry_key, registry_item = game_data.find_registry_item(
                    category, key
                )
                assert registry_key == key
                assert registry_item is item

    assert canonical_names == {
        category: {
            key: item.name
            for key, item in items.items()
        }
        for category, items in game_data.ITEM_REGISTRY.items()
    }
