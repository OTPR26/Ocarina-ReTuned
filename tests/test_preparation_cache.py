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

    def test_new_source_tree_cannot_evict_compiled_objects(self):
        sources = cache_module.LocalCache(self.root / 'sources', limit=700000)
        compiled = cache_module.LocalCache(self.root / 'objects', limit=500000)
        source = self.root / 'generated.cpp'; source.write_bytes(b's' * 600000)
        obj = self.root / 'unit.o'; obj.write_bytes(b'o' * 25000)
        keys = [cache_module.fingerprint({'unit': n}) for n in range(10)]
        old = cache_module.fingerprint('old source')
        new = cache_module.fingerprint('new source')
        self.assertTrue(sources.store(old, {'generated.cpp': source}))
        for key in keys:
            self.assertTrue(compiled.store(key, {'unit.o': obj}))
        source.write_bytes(b't' * 600000)
        self.assertTrue(sources.store(new, {'generated.cpp': source}))
        self.assertFalse(sources.entry(old).exists())
        for number, key in enumerate(keys):
            self.assertTrue(compiled.restore(key, self.root / ('out' + str(number))))
        self.assertTrue(sources.restore(new, self.root / 'new-source'))

    def test_migration_discards_only_the_selected_cache_entry(self):
        self.assertTrue(self.cache.store(self.key, {'unit.o': self.source}))
        outside=self.root/'saves';outside.mkdir();(outside/'save').write_bytes(b'keep')
        other=cache_module.fingerprint('symlink');self.cache.entry(other).symlink_to(outside,target_is_directory=True)
        self.assertFalse(self.cache.discard(other))
        self.assertTrue(self.cache.discard(self.key))
        self.assertFalse(self.cache.entry(self.key).exists())
        self.assertEqual((outside/'save').read_bytes(),b'keep')

    def test_mixed_cache_reproduces_object_eviction_after_source_refresh(self):
        import os
        mixed = cache_module.LocalCache(self.root / 'mixed', limit=1300000)
        source = self.root / 'generated.cpp'; source.write_bytes(b's' * 600000)
        obj = self.root / 'unit.o'; obj.write_bytes(b'o' * 250000)
        old, unit, new = map(cache_module.fingerprint, ('old', 'unit', 'new'))
        self.assertTrue(mixed.store(old, {'generated.cpp': source}))
        self.assertTrue(mixed.store(unit, {'unit.o': obj}))
        # Restoring the old tree makes it newer than the compiled objects.
        os.utime(mixed.entry(unit), (1, 1))
        self.assertTrue(mixed.restore(old, self.root / 'generated'))
        source.write_bytes(b't' * 600000)
        self.assertTrue(mixed.store(new, {'generated.cpp': source}))
        self.assertFalse(mixed.entry(unit).exists())
        self.assertTrue(mixed.entry(old).exists())
        self.assertTrue(mixed.entry(new).exists())
