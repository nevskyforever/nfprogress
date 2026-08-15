#!/usr/bin/env python3
"""Export canonical Python localization and help content for the Vue client."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from help_content import HELP_SECTIONS, render_help_content  # noqa: E402
from localization import (  # noqa: E402
    SUPPORTED_LANGUAGES,
    TRANSLATION_OVERRIDES,
    tr,
)
from translations_catalog import TRANSLATIONS  # noqa: E402


DEFAULT_OUTPUT = PROJECT_ROOT / 'frontend' / 'src' / 'i18n' / 'generated'


def _source_keys() -> list[str]:
    keys = set()
    for catalog in TRANSLATIONS.values():
        keys.update(catalog)
    for overrides in TRANSLATION_OVERRIDES.values():
        keys.update(overrides)
    return sorted(keys)


def _project_help(section: dict, language: str) -> dict:
    return {
        'key': section['key'],
        'title': tr(section['title'], language),
        'content': render_help_content(tr(section['content'], language)),
        'children': [
            _project_help(child, language)
            for child in section.get('children', ())
        ],
    }


def build_payloads() -> dict[str, object]:
    source_keys = _source_keys()
    payloads: dict[str, object] = {}
    manifest = {
        'source_language': 'ru',
        'languages': list(SUPPORTED_LANGUAGES),
        'translation_key_count': len(source_keys),
        'help_root_count': len(HELP_SECTIONS),
    }
    payloads['manifest.json'] = manifest
    for language in SUPPORTED_LANGUAGES:
        payloads[f'locales/{language}.json'] = {
            source: source if language == 'ru' else tr(source, language)
            for source in source_keys
        }
        payloads[f'help/{language}.json'] = [
            _project_help(section, language) for section in HELP_SECTIONS
        ]
    return payloads


def _render(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + '\n'


def export(output: Path, *, check: bool = False) -> list[Path]:
    changed = []
    for relative_path, payload in build_payloads().items():
        destination = output / relative_path
        expected = _render(payload)
        current = destination.read_text(encoding='utf-8') if destination.exists() else None
        if current == expected:
            continue
        changed.append(destination)
        if check:
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(expected, encoding='utf-8')
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    changed = export(args.output, check=args.check)
    if args.check and changed:
        for path in changed:
            print(f'out of date: {path.relative_to(PROJECT_ROOT)}', file=sys.stderr)
        return 1
    if not args.check:
        print(f'Exported {len(build_payloads())} files to {args.output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
