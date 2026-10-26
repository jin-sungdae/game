import hashlib
import json
import unittest
from test_assets import ROOT
from test_creature_new_pose_quality import measure_parts

BATCH = ROOT / 'design/production-batches/action-followup'

class MechanicalAnatomyContinuationTests(unittest.TestCase):
    def test_drake_hit_preserves_contacts_and_moves_local_silhouette(self):
        folder = BATCH / 'M082/hit-pilot'
        r = measure_parts(folder)
        self.assertEqual(r, json.loads((folder / 'frame-validation.json').read_text()))
        self.assertEqual(r['automated'], 'PASS')
        self.assertEqual(r['uniquePixelHashes'], 8)
        self.assertTrue(all(f['protectedPixelChanges'] == 0 for f in r['frames']))
        self.assertTrue(any(f['silhouetteSupportChangedPixels'] for f in r['frames']))
        self.assertFalse(r['productionEligible'])

    def test_unresolved_mechanical_identity_and_layers_stay_blocked(self):
        q = json.loads((ROOT / 'design/creature-production-queue.json').read_text())
        for creature, action in [('M077', 'HIT'), ('M078', 'HIT'), ('M079', 'TURN'), ('M080', 'TURN')]:
            c = next(c for c in q['creatures'] if c['creatureId'] == creature)
            a = next(a for a in c['actions'] if a['action'] == action)
            self.assertEqual(a['frameCount'], 0)
            self.assertEqual(a['runtimeStatus'], 'BLOCKED')
            self.assertIsNone(c['productionSpeciesId'])
        self.assertEqual(q['repairIterations'], 3)
        self.assertEqual(q['approvalBottleneckContinuation']['approvalAudit']['summary']['approvedRuntimePendingClips'], 0)
