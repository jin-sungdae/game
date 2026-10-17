import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import test_assets

validator = test_assets.validator
ROOT = test_assets.ROOT

class RuuStage3Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/'src/entities').mkdir(parents=True)
        self.registry = self.root/'src/entities/companions.json'
        self.registry.write_text(json.dumps({'ruu': {'stages': {'3':'/assets/creatures/ruu/stage03/manifest.json'}}}))
        self.stage = self.root/'public/assets/creatures/ruu/stage03'
        shutil.copytree(ROOT/'public/assets/creatures/ruu/stage03', self.stage)
        self.manifest = self.stage/'manifest.json'

    def errors(self):
        with patch.object(validator, 'validate_pip_animation', return_value=([], [])):
            return validator.validate(self.root)[0]

    def test_real_partial_delivery_and_anchor_bounds(self):
        self.assertEqual(self.errors(), [])
        hashes = []
        for file in sorted((self.stage/'idle').glob('*.png')):
            bounds = []
            self.assertEqual(validator.png_errors(file, True, bounds, hashes), [])
            self.assertEqual(bounds, [17, 25, 238, 228])
        self.assertEqual(len(set(hashes)), 8)
        self.assertEqual(json.loads(self.manifest.read_text())['anchor'], {'x':.5,'y':1})

    def test_missing_and_duplicate_frames_fail_closed(self):
        final = self.stage/'idle/idle_07.png'
        final.unlink()
        self.assertTrue(any('missing frame' in error for error in self.errors()))
        shutil.copy2(self.stage/'idle/idle_00.png', final)
        self.assertTrue(any('duplicate decoded' in error for error in self.errors()))

    def test_partial_contract_cannot_authorize_other_stages_or_actions(self):
        data = json.loads(self.manifest.read_text())
        data['animations']['walk'] = {'frames':8,'frameDuration':80,'loop':True}
        self.manifest.write_text(json.dumps(data))
        self.assertTrue(any('required animation keys mismatch' in error for error in self.errors()))
        del data['animations']['walk']
        data['stage'] = 2
        self.manifest.write_text(json.dumps(data))
        self.registry.write_text(json.dumps({'ruu':{'stages':{'2':'/assets/creatures/ruu/stage03/manifest.json'}}}))
        self.assertTrue(any('required animation keys mismatch' in error for error in self.errors()))

    def test_wrong_count_anchor_and_empty_alpha_rejected(self):
        original = json.loads(self.manifest.read_text())
        for field in ['count','anchor']:
            data = json.loads(json.dumps(original))
            if field == 'count': data['animations']['idle']['frames'] = 7
            else: data['anchor']['y'] = .9
            self.manifest.write_text(json.dumps(data))
            self.assertTrue(self.errors())
        self.manifest.write_text(json.dumps(original))
        (self.stage/'idle/idle_07.png').write_bytes(test_assets.png())
        self.assertTrue(any('empty alpha content' in error for error in self.errors()))
