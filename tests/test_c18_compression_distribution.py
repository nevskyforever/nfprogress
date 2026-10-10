"""Packaging verifier negatives use isolated synthetic build/APK fixtures."""
import importlib.util
from pathlib import Path
import shutil
import zipfile
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('c18_package_proof',ROOT/'scripts/compression/verify_platform_package.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def fixture(tmp):
    dist=tmp/'dist';(dist/'licenses').mkdir(parents=True)
    shutil.copyfile(ROOT/'frontend/public/licenses/C18-compression.txt',dist/'licenses/C18-compression.txt')
    (dist/'assets').mkdir();(dist/'assets/changing-name.js').write_text('compression_length_mismatch')
    android=tmp/'android';shutil.copytree(dist,android)
    apk=tmp/'app.apk'
    with zipfile.ZipFile(apk,'w') as z:
        for path in dist.rglob('*'):
            if path.is_file():z.write(path,'assets/public/'+path.relative_to(dist).as_posix())
    return dist,android,apk


def test_exact_dist_android_apk_identity_and_notice(tmp_path):
    dist,android,apk=fixture(tmp_path)
    proof=module.verify(dist,android,apk)
    assert proof['android_copy'] and proof['apk'] and proof['dist_files']==2
    assert proof['notice_sha256']==module.digest((ROOT/'frontend/public/licenses/C18-compression.txt').read_bytes())


@pytest.mark.parametrize('target',['notice','android','apk','module'])
def test_stale_missing_or_modified_assets_rejected(tmp_path,target):
    dist,android,apk=fixture(tmp_path)
    if target=='notice':(dist/'licenses/C18-compression.txt').write_text('stale notice')
    if target=='android':(android/'assets/changing-name.js').write_text('stale copy')
    if target=='apk':
        with zipfile.ZipFile(apk,'w') as z:z.writestr('assets/public/index.html','stale apk')
    if target=='module':(dist/'assets/changing-name.js').write_text('module omitted')
    with pytest.raises(module.PackageProofError):module.verify(dist,android,apk)
