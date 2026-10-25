"""Build an isolated UIKit layout probe with the explicitly selected Xcode.

Run with DEVELOPER_DIR pointing to Xcode 27.1 or later. This builds only a
simulator diagnostic, not a playable game or a distribution package.
"""
import argparse
import os
from pathlib import Path
import plistlib
import subprocess


def build(output):
    root = Path(__file__).resolve().parents[2]
    if not os.environ.get('DEVELOPER_DIR'):
        raise ValueError('Select Xcode explicitly with DEVELOPER_DIR')
    sdk = subprocess.check_output(['xcrun', '--sdk', 'iphonesimulator', '--show-sdk-version'],
                                  text=True).strip()
    if tuple(int(part) for part in sdk.split('.')) < (27, 1):
        raise ValueError('The Duo simulator probe requires the iOS 27.1 SDK or later')
    output = output.resolve()
    if output.suffix != '.app':
        raise ValueError('Choose a dedicated .app output folder')
    identity = 'io.github.otpr26.ocarinaretuned.displayprobe'
    plist = output / 'Info.plist'
    if output.exists() and any(output.iterdir()):
        if not plist.exists() or plistlib.loads(plist.read_bytes()).get('CFBundleIdentifier') != identity:
            raise ValueError('Refusing to replace a different application')
    output.mkdir(parents=True, exist_ok=True)
    plist.write_bytes(plistlib.dumps({
        'CFBundleIdentifier': identity,
        'CFBundleExecutable': 'OcarinaDisplayProbe',
        'CFBundleName': 'Ocarina Display Probe',
        'CFBundleDisplayName': 'Ocarina Display Probe',
        'CFBundlePackageType': 'APPL',
        'CFBundleVersion': '1',
        'CFBundleShortVersionString': '1.0',
        'MinimumOSVersion': '17.0',
        'LSRequiresIPhoneOS': True,
        'NSMotionUsageDescription': 'Inspect fold posture in this isolated display test.',
        'UIDeviceFamily': [1, 2],
        'UILaunchScreen': {},
        'UISupportedInterfaceOrientations': ['UIInterfaceOrientationPortrait',
            'UIInterfaceOrientationPortraitUpsideDown',
            'UIInterfaceOrientationLandscapeLeft', 'UIInterfaceOrientationLandscapeRight'],
        'UIApplicationSceneManifest': {'UIApplicationSupportsMultipleScenes': False,
            'UISceneConfigurations': {'UIWindowSceneSessionRoleApplication': [{
                'UISceneConfigurationName': 'Probe', 'UISceneDelegateClassName': 'RetunedProbeScene'}]}}
    }))
    subprocess.run(['xcrun', '--sdk', 'iphonesimulator', 'clang++', '-std=c++20',
        '-target', 'arm64-apple-ios17.0-simulator', '-fobjc-arc', '-fblocks',
        '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter', '-Wno-deprecated-declarations',
        '-ffile-prefix-map=' + str(root) + '=/retuned',
        '-I', str(root / 'tools/frontend'), '-I', str(root / 'tools/native/apple'),
        str(root / 'tests/apple/duo_display_probe.mm'),
        str(root / 'tools/native/apple/duo_layout_observer.mm'),
        '-framework', 'UIKit', '-framework', 'Foundation', '-framework', 'CoreGraphics',
        '-framework', 'CoreMotion',
        '-o', str(output / 'OcarinaDisplayProbe')], check=True)
    subprocess.run(['codesign', '--force', '--sign', '-', '--timestamp=none', str(output)], check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    build(parser.parse_args().output)
