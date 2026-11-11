import importlib.util
import json
from pathlib import Path
import stat
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location('driver_package', Path(__file__).resolve().parents[1] / 'tools/native/android/driver_package.py')
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


class DriverPackageTests(unittest.TestCase):
    def archive(self, path, **changes):
        metadata = dict(schemaVersion=1, name='Test driver', minApi=29, libraryName='libtest.so')
        metadata.update(changes)
        elf = bytearray(64)
        elf[:6] = b'\x7fELF\x02\x01'
        elf[16:18] = (3).to_bytes(2, 'little')
        elf[18:20] = (183).to_bytes(2, 'little')
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr('meta.json', json.dumps(metadata))
            archive.writestr('libtest.so', elf)

    def test_install_and_repeat(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.archive(root / 'driver.zip')
            first = driver.install(root / 'driver.zip', root / 'drivers', 35)
            self.assertEqual(first, driver.install(root / 'driver.zip', root / 'drivers', 35))
            self.assertEqual([first['id']], [p.name for p in (root / 'drivers').iterdir()])

    def test_reject_traversal_without_install(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.archive(root / 'driver.zip')
            with zipfile.ZipFile(root / 'driver.zip', 'a') as archive:
                archive.writestr('../outside', b'bad')
            with self.assertRaises(ValueError):
                driver.install(root / 'driver.zip', root / 'drivers', 35)
            self.assertFalse((root / 'outside').exists())
            self.assertEqual([], list((root / 'drivers').iterdir()))

    def test_reject_incompatible_android(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.archive(root / 'driver.zip', minApi=36)
            with self.assertRaises(ValueError):
                driver.install(root / 'driver.zip', root / 'drivers', 35)
            self.assertEqual([], list((root / 'drivers').iterdir()))

    def test_damaged_existing_import_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.archive(root / 'driver.zip')
            result = driver.install(root / 'driver.zip', root / 'drivers', 35)
            library = root / 'drivers' / result['id'] / 'libtest.so'
            library.write_bytes(b'damaged')
            with self.assertRaises(ValueError):
                driver.install(root / 'driver.zip', root / 'drivers', 35)
            self.assertEqual(b'damaged', library.read_bytes())

    def test_accept_standard_driver_library_names(self):
        for library in ('vulkan.ad07xx.so', 'vulkan.mali.so', 'libvulkan_panfrost.so'):
            with self.subTest(library=library), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                self.archive(root / 'driver.zip')
                with zipfile.ZipFile(root / 'driver.zip') as source:
                    data = source.read('libtest.so')
                with zipfile.ZipFile(root / 'driver.zip', 'w') as archive:
                    archive.writestr('meta.json', json.dumps(dict(schemaVersion=1, minApi=29, libraryName=library)))
                    archive.writestr(library, data)
                result = driver.install(root/'driver.zip',root/'drivers',33)
                self.assertEqual(library, result['library'])
                self.assertEqual(data, (root/'drivers'/result['id']/library).read_bytes())

    def test_reject_symlink_and_special_file(self):
        for mode in (stat.S_IFLNK, stat.S_IFIFO, stat.S_IFCHR):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                self.archive(root/'driver.zip')
                with zipfile.ZipFile(root/'driver.zip', 'a') as archive:
                    info = zipfile.ZipInfo('extra'); info.external_attr = (mode | 0o600) << 16
                    archive.writestr(info, b'target')
                with self.assertRaises(ValueError): driver.install(root/'driver.zip',root/'drivers',33)
                self.assertEqual([], list((root/'drivers').iterdir()))

    def test_reject_wrong_architecture_without_install(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); self.archive(root/'driver.zip')
            with zipfile.ZipFile(root/'driver.zip') as archive:
                metadata=archive.read('meta.json'); elf=bytearray(archive.read('libtest.so'))
            elf[18:20]=(62).to_bytes(2,'little')
            with zipfile.ZipFile(root/'driver.zip','w') as archive:
                archive.writestr('meta.json',metadata);archive.writestr('libtest.so',elf)
            with self.assertRaises(ValueError):driver.install(root/'driver.zip',root/'drivers',33)
            self.assertEqual([],list((root/'drivers').iterdir()))
