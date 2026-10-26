import json
import unittest
import test_assets

class MonsterBatch05Tests(unittest.TestCase):
    def test_remaining_candidates_do_not_imply_production_approval(self):
        root=test_assets.ROOT/'design/production-batches/monsters/batch05'
        for code in ['M041', 'M042', 'M044', 'M045', 'M046', 'M047', 'M049', 'M050']:
            p=root/code;manifest=json.loads((p/'candidate-clip.json').read_text())
            self.assertFalse(manifest['productionEligible']);self.assertFalse(manifest['runtimeEnabled'])
            self.assertIsNone(manifest['productionSpeciesId'])
            bounds=[];self.assertEqual(test_assets.validator.png_errors(p/'base-v2.png',True,bounds,[]),[])
            frames=sorted((p/'rigged/idle').glob('*.png'));self.assertEqual(len(frames),6)
            hashes=[]
            for frame in frames:
                actual=[];self.assertEqual(test_assets.validator.png_errors(frame,True,actual,hashes),[])
                self.assertEqual(actual,bounds)
            self.assertEqual(len(set(hashes)),6)
            evidence=json.loads((p/'frame-validation.json').read_text())
            self.assertEqual(evidence['naturalMotionReview'],'NOT_VERIFIED')
            self.assertFalse(evidence['productionEligible'])

        for code in ['M043', 'M048']:
            self.assertFalse((root/code/'rigged').exists())
