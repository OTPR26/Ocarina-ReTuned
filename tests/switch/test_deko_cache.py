import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[2] / 'tools/native/switch/deko_cache.py'
spec = importlib.util.spec_from_file_location('deko_cache', MODULE)
deko = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deko)

VERTEX = '''#version 450
layout(location=0) in vec4 position;
layout(set=0,binding=0,std140) uniform PicaVertexUniforms { vec4 shift; } params;
void main() { gl_Position = position + params.shift; }
'''
FRAGMENT = '''#version 450
layout(location=0) out vec4 color;
layout(set=0,binding=4,std140) uniform PicaFragmentUniforms { vec4 tint; } params;
layout(set=0,binding=1) uniform sampler2D tex0;
layout(set=0,binding=13) uniform usampler2D lut;
void main() { color = params.tint * texture(tex0, vec2(0)); }
'''


class DekoCacheCheck(unittest.TestCase):
    def test_six_stage_local_arrays_use_explicit_selections(self):
        source = '''#version 450
struct PicaTevProgram { uvec4 stages[6]; uvec4 control; };
struct PicaTevInputs { vec4 constants[6]; };
vec4 constant_at(PicaTevInputs inputs, int stage) { return inputs.constants[stage]; }
uvec4 stage_at(PicaTevProgram program, int stage) { return program.stages[stage]; }
'''
        converted, _ = deko.convert(source, 'frag')
        self.assertNotIn('[stage]', converted)
        for member in ('inputs.constants', 'program.stages'):
            for stage in range(6):
                self.assertIn(f'{member}[{stage}]', converted)
        self.assertEqual(deko.select_local_tev_arrays(converted), converted)
        other = source.replace('PicaTevProgram', 'OtherProgram').replace('PicaTevInputs', 'OtherInputs')
        self.assertEqual(deko.select_local_tev_arrays(other), other)
        four = source.replace('[6]', '[4]')
        self.assertEqual(deko.select_local_tev_arrays(four), four)
        vertex, _ = deko.convert(source, 'vert')
        self.assertIn('program.stages[stage]', vertex)

    def test_binding_maps_and_coordinate_policy(self):
        text, bindings = deko.convert(FRAGMENT, 'frag')
        self.assertNotIn('set=', text)
        self.assertIn('layout(binding=0, std140) uniform PicaFragmentUniforms', text)
        self.assertEqual([(b['kind'], b['binding'], b['slot']) for b in bindings],
                         [('sampler', 1, 0), ('sampler', 13, 1), ('ubo', 4, 0)])
        vertex, _ = deko.convert(VERTEX, 'vert')
        self.assertIn('gl_Position = position + params.shift;', vertex)

    def test_unsupported_interfaces_fail_clearly(self):
        for source in [FRAGMENT.replace('set=0','set=1'), VERTEX+'\nuniform float bad;\n',
                       FRAGMENT.replace('usampler2D', 'samplerCube'), VERTEX.replace('binding=0','binding=-1'),
                       VERTEX+'\nlayout(push_constant) uniform P {float x;} p;\n']:
            with self.subTest(source=source):
                with self.assertRaises(ValueError): deko.convert(source,'frag')
        with self.assertRaises(ValueError): deko.convert(VERTEX, 'comp')

    def test_duplicate_binding_rejected(self):
        with self.assertRaises(ValueError):deko.convert(FRAGMENT.replace('binding=13','binding=1'),'frag')

    def test_source_bound(self):
        with self.assertRaises(ValueError):deko.convert(VERTEX+' '*deko.MAX_SOURCE,'vert')

    def test_corrupt_truncated_and_stale_cache(self):
        metadata={'stage':'vert','compiler_sha256':'compiler-a'}
        binary=bytearray(512)
        struct.pack_into('<6I',binary,0,0x48534B44,24,256,256,24,1)
        struct.pack_into('<5I',binary,24,0,0,1,0,0)
        binary=bytes(binary)
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'test.rtshader'
            deko.store_record(p,metadata,binary);good=p.read_bytes()
            self.assertEqual(deko.load_record(p,metadata),binary)
            self.assertIsNone(deko.load_record(p,dict(metadata,compiler_sha256='compiler-b')))
            for data in [good[:8],good[:-1],good+b'x',good[:20]+bytes([good[20]^1])+good[21:],
                         struct.pack('<8sII',deko.MAGIC,deko.MAX_META+1,32)+b'\0'*32]:
                p.write_bytes(data);self.assertIsNone(deko.load_record(p,metadata))
            deko.store_record(p,metadata,binary)
            self.assertEqual(deko.load_record(p,metadata),binary)
            self.assertEqual(list(Path(folder).glob('*.new')),[])

    def test_dksh_offsets_and_stage(self):
        binary=bytearray(512)
        struct.pack_into('<6I',binary,0,0x48534B44,24,256,256,24,1)
        struct.pack_into('<5I',binary,24,0,0,1,0,0)
        self.assertTrue(deko.valid_dksh(binary,'vert'))
        self.assertFalse(deko.valid_dksh(binary,'frag'))
        struct.pack_into('<I',binary,28,256)
        self.assertFalse(deko.valid_dksh(binary,'vert'))
        struct.pack_into('<I',binary,28,0)
        struct.pack_into('<I',binary,16,250)
        self.assertFalse(deko.valid_dksh(binary,'vert'))

    def test_warm_hit_never_runs_compiler(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder);compiler=folder/'uam';compiler.write_bytes(b'compiler identity only')
            metadata={'schema':1,'policy':deko.POLICY,'tool_sha256':deko.digest(MODULE.read_bytes()),
                      'compiler_sha256':'test-id','compat_sha256':None,'stage':'vert',
                      'source_sha256':deko.digest(VERTEX.encode()),
                      'converted_sha256':deko.digest(deko.convert(VERTEX,'vert')[0].encode()),
                      'bindings':deko.convert(VERTEX,'vert')[1]}
            binary=bytearray(512);struct.pack_into('<6I',binary,0,0x48534B44,24,256,256,24,1)
            struct.pack_into('<5I',binary,24,0,0,1,0,0)
            deko.store_record(folder/(deko.digest(deko.encoded(metadata))+'.rtshader'),metadata,bytes(binary))
            with patch.object(deko.subprocess,'run',side_effect=AssertionError('compiler called on cache hit')):
                result=deko.compile_stage(VERTEX,'vert',compiler,folder,'test-id')
            self.assertTrue(result['cache_hit']);self.assertEqual(result['compiler_invocations'],0)

    def test_invalid_compiler_output_not_cached(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'bad.rtshader'
            with self.assertRaises(ValueError):deko.store_record(p,{},b'not a module')
            self.assertFalse(p.exists())


if __name__ == '__main__':unittest.main()
