"""One settings file for startup and gameplay consumers."""
import copy
import json
import os
import sys
import tempfile
from pathlib import Path

DEFAULTS = {
    'schema': 1, 'language': 'en', 'rom': None, 'texture_folder': None,
    'bindings': {'item_i': 'left_shoulder', 'item_ii': 'right_shoulder',
                 'target': 'left_trigger', 'shield': 'right_trigger'},
}


def data_root():
    if sys.platform == 'darwin':
        return Path.home() / 'Library/Application Support/Ocarina ReTuned'
    if sys.platform == 'win32':
        return Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'Ocarina ReTuned'
    return Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'ocarina-retuned'


class Settings:
    def __init__(self, root=None):
        self.root = Path(root) if root is not None else data_root()
        self.path = self.root / 'settings.json'

    def read(self):
        result = copy.deepcopy(DEFAULTS)
        if self.path.exists():
            saved = json.loads(self.path.read_text())
            if not isinstance(saved, dict) or saved.get('schema') != 1:
                raise ValueError('Unsupported settings format; existing file was preserved.')
            bindings = saved.get('bindings', {})
            if not isinstance(bindings, dict):
                raise ValueError('Invalid controller bindings; existing file was preserved.')
            result.update(saved)
            result['bindings'] = {**DEFAULTS['bindings'], **bindings}
        return result

    def update(self, changes):
        result = self.read()
        changes = copy.deepcopy(changes)
        if 'schema' in changes:
            raise ValueError('Settings schema cannot be changed through an editor.')
        if 'bindings' in changes:
            result['bindings'].update(changes.pop('bindings'))
        result.update(changes)
        if result['language'] not in {'en', 'fr', 'es'}:
            raise ValueError('Unsupported game language.')
        self.root.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix='.settings-', dir=self.root)
        try:
            with os.fdopen(fd, 'w') as stream:
                json.dump(result, stream, indent=2)
                stream.write('\n')
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.path)
        finally:
            Path(name).unlink(missing_ok=True)
        return result
