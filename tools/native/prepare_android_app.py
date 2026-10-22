#!/usr/bin/env python3
"""Configure the neutral development APK; title libraries stay outside the APK."""
from pathlib import Path
import argparse
import os
import shutil
import xml.etree.ElementTree as ET


def replace(path, before, after):
    source = path.read_text()
    if after in source:
        return
    if source.count(before) != 1:
        raise ValueError('Android app context changed: ' + str(path))
    path.write_text(source.replace(before, after))


def prepare(engine, private_kit=None):
    root = Path(engine) / 'ports/android'
    shutil.copytree(Path(__file__).parent/'android/drawable',root/'app/src/main/res/drawable',dirs_exist_ok=True)
    notices=root/'app/src/main/assets/licenses'
    notices.mkdir(parents=True,exist_ok=True)
    shutil.copy2(Path(__file__).parents[2]/'resources/fonts/LICENSE.txt',notices/'interface-font-OFL.txt')
    shutil.copytree(Path(__file__).parents[2]/'resources/icons/android',root/'app/src/main/res',dirs_exist_ok=True)
    replace(root/'app/src/main/AndroidManifest.xml', 'android:allowBackup="false"',
            'android:allowBackup="false" android:icon="@mipmap/ic_launcher" android:roundIcon="@mipmap/ic_launcher_round"')
    gradle = root / 'app/build.gradle.kts'
    replace(gradle, 'applicationId = "org.triaevum.android"',
            'applicationId = "io.github.otpr26.ocarinaretuned"')
    replace(gradle, 'versionName = "0.1-intro-dev"', 'versionName = "0.1.0-native-prototype"')
    # Public Preview packages must not expose the private test app's debug mode.
    legacy_debug = '    buildTypes { getByName("release") { isDebuggable = true } }\n'
    gradle.write_text(gradle.read_text().replace(legacy_debug, ''))
    replace(gradle, '    compileOptions {',
            '    buildTypes { getByName("release") { isDebuggable = false } }\n    compileOptions {')
    replace(gradle, '"triaevum_title_bootstrap", "triaevum_title_aot", "c++_shared"',
            '"triaevum_title_bootstrap", "c++_shared"')
    replace(root / 'app/src/main/AndroidManifest.xml',
            'android:label="TriAevum — Echoes of Time"', 'android:label="Ocarina ReTuned"')
    activity = root / 'app/src/main/java/org/triaevum/android/TriAevumActivity.java'
    gameplay = activity.with_name('RetunedGameActivity.java')
    if gameplay.exists():
        activity.write_text(gameplay.read_text().replace('class RetunedGameActivity extends SDLActivity', 'class TriAevumActivity extends SDLActivity'))
    for name in ('TouchOverlay.java','TextureFolder.java'):
        shutil.copy2(Path(__file__).parent/'android'/name,activity.parent/name)
    if 'private TextureFolder retunedTextures;' not in activity.read_text():
        replace(activity,'public final class TriAevumActivity extends SDLActivity {',
                'public final class TriAevumActivity extends SDLActivity {\n    private TextureFolder retunedTextures;\n    public void retunedChooseTextureFolder(){if(retunedTextures!=null)retunedTextures.choose();}\n    public String retunedTakeTextureFolder(){return retunedTextures==null?"":retunedTextures.take();}\n    public String retunedTextureFolderStatus(){return retunedTextures==null?"":retunedTextures.status();}\n    public byte[] retunedReadTextureFile(String path){return retunedTextures==null?null:retunedTextures.read(path);}\n    @Override protected void onActivityResult(int request,int result,android.content.Intent data){\n        if(request==TextureFolder.REQUEST&&retunedTextures!=null){retunedTextures.result(result,data);return;}\n        super.onActivityResult(request,result,data);\n    }')
    if 'retunedTextures=new TextureFolder(this);' not in activity.read_text():
        replace(activity,'        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);',
                '        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);\n        retunedTextures=new TextureFolder(this);')
    if 'private TouchOverlay touchOverlay;' not in activity.read_text():
        replace(activity,'public final class TriAevumActivity extends SDLActivity {',
                'public final class TriAevumActivity extends SDLActivity {\n    private TouchOverlay touchOverlay;')
    if 'touchOverlay=new TouchOverlay(this);' not in activity.read_text():
        replace(activity,'        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);',
                '        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);\n        touchOverlay=new TouchOverlay(this);\n        addContentView(touchOverlay,new android.view.ViewGroup.LayoutParams(-1,-1));')
    if '@Override protected void onPause()' not in activity.read_text():
        replace(activity,'    @Override protected String[] getLibraries() {',
                '    @Override protected void onPause() { if(touchOverlay!=null)touchOverlay.cancelInputs();super.onPause(); }\n\n    @Override protected String[] getLibraries() {')

    replace(activity,'int maximumShortEdge = 720;','int maximumShortEdge = 0;')
    replace(activity,'maximumShortEdge = 720;','maximumShortEdge = 0;')
    replace(activity,'using 720p surface limit','using native output resolution')
    replace(activity,'        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);',
            '        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);\n        applyImmersiveWindow();')
    replace(activity,'    @Override protected String[] getLibraries() {',
            '    @Override public void onWindowFocusChanged(boolean focused) {\n        super.onWindowFocusChanged(focused);\n        if(focused)applyImmersiveWindow();\n    }\n\n    private void applyImmersiveWindow() {\n        if(android.os.Build.VERSION.SDK_INT>=30) {\n            getWindow().setDecorFitsSystemWindows(false);\n            android.view.WindowInsetsController controller=getWindow().getInsetsController();\n            if(controller!=null){\n                controller.hide(android.view.WindowInsets.Type.systemBars());\n                controller.setSystemBarsBehavior(android.view.WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);\n            }\n        }else getWindow().getDecorView().setSystemUiVisibility(android.view.View.SYSTEM_UI_FLAG_FULLSCREEN | android.view.View.SYSTEM_UI_FLAG_HIDE_NAVIGATION | android.view.View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY | android.view.View.SYSTEM_UI_FLAG_LAYOUT_STABLE | android.view.View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN | android.view.View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION);\n    }\n\n    @Override protected String[] getLibraries() {')

    replace(activity,
            'new File(getApplicationInfo().nativeLibraryDir,\n                "libtriaevum_title_aot.so")',
            'new File(getFilesDir(), "native/triaevum_title_aot.so")')
    replace(activity, '"TriAevum.android.launch.json"', '"native-launch.json"')


    # The Java bootstrap can run before SDL/title loading on a clean install.
    for name in ('RomSetupActivity.java', 'RomPreparationService.java', 'PreparationKit.java'):
        shutil.copy2(Path(__file__).parent/'android'/name, activity.parent/name)
    manifest = root/'app/src/main/AndroidManifest.xml'
    text = manifest.read_text()
    permissions = ('FOREGROUND_SERVICE', 'FOREGROUND_SERVICE_DATA_SYNC', 'WAKE_LOCK')
    for permission in permissions:
        line = '    <uses-permission android:name="android.permission.' + permission + '" />'
        if line not in text:
            text = text.replace('    <application ', line + '\n    <application ', 1)
    manifest.write_text(text)
    namespace = 'http://schemas.android.com/apk/res/android'
    attribute = lambda name: '{' + namespace + '}' + name
    ET.register_namespace('android', namespace)
    document = ET.parse(manifest)
    application = document.getroot().find('application')
    launcher = next(node for node in application.findall('activity') if node.find('intent-filter') is not None)
    launcher.set(attribute('name'), '.TriAevumActivity')
    for node in list(application.findall('activity')):
        if node is not launcher and node.get(attribute('name')) == '.TriAevumActivity': application.remove(node)
    if not any(node.get(attribute('name')) == '.RetunedGameActivity' for node in application.findall('activity')):
        ET.SubElement(application, 'activity', {attribute('name'): '.RetunedGameActivity', attribute('exported'): 'false',
            attribute('screenOrientation'): 'sensorLandscape', attribute('configChanges'): 'keyboard|keyboardHidden|orientation|screenLayout|screenSize|smallestScreenSize|uiMode|navigation|density'})
    if not any(node.get(attribute('name')) == '.RomPreparationService' for node in application.findall('service')):
        ET.SubElement(application, 'service', {attribute('name'): '.RomPreparationService', attribute('exported'): 'false', attribute('process'): ':preparation', attribute('foregroundServiceType'): 'dataSync'})
    document.write(manifest, encoding='unicode', xml_declaration=True)
    text = activity.read_text()
    start = text.index('    @Override protected String[] getArguments() {')
    end = text.index('\n    }', start) + len('\n    }')
    text = text[:start] + (Path(__file__).parent/'android/game_arguments.java.inc').read_text().rstrip() + text[end:]
    gameplay.write_text(text.replace('class TriAevumActivity extends SDLActivity', 'class RetunedGameActivity extends SDLActivity'))
    activity.write_text('package org.triaevum.android;\n/** Stable launcher component preserves existing home-screen shortcuts. */\npublic final class TriAevumActivity extends RomSetupActivity {}\n')
    asset = root/'app/src/main/assets/retuned'
    asset.mkdir(parents=True, exist_ok=True)
    for name in ('InterfaceSans-Regular.ttf', 'InterfaceSans-Bold.ttf'):
        shutil.copy2(Path(__file__).parents[2]/'resources/fonts'/name, asset/name)
    shutil.copy2(Path(__file__).parents[2]/'resources/artwork/ocarina-illustration.png', asset/'ocarina-illustration.png')
    python = root/'app/src/main/python'
    python.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(__file__).parent/'android/retuned_setup_entry.py', python/'retuned_setup_entry.py')
    top = root/'build.gradle.kts'
    replace(top, 'plugins {', 'plugins {\n    id("com.chaquo.python") version "17.1.0" apply false')
    replace(gradle, 'plugins { id("com.android.application") }', 'plugins { id("com.android.application"); id("com.chaquo.python") }')
    if 'chaquopy {' not in gradle.read_text():
        gradle.write_text(gradle.read_text() + '\nchaquopy { defaultConfig { version = "3.12" } }\n')

    if private_kit is not None:
        private_kit = Path(private_kit).resolve()
        private_root = (Path(__file__).parents[2]/'work/private').resolve()
        if os.environ.get('GITHUB_ACTIONS') or not private_kit.is_relative_to(private_root):
            raise ValueError('Private preparation fixtures must remain local.')
        for directory, destination in (('assets', root/'app/src/main/assets'),
                                       ('jniLibs', root/'app/src/main/jniLibs'),
                                       ('python', python)):
            source = private_kit/directory
            if not source.is_dir(): raise ValueError('Incomplete private preparation fixture')
            shutil.copytree(source, destination, dirs_exist_ok=True)
        print('Private preparation fixture staged for local testing; do not publish this package.')



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('engine', type=Path)
    parser.add_argument('--private-preparation-kit', type=Path)
    args = parser.parse_args()
    prepare(args.engine, args.private_preparation_kit)
