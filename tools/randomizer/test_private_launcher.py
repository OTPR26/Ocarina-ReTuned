import tempfile
import unittest
from pathlib import Path
from run_private_launcher import arguments_for
from apply_private_launcher import install_session_continue, BASE


class HandoffTests(unittest.TestCase):
    def test_continue_state_belongs_to_session_and_patch_is_repeatable(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/BASE).mkdir(parents=True)
            shared=root/BASE/'oot3d_native_a32_window_shared.h'
            policy=root/BASE/'oot3d_native_a32_projection_policy.cpp'
            shared.write_text('#pragma once\nstruct NativeWidescreenProjectionState {\n};\n')
            policy.write_text('  auto &runtime = *static_cast<NativeWidescreenProjectionState *>(user);\n')
            install_session_continue(root)
            expected=(shared.read_text(),policy.read_text())
            install_session_continue(root)
            self.assertEqual((shared.read_text(),policy.read_text()),expected)
            self.assertIn('ContinueGame RandomizerContinue{',expected[0])
            self.assertIn('runtime.RandomizerContinue.Update',expected[1])
            self.assertNotIn('static RetunedRandomizer::ContinueGame',expected[1])

    def test_modes_keep_normal_arguments_and_slot_profiles_separate(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            config={'app_data':str(root/'data'),'artifacts':str(root/'artifacts'),
                'normal_arguments':['--a32-process-manifest','normal.json',
                                    '--title-plugin','normal.dylib','--save-data',str(root/'normal')]}
            original=list(config['normal_arguments'])
            request={'mode':'randomizer','slot':2,'manifest':str(root/'artifacts/game.json'),
                     'module':str(root/'artifacts/game.dylib'),
                     'profile':str(root/'data/randomizer-runs/slot-3/profile')}
            args=arguments_for(config,request)
            self.assertEqual(args[-1],request['profile'])
            self.assertEqual(config['normal_arguments'],original)
            self.assertEqual(arguments_for(config,{'mode':'normal'}),original)
            for bad in ({'slot':3},{'slot':-1},{'slot':True},{'profile':str(root/'normal')},
                        {'module':str(root/'outside.dylib')},{'mode':'unknown'}):
                with self.subTest(bad=bad),self.assertRaises(ValueError):
                    arguments_for(config,request|bad)


if __name__=='__main__':
    unittest.main()
