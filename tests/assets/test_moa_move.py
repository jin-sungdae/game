import hashlib,json,unittest
from test_assets import ROOT,validator
class MoaMove(unittest.TestCase):
    def test_approved_move_original_bytes_registration_and_timing(self):
        m=json.loads((ROOT/'docs/evidence/moa-move-v1/source-manifest.json').read_text());root=ROOT/'public/assets/creatures/moa/stage01'
        self.assertEqual((m['character'],m['stage'],m['canvas'],m['source_facing'],m['anchor'],m['frame_count']),('MOA',1,[256,256],'RIGHT','bottom-center',8))
        self.assertEqual((m['candidate_frame_ms'],m['cycle_ms']),(80,640));centers=[];bottoms=[]
        self.assertEqual(len(m['frames']),8)
        for i,f in enumerate(m['frames']):
            self.assertEqual(f['file'],f'move_{i+1:02}.png');p=root/f'walk/walk_{i:02}.png';b=[]
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),f['sha256']);self.assertEqual(validator.png_errors(p,True,b),[])
            self.assertEqual([b[0],b[1],b[2]+1,b[3]+1],f['alpha_bounds']);centers.append((b[0]+b[2]+1)/2);bottoms.append(b[3]+1)
            self.assertEqual(centers[-1],f['center_x']);self.assertEqual(bottoms[-1],f['bottom'])
        self.assertEqual(max(centers)-min(centers),0);self.assertEqual(max(bottoms)-min(bottoms),0)
        c=json.loads((root/'manifest.json').read_text())['animations']['walk'];self.assertEqual(c,{'frames':8,'frameDuration':80,'loop':True})
