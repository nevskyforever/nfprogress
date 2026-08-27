#!/usr/bin/env python3
"""Generate the shared translation catalog for Python, Qt, and Vue clients."""

from __future__ import annotations

import argparse
import ast
import base64
import json
import re
import runpy
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON_SOURCES = (
    "accessibility.py",
    "engine.py",
    "gama_quests.py",
    "game.py",
    "game_UI.py",
    "game_data.py",
    "help_content.py",
    "lottery_dialog.py",
    "localization.py",
    "main_UI.py",
    "mindmap.py",
    "project_notes.py",
    "scrivener_parser.py",
    "update_checker.py",
    "updater_core.py",
    "updater_main.py",
    "UI_fiiles/project_widget.py",
)
QT_FREE_PYTHON_ROOTS = (
    "backend",
    "nfprogress/core",
)
FRONTEND_SOURCE_ROOT = "frontend/src"
FRONTEND_SOURCE_SUFFIXES = frozenset({".js", ".jsx", ".ts", ".tsx", ".vue"})
FRONTEND_IGNORED_DIRECTORIES = frozenset(
    {"generated", "node_modules", "test", "tests"}
)
TARGET_LANGUAGES = ("en", "es", "de", "fr", "pt")
CATALOG_LANGUAGE = {"pt": "pt_BR"}
CYRILLIC = re.compile(r"[А-Яа-яЁё]")
PLACEHOLDER = re.compile(
    r"(?<!\{)\{(?:\d+|[A-Za-z_][A-Za-z0-9_.-]*)\}(?!\})"
)
HTML_TAG = re.compile(r"<!DOCTYPE[^>]*>|</?[A-Za-z][^>]*>", re.IGNORECASE)
SCRIPT_BLOCK = re.compile(r"<script\b[^>]*>(.*?)</script>", re.IGNORECASE | re.DOTALL)
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
TRANSLATION_CALL = re.compile(r"(?<![\w$])(?:t|locale\.translate)\s*\(")
SEPARATOR = "\n[[[NFPROGRESS_7A9C]]]\n"
TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"

try:
    import certifi
except ImportError:
    SSL_CONTEXT = ssl.create_default_context()
else:
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def joined_string_template(node: ast.JoinedStr) -> str:
    parts = []
    expression_index = 0
    for value in node.values:
        if isinstance(value, ast.Constant):
            parts.append(str(value.value))
        else:
            parts.append("{" + str(expression_index) + "}")
            expression_index += 1
    return "".join(parts)


def extract_python_strings(path: Path) -> set[str]:
    strings = set()
    tree = ast.parse(path.read_text(encoding="utf-8"))
    joined_constants = {
        id(value)
        for node in ast.walk(tree)
        if isinstance(node, ast.JoinedStr)
        for value in node.values
        if isinstance(value, ast.Constant)
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            value = joined_string_template(node)
        elif (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in joined_constants
        ):
            value = node.value
        else:
            continue
        if CYRILLIC.search(value) and len(value) <= 3000:
            strings.add(value)
    return strings


def _decode_javascript_string(value: str) -> str:
    """Decode escapes used by ordinary JavaScript and TypeScript strings."""
    decoded = []
    index = 0
    simple_escapes = {
        "b": "\b",
        "f": "\f",
        "n": "\n",
        "r": "\r",
        "t": "\t",
        "v": "\v",
        "0": "\0",
        "\\": "\\",
        "'": "'",
        '"': '"',
        "`": "`",
    }
    while index < len(value):
        character = value[index]
        if character != "\\" or index + 1 >= len(value):
            decoded.append(character)
            index += 1
            continue

        escaped = value[index + 1]
        if escaped in {"\n", "\r"}:
            index += 2
            if escaped == "\r" and index < len(value) and value[index] == "\n":
                index += 1
            continue
        if escaped in simple_escapes:
            decoded.append(simple_escapes[escaped])
            index += 2
            continue
        if escaped == "x" and index + 3 < len(value):
            try:
                decoded.append(chr(int(value[index + 2:index + 4], 16)))
            except ValueError:
                decoded.append(escaped)
                index += 2
            else:
                index += 4
            continue
        if escaped == "u":
            brace_end = (
                value.find("}", index + 3)
                if value[index + 2:index + 3] == "{"
                else -1
            )
            digits = (
                value[index + 3:brace_end]
                if brace_end >= 0
                else value[index + 2:index + 6]
            )
            try:
                decoded.append(chr(int(digits, 16)))
            except (ValueError, OverflowError):
                decoded.append(escaped)
                index += 2
            else:
                index = brace_end + 1 if brace_end >= 0 else index + 6
            continue

        # JavaScript treats an unknown escape as the escaped character.
        decoded.append(escaped)
        index += 2
    return "".join(decoded)


def _javascript_string_at(source: str, start: int) -> tuple[str | None, int]:
    quote = source[start]
    index = start + 1
    raw_value = []
    dynamic_template = False
    while index < len(source):
        character = source[index]
        if character == "\\":
            raw_value.append(character)
            if index + 1 < len(source):
                raw_value.append(source[index + 1])
                index += 2
            else:
                index += 1
            continue
        if character == quote:
            value = (
                None
                if dynamic_template
                else _decode_javascript_string("".join(raw_value))
            )
            return value, index + 1
        if quote == "`" and source.startswith("${", index):
            dynamic_template = True
        raw_value.append(character)
        index += 1
    return None, len(source)


def _static_javascript_strings(source: str) -> set[str]:
    """Return static string literals while ignoring comments and templates."""
    strings = set()
    index = 0
    while index < len(source):
        if source.startswith("//", index):
            newline = source.find("\n", index + 2)
            index = len(source) if newline < 0 else newline + 1
            continue
        if source.startswith("/*", index):
            comment_end = source.find("*/", index + 2)
            index = len(source) if comment_end < 0 else comment_end + 2
            continue
        if source[index] not in {"'", '"', "`"}:
            index += 1
            continue
        value, index = _javascript_string_at(source, index)
        if value is not None and CYRILLIC.search(value) and len(value) <= 3000:
            strings.add(value)
    return strings


def _vue_template_translation_strings(source: str) -> set[str]:
    """Extract literal first arguments from t()/locale.translate() calls."""
    strings = set()
    template_source = SCRIPT_BLOCK.sub("", source)
    template_source = HTML_COMMENT.sub("", template_source)
    for match in TRANSLATION_CALL.finditer(template_source):
        index = match.end()
        while index < len(template_source) and template_source[index].isspace():
            index += 1
        if index >= len(template_source) or template_source[index] not in {
            "'",
            '"',
            "`",
        }:
            continue
        value, _ = _javascript_string_at(template_source, index)
        if value is not None and CYRILLIC.search(value) and len(value) <= 3000:
            strings.add(value)
    return strings


def extract_frontend_strings(path: Path) -> set[str]:
    """Extract canonical literals without evaluating dynamic user values."""
    source = path.read_text(encoding="utf-8")
    if path.suffix == ".vue":
        strings = set()
        for script in SCRIPT_BLOCK.findall(source):
            strings.update(_static_javascript_strings(script))
        strings.update(_vue_template_translation_strings(source))
        return strings
    return _static_javascript_strings(source)


def frontend_source_paths() -> list[Path]:
    source_root = PROJECT_ROOT / FRONTEND_SOURCE_ROOT
    if not source_root.exists():
        return []
    paths = []
    for path in source_root.rglob("*"):
        if not path.is_file() or path.suffix not in FRONTEND_SOURCE_SUFFIXES:
            continue
        relative_parts = path.relative_to(source_root).parts
        if any(part in FRONTEND_IGNORED_DIRECTORIES for part in relative_parts):
            continue
        if ".spec." in path.name or ".test." in path.name:
            continue
        paths.append(path)
    return sorted(paths)


def frontend_source_strings() -> list[str]:
    strings = set()
    for path in frontend_source_paths():
        strings.update(extract_frontend_strings(path))
    return sorted(strings)


def extract_placeholders(value: str) -> tuple[str, ...]:
    return tuple(sorted(PLACEHOLDER.findall(value)))


def extract_html_tags(value: str) -> tuple[str, ...]:
    return tuple(HTML_TAG.findall(value))


def is_html_source(value: str) -> bool:
    lowered = value.lower()
    return "<html" in lowered or "<!doctype html" in lowered


def translation_preserves_structure(source: str, translated: str) -> bool:
    if not translated.strip():
        return False
    if extract_placeholders(source) != extract_placeholders(translated):
        return False
    if not is_html_source(source):
        return True
    return extract_html_tags(source) == extract_html_tags(translated)


def extract_ui_strings(path: Path) -> tuple[set[str], str]:
    strings = set()
    agreement = ""
    root = ET.parse(path).getroot()
    for string_node in root.findall(".//string"):
        value = "".join(string_node.itertext())
        if CYRILLIC.search(value):
            strings.add(value)
        parent = None
        for property_node in root.findall(".//property[@name='html']"):
            if string_node in list(property_node):
                parent = property_node
                break
        if path.name == "user_agreement.ui" and parent is not None:
            agreement = value
    return strings, agreement


def source_strings() -> tuple[list[str], str]:
    strings = set()
    agreement = ""
    for relative_path in PYTHON_SOURCES:
        strings.update(extract_python_strings(PROJECT_ROOT / relative_path))
    for relative_root in QT_FREE_PYTHON_ROOTS:
        root = PROJECT_ROOT / relative_root
        for python_path in sorted(root.rglob("*.py")):
            strings.update(extract_python_strings(python_path))
    for ui_path in sorted((PROJECT_ROOT / "UI template").glob("*.ui")):
        ui_strings, ui_agreement = extract_ui_strings(ui_path)
        strings.update(ui_strings)
        agreement = ui_agreement or agreement
    strings.update(frontend_source_strings())
    return sorted(strings), agreement


def make_batches(strings: list[str], maximum_characters: int = 2500):
    batch = []
    batch_size = 0
    for source in strings:
        extra_size = len(source) + (len(SEPARATOR) if batch else 0)
        if batch and (len(batch) >= 15 or batch_size + extra_size > maximum_characters):
            yield batch
            batch = []
            batch_size = 0
        batch.append(source)
        batch_size += extra_size
    if batch:
        yield batch


def translate_batch(language: str, batch: list[str]) -> list[str]:
    protected_batch = []
    placeholders_by_source = []
    for source in batch:
        matches = list(PLACEHOLDER.finditer(source))
        protected = source
        replacements = []
        for index, match in reversed(list(enumerate(matches))):
            token = f"__NFPROGRESS_PH_{index}__"
            protected = protected[:match.start()] + token + protected[match.end():]
            replacements.append((token, match.group(0)))
        protected_batch.append(protected)
        placeholders_by_source.append(replacements)

    request_data = urllib.parse.urlencode(
        {
            "client": "gtx",
            "sl": "ru",
            "tl": language,
            "dt": "t",
            "q": SEPARATOR.join(protected_batch),
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        TRANSLATE_URL,
        data=request_data,
        headers={"User-Agent": "nfprogress-translation-generator/1.0"},
    )
    for attempt in range(8):
        try:
            with urllib.request.urlopen(
                request, timeout=45, context=SSL_CONTEXT
            ) as response:
                data = json.loads(response.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as error:
            if attempt == 7 or error.code not in {429, 500, 502, 503, 504}:
                raise
            time.sleep(min(30, 2 ** attempt))
    translated_text = "".join(part[0] for part in data[0] if part[0])
    translated = translated_text.split(SEPARATOR)
    if len(translated) != len(batch):
        if len(batch) == 1:
            raise RuntimeError("Translation service changed the batch separator")
        translated = []
        for source in batch:
            translated.extend(translate_batch(language, [source]))
    restored = []
    for source, translated_value, replacements in zip(
        batch, translated, placeholders_by_source
    ):
        for token, placeholder in replacements:
            translated_value = translated_value.replace(token, placeholder)
        if extract_placeholders(source) != extract_placeholders(translated_value):
            raise RuntimeError(
                f"Translation service changed placeholders for {source!r}"
            )
        restored.append(translated_value)
    return restored


def translate_html(language: str, source: str) -> str:
    return translate_html_strings(language, [source])[source]


def translate_html_strings(language: str, sources: list[str]) -> dict[str, str]:
    """Translate text nodes from several HTML strings in shared API batches."""
    parsed_sources = []
    text_targets = []
    text_values = []

    for source in sources:
        parts = re.split(r"(<[^>]+>)", source)
        parsed_sources.append((source, parts))
        for index in range(0, len(parts), 2):
            source_text = parts[index]
            if not CYRILLIC.search(source_text):
                continue
            match = re.match(r"^(\s*)(.*?)(\s*)$", source_text, re.DOTALL)
            leading, core, trailing = match.groups()
            text_targets.append((parts, index, leading, trailing))
            text_values.append(core)

    batches = list(make_batches(text_values))
    translated_values = []
    for completed, batch in enumerate(batches, start=1):
        translated_values.extend(translate_batch(language, batch))
        print(
            f"{language}: HTML batch {completed}/{len(batches)}",
            file=sys.stderr,
            flush=True,
        )

    for target, translated in zip(text_targets, translated_values):
        parts, index, leading, trailing = target
        parts[index] = leading + translated + trailing

    return {
        source: "".join(parts)
        for source, parts in parsed_sources
    }


def translate_language(language: str, strings: list[str]) -> dict[str, str]:
    html_strings = [
        source
        for source in strings
        if is_html_source(source)
    ]
    plain_strings = [source for source in strings if source not in html_strings]
    batches = list(make_batches(plain_strings))
    results = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(translate_batch, language, batch): batch
            for batch in batches
        }
        for completed, future in enumerate(as_completed(futures), start=1):
            batch = futures[future]
            translated = future.result()
            results.update(zip(batch, translated))
            print(
                f"{language}: {completed}/{len(batches)} batches",
                file=sys.stderr,
                flush=True,
            )
    results.update(translate_html_strings(language, html_strings))
    return results


def write_catalog(catalog: dict[str, dict[str, str]], agreement: str) -> None:
    encoded_catalog = {
        language: base64.b85encode(
            zlib.compress(
                json.dumps(
                    language_catalog,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("utf-8"),
                level=9,
            )
        ).decode("ascii")
        for language, language_catalog in catalog.items()
    }
    payload = (
        '"""Generated localization catalog. Do not edit by hand."""\n\n'
        "import base64\n"
        "import json\n"
        "import zlib\n"
        "from collections.abc import Mapping\n"
        "from functools import lru_cache\n\n"
        f"AGREEMENT_SOURCE = {agreement!r}\n"
        f"_COMPRESSED_TRANSLATIONS = {encoded_catalog!r}\n\n"
        "@lru_cache(maxsize=1)\n"
        "def _load_language_catalog(language):\n"
        "    try:\n"
        "        payload = _COMPRESSED_TRANSLATIONS[language]\n"
        "    except KeyError:\n"
        "        raise KeyError(language) from None\n"
        "    return json.loads(zlib.decompress(base64.b85decode(payload)))\n\n"
        "class _LazyTranslations(Mapping):\n"
        "    def __getitem__(self, language):\n"
        "        return _load_language_catalog(language)\n\n"
        "    def __iter__(self):\n"
        "        return iter(_COMPRESSED_TRANSLATIONS)\n\n"
        "    def __len__(self):\n"
        "        return len(_COMPRESSED_TRANSLATIONS)\n\n"
        "TRANSLATIONS = _LazyTranslations()\n"
    )
    (PROJECT_ROOT / "translations_catalog.py").write_text(
        payload, encoding="utf-8"
    )


def load_catalog() -> dict[str, dict[str, str]]:
    catalog_path = PROJECT_ROOT / "translations_catalog.py"
    if not catalog_path.exists():
        return {}

    namespace = runpy.run_path(str(catalog_path))
    translations = namespace.get("TRANSLATIONS", {})
    return {
        language: dict(language_catalog)
        for language, language_catalog in translations.items()
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate missing translations for the bundled catalog."
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Regenerate every translation instead of adding only missing strings.",
    )
    return parser.parse_args()


def load_translation_overrides() -> dict[str, dict[str, str]]:
    """Load manual terminology only when generating the runtime catalog."""
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from localization import TRANSLATION_OVERRIDES

    return {
        language: dict(language_overrides)
        for language, language_overrides in TRANSLATION_OVERRIDES.items()
    }


def main() -> int:
    args = parse_args()
    strings, agreement = source_strings()
    overrides = load_translation_overrides()
    override_sources = {
        source
        for language_overrides in overrides.values()
        for source in language_overrides
    }
    strings = sorted(set(strings) | override_sources)
    print(f"Extracted {len(strings)} Russian strings", file=sys.stderr)
    catalog = {} if args.full else load_catalog()
    russian_catalog = catalog.setdefault("ru", {})
    russian_catalog.update({source: source for source in strings})

    for language in TARGET_LANGUAGES:
        output_language = CATALOG_LANGUAGE.get(language, language)
        language_catalog = catalog.setdefault(output_language, {})
        if args.full:
            language_catalog.clear()
        language_catalog.update(overrides.get(output_language, {}))
        missing_strings = [
            source
            for source in strings
            if source not in language_catalog
            or not translation_preserves_structure(source, language_catalog[source])
        ]
        print(
            f"{output_language}: {len(missing_strings)} missing strings",
            file=sys.stderr,
        )
        if missing_strings:
            language_catalog.update(
                translate_language(language, missing_strings)
            )
            language_catalog.update(overrides.get(output_language, {}))
            # Keep completed languages so a temporary translation-service
            # failure can be resumed without repeating successful requests.
            write_catalog(catalog, agreement)

    english_agreement = catalog["en"].get(agreement, agreement)
    for language in ("es", "de", "fr", "pt_BR"):
        catalog[language][agreement] = english_agreement
    write_catalog(catalog, agreement)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
