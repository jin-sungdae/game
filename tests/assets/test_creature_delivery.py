import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import validate_creature_delivery as v
from test_alpha_assets import rgba_fixture

class CreatureDelivery(unittest.TestCase):
    def put(self,root,identity='NOX_S1',relative='companions/nox/stage_1/base.png',sha=None):
        p=root/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(rgba_fixture(128))
        row={'identity':identity,'path':relative,'sha256':sha or hashlib.sha256(p.read_bytes()).hexdigest()}
        (root/'manifest.json').write_text(json.dumps({'files':[row]}));return row

    def test_png_success_does_not_approve_identity_clip_or_incomplete_delivery(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);self.put(p);r=v.audit(p)
            self.assertEqual(r['files'][0]['pngErrors'],[])
            self.assertEqual(len(r['missingIdentities']),114)
            self.assertEqual(r['productionAcceptedPngs'],0)
            self.assertIsNone(r['files'][0]['runtimeIdentity'])
            self.assertEqual(r['status'],'VALIDATION_FAILED')

    def test_digest_and_identity_path_mismatch_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);self.put(p,identity='MOA_S1',sha='bad');r=v.audit(p)
            self.assertIn('handoff SHA-256 mismatch',r['files'][0]['pngErrors'])
            self.assertIn('identity/path mismatch: MOA_S1',r['errors'])

    def test_escape_rejected_before_reading_outside_file(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'manifest.json').write_text(json.dumps({'files':[{'identity':'M001','path':'../outside.png'}]}))
            with self.assertRaises(ValueError):v.audit(p)

    def test_duplicate_decoded_pixels_and_identities_are_not_new_species(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);row=self.put(p);(p/'manifest.json').write_text(json.dumps({'files':[row,row]}));r=v.audit(p)
            self.assertEqual(r['duplicatePixelGroups'],[['NOX_S1','NOX_S1']])
            self.assertIn('duplicate decoded pixels across identities',r['errors'])
