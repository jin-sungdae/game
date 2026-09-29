import hashlib,json,shutil,tempfile,unittest
from pathlib import Path
from test_assets import ROOT,validator
class PipAnimation(unittest.TestCase):
    def test_delivered_bytes_and_registration(self):
        m=json.loads((ROOT/'docs/evidence/pip-animation-v1/source-manifest.json').read_text());self.assertEqual((m['character'],m['canvas'],m['source_facing'],m['anchor']),('PIP',[256,256],'RIGHT','bottom-center'));self.assertEqual(len(m['frames']),18)
        centers=[];bottoms=[]
        for f in m['frames']:
            folder,name=f['file'].split('/');clip={'idle':'idle','move':'walk','react':'react'}[folder];i=int(name[-6:-4])-1;p=ROOT/f'public/assets/monsters/pip/{clip}/{clip}_{i:02}.png';b=[]
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),f['sha256']);self.assertEqual(validator.png_errors(p,True,b),[]);centers.append((b[0]+b[2]+1)/2);bottoms.append(b[3]+1);self.assertEqual(centers[-1],f['center_x']);self.assertEqual(bottoms[-1],f['bottom'])
        self.assertEqual(max(centers)-min(centers),0);self.assertEqual(max(bottoms)-min(bottoms),0)
        self.assertEqual(validator.validate_pip_animation(ROOT),( [], [] ))
    def test_partial_wrong_filename_and_invalid_png_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p=root/'public/assets/monsters/pip';shutil.copytree(ROOT/'public/assets/monsters/pip',p)
            frame=p/'walk/walk_03.png';original=frame.read_bytes();frame.unlink();self.assertTrue(validator.validate_pip_animation(root,True)[0]);frame.write_bytes(original)
            frame.rename(p/'walk/Walk_03.png');self.assertTrue(validator.validate_pip_animation(root,True)[0]);(p/'walk/Walk_03.png').rename(frame)
            frame.write_bytes(b'not PNG');self.assertTrue(validator.validate_pip_animation(root,True)[0])
