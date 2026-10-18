import json
import unittest
from PIL import Image
import test_assets

class CapletSleepTests(unittest.TestCase):
    def test_complete_unique_fixed_anchor_clip(self):
        folder=test_assets.ROOT/'design/production-batches/monsters/sleep-pilot/M005'
        frames=sorted((folder/'rigged/sleep').glob('*.png'))
        self.assertEqual(len(frames),6)
        source=list(Image.open(folder/'base-v2.png').getdata())
        hashes=[]; decoded=[]
        for frame in frames:
            bounds=[]
            self.assertEqual(test_assets.validator.png_errors(frame,True,bounds,hashes),[])
            self.assertEqual(bounds,[59,62,204,214])
            data=list(Image.open(frame).getdata());decoded.append(data)
            for i,(before,after) in enumerate(zip(source,data)):
                x,y=i%256,i//256
                if y<=168 or y>=201 or x<=120 or x>=154:
                    self.assertEqual(before,after)
            # Interior-only deformation cannot introduce detached alpha outside the body.
            self.assertEqual([v[3] for v in source],[v[3] for v in data])
        self.assertEqual(len(set(hashes)),6)
        for a,b in zip(decoded,decoded[1:]+decoded[:1]):
            changed=sum(x!=y for x,y in zip(a,b))
            self.assertGreater(changed,0)
            self.assertLessEqual(changed,300)
        public=test_assets.ROOT/'public/assets/monsters/caplet'
        for frame in frames:
            self.assertEqual(frame.read_bytes(),(public/'sleep'/frame.name).read_bytes())
        self.assertEqual((public/'base.png').read_bytes(),(test_assets.ROOT/'design/production-batches/monsters/batch01/M005/base-v2.png').read_bytes())
