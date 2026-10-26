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
