#!/usr/bin/env python3
"""Resolve known patch ownership; never modify a game image."""
import argparse
import hashlib
import json
from pathlib import Path
from audit_runtime import audit


def resolve(overlaps, policy):
    keep = set(policy['keep_reframed'])
    compose = set(policy['compose_before_activation'])
    seen = set()
    decisions = []
    for overlap in overlaps:
        name = overlap['randomizer']
        if name in seen:
            raise ValueError(f'Multiple overlaps for {name}')
        seen.add(name)
        if name in keep:
            action = 'keep_reframed'
        elif name in compose and overlap['hud'] == name and overlap['bytes'] == 4:
            action = 'use_composed_hook'
        else:
            raise ValueError(f'Unreviewed overlap: {name}')
        decisions.append(dict(overlap, action=action))
    if seen != keep | compose:
        raise ValueError('Patch layout changed; ownership must be reviewed again')
    return decisions


def plan(hud, runtime, receipt, policy):
    result = audit(hud, runtime)
    if receipt['elf_sha256'] != result['runtime_sha256'] or receipt['hud_sha256'] != result['hud_sha256']:
        raise ValueError('Composition receipt does not match the supplied binaries')
    if set(receipt['composed_calls']) != {'Retuned_HudBefore', 'Retuned_HudAfter'}:
        raise ValueError('Both update hooks must be composed')
    result['decisions'] = resolve(result['overlaps'], policy)
    result['policy_sha256'] = hashlib.sha256(json.dumps(policy, sort_keys=True).encode()).hexdigest()
    result['remaining_gates'] = policy['additional_runtime_gates']
    # Patch ownership is only one gate. Host services and save handling still
    # need implementation before these sections can be installed.
    result['ready_to_merge'] = False
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('hud', 'runtime', 'receipt', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    policy = json.loads(Path(__file__).with_name('hook_policy.json').read_text())
    result = plan(args.hud, args.runtime, json.loads(args.receipt.read_text()), policy)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(f"Resolved {len(result['decisions'])} patch conflicts; runtime activation remains disabled")
