import hashlib
import json
import unittest
from test_assets import ROOT, validator
from test_creature_new_pose_quality import measure_parts
from test_moa_blink_v2 import rgba
from test_creature_followup import detached_pixels

BATCH = ROOT / 'design/production-batches/action-followup'


class ProductionIntegrationContinuationTests(unittest.TestCase):
    def test_stag_hit_preserves_support_and_moves_local_silhouette(self):
        folder = BATCH / 'M041/hit-pilot'
        result = measure_parts(folder)
        self.assertEqual(result, json.loads((folder / 'frame-validation.json').read_text()))
        self.assertEqual(result['automated'], 'PASS')
        self.assertEqual(result['uniquePixelHashes'], 8)
        self.assertTrue(all(result['adjacentPixelDifferenceSumsIncludingLoop']))
        self.assertTrue(any(f['silhouetteSupportChangedPixels'] for f in result['frames']))
        for f in result['frames']:
            self.assertEqual(f['errors'], [])
            self.assertEqual(f['protectedPixelChanges'], 0)
            self.assertEqual(f['detachedAlphaPixels'], 0)
            self.assertEqual(f['anchorDriftPixels'], {'bottom': 0, 'boundsCenterX': 0})
        spec = json.loads((folder / 'candidate-clip.json').read_text())
        self.assertFalse(spec['runtimeEnabled'])
        self.assertFalse(spec['productionEligible'])
        self.assertFalse(spec['clip']['loop'])
        self.assertEqual(result['naturalMotion'], 'HUMAN_REVIEW_REQUIRED')

    def test_raw_failure_never_reaches_normalization_or_rigging(self):
        for code, count in [('M039/hit-pilot', 267), ('M042/rest-pilot', 517)]:
            with self.subTest(code=code):
                folder = BATCH / code
                report = json.loads((folder / 'keypose-validation.json').read_text())
                generation = json.loads((folder / 'generation.json').read_text())
                source = json.loads((folder / 'source-alpha.json').read_text())
                raw = folder / 'keypose-tool-reference.png'
                self.assertEqual(hashlib.sha256(raw.read_bytes()).hexdigest(), generation['rawSha256'])
                self.assertEqual(report['sourceSha256'], generation['rawSha256'])
                self.assertEqual(report['sourceAlpha'], source)
                self.assertEqual(source['detachedPixels'], count)
                self.assertEqual(source['threshold'], 0)
                self.assertEqual(sum(source['detachedAlphaHistogram'].values()), count)
                self.assertEqual(report['pngErrors'], validator.png_errors(raw, True))
                self.assertEqual(report['status'], 'VALIDATION_FAILED')
                self.assertFalse(report['normalizationPerformed'])
                self.assertFalse(report['riggingPerformed'])
                self.assertFalse((folder / 'keypose.png').exists())
                self.assertFalse((folder / 'rigged').exists())

    def test_anatomy_checked_before_candidate_and_no_new_identity(self):
        catalog = json.loads((ROOT / 'design/visual-reference-v1/catalog.json').read_text())
        concepts = {r['conceptId']: r for r in catalog['monsterConcepts']}
        for code in ['M039/hit-pilot', 'M041/hit-pilot', 'M042/rest-pilot']:
            pre = json.loads((BATCH / code / 'anatomy-preflight.json').read_text())
            concept = concepts[pre['creatureId']]
            self.assertEqual(pre['proposedCatalogContract']['observedForm'], concept['observedForm'])
            self.assertEqual(pre['proposedCatalogContract']['movementProfile'], concept['movementProfile'])
            self.assertEqual(pre['catalogComparisonTiming'], 'Before candidate creation')
            self.assertEqual(hashlib.sha256((ROOT / pre['sourceBase']).read_bytes()).hexdigest(), pre['sourceSha256'])
            self.assertFalse(pre['newBodyParts'])
            self.assertFalse(pre['policyChanged'])
            self.assertFalse(pre['duplicateActionFound'])
            self.assertIsNone(pre['productionSpeciesId'])
            self.assertIsNone(pre['manifest'])

    def test_existing_nox_failure_and_approval_boundary_are_preserved(self):
        queue = json.loads((ROOT / 'design/creature-production-queue.json').read_text())
        run = queue['productionIntegrationContinuation']
        nox = run['baseBlocked']
        path = ROOT / nox['sourceBase']
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), nox['sourceSha256'])
        self.assertEqual(detached_pixels(rgba(path)), 18)
        self.assertFalse(nox['recoveryPerformed'])
        row = next(r for r in queue['creatures'] if r['creatureId'] == 'companion:nox:3')
        self.assertEqual(row['baseStatus'], 'VALIDATION_FAILED')
        action = next(a for a in row['actions'] if a['action'] == 'CURSOR_REACT')
        self.assertEqual(action['frameCount'], 0)
        self.assertEqual(action['runtimeStatus'], 'BLOCKED')
        self.assertEqual(queue['repairIterations'], 3)
        self.assertEqual(run['repairIterations'], 3)
        self.assertEqual(run['candidateFrames'], 8)
        self.assertEqual(run['candidatePng'], sum(len(list((BATCH / c).rglob('*.png'))) for c in ['M039/hit-pilot', 'M041/hit-pilot', 'M042/rest-pilot']))
        self.assertEqual(run['productionRegistrations'], 0)
        self.assertEqual(run['runtimeConnections'], 0)
        self.assertEqual(run['approvedUnconnectedAssets'], [])
        self.assertTrue(run['nextTask'])
