import hashlib
import json
import unittest
from test_moa_blink_v2 import rgba
import test_assets

ROOT = test_assets.ROOT
FOLDER = ROOT/'design/production-batches/monsters/idle-revision/M005'

def components(data):
    left = {i for i in range(256*256) if data[i*4+3]}
    sizes = []
    while left:
        todo = [left.pop()]; size = 0
        while todo:
            i = todo.pop(); size += 1; x,y = i%256,i//256
            for dx in (-1,0,1):
                for dy in (-1,0,1):
                    xx,yy = x+dx,y+dy; j = yy*256+xx
                    if 0 <= xx < 256 and 0 <= yy < 256 and j in left:
                        left.remove(j); todo.append(j)
        sizes.append(size)
    return sorted(sizes, reverse=True)

class CapletIdleRevisionTests(unittest.TestCase):
    def test_cleanup_is_exactly_authorized_seventeen_alpha_pixels(self):
        before, after = rgba(FOLDER/'keypose-v2-256.png'), rgba(FOLDER/'keypose-clean.png')
        changed = [i for i in range(len(before)) if before[i] != after[i]]
        self.assertEqual(len(changed),17)
        for i in changed:
            self.assertEqual(i%4,3); self.assertEqual(before[i],1); self.assertEqual(after[i],0)
        self.assertEqual(len(components(after)),1)
        self.assertEqual(components(after),components(rgba(FOLDER/'keypose.png')))

    def test_complete_unique_clip_keeps_fixed_anatomy_anchor_alpha_and_loop(self):
        source = rgba(FOLDER/'keypose.png'); hashes=[]; decoded=[]
        frames=sorted((FOLDER/'rigged/idle').glob('*.png'))
        self.assertEqual(len(frames),6)
        for frame in frames:
            bounds=[]
            self.assertEqual(test_assets.validator.png_errors(frame,True,bounds,hashes),[])
            self.assertEqual(bounds,[50,33,208,219])
            data=rgba(frame); decoded.append(data)
            self.assertEqual(data[3::4],source[3::4])
            for y in range(256):
                for x in range(256):
                    if y<=158 or y>=202 or x<=124 or x>=151:
                        i=(y*256+x)*4
                        self.assertEqual(data[i:i+4],source[i:i+4])
            self.assertEqual(components(data),components(source))
        self.assertEqual(len(set(hashes)),6)
        for a,b in zip(decoded,decoded[1:]+decoded[:1]):
            changed=sum(a[i:i+4]!=b[i:i+4] for i in range(0,len(a),4))
            self.assertGreater(changed,0); self.assertLessEqual(changed,300)

    def test_original_base_sleep_and_registration_are_preserved(self):
        base=ROOT/'design/production-batches/monsters/batch01/M005/base-v2.png'
        self.assertEqual(hashlib.sha256(base.read_bytes()).hexdigest(),'c48e0d3f3ba31e5abdf91260544740921fbe1e20790128378f7f8aa2908a6927')
        public=ROOT/'public/assets/monsters/caplet'
        self.assertEqual((public/'base.png').read_bytes(),base.read_bytes())
        for frame in (ROOT/'design/production-batches/monsters/sleep-pilot/M005/rigged/sleep').glob('*.png'):
            self.assertEqual(frame.read_bytes(),(public/'sleep'/frame.name).read_bytes())
        self.assertFalse((public/'idle').exists())
        m=json.loads((FOLDER/'candidate-clip.json').read_text())
        self.assertEqual(m['designDirection'],'APPROVED')
        self.assertFalse(m['productionEligible']); self.assertFalse(m['runtimeEnabled'])
