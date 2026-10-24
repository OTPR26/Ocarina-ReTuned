"""A dynamic mod return must remain callable after regenerating title code."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('title_sources', Path(__file__).resolve().parents[2] / 'tools/native/generate_title_sources.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ResumeSitesTests(unittest.TestCase):
    def test_catalog_and_translation_must_match_current_code(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            code, program, catalog = [root / name for name in ('code', 'program.json', 'sites.json')]
            code.write_bytes(b'fixture code')
            catalog.write_text(json.dumps({'format': 'oot3d_whole_aot_observed_sites_v1',
                'code_sha256': hashlib.sha256(code.read_bytes()).hexdigest(),
                'sites': [{'pc': '0x1004'}]}))
            program.write_text(json.dumps({'blocks': [{'pc': 0x1000}]}))
            with self.assertRaisesRegex(ValueError, 'omitted'):
                module.validate_resume_sites(program, code, catalog)
            program.write_text(json.dumps({'blocks': [{'pc': 0x1000}, {'pc': 0x1004}]}))
            module.validate_resume_sites(program, code, catalog)
            code.write_bytes(b'changed code')
            with self.assertRaisesRegex(ValueError, 'does not match'):
                module.validate_resume_sites(program, code, catalog)


if __name__ == '__main__':
    unittest.main()
