#!/usr/bin/env python3
"""Exercise release tools in a chroot without system compilers or binutils libraries."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from stage_linux_compiler import stage


def validate(package, report):
    tools = Path(package).resolve() / 'setup/build-tools'
    old = tools / 'toolchain'
    manifest = json.loads((old / 'toolchain-manifest.json').read_text())
    with tempfile.TemporaryDirectory(prefix='retuned-tools-check-') as directory:
        root = Path(directory)
        bundle = root / 'package with spaces/build-tools'
        bundle.parent.mkdir(parents=True)
        shutil.copytree(tools, bundle, symlinks=True)
        (root / 'bin').mkdir()
        shutil.copy2('/bin/dash', root / 'bin/sh')
        (root / 'tmp').mkdir(mode=0o1777)
        (root / 'dev').mkdir()
        subprocess.run(['mknod', str(root / 'dev/null'), 'c', '1', '3'], check=True)
        (root / 'dev/null').chmod(0o666)
        # Only the shell/CMake/Ninja's ELF dependencies enter the system paths.
        # In particular, never copy dependencies of ar or other compiler tools.
        dependencies = set()
        for executable in ('/bin/dash', tools / 'cmake/bin/cmake', tools / 'ninja/ninja'):
            output = subprocess.check_output(['ldd', str(executable)], text=True)
            for line in output.splitlines():
                match = re.search(r'(?:=>\s*)?(/[^\s]+)', line)
                if match:
                    path = Path(match[1])
                    assert not any(s in path.name for s in ('libbfd', 'libopcodes', 'libsframe', 'libctf'))
                    dependencies.add(str(path))
                    destination = root / str(path).lstrip('/')
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, destination, follow_symlinks=True)
        def run(command, check=True):
            result = subprocess.run(['chroot', str(root), *command],
                env={'PATH': '/nonexistent', 'LC_ALL': 'C', 'HOME': '/tmp'},
                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
            print(result.stdout, end='', flush=True)
            if check: result.check_returncode()
            return result
        original = run(['/package with spaces/build-tools/toolchain/bin/ar', '--version'], False)
        assert original.returncode != 0 and 'libbfd' in original.stdout, original.stdout
        receipts = root / 'packages.json'
        receipts.write_text(json.dumps(manifest['packages']))
        fixed = root / 'fixed'
        stage(old / 'sysroot', fixed, manifest['architecture'], receipts)
        shutil.rmtree(bundle / 'toolchain')
        fixed.rename(bundle / 'toolchain')
        source = root / 'source'
        source.mkdir()
        (source / 'CMakeLists.txt').write_text('''cmake_minimum_required(VERSION 3.20)
project(compiler_check LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
add_library(support STATIC support.cpp)
add_library(plugin SHARED plugin.cpp)
target_link_libraries(plugin PRIVATE support)
add_executable(check main.cpp)
target_link_libraries(check PRIVATE plugin)
''')
        (source / 'support.cpp').write_text('#include <vector>\nint answer(){return std::vector<int>{20,22}.at(0)+22;}\n')
        (source / 'plugin.cpp').write_text('int answer(); extern "C" int value(){return answer();}\n')
        (source / 'main.cpp').write_text('extern "C" int value(); int main(){return value()==42?0:1;}\n')
        for iteration, location in enumerate(('package with spaces', 'moved package')):
            if iteration:
                (root / 'package with spaces').rename(root / location)
            prefix = f'/{location}/build-tools'
            for name in ('as', 'ld', 'ar', 'ranlib', 'strip', 'nm'):
                run([prefix + '/toolchain/bin/' + name, '--version'])
            build = '/build' + str(iteration)
            run([prefix + '/cmake/bin/cmake', '-S', '/source', '-B', build, '-G', 'Ninja',
                 '-DCMAKE_CXX_COMPILER=' + prefix + '/toolchain/bin/c++',
                 '-DCMAKE_MAKE_PROGRAM=' + prefix + '/ninja/ninja'])
            run([prefix + '/cmake/bin/cmake', '--build', build, '--parallel', '2'])
            run([build + '/check'])
        Path(report).write_text(json.dumps({'status': 'PASS', 'architecture': manifest['architecture'],
            'original_failure_reproduced': True, 'relocated_static_shared_and_executable': True,
            'system_libraries': sorted(dependencies)}, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    validate(args.package, args.report)
