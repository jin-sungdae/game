import json
import unittest
from pathlib import Path
import test_assets

class RuuMatureTests(unittest.TestCase):
    def test_delivered_clips_keep_identity_anchor_and_unique_pixels(self):
        for stage,bounds in [(4,[23,28,237,218]),(5,[21,21,231,229])]:
            root=test_assets.ROOT/f'public/assets/creatures/ruu/stage{stage:02}'
            m=json.loads((root/'manifest.json').read_text())
            self.assertEqual((m['species'],m['stage']),('ruu',stage))
            self.assertEqual(m['anchor'],{'x':.5,'y':1})
            self.assertEqual(set(m['animations']),set(test_assets.validator.COUNTS))
            files=sorted((root/'idle').glob('*.png'));self.assertEqual(len(files),6)
            hashes=[]
            for f in files:
                actual=[]
                self.assertEqual(test_assets.validator.png_errors(f,True,actual,hashes),[])
                self.assertEqual(actual,bounds)
            self.assertEqual(len(set(hashes)),6)
            for action in set(m['animations'])-{'idle'}:
                self.assertEqual(list((root/action).glob('*.png')),[])

    def test_rig_evidence_preserves_fixed_anatomy(self):
        for stage in (4,5):
            p=test_assets.ROOT/f'design/production-batches/ruu/stage{stage:02}'
            data=json.loads((p/'rig-evidence.json').read_text())
            self.assertFalse(data['wholeImageTransform'])
            self.assertEqual(len(data['frames']),6)
            for row in data['frames']:
                self.assertEqual(row['fixedRegionChanges'],0)
                self.assertGreater(row['changedPixels'],0)
                self.assertLess(row['maxInverseDisplacementPixels'],2)
