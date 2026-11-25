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
