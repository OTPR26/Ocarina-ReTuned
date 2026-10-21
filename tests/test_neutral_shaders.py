import importlib.util
from pathlib import Path
import tempfile
import unittest

path = Path(__file__).resolve().parents[1] / 'tools/native/apply_neutral_shaders.py'
spec = importlib.util.spec_from_file_location('neutral_shader_port', path)
port = importlib.util.module_from_spec(spec)
spec.loader.exec_module(port)


class NeutralShaderTests(unittest.TestCase):
    def test_title_tables_are_removed_and_user_shader_translation_remains(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            frontend = root / 'tools/oot3d/native_pica_frontend'
            frontend.mkdir(parents=True)
            (root / 'CMake/oot3d').mkdir(parents=True)
            startup = root / 'tools/oot3d/native_game_runtime/oot3d_native_a32_window_setup.cpp'
            startup.parent.mkdir(parents=True)
            startup.write_text('''  if (programPreparation != nullptr &&
      (launch.PicaParametricTev || alwaysAvailablePrograms)) {
    programPreparation->PrepareNativePicaPrograms(
        Oot3dNativeGame::NativePicaVertexProgramFamily());
  }
''')
            shader = frontend / 'oot3d_native_pica_shader_gen.cpp'
            shader.write_text('#include "oot3d_translated_vertex_programs.h"\n    if (requireTranslatedProgram) {\n kTranslatedVertexPrograms;\n }\n    if (body.empty()) {\n        SetError(error, "PICA vertex program could not be decompiled");\n    }\n')
            for name in ('oot3d_translated_vertex_programs.h', 'oot3d_native_vertex.spvpack'):
                (frontend / name).write_bytes(b'private test sentinel')
            cmake = root / 'CMake/oot3d/pica.cmake'
            cmake.write_text(''.join('triaevum_add_spirv_pack('+target+'\n tools/oot3d/native_pica_frontend/oot3d_native_vertex_binaries.cpp\n tools/oot3d/native_pica_frontend/oot3d_native_vertex.spvpack)\n' for target in ('one','two','three')))
            port.apply(root)
            first = shader.read_text()
            self.assertIn('GLSL::DecompileProgram(', first)
            self.assertIn('packet.VertexShader.Program.Values()', first)
            self.assertNotIn('kTranslatedVertexPrograms', first)
            self.assertFalse((frontend / 'oot3d_native_vertex.spvpack').exists())
            self.assertFalse((frontend / 'oot3d_translated_vertex_programs.h').exists())
            self.assertEqual(cmake.read_text().count('target_sources('), 3)
            self.assertIn('!Oot3dNativeGame::NativePicaVertexProgramFamily().empty()', startup.read_text())
            port.apply(root)
            self.assertEqual(shader.read_text(), first)
