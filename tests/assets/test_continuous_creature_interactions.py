import json
import unittest

from test_action_production_continuation import BATCH, measured
from test_assets import ROOT

CASES = (
    'nox/stage02/interact-pilot', 'M002/interact-pilot',
    'moa/stage05/interact-pilot', 'ruu/stage04/cursor-react-pilot',
)


class ContinuousCreatureInteractionTests(unittest.TestCase):
    def test_candidate_pixels_keep_alpha_anchor_and_protected_anatomy(self):
        signatures = set()
        durations = set()
        for code in CASES:
            with self.subTest(code=code):
                folder = BATCH / code
                spec = json.loads((folder / 'candidate-clip.json').read_text())
                report = measured(folder)
                self.assertEqual(report, json.loads((folder / 'frame-validation.json').read_text()))
                self.assertEqual(report['automated'], 'PASS')
                self.assertEqual(report['uniquePixelHashes'], 8)
                self.assertEqual(report['detachedAlphaPixels'], 0)
                self.assertTrue(all(report['adjacentPixelDifferenceSumsIncludingLoop']))
                for frame in report['frames']:
                    self.assertTrue(frame['alphaMatchesBase'])
                    self.assertEqual(frame['protectedPixelChanges'], 0)
                    self.assertEqual(frame['anchorDriftPixels'], {'bottom': 0, 'boundsCenterX': 0})
                rig = json.loads((folder / 'rig-evidence.json').read_text())
                self.assertFalse(rig['wholeImageTransform'])
                self.assertTrue(all(0 < f['maxInverseDisplacementPixels'] < 2 for f in rig['frames']))
                self.assertFalse(spec['clip']['loop'])
                self.assertEqual(spec['anchor'], {'x': .5, 'y': 1})
                self.assertFalse(spec['runtimeEnabled'])
                self.assertFalse(spec['productionEligible'])
                signatures.add(json.dumps(spec['parts'], sort_keys=True))
                durations.add(spec['clip']['frameDuration'])
        self.assertEqual(len(signatures), len(CASES))
        self.assertEqual(len(durations), len(CASES))

    def test_ledger_keeps_review_and_resume_boundaries(self):
        queue = json.loads((ROOT / 'design/creature-production-queue.json').read_text())
        run = queue['continuousDevelopment']
        self.assertEqual(queue['repairIterations'], 3)
        self.assertEqual(run['repairIterations'], 3)
        self.assertEqual(run['candidateFrames'], 32)
        self.assertEqual(run['candidatePng'], 36)
        self.assertEqual(run['productionRegistrations'], 0)
        self.assertEqual(run['runtimeConnections'], 0)
        self.assertEqual(run['approvedUnconnectedAssets'], [])
        self.assertEqual(set(run['newCases'].values()), set(CASES))
        self.assertTrue(run['lastValidatedCommit'])
        self.assertTrue(run['nextTask'])
        for identity_action, code in run['newCases'].items():
            identity, action = identity_action.split()
            row = next(r for r in queue['creatures'] if r['creatureId'] == identity)
            item = next(a for a in row['actions'] if a['action'] == action)
            self.assertEqual(item['runtimeStatus'], 'BLOCKED')
            self.assertEqual(item['artworkReview'], 'HUMAN_REVIEW_REQUIRED')
            self.assertEqual(item['candidatePath'], str((BATCH / code).relative_to(ROOT)))
        caplet = next(r for r in queue['creatures'] if r['creatureId'] == 'M005')
        self.assertFalse(caplet['spawn']['enabled'])
