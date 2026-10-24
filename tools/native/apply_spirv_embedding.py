"""Use bounded-memory binary embedding on Linux compilers without #embed."""
from pathlib import Path
import shutil


def apply(root):
    directory = Path(root) / 'runtime/three_ds_recomp/cmake'
    source = directory / 'spirv_pack.cmake'
    text = source.read_text()
    marker = 'include("${CMAKE_CURRENT_LIST_DIR}/spirv_pack_elf.cmake")'
    if marker not in text:
        before = 'function(triaevum_add_spirv_pack target source pack)'
        if text.count(before) != 1:
            raise ValueError('SPIR-V embedding function context changed')
        text = text.replace(before, 'function(retuned_literal_add_spirv_pack target source pack)')
        source.write_text(text + '\n' + marker + '\n')
    shutil.copy2(Path(__file__).with_name('spirv_pack_elf.cmake'), directory / 'spirv_pack_elf.cmake')
