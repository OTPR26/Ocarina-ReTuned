"""Backport reviewed runtime safety fixes without changing the pinned base."""
from pathlib import Path, PurePosixPath
import argparse


def function_end(source, start):
    opening = source.index('{', start)
    depth = 0
    for position in range(opening, len(source)):
        if source[position] == '{': depth += 1
        elif source[position] == '}':
            depth -= 1
            if depth == 0: return position + 1
    raise ValueError('Unterminated buffer creation function')


def allocation_rollback(source, signature, destroy):
    if source.count(signature) != 1:
        raise ValueError('GPU buffer creation function changed')
    start = source.index(signature)
    end = function_end(source, start)
    function = source[start:end]
    marker = '        // Allocation failures must leave this slot empty for the next frame.'
    if marker in function:
        return source
    anchor = '        ' + destroy + ';\n'
    if function.count(anchor) != 1:
        raise ValueError('GPU buffer cleanup context changed')
    position = function.index(anchor) + len(anchor)
    prefix = function[:position]
    body = function[position:function.rindex('\n    }')].rstrip('\n')
    body = '\n'.join('    ' + line if line else line for line in body.split('\n'))
    replacement = (prefix + marker + '\n        try {\n' + body + '\n'
        '        } catch (...) {\n            ' + destroy + ';\n'
        '            throw;\n        }\n    }')
    return source[:start] + replacement + source[end:]


def apply(root):
    root = Path(root)
    updates = {}

    def read(name):
        if name not in updates: updates[name] = (root / name).read_text()
        return updates[name]

    # Apply the checked-in, modified-file unified hunks by exact context. This
    # works with both Git checkouts and source archives, without touching refs.
    for patch in ('startup-cleanup.patch', 'dsp-cache-requests.patch'):
        lines = (Path(__file__).parent / 'upstream' / patch).read_text().splitlines(keepends=True)
        index, name = 0, None
        while index < len(lines):
            line = lines[index]
            if line.startswith('+++ b/'):
                name = line[6:].strip()
                path = PurePosixPath(name)
                if path.is_absolute() or '..' in path.parts:
                    raise ValueError('Invalid runtime patch path')
            elif line.startswith('@@ '):
                before, after = [], []
                index += 1
                while index < len(lines) and lines[index][:1] in (' ', '+', '-'):
                    part = lines[index]
                    if part[0] != '+': before.append(part[1:])
                    if part[0] != '-': after.append(part[1:])
                    index += 1
                before, after = ''.join(before), ''.join(after)
                if not name or not before or not after:
                    raise ValueError('Invalid runtime patch hunk')
                source = read(name)
                if after not in source:
                    if source.count(before) != 1:
                        raise ValueError('Runtime safety context changed: ' + name)
                    updates[name] = source.replace(before, after, 1)
                continue
            index += 1

    directory = 'runtime/three_ds_recomp/src/fast/oot3d/'
    for name, signature, destroy in (
        ('grass_gpu_instance_compactor.cpp', '    bool EnsureBuffer(', 'DestroyBuffer(buffer)'),
        ('grass_gpu_selection.cpp', '    bool EnsureBuffer(', 'DestroyBuffer(buffer)'),
        ('grass_shadow_grid_pass.cpp', '    void Ensure(', 'Destroy(buffer)'),
        ('interactive_grass_pass.cpp', '    void EnsureBuffer(', 'DestroyBuffer(slot)'),
    ):
        name = directory + name
        updates[name] = allocation_rollback(read(name), signature, destroy)

    for name, source in updates.items():
        path = root / name
        if path.read_text() != source: path.write_text(source)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('engine', type=Path)
    apply(parser.parse_args().engine)
