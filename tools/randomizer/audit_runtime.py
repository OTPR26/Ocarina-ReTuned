#!/usr/bin/env python3
"""Compare ARM patch sections without modifying either mod or a game image."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

def sections(path):
    data=Path(path).read_bytes()
    if data[:7]!=b'\x7fELF\x01\x01\x01' or struct.unpack_from('<H',data,18)[0]!=40:
        raise ValueError('Expected ARM ELF32')
    offset=struct.unpack_from('<I',data,32)[0]
    size,count,names_index=struct.unpack_from('<HHH',data,46)
    if size!=40 or not count or offset+size*count>len(data) or names_index>=count:
        raise ValueError('Invalid section table')
    entries=[struct.unpack_from('<10I',data,offset+i*size) for i in range(count)]
    names=entries[names_index];strings=data[names[4]:names[4]+names[5]]
    result=[]
    for e in entries:
        end=strings.find(b'\0',e[0])
        if e[0]>=len(strings) or end<0:raise ValueError('Invalid section name')
        name=strings[e[0]:end].decode()
        if e[5] and (e[2]&2 or name.startswith('.patch_')):
            result.append({'name':name,'start':e[3],'end':e[3]+e[5],'size':e[5], 'nobits':e[1]==8})
    return result

def audit(hud,runtime):
    hs,rs=sections(hud),sections(runtime)
    overlaps=[]
    for a in hs:
        for b in rs:
            start=max(a['start'],b['start']);end=min(a['end'],b['end'])
            if start<end:overlaps.append({'hud':a['name'],'randomizer':b['name'],'start':hex(start),'bytes':end-start})
    return {'audit_only':True,'ready_to_merge':False,'no_address_overlaps':not overlaps,
            'hud_sha256':hashlib.sha256(Path(hud).read_bytes()).hexdigest(),
            'runtime_sha256':hashlib.sha256(Path(runtime).read_bytes()).hexdigest(),
            'runtime_patch_count':sum(s['name'].startswith('.patch_') for s in rs),
            'runtime_sections':rs,'overlaps':overlaps}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--hud',required=True);p.add_argument('--runtime',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();r=audit(a.hud,a.runtime);Path(a.output).write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({'patches':r['runtime_patch_count'],'overlaps':r['overlaps']},indent=2))
