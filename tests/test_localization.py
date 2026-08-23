import re

import game
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
from scripts.generate_translations import (
    extract_frontend_strings,
    frontend_source_strings,
    source_strings,
    translation_preserves_structure,
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


def test_catalog_covers_current_application_sources():
    current_sources, _ = source_strings()
    assert set(current_sources) <= set(TRANSLATIONS["ru"])


def test_vue_and_qt_free_sources_are_covered_in_every_language():
    vue_sources = frontend_source_strings()
    current_sources, _ = source_strings()

    assert vue_sources == sorted(set(vue_sources))
    assert 'Проекты' in vue_sources
    assert 'Не удалось применить заморозку.' in current_sources
    for source in vue_sources:
        assert TRANSLATIONS['ru'][source] == source
    for language in TARGET_LANGUAGES:
        missing = [
            source for source in current_sources
            if source not in TRANSLATIONS[language]
        ]
        assert not missing, f'{language}: missing {missing[:10]!r}'


def test_frontend_extraction_ignores_comments_and_dynamic_user_values(tmp_path):
    typescript = tmp_path / 'sample.ts'
    typescript.write_text(
        """
        const title = t('Настройки')
        const count = locale.translate("Проектов: {count}")
        const dynamic = t(`Удалить проект ${project.name}`)
        // t('Строка только в комментарии')
        /* locale.translate('Ещё один комментарий') */
        """,
        encoding='utf-8',
    )

    assert extract_frontend_strings(typescript) == {
        'Настройки',
        'Проектов: {count}',
    }


def test_vue_extraction_reads_template_calls_and_script_registries(tmp_path):
    component = tmp_path / 'Sample.vue'
    component.write_text(
        """
        <script setup lang="ts">
        const labels = [{ key: 'default', label: 'Обычный' }]
        const dynamic = `Личное значение ${project.name}`
        </script>
        <template>
          <h1>{{ t('Проекты') }}</h1>
          <div :aria-label="locale.translate('Список проектов')" />
          <!-- {{ t('Скрытый комментарий') }} -->
        </template>
        """,
        encoding='utf-8',
    )

    assert extract_frontend_strings(component) == {
        'Обычный',
        'Проекты',
        'Список проектов',
    }


def test_catalog_preserves_placeholders_and_html_structure():
    current_sources, _ = source_strings()
    for language in TARGET_LANGUAGES:
        malformed = [
            source for source in current_sources
            if not translation_preserves_structure(
                source, TRANSLATIONS[language][source]
            )
        ]
        assert not malformed, f'{language}: malformed {malformed[:5]!r}'


def test_manual_terminology_is_baked_for_qt_free_clients():
    assert TRANSLATIONS['en']['Исследователь'] == 'Explorer'
    assert TRANSLATIONS['de']['Редактор'] == 'Lektor'
    assert TRANSLATIONS['pt_BR']['Искра замысла'] == 'Centelha de uma ideia'


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


def test_creative_event_controls_are_localized():
    expected_safe_choices = {
        'en': 'Safe choice',
        'es': 'Elección segura',
        'de': 'Sichere Wahl',
        'fr': 'Choix sûr',
        'pt_BR': 'Escolha segura',
    }
    for language, expected in expected_safe_choices.items():
        assert tr('Надёжный выбор', language) == expected
        assert tr('Решить событие', language) != 'Решить событие'
        assert tr('Инвентарь и кабинет', language) != 'Инвентарь и кабинет'


def test_manuscript_journey_terms_are_localized():
    assert tr('Переломная точка', 'en') == 'Turning Point'
    assert tr('следующий рубеж', 'de') == 'nächster Meilenstein'
    assert tr('Искра замысла', 'pt_BR') == 'Centelha de uma ideia'
    assert tr('Путь этапа', 'es') == 'Ruta de la etapa'


def test_mindmap_terms_are_localized():
    expected_titles = {
        'en': 'Project and Stage Maps',
        'es': 'Mapas de proyectos y etapas',
        'de': 'Projekt- und Etappenkarten',
        'fr': 'Cartes des projets et des étapes',
        'pt_BR': 'Mapas de projetos e etapas',
    }
    for language, expected_title in expected_titles.items():
        assert tr('Карты проектов и этапов', language) == expected_title
        assert tr('Редактор карты', language) != 'Редактор карты'
        assert tr('Все изменения сохранены.', language) != 'Все изменения сохранены.'
        assert (
            tr('Карта не была создана при работе над этапом.', language)
            != 'Карта не была создана при работе над этапом.'
        )
        assert (
            tr('Объединять карты этапов в карте проекта', language)
            != 'Объединять карты этапов в карте проекта'
        )
        assert tr('Свободный узел', language) not in {
            'Свободный узел',
            'Nœud gratuit',
            'Nó grátis',
        }
        assert 'Mind Elixir' in tr('Карта Mind Elixir (*.json)', language)


def test_project_notes_terms_are_localized_and_system_tag_is_stable():
    expected_titles = {
        'en': 'Project Notes',
        'es': 'Notas del proyecto',
        'de': 'Projektnotizen',
        'fr': 'Notes du projet',
        'pt_BR': 'Notas do projeto',
    }
    for language, expected_title in expected_titles.items():
        assert tr('Заметки проекта', language) == expected_title
        assert tr('Поиск по заметкам', language) != 'Поиск по заметкам'
        assert tr('Заметка карты', language) != 'Заметка карты'
        assert tr('Открыть на карте', language) != 'Открыть на карте'
        assert tr('#карта', language) == '#карта'


def test_cabinet_relic_cards_are_localized():
    cyrillic = re.compile(r"[А-Яа-яЁё]")
    for language in TARGET_LANGUAGES:
        for relic in game.CABINET_RELICS.values():
            assert not cyrillic.search(tr(relic['name'], language))
            assert not cyrillic.search(tr(relic['description'], language))
            assert not cyrillic.search(tr(relic['condition'], language))


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
