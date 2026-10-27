import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / 'tools/native/preparation_cache.py'
spec = importlib.util.spec_from_file_location('preparation_cache', MODULE)
cache_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cache_module)


class PreparationCacheTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.cache = cache_module.LocalCache(self.root / 'cache', limit=2048)
        self.source = self.root / 'source'
        self.source.write_bytes(b'verified local object')
        self.key = cache_module.fingerprint({'compiler': 'one', 'source': 'one'})

    def test_restored_bytes_match_and_inputs_remain_untouched(self):
        self.assertTrue(self.cache.store(self.key, {'unit.o': self.source}))
        self.assertTrue(self.cache.restore(self.key, self.root / 'restored'))
        self.assertEqual((self.root / 'restored/unit.o').read_bytes(), self.source.read_bytes())
        self.assertEqual(self.source.read_bytes(), b'verified local object')

    def test_corrupt_objects_and_wrong_input_identity_are_not_reused(self):
        self.cache.store(self.key, {'unit.o': self.source})
        self.assertFalse(self.cache.restore(self.key, self.root / 'out', {'unit.o': 'wrong'}))
        self.assertFalse(self.cache.restore(self.key, self.root / 'out', required={'other.o'}))
        (self.cache.entry(self.key) / 'unit.o').write_bytes(b'broken')
        self.assertFalse(self.cache.restore(self.key, self.root / 'out'))
        self.assertFalse((self.root / 'out').exists())

    def test_malformed_receipts_are_cache_misses(self):
        for receipt in ('[]', '{"files": []}', '{"files": {"unit.o": 12}}', 'not json'):
            self.cache.store(self.key, {'unit.o': self.source})
            (self.cache.entry(self.key) / 'receipt.json').write_text(receipt)
            self.assertFalse(self.cache.restore(self.key, self.root / 'out'))

    def test_symlink_cache_is_rejected_without_touching_target(self):
        outside = self.root / 'outside'; outside.mkdir()
        (self.root / 'cache').symlink_to(outside, target_is_directory=True)
        self.assertFalse(self.cache.store(self.key, {'unit.o': self.source}))
        self.assertFalse(self.cache.restore(self.key, self.root / 'out'))
        self.assertEqual(list(outside.iterdir()), [])

    def test_changed_compiler_misses_and_disk_failure_is_nonfatal(self):
        self.cache.store(self.key, {'unit.o': self.source})
        key = cache_module.fingerprint({'compiler': 'two', 'source': 'one'})
        self.assertFalse(self.cache.restore(key, self.root / 'out'))
        with patch.object(cache_module.shutil, 'copyfile', side_effect=OSError('full')):
            self.assertFalse(self.cache.store(key, {'unit.o': self.source}))
        self.assertTrue(self.source.is_file())

    def test_old_entries_are_evicted_within_reserved_cache_only(self):
        self.cache.limit = 450
        self.source.write_bytes(b'x' * 200)
        self.cache.store(self.key, {'unit.o': self.source})
        other = cache_module.fingerprint('new')
        self.cache.store(other, {'unit.o': self.source})
        self.assertFalse(self.cache.entry(self.key).exists())
        self.assertTrue(self.cache.restore(other, self.root / 'out'))
        self.assertTrue(self.source.exists())
