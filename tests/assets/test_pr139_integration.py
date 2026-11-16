import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from build_creature_review import recorded_candidate_errors, build

class Pr139IntegrationTests(unittest.TestCase):
    def test_failure_is_scoped_to_action_and_candidate_version(self):
        rows=[{'action':'BLINK','animationStatus':'VALIDATION_FAILED','automated':'FAIL',
               'candidatePath':'candidate/v1','validationEvidence':'original.json'}]
        self.assertTrue(recorded_candidate_errors(rows,'blink','candidate/v1'))
        self.assertEqual(recorded_candidate_errors(rows,'look','candidate/v1'),[])
        self.assertEqual(recorded_candidate_errors(rows,'blink','candidate/v2'),[])
        rows[0]['animationStatus']='CANDIDATE_ONLY'
        self.assertTrue(recorded_candidate_errors(rows,'blink','candidate/v1'))

    def test_six_candidates_keep_failure_and_approval_boundaries(self):
        queue=json.loads((ROOT/'design/creature-production-queue.json').read_text())
        catalog=json.loads((ROOT/'tests/live/creature-review/catalog.json').read_text())
        rows={r['creatureId']:r for r in queue['creatures']}
        review={r['id']:r for r in catalog['creatures']}
        total=0
        for identity in ('M092','M095'):
            self.assertIsNone(rows[identity]['productionSpeciesId'])
            for name,count in [('breath',8),('blink',12),('look',12)]:
                with self.subTest(identity=identity,action=name):
                    action=next(a for a in rows[identity]['actions'] if a['action']==name.upper())
                    clips=[c for c in review[identity]['clips'] if c['action']==name and '/LUMA-ASSET-22/' in c['directory']]
                    self.assertEqual(len(clips),1)
                    clip=clips[0];failed=name=='blink' or (identity=='M092' and name=='breath')
                    self.assertEqual(clip['automated'],'VALIDATION_FAILED' if failed else 'PASS')
                    self.assertEqual(action['automated'],'FAIL' if failed else 'PASS')
                    self.assertEqual(clip['frameCount'],count);total+=count
                    self.assertEqual(action['frameCount'],count)
                    self.assertEqual(action['runtimeStatus'],'BLOCKED')
                    self.assertFalse(action['productionEligible']);self.assertFalse(clip['runtimeEnabled'])
                    self.assertEqual(clip['artwork'],'HUMAN_REVIEW_REQUIRED')
                    self.assertTrue((ROOT/action['validationEvidence']).is_file())
                    self.assertEqual(len(clip['pixelHashes']),count)
                    self.assertEqual(len(set(clip['pixelHashes'])),count)
                    self.assertTrue(all((ROOT/u.lstrip('/')).is_file() for u in clip['urls']))
        self.assertEqual(total,64)
        self.assertEqual(queue['pr139Integration']['productionApprovals'],0)

    def test_scoped_refresh_is_idempotent_and_preserves_other_reviews(self):
        catalog=json.loads((ROOT/'tests/live/creature-review/catalog.json').read_text())
        self.assertEqual(build(['M092','M095']),catalog)

    def test_source_frames_match_preserved_evidence(self):
        analysis=json.loads((ROOT/'design/production-batches/LUMA-ASSET-22/continuation-analysis.json').read_text())
        for result in analysis['results']:
            for frame in result['frames']:
                self.assertEqual(hashlib.sha256((ROOT/frame['file']).read_bytes()).hexdigest(),frame['fileSha256'])
