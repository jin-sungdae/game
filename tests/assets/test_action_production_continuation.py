import json
import unittest
from test_assets import ROOT, validator
from test_creature_followup import measure, detached_pixels
from test_moa_blink_v2 import rgba

BATCH = ROOT / 'design/production-batches/action-followup'
PASS_CASES = ('M010', 'ruu/stage03/interact-pilot', 'M001/interact-pilot')


def measured(folder):
    spec = json.loads((folder / 'candidate-clip.json').read_text())
    if 'eyes' in spec:
        movable = lambda x, y: any(((x-e['x'])/e['rx'])**2 + ((y-e['y'])/e['ry'])**2 < 1 for e in spec['eyes'])
    else:
        left, top, right, bottom = spec['movableRect']
        movable = lambda x, y: left < x < right and top < y < bottom
    return measure(folder, movable)


class ActionProductionContinuationTests(unittest.TestCase):
    def test_new_gaze_and_interaction_frames_preserve_fixed_anatomy(self):
        for code in PASS_CASES:
            with self.subTest(code=code):
                folder = BATCH / code
                spec = json.loads((folder / 'candidate-clip.json').read_text())
                report = measured(folder)
                self.assertEqual(report, json.loads((folder / 'frame-validation.json').read_text()))
                self.assertEqual(report['automated'], 'PASS')
                self.assertEqual(report['uniquePixelHashes'], 8)
                self.assertEqual(report['detachedAlphaPixels'], 0)
                self.assertFalse(spec['runtimeEnabled'])
                self.assertFalse(spec['productionEligible'])
                self.assertEqual(report['appearance'], 'HUMAN_REVIEW_REQUIRED')
                self.assertEqual(spec['clip']['loop'], code == 'M010')

    def test_nox_blink_duplicate_frames_remain_failed_without_recovery(self):
        folder = BATCH / 'nox/stage02/blink-pilot'
        report = measured(folder)
        self.assertEqual(report, json.loads((folder / 'frame-validation.json').read_text()))
        self.assertEqual(len(report['frames']), 6)
        self.assertEqual(report['uniquePixelHashes'], 5)
        self.assertEqual(report['automated'], 'VALIDATION_FAILED')
        self.assertFalse(report['productionEligible'])

    def test_failed_keyposes_preserve_raw_output_and_measured_alpha_defects(self):
        cases = (
            ('design/production-batches/monsters/victory-pilot/M005', 24),
            ('design/production-batches/action-followup/nox/stage02/sleep-pilot', 40),
        )
        for directory, detached in cases:
            with self.subTest(directory=directory):
                folder = ROOT / directory
                report = json.loads((folder / 'keypose-validation.json').read_text())
                self.assertTrue((folder / 'keypose-tool-reference.png').is_file())
                bounds, hashes = [], []
                self.assertEqual(validator.png_errors(folder / 'keypose.png', True, bounds, hashes), report['pngErrors'])
                self.assertEqual(bounds, report['bounds'])
                self.assertEqual(hashes[0], report['pixelHash'])
                self.assertEqual(detached_pixels(rgba(folder / 'keypose.png')), detached)
                self.assertEqual(report['detachedAlphaPixels'], detached)
                self.assertEqual(report['status'], 'VALIDATION_FAILED')
                self.assertFalse(report['animationClipComplete'])
                self.assertFalse((folder / 'rigged').exists())

    def test_ledger_and_manifests_do_not_activate_unapproved_actions(self):
        queue = json.loads((ROOT / 'design/creature-production-queue.json').read_text())
        self.assertEqual(queue['repairIterations'], 3)
        self.assertEqual(queue['actionProductionContinuation']['repairIterations'], 3)
        cases = [('M010', 'LOOK'), ('M001', 'INTERACT'), ('companion:ruu:3', 'INTERACT'),
                 ('companion:nox:2', 'BLINK'), ('companion:nox:2', 'SLEEP'), ('M005', 'VICTORY')]
        for ident, action in cases:
            row = next(r for r in queue['creatures'] if r['creatureId'] == ident)
            item = next(a for a in row['actions'] if a['action'] == action)
            self.assertEqual(item['runtimeStatus'], 'BLOCKED')
            self.assertEqual(item['artworkReview'], 'HUMAN_REVIEW_REQUIRED')
        caplet = next(r for r in queue['creatures'] if r['creatureId'] == 'M005')
        self.assertFalse(caplet['spawn']['enabled'])
        for directory, supplied in [('monsters/caplet', {'sleep'}), ('creatures/ruu/stage03', {'idle'}), ('creatures/nox/stage02', {'idle', 'walk', 'sit', 'look', 'sleep', 'react'})]:
            manifest = json.loads((ROOT / 'public/assets' / directory / 'manifest.json').read_text())
            self.assertEqual(set(manifest['animations']), supplied)
