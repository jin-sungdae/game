import hashlib
import json
import unittest
from test_assets import ROOT
from test_creature_new_pose_quality import measure_parts

BATCH = ROOT / 'design/production-batches/action-followup'

class TentacleContinuationTests(unittest.TestCase):
    def test_drake_hit_preserves_contacts_and_moves_local_silhouette(self):
        folder = BATCH / 'M085/interact-pilot'
        r = measure_parts(folder)
        self.assertEqual(r, json.loads((folder / 'frame-validation.json').read_text()))
        self.assertEqual(r['automated'], 'PASS')
        self.assertEqual(r['uniquePixelHashes'], 8)
        self.assertTrue(all(f['protectedPixelChanges'] == 0 for f in r['frames']))
        self.assertTrue(any(f['silhouetteSupportChangedPixels'] for f in r['frames']))
        self.assertFalse(r['productionEligible'])

    def test_ring_failure_stops_before_normalization(self):
        folder = BATCH / 'M083/attack-pilot'
        r = json.loads((folder / 'keypose-validation.json').read_text())
        self.assertEqual(r['sourceAlpha']['detachedPixels'], 4579)
        self.assertEqual(r['sourceAlpha']['threshold'], 0)
        self.assertEqual(r['sourceSha256'], hashlib.sha256((folder / 'keypose-tool-reference.png').read_bytes()).hexdigest())
        self.assertFalse(r['normalizationPerformed'])
        self.assertFalse(r['riggingPerformed'])
        self.assertFalse((folder / 'rigged').exists())

