#!/usr/bin/env python3
"""Configure the neutral development APK; title libraries stay outside the APK."""
from pathlib import Path
import argparse
import shutil


def replace(path, before, after):
    source = path.read_text()
    if after in source:
        return
    if source.count(before) != 1:
        raise ValueError('Android app context changed: ' + str(path))
    path.write_text(source.replace(before, after))


def prepare(engine):
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
    replace(gradle, '    compileOptions {',
            '    buildTypes { getByName("release") { isDebuggable = true } }\n    compileOptions {')
    replace(gradle, '"triaevum_title_bootstrap", "triaevum_title_aot", "c++_shared"',
            '"triaevum_title_bootstrap", "c++_shared"')
    replace(root / 'app/src/main/AndroidManifest.xml',
            'android:label="TriAevum — Echoes of Time"', 'android:label="Ocarina ReTuned"')
    activity = root / 'app/src/main/java/org/triaevum/android/TriAevumActivity.java'
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('engine', type=Path)
    prepare(parser.parse_args().engine)
