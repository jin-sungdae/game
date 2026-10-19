import json
import unittest
from test_assets import ROOT, validator
from test_creature_followup import measure, detached_pixels
from test_moa_blink_v2 import rgba

CASES = ('M004', 'nox/stage02', 'M008', 'ruu/stage04', 'M009', 'ruu/stage05')

class LookContinuationTests(unittest.TestCase):
    def test_six_distinct_anatomy_rigs_preserve_alpha_anchor_and_original_pixels(self):
        profiles = []
        for code in CASES:
            with self.subTest(creature=code):
                folder = ROOT/'design/production-batches/action-followup'/code
                spec = json.loads((folder/'candidate-clip.json').read_text())
                eyes = spec['eyes']
                report = measure(folder, lambda x, y: any(((x-e['x'])/e['rx'])**2+((y-e['y'])/e['ry'])**2 < 1 for e in eyes))
                self.assertEqual(report, json.loads((folder/'frame-validation.json').read_text()))
                self.assertEqual(report['automated'], 'PASS')
                self.assertEqual(report['uniquePixelHashes'], spec['clip']['frames'])
                self.assertEqual(report['detachedAlphaPixels'], 0)
                self.assertFalse(spec['productionEligible'])
                self.assertFalse(spec['runtimeEnabled'])
                self.assertEqual(spec['artworkReview'], 'HUMAN_REVIEW_REQUIRED')
                self.assertEqual(report['naturalLoop'], 'HUMAN_REVIEW_REQUIRED')
                profiles.append(json.dumps(eyes, sort_keys=True))
        self.assertEqual(len(set(profiles)), len(CASES))
        for code in ('ruu/stage04', 'M009'):
            report = json.loads((ROOT/'design/production-batches/action-followup'/code/'frame-validation.json').read_text())
            self.assertFalse(report['loopWithinInteriorDeltaRange'])

    def test_hit_keypose_failure_is_preserved_without_alpha_cleanup_or_clip(self):
        folder = ROOT/'design/production-batches/monsters/hit-pilot/M005'
        report = json.loads((folder/'keypose-validation.json').read_text())
        self.assertTrue((folder/'keypose-tool-reference.png').is_file())
        bounds, hashes = [], []
        self.assertEqual(validator.png_errors(folder/'keypose.png', True, bounds, hashes), report['pngErrors'])
        self.assertEqual(bounds, report['bounds'])
        self.assertEqual(hashes[0], report['pixelHash'])
        self.assertEqual(detached_pixels(rgba(folder/'keypose.png')), 60)
        self.assertEqual(report['detachedAlphaPixels'], 60)
        self.assertEqual(report['status'], 'VALIDATION_FAILED')
        self.assertFalse(report['productionEligible'])
        self.assertFalse(report['animationClipComplete'])
        self.assertFalse((folder/'rigged').exists())

    def test_ledger_keeps_failed_actions_and_existing_production_boundaries(self):
        queue = json.loads((ROOT/'design/creature-production-queue.json').read_text())
        self.assertEqual(queue['repairIterations'], 3)
        self.assertEqual(queue['post114LookContinuation']['repairIterations'], 3)
        caplet = next(r for r in queue['creatures'] if r['creatureId'] == 'M005')
        self.assertFalse(caplet['spawn']['enabled'])
        for name in ('REST', 'INTERACT', 'MOVE', 'TURN', 'HIT'):
            action = next(a for a in caplet['actions'] if a['action'] == name)
            self.assertEqual(action['animationStatus'], 'VALIDATION_FAILED')
            self.assertEqual(action['frameCount'], 0)
            self.assertEqual(action['runtimeStatus'], 'BLOCKED')
        for ident, action in [('companion:nox:2','LOOK'),('companion:ruu:4','BLINK'),('companion:ruu:5','LOOK'),('M004','LOOK'),('M008','LOOK'),('M009','BLINK')]:
            row = next(r for r in queue['creatures'] if r['creatureId'] == ident)
            item = next(a for a in row['actions'] if a['action'] == action)
            self.assertEqual(item['runtimeStatus'], 'BLOCKED')
            self.assertEqual(item['artworkReview'], 'HUMAN_REVIEW_REQUIRED')
        manifest = json.loads((ROOT/'public/assets/monsters/caplet/manifest.json').read_text())
        self.assertEqual(set(manifest['animations']), {'sleep'})
