import json
import unittest
from test_moa_blink_v2 import rgba
import test_assets

class BreathFollowupTests(unittest.TestCase):
    def test_species_specific_rigs_keep_source_alpha_anchor_and_fixed_anatomy(self):
        root=test_assets.ROOT/'design/production-batches'
        cases=[('M001','monsters/batch01/M001',(165,207,87,181)),('M002','monsters/batch01/M002',(137,180,104,185)),('moa/stage04','moa/stage04',(112,188,105,198))]
        for creature,source_path,mask in cases:
            with self.subTest(creature=creature):
                source=rgba(root/source_path/'base-v2.png');directory=root/'breath-followup'/creature
                frames=sorted((directory/'rigged/breath').glob('*.png'));hashes=[];decoded=[]
                self.assertEqual(len(frames),8)
                source_bounds=[];test_assets.validator.png_errors(root/source_path/'base-v2.png',True,source_bounds,[])
                for frame in frames:
                    bounds=[];self.assertEqual(test_assets.validator.png_errors(frame,True,bounds,hashes),[])
                    self.assertEqual(bounds,source_bounds)
                    data=rgba(frame);decoded.append(data);self.assertEqual(data[3::4],source[3::4])
                    lo,hi,left,right=mask
                    for y in range(256):
                        for x in range(256):
                            if y<=lo or y>=hi or x<=left or x>=right:
                                n=(y*256+x)*4;self.assertEqual(data[n:n+4],source[n:n+4])
                self.assertEqual(len(set(hashes)),8)
                for a,b in zip(decoded,decoded[1:]+decoded[:1]):self.assertNotEqual(a,b)
                contract=json.loads((directory/'candidate-clip.json').read_text())
                self.assertFalse(contract['productionEligible']);self.assertFalse(contract['runtimeEnabled'])
