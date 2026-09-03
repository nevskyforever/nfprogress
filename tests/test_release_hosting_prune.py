import os
import subprocess
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _write_executable(path: Path, content: str) -> None:
    path.write_text(textwrap.dedent(content).lstrip(), encoding='utf-8')
    path.chmod(0o755)


def _touch_release(path: Path, timestamp: int) -> None:
    path.write_bytes(b'release')
    os.utime(path, (timestamp, timestamp))


def test_prune_release_hosting_keeps_three_newest_versions_per_platform(tmp_path):
    release_dir = tmp_path / 'release-hosting'
    release_dir.mkdir()
    for timestamp, version in enumerate(('1.0.0', '1.1.0', '1.2.0', '1.3.0'), start=1):
        installer = release_dir / f'nfprogress-windows-x86_64-{version}-setup.exe'
        _touch_release(installer, timestamp)
        _touch_release(Path(f'{installer}.sig'), timestamp)
        _touch_release(release_dir / f'nfprogress-mac-arm-{version}.zip', timestamp)
        _touch_release(release_dir / f'nfprogress-mac-intel-{version}.zip', timestamp)
    _touch_release(release_dir / 'update_manifest.json', 10)

    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    _write_executable(
        bin_dir / 'ssh',
        '''
        #!/bin/bash
        set -euo pipefail
        command="${!#}"
        exec bash -c "$command"
        ''',
    )
    key_path = tmp_path / 'test-key'
    key_path.write_text('test key\n', encoding='utf-8')

    result = subprocess.run(
        [str(ROOT / 'scripts' / 'prune-release-hosting.sh')],
        cwd=ROOT,
        env=os.environ | {
            'PATH': f'{bin_dir}{os.pathsep}{os.environ["PATH"]}',
            'SSH_UPLOAD_KEY_PATH': str(key_path),
            'SSH_UPLOAD_DIR': str(release_dir),
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    for prefix, suffix in (
        ('nfprogress-windows-x86_64-', '-setup.exe'),
        ('nfprogress-mac-arm-', '.zip'),
        ('nfprogress-mac-intel-', '.zip'),
    ):
        assert sorted(path.name for path in release_dir.glob(f'{prefix}*{suffix}')) == [
            f'{prefix}1.1.0{suffix}',
            f'{prefix}1.2.0{suffix}',
            f'{prefix}1.3.0{suffix}',
        ]
    assert not (release_dir / 'nfprogress-windows-x86_64-1.0.0-setup.exe.sig').exists()
    assert (release_dir / 'update_manifest.json').is_file()
