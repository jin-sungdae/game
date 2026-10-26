import hashlib
import json
import unittest
from test_assets import ROOT
from test_creature_new_pose_quality import measure_parts

BATCH = ROOT / 'design/production-batches/action-followup'

class OceanTurnTests(unittest.TestCase):
    def test_tentacle_clips_preserve_anatomy_and_move_local_silhouettes(self):
        signatures = set()
        for name in ['M069/hit-pilot', 'M070/interact-pilot']:
            folder = BATCH / name
            result = measure_parts(folder)
            self.assertEqual(result, json.loads((folder / 'frame-validation.json').read_text()))
            self.assertEqual(result['automated'], 'PASS')
            self.assertEqual(result['uniquePixelHashes'], 8)
            self.assertTrue(all(f['protectedPixelChanges'] == 0 for f in result['frames']))
            self.assertTrue(all(f['detachedAlphaPixels'] == 0 for f in result['frames']))
            self.assertTrue(any(f['silhouetteSupportChangedPixels'] for f in result['frames']))
            self.assertFalse(result['productionEligible'])
            spec = json.loads((folder / 'candidate-clip.json').read_text())
            signatures.add(json.dumps(spec['parts'], sort_keys=True))
            self.assertFalse(spec['runtimeEnabled'])
        self.assertEqual(len(signatures), 2)

    def test_turn_raw_alpha_failure_stops_pipeline(self):
        folder = BATCH / 'M067/turn-pilot'
        report = json.loads((folder / 'keypose-validation.json').read_text())
        self.assertEqual(report['sourceAlpha']['detachedPixels'], 1175)
        self.assertEqual(report['sourceAlpha']['threshold'], 0)
        self.assertEqual(report['sourceSha256'], hashlib.sha256((folder / 'keypose-tool-reference.png').read_bytes()).hexdigest())
        self.assertFalse(report['normalizationPerformed'])
        self.assertFalse(report['riggingPerformed'])
        self.assertFalse((folder / 'keypose.png').exists())
        self.assertFalse((folder / 'rigged').exists())

    def test_jellyfish_identity_conflict_is_not_reinterpreted(self):
        q = json.loads((ROOT / 'design/creature-production-queue.json').read_text())
        c = next(c for c in q['creatures'] if c['creatureId'] == 'M068')
        a = next(a for a in c['actions'] if a['action'] == 'HIT')
        self.assertEqual(a['frameCount'], 0)
        self.assertEqual(a['runtimeStatus'], 'BLOCKED')
        self.assertIn('Identity review', a['blockReason'])
        self.assertIsNone(c['productionSpeciesId'])
        self.assertEqual(q['repairIterations'], 3)
        catalog = json.loads((ROOT / 'design/visual-reference-v1/catalog.json').read_text())
        proposal = next(x for x in catalog['monsterConcepts'] if x['conceptId'] == 'M068')
        self.assertEqual(proposal['observedForm'], 'long jellyfish')
        self.assertEqual(proposal['movementProfile'], {'status': 'PROPOSED', 'value': 'FLOATING'})
