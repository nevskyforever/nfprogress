"""Runtime localization for UI forms and strings created in Python code."""

from __future__ import annotations

import re
from functools import lru_cache

from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
from PySide6.QtWidgets import QApplication, QMessageBox

try:
    from translations_catalog import AGREEMENT_SOURCE, TRANSLATIONS
except ImportError:
    AGREEMENT_SOURCE = ""
    TRANSLATIONS = {}


SUPPORTED_LANGUAGES = {
    "ru": "Русский",
    "en": "English",
    "es": "Español",
    "de": "Deutsch",
    "fr": "Français",
    "pt_BR": "Português (Brasil)",
}
DEFAULT_LANGUAGE = "en"

UNIT_NAMES = {
    "ru": {
        "symbols": ("символ", "символа", "символов"),
        "A4": ("лист", "листа", "листов"),
        "author_list": ("авторский лист", "авторских листа", "авторских листов"),
        "ficbook_pages": ("страница", "страницы", "страниц"),
    },
    "en": {
        "symbols": ("character", "characters"),
        "A4": ("sheet", "sheets"),
        "author_list": ("author's sheet", "author's sheets"),
        "ficbook_pages": ("page", "pages"),
    },
    "es": {
        "symbols": ("carácter", "caracteres"),
        "A4": ("hoja", "hojas"),
        "author_list": ("hoja de autor", "hojas de autor"),
        "ficbook_pages": ("página", "páginas"),
    },
    "de": {
        "symbols": ("Zeichen", "Zeichen"),
        "A4": ("Blatt", "Blätter"),
        "author_list": ("Autorenblatt", "Autorenblätter"),
        "ficbook_pages": ("Seite", "Seiten"),
    },
    "fr": {
        "symbols": ("caractère", "caractères"),
        "A4": ("feuille", "feuilles"),
        "author_list": ("feuillet d’auteur", "feuillets d’auteur"),
        "ficbook_pages": ("page", "pages"),
    },
    "pt_BR": {
        "symbols": ("caractere", "caracteres"),
        "A4": ("folha", "folhas"),
        "author_list": ("lauda autoral", "laudas autorais"),
        "ficbook_pages": ("página", "páginas"),
    },
}

ENGLISH_AGREEMENT_HTML = """
<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
body { color: #ffffff; font-family: Arial; font-size: 13pt; }
h1 { font-size: xx-large; } h2 { font-size: x-large; }
p, li { white-space: pre-wrap; }
</style></head><body>
<h1>ADDITIONAL TERMS OF USE FOR NFPROGRESS</h1>
<p>Samara<br>23 July 2026</p>
<h2>1. General Provisions</h2>
<p>1.1. The nfprogress computer program is distributed under the GNU General
Public License version 3 (GPLv3).</p>
<p>1.2. This document neither modifies nor restricts the rights granted to the
User under GPLv3. It governs only matters not covered by that license.</p>
<p>1.3. If this document conflicts with GPLv3, the GPLv3 terms prevail.</p>
<h2>2. Intellectual Property</h2>
<p>2.1. The exclusive rights to the program belong to Roman Ruslanovich
Kishochkin.</p>
<p>2.2. The program is distributed under GPLv3, including the User's right to:</p>
<ul>
<li>use the program;</li>
<li>study how it works;</li>
<li>modify the source code;</li>
<li>distribute original and modified versions of the program in compliance
with GPLv3.</li>
</ul>
<h2>3. Personal Data</h2>
<p>3.1. The program does not require user registration and does not collect
names, email addresses, or other identifying information.</p>
<p>3.2. While the program is running, technical information required for
update checks and error diagnostics may be transmitted automatically,
including:</p>
<ul>
<li>the program version;</li>
<li>the operating system version;</li>
<li>information about errors that occurred.</li>
</ul>
<p>3.3. This information is used solely to ensure that the program functions
correctly and is not used to identify the User.</p>
<h2>4. Disclaimer of Warranties</h2>
<p>4.1. The program is provided “AS IS”.</p>
<p>4.2. To the maximum extent permitted by applicable law, the Copyright
Holder makes no warranties regarding the program, including warranties of
fitness for a particular purpose, uninterrupted operation, or freedom from
errors.</p>
<p>4.3. The User independently decides whether to use the program and assumes
all associated risks.</p>
<h2>5. Limitation of Liability</h2>
<p>5.1. To the extent permitted by the laws of the Russian Federation, the
Copyright Holder shall not be liable for any losses arising from the use of,
or inability to use, the program.</p>
<p>5.2. This clause does not apply where liability cannot be limited by law.</p>
<h2>6. Governing Law</h2>
<p>6.1. Matters not governed by GPLv3 are governed by the laws of the Russian
Federation.</p>
<p>6.2. Before applying to a court, the parties shall seek to resolve any
dispute through negotiation.</p>
<h2>7. Contact Details</h2>
<p>Copyright Holder:<br>Roman Ruslanovich Kishochkin</p>
<p>Email: <b>app@nfpr.ru</b></p>
</body></html>
"""

TRANSLATION_OVERRIDES = {
    "en": {
        "Стрики": "Streaks",
        "Автозаморозка стрика": "Automatic streak freeze",
        "Стрики выключены": "Streaks disabled",
        "Если вы отключите стрики проекта, текущий стрик проекта будет завершён.\nВключённые стрики этапов продолжат работать по своим целям на день.\nПродолжить?": "If you disable project streaks, the current project streak will end.\nEnabled stage streaks will continue based on their daily goals.\nContinue?",
        "Если вы отключите стрики, текущий стрик будет завершён!\nПродолжить?": "If you disable streaks, the current streak will end!\nContinue?",
        "Заморозка глобального стрика": "Global streak freeze",
        "Нет активных проектов с активным стриком. Заморозить глобальный стрик на сегодня?": "There are no active projects with an active streak. Freeze the global streak for today?",
        "Не удалось применить заморозку: проверьте инвентарь и статус глобального стрика.": "Could not apply the freeze: check the inventory and global streak status.",
        "Глобальный стрик заморожен!": "Global streak frozen!",
        "Глобальный стрик автоматически заморожен.": "Global streak automatically frozen.",
        "Бесконечный проект": "Infinite project",
        "Параметр": "Parameter",
        "Значение за награду": "Value per reward",
        "Количество": "Quantity",
        "Итого": "Total",
        "Осталось": "Remaining",
        "В наличии": "In stock",
        "нельзя использовать": "cannot be used",
        "за": "for",
        "к параметру": "to the parameter",
        "за завершение квеста": "for completing a quest",
        "Часовое зелье супердоходности": "Hourly Potion of Super Profitability",
        "Суточное зелье супердоходности": "Daily Potion of Super Profitability",
        "Недельное зелье познания": "Weekly Potion of Knowledge",
        "Недельное зелье доходности": "Weekly Potion of Profitability",
        "Недельное зелье просвещения": "Weekly Potion of Enlightenment",
        "Недельное зелье супердоходности": "Weekly Potion of Super Profitability",
        "Супербустер прибыли": "Super Profit Booster",
        "Применено зелье суперприбыли": "Super Profit Potion applied",
        "Увеличивает коэффициент монет на 10 на один час": "Increases coin ratio by 10 for one hour",
        "Увеличивает коэффициент монет на 10 на один день": "Increases coin ratio by 10 for one day",
        "Амулет восстановления": "Recovery Amulet",
        "Постоянно увеличивает коэффициент восстановления здоровья на 1.": "Permanently increases the health recovery ratio by 1.",
        "Исцеление амулетом": "Amulet Healing",
        "Постоянный бонус к коэффициенту восстановления здоровья.": "Permanent bonus to the health recovery ratio.",
        "символов": "characters",
        " символов": " characters",
    },
    "es": {
        "Стрики": "Rachas",
        "Автозаморозка стрика": "Congelación automática de racha",
        "Стрики выключены": "Rachas desactivadas",
        "Если вы отключите стрики проекта, текущий стрик проекта будет завершён.\nВключённые стрики этапов продолжат работать по своим целям на день.\nПродолжить?": "Si desactivas las rachas del proyecto, la racha actual del proyecto finalizará.\nLas rachas activadas de las etapas seguirán funcionando según sus objetivos diarios.\n¿Continuar?",
        "Если вы отключите стрики, текущий стрик будет завершён!\nПродолжить?": "Si desactivas las rachas, la racha actual finalizará.\n¿Continuar?",
        "Заморозка глобального стрика": "Congelación de racha global",
        "Нет активных проектов с активным стриком. Заморозить глобальный стрик на сегодня?": "No hay proyectos activos con una racha activa. ¿Congelar la racha global de hoy?",
        "Не удалось применить заморозку: проверьте инвентарь и статус глобального стрика.": "No se pudo aplicar la congelación: comprueba el inventario y el estado de la racha global.",
        "Глобальный стрик заморожен!": "¡Racha global congelada!",
        "Глобальный стрик автоматически заморожен.": "La racha global se congeló automáticamente.",
        "Бесконечный проект": "Proyecto infinito",
        "Параметр": "Parámetro",
        "Значение за награду": "Valor por recompensa",
        "Количество": "Cantidad",
        "Итого": "Total",
        "Осталось": "Restante",
        "В наличии": "En stock",
        "нельзя использовать": "no se puede usar",
        "за": "por",
        "к параметру": "al parámetro",
        "за завершение квеста": "por completar una misión",
        "Часовое зелье супердоходности": "Poción de superrentabilidad por hora",
        "Суточное зелье супердоходности": "Poción diaria de superrentabilidad",
        "Недельное зелье познания": "Poción semanal de conocimiento",
        "Недельное зелье доходности": "Poción semanal de rentabilidad",
        "Недельное зелье просвещения": "Poción semanal de iluminación",
        "Недельное зелье супердоходности": "Poción semanal de superrentabilidad",
        "Супербустер прибыли": "Superpotenciador de ganancias",
        "Применено зелье суперприбыли": "Poción de superganancias aplicada",
        "Увеличивает коэффициент монет на 10 на один час": "Aumenta la proporción de monedas en 10 durante una hora",
        "Увеличивает коэффициент монет на 10 на один день": "Aumenta la proporción de monedas en 10 durante un día",
        "Амулет восстановления": "Amuleto de recuperación",
        "Постоянно увеличивает коэффициент восстановления здоровья на 1.": "Aumenta permanentemente en 1 la proporción de recuperación de salud.",
        "Исцеление амулетом": "Curación del amuleto",
        "Постоянный бонус к коэффициенту восстановления здоровья.": "Bono permanente a la proporción de recuperación de salud.",
        "символов": "caracteres",
        " символов": " caracteres",
    },
    "de": {
        "Стрики": "Serien",
        "Автозаморозка стрика": "Serie automatisch einfrieren",
        "Стрики выключены": "Serien deaktiviert",
        "Если вы отключите стрики проекта, текущий стрик проекта будет завершён.\nВключённые стрики этапов продолжат работать по своим целям на день.\nПродолжить?": "Wenn Sie die Projektserien deaktivieren, wird die aktuelle Projektserie beendet.\nAktivierte Etappenserien laufen anhand ihrer Tagesziele weiter.\nFortfahren?",
        "Если вы отключите стрики, текущий стрик будет завершён!\nПродолжить?": "Wenn Sie Serien deaktivieren, wird die aktuelle Serie beendet!\nFortfahren?",
        "Заморозка глобального стрика": "Globale Serie einfrieren",
        "Нет активных проектов с активным стриком. Заморозить глобальный стрик на сегодня?": "Es gibt keine aktiven Projekte mit einer aktiven Serie. Die globale Serie für heute einfrieren?",
        "Не удалось применить заморозку: проверьте инвентарь и статус глобального стрика.": "Die Einfrierung konnte nicht angewendet werden: Bitte Inventar und Status der globalen Serie prüfen.",
        "Глобальный стрик заморожен!": "Globale Serie eingefroren!",
        "Глобальный стрик автоматически заморожен.": "Die globale Serie wurde automatisch eingefroren.",
        "Бесконечный проект": "Unbegrenztes Projekt",
        "Параметр": "Parameter",
        "Значение за награду": "Wert pro Belohnung",
        "Количество": "Anzahl",
        "Итого": "Gesamt",
        "Осталось": "Verbleibend",
        "В наличии": "Auf Lager",
        "нельзя использовать": "kann nicht verwendet werden",
        "за": "für",
        "к параметру": "auf den Parameter",
        "за завершение квеста": "für den Abschluss einer Quest",
        "Часовое зелье супердоходности": "Stündlicher Trank der Superrentabilität",
        "Суточное зелье супердоходности": "Täglicher Trank der Superrentabilität",
        "Недельное зелье познания": "Wöchentlicher Trank des Wissens",
        "Недельное зелье доходности": "Wöchentlicher Trank der Rentabilität",
        "Недельное зелье просвещения": "Wöchentlicher Trank der Erleuchtung",
        "Недельное зелье супердоходности": "Wöchentlicher Trank der Superrentabilität",
        "Супербустер прибыли": "Super-Gewinnbooster",
        "Применено зелье суперприбыли": "Supergewinntrank angewendet",
        "Увеличивает коэффициент монет на 10 на один час": "Erhöht das Münzverhältnis eine Stunde lang um 10",
        "Увеличивает коэффициент монет на 10 на один день": "Erhöht das Münzverhältnis einen Tag lang um 10",
        "Амулет восстановления": "Amulett der Erholung",
        "Постоянно увеличивает коэффициент восстановления здоровья на 1.": "Erhöht den Gesundheitsregenerationsfaktor dauerhaft um 1.",
        "Исцеление амулетом": "Amulettheilung",
        "Постоянный бонус к коэффициенту восстановления здоровья.": "Dauerhafter Bonus auf den Gesundheitsregenerationsfaktor.",
        "символов": "Zeichen",
        " символов": " Zeichen",
    },
    "fr": {
        "Стрики": "Séries",
        "Автозаморозка стрика": "Gel automatique de la série",
        "Стрики выключены": "Séries désactivées",
        "Если вы отключите стрики проекта, текущий стрик проекта будет завершён.\nВключённые стрики этапов продолжат работать по своим целям на день.\nПродолжить?": "Si vous désactivez les séries du projet, la série actuelle du projet prendra fin.\nLes séries activées des étapes continueront selon leurs objectifs quotidiens.\nContinuer ?",
        "Если вы отключите стрики, текущий стрик будет завершён!\nПродолжить?": "Si vous désactivez les séries, la série actuelle prendra fin !\nContinuer ?",
        "Заморозка глобального стрика": "Gel de la série globale",
        "Нет активных проектов с активным стриком. Заморозить глобальный стрик на сегодня?": "Il n’y a aucun projet actif avec une série active. Geler la série globale pour aujourd’hui ?",
        "Не удалось применить заморозку: проверьте инвентарь и статус глобального стрика.": "Impossible d’appliquer le gel : vérifiez l’inventaire et l’état de la série globale.",
        "Глобальный стрик заморожен!": "Série globale gelée !",
        "Глобальный стрик автоматически заморожен.": "La série globale a été gelée automatiquement.",
        "Бесконечный проект": "Projet illimité",
        "Параметр": "Paramètre",
        "Значение за награду": "Valeur par récompense",
        "Количество": "Quantité",
        "Итого": "Total",
        "Осталось": "Restant",
        "В наличии": "En stock",
        "нельзя использовать": "ne peut pas être utilisé",
        "за": "pour",
        "к параметру": "au paramètre",
        "за завершение квеста": "pour avoir terminé une quête",
        "Часовое зелье супердоходности": "Potion horaire de super rentabilité",
        "Суточное зелье супердоходности": "Potion quotidienne de super rentabilité",
        "Недельное зелье познания": "Potion hebdomadaire de connaissance",
        "Недельное зелье доходности": "Potion hebdomadaire de rentabilité",
        "Недельное зелье просвещения": "Potion hebdomadaire d’illumination",
        "Недельное зелье супердоходности": "Potion hebdomadaire de super rentabilité",
        "Супербустер прибыли": "Super booster de profits",
        "Применено зелье суперприбыли": "Potion de super profit appliquée",
        "Увеличивает коэффициент монет на 10 на один час": "Augmente le ratio de pièces de 10 pendant une heure",
        "Увеличивает коэффициент монет на 10 на один день": "Augmente le ratio de pièces de 10 pendant un jour",
        "Амулет восстановления": "Amulette de récupération",
        "Постоянно увеличивает коэффициент восстановления здоровья на 1.": "Augmente définitivement le ratio de récupération de santé de 1.",
        "Исцеление амулетом": "Soin de l’amulette",
        "Постоянный бонус к коэффициенту восстановления здоровья.": "Bonus permanent au ratio de récupération de santé.",
        "символов": "caractères",
        " символов": " caractères",
    },
    "pt_BR": {
        "Стрики": "Sequências",
        "Автозаморозка стрика": "Congelamento automático da sequência",
        "Стрики выключены": "Sequências desativadas",
        "Если вы отключите стрики проекта, текущий стрик проекта будет завершён.\nВключённые стрики этапов продолжат работать по своим целям на день.\nПродолжить?": "Se você desativar as sequências do projeto, a sequência atual do projeto será encerrada.\nAs sequências ativadas das etapas continuarão conforme suas metas diárias.\nContinuar?",
        "Если вы отключите стрики, текущий стрик будет завершён!\nПродолжить?": "Se você desativar as sequências, a sequência atual será encerrada!\nContinuar?",
        "Заморозка глобального стрика": "Congelamento da sequência global",
        "Нет активных проектов с активным стриком. Заморозить глобальный стрик на сегодня?": "Não há projetos ativos com uma sequência ativa. Congelar a sequência global de hoje?",
        "Не удалось применить заморозку: проверьте инвентарь и статус глобального стрика.": "Não foi possível aplicar o congelamento: verifique o inventário e o status da sequência global.",
        "Глобальный стрик заморожен!": "Sequência global congelada!",
        "Глобальный стрик автоматически заморожен.": "A sequência global foi congelada automaticamente.",
        "Бесконечный проект": "Projeto infinito",
        "Параметр": "Parâmetro",
        "Значение за награду": "Valor por recompensa",
        "Количество": "Quantidade",
        "Итого": "Total",
        "Осталось": "Restante",
        "В наличии": "Em estoque",
        "нельзя использовать": "não pode ser usado",
        "за": "por",
        "к параметру": "no parâmetro",
        "за завершение квеста": "por concluir uma missão",
        "Часовое зелье супердоходности": "Poção de superlucratividade por hora",
        "Суточное зелье супердоходности": "Poção diária de superlucratividade",
        "Недельное зелье познания": "Poção semanal de conhecimento",
        "Недельное зелье доходности": "Poção semanal de lucratividade",
        "Недельное зелье просвещения": "Poção semanal de iluminação",
        "Недельное зелье супердоходности": "Poção semanal de superlucratividade",
        "Супербустер прибыли": "Superimpulsionador de lucro",
        "Применено зелье суперприбыли": "Poção de superlucro aplicada",
        "Увеличивает коэффициент монет на 10 на один час": "Aumenta a proporção de moedas em 10 por uma hora",
        "Увеличивает коэффициент монет на 10 на один день": "Aumenta a proporção de moedas em 10 por um dia",
        "Амулет восстановления": "Amuleto de recuperação",
        "Постоянно увеличивает коэффициент восстановления здоровья на 1.": "Aumenta permanentemente em 1 a proporção de recuperação de saúde.",
        "Исцеление амулетом": "Cura do amuleto",
        "Постоянный бонус к коэффициенту восстановления здоровья.": "Bônus permanente para a proporção de recuperação de saúde.",
        "символов": "caracteres",
        " символов": " caracteres",
    },
}

_current_language = "ru"
_application_translator: QTranslator | None = None
_qt_translator: QTranslator | None = None
_placeholder_pattern = re.compile(r"\{[^{}]*\}")


def normalize_language(language: str | None) -> str:
    if not language:
        return DEFAULT_LANGUAGE

    normalized = str(language).replace("-", "_")
    if normalized in SUPPORTED_LANGUAGES:
        return normalized

    language_code = normalized.split("_", 1)[0].lower()
    if language_code == "pt":
        return "pt_BR"
    if language_code in SUPPORTED_LANGUAGES:
        return language_code
    return DEFAULT_LANGUAGE


def system_language() -> str:
    return normalize_language(QLocale.system().name())


def current_language() -> str:
    return _current_language


def localized_unit_name(
    unit_code: str,
    number: int | float,
    language: str | None = None,
) -> str:
    """Return a localized unit form without changing the stored unit code."""
    language = normalize_language(language or _current_language)
    forms = UNIT_NAMES.get(language, UNIT_NAMES["en"]).get(unit_code)
    if forms is None:
        return unit_code

    absolute_number = abs(number)
    if language != "ru":
        return forms[0] if absolute_number == 1 else forms[1]

    rounded_number = (
        int(absolute_number)
        if absolute_number == int(absolute_number)
        else int(absolute_number) + 1
    )
    if rounded_number % 10 == 1 and rounded_number % 100 != 11:
        return forms[0]
    if (
        2 <= rounded_number % 10 <= 4
        and (rounded_number % 100 < 10 or rounded_number % 100 >= 20)
    ):
        return forms[1]
    return forms[2]


def _template_regex(template: str) -> tuple[re.Pattern[str], list[str]] | None:
    matches = list(_placeholder_pattern.finditer(template))
    if not matches:
        return None

    parts = []
    placeholders = []
    position = 0
    for index, match in enumerate(matches):
        parts.append(re.escape(template[position:match.start()]))
        parts.append(f"(?P<value_{index}>.*?)")
        placeholders.append(match.group(0))
        position = match.end()
    parts.append(re.escape(template[position:]))
    return re.compile("^" + "".join(parts) + "$", re.DOTALL), placeholders


@lru_cache(maxsize=None)
def _template_entries(language: str, reverse: bool = False):
    entries = []
    language_catalog = TRANSLATIONS.get(language, {})
    for source, translated in language_catalog.items():
        template = translated if reverse else source
        replacement = source if reverse else translated
        compiled = _template_regex(template)
        if compiled is not None:
            entries.append((len(template), compiled[0], compiled[1], replacement))
    entries.sort(key=lambda item: item[0], reverse=True)
    return entries


@lru_cache(maxsize=None)
def _reverse_exact(language: str) -> dict[str, str]:
    return {
        translated: source
        for source, translated in TRANSLATIONS.get(language, {}).items()
        if translated and translated != source
    }


def _apply_template(text: str, entries) -> str | None:
    for _, pattern, placeholders, replacement in entries:
        match = pattern.match(text)
        if match is None:
            continue
        values = {
            placeholder: match.group(f"value_{index}")
            for index, placeholder in enumerate(placeholders)
        }
        result = replacement
        for placeholder, value in values.items():
            result = result.replace(placeholder, value)
        return result
    return None


def source_text(text: object) -> object:
    if not isinstance(text, str) or not text:
        return text
    if _current_language == "ru":
        return text

    source = _reverse_exact(_current_language).get(text)
    if source is not None:
        return source
    return _apply_template(text, _template_entries(_current_language, reverse=True)) or text


def _normalize_domain_terms(source: str, translated: str, language: str) -> str:
    if "стрик" not in source.casefold():
        return translated

    replacements = {
        "en": (
            (r"\bSTREAM\b", "STREAK"),
            (r"\bstream\b", "streak"),
            (r"\bstrings\b", "streaks"),
            (r"\bstring\b", "streak"),
        ),
        "es": (
            (r"\bcadenas\b", "rachas"),
            (r"\bcadena\b", "racha"),
        ),
        "de": (
            (r"\bZeichenfolgen\b", "Streaks"),
            (r"\bZeichenfolge\b", "Streak"),
            (r"\bStreifen\b", "Streaks"),
            (r"\bSerie\b", "Streak"),
        ),
        "fr": (
            (r"\bSéquence\b", "Série"),
            (r"\bséquences\b", "séries"),
            (r"\bséquence\b", "série"),
            (r"\bchaînes\b", "séries"),
            (r"\bchaîne\b", "série"),
            (r"\bmondiale\b", "globale"),
        ),
        "pt_BR": (
            (r"\bTRANSMISSÃO\b", "SEQUÊNCIA"),
            (r"\bSTREAM\b", "SEQUÊNCIA"),
            (r"\bstrings\b", "sequências"),
            (r"\bstring\b", "sequência"),
            (r"\braias\b", "sequências"),
            (r"\braia\b", "sequência"),
            (r"\blistras\b", "sequências"),
            (r"\blistra\b", "sequência"),
            (r"\bfaixas\b", "sequências"),
            (r"\bfaixa\b", "sequência"),
            (r"\bmaré\b", "sequência"),
            (r"\bfase\b", "sequência"),
        ),
    }
    for pattern, replacement in replacements.get(language, ()):
        translated = re.sub(pattern, replacement, translated)
    return translated


def _restore_html_markup(source: str, translated: str) -> str:
    if "<html" not in source.casefold() and "<!doctype html" not in source.casefold():
        return translated

    source_parts = re.split(r"(<[^>]+>)", source)
    translated_parts = re.split(r"(<[^>]+>)", translated)
    if len(source_parts) != len(translated_parts):
        return translated

    result = []
    for index, source_part in enumerate(source_parts):
        if index % 2:
            result.append(source_part)
        elif re.search(r"[А-Яа-яЁё]", source_part):
            result.append(translated_parts[index])
        else:
            result.append(source_part)
    return "".join(result)


def tr(text: object, language: str | None = None) -> object:
    """Translate a Russian source string, including formatted message templates."""
    if not isinstance(text, str) or not text:
        return text

    target_language = normalize_language(language or _current_language)
    if target_language == "ru":
        return source_text(text)

    source = source_text(text)
    if source == AGREEMENT_SOURCE and AGREEMENT_SOURCE:
        return ENGLISH_AGREEMENT_HTML

    translated = TRANSLATION_OVERRIDES.get(target_language, {}).get(source)
    if translated is None:
        translated = TRANSLATIONS.get(target_language, {}).get(source)
    if translated is not None:
        translated = _restore_html_markup(source, translated)
        return _normalize_domain_terms(source, translated, target_language)

    template_translation = _apply_template(
        source, _template_entries(target_language)
    )
    if template_translation is None:
        return source
    return _normalize_domain_terms(source, template_translation, target_language)


class CatalogTranslator(QTranslator):
    def translate(self, context, source_text, disambiguation=None, n=-1):
        return tr(source_text)


def set_language(app: QApplication, language: str) -> str:
    global _application_translator, _current_language, _qt_translator

    language = normalize_language(language)
    if _application_translator is not None:
        app.removeTranslator(_application_translator)
    if _qt_translator is not None:
        app.removeTranslator(_qt_translator)

    _current_language = language
    _application_translator = CatalogTranslator(app)
    app.installTranslator(_application_translator)

    _qt_translator = QTranslator(app)
    translations_path = QLibraryInfo.path(QLibraryInfo.TranslationsPath)
    qt_locale = "pt_BR" if language == "pt_BR" else language
    if _qt_translator.load(f"qtbase_{qt_locale}", translations_path):
        app.installTranslator(_qt_translator)
    QLocale.setDefault(QLocale(qt_locale))
    return language


class LocalizedMessageBox(QMessageBox):
    @staticmethod
    def information(parent, title, text, *args, **kwargs):
        return QMessageBox.information(parent, tr(title), tr(text), *args, **kwargs)

    @staticmethod
    def warning(parent, title, text, *args, **kwargs):
        return QMessageBox.warning(parent, tr(title), tr(text), *args, **kwargs)

    @staticmethod
    def critical(parent, title, text, *args, **kwargs):
        return QMessageBox.critical(parent, tr(title), tr(text), *args, **kwargs)

    @staticmethod
    def question(parent, title, text, *args, **kwargs):
        return QMessageBox.question(parent, tr(title), tr(text), *args, **kwargs)
