import json
import unittest
from test_action_production_continuation import BATCH, measured
from test_assets import ROOT, validator
from test_creature_followup import detached_pixels
from test_moa_blink_v2 import rgba

CASES = {
    'M009 INTERACT': 'M009/interact-pilot',
    'M011 INTERACT': 'M011/interact-pilot',
    'M012 CURSOR_REACT': 'M012/cursor-react-pilot',
    'companion:moa:5 CURSOR_REACT': 'moa/stage05/cursor-react-pilot',
}
FAILED = {'M011/rest-pilot': 85, 'M009/turn-pilot': 536}


class CreaturePoseDiversityTests(unittest.TestCase):
    def test_distinct_responses_preserve_alpha_anchor_and_protected_anatomy(self):
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

    def test_dedicated_rest_and_turn_failures_keep_raw_output_without_fake_clips(self):
        for code, detached in FAILED.items():
            with self.subTest(code=code):
                folder = BATCH / code
                report = json.loads((folder / 'keypose-validation.json').read_text())
                bounds, hashes = [], []
                self.assertEqual(validator.png_errors(folder / 'keypose.png', True, bounds, hashes), report['pngErrors'])
                self.assertEqual(bounds, report['bounds'])
                self.assertEqual(hashes[0], report['pixelHash'])
                self.assertEqual(detached_pixels(rgba(folder / 'keypose.png')), detached)
                self.assertEqual(report['detachedAlphaPixels'], detached)
                self.assertEqual(report['status'], 'VALIDATION_FAILED')
                self.assertFalse(report['productionEligible'])
                self.assertFalse(report['animationClipComplete'])
                self.assertTrue((folder / 'keypose-tool-reference.png').is_file())
                self.assertFalse((folder / 'rigged').exists())

    def test_ledger_preserves_review_repair_and_runtime_boundaries(self):
        queue = json.loads((ROOT / 'design/creature-production-queue.json').read_text())
        run = queue['poseDiversityContinuation']
        self.assertEqual(queue['repairIterations'], 3)
        self.assertEqual(run['repairIterations'], 3)
        self.assertEqual(run['newCases'], CASES)
        self.assertEqual(run['candidateFrames'], 32)
        self.assertEqual(run['candidatePng'], 40)
        self.assertEqual(run['productionRegistrations'], 0)
        self.assertEqual(run['runtimeConnections'], 0)
        self.assertEqual(run['approvedUnconnectedAssets'], [])
        pngs = [p for code in [*CASES.values(), *FAILED] for p in (BATCH / code).rglob('*.png')]
        self.assertEqual(len(pngs), run['candidatePng'])
        for identity_action, code in CASES.items():
            identity, action = identity_action.split()
            item = next(a for r in queue['creatures'] if r['creatureId'] == identity for a in r['actions'] if a['action'] == action)
            self.assertEqual(item['runtimeStatus'], 'BLOCKED')
            self.assertEqual(item['artworkReview'], 'HUMAN_REVIEW_REQUIRED')
            self.assertEqual(item['candidatePath'], str((BATCH / code).relative_to(ROOT)))
        for identity, action in [('M009', 'TURN'), ('M011', 'REST')]:
            item = next(a for r in queue['creatures'] if r['creatureId'] == identity for a in r['actions'] if a['action'] == action)
            self.assertEqual(item['animationStatus'], 'VALIDATION_FAILED')
            self.assertEqual(item['frameCount'], 0)
        self.assertTrue(run['nextTask'])
        self.assertFalse(next(r for r in queue['creatures'] if r['creatureId'] == 'M005')['spawn']['enabled'])
