import json
import unittest

from test_action_production_continuation import BATCH, measured
from test_assets import ROOT, validator
from test_creature_followup import detached_pixels
from test_moa_blink_v2 import rgba

CASES = {
    'M003 INTERACT': 'M003/interact-pilot',
    'M004 CURSOR_REACT': 'M004/cursor-react-pilot',
    'M006 INTERACT': 'M006/interact-pilot',
    'companion:ruu:5 INTERACT': 'ruu/stage05/interact-pilot',
}


class CreatureResponseContinuationTests(unittest.TestCase):
    def test_response_frames_keep_alpha_fixed_anatomy_and_unique_timing(self):
        signatures, durations = set(), set()
        for code in CASES.values():
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
                self.assertFalse(spec['runtimeEnabled'])
                self.assertFalse(spec['productionEligible'])
                self.assertEqual(spec['anchor'], {'x': .5, 'y': 1})
                signatures.add(json.dumps(spec['parts'], sort_keys=True))
                durations.add(spec['clip']['frameDuration'])
        self.assertEqual(len(signatures), len(CASES))
        self.assertEqual(len(durations), len(CASES))

    def test_failed_rest_keypose_preserves_alpha_evidence_and_has_no_clip(self):
        folder = BATCH / 'M008/rest-pilot'
        report = json.loads((folder / 'keypose-validation.json').read_text())
        bounds, hashes = [], []
        self.assertEqual(validator.png_errors(folder / 'keypose.png', True, bounds, hashes), report['pngErrors'])
        self.assertEqual(bounds, report['bounds'])
        self.assertEqual(hashes[0], report['pixelHash'])
        self.assertEqual(detached_pixels(rgba(folder / 'keypose.png')), 93)
        self.assertEqual(report['detachedAlphaPixels'], 93)
        self.assertEqual(report['status'], 'VALIDATION_FAILED')
        self.assertFalse(report['productionEligible'])
        self.assertFalse(report['animationClipComplete'])
        self.assertTrue((folder / 'keypose-tool-reference.png').is_file())
        self.assertFalse((folder / 'rigged').exists())

    def test_ledger_keeps_unapproved_candidates_out_of_runtime(self):
        queue = json.loads((ROOT / 'design/creature-production-queue.json').read_text())
        run = queue['responseContinuation']
        self.assertEqual(queue['repairIterations'], 3)
        self.assertEqual(run['repairIterations'], 3)
        self.assertEqual(run['newCases'], CASES)
        self.assertEqual(run['candidateFrames'], 32)
        self.assertEqual(run['candidatePng'], 38)
        self.assertEqual(run['productionRegistrations'], 0)
        self.assertEqual(run['runtimeConnections'], 0)
        self.assertEqual(run['approvedUnconnectedAssets'], [])
        pngs = list((BATCH / 'M008/rest-pilot').rglob('*.png'))
        for identity_action, code in CASES.items():
            pngs.extend((BATCH / code).rglob('*.png'))
            identity, action = identity_action.split()
            item = next(a for r in queue['creatures'] if r['creatureId'] == identity for a in r['actions'] if a['action'] == action)
            self.assertEqual(item['runtimeStatus'], 'BLOCKED')
            self.assertEqual(item['artworkReview'], 'HUMAN_REVIEW_REQUIRED')
            self.assertEqual(item['candidatePath'], str((BATCH / code).relative_to(ROOT)))
        self.assertEqual(len(pngs), run['candidatePng'])
        rest = next(a for r in queue['creatures'] if r['creatureId'] == 'M008' for a in r['actions'] if a['action'] == 'REST')
        self.assertEqual(rest['animationStatus'], 'VALIDATION_FAILED')
        self.assertEqual(rest['frameCount'], 0)
        self.assertTrue(run['nextTask'])
        self.assertFalse(next(r for r in queue['creatures'] if r['creatureId'] == 'M005')['spawn']['enabled'])
