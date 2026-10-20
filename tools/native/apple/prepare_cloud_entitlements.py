#!/usr/bin/env python3
"""Derive local signing entitlements only from a matching authorized profile."""
import argparse,plistlib,subprocess
from pathlib import Path

def prepare(profile,container,output,environment="Development"):
    document=plistlib.loads(subprocess.check_output(['security','cms','-D','-i',str(profile)]))
    allowed=document.get('Entitlements',{})
    identifier=allowed.get('application-identifier',allowed.get('com.apple.application-identifier',''))
    if not identifier.endswith('.io.github.otpr26.ocarinaretuned') or '*' in identifier:
        raise ValueError('An explicit Ocarina ReTuned provisioning profile is required.')
    if container not in allowed.get('com.apple.developer.icloud-container-identifiers',[]):
        raise ValueError('Profile does not authorize the requested iCloud container.')
    services=allowed.get('com.apple.developer.icloud-services',[])
    if services != '*' and 'CloudKit' not in services:
        raise ValueError('CloudKit is not enabled in this profile.')
    wanted=('application-identifier','com.apple.application-identifier','com.apple.developer.team-identifier',
            'get-task-allow','com.apple.developer.icloud-container-environment')
    result={key:allowed[key] for key in wanted if key in allowed}
    result['com.apple.developer.icloud-container-identifiers']=[container]
    result['com.apple.developer.icloud-services']=['CloudKit']
    if 'com.apple.developer.icloud-container-environment' not in result:
        raise ValueError('Profile must specify its CloudKit environment.')
    environments=result['com.apple.developer.icloud-container-environment']
    if environment != environments and environment not in (environments if isinstance(environments,list) else []):
        raise ValueError('Requested CloudKit environment is not authorized by the profile.')
    result['com.apple.developer.icloud-container-environment']=environment
    output.write_bytes(plistlib.dumps(result))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',type=Path,required=True)
    parser.add_argument('--container',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--environment',choices=['Development','Production'],default='Development')
    options=parser.parse_args();prepare(options.profile,options.container,options.output,options.environment)
