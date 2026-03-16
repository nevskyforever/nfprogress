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
            print(f"Найдена папка с документами: {docs_folder}")
            break

    if docs_folder is None:
        print(f"Папка с документами не найдена в {project_path}")
        return 0

    # Очищаем item_id от возможных фигурных скобок и приводим к нижнему регистру для сравнения
    clean_id = item_id.strip('{}').lower()
    print(f"Ищем папку для item_id {clean_id} в {docs_folder}")

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
        print(f"Папка с UUID {clean_id} не найдена")
        # Для отладки выведем несколько первых папок
        print("Первые 5 подпапок в", docs_folder)
        for i, d in enumerate(list(docs_folder.iterdir())[:5]):
            if d.is_dir():
                print(f"  {d.name}")
        return 0

    print(f"Найдена папка: {target_dir}")

    # Ищем внутри папки RTF-файл (обычно Data.rtf)
    rtf_files = list(target_dir.glob("*.rtf")) + list(target_dir.glob("*.RTF"))
    if not rtf_files:
        print(f"В папке {target_dir} нет RTF-файлов")
        return 0

    # Пробуем прочитать первый RTF
    for rtf_path in rtf_files:
        try:
            print(f"Пробуем прочитать: {rtf_path}")
            # Пробуем разные кодировки
            for enc in ['utf-8', 'cp1251', 'latin-1', 'mac-roman']:
                try:
                    with open(rtf_path, 'r', encoding=enc, errors='ignore') as f:
                        rtf_content = f.read()
                    text = rtf_to_text(rtf_content)
                    count = len(text)
                    print(f"Успешно прочитано {count} символов (кодировка {enc})")
                    return count
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    print(f"Ошибка при декодировании {enc}: {e}")
                    continue

            # Бинарный режим
            with open(rtf_path, 'rb') as f:
                rtf_content = f.read().decode('utf-8', errors='ignore')
            text = rtf_to_text(rtf_content)
            count = len(text)
            print(f"Успешно прочитано {count} символов (бинарный)")
            return count

        except Exception as e:
            print(f"Ошибка чтения {rtf_path}: {e}")
            continue

    print("Не удалось прочитать RTF")
    return 0