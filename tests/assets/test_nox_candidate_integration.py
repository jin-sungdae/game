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

    def test_nox_stage_two_ledger_preserves_unrelated_state(self):
        queue = json.loads((ROOT/'design/creature-production-queue.json').read_text())
        audit = queue['approvalBottleneckContinuation']['approvalAudit']
        added = [c for c in audit['clips'] if c['creatureId']=='companion:nox:2'
                 and '/LUMA-ASSET-03/' in c['directory']]
        self.assertCountEqual([c['action'] for c in added], ACTIONS)
        self.assertTrue(all(c['productionApproval']=='NOT_APPROVED' and
                            c['runtimeStatus']=='BLOCKED' and
                            c['artworkReview']=='HUMAN_REVIEW_REQUIRED' for c in added))

        row = next(r for r in queue['creatures'] if r['creatureId']=='companion:nox:2')
        row.pop('animationCoverage')
        for index, action in enumerate(row['actions']):
            if action['action'] in ACTIONS:
                row['actions'][index] = dict(action=action['action'], animationStatus='ASSET_REQUIRED',
                    frameCount=0, runtimeStatus='NOT_VERIFIED', guiStatus='GUI_NOT_VERIFIED')
        # Compare this creature to PR131 before NOX candidate registration.
        digest = hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
        self.assertEqual(digest, 'c7595fbc7a367c4ae288921c1e6a0c4d91beaaef30231fb06c3a966722f6ae4b')
