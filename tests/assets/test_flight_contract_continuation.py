import hashlib
import json
import unittest
from test_assets import ROOT
from test_creature_new_pose_quality import measure_parts

BATCH = ROOT / 'design/production-batches/action-followup'

class FlightContractTests(unittest.TestCase):
    def test_wolf_local_hit_retains_contact_and_identity_boundaries(self):
        folder = BATCH / 'M050/hit-pilot'
        result = measure_parts(folder)
        self.assertEqual(result, json.loads((folder / 'frame-validation.json').read_text()))
        self.assertEqual(result['automated'], 'PASS')
        self.assertEqual(result['uniquePixelHashes'], 8)
        self.assertTrue(any(f['silhouetteSupportChangedPixels'] for f in result['frames']))
        self.assertTrue(all(f['protectedPixelChanges'] == 0 for f in result['frames']))
        self.assertEqual(result['appearance'], 'HUMAN_REVIEW_REQUIRED')
        self.assertFalse(result['productionEligible'])

    def test_new_raw_failures_stop_before_normalization(self):
        for code, count in [('M047/fly-pilot', 695), ('M051/attack-pilot', 1554)]:
            folder = BATCH / code
            report = json.loads((folder / 'keypose-validation.json').read_text())
            self.assertEqual(report['sourceAlpha']['detachedPixels'], count)
            self.assertEqual(report['sourceAlpha']['threshold'], 0)
            self.assertEqual(report['sourceSha256'], hashlib.sha256((folder / 'keypose-tool-reference.png').read_bytes()).hexdigest())
            self.assertFalse(report['normalizationPerformed'])
            self.assertFalse(report['riggingPerformed'])
            self.assertFalse((folder / 'keypose.png').exists())
            self.assertFalse((folder / 'rigged').exists())

    def test_anatomy_review_never_changes_species_or_enables_runtime(self):
        queue = json.loads((ROOT / 'design/creature-production-queue.json').read_text())
        catalog = json.loads((ROOT / 'design/visual-reference-v1/catalog.json').read_text())
        owl = next(r for r in catalog['monsterConcepts'] if r['conceptId'] == 'M047')
        self.assertEqual(owl['movementProfile'], {'status': 'PROPOSED', 'value': 'FLYING'})
        self.assertEqual(owl['observedForm'], 'snow owl')
        self.assertFalse(owl['runtimeEnabled'])
        for identity in ['M048', 'M049']:
            row = next(r for r in queue['creatures'] if r['creatureId'] == identity)
            action = next(a for a in row['actions'] if a['action'] == 'HIT')
            self.assertIsNone(row['productionSpeciesId'])
            self.assertEqual(action['frameCount'], 0)
            self.assertEqual(action['runtimeStatus'], 'BLOCKED')
            self.assertIn('Identity', action['blockReason'])
        self.assertEqual(queue['repairIterations'], 3)
        self.assertEqual(queue['flightContractContinuation']['approvedUnconnectedAssets'], [])
