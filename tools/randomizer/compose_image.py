#!/usr/bin/env python3
"""Build a private, non-activated combined image from verified local inputs."""
import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
from plan_hooks import plan
from validate_seed import validate

BASE=0x100000
RUNTIME=0x680000
LIMIT=0x800000

def helper():
    path=Path(__file__).resolve().parents[1]/'reframed/prepare_native_image.py'
    spec=importlib.util.spec_from_file_location('native_image',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def elf_sections(path):
    data=path.read_bytes()
    if data[:7]!=b'\x7fELF\x01\x01\x01' or struct.unpack_from('<H',data,18)[0]!=40:
        raise ValueError('Expected ARM ELF32')
    start=struct.unpack_from('<I',data,32)[0]
    stride,count,names=struct.unpack_from('<HHH',data,46)
    if stride!=40 or start+stride*count>len(data) or names>=count:raise ValueError('Invalid ELF sections')
    sections=[struct.unpack_from('<10I',data,start+i*stride) for i in range(count)]
    table=sections[names];strings=data[table[4]:table[4]+table[5]]
    result={}
    for s in sections:
        if s[0]>=len(strings):raise ValueError('Invalid ELF name')
        end=strings.find(b'\0',s[0])
        if end<0:raise ValueError('Invalid ELF name terminator')
        name=strings[s[0]:end].decode()
        if name=='.text' or name.startswith('.patch_'):
            if s[1]==8 or s[4]+s[5]>len(data):raise ValueError('Invalid patch section')
            if name in result:raise ValueError('Duplicate section')
            result[name]=(s[3],data[s[4]:s[4]+s[5]])
    return result


def compose(args):
    if args.output.exists():raise ValueError('Refusing to replace a private experiment')
    module=helper()
    policy=json.loads(Path(__file__).with_name('hook_policy.json').read_text())
    decision=plan(args.hud,args.runtime,json.loads(args.receipt.read_text()),policy)
    manifest=json.loads((args.image/'process-manifest.json').read_text())
    preparation=json.loads((args.image/'preparation.json').read_text())
    image=bytearray((args.image/'code.bin').read_bytes())
    if hashlib.sha256(image).hexdigest()!=manifest['source']['code_bin_sha256']:
        raise ValueError('Prepared ReFramed image hash mismatch')
    if preparation['base_sha256']!=module.BASE_SHA256:raise ValueError('Wrong canonical base')
    # Bind the ReFramed image to the exact ELF used for composed calls.
    if preparation.get('mod_elf_sha256')!=decision['hud_sha256']:
        raise ValueError('Prepared image lacks matching HUD ELF receipt')
    if len(image)+BASE>=RUNTIME:raise ValueError('ReFramed overlaps runtime reservation')
    sections=elf_sections(args.runtime)
    address,payload=sections['.text']
    if address!=RUNTIME or address+len(payload)>LIMIT:raise ValueError('Invalid runtime reservation')
    image.extend(bytes(address+len(payload)-BASE-len(image)))
    image[address-BASE:address-BASE+len(payload)]=payload
    intervals=[]
    # SariaUI also leaves the libctru framebuffer overlay and lifecycle hooks
    # out of its payload activation. ReTuned owns those native UI paths.
    presentation_exclusions={'.patch_Gfx_Update','.patch_AwakeCallback',
        '.patch_SleepQueryCallback','.patch_TitleLinkObject','.patch_GameOverMenuSkip'}
    for name,(address,data) in sections.items():
        if not name.startswith('.patch_') or name in policy['keep_reframed'] or name in presentation_exclusions:continue
        # This pinned assembly fragment has no linker placement. It is a lone
        # NOP, not a patch at guest address zero; reject any changed form.
        if name=='.patch_SwordTrailDurationGrezzoFix':
            if address!=0 or data!=struct.pack('<I',0xe320f000):raise ValueError('Unplaced patch changed')
            continue
        if not BASE<=address or address+len(data)>0x5c7000:raise ValueError('Patch outside canonical game')
        image[address-BASE:address-BASE+len(data)]=data
        intervals.append((address,len(data)))
    symbols={name:(address,size) for address,size,kind,name,_ in module.read_elf_symbols(args.runtime)}
    independent = getattr(args, "seed_independent", False)
    unseeded = bytes(image)
    seed=json.loads(args.seed.read_text());abi=validate(seed,symbols)
    for name,encoded in seed['runtime_fields_hex'].items():
        address,capacity=symbols[name];data=bytes.fromhex(encoded)
        image[address-BASE:address-BASE+capacity]=data+bytes(capacity-len(data))
    patches=seed.get('native_patches',[]);seen=set()
    allowed={0x52236c:22,0x54c222:108,0x54c8b0:14}
    for patch in patches:
        address=patch['address'];data=bytes.fromhex(patch['data_hex'])
        if address in seen or len(data)!=allowed.get(address):raise ValueError('Unexpected seed patch')
        seen.add(address);image[address-BASE:address-BASE+len(data)]=data
    messageBase=symbols['rCustomMessages'][0]
    if messageBase!=BASE+len(image):raise ValueError('Unexpected message append address')
    messages=bytes.fromhex(seed['message_data_hex']);image.extend(messages)
    while len(image)%4:image.append(0)
    entryAddress=BASE+len(image);entries=bytearray.fromhex(seed['message_entries_hex'])
    for offset in range(0,len(entries),0x60):
        for language in range(10):
            at=offset+16+language*8;position,length=struct.unpack_from('<II',entries,at)
            if length:struct.pack_into('<I',entries,at,messageBase+position)
    image.extend(entries)
    if BASE+len(image)>LIMIT:raise ValueError('Combined image exceeds reservation')
    for name,value in [('ptrCustomMessageEntries',entryAddress),('numCustomMessageEntries',len(entries)//0x60)]:
        address,size=symbols[name]
        if size!=4 or not RUNTIME<=address<messageBase-3:raise ValueError('Invalid message pointer symbol')
        struct.pack_into('<I',image,address-BASE,value)
    if independent:
        # Reserve a fixed message arena and trap address. Seed contents must
        # never change the image translated into the installed native module.
        image = bytearray(unseeded)
        for name in seed['runtime_fields_hex']:
            address,capacity=symbols[name]
            image[address-BASE:address-BASE+capacity]=bytes(capacity)
        for name in ('ptrCustomMessageEntries','numCustomMessageEntries'):
            address,size=symbols[name]
            image[address-BASE:address-BASE+size]=bytes(size)
        image.extend(bytes(LIMIT-8-BASE-len(image)))
    with (args.image/'inventory.csv').open(newline='') as f:
        reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
    known={int(r['entry'],0) for r in rows}
    eligible=[s for s in module.elf_symbols(None,args.runtime) if RUNTIME<=s[0]<messageBase]
    additions=[]
    for address,size,kind,name,section in sorted(eligible,key=lambda s:(s[0],s[2]!='FUNC',s[3])):
        if address in known or name=='__text_end':continue
        if not size:
            following=min((a for a,_,_,_,sec in eligible if sec==section and a>address),default=None)
            if following is None:raise ValueError('Unbounded runtime entry: '+name)
            size=following-address
        if address%4 or size%4 or address+size>messageBase:raise ValueError('Invalid runtime entry: '+name)
        row=dict.fromkeys(fields,'');row.update(profile='randomizer_eur',entry=hex(address),end=hex(address+size-1),size=str(size),name='randomizer_'+name,memory_block='randomizer_text')
        rows.append(row);known.add(address);additions.append(dict(entry=address,size=size,name=name))
    observed=json.loads((args.image/'observed-sites.json').read_text())
    resumes=module.adjusted_return_sites(image,intervals,additions)
    sites={int(s['pc'],0) for s in observed['sites']}|set(resumes)
    # GCC emits UDF after unreachable/null-dereference paths. The native
    # translator does not model UDF as a terminator. Route only ARM-mapped UDF
    # words to a dedicated unsupported service, which the host faults on.
    mappings=sorted((a,n[1]) for a,_,_,n,_ in module.read_elf_symbols(args.runtime)
                    if n.startswith(('$a','$d','$t')) and RUNTIME<=a<messageBase)
    traps=[]
    for i,(start,mode) in enumerate(mappings):
        end=mappings[i+1][0] if i+1<len(mappings) else messageBase
        if mode!='a':continue
        for pc in range(start,end-3,4):
            if struct.unpack_from('<I',image,pc-BASE)[0]==0xe7f000f0:traps.append(pc)
    if traps:
        while len(image)%4:image.append(0)
        trap=BASE+len(image);image.extend(struct.pack('<II',0xeffff4ff,0xe12fff1e))
        for pc in traps:
            displacement=trap-(pc+8)
            if displacement%4 or not -(1<<25)<=displacement<(1<<25):raise ValueError('Trap branch out of range')
            struct.pack_into('<I',image,pc-BASE,0xea000000|((displacement>>2)&0xffffff))
        row=dict.fromkeys(fields,'');row.update(profile='randomizer_eur',entry=hex(trap),end=hex(trap+7),
            size='8',name='randomizer_UndefinedInstructionTrap',memory_block='randomizer_text')
        rows.append(row)
    if BASE+len(image)>LIMIT:raise ValueError('Trap exceeds reserved image')
    digest=hashlib.sha256(image).hexdigest()
    observed.update(code_sha256=digest,sites=[{'pc':hex(pc),'reason':'combined mod return'} for pc in sorted(sites)])
    size=len(image)-(RUNTIME-BASE)
    manifest['process']['segments'].append(dict(name='randomizer',address=RUNTIME,mapped_size=(size+4095)&~4095,declared_code_size=size,file_offset=RUNTIME-BASE,file_size=size,writable=True,executable=True))
    manifest['source'].update(code_bin_path=str((args.output/'code.bin').resolve()),code_bin_sha256=digest,code_bin_size=len(image))
    manifest['randomizer_proof']={'schema':1,'seed_sha256':hashlib.sha256(args.seed.read_bytes()).hexdigest(),'runtime_sha256':decision['runtime_sha256'],'extended_save_address':symbols['gExtSaveData'][0],'extended_save_size':symbols['gExtSaveData'][1],'activation_allowed':False}
    if independent:
        names = set(seed['runtime_fields_hex']) | {'ptrCustomMessageEntries','numCustomMessageEntries'}
        manifest['randomizer_proof']['seed_layout'] = {
            'schema':1, 'symbols':{name:list(symbols[name]) for name in sorted(names)}}
        manifest['randomizer_proof']['seed_layout']['symbols']['rCustomMessages'] = [messageBase,LIMIT-8-messageBase]
        manifest['randomizer_proof']['seed_file'] = 'seed.json'
        from stage_runtime import verified_game_image
        manifest['randomizer_proof']['activation_allowed'] = verified_game_image(manifest)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.combined-',dir=args.output.parent) as temp:
        out=Path(temp)/'image';out.mkdir();(out/'code.bin').write_bytes(image)
        if independent:(out/'seed.json').write_bytes(args.seed.read_bytes())
        (out/'process-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        (out/'observed-sites.json').write_text(json.dumps(observed,indent=2)+'\n')
        with (out/'inventory.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(sorted(rows,key=lambda r:int(r['entry'],0)))
        (out/'composition.json').write_text(json.dumps({'private_local_artifact':True,'redistributable':False,'code_sha256':digest,'patch_count':len(intervals),'runtime_entries':len(additions),'adjusted_returns':len(resumes),'undefined_instruction_traps':[hex(pc) for pc in traps],'seed_abi':abi,'playable_verified':False},indent=2)+'\n')
        out.rename(args.output)
    print(f'Combined private image: {len(additions)} runtime entries, {len(intervals)} patches; not activated')

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('image','hud','runtime','receipt','seed','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument("--seed-independent", action="store_true")
    compose(p.parse_args(argv))


if __name__ == "__main__":
    main()
