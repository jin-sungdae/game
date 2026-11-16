import json
import unittest
from test_assets import ROOT
from test_creature_new_pose_quality import measure_parts

BATCH=ROOT/'design/production-batches/luma-asset-08'
class Asset08Tests(unittest.TestCase):
    def test_candidates_remeasure_and_failures_are_not_repaired(self):
        for path in sorted(BATCH.glob('M*/*/candidate-clip.json')):
            with self.subTest(candidate=str(path.parent)):
                spec=json.loads(path.read_text())
                actual=measure_parts(path.parent)
                self.assertEqual(actual,json.loads((path.parent/'frame-validation.json').read_text()))
                self.assertFalse(spec['runtimeEnabled'])
                self.assertFalse(spec['productionEligible'])
                self.assertEqual(spec['repairIterations'],3)
                if spec['conceptId']=='M021':
                    self.assertEqual(actual['automated'],'VALIDATION_FAILED')
                    self.assertEqual(len(actual['frames']),0)
                else:
                    self.assertEqual(actual['automated'],'PASS')
                    self.assertEqual(actual['uniquePixelHashes'],8)
    def test_only_missing_actions_and_no_claimed_identity(self):
        ledger=json.loads((ROOT/'design/creature-production-queue.json').read_text())
        self.assertEqual(ledger['repairIterations'],3)
        for path in BATCH.glob('M*/*/candidate-clip.json'):
            spec=json.loads(path.read_text())
            row=next(r for r in ledger['creatures'] if r['creatureId']==spec['conceptId'])
            action=next(a for a in row['actions'] if a['action']==spec['clip']['name'])
            self.assertEqual(action['animationStatus'],'ASSET_REQUIRED')
            self.assertEqual(spec['sourceBase'],row['basePath'])
            self.assertIsNone(row['productionSpeciesId'])
            self.assertEqual(spec['anchor'],{'x':.5,'y':1})
