import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TAURI = ROOT / 'frontend' / 'src-tauri'


def test_production_tauri_config_has_no_python_sidecar_or_loopback_backend():
    config = json.loads((TAURI / 'tauri.conf.json').read_text(encoding='utf-8'))
    bundle = config['bundle']
    assert 'externalBin' not in bundle
    assert 'nfprogress-backend' not in json.dumps(config)
    assert '127.0.0.1:*' not in config['app']['security']['csp']


def test_native_startup_has_no_python_process_or_backend_health_path():
    source = (TAURI / 'src' / 'lib.rs').read_text(encoding='utf-8')
    assert 'backend_connection' not in source
    assert 'BackendState' not in source
    assert 'nfprogress-backend' not in source
    assert '.sidecar(' not in source
    assert 'TcpListener' not in source
    assert 'TcpStream' not in source
    assert 'GET /health' not in source
    assert 'Command::new("python' not in source


def test_native_frontend_has_no_session_bridge_or_project_api_fallback():
    runtime = (ROOT / 'frontend' / 'src' / 'platform' / 'runtime.ts').read_text(encoding='utf-8')
    client = (ROOT / 'frontend' / 'src' / 'api' / 'client.ts').read_text(encoding='utf-8')
    repository = (ROOT / 'frontend' / 'src' / 'infrastructure' / 'projects' / 'projectReadRepository.ts').read_text(encoding='utf-8')
    assert 'backend_connection' not in runtime
    assert 'sessionToken' not in runtime
    assert 'X-NFProgress-Token' not in client
    assert 'FallbackProjectReadRepository' not in repository
    assert 'catch' not in repository


def test_desktop_build_and_ci_do_not_prepare_a_python_backend():
    paths = [
        ROOT / 'scripts' / 'build-tauri-local.sh',
        ROOT / 'scripts' / 'build-tauri-dmg.sh',
        ROOT / 'Run Tauri.sh',
        ROOT / 'Build Tauri Intel.sh',
        ROOT / 'Release Tauri Intel.sh',
        ROOT / '.github' / 'workflows' / 'build.yml',
    ]
    source = '\n'.join(path.read_text(encoding='utf-8') for path in paths)
    assert 'build-backend-sidecar' not in source
    assert 'sync-tauri-versions.py' not in source
    assert 'nfprogress-backend' not in source
    assert 'nuitka' not in source.lower()
    assert 'NFPROGRESS_TAURI_PYTHON' not in source


def test_web_and_legacy_python_boundaries_remain_available():
    assert (ROOT / 'backend' / 'app' / 'main.py').is_file()
    assert (ROOT / 'nfprogress' / 'core' / 'migration.py').is_file()
    assert (ROOT / 'tests' / 'test_api.py').is_file()
