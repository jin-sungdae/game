import json
import unittest
import test_assets

class MonsterBatch03Tests(unittest.TestCase):
    def test_remaining_candidates_do_not_imply_production_approval(self):
        root=test_assets.ROOT/'design/production-batches/monsters/batch03'
        for code in ['M021', 'M022', 'M025', 'M026', 'M027', 'M028', 'M029']:
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

        for code in ['M023','M024','M030']:
            self.assertFalse((root/code/'rigged').exists())
