import hashlib,json,unittest
from test_assets import ROOT,validator
class MoaIdleV3(unittest.TestCase):
    def test_registered_original_bytes_and_geometry(self):
        m=json.loads((ROOT/'docs/evidence/moa-idle-v3/source-manifest.json').read_text())
        self.assertEqual((m['character'],m['stage'],m['canvas'],m['sourceFacing'],m['anchor']),('MOA',1,[256,256],'RIGHT','bottom-center'))
        self.assertEqual(m['registration'],{'maxCenterXDeltaPx':0,'maxBottomDeltaPx':0,'breath04EqualsBreath01Bytes':True})
        centers=[];bottoms=[]
        self.assertEqual(len(m['frames']),7)
        for frame in m['frames']:
            kind,index=frame['file'].removesuffix('.png').split('_');self.assertIn(kind,['breath','blink'])
            p=ROOT/f'public/assets/creatures/moa/stage01/{kind}/{kind}_{int(index)-1:02}.png';bounds=[]
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),frame['sha256'])
            self.assertEqual(validator.png_errors(p,True,bounds),[])
            actual=[bounds[0],bounds[1],bounds[2]+1,bounds[3]+1]
            self.assertEqual(actual,frame['alpha_bounds']);centers.append((actual[0]+actual[2])/2);bottoms.append(actual[3])
            self.assertEqual(centers[-1],frame['center_x']);self.assertEqual(bottoms[-1],frame['bottom'])
        self.assertEqual(max(centers)-min(centers),0);self.assertEqual(max(bottoms)-min(bottoms),0)
        root=ROOT/'public/assets/creatures/moa/stage01'
        self.assertEqual((root/'breath/breath_00.png').read_bytes(),(root/'breath/breath_03.png').read_bytes())
        self.assertEqual(hashlib.sha256((root/'base.png').read_bytes()).hexdigest(),'3e2f8a31d71bda3005a0a78eb31ac1ac84a146add959034fdcea3f5c1b765743')
