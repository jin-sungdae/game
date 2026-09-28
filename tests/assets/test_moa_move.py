import hashlib,json,unittest
from test_assets import ROOT,validator
class MoaMove(unittest.TestCase):
    def test_approved_move_original_bytes_registration_and_timing(self):
        m=json.loads((ROOT/'docs/evidence/moa-move-v2/source-manifest.json').read_text());root=ROOT/'public/assets/creatures/moa/stage01'
        self.assertEqual((m['character'],m['canvas'],m['source_facing'],m['anchor'],m['frames']),('MOA',[256,256],'RIGHT','bottom-center',8))
        self.assertEqual(hashlib.sha256((root/'base.png').read_bytes()).hexdigest(),m['source_sha256'])
        self.assertEqual((m['frame_ms'],m['frame_ms']*m['frames']),(80,640));centers=[];bottoms=[]
        self.assertEqual(len(m['frame_data']),8)
        for i,f in enumerate(m['frame_data']):
            self.assertEqual(f['file'],f'move_{i+1:02}.png');p=root/f'walk/walk_{i:02}.png';b=[]
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),f['sha256']);self.assertEqual(validator.png_errors(p,True,b),[])
            centers.append((b[0]+b[2]+1)/2);bottoms.append(b[3]+1)
            self.assertEqual(centers[-1],f['center_x']);self.assertEqual(bottoms[-1],f['bottom'])
        self.assertEqual(max(centers)-min(centers),0);self.assertEqual(max(bottoms)-min(bottoms),0)
        c=json.loads((root/'manifest.json').read_text())['animations']['walk'];self.assertEqual(c,{'frames':8,'frameDuration':80,'loop':True})

    def test_v2_has_actual_visible_paw_and_body_variation(self):
        from test_moa_blink_v2 import rgba
        root=ROOT/'public/assets/creatures/moa/stage01'
        data=[rgba(root/f'walk/walk_{i:02}.png') for i in range(8)]
        self.assertGreater(len(set(data)),1)
        for x0,y0,x1,y1 in [(166,229,207,245),(96,225,126,240),(136,190,152,219)]:
            counts=[]
            for a,b in zip(data,data[1:]+data[:1]):
                counts.append(sum(a[j:j+3]!=b[j:j+3] for y in range(y0,y1+1) for x in range(x0,x1+1) for j in [(y*256+x)*4] if a[j+3] or b[j+3]))
            self.assertTrue(any(count>0 for count in counts),counts)
