import hashlib
import json
import unittest
from test_assets import ROOT, validator
from test_moa_blink_v2 import rgba

BATCH = ROOT / 'design/production-batches'
BREATH_CASES = {
    'M021': (102, 170, 181, 216),
    'M022': (119, 137, 199, 190),
    'M025': (121, 150, 193, 208),
    'M026': (132, 125, 215, 176),
    'M027': (127, 136, 212, 190),
    'M028': (120, 110, 202, 172),
    'M029': (104, 163, 178, 209),
    'moa/stage05': (105, 112, 198, 188),
}


def detached_pixels(data):
    remaining = {i for i, alpha in enumerate(data[3::4]) if alpha}
    sizes = []
    while remaining:
        seed = remaining.pop()
        stack = [seed]
        size = 0
        while stack:
            i = stack.pop()
            size += 1
            x, y = i % 256, i // 256
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    xx, yy = x + dx, y + dy
                    j = yy * 256 + xx
                    if 0 <= xx < 256 and 0 <= yy < 256 and j in remaining:
                        remaining.remove(j)
                        stack.append(j)
        sizes.append(size)
    return sum(sizes) - max(sizes, default=0)


def measure(folder, movable):
    spec = json.loads((folder / 'candidate-clip.json').read_text())
    base = rgba(ROOT / spec['sourceBase'])
    base_bounds = []
    base_errors = validator.png_errors(ROOT / spec['sourceBase'], True, base_bounds)
    decoded, frames, hashes = [], [], []
    action = spec['clip']['name'].lower()
    paths = sorted((folder / 'rigged' / action).glob('*.png'))
    for n, path in enumerate(paths):
        bounds = []
        errors = validator.png_errors(path, True, bounds, hashes)
        data = rgba(path)
        decoded.append(data)
        changed = sum(data[i:i+4] != base[i:i+4] for i in range(0, len(data), 4))
        fixed_changes = sum(data[i:i+4] != base[i:i+4] for i in range(0, len(data), 4)
                            if not movable((i // 4) % 256, (i // 4) // 256))
        if path.name != f'{action}_{n:02}.png': errors.append('NONCANONICAL_SEQUENCE')
        if bounds != base_bounds: errors.append('BOUNDS_DRIFT')
        if data[3::4] != base[3::4]: errors.append('ALPHA_CHANGED')
        if fixed_changes: errors.append('PROTECTED_ANATOMY_CHANGED')
        if not changed: errors.append('NO_PIXEL_CHANGE')
        frames.append({'file': path.name, 'errors': errors, 'bounds': bounds,
                       'pixelHash': hashlib.sha256(data).hexdigest(),
                       'alphaMatchesBase': data[3::4] == base[3::4],
                       'protectedPixelChanges': fixed_changes, 'changedPixels': changed,
                       'anchorDriftPixels': {'bottom': bounds[3]-base_bounds[3],
                                            'boundsCenterX': (bounds[0]+bounds[2]-base_bounds[0]-base_bounds[2])/2}})
    deltas = [sum(abs(a-b) for a, b in zip(decoded[i], decoded[(i+1) % len(decoded)]))
              for i in range(len(decoded))]
    detached = detached_pixels(base)
    passed = not base_errors and detached == 0 and len(paths) == spec['clip']['frames'] and len(set(hashes)) == len(paths) and all(deltas) and all(not f['errors'] for f in frames)
    return {'automated': 'PASS' if passed else 'VALIDATION_FAILED', 'frames': frames,
            'sourceSha256': hashlib.sha256((ROOT / spec['sourceBase']).read_bytes()).hexdigest(),
            'baseErrors': base_errors, 'detachedAlphaPixels': detached,
            'uniquePixelHashes': len(set(hashes)), 'adjacentPixelDifferenceSumsIncludingLoop': deltas,
            'loopWithinInteriorDeltaRange': bool(deltas and min(deltas[:-1]) <= deltas[-1] <= max(deltas[:-1])),
            'automatedScope': 'PNG, RGBA, transparency, unchanged alpha, fixed anatomy, bounds, hashes; not artwork approval',
            'appearance': 'HUMAN_REVIEW_REQUIRED', 'naturalLoop': 'HUMAN_REVIEW_REQUIRED',
            'nativeGui': 'DEFERRED_GUI', 'productionEligible': False}


def eye_movable(x, y):
    return any(((x-cx)/rx)**2 + ((y-cy)/ry)**2 < 1
               for cx, cy, rx, ry in [(137.5, 122, 8.5, 11), (164, 120, 4, 10)])


class CreatureFollowupTests(unittest.TestCase):
    def check_candidate(self, folder, movable):
        measured = measure(folder, movable)
        self.assertEqual(measured['automated'], 'PASS', measured)
        self.assertEqual(json.loads((folder/'frame-validation.json').read_text()), measured)
        spec = json.loads((folder/'candidate-clip.json').read_text())
        self.assertFalse(spec['runtimeEnabled'])
        self.assertFalse(spec['productionEligible'])
        self.assertEqual(spec['artworkReview'], 'HUMAN_REVIEW_REQUIRED')
        self.assertEqual(spec['anchor'], {'x': .5, 'y': 1})

    def test_breath_keeps_each_species_head_feet_alpha_and_anchor(self):
        for code, (left, top, right, bottom) in BREATH_CASES.items():
            with self.subTest(creature=code):
                self.check_candidate(BATCH/'breath-followup'/code,
                    lambda x, y: left < x < right and top < y < bottom)

    def test_caplet_cursor_reaction_preserves_every_pixel_outside_eyes(self):
        self.check_candidate(BATCH/'monsters/cursor-react-pilot/M005', eye_movable)
        manifest = json.loads((ROOT/'public/assets/monsters/caplet/manifest.json').read_text())
        self.assertEqual(set(manifest['animations']), {'sleep'})
        self.assertFalse((ROOT/'public/assets/monsters/caplet/cursor_react').exists())

    def test_existing_failure_and_repair_limit_are_preserved(self):
        queue = json.loads((ROOT/'design/creature-production-queue.json').read_text())
        self.assertEqual(queue['restFollowup']['repairIterations'], 3)
        caplet = next(r for r in queue['creatures'] if r['creatureId'] == 'M005')
        rest = next(a for a in caplet['actions'] if a['action'] == 'REST')
        self.assertEqual(rest['animationStatus'], 'VALIDATION_FAILED')
        self.assertEqual(rest['frameCount'], 0)
        self.assertFalse(caplet['spawn']['enabled'])
