"""LUMA-ASSET-04: isolated candidates; existing failures and production remain gated."""
import hashlib
import json
import unittest
from test_assets import ROOT
from test_creature_followup import measure

BATCH = ROOT / 'design/production-batches/luma-asset-04'
CASES = (('M001', 'blink'), ('M001', 'cursor_react'), ('M002', 'look'),
         ('M002', 'cursor_react'), ('M003', 'look'), ('M003', 'cursor_react'),
         ('M004', 'blink'), ('M004', 'interact'))


class LumaAsset04Tests(unittest.TestCase):
    def test_frames_match_existing_validator_and_protected_anatomy(self):
        for identity, action in CASES:
            with self.subTest(identity=identity, action=action):
                folder = BATCH / identity / (action + '-pilot')
                spec = json.loads((folder / 'candidate-clip.json').read_text())
                if 'eyes' in spec:
                    def movable(x, y):
                        return any(((x-e['x'])/e['rx'])**2 + ((y-e['y'])/e['ry'])**2 < 1
                                   for e in spec['eyes'])
                else:
                    left, top, right, bottom = spec['movableRect']
                    def movable(x, y):
                        return left < x < right and top < y < bottom
                result = measure(folder, movable)
                self.assertEqual(result, json.loads((folder / 'frame-validation.json').read_text()))
                self.assertEqual(result['detachedAlphaPixels'], 0)
                for frame in result['frames']:
                    self.assertEqual(frame['errors'], [])
                    self.assertEqual(frame['protectedPixelChanges'], 0)
                    self.assertTrue(frame['alphaMatchesBase'])
                    self.assertEqual(frame['anchorDriftPixels'], {'bottom': 0, 'boundsCenterX': 0.0})
                failed = identity == 'M004' and action == 'blink'
                self.assertEqual(result['automated'], 'VALIDATION_FAILED' if failed else 'PASS')
                self.assertEqual(result['uniquePixelHashes'], 5 if failed else spec['clip']['frames'])
                self.assertFalse(spec['runtimeEnabled'])
                self.assertFalse(spec['productionEligible'])
                self.assertEqual(spec['anchor'], {'x': .5, 'y': 1})
                self.assertEqual((spec['repairIterations'], spec['repairLimit']), (3, 3))
                self.assertEqual(hashlib.sha256((ROOT / spec['rigSource']).read_bytes()).hexdigest(),
                                 spec['rigSourceSha256'])

    def test_only_missing_actions_attempted_without_existing_failure_recovery(self):
        queue = json.loads((ROOT / 'design/creature-production-queue.json').read_text())
        rows = {r['creatureId']: r for r in queue['creatures']}
        for identity, action in CASES:
            previous = next(a for a in rows[identity]['actions'] if a['action'] == action.upper())
            self.assertEqual(previous['animationStatus'], 'ASSET_REQUIRED')
            self.assertEqual(previous['frameCount'], 0)
        caplet = rows['M005']
        for name in ('MOVE', 'TURN', 'REST', 'INTERACT', 'HIT', 'VICTORY'):
            previous = next(a for a in caplet['actions'] if a['action'] == name)
            self.assertEqual(previous['animationStatus'], 'VALIDATION_FAILED')
            self.assertTrue((ROOT / previous['recoveryPath']).is_file())
        self.assertFalse((BATCH / 'M005').exists())
        self.assertEqual(queue['repairIterations'], 3)
        self.assertEqual(queue['repairLimit'], 3)

    def test_review_inventory_keeps_failed_clip_blocked_and_has_all_75_decisions(self):
        inspection = json.loads((BATCH / 'inspection.json').read_text())
        self.assertEqual(len(inspection['checks']), 75)
        self.assertEqual(len({(r['conceptId'], r['action']) for r in inspection['checks']}), 75)
        catalog = json.loads((BATCH / 'review-catalog.json').read_text())
        new_clips = [c for r in catalog['creatures'] for c in r['clips']
                     if '/luma-asset-04/' in c['directory']]
        self.assertEqual(len(new_clips), 8)
        self.assertEqual(sum(c['frameCount'] for c in new_clips), 60)
        self.assertEqual(sum(c['automated'] == 'PASS' for c in new_clips), 7)
        failed = [c for c in new_clips if c['automated'] != 'PASS']
        self.assertEqual(len(failed), 1)
        self.assertIn('/M004/blink-pilot/', failed[0]['directory'])
        self.assertIn('DUPLICATE_OR_UNDECODABLE_PIXELS', failed[0]['errors'])
        self.assertTrue(all(not c['runtimeEnabled'] for c in new_clips))
