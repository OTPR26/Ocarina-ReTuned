"""On-demand conversion in the isolated Android model-import process."""
from pathlib import Path
import sys


def change(kit_path, data_root, internal_root, package, age, use_imported=False):
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(Path(kit_path) / 'project/tools/native'))
    from player_models.install import change as install
    return bool(install(data_root, age=age, package=package, use_imported=use_imported, transaction_root=internal_root) is not None)
