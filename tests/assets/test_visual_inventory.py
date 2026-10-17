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

if __name__=='__main__': unittest.main()
