"""Install the shared NRI object-destruction lifetime correction."""
from pathlib import Path
import shutil


def apply(root):
    base = Path(root) / 'runtime/three_ds_recomp'
    patch = 'nri_destroy_lifetime.cmake'
    shutil.copy2(Path(__file__).with_name(patch), base / 'cmake/patches' / patch)
    cmake = base / 'CMakeLists.txt'
    source = cmake.read_text()
    anchor = '-P ${CMAKE_CURRENT_SOURCE_DIR}/cmake/patches/oot3d_nri_storage_view_sampled.cmake'
    if patch in source:
        if source.count(patch) != 2:
            raise ValueError('Unexpected NRI lifetime patch registration')
        return
    if source.count(anchor) != 2:
        raise ValueError('NRI dependency patch context changed')
    for source_dir in ('${THREE_DS_RECOMP_NRI_SOURCE_DIR}', '<SOURCE_DIR>'):
        position = source.index(anchor)
        replacement = anchor + '\n\t\t\t\tCOMMAND ${CMAKE_COMMAND}\n\t\t\t\t\t-DNRI_SOURCE_DIR=' + source_dir + '\n\t\t\t\t\t-P ${CMAKE_CURRENT_SOURCE_DIR}/cmake/patches/' + patch
        # Advance past the first patched occurrence for the second variant.
        if source_dir == '<SOURCE_DIR>':
            position = source.index(anchor, source.index(patch) + len(patch))
        source = source[:position] + source[position:].replace(anchor, replacement, 1)
    cmake.write_text(source)
