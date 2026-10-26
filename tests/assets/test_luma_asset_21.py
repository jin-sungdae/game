import json
import unittest
from test_assets import ROOT
from test_creature_new_pose_quality import measure_parts


class Asset21Tests(unittest.TestCase):
    def test_isolated_candidates_preserve_anatomy_and_registration(self):
        root = ROOT / 'design/production-batches/LUMA-ASSET-21'
        for relative in ('M089/interact', 'M090/cursor_react'):
            with self.subTest(candidate=relative):
                folder = root / relative
                result = measure_parts(folder)
                self.assertEqual(result, json.loads((folder / 'frame-validation.json').read_text()))
                self.assertEqual(result['automated'], 'PASS')
                self.assertEqual(result['uniquePixelHashes'], 8)
                spec = json.loads((folder / 'candidate-clip.json').read_text())
                self.assertFalse(spec['runtimeEnabled'])
                self.assertFalse(spec['productionEligible'])
                self.assertFalse(spec['clip']['loop'])
