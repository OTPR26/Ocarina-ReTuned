import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/native'))
import region_inputs as regions
from preparation_cache import fingerprint
from rom_setup import launch_profile

spec = importlib.util.spec_from_file_location('region_romfs_fixture', ROOT / 'tests/test_ui_assets.py')
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)


class RegionalInputTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.pins = json.loads((ROOT / 'resources/native-inputs.json').read_text())

    def test_regional_cache_keys_and_exheaders_are_separate(self):
        usa_keys, usa = regions.input_plan(self.pins, 'USA')
        eur_keys, eur = regions.input_plan(self.pins, 'EUR')
        self.assertFalse(set(usa_keys) & set(eur_keys))
        self.assertEqual(usa['canonical-code.bin'], eur['canonical-code.bin'])
        self.assertNotEqual(usa['inputs/exheader.bin'], eur['inputs/exheader.bin'])
        self.assertNotEqual(usa['romfs.bin'], eur['romfs.bin'])
        other = json.loads(json.dumps(self.pins))
        other['inputs'][1]['romfs']['sha256'] = '0' * 64
        self.assertEqual(regions.input_plan(other, 'USA')[0], usa_keys)
        self.assertNotEqual(regions.input_plan(other, 'EUR')[0], eur_keys)

    def test_legacy_usa_cache_key_survives_catalog_expansion(self):
        legacy_pins = {**self.pins, 'inputs': [self.pins['inputs'][0]]}
        old_key = fingerprint({'format': 'verified-inputs-v1', 'code': regions.CANONICAL_CODE,
                              'romfs': regions.NORMALIZED_ROMFS['USA'], 'pins': legacy_pins})
        self.assertIn(old_key, regions.input_plan(self.pins, 'USA')[0])

    def test_unadapted_or_ambiguous_region_is_rejected(self):
        for region in ('JP', 'TWN', 'KOR', '../EUR'):
            with self.subTest(region=region), self.assertRaises(ValueError):
                regions.input_plan(self.pins, region)
        self.pins['inputs'].append(self.pins['inputs'][1])
        with self.assertRaises(ValueError):
            regions.input_plan(self.pins, 'EUR')

    def test_european_service_view_preserves_every_payload_byte(self):
        original = fixtures.NativeRomFsTests().fixture()
        for wrapped in (False, True):
            source = self.root / ('wrapped' if wrapped else 'level3')
            payload = b'IVFC' + bytes(4092) + original if wrapped else original
            source.write_bytes(payload)
            output = self.root / (source.name + '-output')
            regions.level3_view(source, output)
            self.assertEqual(output.read_bytes(), original)
            self.assertEqual(source.read_bytes(), payload)
            self.assertEqual(regions.RomFs(output).read('a'), b'ROM!')

    def test_bad_resources_do_not_replace_an_existing_game(self):
        source = self.root / 'bad'
        source.write_bytes(b'IVFC' + bytes(4092) + bytes(40))
        destination = self.root / 'game'
        with self.assertRaises(ValueError):
            regions.level3_view(source, destination)
        self.assertFalse(destination.exists())
        destination.write_bytes(b'existing game')
        with self.assertRaises(ValueError):
            regions.level3_view(source, destination)
        self.assertEqual(destination.read_bytes(), b'existing game')
        self.assertFalse(list(self.root.glob('.regional-romfs-*')))

    def test_active_region_changes_only_with_the_activated_profile(self):
        self.assertEqual(regions.active_region(self.root), 'USA')
        profile = launch_profile(self.root, self.root / 'installation', input_region='EUR')
        self.assertEqual(regions.active_region(self.root), 'USA')
        profile['arguments'].extend(['--custom-preference', 'keep'])
        (self.root / 'native-launch.json').write_text(json.dumps(profile))
        self.assertEqual(regions.active_region(self.root), 'EUR')
        updated = launch_profile(self.root, self.root / 'updated', input_region='USA')
        self.assertEqual(updated['native_input_region'], 'USA')
        self.assertIn('keep', updated['arguments'])
        self.assertEqual(regions.active_region(self.root), 'EUR')


if __name__ == '__main__':
    unittest.main()
