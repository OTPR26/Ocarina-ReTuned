#!/usr/bin/env python3
"""Install the verified bundled Reframed UI resources into a local ROM copy.

No network access or generated artwork is involved. Resource bytes are supplied
by the package builder; this source file contains only their integrity contract.
"""
from pathlib import Path, PurePosixPath
import hashlib
import json
import stat
import struct
import zipfile

CONTRACT = Path(__file__).with_name('native_ui_resources.json')
MAX_PACK_BYTES = 16 * 1024 * 1024


def read_pack(path):
    """Verify the complete resource/notice set before changing any game data."""
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_PACK_BYTES:
        raise ValueError('Missing or invalid bundled UI resource pack')
    contract = json.loads(CONTRACT.read_text())
    expected = {'romfs/' + name: info for name, info in contract['resources'].items()}
    expected.update(contract['notices'])
    result = {}
    with zipfile.ZipFile(path) as archive:
        for entry in archive.infolist():
            name = entry.filename
            part = PurePosixPath(name)
            if (name in result or name not in expected or part.is_absolute() or
                    '..' in part.parts or '\\' in name or entry.flag_bits & 1 or
                    stat.S_ISLNK(entry.external_attr >> 16) or
                    entry.file_size != expected[name]['bytes']):
                raise ValueError('Invalid bundled UI resource entry')
            data = archive.read(entry)
            if hashlib.sha256(data).hexdigest() != expected[name]['sha256']:
                raise ValueError('Bundled UI resource integrity check failed')
            result[name] = data
    if result.keys() != expected.keys():
        raise ValueError('Bundled UI resource pack is incomplete')
    return contract, result


class RomFs:
    """Bounded Level-3 reader retaining file-record offsets for local rewrites."""
    def __init__(self,path):
        from pathlib import Path
        self.path=Path(path)
        if self.path.is_symlink() or not self.path.is_file():raise ValueError('Expected regular local RomFS')
        self.size=self.path.stat().st_size
        with self.path.open('rb') as f:
            header=f.read(40)
            if len(header)!=40:raise ValueError('Truncated RomFS header')
            h=struct.unpack('<10I',header)
            if h[0]!=40 or h[9]>self.size:raise ValueError('Expected normalized Level-3 RomFS')
            end=40
            for start,length in ((h[1],h[2]),(h[3],h[4]),(h[5],h[6]),(h[7],h[8])):
                if start<end or start%4 or not 0<length<=16*1024*1024 or start+length>self.size:
                    raise ValueError('Invalid RomFS metadata bounds')
                end=start+length
            if h[9]<end or h[9]%16:raise ValueError('Invalid RomFS data offset')
            f.seek(h[3]);dirs=f.read(h[4]);f.seek(h[7]);files=f.read(h[8])
        self.data_offset,self.file_table=h[9],h[7]
        self.files={};seen_dirs=set();seen_files=set();pending=[(0,'',0)]
        def name(table,at,fixed):
            if at%4 or at<0 or at+fixed>len(table):raise ValueError('Invalid RomFS record')
            length=struct.unpack_from('<I',table,at+fixed-4)[0]
            if length%2 or at+fixed+length>len(table):raise ValueError('Invalid RomFS name bounds')
            text=table[at+fixed:at+fixed+length].decode('utf-16-le')
            if '/' in text or '\\' in text or '\0' in text or text in ('.','..'):raise ValueError('Invalid RomFS path')
            return text
        invalid=0xffffffff
        while pending:
            at,prefix,owner=pending.pop()
            if at in seen_dirs:raise ValueError('Cyclic RomFS directory')
            text=name(dirs,at,24);seen_dirs.add(at)
            parent,sibling,child,file,chain,length=struct.unpack_from('<6I',dirs,at)
            if parent!=owner or (at==0 and (text or sibling!=invalid)) or (at and not text):raise ValueError('Invalid RomFS directory ancestry')
            full=prefix+'/'+text if prefix else text
            if sibling!=invalid:pending.append((sibling,prefix,owner))
            if child!=invalid:pending.append((child,full,at))
            while file!=invalid:
                if file in seen_files:raise ValueError('Cyclic RomFS file')
                text=name(files,file,32);seen_files.add(file)
                parent,following,offset,size,chain,length=struct.unpack_from('<IIQQII',files,file)
                path=full+'/'+text if full else text
                if parent!=at or not text or path in self.files or h[9]+offset+size>self.size:raise ValueError('Invalid RomFS file extent')
                self.files[path]=(file,offset,size);file=following

    def read(self,name):
        at,offset,size=self.files[name]
        if size>16*1024*1024:raise ValueError('Native UI resource exceeds size limit')
        with self.path.open('rb') as f:
            f.seek(self.data_offset+offset);data=f.read(size)
        if len(data)!=size:raise ValueError('Truncated native UI resource')
        return data

    def write_replacements(self,destination,replacements):
        from pathlib import Path
        import shutil
        destination=Path(destination)
        if destination.exists() or destination.is_symlink() or destination.resolve()==self.path.resolve():raise ValueError('UI preparation needs a new local output')
        for name,data in replacements.items():
            if name not in self.files or not 0<len(data)<=16*1024*1024:raise ValueError('Invalid native UI replacement')
        temporary=destination.with_name(destination.name+'.partial')
        created=False
        try:
            # Exclusive creation never overwrites a previous interrupted fixture.
            with temporary.open('xb') as output,self.path.open('rb') as source:
                created=True
                shutil.copyfileobj(source,output,4*1024*1024)
                for name,data in sorted(replacements.items()):
                    output.seek(0,2);end=output.tell();aligned=(end+15)&~15
                    output.write(bytes(aligned-end));output.write(data)
                    record=self.files[name][0]
                    output.seek(self.file_table+record+8)
                    output.write(struct.pack('<QQ',aligned-self.data_offset,len(data)))
            temporary.replace(destination)
        except BaseException:
            if created:temporary.unlink(missing_ok=True)
            raise


def prepare(source, destination, *, resources, notices_directory=None):
    """Apply the fixed UI contract, preserving the user's original ROM."""
    contract, entries = read_pack(resources)
    replacements = {name: entries['romfs/' + name] for name in contract['resources']}
    rom = RomFs(source)
    # All six paths must exist in the normalized supported ROM.
    if not replacements.keys() <= rom.files.keys():
        raise ValueError('The ROM lacks the supported UI resource paths')
    if notices_directory is not None:
        target = Path(notices_directory)
        target.mkdir()
        for name in contract['notices']:
            (target / PurePosixPath(name).name).write_bytes(entries[name])
    rom.write_replacements(destination, replacements)
    return {'format': 'retuned_native_ui_assets_v2',
            'source_sha256': contract['source_sha256'],
            'pack_sha256': hashlib.sha256(Path(resources).read_bytes()).hexdigest(),
            'resources': contract['resources'], 'notices': contract['notices'],
            'texture_hash_aliases': contract.get('texture_hash_aliases', [])}


def verify_font_coverage(path):
    """Validate an explicitly supplied local HD pack against the bundled font."""
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_PACK_BYTES:
        raise ValueError('Invalid local font coverage pack')
    contract = json.loads(CONTRACT.read_text())
    expected_native = contract['resources']['message/eu/ltn16.qbf']['sha256']
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        if len(names) != len(set(names)) or sum(e.file_size for e in entries) > MAX_PACK_BYTES:
            raise ValueError('Invalid font coverage archive')
        for entry in entries:
            name = PurePosixPath(entry.filename)
            if (name.is_absolute() or '..' in name.parts or '\\' in entry.filename or
                    entry.flag_bits & 1 or stat.S_ISLNK(entry.external_attr >> 16)):
                raise ValueError('Invalid font coverage entry')
        if archive.getinfo('manifest.json').file_size > 1024 * 1024:
            raise ValueError('Oversized font coverage manifest')
        manifest = json.loads(archive.read('manifest.json'))
        if manifest.get('format') != 'oot3d_qbf_coverage_v1' or len(manifest.get('fonts', [])) != 1:
            raise ValueError('Unsupported font coverage pack')
        font = manifest['fonts'][0]
        if font.get('romfs_path') != 'message/eu/ltn16.qbf' or font.get('native_sha256') != expected_native:
            raise ValueError('Font coverage does not match bundled UI')
        expected_names = {'manifest.json', font['native_file'], font['coverage_file']}
        if manifest.get('name') == 'ReTuned Dialogue' and manifest.get('license') == 'OFL-1.1':
            notice = 'licenses/ReTuned-Dialogue-OFL.txt'
            expected_names.add(notice)
            if archive.read(notice) != (Path(__file__).resolve().parents[2] / 'resources/fonts/LICENSE.txt').read_bytes():
                raise ValueError('Missing or changed font license notice')
        if set(names) != expected_names:
            raise ValueError('Unexpected font coverage files')
        for field in ('native', 'coverage'):
            if hashlib.sha256(archive.read(font[field + '_file'])).hexdigest() != font[field + '_sha256']:
                raise ValueError('Font coverage integrity check failed')
    return {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size}
