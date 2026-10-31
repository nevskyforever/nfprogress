from __future__ import annotations

import hashlib
import io
import importlib.util
import json
import sys
import tarfile
from pathlib import Path

import pytest


def builder():
    path = Path(__file__).resolve().parents[1] / 'scripts/maintenance/build_vps_backend.py'
    spec = importlib.util.spec_from_file_location('vps_backend_bundle', path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_bundle_is_reproducible_and_refuses_missing_wheel(tmp_path, monkeypatch):
    module = builder()
    wheels = tmp_path / 'wheels'
    wheels.mkdir()
    content = b'test wheel, no application data'
    wheel = wheels / 'test-1-py3-none-any.whl'
    wheel.write_bytes(content)
    lock = tmp_path / 'requirements.lock'
    lock.write_text('test==1 --hash=sha256:' + hashlib.sha256(content).hexdigest() + '\n')
    monkeypatch.setattr(module, 'LOCK', lock)
    source = io.BytesIO()
    with tarfile.open(fileobj=source, mode='w') as archive:
        entry = tarfile.TarInfo('backend/app.py')
        entry.size = len(b'safe source')
        archive.addfile(entry, io.BytesIO(b'safe source'))
    monkeypatch.setattr(module.subprocess, 'check_output', lambda command, **kwargs:
                        'a' * 40 + '\n' if command[1] == 'rev-parse' else source.getvalue())
    outputs = [tmp_path / 'one.tar.gz', tmp_path / 'two.tar.gz']
    for output in outputs:
        monkeypatch.setattr(sys, 'argv', ['builder', '--revision', 'HEAD', '--wheelhouse', str(wheels), '--output', str(output)])
        module.main()
    assert outputs[0].read_bytes() == outputs[1].read_bytes()
    with tarfile.open(outputs[0]) as archive:
        manifest = json.load(archive.extractfile('MANIFEST.json'))
        assert manifest['sha256']['wheels/' + wheel.name] == hashlib.sha256(content).hexdigest()
        assert set(archive.getnames()) == {'source.tar', 'requirements.lock', 'wheels/' + wheel.name, 'MANIFEST.json'}
    wheel.unlink()
    with pytest.raises(SystemExit, match='every locked wheel'):
        module.main()
    wheel.write_bytes(content)
    unsafe = io.BytesIO()
    with tarfile.open(fileobj=unsafe, mode='w') as archive:
        archive.addfile(tarfile.TarInfo('backend/.env.production'))
    monkeypatch.setattr(module.subprocess, 'check_output', lambda command, **kwargs:
                        'a' * 40 + '\n' if command[1] == 'rev-parse' else unsafe.getvalue())
    with pytest.raises(SystemExit, match='Unsafe source archive member'):
        module.main()
