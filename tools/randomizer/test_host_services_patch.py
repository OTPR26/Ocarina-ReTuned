from pathlib import Path
import tempfile
import unittest
from apply_host_services import apply, BASE


class HostPatch(unittest.TestCase):
    def tree(self, root):
        directory=root/BASE
        directory.mkdir(parents=True)
        (directory/'oot3d_native_a32_ctr_host.h').write_text('struct NativeA32CtrHostConfig {\n};\n')
        (directory/'oot3d_native_a32_ctr_host.cpp').write_text('    switch (immediate) {\n    case 0x01:\n')
        (directory/'oot3d_native_a32_ctr_host_fs.cpp').write_text('            bool success = false;\n            uint32_t written = 0U;\n')
        (directory/'oot3d_native_a32_window_setup.cpp').write_text(
            'RetunedSaveSyncConfigure(saveDataDirectory.string().c_str());\n'
            'hostConfig.SaveDataCommitted=[] {RetunedSaveSyncCommitted();};\n')
        return directory

    def test_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);directory=self.tree(root)
            apply(root)
            first={p.name:p.read_bytes() for p in directory.iterdir()}
            apply(root)
            self.assertEqual(first,{p.name:p.read_bytes() for p in directory.iterdir()})
            self.assertIn(b'WriteRandomizerSave',first['oot3d_native_a32_ctr_host_fs.cpp'])
            setup=first['oot3d_native_a32_window_setup.cpp']
            self.assertIn(b'hostConfig.RandomizerSvc ? nullptr',setup)
            self.assertIn(b'if(!hostConfig.RandomizerSvc) hostConfig.SaveDataCommitted',setup)

    def test_unknown_host_aborts_before_any_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);directory=self.tree(root)
            (directory/'oot3d_native_a32_ctr_host_fs.cpp').write_text('new implementation\n')
            before={p.name:p.read_bytes() for p in directory.iterdir()}
            with self.assertRaises(ValueError):apply(root)
            self.assertEqual(before,{p.name:p.read_bytes() for p in directory.iterdir()})

if __name__=='__main__':unittest.main()
