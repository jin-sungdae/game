"""ASSET-07 candidate checks; known failed artwork is never promoted by a green test."""
import hashlib
import json
import unittest

from test_action_production_continuation import measured
from test_assets import ROOT

BATCH = ROOT / 'design/production-batches/asset07'


class Asset07Candidates(unittest.TestCase):
    def test_actual_pixels_match_evidence_and_preserve_failure_status(self):
        for number in range(16, 21):
            for action in ('blink', 'look', 'interact'):
                with self.subTest(number=number, action=action):
                    folder = BATCH / f'M{number:03}' / action
                    spec = json.loads((folder / 'candidate-clip.json').read_text())
                    report = measured(folder)
                    self.assertEqual(report, json.loads((folder / 'frame-validation.json').read_text()))
                    failed = action == 'interact' or (number == 18 and action == 'blink')
                    self.assertEqual(report['automated'], 'VALIDATION_FAILED' if failed else 'PASS')
                    review = json.loads((folder / 'review-result.json').read_text())
                    self.assertEqual(review['status'], 'HUMAN_REVIEW_REQUIRED' if action == 'look' else 'BLOCKED')
                    self.assertFalse(review['productionEligible'])
                    self.assertFalse(spec['runtimeEnabled'])
                    self.assertEqual(spec['repairIterations'], 3)
                    self.assertFalse(review['repairPerformed'])
                    self.assertEqual(spec['anchor'], {'x': .5, 'y': 1})
                    if action == 'look':
                        self.assertEqual(report['uniquePixelHashes'], 8)
                        self.assertTrue(all(report['adjacentPixelDifferenceSumsIncludingLoop']))
                        for frame in report['frames']:
                            self.assertEqual(frame['protectedPixelChanges'], 0)
                            self.assertTrue(frame['alphaMatchesBase'])
                            self.assertEqual(frame['anchorDriftPixels'], {'bottom': 0, 'boundsCenterX': 0})
                    elif action == 'blink':
                        self.assertEqual(review['appearance'], 'FAIL')
                    else:
                        self.assertEqual(report['frames'], [])
                        self.assertEqual(review['generationExitCode'], 1)

    def test_existing_artwork_and_failed_candidates_are_preserved(self):
        evidence = json.loads((BATCH / 'session-evidence.json').read_text())
        self.assertEqual(evidence['apiCalls'], 0)
        self.assertEqual(evidence['repairIterations'], evidence['repairLimit'])
        self.assertEqual(evidence['runtimeConnected'], 0)
        self.assertEqual(len(evidence['coverage']), 5)
        for row in evidence['coverage']:
            self.assertEqual(len(row['actions']), 15)
            self.assertIsNone(row['productionSpeciesId'])
        # Shared ledgers may legitimately advance in other tracks; do not freeze them.
        for relative, expected in evidence['preservedFileSha256'].items():
            if '/M0' in relative:
                with self.subTest(path=relative):
                    self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), expected)
