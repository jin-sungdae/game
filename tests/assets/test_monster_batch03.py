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

    def test_m024_approved_cleanup_preserves_evidence_and_is_not_registered(self):
        import hashlib
        p=test_assets.ROOT/'design/production-batches/monsters/batch03/M024'
        report=json.loads((p/'cleanup-approved-validation.json').read_text())
        for name, key in [('base-v3.png','sourceSha256'),('base-v4.png','resultSha256')]:
            self.assertEqual(hashlib.sha256((p/name).read_bytes()).hexdigest(),report[key])
        self.assertEqual(len(report['removedPixels']),52)
        self.assertTrue(all(0 < pixel[2] <= 2 for pixel in report['removedPixels']))
        self.assertEqual(report['afterDetachedPixels'],0)
        self.assertEqual(report['connectedBodyPixelChanges'],0)
        self.assertEqual(report['rgbPixelChanges'],0)
        self.assertEqual(report['coordinateTranslation'],[0,0])
        self.assertEqual(report['approvedExtraCorrectionsUsed'],1)
        self.assertFalse(report['productionEligible'])
        self.assertFalse(report['runtimeEnabled'])
        self.assertEqual(test_assets.validator.png_errors(p/'base-v4.png',True,[],[]),[])
        self.assertEqual(json.loads((p/'base-measurement-v2.json').read_text())['detachedPixels'],52)
        self.assertFalse((p/'candidate-clip.json').exists())
