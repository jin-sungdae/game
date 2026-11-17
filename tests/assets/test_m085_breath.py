import hashlib
import json
import unittest

from test_assets import ROOT, validator
from test_moa_blink_v2 import rgba


CANDIDATE = ROOT / 'design/production-batches/luma-asset-20/M085/breath'


class M085BreathTests(unittest.TestCase):
    def test_breath_cycle_preserves_base_and_differs_from_idle(self):
        spec = json.loads((CANDIDATE / 'candidate-clip.json').read_text(encoding='utf-8'))
        evidence = json.loads((CANDIDATE / 'rig-evidence.json').read_text(encoding='utf-8'))
        base = rgba(ROOT / spec['sourceBase'])
        idle = {hashlib.sha256(rgba(path)).hexdigest()
                for path in (CANDIDATE.parent / 'idle/rigged/idle').glob('*.png')}
        hashes = []
        frames = []
        for index, record in enumerate(evidence['frames']):
            path = CANDIDATE / 'rigged/breath' / f'breath_{index:02}.png'
            self.assertEqual(validator.png_errors(path, True), [])
            frame = rgba(path)
            frames.append(frame)
            self.assertEqual(frame[3::4], base[3::4])
            self.assertEqual(frame[:137*256*4], base[:137*256*4])
            self.assertEqual(frame[168*256*4:], base[168*256*4:])
            digest = hashlib.sha256(frame).hexdigest()
            self.assertEqual(digest, record['pixelSha256'])
            self.assertNotIn(digest, idle)
            hashes.append(digest)
        self.assertEqual(len(set(hashes)), 8)
        self.assertEqual(len(idle), 8)
        self.assertEqual(frames[0], base)
        for index, before in enumerate(frames):
            after = frames[(index + 1) % len(frames)]
            channel_delta = sum(abs(a-b) for a,b in zip(before, after))
            self.assertGreater(channel_delta, 0)
            self.assertLess(channel_delta / (256*256*3), 2)
        self.assertFalse(spec['runtimeEnabled'])
        self.assertFalse(spec['productionEligible'])
