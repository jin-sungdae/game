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
            self.assertEqual(row['productionSpeciesId'], 'CAPLET' if row['conceptId']=='M005' else None)
            self.assertEqual(row['mappingApproved'], row['conceptId']=='M005')
            self.assertFalse(row['runtimeEnabled'])
            self.assertEqual(row['identityStatus'],'USER_APPROVED' if row['conceptId']=='M005' else 'HUMAN_REVIEW_REQUIRED')
    def test_sleep_failure_is_not_a_completed_clip(self):
        folder=test_assets.ROOT/'design/production-batches/monsters/sleep-pilot/M005'
        report=json.loads((folder/'base-measurement.json').read_text())
        self.assertEqual(hashlib.sha256((folder/'source-base-v1.png').read_bytes()).hexdigest(),report['sourceSha256'])
        self.assertEqual(report['detachedPixels'],9)
        self.assertEqual(report['detachedMaxAlpha'],1)
        self.assertFalse((folder/'candidate-clip.json').exists())
        self.assertEqual(test_assets.validator.png_errors(folder/'base-v1.png',True,[],[]),[])
        self.assertFalse(json.loads((folder/'provenance.json').read_text())['productionEligible'])

    def test_inventory_includes_new_sleep_sources_without_counting_completed_clips(self):
        root=test_assets.ROOT
        queue=json.loads((root/'design/creature-production-queue.json').read_text())
        assets=root/'design/production-batches/monsters'
        self.assertEqual(queue['candidateInventory']['allCandidatePng'],len(list(assets.rglob('*.png'))))
        self.assertEqual(queue['candidateInventory']['sourcePngIncludingRecovery'],len(list(assets.rglob('source*.png'))))
        self.assertEqual(queue['currentBatch']['completedAnimationClips'],1)

    def test_approved_cleanup_preserves_body_and_rgb(self):
        from PIL import Image
        folder=test_assets.ROOT/'design/production-batches/monsters/sleep-pilot/M005'
        before=list(Image.open(folder/'base-v1.png').getdata())
        after=list(Image.open(folder/'base-v2.png').getdata())
        changed=[(a,b) for a,b in zip(before,after) if a!=b]
        self.assertEqual(len(changed),9)
        self.assertTrue(all(a[:3]==b[:3] and a[3]==1 and b[3]==0 for a,b in changed))
        self.assertEqual(test_assets.validator.png_errors(folder/'base-v2.png',True,[],[]),[])
