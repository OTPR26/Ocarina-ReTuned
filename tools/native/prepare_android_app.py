#!/usr/bin/env python3
"""Configure the neutral development APK; title libraries stay outside the APK."""
from pathlib import Path
import argparse


def replace(path, before, after):
    source = path.read_text()
    if after in source:
        return
    if source.count(before) != 1:
        raise ValueError('Android app context changed: ' + str(path))
    path.write_text(source.replace(before, after))


def prepare(engine):
    root = Path(engine) / 'ports/android'
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
    replace(activity,
            'new File(getApplicationInfo().nativeLibraryDir,\n                "libtriaevum_title_aot.so")',
            'new File(getFilesDir(), "native/triaevum_title_aot.so")')
    replace(activity, '"TriAevum.android.launch.json"', '"native-launch.json"')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('engine', type=Path)
    prepare(parser.parse_args().engine)
