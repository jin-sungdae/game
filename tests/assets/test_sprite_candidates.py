import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
import validate_sprite_candidates as v
from test_alpha_assets import rgba_fixture

class SpriteCandidates(unittest.TestCase):
    def prepare(self, root, same=False):
        (root/'idle').mkdir()
        (root/'manifest.json').write_text(json.dumps({'species':'ruu','stage':1,
            'canvas':{'width':256,'height':256},'anchor':{'x':.5,'y':1},'display':{'width':130},
            'animations':{'idle':{'frames':2,'frameDuration':100,'loop':True}}}))
        (root/'idle/idle_00.png').write_bytes(rgba_fixture(128,0))
        (root/'idle/idle_01.png').write_bytes(rgba_fixture(128 if same else 129,4))

    def test_valid_format_and_registration_never_approve_identity_or_gui(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);self.prepare(p);r=v.review(p,'ruu',1)
            self.assertEqual(r['clips']['idle']['status'],'AUTOMATED_CHECKS_PASS_VISUAL_REVIEW_REQUIRED')
            self.assertFalse(r['productionEligible']);self.assertFalse(r['runtimeConnected'])
            self.assertEqual(r['gui'],'DEFERRED_GUI')
            self.assertEqual(r['backgroundResidue'],'MANUAL_REVIEW_REQUIRED')

    def test_reencoded_duplicate_is_not_animation(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);self.prepare(p,True);r=v.review(p,'ruu',1)['clips']['idle']
            self.assertEqual(r['status'],'VALIDATION_FAILED')
            self.assertEqual(r['repeatedPixelGroups'],[[0,1]])

    def test_wrong_stage_and_missing_frame_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);self.prepare(p)
            self.assertEqual(v.review(p,'ruu',2)['clips']['idle']['status'],'VALIDATION_FAILED')
            (p/'idle/idle_01.png').unlink()
            self.assertEqual(v.review(p,'ruu',1)['clips']['idle']['status'],'VALIDATION_FAILED')

    def test_registration_failure_cannot_be_hidden_by_png_pass(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);self.prepare(p)
            with patch.object(v,'candidate',return_value={'errors':['registration drift'],'driftPixels':{'centerX':2,'bottom':1}}):
                self.assertEqual(v.review(p,'ruu',1)['clips']['idle']['status'],'VALIDATION_FAILED')

    def test_missing_manifest_fails(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):v.review(Path(d),'ruu',1)
