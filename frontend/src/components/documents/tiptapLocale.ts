/**
 * The kit only ships English and Chinese dictionaries.  It deliberately accepts
 * host-provided dictionaries, so keep UI labels in NFProgress' localisation
 * pipeline rather than leaving an English editor inside a translated app.
 */
export function tiptapLocale(t: (source: string) => string): Record<string, unknown> {
  const toolbar = {
    bold: t('Жирный'), italic: t('Курсив'), underline: t('Подчёркивание'), strikethrough: t('Зачёркнутый'), code: t('Код'), subscript: t('Нижний индекс'), superscript: t('Верхний индекс'), clear: t('Очистить'), clearFormat: t('Очистить форматирование'), formatPainter: t('Копировать формат'), heading: t('Заголовок'), heading1: t('Заголовок 1'), heading2: t('Заголовок 2'), heading3: t('Заголовок 3'), heading4: t('Заголовок 4'), heading5: t('Заголовок 5'), heading6: t('Заголовок 6'), paragraph: t('Обычный текст'), fontFamily: t('Шрифт'), fontDefault: t('По умолчанию'), fontSize: t('Размер текста'), lineHeight: t('Межстрочный интервал'), textColor: t('Цвет текста'), backgroundColor: t('Цвет фона'), highlightColor: t('Выделение'), bulletList: t('Маркированный список'), orderedList: t('Нумерованный список'), taskList: t('Чек-лист'), indent: t('Увеличить отступ'), outdent: t('Уменьшить отступ'), alignLeft: t('По левому краю'), alignCenter: t('По центру'), alignRight: t('По правому краю'), alignJustify: t('По ширине'), insertLink: t('Вставить ссылку'), insertImage: t('Вставить изображение'), insertTable: t('Вставить таблицу'), insertCodeBlock: t('Вставить блок кода'), insertHorizontalRule: t('Вставить разделитель'), link: t('Ссылка'), linkUrl: t('Адрес ссылки'), linkText: t('Текст ссылки'), openLink: t('Открыть ссылку'), editLink: t('Изменить ссылку'), removeLink: t('Удалить ссылку'), undo: t('Отменить'), redo: t('Повторить'), undoDisabledInCollab: t('Недоступно при совместном редактировании'), redoDisabledInCollab: t('Недоступно при совместном редактировании'), more: t('Дополнительно'),
  }
  const editor = {
    bold: t('Жирный'), italic: t('Курсив'), underline: t('Подчёркивание'), strike: t('Зачёркнутый'), inlineCode: t('Код'),
    superscript: t('Верхний индекс'), subscript: t('Нижний индекс'), bulletList: t('Маркированный список'), orderedList: t('Нумерованный список'), taskList: t('Чек-лист'),
    align: t('Выравнивание'), alignLeft: t('По левому краю'), alignCenter: t('По центру'), alignRight: t('По правому краю'), alignJustify: t('По ширине'),
    indent: t('Увеличить отступ'), outdent: t('Уменьшить отступ'), colors: t('Цвета'), textColor: t('Цвет текста'), backgroundColor: t('Цвет фона'),
    undo: t('Отменить'), redo: t('Повторить'), clearFormat: t('Очистить форматирование'), formatPainter: t('Копировать формат'),
    font: t('Шрифт'), fontSize: t('Размер текста'), lineHeight: t('Межстрочный интервал'), insertLink: t('Вставить ссылку'),
    insertImage: t('Вставить изображение'), insertTable: t('Вставить таблицу'), image: t('Изображение'), link: t('Ссылка'),
    editLink: t('Изменить ссылку'), openLink: t('Открыть ссылку'), removeLink: t('Удалить ссылку'), linkPlaceholder: t('Введите адрес ссылки'),
  }
  return {
    'en-US': {
      toolbar,
      editor,
      table: { insertTable: t('Вставить таблицу'), deleteTable: t('Удалить таблицу'), addColumnBefore: t('Добавить столбец слева'), addColumnAfter: t('Добавить столбец справа'), deleteColumn: t('Удалить столбец'), addRowBefore: t('Добавить строку выше'), addRowAfter: t('Добавить строку ниже'), deleteRow: t('Удалить строку'), mergeCells: t('Объединить ячейки'), splitCell: t('Разделить ячейку'), toggleHeaderCell: t('Переключить заголовок ячейки'), toggleHeaderColumn: t('Переключить заголовок столбца'), toggleHeaderRow: t('Переключить заголовок строки'), setCellAttribute: t('Свойства ячейки'), fixTables: t('Исправить таблицу') },
      bubbleMenu: { turnInto: t('Преобразовать в'), textStyle: t('Стиль текста'), color: t('Цвет') },
      dragMenu: { delete: t('Удалить'), duplicate: t('Дублировать'), copy: t('Копировать'), cut: t('Вырезать'), moveUp: t('Переместить выше'), moveDown: t('Переместить ниже') },
      codeBlock: { language: t('Язык'), selectLanguage: t('Выберите язык') },
      stats: { characters: t('Символы'), words: t('Слова'), pages: t('Страницы'), zoom: t('Масштаб'), reset: t('Сбросить'), total: t('Всего') },
      placeholder: { default: t('Начните писать…'), heading: t('Заголовок'), paragraph: t('Обычный текст') },
    },
  }
}
