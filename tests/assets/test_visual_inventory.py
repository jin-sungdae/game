import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import visual_asset_inventory as v

class VisualInventory(unittest.TestCase):
    def test_reference_is_not_gui_acceptance(self):
        base=ROOT/'public/assets/creatures/moa/stage02/base.png'
        r=v.candidate(base,base)
        self.assertEqual(r['automated'],'PASS')
        self.assertEqual(r['driftPixels'],{'centerX':0.,'bottom':0})
        self.assertEqual(r['guiAcceptance'],'NOT_VERIFIED')
        self.assertFalse(r['productionEligible'])

    def test_missing_or_corrupt_does_not_become_artwork(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'missing.png'
            self.assertEqual(v.inspect_png(p)['status'],'NOT_SUPPLIED')
            p.write_bytes(b'not a PNG')
            self.assertTrue(v.inspect_png(p)['errors'])
            self.assertEqual(v.inspect_png(p)['status'],'NOT_SUPPLIED')

    def test_manifest_without_png_is_not_frames_ready(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/'manifest.json').write_text(json.dumps({'animations':{'idle':{'frames':4}}}))
            clip=v.clips(p)['idle']
            self.assertEqual(clip['status'],'NOT_SUPPLIED')
            self.assertEqual(clip['validFrames'],0)
            self.assertEqual(len(clip['missingOrInvalid']),4)

    def test_bad_count_and_path_fail_closed(self):
        for clip in [{'frames':0},{'frames':257},{'frames':True},{'frames':4,'filePrefix':'../other'},{'frames':4,'firstFrame':-1}]:
            with tempfile.TemporaryDirectory() as d:
                p=Path(d)
                (p/'manifest.json').write_text(json.dumps({'animations':{'idle':clip}}))
                with self.assertRaises(ValueError): v.clips(p)

    def test_drift_is_failure_even_when_png_format_valid(self):
        with patch.object(v,'inspect_png',side_effect=[{'errors':[],'bounds':[10,20,100,200]}, {'errors':[],'bounds':[11,20,101,201]}]):
            r=v.candidate(Path('a'),Path('b'))
            self.assertEqual(r['automated'],'FAIL')
            self.assertEqual(r['driftPixels'],{'centerX':-1.,'bottom':-1})

    def test_inventory_covers_all_forms_and_preserves_activation(self):
        # Inventory aggregation test: decoding is independently exercised above and existing PNG tests.
        with patch.object(v,'inspect_png',return_value={'status':'NOT_SUPPLIED','errors':['test']}), patch.object(v,'clips',return_value={}):
            r=v.inventory(ROOT)
        self.assertEqual(len(r['companions']),15)
        self.assertEqual(len(r['monsters']),30)
        self.assertEqual(sum(x['enabled'] for x in r['monsters']),15)
        self.assertEqual(r['guiAcceptance'],'NOT_VERIFIED')
        self.assertTrue(all(len(x['requiredAnimations'])==9 for x in r['companions']))

    def frame_delivery(self, directory, second_alpha=129, second_filter=0):
        from test_alpha_assets import rgba_fixture
        manifest={'species':'moa','stage':1,'canvas':{'width':256,'height':256},
                  'anchor':{'x':.5,'y':1},'display':{'width':130},
                  'animations':{'idle':{'frames':2,'frameDuration':100,'loop':True}}}
        (directory/'manifest.json').write_text(json.dumps(manifest))
        (directory/'idle').mkdir()
        (directory/'idle/idle_00.png').write_bytes(rgba_fixture(128,0))
        (directory/'idle/idle_01.png').write_bytes(rgba_fixture(second_alpha,second_filter))
        return manifest

    def test_same_pixels_with_different_png_filters_are_not_animation(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);self.frame_delivery(p,128,4)
            result=v.clips(p,('moa',1))['idle']
            self.assertEqual(result['status'],'NOT_SUPPLIED')
            self.assertIn('identical decoded frames are not animation',result['errors'])
            a,b=result['frameEvidence']
            self.assertNotEqual(a['sha256'],b['sha256'])
            self.assertEqual(a['pixelSha256'],b['pixelSha256'])

    def test_valid_delivery_has_frame_evidence_but_no_production_or_gui_approval(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);self.frame_delivery(p)
            available=v.clips(p,('moa',1))
            self.assertEqual(available['idle']['status'],'FRAMES_READY')
            self.assertEqual(len(available['idle']['frameEvidence']),2)
            contract=v.delivery_contract('moa',1,available)
            self.assertEqual(contract['actions']['IDLE']['status'],'FRAMES_READY')
            self.assertEqual(contract['actions']['TURN']['status'],'ASSET_REQUIRED')
            self.assertEqual(contract['actions']['IDLE']['runtimeConnection'],'NOT_VERIFIED')
            self.assertFalse(contract['productionEligible'])
            self.assertEqual(contract['guiAcceptance'],'DEFERRED_GUI')

    def test_wrong_identity_canvas_anchor_and_timing_cannot_be_ready(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);original=self.frame_delivery(p)
            for key,value in [('species','ruu'),('stage',2),('canvas',{'width':128,'height':256}),
                              ('anchor',{'x':0,'y':0}),('display',{'width':True})]:
                m=dict(original);m[key]=value
                (p/'manifest.json').write_text(json.dumps(m))
                self.assertEqual(v.clips(p,('moa',1))['idle']['status'],'NOT_SUPPLIED',key)
            for timing in [0,True,float('inf')]:
                original['animations']['idle']['frameDuration']=timing
                (p/'manifest.json').write_text(json.dumps(original))
                self.assertEqual(v.clips(p,('moa',1))['idle']['status'],'NOT_SUPPLIED')

    def test_all_fifteen_delivery_contracts_keep_missing_counts_unknown(self):
        for species in ('moa','ruu','nox'):
            for stage in range(1,6):
                c=v.delivery_contract(species,stage,{})
                self.assertEqual(c['manifestPath'],f'public/assets/creatures/{species}/stage{stage:02}/manifest.json')
                self.assertEqual(set(c['actions']),{'IDLE','MOVE','TURN','INTERACT'})
                self.assertTrue(all(a['status']=='ASSET_REQUIRED' and a['frames'] is None for a in c['actions'].values()))

if __name__=='__main__': unittest.main()
