import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BATCH = ROOT / 'design/production-batches/luma-asset-12'

class Asset12BoundaryTests(unittest.TestCase):
    def test_all_requested_actions_have_explicit_disposition(self):
        request = json.loads((BATCH / 'integration-request.json').read_text())
        self.assertEqual((request['repairIterations'], request['repairLimit']), (3, 3))
        self.assertEqual(len(request['creatures']), 5)
        for creature in request['creatures']:
            self.assertEqual(len({a['action'] for a in creature['actions']}), 21)
            self.assertFalse(creature['runtimeConnected'])
            self.assertIsNone(creature['productionSpeciesId'])
            for action in creature['actions']:
                if action['status'] == 'BLOCKED': self.assertTrue(action['reason'])

    def test_candidates_cannot_be_promoted_by_structural_pass(self):
        for path in BATCH.glob('M*/**/candidate-clip.json'):
            clip = json.loads(path.read_text())
            self.assertFalse(clip['productionEligible'])
            self.assertFalse(clip['runtimeEnabled'])
            self.assertEqual(clip['repairIterations'], 3)
            self.assertEqual(clip['clip']['frames'], len(clip['frames']))
            for frame in clip['frames']: self.assertTrue((path.parent / frame['file']).is_file())
        failed = json.loads((BATCH / 'M043/idle/validation.json').read_text())
        self.assertEqual(failed['status'], 'BLOCKED')
        self.assertFalse(failed['productionEligible'])

    def test_original_twenty_clips_and_failure_sources_are_unchanged(self):
        hashes = json.loads((BATCH / 'preserved-hashes.json').read_text())
        for name, expected in hashes.items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected, name)

    def test_new_actions_return_to_base_and_never_repair_failed_actions(self):
        import test_assets
        count = 0
        for code in ['M041', 'M042', 'M044', 'M045']:
            actions = ['VICTORY', 'RECOVERY'] if code == 'M044' else ['LOOK', 'VICTORY', 'RECOVERY', 'SLEEP'] if code == 'M041' else ['LOOK', 'VICTORY', 'RECOVERY']
            for action in actions:
                path = BATCH / code / action.lower() / 'candidate-clip.json'
                clip = json.loads(path.read_text())
                self.assertEqual(clip['entryContract'], 'BASE_ONLY')
                self.assertEqual(clip['exitContract'], 'EXACT_BASE')
                hashes = []
                for file in [ROOT / clip['sourceBase'], path.parent / clip['frames'][0]['file'], path.parent / clip['frames'][-1]['file']]:
                    self.assertEqual(test_assets.validator.png_errors(file, True, [], hashes), [])
                self.assertEqual(len(set(hashes)), 1, (code, action))
                self.assertFalse(clip['productionEligible'])
                self.assertFalse(clip['runtimeEnabled'])
                count += 1
        self.assertEqual(count, 12)
        self.assertFalse((BATCH / 'M043' / 'recovery').exists())
