#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Host-only PICA-to-DKSH compiler/cache experiment. Generated output is private game data.

No renderer integration or GPU validation is implied by a successful compilation.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import struct
import subprocess
import tempfile
import time

MAX_SOURCE = 1024 * 1024
MAX_BINARY = 8 * 1024 * 1024
MAX_META = 64 * 1024
MAX_STAGES = 4096
MAGIC = b'RTDKSH01'
POLICY = 'pica-deko-bindings-v2;static-local-tev-arrays;origin-upper-left;depth-zero-to-one;canonical-clip-preserved'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def select_local_tev_arrays(source):
    """Avoid dynamic indexing of canonical six-stage, by-value TEV arrays.

    Explicit selections preserve every valid stage index (0..5) without the
    failing large-shader local-array lowering seen in the standalone GPU probe.
    Uniform arrays and unrelated shader structures are left alone.
    """
    arrays = (
        (r"struct\s+PicaTevProgram\s*\{[^}]*\buvec4\s+stages\s*\[\s*6\s*\]", "program.stages"),
        (r"struct\s+PicaTevInputs\s*\{[^}]*\bvec4\s+constants\s*\[\s*6\s*\]", "inputs.constants"),
    )
    for declaration, member in arrays:
        if re.search(declaration, source):
            selection = '(' + ''.join(f'stage == {i} ? {member}[{i}] : ' for i in range(5)) + member + '[5])'
            source = source.replace(member + '[stage]', selection)
    return source


def convert(source, stage):
    """Explicit per-stage UBO/sampler slots; no Cemu converter or title shader code."""
    if stage not in ('vert', 'frag'):
        raise ValueError('only vertex and fragment stages are supported')
    if len(source.encode()) > MAX_SOURCE or '\0' in source:
        raise ValueError('invalid or oversized source')
    if not re.match(r'\s*#version 450\s*\n', source):
        raise ValueError('expected canonical PICA GLSL450')
    if re.search(r'(?m)^\s*uniform\s', source):
        raise ValueError('standalone uniforms need an explicit uniform block')
    if any(t in source for t in ('gl_VertexIndex', 'gl_InstanceIndex', 'gl_ClipDistance', 'layout(push_constant')):
        raise ValueError('unsupported shader interface requires explicit conversion')
    if stage == 'frag':
        source = select_local_tev_arrays(source)
    pattern = re.compile(r'layout\(([^)]*)\)\s*uniform\s+(\w+)\s*(\{|\w+)')
    declarations = []
    seen = set()
    for match in pattern.finditer(source):
        fields = [f.strip() for f in match.group(1).split(',')]
        values = {}
        for field in fields:
            if '=' in field:
                key, value = map(str.strip, field.split('=', 1))
                if key not in ('set', 'binding') or not value.isdigit() or key in values:
                    raise ValueError('unsupported uniform layout')
                values[key] = int(value)
            elif field != 'std140':
                raise ValueError('unsupported block layout')
        if values.get('set') != 0 or 'binding' not in values:
            raise ValueError('expected descriptor set0 and explicit binding')
        kind = 'ubo' if match.group(3) == '{' else 'sampler'
        if kind == 'sampler' and match.group(2) not in ('sampler2D', 'usampler2D', 'isampler2D'):
            raise ValueError('unsupported sampled resource')
        if values['binding'] in seen:
            raise ValueError('duplicate descriptor binding')
        seen.add(values['binding'])
        declarations.append((match, kind, values['binding']))
    slots = {kind: {binding: slot for slot, binding in enumerate(sorted(b for _, k, b in declarations if k == kind))}
             for kind in ('ubo', 'sampler')}
    if len(slots['ubo']) > 16 or len(slots['sampler']) > 32:
        raise ValueError('deko3d per-stage resource limit exceeded')
    bindings = []
    result = source
    for match, kind, binding in reversed(declarations):
        slot = slots[kind][binding]
        tail = ', std140' if kind == 'ubo' else ''
        replacement = f'layout(binding={slot}{tail}) uniform {match.group(2)} {match.group(3)}'
        result = result[:match.start()] + replacement + result[match.end():]
        bindings.append({'kind': kind, 'set': 0, 'binding': binding, 'slot': slot, 'type': match.group(2)})
    if re.search(r'\bset\s*=', result) or re.search(r'(?m)^\s*(?:layout\([^\n]*\)\s*)?uniform\s+\w+\s+\w+\s*;', result):
        # Explicit samplers are valid; exclude those from the standalone-uniform check.
        stripped = re.sub(r'layout\([^)]*\)\s*uniform\s+[ui]?sampler2D\s+\w+\s*;', '', result)
        if re.search(r'\bset\s*=', stripped) or re.search(r'(?m)^\s*(?:layout\([^\n]*\)\s*)?uniform\s+\w+\s+\w+\s*;', stripped):
            raise ValueError('unconverted uniform interface')
    return result, sorted(bindings, key=lambda b: (b['kind'], b['binding']))


def valid_dksh(binary, stage=None):
    # Validate the documented DKSH container, not GPU instruction correctness.
    if not 512 <= len(binary) <= MAX_BINARY:
        return False
    magic, header, control, code, programs, count = struct.unpack('<6I', binary[:24])
    if magic != 0x48534B44 or header != 24 or count != 1 or control < 256 or code < 256:
        return False
    if control % 256 or code % 256 or control + code != len(binary) or programs < header or programs + 64 > control:
        return False
    kind, entry, _, const_offset, const_size = struct.unpack('<5I', binary[programs:programs+20])
    if kind not in (0, 1) or (stage is not None and kind != {'vert': 0, 'frag': 1}.get(stage)):
        return False
    return entry < code and const_offset <= code and const_size <= code - const_offset


def load_record(path, expected):
    try:
        size = path.stat().st_size
        if size < 48 or size > 16 + MAX_META + MAX_BINARY + 32:
            return None
        with path.open('rb') as stream:
            data = stream.read(16 + MAX_META + MAX_BINARY + 33)
        if len(data) != size:
            return None
        magic, meta_size, binary_size = struct.unpack('<8sII', data[:16])
        if magic != MAGIC or meta_size > MAX_META or binary_size > MAX_BINARY or size != 16 + meta_size + binary_size + 32:
            return None
        if hashlib.sha256(data[:-32]).digest() != data[-32:]:
            return None
        metadata = json.loads(data[16:16+meta_size])
        binary = data[16+meta_size:-32]
        if metadata != expected or not valid_dksh(binary, expected.get('stage')):
            return None
        return binary
    except (OSError, ValueError, UnicodeError, struct.error, RecursionError):
        return None


def store_record(path, metadata, binary):
    if not valid_dksh(binary, metadata.get('stage')):
        raise ValueError('compiler output is not a bounded DKSH module')
    meta = encoded(metadata)
    if len(meta) > MAX_META:
        raise ValueError('metadata exceeds bound')
    data = struct.pack('<8sII', MAGIC, len(meta), len(binary)) + meta + binary
    data += hashlib.sha256(data).digest()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name+'.', suffix='.new', delete=False) as f:
            temporary = Path(f.name); f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


class CompileFailure(ValueError):
    compiler_invocations = 1


def compile_stage(source, stage, compiler, cache, compiler_id, compat=None, timeout=60):
    original_hash = digest(source.encode())
    if compat:
        rewritten = subprocess.run([str(compat)], input=source, text=True, capture_output=True, timeout=timeout)
        if rewritten.returncode:
            raise ValueError('arithmetic rewrite failed: '+rewritten.stderr[:1000])
        source = rewritten.stdout
    translated, bindings = convert(source, stage)
    metadata = {'schema': 1, 'policy': POLICY, 'tool_sha256': digest(Path(__file__).read_bytes()),
                'compiler_sha256': compiler_id, 'compat_sha256': digest(compat.read_bytes()) if compat else None,
                'stage': stage, 'source_sha256': original_hash, 'converted_sha256': digest(translated.encode()), 'bindings': bindings}
    path = cache / (digest(encoded(metadata))+'.rtshader')
    previous = load_record(path, metadata)
    if previous is not None:
        return {'stage': stage, 'source_sha256': original_hash, 'cache_hit': True, 'compiler_invocations': 0,
                'cache_record': path.name, 'dksh_bytes': len(previous), 'dksh_sha256': digest(previous), 'bindings': bindings}
    started = time.monotonic()
    with tempfile.TemporaryDirectory(dir=cache) as folder:
        src = Path(folder)/'shader.glsl'; dest = Path(folder)/'shader.dksh'; src.write_text(translated)
        try:
            run = subprocess.run([str(compiler), '-s', stage, '-o', str(dest), str(src)], capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as error:
            raise CompileFailure('uam compilation timed out') from error
        log = (run.stdout+run.stderr)[:12000]
        # A malformed shader cannot turn an old result into a success.
        if run.returncode or not dest.exists():
            raise CompileFailure(f'uam {stage} failed (exit{run.returncode}): {log}')
        if dest.stat().st_size > MAX_BINARY:
            raise CompileFailure('compiler output exceeds bound')
        binary = dest.read_bytes()
    try:
        store_record(path, metadata, binary)
    except (ValueError, OSError) as error:
        raise CompileFailure(str(error)) from error
    return {'stage': stage, 'source_sha256': original_hash, 'cache_hit': False, 'compiler_invocations': 1,
            'cache_record': path.name, 'compile_seconds': time.monotonic()-started, 'dksh_bytes': len(binary), 'dksh_sha256': digest(binary),
            'bindings': bindings, 'compiler_log': log}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--compiler', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--compat-tool', type=Path)
    args = parser.parse_args()
    compiler = args.compiler.resolve(); compat = args.compat_tool.resolve() if args.compat_tool else None
    manifest = json.loads(args.manifest.read_text())
    entries = manifest['stages']
    if not entries or len(entries) > MAX_STAGES:
        raise ValueError('invalid stage count')
    args.cache.mkdir(parents=True, exist_ok=True)
    report = {'schema': 1, 'scope': 'host compilation/cache only; no GPU or gameplay validation', 'private_game_data': True,
              'compiler_sha256': digest(compiler.read_bytes()), 'results': [], 'failures': []}
    started = time.monotonic()
    for entry in entries:
        try:
            path = (args.manifest.parent/entry['file']).resolve()
            if not path.is_relative_to(args.manifest.parent.resolve()) or path.stat().st_size > MAX_SOURCE:
                raise ValueError('manifest source outside input root or exceeds bound')
            result = compile_stage(path.read_text(), entry['stage'], compiler, args.cache, report['compiler_sha256'], compat)
            report['results'].append(result)
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            report['failures'].append({'stage': entry.get('stage'), 'file': entry.get('file'), 'error': str(error), 'compiler_invocations': getattr(error, 'compiler_invocations', 0)})
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2)+'\n')
    report.update(seconds=time.monotonic()-started, compiler_invocations=sum(r['compiler_invocations'] for r in report['results'])+sum(f['compiler_invocations'] for f in report['failures']),
                  cache_hits=sum(r['cache_hit'] for r in report['results']), status='FAIL' if report['failures'] else 'PASS')
    args.report.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','seconds','compiler_invocations','cache_hits')}, indent=2))
    return 1 if report['failures'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
