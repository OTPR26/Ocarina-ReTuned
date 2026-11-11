"""Streaming generation preserves source bytes and commits only complete output."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/reframed'))
from apply_native_port import apply_streaming_generation

ENGINE = Path(os.environ.get('RETUNED_RUNTIME_ROOT', ROOT / 'work/private/dual-screen-proof/android/engine'))
A32 = Path('tools/oot3d/native_a32_runtime')

@unittest.skipUnless((ENGINE / A32 / 'test_whole_aot_cpp.py').is_file(), 'Pinned translator fixture unavailable')
class StreamingGeneration(unittest.TestCase):
    def test_byte_identical_sources_progress_and_interruption(self):
        sys.path.insert(0, str(ENGINE / A32))
        import whole_aot_cpp as original
        from test_whole_aot_cpp import WholeAotCppTests
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / A32 / 'whole_aot_cpp.py'
            target.parent.mkdir(parents=True)
            target.write_text(Path(original.__file__).read_text())
            apply_streaming_generation(root)
            once = target.read_bytes()
            apply_streaming_generation(root)
            self.assertEqual(once, target.read_bytes())
            spec = importlib.util.spec_from_file_location('streaming_generator_test', target)
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            inputs = WholeAotCppTests().write_inputs(root, bytes.fromhex('0100a0e31eff2fe1'))
            for shards in (1, 4, 128):
                old = root / f'old-{shards}'
                new = root / f'new-{shards}'
                before = original.generate(*inputs, old, shard_count=shards)
                events = []
                after = module.generate(*inputs, new, shard_count=shards,
                    progress=lambda done, total: events.append((done, total)))
                self.assertEqual(before['files'], after['files'])
                for name in before['files']:
                    self.assertEqual((old / name).read_bytes(), (new / name).read_bytes())
                if shards > 1:
                    self.assertEqual(events, [(i, shards) for i in range(1, shards + 1)])
                module.generate(*inputs, new, shard_count=shards,
                    progress=lambda *_: self.fail('Valid cache should not regenerate'))
            interrupted = root / 'interrupted'
            def cancel(*_): raise RuntimeError('cancel fixture')
            with self.assertRaisesRegex(RuntimeError, 'cancel fixture'):
                module.generate(*inputs, interrupted, shard_count=4, progress=cancel)
            self.assertFalse((interrupted / module.MANIFEST_NAME).exists())
            self.assertEqual(module.generate(*inputs, interrupted, shard_count=4)['files'],
                             original.generate(*inputs, root / 'reference', shard_count=4)['files'])
