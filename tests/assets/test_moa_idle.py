import hashlib,json,unittest
from test_assets import ROOT,validator
class MoaIdleDelivery(unittest.TestCase):
    def test_approved_six_unchanged_with_documented_zero_based_mapping(self):
        manifest=json.loads((ROOT/'docs/evidence/moa-idle/source-manifest.json').read_text())
        self.assertEqual((manifest['character'],manifest['stage'],manifest['animation'],manifest['frame_count'],manifest['source_facing'],manifest['anchor']),('MOA',1,'IDLE',6,'RIGHT','bottom-center'))
        self.assertEqual(len(manifest['frames']),6)
        for index,frame in enumerate(manifest['frames']):
            self.assertEqual(frame['file'],f'idle_{index+1:02}.png')
            path=ROOT/f'public/assets/creatures/moa/stage01/idle/idle_{index:02}.png';bounds=[]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),frame['sha256'])
            self.assertEqual(validator.png_errors(path,True,bounds),[])
            self.assertEqual([bounds[0],bounds[1],bounds[2]+1,bounds[3]+1],frame['alpha_bounds'])
            self.assertEqual((frame['size'],frame['mode']),([256,256],'RGBA'))
        self.assertEqual(hashlib.sha256((ROOT/'public/assets/creatures/moa/stage01/base.png').read_bytes()).hexdigest(),'3e2f8a31d71bda3005a0a78eb31ac1ac84a146add959034fdcea3f5c1b765743')
