#!/usr/bin/env python3
"""Build neutral release components on hosted runners, without a user ROM."""
import argparse
import hashlib
import json
import os
import plistlib
import re
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
ENGINE_REVISION = '17218b0cfdb944645bb5cde5249f313dca7e53ce'
DOWNLOADS = {
    'moltenvk': ('https://github.com/KhronosGroup/MoltenVK/releases/download/v1.4.2/MoltenVK-all.tar',
                 '562a15a29bc358446a56a4091c5f7e08f604184187c1d34f712148b61ef17276'),
    'llvm': ('https://github.com/mstorsjo/llvm-mingw/releases/download/20261006/llvm-mingw-20261006-ucrt-macos-universal.tar.xz',
             'a7a19b11048e89372637d26279cdb7c430ed3cf8c1e224310421312bf986ebf6'),
}


def run(*args, **kwargs):
    return subprocess.run(list(map(str, args)), check=True, **kwargs)


def fetch(name, work):
    url, expected = DOWNLOADS[name]
    archive = work / (name + '.tar')
    urllib.request.urlretrieve(url, archive)
    with archive.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != expected:
            raise ValueError('Dependency checksum mismatch: ' + name)
    dest = work / name
    dest.mkdir()
    with tarfile.open(archive) as package:
        package.extractall(dest, filter='data')
    archive.unlink()
    return dest


def patch(engine, apple=True):
    scripts = ['tools/native/apply_macos_port.py', 'tools/reframed/apply_native_port.py',
               'tools/reframed/apply_renderer_port.py', 'tools/native/apply_audio_port.py',
               'tools/frontend/apply_frontend_port.py']
    if apple:
        scripts += ['tools/native/apple/apply_apple_port.py',
                    'tools/native/apple/apply_duo_game_probe.py']
    for script in scripts:
        run(sys.executable, ROOT / script, engine)


def configure(engine, build, extra):
    flags = {
        'CMAKE_BUILD_TYPE': 'Release', 'CMAKE_C_COMPILER_LAUNCHER': 'ccache',
        'CMAKE_CXX_COMPILER_LAUNCHER': 'ccache', 'OOT3D_WHOLE_AOT_PRODUCT_MODE': 'ON',
        'OOT3D_DIRECT_AOT_PLUGIN': 'ON', 'OOT3D_REBUILD_WHOLE_AOT': 'OFF',
        'OOT3D_ENABLE_VULKAN_RENDERER': 'ON', 'THREE_DS_RECOMP_ENABLE_NRI': 'ON',
        'ENABLE_SCRIPTING': 'OFF', 'INCLUDE_MPQ_SUPPORT': 'OFF',
        'THREE_DS_RECOMP_OFFER_EXPERIMENTAL_GI': 'OFF',
    }
    for feature in ('IMMERSE', 'NRI_UPSCALER_SDKS', 'DLSS_MODULE', 'SSSR', 'CACAO'):
        flags['THREE_DS_RECOMP_ENABLE_' + feature] = 'OFF'
    flags.update(extra)
    run('cmake', '-S', engine, '-B', build, '-G', 'Ninja',
        *['-D' + k + '=' + str(v) for k, v in flags.items()])


def moltenvk_framework(vendor, platform):
    manifests = list(vendor.glob('**/dynamic/MoltenVK.xcframework/Info.plist'))
    if len(manifests) != 1:
        raise ValueError('Expected one dynamic MoltenVK XCFramework')
    manifest = manifests[0]
    data = plistlib.loads(manifest.read_bytes())
    slices = [entry for entry in data['AvailableLibraries']
              if entry['SupportedPlatform'] == platform
              and 'arm64' in entry['SupportedArchitectures']
              and not entry.get('SupportedPlatformVariant')]
    if len(slices) != 1:
        raise ValueError('Expected one ARM64 device framework for ' + platform)
    entry = slices[0]
    result = (manifest.parent / entry['LibraryIdentifier'] / entry['LibraryPath']).resolve()
    if not result.is_relative_to(vendor.resolve()) or not result.is_dir():
        raise ValueError('Invalid MoltenVK framework path')
    return result


def apple(platform, engine, work, out):
    patch(engine)
    vendor = fetch('moltenvk', work)
    framework = moltenvk_framework(vendor, platform)
    headers = next(vendor.rglob('include/vulkan/vulkan.h')).parents[1]
    build = work / 'build'
    sdk = 'iphoneos' if platform == 'ios' else 'appletvos'
    maps = '-ffile-prefix-map=' + str(ROOT) + '=/source'
    configure(engine, build, {
        'CMAKE_SYSTEM_NAME': 'iOS' if platform == 'ios' else 'tvOS',
        'CMAKE_OSX_SYSROOT': subprocess.check_output(['xcrun', '--sdk', sdk, '--show-sdk-path'], text=True).strip(),
        'CMAKE_OSX_ARCHITECTURES': 'arm64', 'CMAKE_OSX_DEPLOYMENT_TARGET': '17.0',
        'CMAKE_C_FLAGS': maps, 'CMAKE_CXX_FLAGS': maps,
        'CMAKE_OBJC_FLAGS': maps, 'CMAKE_OBJCXX_FLAGS': maps,
        'CMAKE_XCODE_ATTRIBUTE_CODE_SIGNING_ALLOWED': 'NO',
        'Vulkan_INCLUDE_DIR': headers, 'Vulkan_LIBRARY': framework / 'MoltenVK',
    })
    check_commands(build, 'oot3d_native_game')
    run('cmake', '--build', build, '--parallel', '3', '--target', 'oot3d_native_game')
    app = build / 'OcarinaReTuned.app'
    if not app.is_dir():
        raise ValueError('Expected unsigned Apple host bundle')
    payload = out / 'Payload'
    payload.mkdir()
    target = payload / app.name
    shutil.copytree(app, target, symlinks=True)
    (target / 'Frameworks').mkdir(exist_ok=True)
    shutil.copytree(framework, target / 'Frameworks/MoltenVK.framework', symlinks=True)
    from audit_neutral_shaders import verify
    verify(engine, target / 'OcarinaReTuned')
    executable = target / 'OcarinaReTuned'
    loads = subprocess.check_output(['otool', '-l', str(executable)], text=True).splitlines()
    for i, line in enumerate(loads):
        if line.strip() == 'cmd LC_RPATH':
            value = loads[i + 2].strip().split('path ', 1)[1].split(' (offset')[0]
            if value.startswith('/'):
                run('install_name_tool', '-delete_rpath', value, executable)
    # Third-party frameworks may carry a vendor signature; no identity is kept.
    for binary in (target / 'Frameworks/MoltenVK.framework/MoltenVK', target / 'OcarinaReTuned'):
        subprocess.run(['codesign', '--remove-signature', str(binary)], check=False)
    for signature in target.rglob('_CodeSignature'):
        shutil.rmtree(signature)
    for profile in target.rglob('embedded.mobileprovision'):
        profile.unlink()


def windows(engine, work, out):
    llvm = next(fetch('llvm', work).glob('llvm-mingw-*'))
    vcpkg = ROOT / 'dependencies/vcpkg'
    run(vcpkg / 'bootstrap-vcpkg.sh', '-disableMetrics')
    run(sys.executable, ROOT / 'tools/native/build_windows_cross.py', '--arch', 'arm64',
        '--engine', engine, '--llvm', llvm, '--vcpkg', vcpkg, '--work', work / 'windows', '--jobs', '3')
    from stage_desktop_host import binary_architecture, windows_dependency_notices
    from audit_neutral_shaders import verify
    build = work / 'windows/build'
    check_commands(build, 'triaevum_public_runtime')
    targets = json.loads((build / 'triaevum-runtime-targets-Release.json').read_text())
    loader = (vcpkg / 'installed/arm64-mingw-static/bin/vulkan-1.dll').resolve()
    # The runtime has no title-DLL import; its build-time stub is not a download.
    binaries = [Path(targets['runtime']).resolve()]
    if any(not binary.is_relative_to(build) for binary in binaries):
        raise ValueError('Windows target escaped its build directory')
    for binary in binaries + [loader]:
        if binary_architecture(binary, 'windows') != 'arm64':
            raise ValueError('Unexpected Windows ARM64 host component')
        verify(engine, binary)
        imports = subprocess.check_output([str(llvm / 'bin/llvm-objdump'), '-p', str(binary)], text=True)
        names = re.findall(r'DLL Name: (\S+)', imports)
        allowed = {'kernel32.dll', 'user32.dll', 'gdi32.dll', 'advapi32.dll', 'shell32.dll',
                   'ole32.dll', 'oleaut32.dll', 'comdlg32.dll', 'comctl32.dll', 'imm32.dll',
                   'winmm.dll', 'version.dll', 'setupapi.dll', 'ws2_32.dll', 'ntdll.dll',
                   'bcrypt.dll', 'ucrtbase.dll', 'opengl32.dll', 'hid.dll', 'shlwapi.dll',
                   'dwmapi.dll', 'cfgmgr32.dll', 'dbghelp.dll', 'vulkan-1.dll'}
        if any(name.lower() not in allowed and not name.lower().startswith('api-ms-win-') for name in names):
            raise ValueError('Unbundled Windows runtime dependency: ' + ', '.join(names))
        staged = out / binary.name
        shutil.copy2(binary, staged)
        run(llvm / 'bin/llvm-strip', '--strip-debug', staged)
    windows_dependency_notices(vcpkg, out / 'licenses', 'arm64-mingw-static')


def check_commands(build, target):
    from stage_desktop_host import check_neutral_commands
    commands = subprocess.check_output(['ninja', '-C', str(build), '-t', 'commands', target], text=True)
    check_neutral_commands(commands)
    return commands


def switch_xml_dependency(engine):
    path = engine / 'runtime/three_ds_recomp/cmake/dependencies/switch.cmake'
    text = path.read_text()
    old = 'find_package(tinyxml2 QUIET)\nif(NOT tinyxml2_FOUND)'
    new = 'if(NOT TARGET tinyxml2::tinyxml2)'
    if old not in text and new not in text:
        raise ValueError('Unexpected Switch XML dependency configuration')
    path.write_text(text.replace(old, new))


def switch(engine, work, out):
    patch(engine)
    sdk = Path(os.environ['DEVKITPRO'])
    expected = json.loads((ROOT / 'tools/ci/switch-sdk.json').read_text())['sdk_files']
    for name, digest in expected.items():
        with (sdk / name).open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != digest:
                raise ValueError('Switch SDK differs from the published preparation kit: ' + name)
    sdl = ROOT / 'dependencies/sdl'
    uam = ROOT / 'dependencies/switchwaker/runtime/third_party/uam'
    run(sys.executable, ROOT / 'tools/native/switch/apply_switch_port.py', '--engine', engine)
    run(sys.executable, ROOT / 'tools/native/switch/deko_backend/apply.py',
        '--engine', engine, '--sdl', sdl, '--sdk', sdk)
    run(sys.executable, ROOT / 'tools/native/switch/deko_backend/build_uam.py',
        '--source', uam, '--output', work / 'uam', '--sdk', sdk)
    switch_xml_dependency(engine)
    hook = work / 'switch-host.cmake'
    hook.write_text('include("' + str(ROOT / 'tools/native/switch/LinkTitle.cmake') + '")\n'
                    'add_compile_options("-ffile-prefix-map=' + str(ROOT) + '=/source" '
                    '"-fmacro-prefix-map=' + str(ROOT) + '=/source")\n')
    title = work / 'empty-title.a'
    run(sdk / 'devkitA64/bin/aarch64-none-elf-ar', 'rcs', title)
    build = work / 'build'
    configure(engine, build, {
        'CMAKE_TOOLCHAIN_FILE': sdk / 'cmake/Switch.cmake',
        'OOT3D_ENABLE_VULKAN_RENDERER': 'OFF', 'THREE_DS_RECOMP_ENABLE_NRI': 'OFF',
        'RETUNED_REPRODUCIBLE_PATHS': 'ON',
        'CMAKE_PROJECT_Oot3dRecomp_INCLUDE': hook,
        'RETUNED_SWITCH_TITLE_ARCHIVE': title, 'RETUNED_SWITCH_DEKO': 'ON',
        'RETUNED_SDL_SOURCE': sdl, 'RETUNED_UAM_SOURCE': uam,
        'RETUNED_UAM_LIBRARY': work / 'uam/libretuned_uam.a',
    })
    commands = check_commands(build, 'OcarinaReTuned.elf')
    links = [line for line in commands.splitlines() if '-o OcarinaReTuned.elf' in line]
    if len(links) != 1:
        raise ValueError('Cannot identify neutral Switch link components')
    # Compile only host objects/libraries. Never link a playable game in CI.
    targets = []
    for token in shlex.split(links[0]):
        if token.endswith(('.o', '.a')):
            path = Path(token)
            resolved = (build / path).resolve() if not path.is_absolute() else path.resolve()
            if resolved.is_relative_to(build):
                targets.append(str(resolved.relative_to(build)))
    if not targets:
        raise ValueError('No Switch host targets')
    run('ninja', '-C', build, '-j3', *sorted(set(targets)))
    sys.path.insert(0, str(ROOT / 'tools/native/switch'))
    from stage_link_inputs import collect
    collect(links[0], build=build, sdk=sdk, title=title, output=out / 'link-inputs')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('platform', choices=('ios', 'tvos', 'windows-arm64', 'switch'))
    args = p.parse_args()
    sys.path.insert(0, str(ROOT / 'tools/native'))
    engine = ROOT / 'engine'
    revision = subprocess.check_output(['git', '-C', str(engine), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != ENGINE_REVISION:
        raise ValueError('Wrong engine revision')
    work = ROOT / 'build/host-components'
    out = ROOT / 'artifacts/host-components'
    work.mkdir(parents=True, exist_ok=False)
    out.mkdir(parents=True, exist_ok=False)
    {'ios': lambda: apple('ios', engine, work, out),
     'tvos': lambda: apple('tvos', engine, work, out),
     'windows-arm64': lambda: windows(engine, work, out),
     'switch': lambda: switch(engine, work, out)}[args.platform]()
    from runtime_notices import copy_runtime_donor_notices
    copy_runtime_donor_notices(engine, out / 'licenses')
    for name in ('LICENSE', 'LICENSE_SCOPE.md', 'THIRD_PARTY_NOTICES.md'):
        shutil.copy2(engine / name, out / 'licenses' / name)
    receipt = {'platform': args.platform, 'engine_revision': revision,
               'project_revision': os.environ.get('GITHUB_SHA'),
               'contains_user_game': False, 'status': 'BUILD_COMPONENTS_ONLY_NOT_RELEASE_APPROVED'}
    (out / 'build-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    main()
