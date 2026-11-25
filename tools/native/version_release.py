from pathlib import Path
import hashlib,json,plistlib,subprocess as s,struct,tempfile,zipfile,shutil
root=Path.cwd()
URL='https://github.com/OTPR26/Ocarina-ReTuned/releases/download/v0.8.0/'
expected={'Mac':'4012410d11475ed71f687bf632ba0695d0b9a0cb6ae28a866872de111bc04258','Windows-x64':'338457e04779cb0f4539738d5d92722ae6a90fb58fe7e80d722405731efe459f'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(*args):s.run(args,check=True)
out=root/'hotfix';out.mkdir()
for platform,digest in expected.items():
    name=f'Ocarina-ReTuned-0.8.0-{platform}.zip'
    with tempfile.TemporaryDirectory() as temp:
        t=Path(temp);archive=t/name
        run('curl','-fsSL','--retry','3',URL+name,'-o',archive)
        assert sha(archive)==digest
        run('ditto','-x','-k',archive,t/'pkg')
        package=next((t/'pkg').iterdir())
        mac=platform=='Mac'
        exe=package/('Contents/MacOS/retuned-native' if mac else 'OcarinaReTuned.exe')
        initial=exe.read_bytes()
        data=initial.replace(b'0.8.0 Preview',b'0.8.1 Preview')
        assert data!=initial
        if mac:
            exe.write_bytes(data)
            plist=package/'Contents/Info.plist';d=plistlib.loads(plist.read_bytes())
            assert d['CFBundleShortVersionString']=='0.8.0'
            d.update(CFBundleShortVersionString='0.8.1',CFBundleVersion='26')
            plist.write_bytes(plistlib.dumps(d))
            run('codesign','--force','--sign','-',exe)
            run('codesign','--force','--sign','-',package)
            run('codesign','--verify','--deep','--strict',package)
            run(exe,'--product-info')
        else:
            data=data.replace('0.8.0 Preview'.encode('utf-16le'),'0.8.1 Preview'.encode('utf-16le'))
            fixed=lambda minor:struct.pack('<6I',0xfeef04bd,0x10000,8,minor,8,minor)
            assert data.count(fixed(25))==1
            exe.write_bytes(data.replace(fixed(25),fixed(65536+26)))
            abi=package/'preparation-abi.json';a=json.loads(abi.read_text());a['host_sha256']=sha(exe);abi.write_text(json.dumps(a,indent=2)+'\n')
            start=package/'START-HERE.txt';start.write_bytes(start.read_bytes().replace(b'Preview 0.6.9',b'Preview 0.8.1'))
            hotfix=package/'HOTFIX.txt';hotfix.write_text('Ocarina ReTuned Preview 0.8.1\nIncludes the shader compiler libraries required for startup.\n')
            m=package/'package-manifest.json';d=json.loads(m.read_text());d['version']='0.8.1'
            for f in (abi,exe,start,hotfix):
                if f.name in d['files']:d['files'][f.name]=sha(f)
            m.write_text(json.dumps(d,indent=2)+'\n')
        final=out/name.replace('0.8.0','0.8.1')
        run('ditto','-c','-k','--keepParent','--norsrc','--noextattr',package,final)
        print(final.name,sha(final),flush=True)
