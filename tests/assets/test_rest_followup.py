import json
import unittest
from test_moa_blink_v2 import rgba
import test_assets

class RestFollowupTests(unittest.TestCase):
    def test_new_candidates_keep_anatomy_alpha_anchor_and_distinct_frames(self):
        root=test_assets.ROOT/'design/production-batches'
        cases=[('breath-followup/M019','monsters/batch02/M019','breath',8,lambda x,y:not(y<=156 or y>=204 or x<=108 or x>=184)),('breath-followup/M020','monsters/batch02/M020','breath',8,lambda x,y:not(y<=107 or y>=190 or x<=86 or x>=190)),('breath-followup/M017','monsters/batch02/M017','breath',8,lambda x,y:not(y<=146 or y>=191 or x<=107 or x>=194)),('breath-followup/M018','monsters/batch02/M018','breath',8,lambda x,y:not(y<=134 or y>=183 or x<=121 or x>=196)),('breath-followup/M015','monsters/batch02/M015','breath',8,lambda x,y:not(y<=120 or y>=199 or x<=110 or x>=207)),('breath-followup/M016','monsters/batch02/M016','breath',8,lambda x,y:not(y<=139 or y>=197 or x<=103 or x>=192)),('breath-followup/M013','monsters/batch02/M013','breath',8,lambda x,y:not(y<=143 or y>=198 or x<=90 or x>=185)),('breath-followup/M014','monsters/batch02/M014','breath',8,lambda x,y:not(y<=111 or y>=169 or x<=123 or x>=193)),('breath-followup/M012','monsters/batch02/M012','breath',8,lambda x,y:not(y<=131 or y>=191 or x<=124 or x>=208)),('breath-followup/M011','monsters/batch02/M011','breath',8,lambda x,y:not(y<=145 or y>=200 or x<=113 or x>=197))]
        for destination,source,action,count,movable in cases:
            with self.subTest(creature=destination):
                base=rgba(root/source/'base-v2.png');bounds=[];self.assertEqual(test_assets.validator.png_errors(root/source/'base-v2.png',True,bounds),[])
                p=root/destination;frames=sorted((p/'rigged'/action).glob('*.png'));self.assertEqual(len(frames),count)
                hashes=[];decoded=[]
                for n,f in enumerate(frames):
                    self.assertEqual(f.name,f'{action}_{n:02}.png');b=[]
                    self.assertEqual(test_assets.validator.png_errors(f,True,b,hashes),[]);self.assertEqual(b,bounds)
                    data=rgba(f);decoded.append(data);self.assertEqual(data[3::4],base[3::4])
                    for y in range(256):
                        for x in range(256):
                            if not movable(x,y):
                                i=(y*256+x)*4;self.assertEqual(data[i:i+4],base[i:i+4])
                self.assertEqual(len(set(hashes)),count)
                for a,b in zip(decoded,decoded[1:]+decoded[:1]):self.assertNotEqual(a,b)
                spec=json.loads((p/'candidate-clip.json').read_text());self.assertFalse(spec['runtimeEnabled']);self.assertFalse(spec['productionEligible'])
                if action=='look':self.assertEqual(rgba(p/'keypose.png'),decoded[3])
        self.assertFalse((test_assets.ROOT/'public/assets/monsters/caplet/look').exists())

    def test_failed_rest_recovery_is_preserved_and_never_registered(self):
        root=test_assets.ROOT
        folder=root/'design/production-batches/monsters/rest-pilot/M005'
        validation=json.loads((folder/'keypose-recovery-v3.validation.json').read_text())
        self.assertEqual(validation['detachedPixels'],1)
        self.assertFalse(validation['productionEligible'])
        self.assertTrue((folder/'keypose.png').is_file())
        self.assertTrue((folder/'keypose-recovery-v3-tool.png').is_file())
        spec=json.loads((folder/'candidate-clip.json').read_text())
        self.assertEqual(spec['recoveryStatus'],'BLOCKED_HUMAN_REVIEW_REQUIRED')
        self.assertEqual(spec['repairIterations'],3)
        self.assertEqual(spec['clip']['frames'],0)
        self.assertFalse(spec['runtimeEnabled'])
        manifest=json.loads((root/'public/assets/monsters/caplet/manifest.json').read_text())
        self.assertNotIn('rest',manifest['animations'])
