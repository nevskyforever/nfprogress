"""Safe, tree-only importer for XMind files."""

from __future__ import annotations

import json
import uuid
import zipfile
from dataclasses import dataclass
from io import BytesIO
from typing import Any
from xml.etree import ElementTree

from ..errors import ValidationError


MAX_ARCHIVE_SIZE = 50 * 1024 * 1024
MAX_CONTENT_SIZE = 10 * 1024 * 1024


@dataclass(frozen=True)
class XMindTopic:
    title: str
    children: tuple['XMindTopic', ...] = ()


@dataclass(frozen=True)
class XMindSheet:
    title: str
    root: XMindTopic


def _error(message: str) -> ValidationError:
    return ValidationError('invalid_xmind', message)


def _title(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _error(f'В XMind отсутствует название {context}.')
    return value.strip()


def _json_children(value: Any, context: str) -> tuple[XMindTopic, ...]:
    if value is None:
        return ()
    if not isinstance(value, dict):
        raise _error(f'Некорректные дочерние узлы: {context}.')
    attached = value.get('attached', [])
    if not isinstance(attached, list):
        raise _error(f'Некорректные дочерние узлы: {context}.')
    return tuple(_json_topic(item, f'{context}[{index}]') for index, item in enumerate(attached))


def _json_topic(value: Any, context: str) -> XMindTopic:
    if not isinstance(value, dict):
        raise _error(f'Некорректная тема: {context}.')
    return XMindTopic(
        _title(value.get('title'), f'темы {context}'),
        _json_children(value.get('children'), context),
    )


def _parse_json(raw: bytes) -> list[XMindSheet]:
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _error('content.json содержит некорректный JSON.') from error
    if not isinstance(payload, list) or not payload:
        raise _error('В content.json не найдено ни одного листа.')
    sheets: list[XMindSheet] = []
    for index, sheet in enumerate(payload):
        if not isinstance(sheet, dict):
            raise _error(f'Некорректный лист XMind: {index}.')
        root = sheet.get('rootTopic')
        if root is None:
            raise _error(f'В листе {index} отсутствует root topic.')
        topic = _json_topic(root, f'листа {index}')
        sheets.append(XMindSheet(_title(sheet.get('title') or topic.title, f'листа {index}'), topic))
    return sheets


def _local_name(element: ElementTree.Element) -> str:
    return element.tag.rsplit('}', 1)[-1]


def _xml_topic(element: ElementTree.Element, context: str) -> XMindTopic:
    title_element = next((child for child in element if _local_name(child) == 'title'), None)
    title = _title(''.join(title_element.itertext()) if title_element is not None else None, f'темы {context}')
    children: list[XMindTopic] = []
    children_element = next((child for child in element if _local_name(child) == 'children'), None)
    if children_element is not None:
        groups = [child for child in children_element if _local_name(child) == 'topics']
        attached = next((group for group in groups if group.attrib.get('type') == 'attached'), None)
        if attached is not None:
            for index, child in enumerate(attached):
                if _local_name(child) == 'topic':
                    children.append(_xml_topic(child, f'{context}[{index}]'))
    return XMindTopic(title, tuple(children))


def _parse_xml(raw: bytes) -> list[XMindSheet]:
    # ElementTree does not fetch network entities, but reject DTDs/entities
    # explicitly as an additional guard against hostile XML payloads.
    lowered = raw.lower()
    if b'<!doctype' in lowered or b'<!entity' in lowered:
        raise _error('content.xml содержит запрещённые XML-сущности.')
    try:
        root = ElementTree.fromstring(raw)
    except (ElementTree.ParseError, UnicodeDecodeError) as error:
        raise _error('content.xml содержит некорректный XML.') from error
    sheets: list[XMindSheet] = []
    for index, sheet in enumerate(element for element in root.iter() if _local_name(element) == 'sheet'):
        topic = next((child for child in sheet if _local_name(child) == 'topic'), None)
        if topic is None:
            raise _error(f'В листе {index} отсутствует корневая тема.')
        topic_data = _xml_topic(topic, f'листа {index}')
        sheet_title = sheet.attrib.get('title') or ''.join(
            text for child in sheet if _local_name(child) == 'title'
            for text in child.itertext()
        )
        sheets.append(XMindSheet(_title(sheet_title or topic_data.title, f'листа {index}'), topic_data))
    if not sheets:
        raise _error('В content.xml не найдено ни одного листа.')
    return sheets


def _read_content(file_bytes: bytes, name: str) -> tuple[str, bytes]:
    if len(file_bytes) > MAX_ARCHIVE_SIZE:
        raise _error('Файл XMind слишком большой.')
    try:
        archive = zipfile.ZipFile(BytesIO(file_bytes))
    except (zipfile.BadZipFile, OSError) as error:
        raise _error('Файл XMind повреждён или не является ZIP-контейнером.') from error
    with archive:
        names = set(archive.namelist())
        for content_name in ('content.json', 'content.xml'):
            info = archive.getinfo(content_name) if content_name in names else None
            if info is not None:
                if info.file_size > MAX_CONTENT_SIZE:
                    raise _error('Структура XMind слишком большая.')
                try:
                    return content_name, archive.read(info)
                except (OSError, RuntimeError, zipfile.BadZipFile) as error:
                    raise _error(f'Не удалось прочитать {content_name}.') from error
    raise _error('В XMind отсутствует content.json или content.xml.')


def _to_mind_elixir(topic: XMindTopic) -> dict[str, Any]:
    return {
        'id': f'xmind-{uuid.uuid4().hex}',
        'topic': topic.title,
        'children': [_to_mind_elixir(child) for child in topic.children],
    }


def import_xmind(file_bytes: bytes, filename: str = '') -> list[dict[str, Any]]:
    """Parse an XMind archive and return sheets as fresh Mind Elixir maps."""
    content_name, raw = _read_content(file_bytes, filename)
    sheets = _parse_json(raw) if content_name.endswith('.json') else _parse_xml(raw)
    return [
        {
            'title': sheet.title,
            'data': {'nodeData': _to_mind_elixir(sheet.root)},
        }
        for sheet in sheets
    ]


__all__ = ['import_xmind', 'MAX_ARCHIVE_SIZE', 'MAX_CONTENT_SIZE']
