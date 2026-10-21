"""Reject the pinned upstream's translated title shader payloads in public hosts."""
import re
from pathlib import Path
import subprocess


def verify(engine, binary):
    engine, binary = Path(engine), Path(binary)
    prefix = 'tools/oot3d/native_pica_frontend/'
    original_pack = subprocess.check_output(['git', '-C', str(engine), 'show', 'HEAD:' + prefix + 'oot3d_native_vertex.spvpack'])
    original_source = subprocess.check_output(['git', '-C', str(engine), 'show', 'HEAD:' + prefix + 'oot3d_translated_vertex_programs.h'])
    bodies = re.findall(rb'R"PICA_TITLE\((.*?)\)PICA_TITLE"', original_source, re.S)
    if len(bodies) != 3 or not original_pack:
        raise ValueError('Unexpected upstream shader audit baseline')
    contents = binary.read_bytes()
    if original_pack in contents or any(body in contents for body in bodies):
        raise ValueError('Translated title shader payload found in host: ' + binary.name)
    shader = (engine / prefix / 'oot3d_native_pica_shader_gen.cpp').read_text()
    if 'kTranslatedVertexPrograms' in shader or 'oot3d_translated_vertex_programs.h' in shader:
        raise ValueError('Embedded translated title shader source is enabled')
    if (engine / prefix / 'oot3d_native_vertex.spvpack').exists():
        raise ValueError('Title shader pack remains in neutral source tree')
