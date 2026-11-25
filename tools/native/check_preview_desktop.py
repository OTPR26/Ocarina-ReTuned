import hashlib
import os
from pathlib import Path
import subprocess as sp
import sys
import tarfile
import time
import urllib.request

label = sys.argv[1]
windows = os.name == 'nt'
suffix = '.zip' if windows else '.tar.gz'
name = 'Ocarina-ReTuned-0.8.0-' + label + suffix
url = 'https://github.com/OTPR26/Ocarina-ReTuned/releases/download/v0.8.0/'
checks = urllib.request.urlopen(url + 'SHA256-Checksums.txt').read().decode()
digest = next(line.split()[0] for line in checks.splitlines() if line.split()[-1] == name)
sp.run(['curl', '-fsSL', '--retry', '3', url + name, '-o', name], check=True)
with open(name, 'rb') as archive:
    assert hashlib.file_digest(archive, 'sha256').hexdigest() == digest
sp.run(['tar', '-xf', name], check=True)
root = Path('Ocarina-ReTuned-' + label).resolve()
host = root / ('OcarinaReTuned.exe' if windows else 'OcarinaReTuned')
setup = root / 'setup'
python = setup / ('python/python.exe' if windows else 'python/bin/python3')
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
if not windows:
    env['LD_LIBRARY_PATH'] = str(root)
if label == 'Windows-x64':
    import json, zipfile
    outer = Path('verified-host.zip')
    sp.run(['gh','api','repos/OTPR26/Ocarina-ReTuned/actions/artifacts/14997939796/zip'], stdout=outer.open('wb'),check=True)
    assert hashlib.sha256(outer.read_bytes()).hexdigest()=='6746caec08e2c5a7c8961f38c97755145108ee9db6c393745e41f899bb840a80'
    with zipfile.ZipFile(outer) as wrapper:
        archive=Path(wrapper.extract(next(n for n in wrapper.namelist() if n.endswith('.zip'))))
    with zipfile.ZipFile(archive) as package:
        manifest=root/'package-manifest.json'
        data=json.loads(manifest.read_text())
        for member in package.namelist():
            rel=member.partition('/')[2]
            if rel in ('shaderc_shared.dll','MSVCP140.dll','VCRUNTIME140.dll','VCRUNTIME140_1.dll') or (rel.startswith('licenses/') and not member.endswith('/')):
                dest=root/rel
                if dest.exists():continue
                dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_bytes(package.read(member))
                data['files'][rel]=hashlib.sha256(dest.read_bytes()).hexdigest()
        manifest.write_text(json.dumps(data,indent=2)+'\n')
    out=Path('candidate')
    out.mkdir()
    result=out/name
    with zipfile.ZipFile(result,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=5) as package:
        for f in sorted(root.rglob('*')):
            if f.is_file():package.write(f,f.relative_to(root.parent))
    sp.run(['tar','-xf',str(result.resolve())],cwd=out,check=True)
    root=out.resolve()/root.name
    host=root/host.name
    setup=root/'setup'
    python=setup/'python/python.exe'
sp.run([host, '--product-info'], cwd=root, env=env, check=True, timeout=40)
sp.run([python, setup/'project/tools/native/rom_setup.py', '--kit', setup/'kit.json',
        '--host', host, '--check-kit'], cwd=root, env=env, check=True, timeout=180)
folder = Path('compiler probe').resolve()
folder.mkdir()
(folder/'CMakeLists.txt').write_text('cmake_minimum_required(VERSION 3.20)\nproject(probe LANGUAGES CXX)\nadd_library(support STATIC support.cpp)\nadd_executable(probe main.cpp)\ntarget_link_libraries(probe PRIVATE support)\n')
(folder/'support.cpp').write_text('#include <vector>\nint answer(){return std::vector<int>{42}.at(0);}\n')
(folder/'main.cpp').write_text('int answer(); int main(){return answer()!=42;}\n')
if windows:
    tools = setup/'tools'
    cmake = tools/'cmake/bin/cmake.exe'
    args = ['-DCMAKE_TOOLCHAIN_FILE='+str(tools/'windows-toolchain.cmake')]
else:
    tools = setup/'build-tools'
    cmake = tools/'cmake/bin/cmake'
    args = ['-DCMAKE_CXX_COMPILER='+str(tools/'toolchain/bin/c++'), '-DCMAKE_MAKE_PROGRAM='+str(tools/'ninja/ninja')]
build = folder/'build'
sp.run([cmake,'-S',folder,'-B',build,'-G','Ninja',*args],check=True)
sp.run([cmake,'--build',build],check=True)
sp.run([build/('probe.exe' if windows else 'probe')],check=True)
print('Packaged host, preparation preflight, compiler, linker, and compiled executable passed.',flush=True)
