import os
import xml.etree.ElementTree as ET
from pathlib import Path

from striprtf.striprtf import rtf_to_text


def find_scrivener_xml(project_path):
    """
    Ищет файл .scrivx внутри папки проекта Scrivener.
    Возвращает полный путь к XML-файлу или None.
    """
    project_path = Path(project_path)

    # Стандартное имя
    xml_path = project_path / 'project.scrivx'
    if xml_path.exists():
        return str(xml_path)

    # Ищем любой .scrivx файл в корне
    for item in project_path.iterdir():
        if item.suffix == '.scrivx':
            return str(item)

    # Старая версия
    old_xml = project_path / 'binder.scrivproj'
    if old_xml.exists():
        return str(old_xml)

    return None


def parse_scrivener_items(xml_path):
    """
    Парсит XML и возвращает список элементов в виде вложенных словарей:
    [{'id': str, 'title': str, 'children': [...]}]
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Поиск корневого элемента Binder (разные версии)
    binder = root.find('.//Binder')
    if binder is None:
        binder = root.find('.//root')  # альтернативный корень

    if binder is None:
        return []

    # Рекурсивный парсинг элементов
    def parse_element(elem):
        # Получаем ID (разные варианты атрибута)
        item_id = (elem.get('UUID') or elem.get('Uuid') or
                   elem.get('uuid') or elem.get('ID'))
        if not item_id:
            return None

        title_elem = elem.find('Title')
        title = title_elem.text if title_elem is not None else 'Без названия'

        # Ищем дочерние элементы
        children = []
        # В разных версиях дети могут быть в <Children> или <SubDocuments>
        children_container = elem.find('Children')
        if children_container is None:
            children_container = elem.find('SubDocuments')
        if children_container is not None:
            for child in children_container.findall('BinderItem'):
                parsed = parse_element(child)
                if parsed:
                    children.append(parsed)

        return {
            'id': item_id,
            'title': title,
            'children': children
        }

    items = []
    for binder_item in binder.findall('BinderItem'):
        parsed = parse_element(binder_item)
        if parsed:
            items.append(parsed)

    return items


def find_scrivener_item_files(project_path, item_id):
    """Return the RTF files backing a Binder item in deterministic order.

    Scrivener projects encountered by nfprogress use either ``Files/Docs`` or
    ``Files/Data``.  Keeping this lookup separate lets callers distinguish an
    intentionally empty RTF from a stale Binder link whose content directory
    has disappeared.
    """
    project_path = Path(project_path)
    docs_folder = next((
        folder
        for folder in (
            project_path / 'Files' / 'Docs',
            project_path / 'Files' / 'Data',
        )
        if folder.exists()
    ), None)
    if docs_folder is None:
        return []

    clean_id = str(item_id).strip('{}').lower()
    target_dir = None
    for root, dirs, _files in os.walk(docs_folder):
        for directory in dirs:
            if directory.lower() == clean_id:
                target_dir = Path(root) / directory
                break
        if target_dir is not None:
            break
    if target_dir is None:
        return []

    rtf_files = [
        path for path in target_dir.iterdir()
        if path.is_file() and path.suffix.lower() == '.rtf'
    ]
    return sorted(rtf_files, key=lambda path: path.name.casefold())


def read_symbols_from_scrivener_item(project_path, item_id):
    """Count one Binder item's symbols and raise when its RTF is unreadable."""
    rtf_files = find_scrivener_item_files(project_path, item_id)
    if not rtf_files:
        raise FileNotFoundError('Scrivener item content is missing')

    last_error = None
    for rtf_path in rtf_files:
        try:
            # Пробуем разные кодировки
            for enc in ['utf-8', 'cp1251', 'latin-1', 'mac-roman']:
                try:
                    with open(rtf_path, 'r', encoding=enc, errors='ignore') as f:
                        rtf_content = f.read()
                    text = rtf_to_text(rtf_content)
                    return len(text)
                except UnicodeDecodeError:
                    continue
                except Exception as error:
                    last_error = error
                    continue

            # Бинарный режим
            with open(rtf_path, 'rb') as f:
                rtf_content = f.read().decode('utf-8', errors='ignore')
            text = rtf_to_text(rtf_content)
            return len(text)

        except Exception as error:
            last_error = error
            continue

    raise ValueError('Scrivener item content is unreadable') from last_error


def count_symbols_in_scrivener_item(project_path, item_id):
    """
    Подсчитывает количество символов в документе Scrivener по его UUID.
    Ищет папку с именем, равным UUID, внутри Files/Data или Files/Docs,
    а внутри неё файл Data.rtf (или любой .rtf).

    Все UI-сообщения (QMessageBox) удалены, чтобы не блокировать фоновую синхронизацию
    и не мешать запуску приложения. Ошибки теперь возвращают 0, а уведомления
    отображаются через NotificationManager в main_UI.py (в _sync_scrivener).
    """
    try:
        return read_symbols_from_scrivener_item(project_path, item_id)
    except (OSError, ValueError):
        return 0
