import importlib.util
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('apple_scenes',Path(__file__).parents[1]/'tools/native/apple/patch_sdl_scenes.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class ScenePatchTests(unittest.TestCase):
    def test_scene_lifecycle_is_installed_once(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);ui=root/'src/video/uikit';ui.mkdir(parents=True)
            delegate=ui/'SDL_uikitappdelegate.m';window=ui/'SDL_uikitwindow.m'
            delegate.write_text('@implementation SDLUIKitDelegate {\n    [self performSelector:@selector(postFinishLaunch) withObject:nil afterDelay:0.0];\n@end\n')
            window.write_text('        uiwindow = [[SDL_uikitwindow alloc] initWithFrame:data.uiscreen.bounds];\n')
            module.apply(root);first=(delegate.read_text(),window.read_text());module.apply(root)
            self.assertEqual(first,(delegate.read_text(),window.read_text()))
            self.assertEqual(first[0].count('@interface RetunedSceneDelegate'),1)
            for name in ['WillResignActive','DidEnterBackground','WillEnterForeground','DidBecomeActive']:
                self.assertEqual(first[0].count('SDL_OnApplication'+name+'();'),1)
