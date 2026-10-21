"""Check actual ARM64 Mach-O deployment versions, independently of SDK version."""
import re
import subprocess


def version_tuple(version):
    if not re.fullmatch(r'\d+\.\d+(?:\.\d+)?', version):
        raise ValueError('Invalid minimum macOS version: ' + version)
    return tuple(map(int, version.split('.'))) + (0,) * (3 - len(version.split('.')))


def parse_minimum(text):
    versions = re.findall(r'^\s*minos\s+(\d+\.\d+(?:\.\d+)?)\s*$', text, re.M)
    if not versions or not re.search(r'^\s*platform\s+MACOS\s*$', text, re.M):
        raise ValueError('Cannot identify ARM64 macOS deployment version')
    return max(versions, key=version_tuple)


def check_bundle(contents, minimum):
    target = version_tuple(minimum)
    records = []
    for path in sorted(contents.rglob('*')):
        if not path.is_file() or path.is_symlink():
            continue
        with path.open('rb') as stream:
            magic = stream.read(4)
        if magic not in (b'\xcf\xfa\xed\xfe', b'\xfe\xed\xfa\xcf', b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca'):
            continue
        text = subprocess.check_output(['vtool', '-arch', 'arm64', '-show-build', str(path)], text=True)
        required = parse_minimum(text)
        if version_tuple(required) > target:
            raise ValueError(f'{path.name} requires macOS {required}, above package target {minimum}. '
                             'Rebuild the dependency for the target OS or explicitly choose a higher package minimum.')
        records.append({'file': path.relative_to(contents).as_posix(), 'minimum_macos': required})
    if not records:
        raise ValueError('No Mach-O runtime found for deployment verification')
    return {'minimum_macos': minimum, 'architecture': 'arm64', 'binaries': records}
