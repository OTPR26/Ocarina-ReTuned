import json
from pathlib import Path
import tempfile
import unittest
from retuned.native_inputs import verify_identity


class NativeInputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.catalog = Path(self.temp.name) / 'catalog.json'
        self.identity = {'program_id': 'TEST', 'code': {'bytes': 1, 'sha256': 'a'},
                         'exheader': {'bytes': 2, 'sha256': 'b'},
                         'romfs': {'bytes': 3, 'sha256': 'c'}}
        self.catalog.write_text(json.dumps({'inputs': [{'region': 'TEST', **self.identity}]}))

    def test_container_independent_validation(self):
        result = verify_identity(self.identity, self.catalog)
        self.assertEqual(result['validation'], 'native_content_v1')
        self.assertTrue(result['verified'])

    def test_each_content_component_is_required(self):
        for name in ('code', 'exheader', 'romfs'):
            with self.subTest(component=name), self.assertRaises(ValueError):
                verify_identity({**self.identity, name: {'bytes': 1, 'sha256': 'different'}}, self.catalog)

    def test_wrong_program_is_rejected(self):
        with self.assertRaises(ValueError):
            verify_identity({**self.identity, 'program_id': 'WRONG'}, self.catalog)


if __name__ == '__main__':
    unittest.main()
