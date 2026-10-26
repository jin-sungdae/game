import hashlib
import json
import unittest
from test_assets import ROOT
from test_creature_new_pose_quality import measure_parts

BATCH = ROOT / 'design/production-batches/action-followup'

class SeahorseShellTests(unittest.TestCase):
    def test_two_anatomy_rigs_preserve_anchor_and_protected_regions(self):
        signatures = set()
        for code in ['M062', 'M066']:
            folder = BATCH / code / 'hit-pilot'
            result = measure_parts(folder)
            self.assertEqual(result, json.loads((folder / 'frame-validation.json').read_text()))
            self.assertEqual(result['automated'], 'PASS')
            self.assertEqual(result['uniquePixelHashes'], 8)
            self.assertTrue(all(f['protectedPixelChanges'] == 0 for f in result['frames']))
            self.assertTrue(any(f['silhouetteSupportChangedPixels'] for f in result['frames']))
            self.assertFalse(result['productionEligible'])
            spec = json.loads((folder / 'candidate-clip.json').read_text())
            signatures.add(json.dumps(spec['parts'], sort_keys=True))
            self.assertFalse(spec['runtimeEnabled'])
        self.assertEqual(len(signatures), 2)

    def test_crab_raw_failure_has_no_normalized_or_rigged_assets(self):
        folder = BATCH / 'M064/attack-pilot'
        report = json.loads((folder / 'keypose-validation.json').read_text())
        self.assertEqual(report['sourceAlpha']['detachedPixels'], 967)
        self.assertEqual(report['sourceAlpha']['threshold'], 0)
        self.assertEqual(report['sourceSha256'], hashlib.sha256((folder / 'keypose-tool-reference.png').read_bytes()).hexdigest())
        self.assertFalse(report['normalizationPerformed'])
        self.assertFalse(report['riggingPerformed'])
        self.assertFalse((folder / 'keypose.png').exists())
        self.assertFalse((folder / 'rigged').exists())

    def test_identity_reviews_preserve_movement_contract_and_failure_limit(self):
        q = json.loads((ROOT / 'design/creature-production-queue.json').read_text())
        catalog = json.loads((ROOT / 'design/visual-reference-v1/catalog.json').read_text())
        for code in ['M063', 'M065']:
            creature = next(c for c in q['creatures'] if c['creatureId'] == code)
            action = next(a for a in creature['actions'] if a['action'] == 'MOVE')
            self.assertIsNone(creature['productionSpeciesId'])
            self.assertEqual(action['frameCount'], 0)
            self.assertEqual(action['runtimeStatus'], 'BLOCKED')
            self.assertIn('Identity review', action['blockReason'])
            concept = next(c for c in catalog['monsterConcepts'] if c['conceptId'] == code)
            self.assertEqual(concept['movementProfile'], {'status': 'PROPOSED', 'value': 'FREE_2D'})
        self.assertEqual(q['repairIterations'], 3)
