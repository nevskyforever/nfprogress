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

MINDMAP_HELP_SOURCE = """<html><body>
<h2>Карты проектов и этапов</h2>
<p>У каждого проекта и каждого этапа есть собственная независимая карта идей. Выберите нужную сущность на вкладке «Проекты» и нажмите «Карта» в панели действий. Редактор откроется в отдельном окне; при первом открытии корневой узел получит название проекта или этапа.</p>
<ul>
<li>Дважды щёлкните узел или нажмите F2, чтобы изменить текст. Tab добавляет дочерний узел, Enter — соседний, Delete удаляет выбранный узел.</li>
<li>«Свободный узел» создаёт узел первого уровня вне автоматической раскладки; его дочерние элементы выглядят как узлы второго уровня. Для него работают обычные шорткаты, контекстное меню, ссылки и «Описание». Заметка также поддерживает редактирование, удаление, ссылки и Tab для новой заметки рядом.</li>
<li>Узлы можно перетаскивать. Контекстное меню добавляет, связывает, перемещает и группирует узлы, а встроенная панель управляет масштабом и центрированием.</li>
<li>Кнопка режима фокуса на нижней панели показывает выбранную ветвь первого уровня отдельно. Повторное нажатие возвращает общую карту.</li>
<li>Значок поиска в верхней панели или Ctrl+F (Command+F на macOS) ищет по обычным и свободным узлам и заметкам. Выберите результат, чтобы развернуть нужную ветвь, выделить элемент и показать его в центре карты.</li>
<li>Изменения сохраняются автоматически вместе с данными проекта. Кнопка «Сохранить» и закрытие окна также записывают актуальное состояние карты.</li>
<li>Кнопка «Экспорт» сохраняет текущую карту в PNG, SVG или JSON. PNG и SVG подходят для просмотра и публикации, а JSON хранит редактируемую структуру карты.</li>
<li>В окне изменения проекта с этапами можно включить «Объединять карты этапов в карте проекта». Тогда каждый этап показывается в общей карте отдельной ветвью первого уровня под своим актуальным именем.</li>
<li>Содержимое ветвей синхронизируется в обе стороны: изменения в общей карте сохраняются в отдельных картах этапов, а изменения отдельной карты появляются при следующем открытии общей карты. Собственные узлы проекта при этом сохраняются.</li>
<li>Переименование, добавление, удаление и изменение порядка этапов автоматически отражаются в общей карте. Отключение объединения скрывает только собранные ветви и не удаляет карты этапов.</li>
<li>Завершённый этап отмечается в общей карте значком ✅. Его существующая карта и ветвь в общей карте доступны только для просмотра. Если карта этапа не создавалась, кнопка «Карта» показывает сообщение, а в общей карте такое же пояснение выводится в нижней строке состояния, не отдельным узлом. Карта завершённого проекта также доступна только для просмотра.</li>
<li>При удалении проекта или этапа удаляется и его карта. При преобразовании этапного проекта в обычный карты удаляемых этапов не объединяются с картой родителя.</li>
</ul>
<p>Редактор и его ресурсы входят в приложение, поэтому для работы с картой подключение к интернету не требуется.</p>
</body></html>"""

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
        "Марафонец": "Marathoner",
        "Ритуалист": "Ritualist",
        "Финишер": "Finisher",
        "Исследователь": "Explorer",
        "Редактор": "Editor",
        "Смена будет доступна через {0} дн.": "Specialization can be changed in {0} days.",
        "Искра замысла": "Spark of an Idea",
        "Переломная точка": "Turning Point",
        "следующий рубеж": "next milestone",
        "Путь этапа": "Stage Path",
        "Карта": "Map",
        "Карта проекта или этапа": "Project or Stage Map",
        "Карты проектов и этапов": "Project and Stage Maps",
        "Объединять карты этапов в карте проекта": "Combine stage maps in the project map",
        MINDMAP_HELP_SOURCE: """<html><body>
<h2>Project and Stage Maps</h2>
<p>Every project and stage has its own independent idea map. Select the project or stage on the “Projects” tab and click “Map” in the action panel. The editor opens in a separate window; the root node is named after the project or stage when the map is first opened.</p>
<ul>
<li>Double-click a node or press F2 to edit its text. Tab adds a child node, Enter adds a sibling, and Delete removes the selected node.</li>
<li>“Free node” creates a first-level node outside automatic layout; its children look like second-level nodes. Regular shortcuts, the context menu, links, and Summary all work. Notes also support editing, deletion, links, and Tab for a nearby note.</li>
<li>Nodes can be dragged. The context menu adds, links, moves, and groups nodes, while the built-in toolbar controls zoom and centering.</li>
<li>The focus mode button on the bottom toolbar displays the selected first-level branch separately. Press it again to return to the combined map.</li>
<li>The search icon on the top toolbar or Ctrl+F (Command+F on macOS) searches regular and free nodes as well as notes. Select a result to expand its branch, select the item, and center it on the map.</li>
<li>Changes are saved automatically with the project data. The “Save” button and closing the window also store the map’s current state.</li>
<li>The Export button saves the current map as PNG, SVG or JSON. PNG and SVG are suitable for viewing and sharing, while JSON stores the editable map structure.</li>
<li>In the edit window for a staged project, you can enable “Combine stage maps in the project map”. Each stage will then appear in the combined map as a separate first-level branch under its current name.</li>
<li>Branch content is synchronized both ways: changes in the combined map are saved to the individual stage maps, and changes to an individual map appear the next time the combined map is opened. The project’s own nodes are preserved.</li>
<li>Renaming, adding, deleting, and reordering stages is automatically reflected in the combined map. Turning off combining only hides the generated branches and does not delete stage maps.</li>
<li>A completed stage is marked with ✅ in the combined map. Its existing map and its branch in the combined map are read-only. If no stage map was created, the “Map” button shows a message, and the combined map displays the same explanation in the bottom status area rather than as a separate node. A completed project map is also read-only.</li>
<li>Deleting a project or stage also deletes its map. When a staged project is converted to a regular project, maps belonging to the removed stages are not merged into the parent map.</li>
</ul>
<p>The editor and its resources are bundled with the application, so an internet connection is not required to use the map.</p>
</body></html>""",
        "Редактор карты": "Map editor",
        "Выберите узел: Tab — дочерний, Enter — соседний, F2 — изменить, Delete — удалить. Карта сохраняется автоматически.": "Select a node: Tab — child, Enter — sibling, F2 — edit, Delete — delete. The map is saved automatically.",
        "Новая тема": "New topic",
        "Завершённый проект или этап: карта доступна только для просмотра.": "Completed project or stage: the map is read-only.",
        "Карта доступна только для просмотра.": "The map is read-only.",
        "Карта не была создана при работе над этапом.": "The map was not created while working on the stage.",
        "Карта готова.": "The map is ready.",
        "Есть несохранённые изменения.": "There are unsaved changes.",
        "Все изменения сохранены.": "All changes are saved.",
        "Загрузка карты…": "Loading map…",
        "Сохранение карты…": "Saving map…",
        "Сохранить карту": "Save map",
        "Закрыть карту": "Close map",
        "Не удалось загрузить редактор карты.": "The map editor could not be loaded.",
        "Не найдены файлы редактора карты.": "The map editor files were not found.",
        "Не удалось получить данные карты.": "The map data could not be retrieved.",
        "Не удалось сохранить карту.": "The map could not be saved.",
        "Редактор вернул повреждённые данные карты.": "The editor returned invalid map data.",
        "Не удалось сохранить карту. Закрыть окно без сохранения?": "The map could not be saved. Close the window without saving?",
        "Этап больше не существует.": "The stage no longer exists.",
        "Проект больше не существует.": "The project no longer exists.",
        "Все записи этапов будут перенесены в проект в хронологическом порядке. Цели и прогресс этапов сложатся и будут пересчитаны как записи одного проекта. Карты этапов не объединяются с картой проекта и будут удалены.": "All stage records will be moved to the project in chronological order. Stage goals and progress will be combined and recalculated as records of one project. Stage maps are not merged with the project map and will be deleted.",
        "Кабинет, реликвии и комплекты": "Cabinet, Relics, and Sets",
        "Предметы творческого ритма": "Creative Rhythm Items",
        "Параметры и умения": "Parameters and Skills",
        "Специализации и мастерство": "Specializations and Mastery",
        "Изменение и статусы": "Editing and Statuses",
        "Игровая цель дня": "Daily Game Challenge",
        "Поиск по справке…": "Search Help…",
        "Поиск не дал результатов": "No search results",
        "Творческий импульс": "Creative Surge",
        "Искра сессии": "Session Spark",
        "Фокус испытания": "Challenge Focus",
        "Длинное дыхание": "Long Breath",
        "Сила ритуала": "Ritual Power",
        "Рывок к финалу": "Final Push",
        "Новый маршрут": "New Route",
        "Точный взгляд": "Keen Eye",
        "Инвентарь и кабинет": "Inventory and Cabinet",
        "Надёжный выбор": "Safe choice",
        "Рискнуть": "Take a risk",
        "Решить событие": "Resolve event",
        "Надёжный выбор даёт гарантированную награду события без риска.": "A safe choice grants the event's guaranteed reward without risk.",
        "Рискнуть — попытаться получить повышенную награду с возможностью неудачи.": "Take a risk for a chance at a greater reward, with the possibility of failure.",
        "Применяет выбранный вариант к ожидающему творческому событию.": "Applies the selected option to the pending creative event.",
        "Решить событие выбранным способом": "Resolve the event using the selected option",
        "Умение восстанавливается.": "The ability is recharging.",
        "Спринт": "Sprint",
        "Поток": "Flow",
        "Глубокая работа": "Deep Work",
        "Редакторский проход": "Editing Pass",
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
        "Марафонец": "Maratonista",
        "Ритуалист": "Ritualista",
        "Финишер": "Finalizador",
        "Исследователь": "Explorador",
        "Редактор": "Editor",
        "Смена будет доступна через {0} дн.": "La especialización se podrá cambiar dentro de {0} días.",
        "Искра замысла": "Chispa de una idea",
        "Переломная точка": "Punto de giro",
        "следующий рубеж": "siguiente hito",
        "Путь этапа": "Ruta de la etapa",
        "Карта": "Mapa",
        "Карта проекта или этапа": "Mapa del proyecto o de la etapa",
        "Карты проектов и этапов": "Mapas de proyectos y etapas",
        "Объединять карты этапов в карте проекта": "Combinar mapas de etapas",
        MINDMAP_HELP_SOURCE: """<html><body>
<h2>Mapas de proyectos y etapas</h2>
<p>Cada proyecto y cada etapa tiene su propio mapa de ideas independiente. Seleccione el proyecto o la etapa en la pestaña «Proyectos» y pulse «Mapa» en el panel de acciones. El editor se abre en una ventana separada; al abrir el mapa por primera vez, el nodo raíz recibe el nombre del proyecto o de la etapa.</p>
<ul>
<li>Haga doble clic en un nodo o pulse F2 para editar el texto. Tab añade un nodo hijo, Intro añade un nodo hermano y Supr elimina el nodo seleccionado.</li>
<li>«Nodo libre» crea un nodo de primer nivel fuera de la distribución automática; sus hijos parecen nodos de segundo nivel. Funcionan los atajos, el menú contextual, los enlaces y Resumen. Las notas admiten edición, eliminación, enlaces y Tab para crear otra cercana.</li>
<li>Los nodos se pueden arrastrar. El menú contextual permite añadir, vincular, mover y agrupar nodos, mientras que la barra integrada controla el zoom y el centrado.</li>
<li>El botón de modo de enfoque de la barra inferior muestra por separado la rama de primer nivel seleccionada. Púlselo de nuevo para volver al mapa combinado.</li>
<li>El icono de búsqueda o Ctrl+F (Command+F en macOS) busca nodos normales y libres, así como notas. Elija un resultado para desplegar su rama, seleccionar el elemento y centrarlo en el mapa.</li>
<li>Los cambios se guardan automáticamente con los datos del proyecto. El botón «Guardar» y el cierre de la ventana también almacenan el estado actual del mapa.</li>
<li>El botón Exportar guarda el mapa actual como PNG, SVG o JSON. PNG y SVG son adecuados para ver y compartir, mientras que JSON almacena la estructura del mapa editable.</li>
<li>En la ventana de edición de un proyecto con etapas puede activar «Combinar mapas de etapas». Cada etapa aparecerá en el mapa combinado como una rama independiente de primer nivel con su nombre actual.</li>
<li>El contenido de las ramas se sincroniza en ambos sentidos: los cambios del mapa combinado se guardan en los mapas individuales de las etapas, y los cambios de un mapa individual aparecen la próxima vez que se abre el mapa combinado. Los nodos propios del proyecto se conservan.</li>
<li>Los cambios de nombre, la adición, la eliminación y la reordenación de las etapas se reflejan automáticamente en el mapa combinado. Desactivar la combinación solo oculta las ramas generadas y no elimina los mapas de las etapas.</li>
<li>Una etapa finalizada se marca con ✅ en el mapa combinado. Su mapa existente y su rama en el mapa combinado son de solo lectura. Si no se creó un mapa para la etapa, el botón «Mapa» muestra un mensaje y el mapa combinado presenta la misma explicación en la zona de estado inferior, no como un nodo separado. El mapa de un proyecto finalizado también es de solo lectura.</li>
<li>Al eliminar un proyecto o una etapa también se elimina su mapa. Al convertir un proyecto con etapas en un proyecto normal, los mapas de las etapas eliminadas no se fusionan con el mapa principal.</li>
</ul>
<p>El editor y sus recursos se incluyen en la aplicación, por lo que no se necesita conexión a internet para utilizar el mapa.</p>
</body></html>""",
        "Редактор карты": "Editor de mapas",
        "Выберите узел: Tab — дочерний, Enter — соседний, F2 — изменить, Delete — удалить. Карта сохраняется автоматически.": "Seleccione un nodo: Tab — hijo, Intro — hermano, F2 — editar, Supr — eliminar. El mapa se guarda automáticamente.",
        "Новая тема": "Nuevo tema",
        "Завершённый проект или этап: карта доступна только для просмотра.": "Proyecto o etapa finalizado: el mapa es de solo lectura.",
        "Карта доступна только для просмотра.": "El mapa es de solo lectura.",
        "Карта не была создана при работе над этапом.": "El mapa no se creó mientras se trabajaba en la etapa.",
        "Карта готова.": "El mapa está listo.",
        "Есть несохранённые изменения.": "Hay cambios sin guardar.",
        "Все изменения сохранены.": "Todos los cambios están guardados.",
        "Загрузка карты…": "Cargando mapa…",
        "Сохранение карты…": "Guardando mapa…",
        "Сохранить карту": "Guardar mapa",
        "Закрыть карту": "Cerrar mapa",
        "Не удалось загрузить редактор карты.": "No se pudo cargar el editor de mapas.",
        "Не найдены файлы редактора карты.": "No se encontraron los archivos del editor de mapas.",
        "Не удалось получить данные карты.": "No se pudieron obtener los datos del mapa.",
        "Не удалось сохранить карту.": "No se pudo guardar el mapa.",
        "Редактор вернул повреждённые данные карты.": "El editor devolvió datos de mapa no válidos.",
        "Не удалось сохранить карту. Закрыть окно без сохранения?": "No se pudo guardar el mapa. ¿Cerrar la ventana sin guardar?",
        "Этап больше не существует.": "La etapa ya no existe.",
        "Проект больше не существует.": "El proyecto ya no existe.",
        "Все записи этапов будут перенесены в проект в хронологическом порядке. Цели и прогресс этапов сложатся и будут пересчитаны как записи одного проекта. Карты этапов не объединяются с картой проекта и будут удалены.": "Todos los registros de las etapas se trasladarán al proyecto en orden cronológico. Los objetivos y el progreso de las etapas se combinarán y se recalcularán como registros de un único proyecto. Los mapas de las etapas no se fusionan con el mapa del proyecto y se eliminarán.",
        "Кабинет, реликвии и комплекты": "Gabinete, reliquias y conjuntos",
        "Предметы творческого ритма": "Objetos del ritmo creativo",
        "Параметры и умения": "Parámetros y habilidades",
        "Специализации и мастерство": "Especializaciones y maestría",
        "Изменение и статусы": "Edición y estados",
        "Игровая цель дня": "Desafío diario del juego",
        "Поиск по справке…": "Buscar en la ayuda…",
        "Поиск не дал результатов": "La búsqueda no produjo resultados",
        "Творческий импульс": "Impulso creativo",
        "Искра сессии": "Chispa de sesión",
        "Фокус испытания": "Enfoque del desafío",
        "Длинное дыхание": "Aliento largo",
        "Сила ритуала": "Poder del ritual",
        "Рывок к финалу": "Impulso final",
        "Новый маршрут": "Nueva ruta",
        "Точный взгляд": "Mirada precisa",
        "Инвентарь и кабинет": "Inventario y gabinete",
        "Надёжный выбор": "Elección segura",
        "Рискнуть": "Arriesgarse",
        "Решить событие": "Resolver evento",
        "Надёжный выбор даёт гарантированную награду события без риска.": "La elección segura concede la recompensa garantizada del evento sin riesgos.",
        "Рискнуть — попытаться получить повышенную награду с возможностью неудачи.": "Arriesgarse permite intentar conseguir una recompensa mayor, con posibilidad de fracasar.",
        "Применяет выбранный вариант к ожидающему творческому событию.": "Aplica la opción elegida al evento creativo pendiente.",
        "Решить событие выбранным способом": "Resolver el evento con la opción elegida",
        "Умение восстанавливается.": "La habilidad se está recargando.",
        "Спринт": "Sprint",
        "Поток": "Flujo",
        "Глубокая работа": "Trabajo profundo",
        "Редакторский проход": "Pase de edición",
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
        "Марафонец": "Marathonläufer",
        "Ритуалист": "Ritualist",
        "Финишер": "Finisher",
        "Исследователь": "Entdecker",
        "Редактор": "Lektor",
        "Смена будет доступна через {0} дн.": "Die Spezialisierung kann in {0} Tagen geändert werden.",
        "Искра замысла": "Funke einer Idee",
        "Переломная точка": "Wendepunkt",
        "следующий рубеж": "nächster Meilenstein",
        "Путь этапа": "Etappenpfad",
        "Карта": "Karte",
        "Карта проекта или этапа": "Projekt- oder Etappenkarte",
        "Карты проектов и этапов": "Projekt- und Etappenkarten",
        "Объединять карты этапов в карте проекта": "Etappenkarten zusammenführen",
        MINDMAP_HELP_SOURCE: """<html><body>
<h2>Projekt- und Etappenkarten</h2>
<p>Jedes Projekt und jede Etappe besitzt eine eigene Ideenkarte. Wählen Sie das Projekt oder die Etappe auf der Registerkarte „Projekte“ aus und klicken Sie im Aktionsbereich auf „Karte“. Der Editor wird in einem separaten Fenster geöffnet; beim ersten Öffnen erhält der Wurzelknoten den Namen des Projekts oder der Etappe.</p>
<ul>
<li>Doppelklicken Sie auf einen Knoten oder drücken Sie F2, um den Text zu bearbeiten. Tab fügt einen untergeordneten Knoten hinzu, die Eingabetaste einen gleichgeordneten Knoten und Entf löscht den ausgewählten Knoten.</li>
<li>„Freier Knoten“ erstellt einen Knoten erster Ebene außerhalb der automatischen Anordnung; seine Kinder sehen wie Knoten zweiter Ebene aus. Kürzel, Kontextmenü, Verknüpfungen und Zusammenfassung funktionieren wie gewohnt. Notizen unterstützen ebenfalls Bearbeitung, Löschen, Verknüpfungen und Tab.</li>
<li>Knoten können gezogen werden. Über das Kontextmenü lassen sich Knoten hinzufügen, verknüpfen, verschieben und gruppieren; die integrierte Werkzeugleiste steuert Zoom und Zentrierung.</li>
<li>Die Schaltfläche für den Fokusmodus in der unteren Werkzeugleiste zeigt den ausgewählten Zweig der ersten Ebene separat an. Ein erneuter Klick kehrt zur Gesamtkarte zurück.</li>
<li>Das Suchsymbol oder Strg+F (Command+F unter macOS) durchsucht normale und freie Knoten sowie Notizen. Wählen Sie ein Ergebnis, um den Zweig zu öffnen, das Element auszuwählen und es in der Karte zu zentrieren.</li>
<li>Änderungen werden automatisch mit den Projektdaten gespeichert. Auch die Schaltfläche „Speichern“ und das Schließen des Fensters sichern den aktuellen Stand der Karte.</li>
<li>Die Schaltfläche „Exportieren“ speichert die aktuelle Karte als PNG, SVG oder JSON. PNG und SVG eignen sich zum Anzeigen und Teilen, während JSON die bearbeitbare Kartenstruktur speichert.</li>
<li>Im Bearbeitungsfenster eines Etappenprojekts können Sie „Etappenkarten zusammenführen“ aktivieren. Jede Etappe erscheint dann in der Gesamtkarte als eigener Zweig der ersten Ebene unter ihrem aktuellen Namen.</li>
<li>Der Inhalt der Zweige wird in beide Richtungen synchronisiert: Änderungen in der Gesamtkarte werden in den einzelnen Etappenkarten gespeichert, und Änderungen an einer einzelnen Karte erscheinen beim nächsten Öffnen der Gesamtkarte. Projekteigene Knoten bleiben erhalten.</li>
<li>Das Umbenennen, Hinzufügen, Löschen und Neuanordnen von Etappen wird automatisch in der Gesamtkarte berücksichtigt. Wenn die Zusammenführung deaktiviert wird, werden nur die erzeugten Zweige ausgeblendet; die Etappenkarten werden nicht gelöscht.</li>
<li>Eine abgeschlossene Etappe wird in der Gesamtkarte mit ✅ gekennzeichnet. Ihre vorhandene Karte und ihr Zweig in der Gesamtkarte sind schreibgeschützt. Wenn keine Etappenkarte erstellt wurde, zeigt die Schaltfläche „Karte“ eine Meldung an; in der Gesamtkarte erscheint derselbe Hinweis unten im Statusbereich und nicht als eigener Knoten. Die Karte eines abgeschlossenen Projekts ist ebenfalls schreibgeschützt.</li>
<li>Beim Löschen eines Projekts oder einer Etappe wird auch die zugehörige Karte gelöscht. Wird ein Etappenprojekt in ein normales Projekt umgewandelt, werden die Karten der entfernten Etappen nicht mit der übergeordneten Karte zusammengeführt.</li>
</ul>
<p>Der Editor und seine Ressourcen sind in der Anwendung enthalten; für die Nutzung der Karte ist daher keine Internetverbindung erforderlich.</p>
</body></html>""",
        "Редактор карты": "Karteneditor",
        "Выберите узел: Tab — дочерний, Enter — соседний, F2 — изменить, Delete — удалить. Карта сохраняется автоматически.": "Wählen Sie einen Knoten: Tab — untergeordnet, Eingabetaste — gleichgeordnet, F2 — bearbeiten, Entf — löschen. Die Karte wird automatisch gespeichert.",
        "Новая тема": "Neues Thema",
        "Завершённый проект или этап: карта доступна только для просмотра.": "Abgeschlossenes Projekt oder abgeschlossene Etappe: Die Karte ist schreibgeschützt.",
        "Карта доступна только для просмотра.": "Die Karte ist schreibgeschützt.",
        "Карта не была создана при работе над этапом.": "Die Karte wurde während der Arbeit an der Etappe nicht erstellt.",
        "Карта готова.": "Die Karte ist bereit.",
        "Есть несохранённые изменения.": "Es gibt ungespeicherte Änderungen.",
        "Все изменения сохранены.": "Alle Änderungen sind gespeichert.",
        "Загрузка карты…": "Karte wird geladen…",
        "Сохранение карты…": "Karte wird gespeichert…",
        "Сохранить карту": "Karte speichern",
        "Закрыть карту": "Karte schließen",
        "Не удалось загрузить редактор карты.": "Der Karteneditor konnte nicht geladen werden.",
        "Не найдены файлы редактора карты.": "Die Dateien des Karteneditors wurden nicht gefunden.",
        "Не удалось получить данные карты.": "Die Kartendaten konnten nicht abgerufen werden.",
        "Не удалось сохранить карту.": "Die Karte konnte nicht gespeichert werden.",
        "Редактор вернул повреждённые данные карты.": "Der Editor hat ungültige Kartendaten zurückgegeben.",
        "Не удалось сохранить карту. Закрыть окно без сохранения?": "Die Karte konnte nicht gespeichert werden. Fenster ohne Speichern schließen?",
        "Этап больше не существует.": "Die Etappe existiert nicht mehr.",
        "Проект больше не существует.": "Das Projekt existiert nicht mehr.",
        "Все записи этапов будут перенесены в проект в хронологическом порядке. Цели и прогресс этапов сложатся и будут пересчитаны как записи одного проекта. Карты этапов не объединяются с картой проекта и будут удалены.": "Alle Etappeneinträge werden in chronologischer Reihenfolge in das Projekt übernommen. Ziele und Fortschritt der Etappen werden zusammengeführt und als Einträge eines Projekts neu berechnet. Etappenkarten werden nicht mit der Projektkarte zusammengeführt und gelöscht.",
        "Кабинет, реликвии и комплекты": "Kabinett, Relikte und Sets",
        "Предметы творческого ритма": "Gegenstände des kreativen Rhythmus",
        "Параметры и умения": "Parameter und Fertigkeiten",
        "Специализации и мастерство": "Spezialisierungen und Meisterschaft",
        "Изменение и статусы": "Bearbeiten und Status",
        "Игровая цель дня": "Tägliche Spielherausforderung",
        "Поиск по справке…": "Hilfe durchsuchen…",
        "Поиск не дал результатов": "Die Suche ergab keine Treffer",
        "Творческий импульс": "Kreativer Impuls",
        "Искра сессии": "Sitzungsfunke",
        "Фокус испытания": "Herausforderungsfokus",
        "Длинное дыхание": "Langer Atem",
        "Сила ритуала": "Kraft des Rituals",
        "Рывок к финалу": "Endspurt",
        "Новый маршрут": "Neue Route",
        "Точный взгляд": "Scharfer Blick",
        "Инвентарь и кабинет": "Inventar und Kabinett",
        "Надёжный выбор": "Sichere Wahl",
        "Рискнуть": "Risiko eingehen",
        "Решить событие": "Ereignis lösen",
        "Надёжный выбор даёт гарантированную награду события без риска.": "Die sichere Wahl gewährt die garantierte Ereignisbelohnung ohne Risiko.",
        "Рискнуть — попытаться получить повышенную награду с возможностью неудачи.": "Beim Risiko besteht die Chance auf eine höhere Belohnung, aber auch die Möglichkeit zu scheitern.",
        "Применяет выбранный вариант к ожидающему творческому событию.": "Wendet die gewählte Option auf das ausstehende kreative Ereignis an.",
        "Решить событие выбранным способом": "Ereignis mit der gewählten Option lösen",
        "Умение восстанавливается.": "Die Fähigkeit lädt sich wieder auf.",
        "Спринт": "Sprint",
        "Поток": "Flow",
        "Глубокая работа": "Tiefenarbeit",
        "Редакторский проход": "Überarbeitungsdurchgang",
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
        "Марафонец": "Marathonien",
        "Ритуалист": "Ritualiste",
        "Финишер": "Finisseur",
        "Исследователь": "Explorateur",
        "Редактор": "Réviseur",
        "Смена будет доступна через {0} дн.": "La spécialisation pourra être changée dans {0} jours.",
        "Искра замысла": "Étincelle d’une idée",
        "Переломная точка": "Tournant",
        "следующий рубеж": "prochain jalon",
        "Путь этапа": "Parcours de l’étape",
        "Карта": "Carte",
        "Карта проекта или этапа": "Carte du projet ou de l’étape",
        "Карты проектов и этапов": "Cartes des projets et des étapes",
        "Объединять карты этапов в карте проекта": "Regrouper les cartes des étapes",
        MINDMAP_HELP_SOURCE: """<html><body>
<h2>Cartes des projets et des étapes</h2>
<p>Chaque projet et chaque étape possède sa propre carte d’idées indépendante. Sélectionnez le projet ou l’étape dans l’onglet « Projets », puis cliquez sur « Carte » dans le panneau d’actions. L’éditeur s’ouvre dans une fenêtre séparée ; lors de la première ouverture, le nœud racine reçoit le nom du projet ou de l’étape.</p>
<ul>
<li>Double-cliquez sur un nœud ou appuyez sur F2 pour modifier son texte. Tab ajoute un nœud enfant, Entrée ajoute un nœud voisin et Suppr efface le nœud sélectionné.</li>
<li>« Nœud libre » crée un nœud de premier niveau hors de la disposition automatique ; ses enfants ressemblent aux nœuds de second niveau. Les raccourcis, le menu contextuel, les liens et le résumé fonctionnent normalement. Les notes acceptent aussi édition, suppression, liens et Tab.</li>
<li>Les nœuds peuvent être déplacés. Le menu contextuel permet d’ajouter, de relier, de déplacer et de regrouper les nœuds, tandis que la barre intégrée contrôle le zoom et le centrage.</li>
<li>Le bouton du mode focus dans la barre inférieure affiche séparément la branche de premier niveau sélectionnée. Appuyez à nouveau dessus pour revenir à la carte globale.</li>
<li>L’icône de recherche ou Ctrl+F (Command+F sous macOS) recherche les nœuds ordinaires et libres ainsi que les notes. Choisissez un résultat pour développer sa branche, sélectionner l’élément et le centrer dans la carte.</li>
<li>Les modifications sont enregistrées automatiquement avec les données du projet. Le bouton « Enregistrer » et la fermeture de la fenêtre sauvegardent également l’état actuel de la carte.</li>
<li>Le bouton Exporter enregistre la carte actuelle au format PNG, SVG ou JSON. PNG et SVG conviennent à la visualisation et au partage, tandis que JSON stocke la structure de la carte modifiable.</li>
<li>Dans la fenêtre de modification d’un projet à étapes, vous pouvez activer « Regrouper les cartes des étapes ». Chaque étape apparaît alors dans la carte globale sous la forme d’une branche distincte de premier niveau portant son nom actuel.</li>
<li>Le contenu des branches est synchronisé dans les deux sens : les modifications de la carte globale sont enregistrées dans les cartes individuelles des étapes, et celles d’une carte individuelle apparaissent à la prochaine ouverture de la carte globale. Les nœuds propres au projet sont conservés.</li>
<li>Le renommage, l’ajout, la suppression et la réorganisation des étapes sont automatiquement répercutés dans la carte globale. La désactivation du regroupement masque uniquement les branches générées et ne supprime pas les cartes des étapes.</li>
<li>Une étape terminée est signalée par ✅ dans la carte globale. Sa carte existante et sa branche dans la carte globale sont en lecture seule. Si aucune carte n’a été créée pour l’étape, le bouton « Carte » affiche un message et la carte globale présente la même explication dans la zone d’état inférieure, et non sous forme de nœud distinct. La carte d’un projet terminé est également en lecture seule.</li>
<li>La suppression d’un projet ou d’une étape supprime aussi sa carte. Lorsqu’un projet à étapes est converti en projet standard, les cartes des étapes supprimées ne sont pas fusionnées avec la carte parente.</li>
</ul>
<p>L’éditeur et ses ressources sont intégrés à l’application ; aucune connexion à internet n’est donc nécessaire pour utiliser la carte.</p>
</body></html>""",
        "Редактор карты": "Éditeur de cartes",
        "Выберите узел: Tab — дочерний, Enter — соседний, F2 — изменить, Delete — удалить. Карта сохраняется автоматически.": "Sélectionnez un nœud : Tab — enfant, Entrée — voisin, F2 — modifier, Suppr — supprimer. La carte est enregistrée automatiquement.",
        "Новая тема": "Nouveau sujet",
        "Завершённый проект или этап: карта доступна только для просмотра.": "Projet ou étape terminé : la carte est en lecture seule.",
        "Карта доступна только для просмотра.": "La carte est en lecture seule.",
        "Карта не была создана при работе над этапом.": "La carte n’a pas été créée pendant le travail sur l’étape.",
        "Карта готова.": "La carte est prête.",
        "Есть несохранённые изменения.": "Des modifications ne sont pas enregistrées.",
        "Все изменения сохранены.": "Toutes les modifications sont enregistrées.",
        "Загрузка карты…": "Chargement de la carte…",
        "Сохранение карты…": "Enregistrement de la carte…",
        "Сохранить карту": "Enregistrer la carte",
        "Закрыть карту": "Fermer la carte",
        "Не удалось загрузить редактор карты.": "Impossible de charger l’éditeur de cartes.",
        "Не найдены файлы редактора карты.": "Les fichiers de l’éditeur de cartes sont introuvables.",
        "Не удалось получить данные карты.": "Impossible de récupérer les données de la carte.",
        "Не удалось сохранить карту.": "Impossible d’enregistrer la carte.",
        "Редактор вернул повреждённые данные карты.": "L’éditeur a renvoyé des données de carte non valides.",
        "Не удалось сохранить карту. Закрыть окно без сохранения?": "Impossible d’enregistrer la carte. Fermer la fenêtre sans enregistrer ?",
        "Этап больше не существует.": "L’étape n’existe plus.",
        "Проект больше не существует.": "Le projet n’existe plus.",
        "Все записи этапов будут перенесены в проект в хронологическом порядке. Цели и прогресс этапов сложатся и будут пересчитаны как записи одного проекта. Карты этапов не объединяются с картой проекта и будут удалены.": "Toutes les entrées des étapes seront transférées au projet dans l’ordre chronologique. Les objectifs et la progression des étapes seront regroupés et recalculés comme les entrées d’un seul projet. Les cartes des étapes ne sont pas fusionnées avec la carte du projet et seront supprimées.",
        "Кабинет, реликвии и комплекты": "Cabinet, reliques et ensembles",
        "Предметы творческого ритма": "Objets du rythme créatif",
        "Параметры и умения": "Paramètres et compétences",
        "Специализации и мастерство": "Spécialisations et maîtrise",
        "Изменение и статусы": "Modification et statuts",
        "Игровая цель дня": "Défi quotidien du jeu",
        "Поиск по справке…": "Rechercher dans l’aide…",
        "Поиск не дал результатов": "La recherche n’a donné aucun résultat",
        "Творческий импульс": "Élan créatif",
        "Искра сессии": "Étincelle de session",
        "Фокус испытания": "Concentration du défi",
        "Длинное дыхание": "Souffle long",
        "Сила ритуала": "Puissance du rituel",
        "Рывок к финалу": "Sprint final",
        "Новый маршрут": "Nouvel itinéraire",
        "Точный взгляд": "Regard précis",
        "Инвентарь и кабинет": "Inventaire et cabinet",
        "Надёжный выбор": "Choix sûr",
        "Рискнуть": "Prendre un risque",
        "Решить событие": "Résoudre l’événement",
        "Надёжный выбор даёт гарантированную награду события без риска.": "Le choix sûr accorde la récompense garantie de l’événement sans risque.",
        "Рискнуть — попытаться получить повышенную награду с возможностью неудачи.": "Prendre un risque permet de tenter d’obtenir une meilleure récompense, avec une possibilité d’échec.",
        "Применяет выбранный вариант к ожидающему творческому событию.": "Applique l’option choisie à l’événement créatif en attente.",
        "Решить событие выбранным способом": "Résoudre l’événement avec l’option choisie",
        "Умение восстанавливается.": "La capacité se recharge.",
        "Спринт": "Sprint",
        "Поток": "Flux",
        "Глубокая работа": "Travail profond",
        "Редакторский проход": "Passe de révision",
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
        "Марафонец": "Maratonista",
        "Ритуалист": "Ritualista",
        "Финишер": "Finalizador",
        "Исследователь": "Explorador",
        "Редактор": "Editor",
        "Смена будет доступна через {0} дн.": "A especialização poderá ser alterada em {0} dias.",
        "Искра замысла": "Centelha de uma ideia",
        "Переломная точка": "Ponto de virada",
        "следующий рубеж": "próximo marco",
        "Путь этапа": "Caminho da etapa",
        "Карта": "Mapa",
        "Карта проекта или этапа": "Mapa do projeto ou da etapa",
        "Карты проектов и этапов": "Mapas de projetos e etapas",
        "Объединять карты этапов в карте проекта": "Combinar mapas das etapas",
        MINDMAP_HELP_SOURCE: """<html><body>
<h2>Mapas de projetos e etapas</h2>
<p>Cada projeto e cada etapa possui seu próprio mapa de ideias independente. Selecione o projeto ou a etapa na aba “Projetos” e clique em “Mapa” no painel de ações. O editor abre em uma janela separada; na primeira abertura, o nó raiz recebe o nome do projeto ou da etapa.</p>
<ul>
<li>Clique duas vezes em um nó ou pressione F2 para editar o texto. Tab adiciona um nó filho, Enter adiciona um nó irmão e Delete exclui o nó selecionado.</li>
<li>“Nó livre” cria um nó de primeiro nível fora do layout automático; seus filhos parecem nós de segundo nível. Atalhos, menu de contexto, links e Resumo funcionam normalmente. As notas também aceitam edição, exclusão, links e Tab.</li>
<li>Os nós podem ser arrastados. O menu de contexto permite adicionar, vincular, mover e agrupar nós, enquanto a barra integrada controla o zoom e a centralização.</li>
<li>O botão do modo de foco na barra inferior exibe separadamente a ramificação de primeiro nível selecionada. Pressione-o novamente para voltar ao mapa combinado.</li>
<li>O ícone de pesquisa ou Ctrl+F (Command+F no macOS) pesquisa nós regulares e livres, além de notas. Selecione um resultado para expandir a ramificação, selecionar o item e centralizá-lo no mapa.</li>
<li>As alterações são salvas automaticamente com os dados do projeto. O botão “Salvar” e o fechamento da janela também armazenam o estado atual do mapa.</li>
<li>O botão Exportar salva o mapa atual como PNG, SVG ou JSON. PNG e SVG são adequados para visualização e compartilhamento, enquanto JSON armazena a estrutura editável do mapa.</li>
<li>Na janela de edição de um projeto com etapas, você pode ativar “Combinar mapas das etapas”. Cada etapa será exibida no mapa combinado como uma ramificação separada de primeiro nível com seu nome atual.</li>
<li>O conteúdo das ramificações é sincronizado nos dois sentidos: as alterações no mapa combinado são salvas nos mapas individuais das etapas, e as alterações em um mapa individual aparecem na próxima vez que o mapa combinado for aberto. Os nós próprios do projeto são preservados.</li>
<li>Renomear, adicionar, excluir e reordenar etapas é refletido automaticamente no mapa combinado. Desativar a combinação apenas oculta as ramificações geradas e não exclui os mapas das etapas.</li>
<li>Uma etapa concluída é marcada com ✅ no mapa combinado. O mapa existente e a ramificação dessa etapa no mapa combinado são somente leitura. Se nenhum mapa da etapa tiver sido criado, o botão “Mapa” exibirá uma mensagem e o mapa combinado mostrará a mesma explicação na área de status inferior, não como um nó separado. O mapa de um projeto concluído também é somente leitura.</li>
<li>Ao excluir um projeto ou uma etapa, seu mapa também é excluído. Ao converter um projeto com etapas em um projeto normal, os mapas das etapas removidas não são mesclados com o mapa principal.</li>
</ul>
<p>O editor e seus recursos estão incluídos no aplicativo, portanto não é necessária uma conexão com a internet para usar o mapa.</p>
</body></html>""",
        "Редактор карты": "Editor de mapas",
        "Выберите узел: Tab — дочерний, Enter — соседний, F2 — изменить, Delete — удалить. Карта сохраняется автоматически.": "Selecione um nó: Tab — filho, Enter — irmão, F2 — editar, Delete — excluir. O mapa é salvo automaticamente.",
        "Новая тема": "Novo tópico",
        "Завершённый проект или этап: карта доступна только для просмотра.": "Projeto ou etapa concluído: o mapa é somente leitura.",
        "Карта доступна только для просмотра.": "O mapa é somente leitura.",
        "Карта не была создана при работе над этапом.": "O mapa não foi criado durante o trabalho na etapa.",
        "Карта готова.": "O mapa está pronto.",
        "Есть несохранённые изменения.": "Há alterações não salvas.",
        "Все изменения сохранены.": "Todas as alterações foram salvas.",
        "Загрузка карты…": "Carregando mapa…",
        "Сохранение карты…": "Salvando mapa…",
        "Сохранить карту": "Salvar mapa",
        "Закрыть карту": "Fechar mapa",
        "Не удалось загрузить редактор карты.": "Não foi possível carregar o editor de mapas.",
        "Не найдены файлы редактора карты.": "Os arquivos do editor de mapas não foram encontrados.",
        "Не удалось получить данные карты.": "Não foi possível obter os dados do mapa.",
        "Не удалось сохранить карту.": "Não foi possível salvar o mapa.",
        "Редактор вернул повреждённые данные карты.": "O editor retornou dados de mapa inválidos.",
        "Не удалось сохранить карту. Закрыть окно без сохранения?": "Não foi possível salvar o mapa. Fechar a janela sem salvar?",
        "Этап больше не существует.": "A etapa não existe mais.",
        "Проект больше не существует.": "O projeto não existe mais.",
        "Все записи этапов будут перенесены в проект в хронологическом порядке. Цели и прогресс этапов сложатся и будут пересчитаны как записи одного проекта. Карты этапов не объединяются с картой проекта и будут удалены.": "Todos os registros das etapas serão movidos para o projeto em ordem cronológica. Os objetivos e o progresso das etapas serão combinados e recalculados como registros de um único projeto. Os mapas das etapas não são mesclados com o mapa do projeto e serão excluídos.",
        "Кабинет, реликвии и комплекты": "Gabinete, relíquias e conjuntos",
        "Предметы творческого ритма": "Itens do ritmo criativo",
        "Параметры и умения": "Parâmetros e habilidades",
        "Специализации и мастерство": "Especializações e maestria",
        "Изменение и статусы": "Edição e status",
        "Игровая цель дня": "Desafio diário do jogo",
        "Поиск по справке…": "Pesquisar na ajuda…",
        "Поиск не дал результатов": "A pesquisa não encontrou resultados",
        "Творческий импульс": "Impulso criativo",
        "Искра сессии": "Centelha da sessão",
        "Фокус испытания": "Foco no desafio",
        "Ранг": "Grau",
        "Длинное дыхание": "Fôlego longo",
        "Сила ритуала": "Poder do ritual",
        "Рывок к финалу": "Arrancada final",
        "Новый маршрут": "Nova rota",
        "Точный взгляд": "Olhar preciso",
        "Инвентарь и кабинет": "Inventário e gabinete",
        "Надёжный выбор": "Escolha segura",
        "Рискнуть": "Arriscar",
        "Решить событие": "Resolver evento",
        "Надёжный выбор даёт гарантированную награду события без риска.": "A escolha segura concede a recompensa garantida do evento sem risco.",
        "Рискнуть — попытаться получить повышенную награду с возможностью неудачи.": "Arriscar permite tentar obter uma recompensa maior, com possibilidade de fracasso.",
        "Применяет выбранный вариант к ожидающему творческому событию.": "Aplica a opção escolhida ao evento criativo pendente.",
        "Решить событие выбранным способом": "Resolver o evento com a opção escolhida",
        "Умение восстанавливается.": "A habilidade está recarregando.",
        "Спринт": "Sprint",
        "Поток": "Fluxo",
        "Глубокая работа": "Trabalho profundo",
        "Редакторский проход": "Passe de revisão",
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
    language_catalog = dict(TRANSLATIONS.get(language, {}))
    language_catalog.update(TRANSLATION_OVERRIDES.get(language, {}))
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
