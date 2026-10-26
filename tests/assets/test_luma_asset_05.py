"""Offline candidate checks using the existing PNG validator and decoder."""
import json
import unittest
from pathlib import Path
from test_moa_blink_v2 import rgba
import test_assets

class Asset05Tests(unittest.TestCase):
    def test_eye_candidates_preserve_anatomy_and_registration(self):
        root=test_assets.ROOT/'design/production-batches/luma-asset-05'
        specs=sorted(root.glob('M*/*/candidate-clip.json'))
        self.assertEqual(len(specs),8)
        for path in specs:
            with self.subTest(clip=str(path)):
                spec=json.loads(path.read_text());base=rgba(test_assets.ROOT/spec['sourceBase'])
                bounds=[];self.assertEqual(test_assets.validator.png_errors(test_assets.ROOT/spec['sourceBase'],True,bounds),[])
                action=spec['clip']['name'].lower();frames=sorted((path.parent/'rigged'/action).glob('*.png'))
                self.assertEqual(len(frames),spec['clip']['frames'])
                hashes=[];decoded=[]
                for n,f in enumerate(frames):
                    self.assertEqual(f.name,f'{action}_{n:02}.png');b=[]
                    self.assertEqual(test_assets.validator.png_errors(f,True,b,hashes),[]);self.assertEqual(b,bounds)
                    data=rgba(f);decoded.append(data);self.assertEqual(data[3::4],base[3::4])
                    for y in range(256):
                        for x in range(256):
                            movable=any(((x-e['x'])/e['rx'])**2+((y-e['y'])/e['ry'])**2<1 for e in spec['eyes'])
                            if not movable:
                                i=(y*256+x)*4;self.assertEqual(data[i:i+4],base[i:i+4])
                self.assertEqual(len(set(hashes)),len(frames))
                for a,b in zip(decoded,decoded[1:]+decoded[:1]):
                    self.assertNotEqual(a,b)
                    self.assertLess(sum(abs(x-y) for x,y in zip(a,b))/len(a),1)
                self.assertFalse(spec['runtimeEnabled']);self.assertFalse(spec['productionEligible'])
                self.assertEqual(spec['repairIterations'],3)
