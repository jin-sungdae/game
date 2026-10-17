import hashlib
import json
import unittest
from pathlib import Path
import test_assets

class MonsterBatch01Tests(unittest.TestCase):
    def test_candidate_clips_are_unique_and_unmapped(self):
        root=test_assets.ROOT/'design/production-batches/monsters/batch01'
        for code,bounds in [('M004',[28,19,232,234]),('M010',[33,42,229,216])]:
            p=root/code;m=json.loads((p/'candidate-clip.json').read_text())
            self.assertEqual(m['conceptId'],code)
            self.assertIsNone(m['productionSpeciesId'])
            self.assertFalse(m['runtimeEnabled']);self.assertFalse(m['productionEligible'])
            frames=sorted((p/'rigged/idle').glob('*.png'));self.assertEqual(len(frames),4)
            hashes=[]
            for frame in frames:
                actual=[];self.assertEqual(test_assets.validator.png_errors(frame,True,actual,hashes),[])
                self.assertEqual(actual,bounds)
            self.assertEqual(len(set(hashes)),4)
            self.assertFalse((test_assets.ROOT/'public/assets/monsters'/code.lower()).exists())

    def test_existing_thirty_identities_and_fifteen_artworks_unchanged(self):
        p=test_assets.ROOT/'design/production-batches/monsters/batch01/identity-review.json';review=json.loads(p.read_text())
        self.assertEqual(review['existingDexCount'],30);self.assertEqual(review['existingPngCount'],15)
        for file,key in [('src/entities/monster-dex.json','existingIdentitySha256'),('src/entities/monsters.json','productionRegistrySha256')]:
            self.assertEqual(hashlib.sha256((test_assets.ROOT/file).read_bytes()).hexdigest(),review[key])
        for row in review['existingPngs']:
            self.assertEqual(hashlib.sha256((test_assets.ROOT/row['path']).read_bytes()).hexdigest(),row['sha256'])
        for row in review['rows']:
            self.assertIsNone(row['productionSpeciesId']);self.assertFalse(row['mappingApproved']);self.assertFalse(row['runtimeEnabled'])
