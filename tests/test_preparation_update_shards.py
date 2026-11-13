"""HUD edits preserve unrelated compiled-source cache keys."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/reframed'))
from apply_native_port import apply_update_sharding
ENGINE = Path(os.environ.get('RETUNED_RUNTIME_ROOT', ROOT / 'work/private/dual-screen-proof/android/engine'))
A32 = Path('tools/oot3d/native_a32_runtime')

@unittest.skipUnless((ENGINE / A32 / 'whole_aot_cpp.py').is_file(), 'Pinned translator unavailable')
class UpdateShards(unittest.TestCase):
    def test_injected_edit_preserves_game_sources_and_dispatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / A32 / 'whole_aot_cpp.py'
            target.parent.mkdir(parents=True)
            target.write_bytes((ENGINE / A32 / 'whole_aot_cpp.py').read_bytes())
            apply_update_sharding(root)
            once = target.read_bytes()
            apply_update_sharding(root)
            self.assertEqual(once, target.read_bytes())
            sys.path.insert(0, str(ENGINE / A32))
            self.addCleanup(sys.path.remove, str(ENGINE / A32))
            spec = importlib.util.spec_from_file_location('update_shard_fixture', target)
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            self.addCleanup(sys.modules.pop, spec.name, None)
            spec.loader.exec_module(module)
            entries = [0x1000+i*8 for i in range(256)] + [0x5C7000+i*8 for i in range(128)]
            code = bytearray(entries[-1]+8-0x1000)
            blocks, functions = [], []
            for i, entry in enumerate(entries):
                offset = entry-0x1000
                code[offset:offset+8] = bytes.fromhex('0100a0e31eff2fe1')
                blocks.append(dict(id=i, pc=entry, end_pc=entry+8, successors=[dict(site=entry+4, kind='return')]))
                functions.append(dict(entry=entry, name=f'Fixture_{entry:08X}', blocks=[i], closed_static_cfg=True, direct_calls=[], tail_calls=[], indirect_sites=[]))
            program = dict(format=module.PROGRAM_FORMAT, base=0x1000, blocks=blocks, functions=functions)
            inputs = root/'program.json', root/'selection.json', root/'code.bin'
            inputs[1].write_text(json.dumps(dict(format=module.SELECTION_FORMAT, functions=[dict(entry=x) for x in entries])))
            def generate(label, strategy):
                inputs[2].write_bytes(code)
                program['code_sha256'] = hashlib.sha256(code).hexdigest()
                inputs[0].write_text(json.dumps(program))
                output = root / label
                manifest = module.generate(*inputs, output, shard_count=64, shard_strategy=strategy)
                return output, manifest
            stable, stable_manifest = generate('stable', 'stable')
            before, before_manifest = generate('before', 'retuned-update')
            # Partitioning cannot alter the dispatch table, headers, or lowered functions.
            for name in (module.HEADER_NAME, module.INTERNAL_HEADER_NAME, module.SOURCE_NAME):
                self.assertEqual((stable/name).read_bytes(), (before/name).read_bytes())
            self.assertEqual(stable_manifest['functions'], before_manifest['functions'])
            for entry in entries[256:]:
                code[entry-0x1000] = 2
            stable_after, _ = generate('stable-after', 'stable')
            after, _ = generate('after', 'retuned-update')
            names = sorted(p.name for p in before.glob('*shard_*.cpp'))
            changed = [n for n in names if (before/n).read_bytes() != (after/n).read_bytes()]
            old_changed = [n for n in names if (stable/n).read_bytes() != (stable_after/n).read_bytes()]
            self.assertEqual(changed, names[56:])
            self.assertGreater(len(old_changed), 50)
            self.assertEqual((before/module.HEADER_NAME).read_bytes(), (after/module.HEADER_NAME).read_bytes())
            # All bucket sizes retain every function once, including boundary addresses.
            from types import SimpleNamespace
            values = tuple(SimpleNamespace(entry=e) for e in (0x1000, 0x5C6FFC, 0x5C7000, 0x600000))
            for count in (1, 2, 4, 64, 128):
                buckets = module._shard_buckets(values, count, 'retuned-update')
                self.assertEqual(len(buckets), count)
                self.assertEqual(sorted(x.entry for bucket in buckets for x in bucket), sorted(x.entry for x in values))
