import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('switch_prepare', Path(__file__).resolve().parents[2]/'tools/native/switch/prepare.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PreparationTests(unittest.TestCase):
    def test_component_cannot_escape_kit(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);kit=root/'kit';kit.mkdir();(root/'private').write_text('fixture')
            with self.assertRaises(ValueError):module.checked_file(kit,'../private')
            (kit/'escape').symlink_to(root/'private')
            with self.assertRaises(ValueError):module.checked_file(kit,'escape')

    def test_link_paths_with_spaces_are_separate_arguments(self):
        with tempfile.TemporaryDirectory(prefix='switch preparation ') as directory:
            root=Path(directory).resolve()
            args=module.link_arguments({'arguments':['@KIT@/host.a','@TITLE@','-o','@OUTPUT@','-L@SDK@/lib']},root,root/'sdk',root/'game.a',root/'output.elf')
            self.assertEqual(args,[str(root/'host.a'),str(root/'game.a'),'-o',str(root/'output.elf'),'-L'+str(root/'sdk/lib')])


if __name__=='__main__':unittest.main()
