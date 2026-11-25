import copy
import json
from pathlib import Path
import unittest
from plan_hooks import resolve


class HookOwnership(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(Path(__file__).with_name('hook_policy.json').read_text())
        self.overlaps = [dict(randomizer=name, hud=name, bytes=4, start='0x100000')
                         for name in self.policy['keep_reframed'] + self.policy['compose_before_activation']]

    def test_all_conflicts_have_one_owner(self):
        decisions = resolve(self.overlaps, self.policy)
        self.assertEqual(sum(d['action'] == 'use_composed_hook' for d in decisions), 2)
        self.assertEqual(sum(d['action'] == 'keep_reframed' for d in decisions), 6)

    def test_unknown_conflict_rejected(self):
        self.overlaps.append(dict(randomizer='.patch_new', hud='.patch_HUD', bytes=4))
        with self.assertRaises(ValueError): resolve(self.overlaps, self.policy)

    def test_missing_conflict_rejected(self):
        with self.assertRaises(ValueError): resolve(self.overlaps[:-1], self.policy)

    def test_partial_composition_rejected(self):
        for field, value in [('bytes', 2), ('hud', '.patch_other')]:
            changed = copy.deepcopy(self.overlaps)
            changed[-1][field] = value
            with self.assertRaises(ValueError): resolve(changed, self.policy)

    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError): resolve(self.overlaps + self.overlaps[:1], self.policy)


if __name__ == '__main__': unittest.main()
