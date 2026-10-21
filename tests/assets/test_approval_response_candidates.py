import hashlib
import json
import struct
import unittest

from test_assets import ROOT, validator
from test_creature_new_pose_quality import measure_parts

BATCH = ROOT / 'design/production-batches/action-followup'
CASES = {'M023 INTERACT': 'M023/interact-pilot',
         'companion:ruu:5 CURSOR_REACT': 'ruu/stage05/cursor-react-pilot',
         'M024 HIT': 'M024/hit-pilot'}


class ApprovalResponseTests(unittest.TestCase):
    def test_new_parts_preserve_anchor_and_anatomy_without_global_transform(self):
        signatures = set()
        for identity, code in CASES.items():
            with self.subTest(identity=identity):
                folder = BATCH / code
                spec = json.loads((folder / 'candidate-clip.json').read_text())
                result = measure_parts(folder)
                self.assertEqual(result, json.loads((folder / 'frame-validation.json').read_text()))
                self.assertEqual(result['automated'], 'PASS')
                self.assertEqual(result['uniquePixelHashes'], 8)
                self.assertEqual(result['appearance'], 'HUMAN_REVIEW_REQUIRED')
                self.assertEqual(result['naturalMotion'], 'HUMAN_REVIEW_REQUIRED')
                self.assertTrue(all(result['adjacentPixelDifferenceSumsIncludingLoop']))
                self.assertFalse(spec['clip']['loop'])
                self.assertFalse(spec['productionEligible'])
                self.assertFalse(spec['runtimeEnabled'])
                for frame in result['frames']:
                    self.assertEqual(frame['errors'], [])
                    self.assertEqual(frame['protectedPixelChanges'], 0)
                    self.assertEqual(frame['detachedAlphaPixels'], 0)
                    self.assertEqual(frame['anchorDriftPixels'], {'bottom': 0, 'boundsCenterX': 0})
                self.assertTrue(any(f['silhouetteSupportChangedPixels'] > 0 for f in result['frames']))
                signatures.add(json.dumps(spec['parts'], sort_keys=True))
        self.assertEqual(len(signatures), len(CASES))

    def test_source_alpha_failure_stops_before_normalization_and_rigging(self):
        folder = BATCH / 'M025/turn-pilot'
        raw = folder / 'keypose-tool-reference.png'
        report = json.loads((folder / 'keypose-validation.json').read_text())
        source = json.loads((folder / 'source-alpha.json').read_text())
        generation = json.loads((folder / 'generation.json').read_text())
        self.assertEqual(hashlib.sha256(raw.read_bytes()).hexdigest(), generation['rawSha256'])
        self.assertEqual(report['sourceSha256'], generation['rawSha256'])
        self.assertEqual(struct.unpack('>II', raw.read_bytes()[16:24]), (source['width'], source['height']))
        self.assertEqual(report['pngErrors'], validator.png_errors(raw, True))
        self.assertIn('dimensions must be 256x256', report['pngErrors'])
        self.assertEqual(source['threshold'], 0)
        self.assertEqual(source['detachedPixels'], 7557)
        self.assertEqual(sum(source['detachedAlphaHistogram'].values()), source['detachedPixels'])
        self.assertEqual(report['sourceAlpha'], source)
        self.assertEqual(report['status'], 'VALIDATION_FAILED')
        self.assertFalse(report['normalizationPerformed'])
        self.assertFalse(report['riggingPerformed'])
        self.assertFalse(report['productionEligible'])
        self.assertFalse((folder / 'keypose.png').exists())
        self.assertFalse((folder / 'rigged').exists())

    def test_approval_audit_covers_every_candidate_and_never_infers_approval(self):
        queue = json.loads((ROOT / 'design/creature-production-queue.json').read_text())
        catalog = json.loads((ROOT / 'tests/live/creature-review/catalog.json').read_text())
        audit = queue['approvalBottleneckContinuation']['approvalAudit']
        expected = {c['directory']: (r, c) for r in catalog['creatures'] for c in r['clips']}
        self.assertEqual({e['directory'] for e in audit['clips']}, set(expected))
        self.assertEqual(len(audit['clips']), len(expected))
        for entry in audit['clips']:
            row, clip = expected[entry['directory']]
            self.assertEqual(entry['automatedPng'], clip['automated'])
            action = next(a for a in row['actions'] if a['action'] == clip['action'].upper())
            self.assertEqual(entry['productionApproval'], 'USER_APPROVED' if action.get('artworkReview') == 'USER_APPROVED' else 'NOT_APPROVED')
            self.assertEqual(entry['runtimeStatus'], action['runtimeStatus'])
            self.assertEqual(entry['identityReviewRequired'], row['id'].startswith('M') and not row.get('productionSpeciesId'))
        self.assertEqual(audit['approvedUnconnected'], [])
        self.assertEqual(audit['summary']['productionApprovedClips'], 1)
        self.assertEqual(audit['summary']['guiPassedClips'], 0)
        approved = [e for e in audit['clips'] if e['productionApproval'] == 'USER_APPROVED']
        self.assertEqual([(e['creatureId'], e['action']) for e in approved], [('M005', 'SLEEP')])
        self.assertTrue(approved[0]['productionFramesMatch'])
        self.assertEqual(queue['repairIterations'], 3)

    def test_ledger_keeps_candidate_and_production_progress_separate(self):
        queue = json.loads((ROOT / 'design/creature-production-queue.json').read_text())
        run = queue['approvalBottleneckContinuation']
        self.assertEqual(run['newCases'], CASES)
        self.assertEqual(run['candidateFrames'], 24)
        self.assertEqual(run['candidatePng'], 28)
        self.assertEqual(run['productionRegistrations'], 0)
        self.assertEqual(run['runtimeConnections'], 0)
        paths = list(CASES.values()) + ['M025/turn-pilot']
        self.assertEqual(sum(len(list((BATCH / p).rglob('*.png'))) for p in paths), 28)
        for identity_action in CASES:
            identity, action = identity_action.split()
            item = next(a for r in queue['creatures'] if r['creatureId'] == identity for a in r['actions'] if a['action'] == action)
            self.assertEqual(item['artworkReview'], 'HUMAN_REVIEW_REQUIRED')
            self.assertEqual(item['runtimeStatus'], 'BLOCKED')
        caplet = next(r for r in queue['creatures'] if r['creatureId'] == 'M005')
        self.assertFalse(caplet['spawn']['enabled'])
