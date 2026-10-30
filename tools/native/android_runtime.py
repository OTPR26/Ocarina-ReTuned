"""Check C++ symbol compatibility before packaging Android libraries."""
from pathlib import Path
import re
import struct


def dynamic_symbols(path):
    with Path(path).open('rb') as stream:
        header = stream.read(64)
        if len(header) != 64 or header[:6] != b'\x7fELF\x02\x01':
            raise ValueError('Expected a little-endian ELF64 library: ' + Path(path).name)
        offset = struct.unpack_from('<Q', header, 40)[0]
        size, count = struct.unpack_from('<HH', header, 58)
        if size != 64 or not count:
            raise ValueError('Missing ELF section table: ' + Path(path).name)
        stream.seek(offset)
        sections = list(struct.iter_unpack('<IIQQQQIIQQ', stream.read(size * count)))
        exports, imports = set(), set()
        for section in sections:
            if section[1] != 11:  # SHT_DYNSYM
                continue
            strings = sections[section[6]]
            stream.seek(strings[4])
            names = stream.read(strings[5])
            if section[9] != 24:
                raise ValueError('Invalid dynamic symbol table: ' + Path(path).name)
            stream.seek(section[4])
            for name, info, visibility, index, _, _ in struct.iter_unpack(
                    '<IBBHQQ', stream.read(section[5])):
                binding = info >> 4
                if not name or binding not in (1, 2):
                    continue
                symbol = names[name:names.index(b'\0', name)].decode('utf-8')
                if index and visibility & 3 in (0, 3):
                    exports.add(symbol)
                elif not index and binding == 1:
                    imports.add(symbol)
        if not any(section[1] == 11 for section in sections):
            raise ValueError('Missing dynamic symbols: ' + Path(path).name)
        return exports, imports


def verify_runtime(libraries):
    if 'libc++_shared.so' not in libraries or 'libTriAevum.so' not in libraries:
        raise ValueError('Missing Android host or C++ runtime')
    symbols = {name: dynamic_symbols(path) for name, path in libraries.items()}
    exports = set().union(*(item[0] for item in symbols.values()))
    # These unmangled ABI entry points are supplied by Android's libc.
    system = {'__cxa_atexit', '__cxa_finalize', '__cxa_thread_atexit_impl'}
    for name, (_, imports) in symbols.items():
        missing = sorted(symbol for symbol in imports - exports - system
                         if symbol.startswith(('__cxa_', '__gxx_', '_Unwind_'))
                         or re.match(r'_Z(?:N[KOR]?St|St|T[VIS]NSt|n[aw]|d[al])', symbol))
        if missing:
            raise ValueError('Android C++ runtime mismatch in ' + name + ': ' + ', '.join(missing))
