#!/usr/bin/env python3
"""Create the temporary signed-release overlay consumed by Tauri CI."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import quote


SEMVER = re.compile(r'^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$')
REPOSITORY = re.compile(r'^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$')
THUMBPRINT = re.compile(r'^[0-9A-Fa-f]{40,64}$')


def release_config(
    *,
    version: str,
    repository: str,
    public_key: str,
    certificate_thumbprint: str,
    timestamp_url: str,
) -> dict[str, object]:
    if not SEMVER.fullmatch(version):
        raise ValueError(f'Invalid semantic version: {version!r}.')
    if not REPOSITORY.fullmatch(repository):
        raise ValueError(f'Invalid GitHub repository: {repository!r}.')
    public_key = public_key.strip()
    if not public_key:
        raise ValueError('The Tauri updater public key is empty.')
    certificate_thumbprint = certificate_thumbprint.replace(' ', '').upper()
    if not THUMBPRINT.fullmatch(certificate_thumbprint):
        raise ValueError('The Authenticode certificate thumbprint is invalid.')
    if not timestamp_url.startswith(('https://', 'http://')):
        raise ValueError('The timestamp URL must use HTTP or HTTPS.')

    endpoint = (
        f'https://github.com/{quote(repository, safe="/")}'
        '/releases/latest/download/latest.json'
    )
    return {
        'version': version,
        'bundle': {
            'targets': ['nsis'],
            'createUpdaterArtifacts': True,
            'windows': {
                'certificateThumbprint': certificate_thumbprint,
                'digestAlgorithm': 'sha256',
                'timestampUrl': timestamp_url,
                'nsis': {'installMode': 'currentUser'},
            },
        },
        'plugins': {
            'updater': {
                'pubkey': public_key,
                'endpoints': [endpoint],
                'windows': {'installMode': 'passive'},
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', required=True)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--public-key-file', type=Path, required=True)
    parser.add_argument('--certificate-thumbprint', required=True)
    parser.add_argument('--timestamp-url', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()

    payload = release_config(
        version=args.version,
        repository=args.repository,
        public_key=args.public_key_file.read_text(encoding='utf-8'),
        certificate_thumbprint=args.certificate_thumbprint,
        timestamp_url=args.timestamp_url,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )
    print(args.output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
