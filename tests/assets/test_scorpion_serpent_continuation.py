import hashlib
import json
import unittest
from test_assets import ROOT
from test_creature_new_pose_quality import measure_parts

BATCH = ROOT / 'design/production-batches/action-followup'

class ScorpionSerpentTests(unittest.TestCase):
    def test_independent_anatomy_responses_keep_anchor_and_approval_boundary(self):
        for code in ['M058/hit-pilot', 'M061/interact-pilot']:
            folder = BATCH / code
            result = measure_parts(folder)
            self.assertEqual(result, json.loads((folder / 'frame-validation.json').read_text()))
            self.assertEqual(result['automated'], 'PASS')
            self.assertEqual(result['uniquePixelHashes'], 8)
            self.assertTrue(all(f['protectedPixelChanges'] == 0 for f in result['frames']))
            self.assertTrue(any(f['silhouetteSupportChangedPixels'] for f in result['frames']))
            self.assertFalse(result['productionEligible'])

    def test_internal_pixel_only_candidate_is_not_a_completed_action(self):
        folder = BATCH / 'M060/cursor-react-pilot'
        result = measure_parts(folder)
        self.assertEqual(result, json.loads((folder / 'frame-validation.json').read_text()))
        self.assertEqual(result['uniquePixelHashes'], 8)
        self.assertEqual(result['automated'], 'VALIDATION_FAILED')
        self.assertTrue(all(f['silhouetteSupportChangedPixels'] == 0 for f in result['frames']))
        q = json.loads((ROOT / 'design/creature-production-queue.json').read_text())
        action = next(a for c in q['creatures'] if c['creatureId'] == 'M060' for a in c['actions'] if a['action'] == 'CURSOR_REACT')
        self.assertEqual(action['animationStatus'], 'VALIDATION_FAILED')
        self.assertEqual(action['runtimeStatus'], 'BLOCKED')
        self.assertEqual(q['repairIterations'], 3)

    def test_scorpion_raw_alpha_failure_stops_before_rigging(self):
        folder = BATCH / 'M056/attack-pilot'
        report = json.loads((folder / 'keypose-validation.json').read_text())
        self.assertEqual(report['sourceAlpha']['threshold'], 0)
        self.assertEqual(report['sourceAlpha']['detachedPixels'], 4290)
        self.assertEqual(report['sourceSha256'], hashlib.sha256((folder / 'keypose-tool-reference.png').read_bytes()).hexdigest())
        self.assertFalse(report['normalizationPerformed'])
        self.assertFalse(report['riggingPerformed'])
        self.assertFalse((folder / 'rigged').exists())
