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
        children_container = (elem.find('Children') or elem.find('SubDocuments'))
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


def count_symbols_in_scrivener_item(project_path, item_id):
    """
    Подсчитывает количество символов в документе Scrivener по его UUID.
    Ищет папку с именем, равным UUID, внутри Files/Data или Files/Docs,
    а внутри неё файл Data.rtf (или любой .rtf).

    Все UI-сообщения (QMessageBox) удалены, чтобы не блокировать фоновую синхронизацию
    и не мешать запуску приложения. Ошибки теперь возвращают 0, а уведомления
    отображаются через NotificationManager в main_UI.py (в _sync_scrivener).
    """
    project_path = Path(project_path)

    # Возможные пути к папкам с документами
    possible_docs_folders = [
        project_path / 'Files' / 'Docs',
        project_path / 'Files' / 'Data',
    ]

    docs_folder = None
    for folder in possible_docs_folders:
        if folder.exists():
            docs_folder = folder
            break

    if docs_folder is None:
        # Папка с документами не найдена — молча возвращаем 0
        # (уведомление покажет _sync_scrivener, если это не фоновая синхронизация)
        return 0

    # Очищаем item_id от возможных фигурных скобок и приводим к нижнему регистру для сравнения
    clean_id = item_id.strip('{}').lower()

    # Рекурсивно ищем папку, имя которой (без учёта регистра) совпадает с clean_id
    target_dir = None
    for root, dirs, files in os.walk(docs_folder):
        for d in dirs:
            if d.lower() == clean_id:
                target_dir = Path(root) / d
                break
        if target_dir:
            break

    if not target_dir:
        # Папка с UUID не найдена — молча возвращаем 0
        return 0

    # Ищем внутри папки RTF-файл (обычно Data.rtf)
    rtf_files = list(target_dir.glob("*.rtf")) + list(target_dir.glob("*.RTF"))
    if not rtf_files:
        # Документ пустой — молча возвращаем 0
        # (в ручном режиме _sync_scrivener покажет предупреждение)
        return 0

    # Пробуем прочитать первый RTF
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
                except Exception:
                    continue

            # Бинарный режим
            with open(rtf_path, 'rb') as f:
                rtf_content = f.read().decode('utf-8', errors='ignore')
            text = rtf_to_text(rtf_content)
            return len(text)

        except Exception:
            # Ошибка чтения конкретного файла — пробуем следующий RTF
            continue

    # Ни один RTF не удалось прочитать
    return 0