import hashlib
import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
CANDIDATES = ROOT/'design/production-candidates-v1'

class SpriteAlignmentRecovery(unittest.TestCase):
    def test_lossless_translation_and_clipping_guards(self):
        result = subprocess.run(['node', '--test', 'tests/assets/sprite_alignment.test.cjs'],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)

    def test_original_evidence_preserved_and_no_clip_approved(self):
        directory = CANDIDATES/'ruu/stage01/recovery-v1'
        report = json.loads((directory/'measurements.json').read_text())
        self.assertEqual(len(report['frames']), 16)
        self.assertEqual(report['productionRegisteredClips'], 0)
        self.assertFalse(report['productionEligible'])
        for frame in report['frames']:
            source = CANDIDATES/frame['source']
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), frame['sourceSha256'])
            self.assertEqual(frame['alphaPixelCountBefore'], frame['alphaPixelCountAfter'])
        for revision in ('v1', 'v2'):
            validation = json.loads((directory/revision/'validation.json').read_text())
            self.assertEqual(validation['clips']['idle']['status'], 'VALIDATION_FAILED')
            self.assertTrue(all(c['automated']=='FAIL' for c in validation['baseComparisons']))
            self.assertFalse(validation['runtimeConnected'])
