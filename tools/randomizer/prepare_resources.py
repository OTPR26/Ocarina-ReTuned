#!/usr/bin/env python3
"""Prepare private test RomFS with UI replacements and one randomizer archive."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'native'))
from prepare_ui_assets import RomFs, read_pack, localized_menu_resources

DEFAULT_ARCHIVE = Path(__file__).with_name('assets') / 'zelda_ootr_assets.zar'
ARCHIVE_SHA256 = '84735e0df767a19ce5090e369d82d0cc716a837bbde338a64776bd40e3e9dab2'

def name_hash(parent,name):
    value=parent^123456789
    raw=name.encode('utf-16-le')
    for (unit,) in struct.iter_unpack('<H',raw):
        value=((value>>5)|(value<<27))&0xffffffff
        value^=unit
    return value

def prepare(source,destination,archive,ui):
    if destination.exists():raise ValueError('Refusing to replace private RomFS')
    rom=RomFs(source);name='actor/zelda_ootr_assets.zar'
    if name in rom.files:raise ValueError('Randomizer archive already exists')
    data=archive.read_bytes()
    if hashlib.sha256(data).hexdigest() != ARCHIVE_SHA256:
        raise ValueError('Randomizer artwork does not match the pinned upstream archive')
    contract,entries=read_pack(ui)
    replacements=localized_menu_resources({n:entries['romfs/'+n] for n in contract['resources']},rom.files)
    with source.open('rb') as f:prefix=bytearray(f.read(rom.data_offset))
    header=list(struct.unpack_from('<10I',prefix))
    fileStart=header[7];table=bytearray(prefix[fileStart:fileStart+header[8]])
    known=rom.files['actor/zelda_gi_melody.zar'][0]
    parent=struct.unpack_from('<I',table,known)[0]
    buckets=header[6]//4
    bucket=name_hash(parent,'zelda_gi_melody.zar')%buckets
    cursor=struct.unpack_from('<I',prefix,header[5]+bucket*4)[0];seen=set()
    while cursor!=0xffffffff and cursor!=known:
        if cursor in seen or cursor+32>len(table):raise ValueError('Invalid existing hash chain')
        seen.add(cursor);cursor=struct.unpack_from('<I',table,cursor+24)[0]
    if cursor!=known:raise ValueError('Unexpected RomFS hash algorithm')
    directory=header[3]+parent
    previous=struct.unpack_from('<I',prefix,directory+12)[0]
    bucket=name_hash(parent,'zelda_ootr_assets.zar')%buckets
    chain=struct.unpack_from('<I',prefix,header[5]+bucket*4)[0]
    record=len(table);encoded='zelda_ootr_assets.zar'.encode('utf-16-le')
    table.extend(struct.pack('<IIQQII',parent,previous,0,len(data),chain,len(encoded))+encoded)
    while len(table)%4:table.append(0)
    struct.pack_into('<I',prefix,directory+12,record)
    struct.pack_into('<I',prefix,header[5]+bucket*4,record)
    header[8]=len(table);header[9]=(fileStart+len(table)+15)&~15
    metadata=prefix[:fileStart]+table
    metadata.extend(bytes(header[9]-len(metadata)));struct.pack_into('<10I',metadata,0,*header)
    additions=[(record,data)]+[(rom.files[n][0],b) for n,b in sorted(replacements.items())]
    temporary=destination.with_suffix('.partial')
    created=False
    try:
        with temporary.open('xb') as output,source.open('rb') as input:
            created=True;output.write(metadata);input.seek(rom.data_offset);shutil.copyfileobj(input,output,4*1024*1024)
            for at,blob in additions:
                output.seek(0,2);end=output.tell();aligned=(end+15)&~15
                output.write(bytes(aligned-end));output.write(blob)
                output.seek(fileStart+at+8);output.write(struct.pack('<QQ',aligned-header[9],len(blob)))
        check=RomFs(temporary)
        if check.read(name)!=data:raise ValueError('Resource roundtrip failed')
        for n,b in replacements.items():
            if check.read(n)!=b:raise ValueError('UI resource roundtrip failed')
        temporary.rename(destination)
    except BaseException:
        if created:temporary.unlink(missing_ok=True)
        raise
    return {'private_test_only':True,'resource_sha256':hashlib.sha256(data).hexdigest(),
            'texture_hash_aliases':contract.get('texture_hash_aliases',[]),'files':len(check.files)}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','output','ui'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--archive', type=Path, default=DEFAULT_ARCHIVE)
    a=p.parse_args();result=prepare(a.source,a.output,a.archive,a.ui)
    a.output.with_suffix('.receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Private resource image verified')
