#!/usr/bin/env python3
"""Check release archives for private payloads and preparation-tool integrity."""
import argparse
import hashlib
import io
import json
import tarfile
from pathlib import Path, PurePosixPath
import zipfile


def preparation_findings(archive, parent):
    findings = []
    names = set(archive.namelist())
    roots = {name.rsplit('/', 1)[0] for name in names
             if name.endswith(('/retuned/preparation-kit.json', '/retuned/preparation-kit.zip'))}
    for root in sorted(roots):
        manifest = root + '/preparation-kit.json'
        bundle = root + '/preparation-kit.zip'
        path = parent + '/' + manifest
        if not {manifest, bundle}.issubset(names):
            findings.append({'path': path, 'issue': 'incomplete preparation assets'})
            continue
        if archive.getinfo(manifest).file_size > 16384 or archive.getinfo(bundle).file_size > 512 * 1024**2:
            raise ValueError('Preparation assets exceed audit limits')
        try:
            metadata = json.loads(archive.read(manifest))
            if metadata.get('format') != 'retuned_preparation_asset_v1':
                raise ValueError('Unsupported preparation manifest')
            declared = metadata['unpacked_bytes']
            if type(declared) is not int or not 0 < declared <= 1024**3:
                raise ValueError('Invalid preparation size')
            data = archive.read(bundle)
            if metadata.get('sha256') != hashlib.sha256(data).hexdigest():
                findings.append({'path': path, 'issue': 'preparation archive checksum mismatch'})
            with zipfile.ZipFile(io.BytesIO(data)) as tools:
                actual = sum(entry.file_size for entry in tools.infolist() if not entry.is_dir())
            if declared != actual:
                findings.append({'path': path, 'issue': 'preparation archive size mismatch',
                                 'declared_bytes': declared, 'actual_bytes': actual})
        except (ValueError, KeyError, AttributeError, zipfile.BadZipFile):
            findings.append({'path': path, 'issue': 'invalid preparation assets'})
    return findings


def audit(paths, contract=None):
    contract = Path(contract) if contract else Path(__file__).with_name('native_ui_resources.json')
    resources = json.loads(contract.read_text())['resources']
    forbidden = {record['sha256']: name for name, record in resources.items()}
    findings = []
    count = 0
    total = 0

    def visit(data, name, depth):
        nonlocal count, total
        count += 1
        total += len(data)
        if total > 3 * 1024**3:
            raise ValueError('Release archive exceeds audit expansion limit')
        digest = hashlib.sha256(data).hexdigest()
        if digest in forbidden:
            findings.append({'path': name, 'issue': 'private legacy UI resource',
                             'resource': forbidden[digest], 'sha256': digest})
        lower = name.lower()
        if lower.endswith(('.cci', '.3ds', '.cia', '.romfs', '.keystore', '.jks', '.p12', '.sav', '.state')):
            findings.append({'path': name, 'issue': 'game, save or signing file'})
        if any(token in lower for token in ('/privategame/', 'libtriaevum_title_aot.so', 'triaevum_title_aot.dll')):
            findings.append({'path': name, 'issue': 'private generated title content'})
        is_tar = lower.endswith(('.tar', '.tar.gz', '.tgz', '.tar.xz'))
        if data[:4] != b'PK\x03\x04' and not is_tar:
            return
        if depth >= 5:
            raise ValueError('Release archive nesting exceeds audit limit')
        if is_tar:
            with tarfile.open(fileobj=io.BytesIO(data), mode='r:*') as archive:
                seen = set()
                for entry in archive:
                    path = PurePosixPath(entry.name)
                    if (entry.name in seen or path.is_absolute() or '..' in path.parts or
                            '\\' in entry.name or not (entry.isfile() or entry.isdir())):
                        raise ValueError('Unsafe, linked or duplicate release archive path')
                    seen.add(entry.name)
                    if entry.size > 512 * 1024**2:
                        raise ValueError('Release archive entry exceeds audit limit')
                    if entry.isfile():
                        if total + entry.size > 3 * 1024**3:
                            raise ValueError('Release archive exceeds audit expansion limit')
                        visit(archive.extractfile(entry).read(), name + '/' + entry.name, depth + 1)
            return
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            findings.extend(preparation_findings(archive, name))
            seen = set()
            for entry in archive.infolist():
                path = PurePosixPath(entry.filename)
                if entry.filename in seen or path.is_absolute() or '..' in path.parts or '\\' in entry.filename:
                    raise ValueError('Unsafe or duplicate release archive path')
                seen.add(entry.filename)
                if entry.file_size > 512 * 1024**2:
                    raise ValueError('Release archive entry exceeds audit limit')
                if not entry.is_dir():
                    visit(archive.read(entry), name + '/' + entry.filename, depth + 1)

    for source in map(Path, paths):
        visit(source.read_bytes(), source.name, 0)
    return {'status': 'FAIL' if findings else 'PASS', 'files_checked': count,
            'findings': findings,
            'scope': 'Known private fixtures, file types, and preparation manifest integrity; independent license, shader, signature and privacy checks remain required.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archives', nargs='+', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    result = audit(args.archives)
    text = json.dumps(result, indent=2) + '\n'
    if args.report:
        args.report.write_text(text)
    print(text)
    raise SystemExit(0 if result['status'] == 'PASS' else 1)
