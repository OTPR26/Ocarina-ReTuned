import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from stage_runtime import stage_runtime, digest


class RetentionTests(unittest.TestCase):
    def test_relocation_reuse_and_original_build_removal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root/'build'; source.mkdir()
            for name, data in {'code.bin': b'code', 'romfs.bin': b'private game resources',
                               'seed.json': b'{}', 'game.dylib': b'module'}.items():
                (source/name).write_bytes(data)
            layout = {'schema': 1, 'symbols': {}}
            manifest = {'source': {'code_bin_path': 'code.bin',
                'code_bin_sha256': digest(source/'code.bin'), 'romfs_image_path': 'romfs.bin'},
                'randomizer_proof': {'schema': 1, 'extended_save_size': 1244,
                    'activation_allowed': False, 'seed_layout': layout,
                    'seed_file': 'seed.json', 'seed_sha256': digest(source/'seed.json')}}
            (source/'manifest.json').write_text(json.dumps(manifest))
            binding = {'format': 'retuned-randomizer-module-v2',
                'code_sha256': digest(source/'code.bin'), 'module_sha256': digest(source/'game.dylib'),
                'seed_layout_sha256': hashlib.sha256(json.dumps(layout, sort_keys=True, separators=(',', ':')).encode()).hexdigest()}
            (source/'game.dylib.randomizer.json').write_text(json.dumps(binding))
            destination = root/'data'
            with self.assertRaises(ValueError):
                stage_runtime(source/'manifest.json', source/'game.dylib', destination)
            self.assertFalse(destination.exists())
            result = stage_runtime(source/'manifest.json', source/'game.dylib', destination, True)
            files = {p.relative_to(destination): (p.stat().st_mtime_ns, digest(p))
                     for p in destination.rglob('*') if p.is_file()}
            self.assertEqual(result, stage_runtime(source/'manifest.json', source/'game.dylib', destination, True))
            self.assertEqual(files, {p.relative_to(destination): (p.stat().st_mtime_ns, digest(p))
                     for p in destination.rglob('*') if p.is_file()})
            shutil.rmtree(source)
            retained = Path(result['manifest'])
            restored = json.loads(retained.read_text())
            self.assertEqual((retained.parent/restored['source']['code_bin_path']).read_bytes(), b'code')
            self.assertEqual((retained.parent/restored['source']['romfs_image_path']).read_bytes(), b'private game resources')
            self.assertEqual(Path(result['module']).read_bytes(), b'module')
            self.assertNotIn(str(source), retained.read_text())
            self.assertFalse(list(destination.rglob('.pending-*')))


if __name__ == '__main__':
    unittest.main()
