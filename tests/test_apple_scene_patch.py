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
            delegate.write_text('- (void)postFinishLaunch\n{\n}\n@implementation SDLUIKitDelegate {\n    [self performSelector:@selector(postFinishLaunch) withObject:nil afterDelay:0.0];\n@end\n')
            window.write_text('        uiwindow = [[SDL_uikitwindow alloc] initWithFrame:data.uiscreen.bounds];\n')
            events=ui/'SDL_uikitevents.m'
            events.write_text('    /* See the comment in the function definition. */\n')
            module.apply(root);first=(delegate.read_text(),window.read_text(),events.read_text());module.apply(root)
            self.assertEqual(first,(delegate.read_text(),window.read_text(),events.read_text()))
            self.assertEqual(first[0].count('@interface RetunedSceneDelegate'),1)
            for name in ['WillResignActive','DidEnterBackground','WillEnterForeground','DidBecomeActive']:
                self.assertEqual(first[0].count('SDL_OnApplication'+name+'();'),1)

            startup=first[0].split('- (void)postFinishLaunch',1)[1].split('@implementation',1)[0]
            self.assertIn('applicationState != UIApplicationStateActive',startup)
            self.assertIn('afterDelay:0.05',startup)
            self.assertIn('while (UIKit_EventPumpEnabled &&',first[2])
            self.assertIn('CFRunLoopRunInMode(kCFRunLoopDefaultMode, 0.05, TRUE)',first[2])

    def test_actual_event_pump_waits_until_foreground(self):
        import shutil
        import subprocess
        import sys
        if sys.platform != 'darwin' or not shutil.which('clang++'):
            self.skipTest('Requires Foundation and Clang')
        source=Path(__file__).parents[1]/'work/private/apple/build-ios-host/_deps/sdl2-src/src/video/uikit/SDL_uikitevents.m'
        if not source.exists():
            self.skipTest('Requires pinned SDL checkout')
        # Execute the patched SDL function itself with a deterministic UIKit
        # transition: resign during the first run-loop pass, become active
        # only when the guard continues servicing the run loop.
        text=source.read_text()
        start=text.index('void UIKit_PumpEvents(_THIS)')
        end=text.index('\n#ifdef ENABLE_GCKEYBOARD',start)
        pump=text[start:end]
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder)
            code=folder/'pump.mm'
            code.write_text('''#import <Foundation/Foundation.h>
#include <cassert>
enum { UIApplicationStateActive, UIApplicationStateInactive };
@interface UIApplication : NSObject
@property int applicationState;
+ (instancetype)sharedApplication;
@end
@implementation UIApplication
+ (instancetype)sharedApplication { static UIApplication* app=[UIApplication new]; return app; }
@end
static int calls=0,logs=0;
static bool UIKit_EventPumpEnabled=true;
static int Pump(CFStringRef, double, bool) {
    ++calls;
    if(calls==1)UIApplication.sharedApplication.applicationState=UIApplicationStateInactive;
    if(calls==3)UIApplication.sharedApplication.applicationState=UIApplicationStateActive;
    return 0;
}
#define CFRunLoopRunInMode Pump
#define _THIS void* unused
#define SDL_LOG_CATEGORY_RENDER 1
#define SDL_LogInfo(...) (++logs)
#define UITrackingRunLoopMode @"Tracking"
''' +pump+'''
int main() { @autoreleasepool {
    UIApplication.sharedApplication.applicationState=UIApplicationStateActive;
    UIKit_PumpEvents(nullptr);
    assert(UIApplication.sharedApplication.applicationState==UIApplicationStateActive);
    assert(calls==3 && logs==2);
} }
''')
            binary=folder/'pump'
            subprocess.run(['clang++','-std=c++20','-fobjc-arc',str(code),'-framework','Foundation','-o',str(binary)],check=True,capture_output=True)
            subprocess.run([str(binary)],check=True,capture_output=True)
