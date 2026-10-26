import hashlib
import json
import unittest
import test_assets

class MonsterBatch08Tests(unittest.TestCase):
    def test_mechanical_bases_remain_unregistered_without_joint_frames(self):
        root=test_assets.ROOT/'design/production-batches/monsters/batch08'
        data=json.loads((root/'provenance.json').read_text())
        self.assertEqual(data['productionRegistered'],0)
        for identity in data['identityReview']:
            self.assertIsNone(identity['productionSpeciesId'])
            self.assertFalse(identity['runtimeEnabled'])
            p=root/identity['conceptId']
            evidence=json.loads((p/'base-measurement.json').read_text())
            self.assertEqual(hashlib.sha256((p/'source-base-v1.png').read_bytes()).hexdigest(),evidence['sourceSha256'])
            self.assertEqual(test_assets.validator.png_errors(p/'base-v2.png',True,[],[]),[])
            cleanup=json.loads((p/'cleanup-validation.json').read_text())
            self.assertEqual(cleanup['connectedBodyPixelChanges'],0)
            self.assertTrue(all(pixel[2]<=4 for pixel in cleanup['removedDisconnectedLowAlphaPixels']))
            self.assertFalse((p/'rigged').exists())
            self.assertFalse((p/'candidate-clip.json').exists())
