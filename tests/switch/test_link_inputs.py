import importlib.util
from pathlib import Path
import shlex
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

spec=importlib.util.spec_from_file_location('switch_link_inputs',Path(__file__).parents[2]/'tools/native/switch/stage_link_inputs.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class LinkInputTests(unittest.TestCase):
    def test_title_is_excluded_and_paths_are_relocatable(self):
        with tempfile.TemporaryDirectory(prefix='switch link ') as tmp:
            base=Path(tmp);build=base/'build';build.mkdir();sdk=base/'sdk';sdk.mkdir()
            (build/'main.o').write_bytes(b'neutral host');(build/'title.a').write_bytes(b'private fixture')
            (sdk/'lib').mkdir();(sdk/'lib/libnx.a').write_bytes(b'sdk')
            command=shlex.join([str(sdk/'devkitA64/bin/aarch64-none-elf-g++'),'-L'+str(sdk/'lib'),
                'main.o','-Wl,--whole-archive',str(build/'title.a'),'-Wl,--no-whole-archive',
                str(sdk/'lib/libnx.a'),'-o','OcarinaReTuned.elf'])+' && :'
            with patch.object(module.subprocess,'run',return_value=SimpleNamespace(stdout='T host_function\n')):
                result=module.collect(command,build=build,sdk=sdk,title=build/'title.a',output=base/'out')
            self.assertEqual(len(result['files']),1)
            self.assertIn('@TITLE@',result['arguments'])
            self.assertIn('@SDK@/lib/libnx.a',result['arguments'])
            self.assertIn('@OUTPUT@',result['arguments'])
            self.assertFalse(result['title_included'])
            self.assertNotIn(tmp,(base/'out/link-inputs.json').read_text())
            self.assertEqual((base/'out/link/000-main.o').read_bytes(),b'neutral host')

    def test_generated_definition_is_rejected_before_staging(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);(base/'main.o').write_bytes(b'fixture');(base/'title.a').write_bytes(b'title')
            command=shlex.join([str(base/'devkitA64/bin/aarch64-none-elf-g++'),'main.o','title.a','-o','OcarinaReTuned.elf'])
            with patch.object(module.subprocess,'run',return_value=SimpleNamespace(stdout='T RetunedSwitchTitleEntryPoints\n')):
                with self.assertRaises(ValueError):
                    module.collect(command,build=base,sdk=base/'sdk',title=base/'title.a',output=base/'out')
            self.assertFalse((base/'out').exists())

if __name__=='__main__':unittest.main()
