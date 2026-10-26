import hashlib
import json
import unittest
from test_assets import ROOT
from test_creature_new_pose_quality import measure_parts

BATCH = ROOT / 'design/production-batches/action-followup'

class ShadowStagContinuationTests(unittest.TestCase):
    def test_drake_hit_preserves_contacts_and_moves_local_silhouette(self):
        folder = BATCH / 'M090/hit-pilot'
        r = measure_parts(folder)
        self.assertEqual(r, json.loads((folder / 'frame-validation.json').read_text()))
        self.assertEqual(r['automated'], 'PASS')
        self.assertEqual(r['uniquePixelHashes'], 8)
        self.assertTrue(all(f['protectedPixelChanges'] == 0 for f in r['frames']))
        self.assertTrue(any(f['silhouetteSupportChangedPixels'] for f in r['frames']))
        self.assertFalse(r['productionEligible'])

    def test_stag_hit_preserves_contacts_and_moves_local_silhouette(self):
        folder = BATCH / 'M092/hit-pilot'
        r = measure_parts(folder)
        self.assertEqual(r, json.loads((folder / 'frame-validation.json').read_text()))
        self.assertEqual(r['automated'], 'PASS')
        self.assertEqual(r['uniquePixelHashes'], 8)
        self.assertTrue(all(f['protectedPixelChanges'] == 0 for f in r['frames']))
        self.assertTrue(any(f['silhouetteSupportChangedPixels'] for f in r['frames']))
        self.assertFalse(r['productionEligible'])


    def test_deer_cursor_response_has_fixed_contacts_and_distinct_frames(self):
        folder = BATCH / 'M096/cursor_react-pilot'
        r = measure_parts(folder)
        self.assertEqual(r, json.loads((folder / 'frame-validation.json').read_text()))
        self.assertEqual(r['automated'], 'PASS')
        self.assertEqual(r['uniquePixelHashes'], 8)
        self.assertTrue(all(f['protectedPixelChanges'] == 0 for f in r['frames']))
        self.assertTrue(any(f['silhouetteSupportChangedPixels'] for f in r['frames']))
        self.assertFalse(r['productionEligible'])
