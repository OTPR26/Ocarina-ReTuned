#!/usr/bin/env python3
"""Supervise clean-process mode changes for the private Mac randomizer test."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import uuid


def arguments_for(config, request):
    args = list(config['normal_arguments'])
    def set_argument(flag, value):
        index=args.index(flag)
        args[index+1]=str(value)
    if request['mode'] == 'randomizer':
        slot=request['slot']
        if type(slot) is not int or not 0 <= slot < 3:
            raise ValueError('Invalid run slot')
        expected=Path(config['app_data'])/'randomizer-runs'/f'slot-{slot+1}'/'profile'
        if Path(request['profile']).resolve()!=expected.resolve():
            raise ValueError('Run profile is outside its slot')
        # Restrict handoff paths to locally prepared randomizer artifacts.
        for key in ('manifest','module'):
            installed=config.get('installed_runtime',{})
            is_shared_module=key=='module' and installed.get('module') and Path(request[key]).resolve()==Path(installed['module']).resolve()
            if not is_shared_module and not Path(request[key]).resolve().is_relative_to(Path(config['artifacts']).resolve()):
                raise ValueError('Unrecognized prepared artifact')
        set_argument('--a32-process-manifest',request['manifest'])
        set_argument('--title-plugin',request['module'])
        set_argument('--save-data',expected)
    elif request['mode'] != 'normal':
        raise ValueError('Invalid game mode')
    return args


def main(path):
    config=json.loads(path.read_text())
    handoff=Path(config['handoff'])
    if handoff.exists():
        raise RuntimeError('A prior handoff remains; review it before restarting the supervisor')
    env=os.environ.copy()
    env.update(RETUNED_RANDOMIZER_LAUNCHER=str(path.resolve()),RETUNED_MAC_BOOTSTRAPPED='1',
        VK_ICD_FILENAMES=config['vulkan_icd'])
    request={'mode':'normal'}
    generation=0
    session=uuid.uuid4().hex[:12]
    while True:
        args=arguments_for(config,request)
        env.pop('RETUNED_RANDOMIZER_ACTIVE_SLOT',None)
        env.pop('RETUNED_RANDOMIZER_START_NORMAL',None)
        env.pop('RETUNED_RANDOMIZER_CONTINUE',None)
        env.pop('RETUNED_RANDOMIZER_NEW_GAME',None)
        if request['mode']=='randomizer':
            env['RETUNED_RANDOMIZER_ACTIVE_SLOT']=str(request['slot'])
            if (Path(request['profile'])/'native/save00.bin').is_file():
                env['RETUNED_RANDOMIZER_CONTINUE']='1'
            else:
                env['RETUNED_RANDOMIZER_NEW_GAME']='1'
        elif generation:
            env['RETUNED_RANDOMIZER_START_NORMAL']='1'
        with (path.parent/f'launcher-{session}-{generation}.log').open('w') as log:
            result=subprocess.run([config['executable'],*args],cwd=path.parent,env=env,stdout=log,stderr=subprocess.STDOUT)
        if result.returncode or not handoff.exists():
            return result.returncode
        request=json.loads(handoff.read_text())
        arguments_for(config,request)  # Validate before consuming the request.
        handoff.rename(path.parent/f'handoff-{session}-{generation}.json')
        generation+=1


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('config',type=Path)
    raise SystemExit(main(p.parse_args().config))
