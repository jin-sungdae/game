import importlib.util
import json
import unittest
from test_assets import ROOT

spec = importlib.util.spec_from_file_location('pr131_boundaries', ROOT / 'scripts/analysis/pr131_clip_boundaries.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class Pr131ClipBoundaries(unittest.TestCase):
    def test_hidden_rgb_is_reported_but_not_visible_motion(self):
        a, b = bytes([255, 0, 80, 0]), bytes([0, 255, 0, 0])
        result = audit.pixel_difference(a, b)
        self.assertGreater(result['rawRgbaAbsoluteDifference'], 0)
        self.assertEqual(result['visibleChangedPixels'], 0)
        self.assertEqual(audit.visible_hash(a), audit.visible_hash(b))

    def test_alpha_only_change_is_visible_on_white(self):
        result = audit.pixel_difference(bytes([0, 0, 0, 255]), bytes([0, 0, 0, 0]))
        self.assertEqual(result['maxCompositeDifference'], 255)
        self.assertEqual(result['maxAlphaDifference'], 255)
        self.assertEqual(result['visibleChangedPixels'], 1)

    def test_opaque_shift_and_invalid_buffers(self):
        result = audit.pixel_difference(bytes([10, 20, 30, 255]), bytes([11, 40, 35, 255]))
        self.assertEqual(result['maxCompositeDifference'], 20)
        self.assertEqual(result['rawRgbaAbsoluteDifference'], 26)
        for a, b in [(b'', b''), (b'abc', b'abc'), (b'1234', b'12345678')]:
            with self.assertRaises(ValueError):
                audit.pixel_difference(a, b)

    def test_saved_measurements_preserve_all_four_unapproved_clips(self):
        result = audit.report()
        saved = json.loads((ROOT / 'design/production-batches/pr131-continuation/boundary-validation.json').read_text())
        self.assertEqual(result, saved)
        self.assertEqual(len(result['clips']), 4)
        for clip in result['clips']:
            self.assertEqual(clip['existingValidatorStatus'], 'PASS')
            self.assertEqual(len(clip['frameSha256']), 8)
            self.assertEqual(clip['uniqueVisibleHashes'], 8)
            self.assertEqual(len(clip['adjacent']), 7)
            self.assertFalse(clip['productionApproved'])
            self.assertFalse(clip['runtimeEnabled'])
            self.assertEqual(clip['naturalMotion'], 'HUMAN_REVIEW_REQUIRED')
