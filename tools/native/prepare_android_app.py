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


def install_randomizer_documents(activity):
    shutil.copy2(Path(__file__).parent/'android/RandomizerDocuments.java',activity.parent/'RandomizerDocuments.java')
    if 'private RandomizerDocuments retunedRuns;' not in activity.read_text():
        replace(activity,'    private TextureFolder retunedTextures;', '''    private TextureFolder retunedTextures;
    private RandomizerDocuments retunedRuns;
    public boolean retunedImportRun(int slot){return retunedRuns!=null&&retunedRuns.chooseImport(slot);}
    public boolean retunedExportRun(int slot,byte[] bytes){return retunedRuns!=null&&retunedRuns.chooseExport(slot,bytes);}
    public String retunedTakeRunDocument(){return retunedRuns==null?"":retunedRuns.takeResult();}''')
    replace(activity,'    private RandomizerDocuments retunedRuns;',
            '    private RandomizerDocuments retunedRuns;\n    public boolean retunedLaunchRun(String arguments,int slot,boolean newGame){return RandomizerSession.queue(this,arguments,slot,newGame);}')
    replace(activity, '    private RandomizerDocuments retunedRuns;',
            '''    private RandomizerDocuments retunedRuns;
    public boolean retunedPrepareRandomizer(String id) {
        if (RomPreparationService.randomizerJob(this, id) == null) return false;
        startForegroundService(new android.content.Intent(this, RomPreparationService.class)
            .putExtra(RomPreparationService.RANDOMIZER_JOB, id));
        return true;
    }''')
    replace(activity,'        retunedTextures=new TextureFolder(this);',
            '        retunedTextures=new TextureFolder(this);\n        retunedRuns=new RandomizerDocuments(this);')
    replace(activity,'        if(request==TextureFolder.REQUEST',
            '        if(retunedRuns!=null&&retunedRuns.result(request,result,data))return;\n        if(request==TextureFolder.REQUEST')


def add_randomizer_tools(assets, recipe=None):
    import hashlib
    import json
    import tempfile
    import zipfile

    source = Path(__file__).resolve().parents[1] / 'randomizer'
    archive = assets / 'preparation-kit.zip'
    scripts = ('prepare_run.py', 'compose_image.py', 'stage_runtime.py', 'plan_hooks.py',
               'audit_runtime.py', 'validate_seed.py', 'hook_policy.json')
    with tempfile.TemporaryDirectory(dir=assets) as temporary:
        stage = Path(temporary)
        with zipfile.ZipFile(archive) as original:
            for name in ('engine/preparation-runtime.json',
                         'engine/tools/oot3d/native_a32_runtime/whole_aot_cpp.py',
                         'engine/tools/oot3d/native_a32_runtime/upstream/recomp/a32_vfp_binary64.cpp'):
                original.extract(name, stage)
            import sys
            sys.path.insert(0, str(source))
            try:
                from apply_translation import apply
                apply(stage / 'engine')
            finally:
                sys.path.pop(0)
            manifest_path = stage / 'engine/preparation-runtime.json'
            manifest = json.loads(manifest_path.read_text())
            replacements = {}
            for path in (stage / 'engine/tools').rglob('*'):
                if path.is_file():
                    contents = path.read_bytes()
                    manifest['files'][path.relative_to(stage / 'engine').as_posix()] = hashlib.sha256(contents).hexdigest()
                    replacements['randomizer-engine/' + path.relative_to(stage / 'engine').as_posix()] = contents
            replacements['randomizer-engine/preparation-runtime.json'] = json.dumps(manifest, indent=2).encode()
            for name in scripts:
                replacements['project/tools/randomizer/' + name] = (source / name).read_bytes()
            if recipe is not None:
                from stage_preparation_sources import digest
                sys.path.insert(0, str(source))
                try:
                    from stage_recipe import HUD, IPS, RUNTIME
                    from prepare_resources import ARCHIVE_SHA256, DEFAULT_ARCHIVE
                finally:
                    sys.path.pop(0)
                for name, expected in [('hud.elf', HUD), ('hud.ips', IPS), ('runtime.elf', RUNTIME)]:
                    if digest(recipe / name) != expected:
                        raise ValueError('Unexpected Randomizer recipe file: ' + name)
                    replacements['randomizer/' + name] = (recipe / name).read_bytes()
                proof = json.loads((recipe / 'runtime-receipt.json').read_text())
                if proof['elf_sha256'] != RUNTIME or proof['hud_sha256'] != HUD:
                    raise ValueError('Invalid Randomizer runtime receipt')
                replacements['randomizer/runtime-receipt.json'] = (recipe / 'runtime-receipt.json').read_bytes()
                if digest(DEFAULT_ARCHIVE) != ARCHIVE_SHA256:
                    raise ValueError('Unexpected Randomizer artwork archive')
                for name in ('prepare_rom.py', 'prepare_resources.py', 'assets/zelda_ootr_assets.zar',
                             'COPYING', 'NOTICE.md', 'UPSTREAM-LICENSE.md'):
                    replacements['project/tools/randomizer/' + name] = (source / name).read_bytes()
                replacements['project/tools/native/rom_setup.py'] = (source.parent/'native/rom_setup.py').read_bytes()
            updated = stage / 'preparation-kit.zip'
            with zipfile.ZipFile(updated, 'w', compression=zipfile.ZIP_DEFLATED) as output:
                for entry in original.infolist():
                    if entry.filename not in replacements:
                        from copy import copy as copy_entry
                        with original.open(entry) as data, output.open(copy_entry(entry), 'w') as copy:
                            shutil.copyfileobj(data, copy)
                    if entry.filename.startswith('engine/') and not entry.is_dir():
                        name = 'randomizer-' + entry.filename
                        if name not in replacements:
                            with original.open(entry.filename) as data, output.open(name, 'w') as copy:
                                shutil.copyfileobj(data, copy)
                for name, contents in replacements.items():
                    output.writestr(name, contents)
        updated.replace(archive)
    from preparation_identity import stream_hash
    metadata = assets / 'preparation-kit.json'
    manifest = json.loads(metadata.read_text())
    with archive.open('rb') as stream:
        manifest['sha256'] = stream_hash(stream)
    with zipfile.ZipFile(archive) as bundle:
        manifest['unpacked_bytes'] = sum(entry.file_size for entry in bundle.infolist())
    metadata.write_text(json.dumps(manifest, sort_keys=True) + '\n')


def prepare(engine, private_kit=None, preparation_native_stage=None, private_randomizer=False, randomizer_recipe=None):
    if randomizer_recipe and (private_kit or private_randomizer or preparation_native_stage is None):
        raise ValueError('Choose a public preparation kit and native host for a release recipe.')
    if private_randomizer and (private_kit is None or preparation_native_stage is None):
        raise ValueError('Randomizer test tools require a private preparation kit and native stage.')
    root = Path(engine) / 'ports/android'
    shutil.copytree(Path(__file__).parent/'android/drawable',root/'app/src/main/res/drawable',dirs_exist_ok=True)
    notices=root/'app/src/main/assets/licenses'
    notices.mkdir(parents=True,exist_ok=True)
    randomizer_notices = notices / 'randomizer'
    randomizer_notices.mkdir(exist_ok=True)
    for name in ('NOTICE.md', 'COPYING', 'UPSTREAM-LICENSE.md'):
        shutil.copy2(Path(__file__).parents[1] / 'randomizer' / name, randomizer_notices / name)
    shutil.copytree(Path(__file__).parents[2]/'resources/licenses/android-driver',notices/'android-driver',dirs_exist_ok=True)
    shutil.copy2(Path(__file__).parents[2]/'resources/fonts/LICENSE.txt',notices/'interface-font-OFL.txt')
    shutil.copytree(Path(__file__).parents[2]/'resources/licenses/player-models', notices/'player-models', dirs_exist_ok=True)
    shutil.copytree(Path(__file__).resolve().parents[2]/'resources/fonts/interface',notices/'interface-fonts',dirs_exist_ok=True,ignore=shutil.ignore_patterns('*.ttf'))
    shutil.copytree(Path(__file__).parents[2]/'resources/icons/android',root/'app/src/main/res',dirs_exist_ok=True)
    manifest = root/'app/src/main/AndroidManifest.xml'
    manifest.write_text(manifest.read_text().replace('android:icon="@mipmap/ic_launcher"', 'android:icon="@mipmap/ic_launcher_round"'))
    replace(manifest, 'android:allowBackup="false"',
            'android:allowBackup="false" android:icon="@mipmap/ic_launcher_round" android:roundIcon="@mipmap/ic_launcher_round"')
    gradle = root / 'app/build.gradle.kts'
    replace(gradle, 'applicationId = "org.triaevum.android"',
            'applicationId = "io.github.otpr26.ocarinaretuned"')
    text = gradle.read_text()
    for previous in ('0.1-intro-dev', '0.1.0-native-prototype', '0.1.0-preview', '0.1.2-preview', '0.1.3-preview', '0.1.4-preview', '0.2.0-preview', '0.5.0', '0.5.1-rc1', '0.5.5', '0.5.6', '0.5.7', '0.5.8', '0.5.9', '2.6.0', '0.6.1', '0.6.2', '0.6.3', '0.6.4', '0.6.5', '0.6.6', '0.6.7', '0.6.8', '0.6.9', '0.6.10', '0.7.0', '0.8.0'):
        text = text.replace('versionName = "' + previous + '"', 'versionName = "0.8.1"')
    if 'versionName = "0.8.1"' not in text:
        raise ValueError('Android Preview version context changed')
    text = re.sub(r'\bversionCode = [0-9]+\b', 'versionCode = 26', text)
    if 'versionCode = 26' not in text: raise ValueError('Android version code context changed')
    gradle.write_text(text)
    shutil.copy2(Path(__file__).with_name('preparation_identity.py'), root/'preparation_identity.py')
    shutil.copy2(Path(__file__).with_name('android_runtime.py'), root/'android_runtime.py')
    shutil.copy2(Path(__file__).with_name('audit_frontend_settings.py'), root/'audit_frontend_settings.py')
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
    for name in ('TouchOverlay.java','TouchLayout.java','ControllerMotion.java','ControllerMotionState.java','TextureFolder.java','InterfaceTypography.java'):
        shutil.copy2(Path(__file__).parent/'android'/name,activity.parent/name)
    if 'private TextureFolder retunedTextures;' not in activity.read_text():
        replace(activity,'public final class TriAevumActivity extends SDLActivity {',
                'public final class TriAevumActivity extends SDLActivity {\n    private TextureFolder retunedTextures;\n    public void retunedChooseTextureFolder(){if(retunedTextures!=null)retunedTextures.choose();}\n    public String retunedTakeTextureFolder(){return retunedTextures==null?"":retunedTextures.take();}\n    public String retunedTextureFolderStatus(){return retunedTextures==null?"":retunedTextures.status();}\n    public byte[] retunedReadTextureFile(String path){return retunedTextures==null?null:retunedTextures.read(path);}\n    @Override protected void onActivityResult(int request,int result,android.content.Intent data){\n        if(request==TextureFolder.REQUEST&&retunedTextures!=null){retunedTextures.result(result,data);return;}\n        super.onActivityResult(request,result,data);\n    }')
    if 'retunedTextures=new TextureFolder(this);' not in activity.read_text():
        replace(activity,'        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);',
                '        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);\n        retunedTextures=new TextureFolder(this);')
    install_randomizer_documents(activity)
    if 'private TouchOverlay touchOverlay;' not in activity.read_text():
        replace(activity,'public final class TriAevumActivity extends SDLActivity {',
                'public final class TriAevumActivity extends SDLActivity {\n    private TouchOverlay touchOverlay;')
    if 'retunedControllerMotion(' not in activity.read_text():
        replace(activity,'    private TouchOverlay touchOverlay;',
                '    private TouchOverlay touchOverlay;\n    public double[] retunedControllerMotion(String name,int vendor,int product){return touchOverlay==null?null:touchOverlay.controllerMotion.sample(name,vendor,product);}')
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
    for name in ('RandomizerSession.java', 'RandomizerRestartActivity.java', 'GraphicsDriver.java', 'GraphicsDriverRestartActivity.java', 'GraphicsDriverPickerActivity.java', 'GraphicsDriverProbeService.java', 'RomSetupActivity.java', 'RomPreparationActivity.java', 'RomPreparationService.java', 'PreparationSession.java', 'PreparationProgress.java', 'GameSession.java', 'PreparationUpdate.java', 'PreparationKit.java', 'SaveFilesCore.java', 'SaveDocumentStore.java', 'SaveFiles.java', 'SaveFilesActivity.java', 'PlayerModelsActivity.java', 'StartupReport.java', 'NativeCrashReport.java', 'StartupDiagnostics.java', 'StartupDiagnosticsActivity.java'):
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
    for kind, name, process in (('activity', '.RandomizerRestartActivity', ':randomizerrestart'), ('activity', '.GraphicsDriverPickerActivity', ':drivers'), ('activity', '.GraphicsDriverRestartActivity', ':driverrestart'), ('service', '.GraphicsDriverProbeService', ':driverprobe')):
        if not any(node.get(attribute('name')) == name for node in application.findall(kind)):
            ET.SubElement(application, kind, {attribute('name'): name, attribute('exported'): 'false', attribute('process'): process})
    for node in list(application.findall('activity')):
        if node.get(attribute('name')) == '.GraphicsDriverActivity': application.remove(node)
        if node.get(attribute('name')) in ('.RandomizerRestartActivity', '.GraphicsDriverPickerActivity', '.GraphicsDriverRestartActivity'):
            node.set(attribute('theme'), '@android:style/Theme.Translucent.NoTitleBar')
            node.set(attribute('configChanges'), 'orientation|screenSize|keyboardHidden')
    old_driver_ui = activity.parent/'GraphicsDriverActivity.java'
    if old_driver_ui.exists(): old_driver_ui.unlink()
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
        ('void retunedStartupException(', '    public void retunedStartupException(String message){StartupDiagnostics.nativeException(this,message);}'),
        ('void retunedStartupCandidate(', '    public void retunedStartupCandidate(int api,int vendor,int driver){StartupDiagnostics.candidate(this,api,vendor,driver);}')):
        if signature not in text:text=text.replace('    private TextureFolder retunedTextures;', method+'\n    private TextureFolder retunedTextures;')
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
    text = re.sub(r'    public void retunedOpenGraphicsDriver\(\)\{[^\n]*\}\n', '', text)
    if 'String retunedGraphicsDriverStatus()' not in text:
        text=text.replace('    @Override public void loadLibraries() {',
            '    public String retunedGraphicsDriverStatus(){return GraphicsDriver.status(this);}\n'
            '    public void retunedUseSystemDriver(){runOnUiThread(()->GraphicsDriver.useSystem(this));}\n'
            '    @Override public void loadLibraries() {')
    text=text.replace('    @Override public void loadLibraries() {',
        '    public void retunedOpenGraphicsDriver(){runOnUiThread(()->GraphicsDriver.choose(this));}\n'
        '    @Override public void loadLibraries() {')
    if 'request==GraphicsDriver.PICK_REQUEST' not in text:
        text=text.replace('        if(request==TextureFolder.REQUEST',
            '        if(request==GraphicsDriver.PICK_REQUEST){GraphicsDriver.result(data);return;}\n        if(request==TextureFolder.REQUEST')
    if 'boolean retunedDriverNeedsRestart()' not in text:
        text=text.replace('    @Override public void loadLibraries() {',
            '    public boolean retunedDriverNeedsRestart(){return GraphicsDriver.needsRestart(this);}\n'
            '    public void retunedRestartForDriver(){runOnUiThread(()->GraphicsDriver.restart(this));}\n'
            '    @Override public void loadLibraries() {')
    if 'GraphicsDriver.load(this' not in text:
        text = text.replace('    @Override public void loadLibraries() {',
            '    @Override public void loadLibraries() {\n        try { GraphicsDriver.load(this,GraphicsDriver.read(this)); android.system.Os.setenv("SDL_VULKAN_LIBRARY",getApplicationInfo().nativeLibraryDir+"/libretuned_vulkan.so",true); }\n        catch(Exception | LinkageError error){StartupDiagnostics.failure(this,error);throw new IllegalStateException("Graphics driver initialization failed",error);}')
    gameplay.write_text(text)
    activity.write_text('package org.triaevum.android;\n/** Stable launcher component preserves existing home-screen shortcuts. */\npublic final class TriAevumActivity extends RomSetupActivity {}\n')
    asset = root/'app/src/main/assets/retuned'
    asset.mkdir(parents=True, exist_ok=True)
    for font in (Path(__file__).parents[2]/'resources/fonts/interface').glob('*.ttf'):
        shutil.copy2(font, asset/font.name)
    shutil.copy2(Path(__file__).parents[2]/'resources/artwork/ocarina-illustration.png', asset/'ocarina-illustration.png')
    python = root/'app/src/main/python'
    python.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(__file__).parent/'android/driver_package.py', python/'driver_package.py')
    shutil.copy2(Path(__file__).parent/'android/retuned_setup_entry.py', python/'retuned_setup_entry.py')
    shutil.copy2(Path(__file__).parent/'android/retuned_models_entry.py', python/'retuned_models_entry.py')
    shutil.copy2(Path(__file__).parent/'android/retuned_lower_art_entry.py', python/'retuned_lower_art_entry.py')
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

    if private_randomizer or randomizer_recipe:
        add_randomizer_tools(asset, randomizer_recipe)
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
    parser.add_argument('--private-randomizer-preparation', action='store_true')
    parser.add_argument('--randomizer-recipe', type=Path)
    args = parser.parse_args()
    prepare(args.engine, args.private_preparation_kit, args.preparation_native_stage,
            args.private_randomizer_preparation, args.randomizer_recipe)
