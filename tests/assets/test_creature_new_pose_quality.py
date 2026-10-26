import hashlib
import json
import unittest
from pathlib import Path

from test_assets import ROOT, validator
from test_moa_blink_v2 import rgba
from test_creature_followup import detached_pixels

BATCH = ROOT / 'design/production-batches/action-followup'
CASES = {'companion:moa:5 HIT': 'moa/stage05/hit-pilot', 'M022 INTERACT': 'M022/interact-pilot', 'companion:ruu:5 HIT': 'ruu/stage05/hit-pilot'}
FAILED = {'M019 ATTACK': ('M019/attack-pilot', 9), 'M021 TURN': ('M021/turn-pilot', 582)}


def measure_parts(folder):
    spec = json.loads((folder / 'candidate-clip.json').read_text())
    base_path = ROOT / spec['sourceBase']
    base = rgba(base_path)
    base_bounds = []
    base_errors = validator.png_errors(base_path, True, base_bounds)
    l, t, r, b = spec['movableRect']
    name = spec['clip']['name'].lower()
    paths = sorted((folder / 'rigged' / name).glob('*.png'))
    reports, decoded, hashes = [], [], []
    for n, path in enumerate(paths):
        bounds = []
        errors = validator.png_errors(path, True, bounds, hashes)
        data = rgba(path)
        decoded.append(data)
        protected = sum(data[i:i+4] != base[i:i+4] for i in range(0, len(data), 4)
                        if not (l < (i//4) % 256 < r and t < (i//4)//256 < b))
        alpha_changes = sum(a != z for a, z in zip(data[3::4], base[3::4]))
        support_changes = sum((a > 0) != (z > 0) for a, z in zip(data[3::4], base[3::4]))
        detached = detached_pixels(data)
        edge = sum(data[(y*256+x)*4+3] > 0 for y in range(256) for x in range(256)
                   if x in (0, 255) or y in (0, 255))
        if path.name != f'{name}_{n:02}.png': errors.append('NONCANONICAL_SEQUENCE')
        if bounds != base_bounds: errors.append('BOUNDS_DRIFT')
        if protected: errors.append('PROTECTED_ANATOMY_CHANGED')
        if not alpha_changes: errors.append('NO_LOCAL_ALPHA_MOTION')
        if detached: errors.append('DETACHED_ALPHA')
        if edge: errors.append('CANVAS_EDGE_CLIPPING')
        reports.append({'file': path.name, 'errors': errors, 'bounds': bounds,
                        'pixelHash': hashlib.sha256(data).hexdigest(),
                        'protectedPixelChanges': protected, 'alphaChangedPixels': alpha_changes,
                        'silhouetteSupportChangedPixels': support_changes,
                        'detachedAlphaPixels': detached, 'canvasEdgePixels': edge,
                        'anchorDriftPixels': {'bottom': bounds[3]-base_bounds[3],
                                             'boundsCenterX': (bounds[0]+bounds[2]-base_bounds[0]-base_bounds[2])/2}})
    deltas = [sum(abs(a-b) for a, b in zip(decoded[n], decoded[(n+1) % len(decoded)]))
              for n in range(len(decoded))]
    passed = (not base_errors and detached_pixels(base) == 0
              and len(paths) == spec['clip']['frames'] and len(set(hashes)) == len(paths)
              and all(deltas) and all(not f['errors'] for f in reports)
              and any(f['silhouetteSupportChangedPixels'] > 0 for f in reports))
    return {'automated': 'PASS' if passed else 'VALIDATION_FAILED', 'frames': reports,
            'sourceSha256': hashlib.sha256(base_path.read_bytes()).hexdigest(),
            'baseErrors': base_errors, 'baseDetachedAlphaPixels': detached_pixels(base),
            'uniquePixelHashes': len(set(hashes)), 'adjacentPixelDifferenceSumsIncludingLoop': deltas,
            'loopContract': 'ONE_SHOT; boundary measured but seamless cyclic motion is not claimed',
            'automatedScope': 'Existing PNG validator plus local RGBA/support motion, protected anatomy, bounds, anchor, zero detached alpha, no canvas clipping and unique frames',
            'appearance': 'HUMAN_REVIEW_REQUIRED', 'naturalMotion': 'HUMAN_REVIEW_REQUIRED',
            'nativeGui': 'DEFERRED_GUI', 'productionEligible': False}


def compare_keypose(folder):
    generation = json.loads((folder / 'generation.json').read_text())
    base = rgba(ROOT / generation['sourceBase'])
    candidate = rgba(folder / 'keypose.png')
    bb, cb = [], []
    validator.png_errors(ROOT / generation['sourceBase'], True, bb)
    validator.png_errors(folder / 'keypose.png', True, cb)
    intersection = sum(a > 0 and b > 0 for a, b in zip(base[3::4], candidate[3::4]))
    union = sum(a > 0 or b > 0 for a, b in zip(base[3::4], candidate[3::4]))
    def palette(data):
        bins = [0.0] * 64
        total = sum(data[3::4])
        for i in range(0, len(data), 4):
            index = (data[i] // 64)*16 + (data[i+1] // 64)*4 + data[i+2] // 64
            bins[index] += data[i+3] / total
        return bins
    palette_l1 = sum(abs(a-b) for a, b in zip(palette(base), palette(candidate)))
    return {'sourceBase': generation['sourceBase'],
            'baseFileSha256': hashlib.sha256((ROOT / generation['sourceBase']).read_bytes()).hexdigest(),
            'keyposeFileSha256': hashlib.sha256((folder / 'keypose.png').read_bytes()).hexdigest(),
            'baseBounds': bb, 'candidateBounds': cb,
            'canvasAlignedAlphaIoU': round(intersection / union, 6),
            'alphaWeightedPaletteL1': round(palette_l1, 6),
            'boundsBottomDelta': cb[3]-bb[3],
            'scope': 'Read-only same-canvas geometry and palette comparison; pose/scale differences affect metrics. No semantic species, head, limb, face, or natural-motion approval inferred.',
            'identityReview': 'HUMAN_REVIEW_REQUIRED'}


class NewPoseQualityTests(unittest.TestCase):
    def test_candidates_move_local_silhouette_and_preserve_protected_anatomy(self):
        signatures = set()
        for identity, code in CASES.items():
            with self.subTest(identity=identity):
                folder = BATCH / code
                spec = json.loads((folder / 'candidate-clip.json').read_text())
                result = measure_parts(folder)
                self.assertEqual(result, json.loads((folder / 'frame-validation.json').read_text()))
                self.assertEqual(result['automated'], 'PASS')
                self.assertEqual(result['uniquePixelHashes'], 8)
                self.assertEqual(result['baseDetachedAlphaPixels'], 0)
                self.assertTrue(any(f['silhouetteSupportChangedPixels'] > 0 for f in result['frames']))
                for f in result['frames']:
                    self.assertEqual(f['errors'], [])
                    self.assertEqual(f['protectedPixelChanges'], 0)
                    self.assertEqual(f['detachedAlphaPixels'], 0)
                    self.assertEqual(f['anchorDriftPixels'], {'bottom': 0, 'boundsCenterX': 0})
                self.assertFalse(spec['runtimeEnabled'])
                self.assertFalse(spec['productionEligible'])
                self.assertFalse(spec['clip']['loop'])
                signatures.add(json.dumps(spec['parts'], sort_keys=True))
        self.assertEqual(len(signatures), len(CASES))

    def test_source_alpha_failures_and_unapproved_identity_are_not_hidden(self):
        for identity, (code, expected) in FAILED.items():
            with self.subTest(identity=identity):
                folder = BATCH / code
                report = json.loads((folder / 'keypose-validation.json').read_text())
                bounds, hashes = [], []
                self.assertEqual(validator.png_errors(folder / 'keypose.png', True, bounds, hashes), report['pngErrors'])
                self.assertEqual(bounds, report['bounds'])
                self.assertEqual(hashes[0], report['pixelHash'])
                self.assertEqual(detached_pixels(rgba(folder / 'keypose.png')), expected)
                self.assertEqual(report['detachedAlphaPixels'], expected)
                self.assertEqual(report['status'], 'VALIDATION_FAILED')
                self.assertFalse(report['productionEligible'])
                self.assertFalse((folder / 'rigged').exists())
                source = json.loads((folder / 'source-alpha.json').read_text())
                self.assertEqual(source['threshold'], 0)
                self.assertGreater(source['detachedPixels'], 0)
                self.assertEqual(compare_keypose(folder), report['baseComparison'])
                self.assertEqual(report['baseComparison']['identityReview'], 'HUMAN_REVIEW_REQUIRED')

    def test_ledger_keeps_existing_approvals_and_limit(self):
        queue = json.loads((ROOT / 'design/creature-production-queue.json').read_text())
        run = queue['newPoseQualityContinuation']
        self.assertEqual(queue['repairIterations'], 3)
        self.assertEqual(run['repairIterations'], 3)
        self.assertEqual(run['newCases'], CASES)
        self.assertEqual(run['candidateFrames'], 24)
        self.assertEqual(run['candidatePng'], 31)
        self.assertEqual(run['productionRegistrations'], 0)
        self.assertEqual(run['runtimeConnections'], 0)
        self.assertEqual(run['approvedUnconnectedAssets'], [])
        paths = list(CASES.values()) + [x[0] for x in FAILED.values()]
        self.assertEqual(sum(len(list((BATCH / p).rglob('*.png'))) for p in paths), 31)
        for identity_action, code in CASES.items():
            identity, action = identity_action.split()
            item = next(a for r in queue['creatures'] if r['creatureId'] == identity
                        for a in r['actions'] if a['action'] == action)
            self.assertEqual(item['runtimeStatus'], 'BLOCKED')
            self.assertEqual(item['artworkReview'], 'HUMAN_REVIEW_REQUIRED')
        caplet = next(r for r in queue['creatures'] if r['creatureId'] == 'M005')
        self.assertFalse(caplet['spawn']['enabled'])
        self.assertTrue(run['nextTask'])
