import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/native'))
from player_models.reader import select, skeleton, unpack, LIMIT


class PlayerModelPackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def package(self, entries):
        path = self.root / 'model.pak'
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, data in entries.items():
                archive.writestr(name, data)
        return path

    def test_selects_oot_age_without_running_package_scripts(self):
        manifest = {'zzplayas': {'MM': {'child_model': [{'file': 'mm.zobj'}]},
                                'OOT': {'child_model': [{'file': 'child.zobj'}],
                                        'adult_model': [{'file': 'adult.zobj'}]}}}
        path = self.package({'package.json': json.dumps(manifest), 'mm.zobj': b'mm',
                             'child.zobj': b'child', 'adult.zobj': b'adult',
                             'ootscript.js': 'throw new Error("must not execute");'})
        self.assertEqual(select(path, age='child')[:2], ('child.zobj', b'child'))
        self.assertEqual(select(path, age='adult')[:2], ('adult.zobj', b'adult'))

    def test_does_not_substitute_wrong_age_or_game(self):
        path = self.package({'package.json': json.dumps({'zzplayas': {'MM': {
            'child_model': [{'file': 'only.zobj'}]}}}), 'only.zobj': b'model'})
        with self.assertRaisesRegex(ValueError, 'matching OoT model'):
            select(path, age='adult')

    def test_rejects_traversal_links_and_expansion_bombs(self):
        for name in ('../outside', '/absolute', 'C:/outside', 'folder/../../outside'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                unpack(self.package({name: b'x', 'model.zobj': b'model'}))
        path = self.root / 'link.pak'
        with zipfile.ZipFile(path, 'w') as archive:
            entry = zipfile.ZipInfo('model.zobj'); entry.external_attr = 0o120777 << 16
            archive.writestr(entry, 'outside')
        with self.assertRaises(ValueError): unpack(path)
        path = self.package({'large': bytes(LIMIT + 1)})
        with self.assertRaises(ValueError): unpack(path)
        self.assertFalse((self.root / 'outside').exists())

    def test_ambiguous_entries_and_bad_manifests_fail_clearly(self):
        path = self.package({'a/model.zobj': b'a', 'b/model.zobj': b'b'})
        with self.assertRaisesRegex(ValueError, 'ambiguous'): select(path, 'model.zobj')
        for bad in ([], {'zzplayas': []}, {'zzplayas': {'OOT': []}}):
            path = self.package({'package.json': json.dumps(bad), 'model.zobj': b'x'})
            with self.assertRaises(ValueError): select(path, age='child')

    def test_rejects_truncated_or_nonhuman_skeletons(self):
        for data in (b'', bytes(0x5018), b'x' * 0x6000):
            with self.assertRaises(ValueError): skeleton(data)
        data = bytearray(0x5100); data[0x5000:0x500b] = b'MODLOADER64'
        data[0x500b] = 3
        with self.assertRaisesRegex(ValueError, 'unsupported rig'): skeleton(data)

    def test_direct_model_is_read_as_data_only(self):
        path = self.root / 'model.zobj'; path.write_bytes(b'model')
        self.assertEqual(select(path)[:2], ('model.zobj', b'model'))
        document = self.root / 'document.pak'
        document.write_bytes(bytes(0x5000) + b'MODLOADER64' + bytes(32))
        self.assertEqual(select(document)[0], 'model.zobj')
        link = self.root / 'linked.zobj'; link.symlink_to(path)
        with self.assertRaises(ValueError): unpack(link)
