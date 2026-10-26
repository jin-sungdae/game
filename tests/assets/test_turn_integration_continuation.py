import hashlib
import json
import unittest
from test_assets import ROOT
from test_creature_new_pose_quality import measure_parts

class TurnIntegrationTests(unittest.TestCase):
    def test_desert_beast_hit_preserves_anatomy_and_approval_boundary(self):
        folder = ROOT / 'design/production-batches/action-followup/M057/hit-pilot'
        actual = measure_parts(folder)
        self.assertEqual(actual, json.loads((folder / 'frame-validation.json').read_text()))
        self.assertEqual(actual['automated'], 'PASS')
        self.assertEqual(actual['uniquePixelHashes'], 8)
        self.assertTrue(all(f['protectedPixelChanges'] == 0 for f in actual['frames']))
        self.assertTrue(any(f['silhouetteSupportChangedPixels'] for f in actual['frames']))
        self.assertFalse(actual['productionEligible'])

    def test_raw_turn_failure_stops_before_normalization(self):
        folder = ROOT / 'design/production-batches/action-followup/M052/turn-pilot'
        report = json.loads((folder / 'keypose-validation.json').read_text())
        self.assertEqual(report['sourceAlpha']['detachedPixels'], 986)
        self.assertEqual(report['sourceAlpha']['threshold'], 0)
        self.assertEqual(report['sourceSha256'], hashlib.sha256((folder / 'keypose-tool-reference.png').read_bytes()).hexdigest())
        self.assertFalse(report['normalizationPerformed'])
        self.assertFalse(report['riggingPerformed'])
        self.assertFalse((folder / 'rigged').exists())

    def test_identity_reviews_do_not_activate_production(self):
        q = json.loads((ROOT / 'design/creature-production-queue.json').read_text())
        for code in ['M053', 'M054', 'M055']:
            creature = next(c for c in q['creatures'] if c['creatureId'] == code)
            hit = next(a for a in creature['actions'] if a['action'] == 'HIT')
            self.assertIsNone(creature['productionSpeciesId'])
            self.assertEqual(hit['frameCount'], 0)
            self.assertEqual(hit['runtimeStatus'], 'BLOCKED')
            self.assertIn('Identity review', hit['blockReason'])
        self.assertEqual(q['repairIterations'], 3)
