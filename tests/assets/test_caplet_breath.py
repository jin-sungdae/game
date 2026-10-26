import unittest
from test_moa_blink_v2 import rgba
import test_assets

class CapletBreathTests(unittest.TestCase):
    def test_breath_preserves_approved_anatomy_alpha_and_loop(self):
        root=test_assets.ROOT
        source=rgba(root/'design/production-batches/monsters/batch01/M005/base-v2.png')
        frames=sorted((root/'design/production-batches/monsters/caplet-breath/M005/rigged/breath').glob('*.png'))
        self.assertEqual(len(frames),8);hashes=[];decoded=[]
        for f in frames:
            bounds=[];self.assertEqual(test_assets.validator.png_errors(f,True,bounds,hashes),[])
            self.assertEqual(bounds,[54,37,204,219]);data=rgba(f);decoded.append(data)
            self.assertEqual(data[3::4],source[3::4])
            for y in range(256):
                for x in range(256):
                    if y<=146 or y>=202 or x<=120 or x>=153:
                        i=(y*256+x)*4;self.assertEqual(data[i:i+4],source[i:i+4])
        self.assertEqual(len(set(hashes)),8)
        for a,b in zip(decoded,decoded[1:]+decoded[:1]):
            changes=sum(a[i:i+4]!=b[i:i+4] for i in range(0,len(a),4))
            self.assertGreater(changes,0);self.assertLessEqual(changes,500)
        self.assertFalse((root/'public/assets/monsters/caplet/breath').exists())
