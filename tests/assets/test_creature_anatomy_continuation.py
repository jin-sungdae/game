import hashlib
import json
import struct
import unittest

from test_assets import ROOT, validator
from test_creature_new_pose_quality import measure_parts

BATCH = ROOT / 'design/production-batches/action-followup'
CASES = {'companion:moa:4 CURSOR_REACT': 'moa/stage04/cursor-react-pilot',
         'M031 HIT': 'M031/hit-pilot', 'M032 INTERACT': 'M032/interact-pilot'}
FAILED = {'M030 ATTACK': ('M030/attack-pilot', 2582),
          'M032 TURN': ('M032/turn-pilot', 1515)}


class CreatureAnatomyContinuationTests(unittest.TestCase):
    def test_local_reactions_keep_anchor_and_protected_anatomy(self):
        signatures = set()
        for identity, code in CASES.items():
            with self.subTest(identity=identity):
                folder = BATCH / code
                spec = json.loads((folder / 'candidate-clip.json').read_text())
                result = measure_parts(folder)
                self.assertEqual(result, json.loads((folder / 'frame-validation.json').read_text()))
                self.assertEqual(result['automated'], 'PASS')
                self.assertEqual(result['uniquePixelHashes'], 8)
                self.assertTrue(all(result['adjacentPixelDifferenceSumsIncludingLoop']))
                self.assertTrue(any(f['silhouetteSupportChangedPixels'] for f in result['frames']))
                for frame in result['frames']:
                    self.assertEqual(frame['errors'], [])
                    self.assertEqual(frame['detachedAlphaPixels'], 0)
                    self.assertEqual(frame['protectedPixelChanges'], 0)
                    self.assertEqual(frame['canvasEdgePixels'], 0)
                    self.assertEqual(frame['anchorDriftPixels'], {'bottom': 0, 'boundsCenterX': 0})
                self.assertEqual(result['appearance'], 'HUMAN_REVIEW_REQUIRED')
                self.assertEqual(result['naturalMotion'], 'HUMAN_REVIEW_REQUIRED')
                self.assertFalse(spec['productionEligible'])
                self.assertFalse(spec['runtimeEnabled'])
                self.assertFalse(spec['clip']['loop'])
                signatures.add(json.dumps(spec['parts'], sort_keys=True))
        self.assertEqual(len(signatures), len(CASES))

    def test_raw_keypose_failure_stops_before_resize_and_rigging(self):
        for identity, (code, expected) in FAILED.items():
            with self.subTest(identity=identity):
                folder = BATCH / code
                raw = folder / 'keypose-tool-reference.png'
                source = json.loads((folder / 'source-alpha.json').read_text())
                generation = json.loads((folder / 'generation.json').read_text())
                report = json.loads((folder / 'keypose-validation.json').read_text())
                self.assertEqual(hashlib.sha256(raw.read_bytes()).hexdigest(), generation['rawSha256'])
                self.assertEqual(report['sourceSha256'], generation['rawSha256'])
                self.assertEqual(struct.unpack('>II', raw.read_bytes()[16:24]), (source['width'], source['height']))
                self.assertEqual(report['sourceAlpha'], source)
                self.assertEqual(source['threshold'], 0)
                self.assertEqual(source['detachedPixels'], expected)
                self.assertEqual(sum(source['detachedAlphaHistogram'].values()), expected)
                self.assertEqual(report['pngErrors'], validator.png_errors(raw, True))
                self.assertEqual(report['status'], 'VALIDATION_FAILED')
                self.assertFalse(report['normalizationPerformed'])
                self.assertFalse(report['riggingPerformed'])
                self.assertFalse((folder / 'keypose.png').exists())
                self.assertFalse((folder / 'rigged').exists())

    def test_anatomy_preflight_does_not_invent_identity_or_movement_policy(self):
        queue = json.loads((ROOT / 'design/creature-production-queue.json').read_text())
        paths = list(CASES.values()) + [v[0] for v in FAILED.values()]
        for code in paths:
            pre = json.loads((BATCH / code / 'anatomy-preflight.json').read_text())
            row = next(r for r in queue['creatures'] if r['creatureId'] == pre['creatureId'])
            self.assertEqual(hashlib.sha256((ROOT / pre['sourceBase']).read_bytes()).hexdigest(), pre['sourceSha256'])
            self.assertEqual(pre['movementProfile'], row['movementProfile'])
            self.assertFalse(pre['movementProfile']['runtimeApproved'])
            self.assertFalse(pre['duplicateActionFound'])
            self.assertFalse(pre['newBodyParts'])
            self.assertFalse(pre['policyChanged'])
            self.assertEqual(pre['artworkReview'], 'HUMAN_REVIEW_REQUIRED')
            if row['creatureId'].startswith('M'):
                self.assertIsNone(pre['productionSpeciesId'])
                self.assertIsNone(pre['manifest'])
        moa = json.loads((BATCH / CASES['companion:moa:4 CURSOR_REACT'] / 'anatomy-preflight.json').read_text())
        self.assertEqual(moa['manifest'], 'public/assets/creatures/moa/stage04/manifest.json')
        self.assertFalse((ROOT / 'public/assets/creatures/moa/stage04/cursor_react').exists())
        self.assertEqual(queue['flightAnatomyContinuation']['identityBlocked'][0]['creatureId'], 'M026')

    def test_inventory_audit_and_ledger_keep_approvals_separate(self):
        queue = json.loads((ROOT / 'design/creature-production-queue.json').read_text())
        run = queue['creatureAnatomyContinuation']
        self.assertEqual(run['newCases'], CASES)
        self.assertEqual(run['candidateFrames'], 24)
        self.assertEqual(run['candidatePng'], 29)
        paths = list(CASES.values()) + [v[0] for v in FAILED.values()]
        self.assertEqual(sum(len(list((BATCH / p).rglob('*.png'))) for p in paths), 29)
        self.assertEqual(queue['repairIterations'], 3)
        self.assertEqual(run['repairIterations'], 3)
        self.assertEqual(run['productionRegistrations'], 0)
        self.assertEqual(run['runtimeConnections'], 0)
        self.assertEqual(run['approvedUnconnectedAssets'], [])
        for identity in list(CASES) + list(FAILED):
            creature, name = identity.split()
            row = next(r for r in queue['creatures'] if r['creatureId'] == creature)
            action = next(a for a in row['actions'] if a['action'] == name)
            self.assertEqual(action['runtimeStatus'], 'BLOCKED')
            self.assertEqual(action['artworkReview'], 'HUMAN_REVIEW_REQUIRED')
        audit = queue['approvalBottleneckContinuation']['approvalAudit']
        self.assertEqual(audit['summary']['productionApprovedClips'], 1)
        self.assertEqual(audit['summary']['approvedRuntimePendingClips'], 0)
        self.assertEqual(audit['summary']['guiPassedClips'], 0)
        catalog = json.loads((ROOT / 'tests/live/creature-review/catalog.json').read_text())
        self.assertEqual(audit['summary']['candidateClips'], sum(len(r['clips']) for r in catalog['creatures']))
        self.assertTrue(queue['nextTask'])
