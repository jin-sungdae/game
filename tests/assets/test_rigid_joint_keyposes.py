import hashlib
import json
import unittest
from test_assets import ROOT

BATCH = ROOT / 'design/production-batches/action-followup'

class RigidJointKeyposeTests(unittest.TestCase):
    def test_raw_failures_preserve_originals_and_stop_before_rigging(self):
        for code, action, count in [('M071', 'hit', 353), ('M072', 'turn', 1208), ('M073', 'hit', 480)]:
            with self.subTest(code=code):
                folder = BATCH / code / (action + '-pilot')
                report = json.loads((folder / 'keypose-validation.json').read_text())
                source = json.loads((folder / 'source-alpha.json').read_text())
                self.assertEqual(report['status'], 'VALIDATION_FAILED')
                self.assertEqual(report['sourceAlpha'], source)
                self.assertEqual(source['threshold'], 0)
                self.assertEqual(source['detachedPixels'], count)
                self.assertEqual(sum(source['detachedAlphaHistogram'].values()), count)
                self.assertEqual(report['sourceSha256'], hashlib.sha256((folder / 'keypose-tool-reference.png').read_bytes()).hexdigest())
                self.assertFalse(report['normalizationPerformed'])
                self.assertFalse(report['riggingPerformed'])
                self.assertFalse(report['productionEligible'])
                self.assertFalse((folder / 'rigged').exists())
                self.assertFalse((folder / 'keypose.png').exists())
                self.assertFalse((folder / 'candidate-clip.json').exists())

    def test_ledger_preserves_rigid_failures_identity_and_approval_limit(self):
        q = json.loads((ROOT / 'design/creature-production-queue.json').read_text())
        rows = {c['creatureId']: c for c in q['creatures']}
        for code, name in [('M071', 'HIT'), ('M072', 'TURN'), ('M073', 'HIT')]:
            a = next(a for a in rows[code]['actions'] if a['action'] == name)
            self.assertEqual(a['animationStatus'], 'VALIDATION_FAILED')
            self.assertEqual(a['frameCount'], 0)
            self.assertEqual(a['runtimeStatus'], 'BLOCKED')
            self.assertTrue((ROOT / a['recoveryPath']).is_file())
        a = next(a for a in rows['M074']['actions'] if a['action'] == 'INTERACT')
        self.assertIn('Identity review', a['blockReason'])
        self.assertEqual(a['frameCount'], 0)
        self.assertIsNone(rows['M074']['productionSpeciesId'])
        self.assertEqual(q['repairIterations'], 3)
        self.assertEqual(q['repairLimit'], 3)
