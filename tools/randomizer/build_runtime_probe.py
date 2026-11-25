#!/usr/bin/env python3
"""Build a relocated EUR-addressed randomizer ELF for hook auditing only."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import json
import hashlib
import importlib.util

def build(source, output, compiler, hud=None):
    source, output = source.resolve(), output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    subprocess.run(['python3', str(Path(__file__).with_name('verify_source.py')), str(source)], check=True)
    upstream = source / 'externals/oot3d-randomizer'
    includes = [source/'tools/oot3d/randomizer/guest_include', upstream/'code/include', upstream/'shared']
    includes += sorted({p.parent for p in (upstream/'code/src').rglob('*.h')})
    flags = ['-std=gnu11','-ffreestanding','-O2','-fno-builtin','-fno-strict-aliasing',
             '-march=armv6k','-mtune=mpcore','-mfloat-abi=softfp','-mfpu=vfpv2','-mtp=soft',
             '-ffunction-sections','-fdata-sections','-fno-jump-tables','-DARM11','-D_3DS']
    flags += ['-I'+str(p) for p in includes]
    sources = sorted((upstream/'shared').glob('*.c')) + sorted((upstream/'code/src').rglob('*.c')) + sorted((upstream/'code/src').rglob('*.s'))
    hud_symbols = {}
    if hud:
        helper = Path(__file__).resolve().parents[1] / 'reframed/prepare_native_image.py'
        spec = importlib.util.spec_from_file_location('native_image', helper)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        symbols = {name: (address, size, kind) for address,size,kind,name,_ in module.read_elf_symbols(hud)}
        for phase in ('before', 'after'):
            address, size, kind = symbols[phase + '_GlobalContext_Update']
            if kind != 'FUNC' or not size or address % 4:
                raise ValueError('Invalid ReFramed update function')
            hud_symbols['Retuned_Hud' + phase.title()] = address
        original = upstream/'code/src/asm/hooks.s'
        text = original.read_text()
        for phase in ('before', 'after'):
            marker = 'HOOK ' + phase + '_GlobalContext_Update\n'
            if text.count(marker) != 1: raise ValueError('Unknown update-hook source')
            # Both existing hooks use the softfp ABI. Restore the original
            # integer arguments before entering the randomizer's own wrapper.
            text = text.replace(marker, marker + '    push {r0-r12, lr}\n    bl Retuned_Hud' + phase.title() + '\n    pop {r0-r12, lr}\n')
        composed = output/'composed_hooks.s'; composed.write_text(text)
        sources = [composed if p == original else p for p in sources]
    # File creation bypasses the normal SaveGame hook. Capture the initialized
    # extended state before the original game writes that new native file.
    original_save = upstream/'code/src/savefile.c'
    save_text = original_save.read_text()
    marker = '    SaveFile_SetStartingInventory();'
    if save_text.count(marker) != 1:
        raise ValueError('Unknown new-file initialization source')
    save_text = save_text.replace(marker, marker + '\n    SaveFile_SaveExtSaveData(fileBaseIndex + gSaveContext.fileNum);')
    save_source = output/'savefile.c'; save_source.write_text(save_text)
    sources = [save_source if path == original_save else path for path in sources]
    def compile_one(path):
        relative = path.relative_to(upstream) if path.is_relative_to(upstream) else Path(path.name)
        obj=output/(str(relative).replace('/','_')+'.o')
        command=[str(compiler),*flags,*(['-include','stddef.h'] if path.suffix=='.c' else []),'-c',str(path),'-o',str(obj)]
        run=subprocess.run(command, text=True,capture_output=True)
        return obj,run
    objects=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for obj,run in pool.map(compile_one,sources):
            if run.returncode:
                raise RuntimeError(run.stderr[-6000:])
            objects.append(str(obj))
    script=(upstream/'code/oot.ld').read_text()
    old='. = 0x005C7000 + _LD_OFF;'
    if script.count(old)!=1:raise ValueError('Unknown runtime linker layout')
    script=script.replace(old,'. = 0x00680000;')
    script += '\n' + '\n'.join(f'{name} = 0x{address:x};' for name,address in hud_symbols.items()) + '\n'
    linker=output/'runtime.ld';linker.write_text(script)
    elf=output/'runtime.elf'
    subprocess.run([str(compiler),'-nostdlib','-march=armv6k','-mfloat-abi=softfp','-mfpu=vfpv2',
                    '-Wl,--defsym,_LD_USA=0','-Wl,--defsym,_LD_EUR=1','-Wl,-Map='+str(output/'runtime.map'),
                    '-T',str(linker),*objects,'-lgcc','-o',str(elf)],check=True)
    (output/'build-receipt.json').write_text(json.dumps({'audit_only':True,'region':'canonical-EUR',
        'base':0x680000,'source_units':len(sources),'elf_sha256':hashlib.sha256(elf.read_bytes()).hexdigest(),
        'hud_sha256':hashlib.sha256(hud.read_bytes()).hexdigest() if hud else None,
        'composed_calls':hud_symbols,'new_file_extended_snapshot':True},indent=2)+'\n')
    print('Audit ELF built; not installed or activated')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--compiler',type=Path,required=True);p.add_argument('--hud',type=Path)
    a=p.parse_args();build(a.source,a.output,a.compiler,a.hud)
