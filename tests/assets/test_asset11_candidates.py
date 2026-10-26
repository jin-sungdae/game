import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SESSION = ROOT / 'design/production-batches/LUMA-ASSET-11'
spec = importlib.util.spec_from_file_location('asset11', SESSION / 'validate-session.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)

class Asset11Candidates(unittest.TestCase):
    def test_frames_are_remeasured_and_failures_remain_failures(self):
        for action, expected in [('breath', 'PASS'), ('look', 'PASS'), ('blink', 'VALIDATION_FAILED')]:
            with self.subTest(action=action):
                folder = SESSION / 'M036' / action
                actual = validator.measure(folder)
                self.assertEqual(actual, json.loads((folder / 'frame-validation.json').read_text()))
                self.assertEqual(actual['automated'], expected)
                self.assertFalse(actual['productionEligible'])
                self.assertFalse(actual['repairPerformed'])
                self.assertEqual(actual['repairIterations'], 3)

    def test_all_requested_actions_and_blocked_raw_sources_are_preserved(self):
        report = json.loads((SESSION / 'integration-request.json').read_text())
        self.assertEqual(len(report['monsters']), 5)
        for row in report['monsters']:
            self.assertEqual(len(row['actions']), 21)
            self.assertFalse(row['productionApproved'])
            self.assertFalse(row['runtimeConnected'])
        failures = list(SESSION.glob('M*/*/keypose-validation.json'))
        self.assertEqual(len(failures), 40)
        for path in failures:
            entry = json.loads(path.read_text())
            self.assertEqual(entry['status'], 'VALIDATION_FAILED')
            self.assertFalse(entry['normalizationPerformed'])
            self.assertFalse(entry['riggingPerformed'])
            self.assertTrue((path.parent / 'keypose-tool-reference.png').is_file())
            self.assertFalse((path.parent / 'rigged').exists())
