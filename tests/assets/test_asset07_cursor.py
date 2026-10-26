"""Independent cursor cues; existing failures and approval boundaries stay intact."""
import json
import unittest
from test_action_production_continuation import measured
from test_assets import ROOT
from test_moa_blink_v2 import rgba

BATCH = ROOT / 'design/production-batches/asset07'


class Asset07Cursor(unittest.TestCase):
    def test_cursor_pixels_and_return_evidence(self):
        for n in range(16, 21):
            with self.subTest(monster=n):
                folder = BATCH / f'M{n:03}' / 'cursor-react'
                spec = json.loads((folder / 'candidate-clip.json').read_text())
                report = measured(folder)
                self.assertEqual(report, json.loads((folder / 'frame-validation.json').read_text()))
                self.assertEqual(report['automated'], 'PASS')
                self.assertEqual(report['uniquePixelHashes'], 8)
                base = rgba(ROOT / spec['sourceBase'])
                frames = [rgba(p) for p in sorted((folder / 'rigged/cursor_react').glob('*.png'))]
                distances = [sum(abs(a-b) for a,b in zip(base,f)) for f in frames]
                self.assertLess(distances[-1], distances[3])
                self.assertLess(distances[0], distances[3])
                self.assertTrue(all(a >= b for a,b in zip(distances[3:], distances[4:])))
                self.assertFalse(spec['clip']['loop'])
                self.assertFalse(spec['runtimeEnabled'])
                self.assertEqual(spec['repairIterations'], 3)
                for frame in report['frames']:
                    self.assertEqual(frame['protectedPixelChanges'], 0)
                    self.assertTrue(frame['alphaMatchesBase'])
                # An initial/terminal near-base frame is not claimed to be an exact base.
                self.assertEqual(spec['naturalMotion'], 'NOT_VERIFIED')
