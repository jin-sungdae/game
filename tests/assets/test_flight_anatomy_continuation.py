import hashlib
import json
import struct
import unittest

from test_assets import ROOT, validator
from test_creature_new_pose_quality import measure_parts

BATCH = ROOT / 'design/production-batches/action-followup'
CASES = {'M027 HIT': 'M027/hit-pilot', 'M029 CURSOR_REACT': 'M029/cursor-react-pilot',
         'companion:nox:2 CURSOR_REACT': 'nox/stage02/cursor-react-pilot'}


class FlightAnatomyContinuationTests(unittest.TestCase):
    def test_local_parts_change_silhouette_without_moving_anchor_or_fixed_anatomy(self):
        signatures = set()
        for identity, code in CASES.items():
            with self.subTest(identity=identity):
                folder = BATCH / code
                spec = json.loads((folder / 'candidate-clip.json').read_text())
                measured = measure_parts(folder)
                self.assertEqual(measured, json.loads((folder / 'frame-validation.json').read_text()))
                self.assertEqual(measured['automated'], 'PASS')
                self.assertEqual(measured['uniquePixelHashes'], 8)
                self.assertTrue(all(measured['adjacentPixelDifferenceSumsIncludingLoop']))
                for frame in measured['frames']:
                    self.assertEqual(frame['errors'], [])
                    self.assertEqual(frame['detachedAlphaPixels'], 0)
                    self.assertEqual(frame['protectedPixelChanges'], 0)
                    self.assertEqual(frame['canvasEdgePixels'], 0)
                    self.assertEqual(frame['anchorDriftPixels'], {'bottom': 0, 'boundsCenterX': 0})
                self.assertTrue(any(f['silhouetteSupportChangedPixels'] for f in measured['frames']))
                self.assertEqual(measured['appearance'], 'HUMAN_REVIEW_REQUIRED')
                self.assertEqual(measured['naturalMotion'], 'HUMAN_REVIEW_REQUIRED')
                self.assertFalse(spec['productionEligible'])
                self.assertFalse(spec['runtimeEnabled'])
                self.assertFalse(spec['clip']['loop'])
                signatures.add(json.dumps(spec['parts'], sort_keys=True))
        self.assertEqual(len(signatures), 3)

    def test_raw_alpha_failure_is_preserved_before_any_normalization(self):
        folder = BATCH / 'M028/move-pilot'
        raw = folder / 'keypose-tool-reference.png'
        source = json.loads((folder / 'source-alpha.json').read_text())
        generation = json.loads((folder / 'generation.json').read_text())
        report = json.loads((folder / 'keypose-validation.json').read_text())
        self.assertEqual(hashlib.sha256(raw.read_bytes()).hexdigest(), generation['rawSha256'])
        self.assertEqual(report['sourceSha256'], generation['rawSha256'])
        self.assertEqual(struct.unpack('>II', raw.read_bytes()[16:24]), (source['width'], source['height']))
        self.assertEqual(report['sourceAlpha'], source)
        self.assertEqual(source['threshold'], 0)
        self.assertEqual(source['detachedPixels'], 842)
        self.assertEqual(source['detachedAlphaHistogram'], {'1': 839, '2': 3})
        self.assertEqual(report['pngErrors'], validator.png_errors(raw, True))
        self.assertEqual(report['status'], 'VALIDATION_FAILED')
        self.assertFalse(report['normalizationPerformed'])
        self.assertFalse(report['riggingPerformed'])
        self.assertFalse((folder / 'keypose.png').exists())
        self.assertFalse((folder / 'rigged').exists())

    def test_wingless_identity_is_blocked_without_inventing_flight_anatomy(self):
        queue = json.loads((ROOT / 'design/creature-production-queue.json').read_text())
        blocked = queue['flightAnatomyContinuation']['identityBlocked'][0]
        provenance = json.loads((ROOT / blocked['provenance']).read_text())
        self.assertEqual(provenance['prompts']['M026']['subject'], 'spectral violet wolf')
        self.assertEqual(hashlib.sha256((ROOT / blocked['sourceBase']).read_bytes()).hexdigest(), blocked['sourceSha256'])
        self.assertEqual(blocked['generatedPng'], 0)
        self.assertFalse((BATCH / 'M026/move-pilot').exists())
        row = next(x for x in queue['creatures'] if x['creatureId'] == 'M026')
        action = next(a for a in row['actions'] if a['action'] == 'MOVE')
        self.assertEqual(action['animationStatus'], 'ASSET_REQUIRED')
        self.assertEqual(action['frameCount'], 0)
        self.assertIn('WINGLESS_BASE_VS_FLIGHT_REQUEST', action['blockReason'])
        self.assertIsNone(row['productionSpeciesId'])

    def test_counts_and_review_evidence_do_not_promote_candidates(self):
        queue = json.loads((ROOT / 'design/creature-production-queue.json').read_text())
        catalog = json.loads((ROOT / 'tests/live/creature-review/catalog.json').read_text())
        run = queue['flightAnatomyContinuation']
        self.assertEqual(run['newCases'], CASES)
        self.assertEqual(run['candidateFrames'], 24)
        self.assertEqual(run['candidatePng'], 28)
        paths = list(CASES.values()) + ['M028/move-pilot']
        self.assertEqual(sum(len(list((BATCH / p).rglob('*.png'))) for p in paths), 28)
        self.assertEqual(queue['repairIterations'], 3)
        self.assertEqual(run['repairIterations'], 3)
        self.assertEqual(run['productionRegistrations'], 0)
        self.assertEqual(run['runtimeConnections'], 0)
        self.assertEqual(run['approvedUnconnectedAssets'], [])
        audit = queue['approvalBottleneckContinuation']['approvalAudit']
        clips = [c for r in catalog['creatures'] for c in r['clips']]
        self.assertEqual(audit['summary']['candidateClips'], len(clips))
        self.assertEqual(audit['summary']['candidateFrames'], sum(c['frameCount'] for c in clips))
        for key in CASES:
            identity, name = key.split()
            entries = [c for c in audit['clips'] if c['creatureId'] == identity and c['action'] == name]
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]['productionApproval'], 'NOT_APPROVED')
            self.assertEqual(entries[0]['naturalMotion'], 'HUMAN_REVIEW_REQUIRED')
            self.assertEqual(entries[0]['runtimeStatus'], 'BLOCKED')
        self.assertEqual(audit['summary']['productionApprovedClips'], 1)
        self.assertEqual(audit['summary']['approvedRuntimePendingClips'], 0)
        self.assertEqual(audit['summary']['guiPassedClips'], 0)
