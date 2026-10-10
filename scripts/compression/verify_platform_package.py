"""C18.7 distribution proof. Build artifacts only; no application/user data."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[2]
NOTICE = 'licenses/C18-compression.txt'


class PackageProofError(ValueError):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def manifest(root: Path) -> dict[str, str]:
    if not root.is_dir():
        raise PackageProofError('package_missing')
    files = {p.relative_to(root).as_posix(): digest(p.read_bytes())
             for p in sorted(root.rglob('*')) if p.is_file()}
    if not files or NOTICE not in files:
        raise PackageProofError('notice_missing')
    return files


def verify(dist: Path, android: Path | None = None, apk: Path | None = None) -> dict:
    source = (ROOT / 'frontend/public' / NOTICE).read_bytes()
    expected = manifest(dist)
    if expected[NOTICE] != digest(source):
        raise PackageProofError('notice_mismatch')
    package = json.loads((ROOT / 'frontend/package.json').read_text())
    lock = json.loads((ROOT / 'frontend/package-lock.json').read_text())
    if package['dependencies']['pako'] != '2.1.0' or lock['packages']['node_modules/pako']['version'] != '2.1.0':
        raise PackageProofError('dependency_pin_changed')
    if any(re.search(r'(^|/)(brotli-wasm|zstd-codec|zstandard|@bokuweb/zstd-wasm)(/|$)', name)
           for name in lock['packages']):
        raise PackageProofError('rejected_runtime')
    module = (ROOT / 'frontend/src/cloud/frameCompression.ts').read_text()
    imports = re.findall(r"from\s+['\"]([^'\"]+)['\"]", module)
    if not imports or any(not (name == 'pako' or name.startswith('pako/')) for name in imports):
        raise PackageProofError('nonportable_compression_import')
    if re.search(r'\bBuffer\b|node:|@tauri|\bfetch\s*\(', module):
        raise PackageProofError('nonportable_compression_source')
    js = [name for name in expected if name.endswith('.js') and
          b'compression_length_mismatch' in (dist / name).read_bytes()]
    if not js:
        raise PackageProofError('production_compression_missing')
    if json.loads((ROOT / 'frontend/src-tauri/tauri.conf.json').read_text())['build']['frontendDist'] != '../dist':
        raise PackageProofError('desktop_dist_changed')
    if not re.search(r"webDir:\s*['\"]dist['\"]", (ROOT / 'frontend/capacitor.config.ts').read_text()):
        raise PackageProofError('android_dist_changed')
    result = dict(dist_files=len(expected), compression_assets=js,
                  notice_sha256=expected[NOTICE], dist_manifest_sha256=digest(json.dumps(expected, sort_keys=True).encode()),
                  pako='2.1.0', android_copy=False, apk=False)
    if android is not None:
        actual = manifest(android)
        if set(actual)-set(expected)-{'cordova.js','cordova_plugins.js','capacitor.js'}:
            raise PackageProofError('android_stale_extra_assets')
        if any(actual.get(name) != hash_value for name, hash_value in expected.items()):
            raise PackageProofError('android_assets_mismatch')
        # Capacitor may add its own bridge files; all dist files must match exactly.
        result['android_copy'] = True
    if apk is not None:
        with zipfile.ZipFile(apk) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise PackageProofError('apk_duplicate_entry')
            public={name.removeprefix('assets/public/') for name in names if name.startswith('assets/public/') and not name.endswith('/')}
            if public-set(expected)-{'cordova.js','cordova_plugins.js','capacitor.js'}:
                raise PackageProofError('apk_stale_extra_assets')
            for name, hash_value in expected.items():
                key = 'assets/public/' + name
                if key not in names or digest(archive.read(key)) != hash_value:
                    raise PackageProofError('apk_assets_mismatch')
            if any(re.search(r'(brotli|zstd|zstandard).*\.wasm$', name, re.I) for name in names):
                raise PackageProofError('rejected_wasm')
        result['apk'] = True
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dist', type=Path, default=ROOT / 'frontend/dist')
    parser.add_argument('--android', type=Path)
    parser.add_argument('--apk', type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.dist, args.android, args.apk), sort_keys=True))


if __name__ == '__main__':
    main()
