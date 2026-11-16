import hashlib
import json
import unittest
from test_assets import ROOT

ACTIONS = {'BREATH', 'SKILL_CAST', 'VICTORY'}

class NoxCandidateIntegrationTests(unittest.TestCase):
    def test_three_candidates_are_registered_once_without_activation(self):
        queue = json.loads((ROOT/'design/creature-production-queue.json').read_text())
        catalog = json.loads((ROOT/'tests/live/creature-review/catalog.json').read_text())
        row = next(r for r in queue['creatures'] if r['creatureId']=='companion:nox:2')
        review = next(r for r in catalog['creatures'] if r['id']==row['creatureId'])
        for action in ACTIONS:
            records = [a for a in row['actions'] if a['action']==action]
            clips = [c for c in review['clips'] if c['action']==action.lower()]
            self.assertEqual(len(records),1)
            self.assertEqual(len(clips),1)
            record, clip = records[0], clips[0]
            self.assertEqual(record['candidateStatus'],'CANDIDATE_ONLY')
            self.assertEqual(record['artworkReview'],'HUMAN_REVIEW_REQUIRED')
            self.assertEqual(record['guiStatus'],'DEFERRED_GUI')
            self.assertEqual(record['runtimeStatus'],'BLOCKED')
            self.assertEqual(record['animationStatus'],'ANIMATION_IN_PROGRESS')
            self.assertEqual(record['frameCount'],8)
            self.assertEqual(clip['frameCount'],8)
            self.assertEqual(len(set(clip['pixelHashes'])),8)
            self.assertFalse(clip['runtimeEnabled'])
            self.assertEqual(clip['directory'],'/'+record['candidatePath']+'/rigged/'+action.lower())
            self.assertEqual(review['actions'],row['actions'])
        self.assertEqual(row['animationCoverage'],review['coverage'])
        self.assertFalse(catalog['productionRegistration'])

    def test_other_ledger_state_is_identical_to_pr131(self):
        queue = json.loads((ROOT/'design/creature-production-queue.json').read_text())
        audit = queue['approvalBottleneckContinuation']['approvalAudit']
        added = [c for c in audit['clips'] if '/LUMA-ASSET-03/' in c['directory']]
        self.assertEqual({c['action'] for c in added}, ACTIONS)
        self.assertEqual(len(added), 3)
        self.assertTrue(all(c['productionApproval']=='NOT_APPROVED' for c in added))
        audit['clips'] = [c for c in audit['clips'] if c not in added]
        for key in ('candidateClips','automatedPngPassClips','artworkReviewPendingClips',
                    'naturalMotionReviewPendingClips','guiPendingClips'):
            audit['summary'][key] -= 3
        audit['summary']['candidateFrames'] -= 24
        queue.pop('animationCoverageSummary')
        for row in queue['creatures']:
            row.pop('animationCoverage')
            if row['creatureId']=='companion:nox:2':
                for index, action in enumerate(row['actions']):
                    if action['action'] in ACTIONS:
                        row['actions'][index] = dict(action=action['action'],animationStatus='ASSET_REQUIRED',
                            frameCount=0,runtimeStatus='NOT_VERIFIED',guiStatus='GUI_NOT_VERIFIED')
        digest = hashlib.sha256(json.dumps(queue,sort_keys=True).encode()).hexdigest()
        # PR131 c40da57: all failures, approvals, counters, runtime and other creatures stay unchanged.
        self.assertEqual(digest,'81202eafa11afb8a082dc970722d79c96fdfe765f65d8cd65a138a92ef1fdd40')
