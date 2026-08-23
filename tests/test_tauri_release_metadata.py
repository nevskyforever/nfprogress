import importlib.util
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_script(filename: str, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, ROOT / 'scripts' / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


release_config = _load_script(
    'create-tauri-release-config.py', 'create_tauri_release_config',
).release_config
update_manifest = _load_script(
    'create-tauri-update-manifest.py', 'create_tauri_update_manifest',
).update_manifest
windows_release_options = _load_script(
    'build-backend-sidecar.py', 'build_backend_sidecar',
)._windows_release_options
sync_versions = _load_script(
    'sync-tauri-versions.py', 'sync_tauri_versions',
)


def test_engine_versions_are_normalized_to_three_components():
    assert sync_versions.canonical_version('5.0') == '5.0.0'
    assert sync_versions.canonical_version('4.14.2') == '4.14.2'
    assert sync_versions.canonical_version('5.0-rc1') == '5.0.0-rc1'


def test_release_config_creates_nsis_updater_artifacts():
    payload = release_config(
        version='4.15.0',
        repository='owner/nfprogress',
        public_key='untrusted comment: minisign public key\nRWQexample',
    )

    assert payload['bundle']['createUpdaterArtifacts'] is True
    assert payload['bundle']['windows']['nsis']['installMode'] == 'currentUser'
    assert payload['plugins']['updater']['endpoints'] == [
        'https://github.com/owner/nfprogress/releases/latest/download/latest.json',
    ]
    assert payload['plugins']['updater']['windows']['installMode'] == 'passive'


def test_update_manifest_embeds_signature_and_stable_release_url():
    payload = update_manifest(
        version='4.15.0',
        repository='owner/nfprogress',
        tag='v4.15.0',
        artifact_name='nfprogress-windows-x86_64-4.15.0-setup.exe',
        signature='signed-content\n',
        notes='Исправления\n',
        published_at='2026-08-23T10:00:00Z',
    )

    windows = payload['platforms']['windows-x86_64']
    assert windows['signature'] == 'signed-content'
    assert windows['url'].endswith(
        '/releases/download/v4.15.0/nfprogress-windows-x86_64-4.15.0-setup.exe',
    )


def test_windows_sidecar_has_stable_identity_and_uncompressed_payload():
    options = windows_release_options()
    cargo = tomllib.loads(
        (ROOT / 'frontend' / 'src-tauri' / 'Cargo.toml').read_text(encoding='utf-8'),
    )
    version = cargo['package']['version'].split('-', 1)[0].split('+', 1)[0]

    assert '--onefile-no-compression' in options
    assert '--windows-console-mode=disable' in options
    assert '--product-name=nfprogress' in options
    assert f'--file-version={version}' in options
    assert any(option.startswith('--windows-icon-from-ico=') for option in options)
