#!/usr/bin/env python3
"""Build the existing offline Linux/CPython backend bundle from tracked Git data."""
import argparse
import gzip
import hashlib
import io
import json
import re
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / 'deploy/vps/requirements-backend-linux-amd64-py313.lock'
PATHS = ('backend', 'nfprogress', 'alembic.ini', 'requirements-backend.txt',
         'engine.py', 'gama_quests.py', 'game.py', 'game_data.py',
         'help_content.py', 'scrivener_parser.py', 'translations_catalog.py',
         'deploy/vps/worta-staging.service.example')


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--revision', required=True)
    parser.add_argument('--wheelhouse', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    revision = subprocess.check_output(['git', 'rev-parse', '--verify', args.revision + '^{commit}'], cwd=ROOT, text=True).strip()
    lock = LOCK.read_bytes()
    required = re.findall(rb'--hash=sha256:([a-f0-9]{64})', lock)
    if not required or len(set(required)) != len(required):
        raise SystemExit('Invalid or duplicate lock hashes')
    selected = {}
    for path in args.wheelhouse.glob('*.whl'):
        content = path.read_bytes()
        checksum = digest(content).encode()
        if checksum in required:
            if checksum in selected:
                raise SystemExit('Duplicate wheel hash')
            selected[checksum] = (path.name, content)
    if set(selected) != set(required):
        raise SystemExit('Wheelhouse does not contain every locked wheel')
    source = subprocess.check_output(['git', 'archive', '--format=tar', revision, '--', *PATHS], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(source), mode='r:') as archive:
        for entry in archive:
            name = entry.name.lower()
            if (not (entry.isfile() or entry.isdir()) or
                    (entry.isfile() and (name.endswith(('.db', '.sqlite', '.sqlite3', '.env', '.pem', '.key'))
                     or name.rsplit('/', 1)[-1].startswith('.env')))):
                raise SystemExit(f'Unsafe source archive member: {entry.name}')
    entries = {'source.tar': source, LOCK.name: lock}
    entries.update({f'wheels/{name}': content for name, content in selected.values()})
    manifest = {'revision': revision, 'target': 'ubuntu24.04-linux-amd64-cpython3.13',
                'sha256': {name: digest(content) for name, content in sorted(entries.items())}}
    entries['MANIFEST.json'] = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('wb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', filename='', mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode='w', format=tarfile.USTAR_FORMAT) as archive:
            for name, content in sorted(entries.items()):
                info = tarfile.TarInfo(name)
                info.size = len(content)
                info.mode = 0o644
                info.mtime = 0
                archive.addfile(info, io.BytesIO(content))
    print(f'{digest(args.output.read_bytes())}  {args.output}')


if __name__ == '__main__':
    main()
