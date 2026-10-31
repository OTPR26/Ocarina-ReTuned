"""Apply neutral UIKit lifecycle and asset-catalog metadata to a built host."""
from pathlib import Path
import argparse,plistlib,sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from audit_frontend_settings import verify as verify_frontend_settings

def finalize(app,platform,icons):
    path=Path(app)/'Info.plist'
    data=plistlib.loads(path.read_bytes())
    verify_frontend_settings(Path(app)/data['CFBundleExecutable'],require_dual=platform=='ios')
    data.update(plistlib.loads(Path(icons).read_bytes()))
    data.update(CFBundleDisplayName='Ocarina ReTuned',CFBundleShortVersionString='2.6.0',CFBundleVersion='14',MinimumOSVersion='17.0',LSRequiresIPhoneOS=True,
        UIDeviceFamily=[3] if platform=='tvos' else [1,2],
        UISupportedInterfaceOrientations=['UIInterfaceOrientationLandscapeLeft','UIInterfaceOrientationLandscapeRight'],
        UIApplicationSceneManifest={'UIApplicationSupportsMultipleScenes':False,'UISceneConfigurations':{'UIWindowSceneSessionRoleApplication':[{'UISceneConfigurationName':'Game','UISceneDelegateClassName':'RetunedSceneDelegate'}]}})
    if platform=='ios':
        data['UILaunchScreen']={}
        data['NSMotionUsageDescription']='Use device motion for in-game aiming.'
    path.write_bytes(plistlib.dumps(data))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('app');p.add_argument('platform',choices=['ios','tvos']);p.add_argument('icons');a=p.parse_args();finalize(a.app,a.platform,a.icons)
