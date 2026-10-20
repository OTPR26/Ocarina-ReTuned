"""Package the Ocarina artwork at each platform's required icon sizes."""
from pathlib import Path
import argparse,json,shutil,subprocess

def resize(source,target,width,height=None):
    target.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run(['sips','-z',str(height or width),str(width),str(source),'--out',str(target)],check=True,stdout=subprocess.DEVNULL)

def prepare(output):
    root=Path(__file__).resolve().parents[2];output=Path(output)
    icon=root/'resources/artwork/ocarina-icon.png'
    for density,size in [('mdpi',48),('hdpi',72),('xhdpi',96),('xxhdpi',144),('xxxhdpi',192)]:
        resize(icon,output/'android'/('mipmap-'+density)/'ic_launcher.png',size)
        resize(icon,output/'android'/('mipmap-'+density)/'ic_launcher_round.png',size)
    asset=output/'apple/Assets.xcassets/AppIcon.appiconset';asset.mkdir(parents=True,exist_ok=True)
    resize(icon,asset/'AppIcon.png',1024)
    (asset/'Contents.json').write_text(json.dumps({'images':[{'idiom':'universal','platform':'ios','size':'1024x1024','filename':'AppIcon.png'}],'info':{'version':1,'author':'OTPR26'}},indent=2))
    iconset=output/'macos/OcarinaReTuned.iconset'
    for logical in [16,32,128,256,512]:
        resize(icon,iconset/f'icon_{logical}x{logical}.png',logical)
        resize(icon,iconset/f'icon_{logical}x{logical}@2x.png',logical*2)
    subprocess.run(['iconutil','-c','icns',str(iconset),'-o',str(output/'macos/OcarinaReTuned.icns')],check=True)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);prepare(p.parse_args().output)
