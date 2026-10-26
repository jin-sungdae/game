import json
import unittest
import test_assets

class MonsterBatch09Tests(unittest.TestCase):
    def test_remaining_candidates_do_not_imply_production_approval(self):
        root=test_assets.ROOT/'design/production-batches/monsters/batch09'
        for code in ['M081', 'M082', 'M090']:
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

        for code in ['M083', 'M084', 'M085', 'M086', 'M087', 'M088', 'M089']:
            self.assertFalse((root/code/'rigged').exists())

    def test_failed_alpha_candidate_is_not_promoted(self):
        root=test_assets.ROOT/"design/production-batches/monsters/batch09/M084"
        evidence=json.loads((root/"base-measurement.json").read_text())
        self.assertGreater(evidence["detachedMaxAlpha"],4)
        self.assertFalse((root/"base-v2.png").exists())
        self.assertFalse((root/"candidate-clip.json").exists())
