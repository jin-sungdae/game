"""Scoped continuation: preserve failures and validate anatomically bounded candidates."""
import hashlib
import json
import unittest
from test_assets import ROOT
from test_creature_followup import measure

BATCH = ROOT / 'design/production-batches/luma-asset-04'
CASES = [('M004', 'blink-approved-repair')] + [(m, 'rest-pilot') for m in ('M001', 'M002', 'M003', 'M004')]


def movable_for(spec):
    rectangles = {'M001': (87, 165, 181, 207), 'M002': (104, 137, 185, 180),
                  'M003': (83, 129, 183, 192)}
    def movable(x, y):
        eye = any(((x-e['x'])/e['rx'])**2 + ((y-e['y'])/e['ry'])**2 < 1 for e in spec['eyes'])
        if spec['clip']['name'] != 'REST':
            return eye
        if spec['conceptId'] == 'M004':
            return eye or (80 < x < 188 and 100 < y < 182 and not (x >= 151 and y <= 123))
        left, top, right, bottom = rectangles[spec['conceptId']]
        return eye or left < x < right and top < y < bottom
    return movable


class LumaAsset04ContinuationTests(unittest.TestCase):
    def test_candidate_pixels_and_evidence(self):
        for identity, name in CASES:
            with self.subTest(identity=identity, name=name):
                folder = BATCH / identity / name
                spec = json.loads((folder / 'candidate-clip.json').read_text())
                result = measure(folder, movable_for(spec))
                self.assertEqual(result, json.loads((folder / 'frame-validation.json').read_text()))
                self.assertEqual(result['automated'], 'PASS')
                self.assertEqual(result['uniquePixelHashes'], spec['clip']['frames'])
                self.assertTrue(all(v > 0 for v in result['adjacentPixelDifferenceSumsIncludingLoop']))
                for frame in result['frames']:
                    self.assertEqual(frame['errors'], [])
                    self.assertEqual(frame['protectedPixelChanges'], 0)
                    self.assertTrue(frame['alphaMatchesBase'])
                    self.assertEqual(frame['anchorDriftPixels'], {'bottom': 0, 'boundsCenterX': 0.0})
                self.assertFalse(spec['runtimeEnabled'])
                self.assertFalse(spec['productionEligible'])
                for prefix in ('rigSource', 'eyeRigSource'):
                    if prefix in spec:
                        self.assertEqual(hashlib.sha256((ROOT / spec[prefix]).read_bytes()).hexdigest(), spec[prefix+'Sha256'])

    def test_original_failed_blink_preserved_and_exception_scoped(self):
        original = BATCH / 'M004/blink-pilot'
        evidence = json.loads((original / 'frame-validation.json').read_text())
        self.assertEqual(evidence['automated'], 'VALIDATION_FAILED')
        self.assertEqual(evidence['uniquePixelHashes'], 5)
        self.assertIn(0, evidence['adjacentPixelDifferenceSumsIncludingLoop'])
        repair = json.loads((BATCH / 'M004/blink-approved-repair/candidate-clip.json').read_text())
        self.assertEqual(repair['exceptionAttempt'], 1)
        self.assertEqual(repair['preservedFailure'], str(original.relative_to(ROOT)))
        self.assertEqual((repair['repairIterations'], repair['repairLimit']), (3, 3))
        self.assertFalse((BATCH / 'M005').exists())

    def test_rest_only_previously_unproduced_actions(self):
        rows = json.loads((ROOT / 'design/creature-production-queue.json').read_text())['creatures']
        for row in rows:
            if row['creatureId'] in ('M001', 'M002', 'M003', 'M004'):
                action = next(a for a in row['actions'] if a['action'] == 'REST')
                self.assertEqual(action['frameCount'], 0)
                self.assertEqual(action['animationStatus'], 'ASSET_REQUIRED')
