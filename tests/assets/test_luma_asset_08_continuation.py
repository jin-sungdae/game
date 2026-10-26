import importlib.util,json,unittest
from test_assets import ROOT
from test_creature_followup import detached_pixels
from test_moa_blink_v2 import rgba
BATCH=ROOT/'design/production-batches/luma-asset-08/continuation'
spec=importlib.util.spec_from_file_location('asset08_measure',BATCH/'validate.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class Asset08ContinuationTests(unittest.TestCase):
    def test_independent_clips_and_base_return(self):
        paths=list(BATCH.glob('M*/*/candidate-clip.json'))
        self.assertEqual(len(paths),9)
        for p in paths:
            with self.subTest(candidate=str(p.parent)):
                report,continuity=module.measured(p.parent)
                self.assertEqual(report,json.loads((p.parent/'frame-validation.json').read_text()))
                self.assertEqual(continuity,json.loads((p.parent/'base-return.json').read_text()))
                self.assertEqual(report['automated'],'PASS')
                self.assertTrue(continuity['lastToBaseLessThanPeak'])
                self.assertLess(continuity['lastToBaseNormalizedMean'],.001)
                contract=json.loads(p.read_text())
                self.assertFalse(contract['productionEligible']);self.assertFalse(contract['runtimeEnabled'])
    def test_m021_failure_is_not_base_alpha_corruption(self):
        ledger=json.loads((ROOT/'design/creature-production-queue.json').read_text())
        row=next(r for r in ledger['creatures'] if r['creatureId']=='M021')
        self.assertEqual(detached_pixels(rgba(ROOT/row['basePath'])),0)
        for action in ['hit','interact','cursor_react']:
            folder=BATCH.parent/'M021'/action
            self.assertEqual(json.loads((folder/'frame-validation.json').read_text())['automated'],'VALIDATION_FAILED')
            self.assertFalse(any(folder.glob('rigged/**/*.png')))
        for record in json.loads((BATCH/'m021-sampling-analysis.json').read_text()):
            self.assertEqual(record['firstFrameSampling']['alphaChanges'],0)
            self.assertEqual(record['firstFrameSampling']['fixedChanges'],0)
            self.assertGreater(record['firstFrameSampling']['changed'],0)
