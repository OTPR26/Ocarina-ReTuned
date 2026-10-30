#!/usr/bin/env python3
"""Configure the neutral development APK; title libraries stay outside the APK."""
from pathlib import Path
import argparse
import os
import re
import shutil
import xml.etree.ElementTree as ET


def replace(path, before, after):
    source = path.read_text()
    if after in source:
        return
    if source.count(before) != 1:
        raise ValueError('Android app context changed: ' + str(path))
    path.write_text(source.replace(before, after))


def prepare(engine, private_kit=None, preparation_native_stage=None):
    root = Path(engine) / 'ports/android'
    shutil.copytree(Path(__file__).parent/'android/drawable',root/'app/src/main/res/drawable',dirs_exist_ok=True)
    notices=root/'app/src/main/assets/licenses'
    notices.mkdir(parents=True,exist_ok=True)
    shutil.copy2(Path(__file__).parents[2]/'resources/fonts/LICENSE.txt',notices/'interface-font-OFL.txt')
    shutil.copytree(Path(__file__).parents[2]/'resources/licenses/player-models', notices/'player-models', dirs_exist_ok=True)
    shutil.copytree(Path(__file__).resolve().parents[2]/'resources/fonts/interface',notices/'interface-fonts',dirs_exist_ok=True,ignore=shutil.ignore_patterns('*.ttf'))
    shutil.copytree(Path(__file__).parents[2]/'resources/icons/android',root/'app/src/main/res',dirs_exist_ok=True)
    replace(root/'app/src/main/AndroidManifest.xml', 'android:allowBackup="false"',
            'android:allowBackup="false" android:icon="@mipmap/ic_launcher" android:roundIcon="@mipmap/ic_launcher_round"')
    gradle = root / 'app/build.gradle.kts'
    replace(gradle, 'applicationId = "org.triaevum.android"',
            'applicationId = "io.github.otpr26.ocarinaretuned"')
    text = gradle.read_text()
    for previous in ('0.1-intro-dev', '0.1.0-native-prototype', '0.1.0-preview', '0.1.2-preview', '0.1.3-preview', '0.1.4-preview', '0.2.0-preview', '0.5.0', '0.5.1-rc1', '0.5.5', '0.5.6', '0.5.7', '0.5.8'):
        text = text.replace('versionName = "' + previous + '"', 'versionName = "0.5.9"')
    if 'versionName = "0.5.9"' not in text:
        raise ValueError('Android Preview version context changed')
    text = re.sub(r'\bversionCode = [0-9]+\b', 'versionCode = 13', text)
    if 'versionCode = 13' not in text: raise ValueError('Android version code context changed')
    gradle.write_text(text)
    shutil.copy2(Path(__file__).with_name('preparation_identity.py'), root/'preparation_identity.py')
    shutil.copy2(Path(__file__).with_name('android_runtime.py'), root/'android_runtime.py')
    identity_task = '''
// Stamp final preparation inputs after staging, independently of app/UI versions.
tasks.register<Exec>("stampPreparationIdentity") {
    dependsOn("checkNativeStage")
    onlyIf { file("src/main/assets/retuned/preparation-kit.zip").isFile }
    doFirst {
        commandLine(providers.gradleProperty("retunedHostPython").getOrElse("python3"),
            rootProject.file("preparation_identity.py").absolutePath,
            "--assets", file("src/main/assets/retuned").absolutePath,
            "--compiler-directory", file("src/main/jniLibs/arm64-v8a").absolutePath,
            "--runtime-directory", file(nativeStage.get()).resolve("arm64-v8a").absolutePath)
    }
}
tasks.named("preBuild") { dependsOn("stampPreparationIdentity") }
'''
    if 'tasks.register<Exec>("stampPreparationIdentity")' not in gradle.read_text():
        gradle.write_text(gradle.read_text() + identity_task)
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
    for name in ('TouchOverlay.java','TouchLayout.java','TextureFolder.java','InterfaceTypography.java'):
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
    if 'public void retunedEditTouchLayout()' not in activity.read_text():
        replace(activity,'    private TouchOverlay touchOverlay;',
                '    private TouchOverlay touchOverlay;\n    public void retunedEditTouchLayout(){runOnUiThread(()->{if(touchOverlay!=null)touchOverlay.startEditing();});}')
    if 'touchOverlay.cancelEditing()' not in activity.read_text():
        replace(activity,'    private TouchOverlay touchOverlay;',
                '    private TouchOverlay touchOverlay;\n    @Override public void onBackPressed(){if(touchOverlay==null||!touchOverlay.cancelEditing())super.onBackPressed();}')
    if 'touchOverlay=new TouchOverlay(this);' not in activity.read_text():
        replace(activity,'        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);',
                '        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);\n        touchOverlay=new TouchOverlay(this);\n        addContentView(touchOverlay,new android.view.ViewGroup.LayoutParams(-1,-1));')
    if '@Override protected void onPause()' not in activity.read_text():
        replace(activity,'    @Override protected String[] getLibraries() {',
                '    @Override protected void onPause() { if(touchOverlay!=null)touchOverlay.cancelInputs();super.onPause(); }\n\n    @Override protected String[] getLibraries() {')

    activity.write_text(activity.read_text().replace('if(touchOverlay!=null)touchOverlay.cancelInputs();super.onPause();', 'if(touchOverlay!=null)touchOverlay.suspendEditing();super.onPause();'))
    replace(activity,'int maximumShortEdge = 720;','int maximumShortEdge = 0;')
    replace(activity,'maximumShortEdge = 720;','maximumShortEdge = 0;')
    replace(activity,'using 720p surface limit','using native output resolution')
    replace(activity,'        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);',
            '        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);\n        applyImmersiveWindow();')
    if 'private void applyImmersiveWindow()' not in activity.read_text():
        replace(activity,'    @Override protected String[] getLibraries() {',
                '    @Override public void onWindowFocusChanged(boolean focused) {\n        super.onWindowFocusChanged(focused);\n        if(focused)applyImmersiveWindow();\n    }\n\n    private void applyImmersiveWindow() {\n        if(android.os.Build.VERSION.SDK_INT>=30) {\n            getWindow().setDecorFitsSystemWindows(false);\n            android.view.WindowInsetsController controller=getWindow().getInsetsController();\n            if(controller!=null){\n                controller.hide(android.view.WindowInsets.Type.systemBars());\n                controller.setSystemBarsBehavior(android.view.WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);\n            }\n        }else getWindow().getDecorView().setSystemUiVisibility(android.view.View.SYSTEM_UI_FLAG_FULLSCREEN | android.view.View.SYSTEM_UI_FLAG_HIDE_NAVIGATION | android.view.View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY | android.view.View.SYSTEM_UI_FLAG_LAYOUT_STABLE | android.view.View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN | android.view.View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION);\n    }\n\n    @Override protected String[] getLibraries() {')

    replace(activity,
            'new File(getApplicationInfo().nativeLibraryDir,\n                "libtriaevum_title_aot.so")',
            'new File(getFilesDir(), "native/triaevum_title_aot.so")')
    replace(activity, '"TriAevum.android.launch.json"', '"native-launch.json"')


    # The Java bootstrap can run before SDL/title loading on a clean install.
    for name in ('RomSetupActivity.java', 'RomPreparationActivity.java', 'RomPreparationService.java', 'PreparationSession.java', 'PreparationProgress.java', 'GameSession.java', 'PreparationUpdate.java', 'PreparationKit.java', 'SaveFilesCore.java', 'SaveDocumentStore.java', 'SaveFiles.java', 'SaveFilesActivity.java', 'PlayerModelsActivity.java', 'StartupReport.java', 'NativeCrashReport.java', 'StartupDiagnostics.java', 'StartupDiagnosticsActivity.java'):
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
    application.set(attribute('name'), '.StartupDiagnostics')
    if not any(node.get(attribute('name')) == '.PlayerModelsActivity' for node in application.findall('activity')):
        ET.SubElement(application, 'activity', {attribute('name'): '.PlayerModelsActivity',
            attribute('exported'): 'false', attribute('process'): ':models',
            attribute('screenOrientation'): 'sensorLandscape',
            attribute('configChanges'): 'orientation|screenSize|keyboardHidden'})
    if not any(node.get(attribute('name')) == '.StartupDiagnosticsActivity' for node in application.findall('activity')):
        ET.SubElement(application, 'activity', {attribute('name'): '.StartupDiagnosticsActivity', attribute('exported'): 'false'})
    launcher = next(node for node in application.findall('activity') if node.find('intent-filter') is not None)
    launcher.set(attribute('name'), '.TriAevumActivity')
    for node in list(application.findall('activity')):
        if node is not launcher and node.get(attribute('name')) == '.TriAevumActivity': application.remove(node)
    if not any(node.get(attribute('name')) == '.RetunedGameActivity' for node in application.findall('activity')):
        ET.SubElement(application, 'activity', {attribute('name'): '.RetunedGameActivity', attribute('exported'): 'false',
            attribute('screenOrientation'): 'sensorLandscape', attribute('configChanges'): 'keyboard|keyboardHidden|orientation|screenLayout|screenSize|smallestScreenSize|uiMode|navigation|density'})
    game_activity = next(node for node in application.findall('activity') if node.get(attribute('name')) == '.RetunedGameActivity')
    game_activity.set(attribute('launchMode'), 'singleTask')
    if not any(node.get(attribute('name')) == '.RomPreparationActivity' for node in application.findall('activity')):
        ET.SubElement(application, 'activity', {attribute('name'): '.RomPreparationActivity', attribute('exported'): 'false',
            attribute('process'): ':setup', attribute('screenOrientation'): 'sensorLandscape'})
    if not any(node.get(attribute('name')) == '.SaveFilesActivity' for node in application.findall('activity')):
        ET.SubElement(application, 'activity', {attribute('name'): '.SaveFilesActivity', attribute('exported'): 'false', attribute('screenOrientation'): 'sensorLandscape'})
    if not any(node.get(attribute('name')) == '.RomPreparationService' for node in application.findall('service')):
        ET.SubElement(application, 'service', {attribute('name'): '.RomPreparationService', attribute('exported'): 'false', attribute('process'): ':preparation', attribute('foregroundServiceType'): 'dataSync'})
    document.write(manifest, encoding='unicode', xml_declaration=True)
    text = activity.read_text()
    start = text.index('    @Override protected String[] getArguments() {')
    end = text.index('\n    }', start) + len('\n    }')
    text = text[:start] + (Path(__file__).parent/'android/game_arguments.java.inc').read_text().rstrip() + text[end:]
    gameplay.write_text(text.replace('class TriAevumActivity extends SDLActivity', 'class RetunedGameActivity extends SDLActivity'))
    text=gameplay.read_text()
    if 'void retunedStartupStage(int stage)' not in text:
        text = text.replace('    private TextureFolder retunedTextures;',
            '    public void retunedStartupStage(int stage){StartupDiagnostics.nativeStage(this,stage);}\n    private TextureFolder retunedTextures;')
    if 'void retunedStartupGraphics(int api' not in text:
        text = text.replace('    private TextureFolder retunedTextures;',
            '    public void retunedStartupGraphics(int api,int vendor,int driver){StartupDiagnostics.graphics(this,api,vendor,driver);}\n    private TextureFolder retunedTextures;')
    for signature, method in (
        ('void retunedSaveCommitted()', '    public void retunedSaveCommitted(){SaveFiles.committed(this);}'),
        ('void retunedOpenSaveFiles(', '    public void retunedOpenSaveFiles(String action){SaveFiles.open(this,action);}'),
        ('void retunedOpenRomPreparation()', '    private boolean retunedOpeningPreparation;\n    public void retunedOpenRomPreparation(){runOnUiThread(()->{retunedOpeningPreparation=true;startActivity(new android.content.Intent(this,RomPreparationActivity.class).putExtra("reprepare-rom",true));finish();});}'),
        ('void retunedOpenPlayerModels()', '    public void retunedOpenPlayerModels(){runOnUiThread(()->{retunedOpeningPreparation=true;startActivity(new android.content.Intent(this,PlayerModelsActivity.class));finish();});}'),
        ('String retunedSaveFilesStatus()', '    public String retunedSaveFilesStatus(){return SaveFiles.status();}')):
        if signature not in text:text=text.replace('    private TextureFolder retunedTextures;', method+'\n    private TextureFolder retunedTextures;')
    text = text.replace('    public void retunedOpenRomPreparation(){runOnUiThread(()->{startActivity(new android.content.Intent(this,TriAevumActivity.class).putExtra("reprepare-rom",true));finish();});}',
        '    private boolean retunedOpeningPreparation;\n    public void retunedOpenRomPreparation(){runOnUiThread(()->{retunedOpeningPreparation=true;startActivity(new android.content.Intent(this,RomPreparationActivity.class).putExtra("reprepare-rom",true));finish();});}')
    if 'protected void onDestroy()' not in text:
        text = text.replace('    private TextureFolder retunedTextures;',
            '    @Override protected void onDestroy(){super.onDestroy();if(retunedOpeningPreparation)android.os.Process.killProcess(android.os.Process.myPid());}\n    private TextureFolder retunedTextures;')
    elif 'if(retunedOpeningPreparation' not in text:
        start = text.index('protected void onDestroy()')
        position = text.index('super.onDestroy();', start) + len('super.onDestroy();')
        text = text[:position] + 'if(retunedOpeningPreparation)android.os.Process.killProcess(android.os.Process.myPid());' + text[position:]
    if 'GameSession.detach(this);' not in text:
        text = text.replace('@Override protected void onDestroy(){', '@Override protected void onDestroy(){GameSession.detach(this);')
    text = text.replace('if(retunedOpeningPreparation)android.os.Process.killProcess',
                        'if(retunedOpeningPreparation||isFinishing())android.os.Process.killProcess')
    if 'StartupDiagnostics.stage(this, "loading SDL and game libraries")' not in text:
        text = text.replace('        super.onCreate(state);', '        StartupDiagnostics.stage(this, "loading SDL and game libraries");\n        super.onCreate(state);\n        if (org.libsdl.app.SDLActivity.mBrokenLibraries) {\n            if (!StartupDiagnostics.prefs(this).getBoolean("pending", false)) StartupDiagnostics.failure(this, new IllegalStateException("SDL initialization failed"));\n            startActivity(new android.content.Intent(this, StartupDiagnosticsActivity.class)); finish(); return;\n        }\n        StartupDiagnostics.stage(this, "SDL activity created");')
        text = text.replace('        return new TriAevumSurface(context, maximumShortEdge);', '        StartupDiagnostics.stage(this, "creating graphics surface");\n        return new TriAevumSurface(context, maximumShortEdge);')
    text = text.replace('        File profile = new File(getExternalFilesDir(null), "native-launch.json");', '        StartupDiagnostics.stage(this, "starting native runtime / Vulkan initialization");\n        File profile = new File(getExternalFilesDir(null), "native-launch.json");')
    if 'SDLActivity.mBrokenLibraries' not in text:
        text = text.replace('        super.onCreate(state);', '        super.onCreate(state);\n        if (org.libsdl.app.SDLActivity.mBrokenLibraries) {\n            if (!StartupDiagnostics.prefs(this).getBoolean("pending", false)) StartupDiagnostics.failure(this, new IllegalStateException("SDL initialization failed"));\n            startActivity(new android.content.Intent(this, StartupDiagnosticsActivity.class)); finish(); return;\n        }')
    if 'public void loadLibraries()' not in text:
        text = text.replace('    @Override protected String[] getLibraries() {', '    @Override public void loadLibraries() {\n        for (String library : getLibraries()) {\n            StartupDiagnostics.stage(this, "loading library " + library);\n            try { org.libsdl.app.SDL.loadLibrary(library, this); }\n            catch (UnsatisfiedLinkError | RuntimeException error) { StartupDiagnostics.failure(this, error); throw error; }\n        }\n        StartupDiagnostics.stage(this, "native libraries loaded");\n    }\n\n    @Override protected String[] getLibraries() {')
    if 'GameSession.attach(this);' not in text:
        text = text.replace('        StartupDiagnostics.stage(this, "SDL activity created");',
            '        StartupDiagnostics.stage(this, "SDL activity created");\n        GameSession.attach(this);')
    text=text.replace('new android.content.Intent(this,PlayerModelsActivity.class).putExtra("choose-pak",true)',
        'new android.content.Intent(this,PlayerModelsActivity.class)')
    gameplay.write_text(text)
    activity.write_text('package org.triaevum.android;\n/** Stable launcher component preserves existing home-screen shortcuts. */\npublic final class TriAevumActivity extends RomSetupActivity {}\n')
    asset = root/'app/src/main/assets/retuned'
    asset.mkdir(parents=True, exist_ok=True)
    for font in (Path(__file__).parents[2]/'resources/fonts/interface').glob('*.ttf'):
        shutil.copy2(font, asset/font.name)
    shutil.copy2(Path(__file__).parents[2]/'resources/artwork/ocarina-illustration.png', asset/'ocarina-illustration.png')
    python = root/'app/src/main/python'
    python.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(__file__).parent/'android/retuned_setup_entry.py', python/'retuned_setup_entry.py')
    shutil.copy2(Path(__file__).parent/'android/retuned_models_entry.py', python/'retuned_models_entry.py')
    top = root/'build.gradle.kts'
    replace(top, 'plugins {', 'plugins {\n    id("com.chaquo.python") version "17.1.0" apply false')
    replace(gradle, 'plugins { id("com.android.application") }', 'plugins { id("com.android.application"); id("com.chaquo.python") }')
    if 'chaquopy {' not in gradle.read_text():
        gradle.write_text(gradle.read_text() + '\nchaquopy { defaultConfig { version = "3.12" } }\n')

    numpy_url = ('https://chaquo.com/pypi-upstream/numpy/'
        'numpy-2.3.2-1-cp313-cp313-android_24_arm64_v8a.whl'
        '#sha256=f7beb51f8d162c110ee8d4c9e275f490ce39dddba919643d949687bb4286bedd')
    python_config = 'chaquopy { defaultConfig { version = "3.13"; pip { install("' + numpy_url + '") } } }'
    text = gradle.read_text()
    previous = 'chaquopy { defaultConfig { version = "3.12" } }'
    if previous in text:
        gradle.write_text(text.replace(previous, python_config))
    elif python_config not in text:
        raise ValueError('Android model-import dependency context changed')

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

    if preparation_native_stage is not None:
        from preparation_identity import stamp_android
        stamp_android(asset, root/'app/src/main/jniLibs/arm64-v8a', Path(preparation_native_stage)/'arm64-v8a')

    from apply_android_startup import apply as apply_startup
    apply_startup(engine)



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('engine', type=Path)
    parser.add_argument('--private-preparation-kit', type=Path)
    parser.add_argument('--preparation-native-stage', type=Path)
    args = parser.parse_args()
    prepare(args.engine, args.private_preparation_kit, args.preparation_native_stage)
