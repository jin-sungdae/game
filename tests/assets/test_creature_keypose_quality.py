import hashlib
import json
import struct
import unittest
from pathlib import Path
from test_assets import ROOT, validator
from test_moa_blink_v2 import rgba
from test_creature_followup import detached_pixels
from test_creature_impact_continuation import measure_impact

BATCH = ROOT / 'design/production-batches/action-followup'
CASES = {'companion:moa:4': 'moa/stage04/hit-pilot', 'M018': 'M018/hit-pilot', 'companion:ruu:4': 'ruu/stage04/hit-pilot'}
FAILED = {'M017/turn-pilot': 147, 'M020/rest-pilot': 187}

class KeyposeQualityContinuation(unittest.TestCase):
    def test_three_impact_candidates_have_actual_part_motion_without_fixed_anatomy_drift(self):
        signatures = set()
        for identity, code in CASES.items():
            with self.subTest(identity=identity):
                folder = BATCH / code
                spec = json.loads((folder / 'candidate-clip.json').read_text())
                report = measure_impact(folder)
                self.assertEqual(report, json.loads((folder / 'frame-validation.json').read_text()))
                self.assertEqual(report['automated'], 'PASS')
                self.assertEqual(report['uniquePixelHashes'], 8)
                self.assertEqual(len(report['frames']), 8)
                for f in report['frames']:
                    self.assertEqual(f['errors'], [])
                    self.assertGreater(f['alphaChangedPixels'], 0)
                    self.assertEqual(f['protectedPixelChanges'], 0)
                    self.assertEqual(f['detachedAlphaPixels'], 0)
                    self.assertEqual(f['canvasEdgePixels'], 0)
                    self.assertEqual(f['anchorDriftPixels'], {'bottom': 0, 'boundsCenterX': 0})
                self.assertTrue(all(report['adjacentPixelDifferenceSumsIncludingLoop']))
                self.assertFalse(spec['clip']['loop'])
                self.assertFalse(spec['runtimeEnabled'])
                self.assertFalse(spec['productionEligible'])
                rig = json.loads((folder / 'rig-evidence.json').read_text())
                self.assertFalse(rig['wholeImageTransform'])
                self.assertTrue(rig['silhouetteMotion'])
                self.assertTrue(all(0 < f['maxInverseDisplacementPixels'] < 4 for f in rig['frames']))
                signatures.add(json.dumps(spec['parts'], sort_keys=True))
        self.assertEqual(len(signatures), 3)

    def test_failed_turn_and_rest_keyposes_are_retained_without_fake_animation(self):
        for code, count in FAILED.items():
            with self.subTest(code=code):
                folder = BATCH / code
                report = json.loads((folder / 'keypose-validation.json').read_text())
                bounds, hashes = [], []
                self.assertEqual(validator.png_errors(folder / 'keypose.png', True, bounds, hashes), report['pngErrors'])
                self.assertEqual(bounds, report['bounds'])
                self.assertEqual(hashes[0], report['pixelHash'])
                self.assertEqual(detached_pixels(rgba(folder / 'keypose.png')), count)
                self.assertEqual(report['detachedAlphaPixels'], count)
                self.assertEqual(report['status'], 'VALIDATION_FAILED')
                self.assertFalse(report['productionEligible'])
                self.assertFalse(report['animationClipComplete'])
                self.assertTrue((folder / 'keypose-tool-reference.png').is_file())
                self.assertFalse((folder / 'rigged').exists())

    def test_alpha_diagnostic_evidence_keeps_originals_and_zero_threshold_gate(self):
        q = json.loads((ROOT / 'design/creature-production-queue.json').read_text())
        evidence = q['keyposeQualityContinuation']['alphaRootCause']['measurements']
        self.assertEqual(len(evidence), 6)
        for code, result in evidence.items():
            with self.subTest(code=code):
                for filename in ['keypose-tool-reference.png', 'keypose.png']:
                    b = (ROOT / code / filename).read_bytes()
                    self.assertEqual(hashlib.sha256(b).hexdigest(), result[filename]['sha256'])
                    first = result[filename]['probes'][0]
                    self.assertEqual(first['threshold'], 0)
                    self.assertEqual(struct.unpack('>II', b[16:24]), (first['width'], first['height']))
                    self.assertGreater(first['detachedPixels'], 0)
                self.assertEqual(detached_pixels(rgba(ROOT / code / 'keypose.png')), result['keypose.png']['probes'][0]['detachedPixels'])
                self.assertTrue(result['kernels']['lanczos3']['preparedPixelsIdentical'])
                self.assertTrue(all(k['detachedPixels'] > 0 for k in result['kernels'].values()))
        self.assertEqual(q['repairIterations'], 3)

    def test_ledger_separates_candidate_generation_approval_and_runtime(self):
        q = json.loads((ROOT / 'design/creature-production-queue.json').read_text())
        run = q['keyposeQualityContinuation']
        self.assertEqual(run['newCases'], CASES)
        self.assertEqual(run['repairIterations'], 3)
        self.assertEqual(run['candidateFrames'], 24)
        self.assertEqual(run['candidatePng'], 31)
        self.assertEqual(sum(len(list((BATCH / p).rglob('*.png'))) for p in [*CASES.values(), *FAILED]), 31)
        self.assertEqual(run['productionRegistrations'], 0)
        self.assertEqual(run['runtimeConnections'], 0)
        self.assertEqual(run['approvedUnconnectedAssets'], [])
        for identity in CASES:
            action = next(a for r in q['creatures'] if r['creatureId'] == identity for a in r['actions'] if a['action'] == 'HIT')
            self.assertEqual(action['artworkReview'], 'HUMAN_REVIEW_REQUIRED')
            self.assertEqual(action['runtimeStatus'], 'BLOCKED')
        self.assertTrue(run['nextTask'])
