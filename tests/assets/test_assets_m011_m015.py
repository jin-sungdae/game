import importlib.util,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BATCH=ROOT/'design/production-batches/luma-asset-06'
spec=importlib.util.spec_from_file_location('asset06',BATCH/'validate.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class Asset06Tests(unittest.TestCase):
    def test_recomputed_measurements_preserve_pass_and_failure(self):
        passed=failed=frames=0
        for folder in sorted(BATCH.glob('M*/*')):
            with self.subTest(candidate=str(folder)):
                measured=module.audit(folder)
                self.assertEqual(measured,json.loads((folder/'frame-validation.json').read_text()))
                passed+=measured['automated']=='PASS';failed+=measured['automated']!='PASS';frames+=len(measured['frames'])
                self.assertFalse(measured['productionEligible']);self.assertEqual(measured['repairIterations'],3)
        self.assertEqual((passed,failed,frames),(6,5,64))

    def test_no_duplicate_existing_actions_or_approval(self):
        queue=json.loads((ROOT/'design/creature-production-queue.json').read_text())
        rows={r['creatureId']:r for r in queue['creatures']}
        for path in BATCH.glob('M*/*/candidate-clip.json'):
            candidate=json.loads(path.read_text());row=rows[candidate['conceptId']]
            old=next(a for a in row['actions'] if a['action']==candidate['clip']['name'])
            self.assertEqual(old['animationStatus'],'ASSET_REQUIRED')
            self.assertFalse(candidate['productionEligible']);self.assertFalse(candidate['runtimeEnabled'])
            self.assertEqual(candidate['repairLimit'],candidate['repairIterations'])
            self.assertIsNone(candidate['species'])
        for ident,action in [('M011','REST'),('M012','MOVE')]:
            self.assertEqual(next(a for a in rows[ident]['actions'] if a['action']==action)['animationStatus'],'VALIDATION_FAILED')

    def test_catalog_cannot_promote_continuity_failures(self):
        catalog=json.loads((BATCH/'catalog.json').read_text())
        clips=[c for row in catalog['creatures'] for c in row['clips']]
        self.assertEqual(len(clips),8)
        self.assertEqual(sum(c['automated']=='PASS' for c in clips),6)
        self.assertTrue(all(not c['runtimeEnabled'] for c in clips))
