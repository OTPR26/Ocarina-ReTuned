#!/usr/bin/env python3
"""Keep title-derived shader tables out of the redistributable runtime.

The neutral GLSL decompiler translates shaders supplied by the user's title at
runtime. GPU drivers still compile the resulting GLSL/SPIR-V normally.
"""
from pathlib import Path
import re


def apply(root):
    root = Path(root)
    frontend = root / 'tools/oot3d/native_pica_frontend'
    source = frontend / 'oot3d_native_pica_shader_gen.cpp'
    text = source.read_text()
    text = text.replace('#include "oot3d_translated_vertex_programs.h"\n', '')
    start = text.find('    if (requireTranslatedProgram) {')
    if start != -1:
        end = text.index('    if (body.empty()) {\n        SetError(error, "PICA vertex program could not be decompiled");', start)
        text = text[:start] + '''    // ReTuned never embeds translated title shader bodies. The packet comes
    // from the user's locally prepared title; retain the generic decompiler.
    (void)requireTranslatedProgram;
    body = Pica::Shader::Generator::GLSL::DecompileProgram(
        packet.VertexShader.Program.Values(),
        packet.VertexShader.Swizzles.Values(),
        state.ShaderInterface.VertexMainOffset, InputRegisterName,
        OutputRegisterName, kAccuratePicaMultiplication);
''' + text[end:]
    if 'kTranslatedVertexPrograms' in text:
        raise ValueError('Embedded title shader lookup remains')
    source.write_text(text)
    (frontend / 'oot3d_native_vertex_binaries.cpp').write_text('''// Neutral host: title shader artifacts are generated from user-supplied data.
#include "oot3d_native_vertex_binaries.h"
namespace Oot3dNativeGame {
std::span<const Fast::Renderer3ds::PicaVertexArtifact> TitleVertexArtifacts() { return {}; }
std::span<const Fast::Renderer::PassShaderArtifact> TitlePassArtifacts() { return {}; }
}
''')
    cmake = root / 'CMake/oot3d/pica.cmake'
    text = cmake.read_text()
    pattern = r'triaevum_add_spirv_pack\((\S+)\s+tools/oot3d/native_pica_frontend/oot3d_native_vertex_binaries\.cpp\s+tools/oot3d/native_pica_frontend/oot3d_native_vertex\.spvpack\)'
    text, count = re.subn(pattern, r'target_sources(\1 PRIVATE tools/oot3d/native_pica_frontend/oot3d_native_vertex_binaries.cpp)', text)
    if count not in (0, 3):
        raise ValueError('Unexpected title pack CMake registrations')
    if 'oot3d_native_vertex.spvpack' in text:
        raise ValueError('Title shader pack build dependency remains')
    cmake.write_text(text)
    # Missing inputs expose accidental future embedding during a clean build.
    for name in ('oot3d_translated_vertex_programs.h', 'oot3d_native_vertex.spvpack'):
        (frontend / name).unlink(missing_ok=True)
