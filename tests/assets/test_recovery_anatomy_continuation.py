import hashlib
import json
import unittest
from test_assets import ROOT
from test_creature_new_pose_quality import measure_parts
from test_moa_blink_v2 import rgba
from test_creature_followup import detached_pixels

BATCH = ROOT / 'design/production-batches/action-followup'

class RecoveryAnatomyTests(unittest.TestCase):
    def test_authorized_paths_preserve_failed_originals(self):
        queue = json.loads((ROOT / 'design/creature-production-queue.json').read_text())
        catalog = json.loads((ROOT / 'tests/live/creature-review/catalog.json').read_text())
        for identity, action in [('M039', 'HIT'), ('M042', 'REST')]:
            row = next(a for r in queue['creatures'] if r['creatureId'] == identity for a in r['actions'] if a['action'] == action)
            self.assertEqual(row['recoveryPath'], row['candidatePath'] + '/keypose-tool-reference.png')
            self.assertTrue((ROOT / row['recoveryPath']).is_file())
            self.assertEqual(row['animationStatus'], 'VALIDATION_FAILED')
            report = json.loads((ROOT / row['candidatePath'] / 'keypose-validation.json').read_text())
            self.assertEqual(hashlib.sha256((ROOT / row['recoveryPath']).read_bytes()).hexdigest(), report['sourceSha256'])
            visible = next(a for r in catalog['creatures'] if r['id'] == identity for a in r['actions'] if a['action'] == action)
            self.assertEqual(visible['recoveryPath'], row['recoveryPath'])
        self.assertEqual(queue['repairIterations'], 3)

    def test_raw_failures_never_reach_rigging(self):
        for code, count in [('M043/turn-pilot', 2032), ('M046/rest-pilot', 3942)]:
            folder = BATCH / code
            report = json.loads((folder / 'keypose-validation.json').read_text())
            self.assertEqual(report['sourceAlpha']['detachedPixels'], count)
            self.assertEqual(report['sourceAlpha']['threshold'], 0)
            self.assertEqual(report['sourceSha256'], hashlib.sha256((folder / 'keypose-tool-reference.png').read_bytes()).hexdigest())
            self.assertFalse(report['normalizationPerformed'])
            self.assertFalse(report['riggingPerformed'])
            self.assertFalse((folder / 'keypose.png').exists())
            self.assertFalse((folder / 'rigged').exists())

    def test_existing_moa_base_is_not_repaired(self):
        report = json.loads((BATCH / 'moa/stage03/hit-preflight/keypose-validation.json').read_text())
        base = ROOT / 'public/assets/creatures/moa/stage03/base.png'
        self.assertEqual(hashlib.sha256(base.read_bytes()).hexdigest(), report['sourceSha256'])
        self.assertEqual(detached_pixels(rgba(base)), 44)
        self.assertFalse(report['riggingPerformed'])

    def test_snow_cat_hit_has_real_local_motion_and_fixed_contacts(self):
        folder = BATCH / 'M045/hit-pilot'
        result = measure_parts(folder)
        self.assertEqual(result, json.loads((folder / 'frame-validation.json').read_text()))
        self.assertEqual(result['automated'], 'PASS')
        self.assertEqual(result['uniquePixelHashes'], 8)
        self.assertEqual(result['appearance'], 'HUMAN_REVIEW_REQUIRED')
        self.assertTrue(any(f['silhouetteSupportChangedPixels'] for f in result['frames']))
        self.assertTrue(all(f['protectedPixelChanges'] == 0 for f in result['frames']))
        self.assertFalse(result['productionEligible'])
