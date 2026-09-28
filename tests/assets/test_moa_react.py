import hashlib,json,unittest
from test_assets import ROOT,validator
class MoaReact(unittest.TestCase):
    def test_original_bytes_registration_and_nonlooping_contract(self):
        m=json.loads((ROOT/'docs/evidence/moa-react-v1/source-manifest.json').read_text());root=ROOT/'public/assets/creatures/moa/stage01'
        self.assertEqual((m['character'],m['canvas'],m['source_facing'],m['anchor']),('MOA',[256,256],'RIGHT','bottom-center'))
        self.assertEqual((m['frame_count'],m['frame_ms'],m['cycle_ms']),(6,80,480));centers=[];bottoms=[]
        self.assertEqual(hashlib.sha256((root/'base.png').read_bytes()).hexdigest(),'3e2f8a31d71bda3005a0a78eb31ac1ac84a146add959034fdcea3f5c1b765743')
        for i,f in enumerate(m['frames']):
            self.assertEqual(f['file'],f'react_{i+1:02}.png');p=root/f'react/react_{i:02}.png';bounds=[]
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),f['sha256']);self.assertEqual(validator.png_errors(p,True,bounds),[])
            centers.append((bounds[0]+bounds[2]+1)/2);bottoms.append(bounds[3]+1)
            self.assertEqual(centers[-1],f['center_x']);self.assertEqual(bottoms[-1],f['bottom'])
        self.assertEqual(max(centers)-min(centers),0);self.assertEqual(max(bottoms)-min(bottoms),0)
        self.assertEqual((root/'react/react_00.png').read_bytes(),(root/'react/react_05.png').read_bytes())
        self.assertEqual(json.loads((root/'manifest.json').read_text())['animations']['react'],{'frames':6,'frameDuration':80,'loop':False})
