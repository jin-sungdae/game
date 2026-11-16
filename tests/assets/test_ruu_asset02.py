import hashlib
import json
import unittest
from test_assets import ROOT
from test_creature_followup import measure
from test_moa_blink_v2 import rgba

BATCH = ROOT / 'design/production-batches/luma-asset-02/ruu'
CASES = ('stage03/blink', 'stage04/look', 'stage04/interact', 'stage05/blink')


def measured(folder):
    spec = json.loads((folder / 'candidate-clip.json').read_text())
    if 'eyes' in spec:
        movable = lambda x, y: any(((x-e['x'])/e['rx'])**2 + ((y-e['y'])/e['ry'])**2 < 1
                                   for e in spec['eyes'])
    else:
        left, top, right, bottom = spec['movableRect']
        movable = lambda x, y: left < x < right and top < y < bottom
    return measure(folder, movable)


class RuuAsset02Tests(unittest.TestCase):
    def test_frames_match_existing_validator_and_fixed_anatomy_contract(self):
        for case in CASES:
            with self.subTest(case=case):
                folder = BATCH / case
                spec = json.loads((folder / 'candidate-clip.json').read_text())
                report = measured(folder)
                self.assertEqual(report, json.loads((folder / 'frame-validation.json').read_text()))
                self.assertEqual(report['automated'], 'PASS')
                self.assertEqual(report['uniquePixelHashes'], spec['clip']['frames'])
                self.assertEqual(report['detachedAlphaPixels'], 0)
                self.assertFalse(spec['runtimeEnabled'])
                self.assertFalse(spec['productionEligible'])
                self.assertFalse(spec['clip']['loop'])
                self.assertEqual(spec['anchor'], {'x': .5, 'y': 1})
                self.assertEqual(spec['artworkReview'], 'HUMAN_REVIEW_REQUIRED')
                self.assertEqual(report['nativeGui'], 'DEFERRED_GUI')

    def test_failed_first_blinks_remain_failed_and_are_not_selected(self):
        for stage in ('stage03', 'stage05'):
            folder = BATCH / stage / 'blink-attempt01-failed'
            report = measured(folder)
            self.assertEqual(report, json.loads((folder / 'frame-validation.json').read_text()))
            self.assertEqual(report['automated'], 'VALIDATION_FAILED')
            self.assertEqual(report['uniquePixelHashes'], 5)
            self.assertEqual(json.loads((BATCH / stage / 'blink/candidate-clip.json').read_text())['attempt'], 2)

    def test_continuity_and_appearance_drift_are_bounded_but_not_artwork_approval(self):
        # Small eye/feather rigs: every transition incl. return to BASE stays below
        # one RGB intensity unit averaged over the canvas; alpha is checked separately.
        for case in CASES:
            folder = BATCH / case
            spec = json.loads((folder / 'candidate-clip.json').read_text())
            base = rgba(ROOT / spec['sourceBase'])
            frames = [rgba(p) for p in sorted((folder / 'rigged' / spec['clip']['name'].lower()).glob('*.png'))]
            sequence = [base, *frames, base]
            for a, b in zip(sequence, sequence[1:]):
                self.assertLess(sum(abs(x-y) for x, y in zip(a, b))/(256*256*3), 1)
            for frame in frames:
                self.assertEqual(frame[3::4], base[3::4])
                self.assertLess(sum(abs(x-y) for x, y in zip(base, frame))/(256*256*3), 1)

    def test_no_new_clip_duplicates_existing_ruu_frames(self):
        existing = set()
        for stage in (3, 4, 5):
            for p in (ROOT / f'design/production-batches/action-followup/ruu/stage{stage:02}').glob('**/rigged/*/*.png'):
                existing.add(hashlib.sha256(rgba(p)).hexdigest())
        for case in CASES:
            for p in (BATCH / case).glob('rigged/*/*.png'):
                self.assertNotIn(hashlib.sha256(rgba(p)).hexdigest(), existing)

    def test_handoff_selects_only_new_candidates_and_preserves_blocked_stages(self):
        handoff = json.loads((BATCH / 'handoff.json').read_text())
        queue = json.loads((ROOT / 'design/creature-production-queue.json').read_text())
        self.assertEqual(handoff['sessionId'], 'LUMA-ASSET-02')
        self.assertEqual(handoff['repairIterations'], 1)
        self.assertEqual(handoff['repairLimit'], 3)
        self.assertEqual(set(handoff['candidateDirectories']), set(CASES))
        for stage in (1, 2):
            row = next(r for r in queue['creatures'] if r['creatureId'] == f'companion:ruu:{stage}')
            self.assertEqual(row['state'], 'BLOCKED')
            self.assertFalse((BATCH / f'stage{stage:02}').exists())
        self.assertFalse(handoff['productionEligible'])
        self.assertFalse(handoff['runtimeEnabled'])
