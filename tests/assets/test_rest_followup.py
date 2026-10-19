import json
import unittest
from test_moa_blink_v2 import rgba
import test_assets

class RestFollowupTests(unittest.TestCase):
    def test_new_candidates_keep_anatomy_alpha_anchor_and_distinct_frames(self):
        root=test_assets.ROOT/'design/production-batches'
        cases=[('breath-followup/M012','monsters/batch02/M012','breath',8,lambda x,y:not(y<=131 or y>=191 or x<=124 or x>=208)),('breath-followup/M011','monsters/batch02/M011','breath',8,lambda x,y:not(y<=145 or y>=200 or x<=113 or x>=197))]
        for destination,source,action,count,movable in cases:
            with self.subTest(creature=destination):
                base=rgba(root/source/'base-v2.png');bounds=[];self.assertEqual(test_assets.validator.png_errors(root/source/'base-v2.png',True,bounds),[])
                p=root/destination;frames=sorted((p/'rigged'/action).glob('*.png'));self.assertEqual(len(frames),count)
                hashes=[];decoded=[]
                for n,f in enumerate(frames):
                    self.assertEqual(f.name,f'{action}_{n:02}.png');b=[]
                    self.assertEqual(test_assets.validator.png_errors(f,True,b,hashes),[]);self.assertEqual(b,bounds)
                    data=rgba(f);decoded.append(data);self.assertEqual(data[3::4],base[3::4])
                    for y in range(256):
                        for x in range(256):
                            if not movable(x,y):
                                i=(y*256+x)*4;self.assertEqual(data[i:i+4],base[i:i+4])
                self.assertEqual(len(set(hashes)),count)
                for a,b in zip(decoded,decoded[1:]+decoded[:1]):self.assertNotEqual(a,b)
                spec=json.loads((p/'candidate-clip.json').read_text());self.assertFalse(spec['runtimeEnabled']);self.assertFalse(spec['productionEligible'])
                if action=='look':self.assertEqual(rgba(p/'keypose.png'),decoded[3])
        self.assertFalse((test_assets.ROOT/'public/assets/monsters/caplet/look').exists())
