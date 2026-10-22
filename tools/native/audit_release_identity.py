#!/usr/bin/env python3
"""Scan release archives using private identity markers supplied outside source."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import stat
import tarfile
import zipfile


def audit(paths, markers):
    patterns = []
    for record in markers:
        value = record['value']
        if len(value) < 5:
            raise ValueError('Identity markers must contain at least five characters')
        for encoding in ('utf-8', 'utf-16le', 'utf-16be'):
            patterns.append((record['label'], value.encode(encoding).lower()))
    findings, archives = [], []
    count = total = 0

    def safe_name(name):
        for record in markers:
            name = re.sub(re.escape(record['value']), '[redacted]', name, flags=re.I)
        return name

    def check_path(name):
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or '\\' in name:
            raise ValueError('Unsafe archive path')

    def visit(data, name, depth):
        nonlocal count, total
        count += 1
        total += len(data)
        if total > 4 * 1024**3 or depth > 6:
            raise ValueError('Identity audit expansion limit exceeded')
        folded = data.lower()
        folded_name = name.encode().lower()
        labels = sorted({label for label, needle in patterns
                         if needle in folded or needle in folded_name})
        del folded
        if labels:
            findings.append({'path': safe_name(name), 'issue': 'personal identity marker',
                             'marker_labels': labels})
        low = name.lower()
        if low.endswith(('.mobileprovision', '.provisionprofile', '.p12', '.pfx', '.jks', '.keystore')):
            findings.append({'path': safe_name(name), 'issue': 'signing profile or key material'})
        for header in re.finditer(rb'-----BEGIN ([A-Z ]*PRIVATE KEY)-----', data):
            end = data.find(b'-----END ' + header[1] + b'-----',
                            header.end(), header.end() + 65536)
            if end < 0:
                continue
            try:
                decoded = base64.b64decode(b''.join(data[header.end():end].split()), validate=True)
            except ValueError:
                continue
            # Libraries can contain PEM parser delimiters without a key. Check
            # for a complete encoded ASN.1/OpenSSH payload before flagging it.
            if len(decoded) >= 32 and (decoded.startswith(b'\x30') or
                                       decoded.startswith(b'openssh-key-v1\0')):
                findings.append({'path': safe_name(name), 'issue': 'private key material'})
                break
        if data.startswith(b'PK\x03\x04'):
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                seen = set()
                for entry in archive.infolist():
                    check_path(entry.filename)
                    if entry.filename in seen or entry.flag_bits & 1:
                        raise ValueError('Duplicate or encrypted archive entry')
                    seen.add(entry.filename)
                    if entry.file_size > 600 * 1024**2 or total + entry.file_size > 4 * 1024**3:
                        raise ValueError('Identity audit entry limit exceeded')
                    if entry.is_dir():
                        continue
                    payload = archive.read(entry)
                    if stat.S_ISLNK(entry.external_attr >> 16):
                        target = payload.decode('utf-8')
                        # Internal framework links are valid; links escaping the
                        # archive are not. Resolve lexically without extracting.
                        parts = list(PurePosixPath(entry.filename).parent.parts)
                        if target.startswith('/'):
                            raise ValueError('Absolute archive link')
                        for part in PurePosixPath(target).parts:
                            if part == '..':
                                if not parts:
                                    raise ValueError('Escaping archive link')
                                parts.pop()
                            elif part != '.':
                                parts.append(part)
                    visit(payload, name + '/' + entry.filename, depth + 1)
        elif low.endswith(('.tar', '.tar.gz', '.tgz', '.tar.xz')):
            with tarfile.open(fileobj=io.BytesIO(data), mode='r:*') as archive:
                seen = set()
                for entry in archive:
                    check_path(entry.name)
                    if entry.name in seen or not (entry.isfile() or entry.isdir()):
                        raise ValueError('Duplicate, linked or unsupported tar entry')
                    seen.add(entry.name)
                    if entry.size > 600 * 1024**2 or total + entry.size > 4 * 1024**3:
                        raise ValueError('Identity audit entry limit exceeded')
                    if entry.isfile():
                        visit(archive.extractfile(entry).read(), name + '/' + entry.name, depth + 1)

    for path in map(Path, paths):
        data = path.read_bytes()
        before = len(findings)
        visit(data, path.name, 0)
        archives.append({'file': path.name, 'sha256': hashlib.sha256(data).hexdigest(),
                         'findings': len(findings) - before})
    return {'status': 'FAIL' if findings else 'PASS', 'files_checked': count,
            'archives': archives, 'findings': findings,
            'scope': 'Explicit identity markers in UTF-8/UTF-16, profiles and private keys. '
                     'Not a claim that all possible identifying information has been detected.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archives', nargs='+', type=Path)
    parser.add_argument('--markers', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    result = audit(args.archives, json.loads(args.markers.read_text())['markers'])
    args.report.write_text(json.dumps(result, indent=2) + '\n')
    print(result['status'], 'files:', result['files_checked'], 'findings:', len(result['findings']))
    raise SystemExit(result['status'] != 'PASS')
