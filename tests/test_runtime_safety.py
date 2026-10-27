"""Run buffer-allocation failures through the pinned runtime's actual methods."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('runtime_safety', ROOT / 'tools/native/apply_runtime_safety.py')
safety = importlib.util.module_from_spec(spec)
spec.loader.exec_module(safety)
BASE = '17218b0cfdb944645bb5cde5249f313dca7e53ce'
ENGINE = Path(os.environ.get('RETUNED_RUNTIME_ROOT', ROOT / 'work/reference/triaevum'))
GPU = 'runtime/three_ds_recomp/src/fast/oot3d/'
CASES = (
    ('grass_gpu_instance_compactor.cpp', '    bool EnsureBuffer(', '    void DestroyBuffer(',
     'probe.EnsureBuffer(buffer, 128, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT, false)', 'probe.DestroyBuffer(buffer)'),
    ('grass_gpu_selection.cpp', '    bool EnsureBuffer(', '    void DestroyBuffer(',
     'probe.EnsureBuffer(buffer, 128, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT, false)', 'probe.DestroyBuffer(buffer)'),
    ('grass_shadow_grid_pass.cpp', '    void Ensure(', '    void Destroy(',
     'probe.Ensure(buffer, 128, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT, true)', 'probe.Destroy(buffer)'),
    ('interactive_grass_pass.cpp', '    void EnsureBuffer(', '    void DestroyBuffer(',
     'probe.EnsureBuffer(buffer, 128, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT, 4096)', 'probe.DestroyBuffer(buffer)'),
)


@unittest.skipUnless((ENGINE / '.git').exists(), 'requires the pinned runtime checkout')
class RuntimeSafetyTests(unittest.TestCase):
    def sources(self, root):
        names = {GPU + case[0] for case in CASES}
        for patch in (ROOT / 'tools/native/upstream').glob('*.patch'):
            names.update(line[6:] for line in patch.read_text().splitlines() if line.startswith('+++ b/'))
        for name in names:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(subprocess.check_output(['git', '-C', str(ENGINE), 'show', BASE + ':' + name]))

    def test_backports_preserve_unrelated_changes_and_are_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.sources(root)
            path = root / 'runtime/three_ds_recomp/src/ship/Context.cpp'
            path.write_text(path.read_text() + '\n// Local platform adaptation.\n')
            safety.apply(root)
            first = {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            safety.apply(root)
            self.assertEqual(first, {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()})
            self.assertTrue(path.read_text().endswith('// Local platform adaptation.\n'))

    def test_actual_gpu_creation_methods_cleanup_on_failure(self):
        compiler = shutil.which('c++')
        header = Path(os.environ.get('RETUNED_VULKAN_INCLUDE', '/opt/homebrew/include'))
        if not compiler or not (header / 'vulkan/vulkan.h').is_file():
            self.skipTest('requires a C++20 compiler and Vulkan headers')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.sources(root)
            baseline = {name: (root / (GPU + name)).read_text() for name, *_ in CASES}
            safety.apply(root)
            template = (ROOT / 'tests/gpu_allocation_failure.cpp.inc').read_text()
            for name, ensure, destroy, call, cleanup in CASES:
                def fixture(source):
                    methods = []
                    for signature in (destroy, ensure):
                        start = source.index(signature)
                        methods.append(source[start:safety.function_end(source, start)])
                    return template.replace('// ACTUAL_METHODS', '\n'.join(methods)).replace(
                        '/* ENSURE_BUFFER */', call).replace('/* DESTROY_BUFFER */', cleanup)
                for label, source in [('before', baseline[name]), ('after', (root / (GPU + name)).read_text())]:
                    with self.subTest(buffer=name, version=label):
                        path = root / (name + '.' + label + '.cpp')
                        path.write_text(fixture(source))
                        executable = path.with_suffix('')
                        compiled = subprocess.run([compiler, '-std=c++20', '-I', str(header), str(path), '-o', str(executable)],
                                                  capture_output=True, text=True)
                        self.assertEqual(compiled.returncode, 0, compiled.stderr)
                        result = subprocess.run([str(executable)], capture_output=True, text=True)
                        if label == 'before':
                            self.assertNotEqual(result.returncode, 0)
                            self.assertIn('partial buffer', result.stderr)
                        else:
                            self.assertEqual(result.returncode, 0, result.stderr)
