"""Offline candidate checks using the existing PNG validator and decoder."""
import json
import unittest
from pathlib import Path
from test_moa_blink_v2 import rgba
import test_assets

class Asset05Tests(unittest.TestCase):
    def test_eye_candidates_preserve_anatomy_and_registration(self):
        root=test_assets.ROOT/'design/production-batches/luma-asset-05'
        specs=sorted(p for p in root.glob('M*/*/candidate-clip.json') if p.parent.name in ('look','blink','cursor_react'))
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

    def test_body_candidates_keep_alpha_contact_and_fixed_anatomy(self):
        root=test_assets.ROOT/'design/production-batches/luma-asset-05'
        specs=sorted(p for p in root.glob('M*/*/candidate-clip.json') if p.parent.name in ('hit','recovery','interact'))
        self.assertEqual(len(specs),10)
        for path in specs:
            with self.subTest(clip=str(path)):
                spec=json.loads(path.read_text());base=rgba(test_assets.ROOT/spec['sourceBase'])
                bounds=[];self.assertEqual(test_assets.validator.png_errors(test_assets.ROOT/spec['sourceBase'],True,bounds),[])
                action=spec['clip']['name'].lower();frames=sorted((path.parent/'rigged'/action).glob('*.png'))
                self.assertEqual(len(frames),8);hashes=[];decoded=[]
                for n,f in enumerate(frames):
                    self.assertEqual(f.name,f'{action}_{n:02}.png');b=[]
                    self.assertEqual(test_assets.validator.png_errors(f,True,b,hashes),[]);self.assertEqual(b,bounds)
                    d=rgba(f);decoded.append(d);self.assertEqual(d[3::4],base[3::4])
                    changed=0
                    for y in range(256):
                        for x in range(256):
                            i=(y*256+x)*4
                            if d[i:i+4]!=base[i:i+4]:
                                changed+=1
                                self.assertTrue(any(((x-p['x'])/p['rx'])**2+((y-p['y'])/p['ry'])**2<1 for p in spec['parts']))
                    self.assertGreater(changed,30);self.assertLess(changed,5000)
                self.assertEqual(len(set(hashes)),8)
                # One-shot clips: check successive frames, not a fabricated looping seam.
                for a,b in zip(decoded,decoded[1:]):
                    self.assertNotEqual(a,b)
                    self.assertLess(sum(abs(x-y) for x,y in zip(a,b))/len(a),1)
                self.assertFalse(spec['clip']['loop']);self.assertFalse(spec['runtimeEnabled'])
                self.assertFalse(spec['productionEligible']);self.assertEqual(spec['repairIterations'],3)

    def test_hit_recovery_boundary_and_return_toward_base(self):
        root=test_assets.ROOT/'design/production-batches/luma-asset-05'
        for identity in ('M006','M008','M009','M010'):
            with self.subTest(identity=identity):
                p=root/identity
                spec=json.loads((p/'hit/candidate-clip.json').read_text())
                base=rgba(test_assets.ROOT/spec['sourceBase'])
                hit=rgba(p/'hit/rigged/hit/hit_07.png')
                start=rgba(p/'recovery/rigged/recovery/recovery_00.png')
                end=rgba(p/'recovery/rigged/recovery/recovery_07.png')
                self.assertEqual(hit,start)
                difference=lambda d:sum(abs(a-b) for a,b in zip(d,base))
                self.assertLess(difference(end),difference(start)/5)
