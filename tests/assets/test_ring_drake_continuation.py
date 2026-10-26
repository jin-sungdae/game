import hashlib
import json
import unittest
from test_assets import ROOT
from test_creature_new_pose_quality import measure_parts

BATCH = ROOT / 'design/production-batches/action-followup'

class RingDrakeTests(unittest.TestCase):
    def test_drake_hit_preserves_contacts_and_moves_local_silhouette(self):
        folder = BATCH / 'M081/hit-pilot'
        r = measure_parts(folder)
        self.assertEqual(r, json.loads((folder / 'frame-validation.json').read_text()))
        self.assertEqual(r['automated'], 'PASS')
        self.assertEqual(r['uniquePixelHashes'], 8)
        self.assertTrue(all(f['protectedPixelChanges'] == 0 for f in r['frames']))
        self.assertTrue(any(f['silhouetteSupportChangedPixels'] for f in r['frames']))
        self.assertFalse(r['productionEligible'])

    def test_ring_failure_stops_before_normalization(self):
        folder = BATCH / 'M076/turn-pilot'
        r = json.loads((folder / 'keypose-validation.json').read_text())
        self.assertEqual(r['sourceAlpha']['detachedPixels'], 392)
        self.assertEqual(r['sourceAlpha']['threshold'], 0)
        self.assertEqual(r['sourceSha256'], hashlib.sha256((folder / 'keypose-tool-reference.png').read_bytes()).hexdigest())
        self.assertFalse(r['normalizationPerformed'])
        self.assertFalse(r['riggingPerformed'])
        self.assertFalse((folder / 'rigged').exists())

    def test_flattened_rigid_artwork_is_not_registered_as_joint_motion(self):
        q = json.loads((ROOT / 'design/creature-production-queue.json').read_text())
        c = next(c for c in q['creatures'] if c['creatureId'] == 'M075')
        a = next(a for a in c['actions'] if a['action'] == 'INTERACT')
        self.assertEqual(a['frameCount'], 0)
        self.assertEqual(a['runtimeStatus'], 'BLOCKED')
        self.assertIn('RIG_LAYER_REQUIRED', a['blockReason'])
        self.assertEqual(q['repairIterations'], 3)
        self.assertFalse(q['flightContractContinuation']['riggingBottleneck']['engineChanged'])
        self.assertFalse(q['flightContractContinuation']['riggingBottleneck']['failedCandidatesRecovered'])
