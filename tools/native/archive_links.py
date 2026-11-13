"""Validate relative links without extracting a release archive."""
from collections import deque
from pathlib import PurePosixPath


def validate_tar_links(entries):
    members = {}
    for entry in entries:
        path = PurePosixPath(entry.name)
        name = str(path)
        if (path.is_absolute() or '..' in path.parts or '\\' in entry.name or
                name in members or not (entry.isfile() or entry.isdir() or entry.issym())):
            raise ValueError('Unsafe, duplicate, or unsupported tar entry')
        members[name] = entry
    links = {name: entry.linkname for name, entry in members.items() if entry.issym()}
    for name, entry in members.items():
        if any(str(parent) in links for parent in PurePosixPath(name).parents):
            raise ValueError('Archive entry is nested beneath a symbolic link')
        if not entry.issym():
            continue
        stack = list(PurePosixPath(name).parent.parts)
        pending = deque([entry.linkname])
        followed = 0
        while pending:
            target = pending.popleft()
            if not target or target.startswith('/') or '\\' in target:
                raise ValueError('Absolute or invalid archive link')
            parts = list(PurePosixPath(target).parts)
            for index, part in enumerate(parts):
                if part == '..':
                    if not stack:
                        raise ValueError('Archive link escapes its root')
                    stack.pop()
                elif part != '.':
                    stack.append(part)
                current = '/'.join(stack)
                if current in links:
                    followed += 1
                    if followed > 40:
                        raise ValueError('Cyclic archive link')
                    stack.pop()
                    if parts[index + 1:]:
                        pending.appendleft('/'.join(parts[index + 1:]))
                    pending.appendleft(links[current])
                    break
        if '/'.join(stack) not in members:
            raise ValueError('Archive link target is missing')
