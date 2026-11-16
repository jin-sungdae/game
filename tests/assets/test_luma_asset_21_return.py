import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from test_assets import ROOT, validator
from test_moa_blink_v2 import rgba
from test_creature_new_pose_quality import measure_parts, compare_keypose

FOLDER = ROOT / 'design/production-batches/LUMA-ASSET-21/continuation-02'
CASES = ('M087/idle', 'M088/idle', 'M090/rest')


def measure_return(folder):
    spec = json.loads((folder / 'candidate-clip.json').read_text())
    action = spec['clip']['name'].lower()
    paths = sorted((folder / 'rigged' / action).glob('*.png'))
    # Run unchanged shared part-motion checks on all seven animated frames.
    with tempfile.TemporaryDirectory(prefix='luma-asset21-motion-') as tmp:
        stage = Path(tmp)
        motion_spec = copy.deepcopy(spec)
        motion_spec['clip']['frames'] = 7
        (stage / 'candidate-clip.json').write_text(json.dumps(motion_spec))
        dest = stage / 'rigged' / action
        dest.mkdir(parents=True)
        for path in paths[:7]:
            shutil.copyfile(path, dest / path.name)
        motion = measure_parts(stage)
    base_path = ROOT / spec['sourceBase']
    base = rgba(base_path)
    decoded = [rgba(p) for p in paths]
    hashes = []
    errors = []
    base_bounds = []
    errors += validator.png_errors(base_path, True, base_bounds)
    for p in paths:
        bounds = []
        errors += validator.png_errors(p, True, bounds, hashes)
        if bounds != base_bounds:
            errors.append('BOUNDS_DRIFT')
    distance = lambda a, b: sum(abs(x-y) for x, y in zip(a, b))
    adjacent = [distance(a, b) for a, b in zip(decoded, decoded[1:])]
    entry = distance(base, decoded[0])
    terminal = decoded[-1] == base
    passed = (len(paths) == 8 and len(set(hashes)) == 8 and not errors
              and motion['automated'] == 'PASS' and terminal
              and all(adjacent) and entry <= max(adjacent))
    return {'automated': 'PASS' if passed else 'VALIDATION_FAILED',
            'motionFrames': motion, 'allFrameErrors': errors,
            'uniquePixelHashes': len(set(hashes)),
            'entryRgbaL1': entry, 'adjacentRgbaL1': adjacent,
            'terminalEqualsBase': terminal,
            'terminalRgbaL1': distance(decoded[-1], base),
            'entryWithinObservedAdjacentMaximum': entry <= max(adjacent),
            'sourceSha256': hashlib.sha256(base_path.read_bytes()).hexdigest(),
            'appearance': compare_keypose(folder),
            'naturalMotion': 'HUMAN_REVIEW_REQUIRED', 'gui': 'DEFERRED_GUI',
            'productionEligible': False, 'runtimeEnabled': False}


class Asset21ReturnTests(unittest.TestCase):
    def test_independent_motion_and_exact_base_terminal(self):
        for case in CASES:
            with self.subTest(case=case):
                folder = FOLDER / case
                result = measure_return(folder)
                self.assertEqual(result, json.loads((folder / 'frame-validation.json').read_text()))
                self.assertEqual(result['automated'], 'PASS')
