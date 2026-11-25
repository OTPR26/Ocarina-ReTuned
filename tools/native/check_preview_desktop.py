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

if not windows:
    launch=sp.Popen([root/'Ocarina-ReTuned.sh'],cwd=root,env=env)
    try:
        for attempt in range(60):
            listing=sp.check_output(['xwininfo','-root','-tree'],text=True)
            if 'Ocarina ReTuned - Setup' in listing:
                print('Visible setup window confirmed through the shipped launcher.',flush=True)
                break
            if launch.poll() is not None:
                raise RuntimeError(f'Launcher exited before setup appeared: {launch.returncode}')
            time.sleep(0.5)
        else:
            raise RuntimeError('Setup window missing: '+listing)
    finally:
        if launch.poll() is None:
            launch.terminate()
            launch.wait(timeout=15)

if windows:
    # A successful product-info query does not initialize the setup frontend.
    import ctypes
    from ctypes import wintypes
    user32=ctypes.windll.user32
    callback=ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    # SDL loads opengl32 by name. Provide the test machine's software driver.
    import shutil
    gl=Path(os.environ['TEST_GL_DIR'])
    shutil.copyfile(gl/'opengl32.dll', root/'opengl32.dll')
    env['PATH']=str(gl)+os.pathsep+env['PATH']
    env['SDL_OPENGL_LIBRARY']=str(root/'opengl32.dll')
    env['GALLIUM_DRIVER']='llvmpipe'
    launch=sp.Popen([host],cwd=root,env=env)
    titles=set()
    @callback
    def visit(hwnd, lparam):
        pid=wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value==launch.pid and user32.IsWindowVisible(hwnd):
            title=ctypes.create_unicode_buffer(1024)
            user32.GetWindowTextW(hwnd,title,len(title))
            titles.add(title.value)
        return True
    try:
        for attempt in range(90):
            user32.EnumWindows(visit,0)
            if any('setup' in t.lower() and 'ocarina' in t.lower() for t in titles):
                print('Visible setup window confirmed:',titles,flush=True)
                break
            if launch.poll() is not None:raise RuntimeError(f'Host exited {launch.returncode}: {titles}')
            time.sleep(0.5)
        else:raise RuntimeError(f'No setup window; titles seen: {titles}')
    finally:
        if launch.poll() is None:
            launch.terminate();launch.wait(timeout=15)
