"""HIT candidates reuse existing anatomy; fixed contacts and recovery remain measurable."""
import hashlib
import json
import unittest
from test_assets import ROOT
from test_creature_followup import measure
from test_luma_asset_04_continuation import movable_for
from test_moa_blink_v2 import rgba

BATCH = ROOT / 'design/production-batches/luma-asset-04'
IDS = ('M001', 'M002', 'M003', 'M004')


def movable(spec):
    return movable_for(dict(spec, clip={'name': 'REST'}))


def recovery(folder):
    spec = json.loads((folder / 'candidate-clip.json').read_text())
    base = rgba(ROOT / spec['sourceBase'])
    frames = [rgba(p) for p in sorted((folder / 'rigged/hit').glob('*.png'))]
    deltas = [sum(abs(a-b) for a, b in zip(frame, base)) for frame in frames]
    passed = deltas[0] / max(deltas) < .05 and deltas[-1] / max(deltas) < .05
    return {'automated': 'PASS' if passed else 'VALIDATION_FAILED',
            'threshold': .05,
            'basePixelDifferenceSums': deltas,
            'entryToPeakRatio': deltas[0] / max(deltas),
            'exitToPeakRatio': deltas[-1] / max(deltas),
            'exactBaseReturn': frames[-1] == base,
            'appearance': 'HUMAN_REVIEW_REQUIRED', 'nativeGui': 'DEFERRED_GUI'}


class LumaAsset04HitTests(unittest.TestCase):
    def test_png_anatomy_contact_hash_and_recovery(self):
        for identity in IDS:
            with self.subTest(identity=identity):
                folder = BATCH / identity / 'hit-pilot'
                spec = json.loads((folder / 'candidate-clip.json').read_text())
                result = measure(folder, movable(spec))
                self.assertEqual(result, json.loads((folder / 'frame-validation.json').read_text()))
                self.assertEqual(result['automated'], 'PASS')
                self.assertEqual(result['uniquePixelHashes'], 8)
                r = recovery(folder)
                self.assertEqual(r, json.loads((folder / 'recovery-validation.json').read_text()))
                if identity == 'M002':
                    self.assertEqual(r['automated'], 'VALIDATION_FAILED')
                    self.assertGreaterEqual(r['entryToPeakRatio'], .05)
                    self.assertGreaterEqual(r['exitToPeakRatio'], .05)
                    self.assertEqual(spec['status'], 'VALIDATION_FAILED')
                    self.assertIn('BASE_RETURN_RESIDUAL', spec['blockReason'])
                else:
                    self.assertEqual(r['automated'], 'PASS')
                    self.assertLess(r['entryToPeakRatio'], .05)
                    self.assertLess(r['exitToPeakRatio'], .05)
                self.assertTrue(all(a > b for a, b in zip(r['basePixelDifferenceSums'][3:-1], r['basePixelDifferenceSums'][4:])))
                self.assertFalse(spec['clip']['loop'])
                self.assertFalse(spec['runtimeEnabled'])
                self.assertFalse(spec['productionEligible'])
                self.assertEqual((spec['repairIterations'], spec['repairLimit']), (3, 3))

    def test_rig_geometry_is_reused_and_response_is_not_breathing(self):
        for identity in IDS:
            folder = BATCH / identity / 'hit-pilot'
            spec = json.loads((folder / 'candidate-clip.json').read_text())
            rest = json.loads((BATCH / identity / 'rest-pilot/candidate-clip.json').read_text())
            rig = json.loads((folder / 'rig-evidence.json').read_text())
            self.assertEqual(spec['eyes'], rest['eyes'])
            self.assertEqual(rig['protectedRegions'], rest['fixedBodyExpression'])
            for part, original in zip(spec['parts'], rest['parts']):
                self.assertEqual({k:part[k] for k in ('x','y','rx','ry')}, {k:original[k] for k in ('x','y','rx','ry')})
            self.assertLess(spec['parts'][0]['dx'], 0)
            self.assertGreater(spec['parts'][1]['dx'], 0)
            self.assertEqual(spec['parts'][0]['samples'].index(1), 1)
            self.assertEqual(spec['parts'][1]['samples'].index(1), 3)
            self.assertEqual(hashlib.sha256((ROOT / spec['rigSource']).read_bytes()).hexdigest(), spec['rigSourceSha256'])
            self.assertTrue(all(f['fixedRegionChanges'] == 0 for f in rig['frames']))
            self.assertGreater(max(f['maxInverseDisplacementPixels'] for f in rig['frames']), 1)

    def test_no_previous_hit_or_caplet_repair(self):
        queue = json.loads((ROOT / 'design/creature-production-queue.json').read_text())
        for row in queue['creatures']:
            if row['creatureId'] in IDS:
                hit = next(a for a in row['actions'] if a['action'] == 'HIT')
                self.assertEqual(hit['frameCount'], 0)
                self.assertEqual(hit['animationStatus'], 'ASSET_REQUIRED')
        self.assertFalse((BATCH / 'M005').exists())

    def test_review_catalog_retains_recovery_failure(self):
        catalog = json.loads((BATCH / 'hit-review-catalog.json').read_text())
        hits = [clip for row in catalog['creatures'] for clip in row['clips']
                if '/luma-asset-04/' in clip['directory'] and '/hit-pilot/' in clip['directory']]
        self.assertEqual(len(hits), 4)
        self.assertEqual(sum(c['automated'] == 'PASS' for c in hits), 3)
        failed = next(c for c in hits if '/M002/' in c['directory'])
        self.assertEqual(failed['automated'], 'VALIDATION_FAILED')
        self.assertTrue(any('BASE_RETURN_RESIDUAL' in e for e in failed['errors']))
