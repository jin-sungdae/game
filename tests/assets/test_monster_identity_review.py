import hashlib
import json
import unittest
import test_assets

class MonsterIdentityReviewTests(unittest.TestCase):
    def test_review_evidence_cannot_activate_concept_species(self):
        root=test_assets.ROOT
        review=json.loads((root/'design/monster-identity-review.json').read_text())
        self.assertEqual(len(review['legacy']),30)
        self.assertEqual({x['conceptId'] for x in review['candidates']},{f'M{n:03}' for n in range(1,101)})
        self.assertEqual(len(review['missingLegacyArtwork']),15)
        for row in review['legacy']+review['candidates']:
            info=row['asset']
            if 'sha256' in info:
                self.assertEqual(hashlib.sha256((root/info['path']).read_bytes()).hexdigest(),info['sha256'])
        for row in review['candidates']:
            self.assertIsNone(row['productionSpeciesId'])
            self.assertFalse(row['mappingApproved'])
            self.assertFalse(row['runtimeEnabled'])
            self.assertEqual(row['identityStatus'],'HUMAN_REVIEW_REQUIRED')
    def test_sleep_failure_is_not_a_completed_clip(self):
        folder=test_assets.ROOT/'design/production-batches/monsters/sleep-pilot/M005'
        report=json.loads((folder/'base-measurement.json').read_text())
        self.assertEqual(hashlib.sha256((folder/'source-base-v1.png').read_bytes()).hexdigest(),report['sourceSha256'])
        self.assertEqual(report['detachedPixels'],9)
        self.assertEqual(report['detachedMaxAlpha'],1)
        self.assertFalse((folder/'candidate-clip.json').exists())
        self.assertEqual(test_assets.validator.png_errors(folder/'base-v1.png',True,[],[]),[])
        self.assertFalse(json.loads((folder/'provenance.json').read_text())['productionEligible'])
