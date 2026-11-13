import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('linux_compiler_stage',
    Path(__file__).resolve().parents[1] / 'tools/native/stage_linux_compiler.py')
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


class LinuxCompilerStaging(unittest.TestCase):
    def fixture(self, root):
        triple = 'x86_64-linux-gnu'
        for name in (f'usr/bin/{triple}-gcc-13', f'usr/bin/{triple}-g++-13',
                     f'usr/bin/{triple}-as', f'usr/bin/{triple}-ld',
                     f'usr/libexec/gcc/{triple}/13/cc1plus',
                     'usr/include/c++/13/vector', 'usr/include/stdio.h',
                     f'usr/lib/{triple}/crt1.o', 'usr/share/doc/gcc-13/copyright'):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'\x7fELF\x02\x01' + b'\0' * 12 + b'\x3e\x00')
        receipts = root.parent / 'receipts.json'
        for name in stage.COMMON_LICENSES:
            path = root / 'usr/share/common-licenses' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('License fixture')
        receipts.write_text(json.dumps([{'package': 'gcc-13', 'version': '13.3',
                                        'source': 'gcc-13', 'sha256': 'a' * 64}]))
        return receipts

    def test_relocation_does_not_embed_the_staging_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'sysroot'
            receipts = self.fixture(root)
            output = root.with_name('tools')
            stage.stage(root, output, 'x86_64', receipts)
            wrapper = (output / 'bin/c++').read_text()
            self.assertNotIn(temporary, wrapper)
            self.assertIn('--sysroot="$root/sysroot"', wrapper)
            self.assertTrue((output / 'bin/ld').is_file())
            manifest = json.loads((output / 'toolchain-manifest.json').read_text())
            self.assertIn('sysroot/usr/share/doc/gcc-13/copyright', manifest['files'])
            moved = output.with_name('moved tools')
            output.rename(moved)
            self.assertTrue((moved / 'bin/ld').is_file())

    def test_external_link_is_rejected_before_copying(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'sysroot'
            receipts = self.fixture(root)
            (root / 'outside').symlink_to('/usr/include')
            with self.assertRaisesRegex(ValueError, 'escapes'):
                stage.stage(root, root.with_name('tools'), 'x86_64', receipts)
            self.assertFalse(root.with_name('tools').exists())

    def test_wrong_architecture_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'sysroot'
            receipts = self.fixture(root)
            (root / 'usr/bin/x86_64-linux-gnu-g++-13').write_bytes(
                b'\x7fELF\x02\x01' + b'\0' * 12 + b'\xb7\x00')
            with self.assertRaisesRegex(ValueError, 'architecture'):
                stage.stage(root, root.with_name('tools'), 'x86_64', receipts)

    def test_missing_runtime_link_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'sysroot'
            receipts = self.fixture(root)
            (root / 'usr/lib/missing.so').symlink_to('missing.so.1')
            with self.assertRaisesRegex(ValueError, 'target is missing'):
                stage.stage(root, root.with_name('tools'), 'x86_64', receipts)
