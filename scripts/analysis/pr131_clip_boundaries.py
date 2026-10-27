"""Read-only boundary measurements for PR131 candidates, never artwork approval."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tests/assets'))
from test_moa_blink_v2 import rgba
from test_creature_new_pose_quality import measure_parts

CASES = ('M088/interact-pilot', 'M090/hit-pilot', 'M092/hit-pilot',
         'M096/cursor_react-pilot')
BATCH = ROOT / 'design/production-batches/action-followup'


def pixel_difference(before, after):
    if not before or len(before) != len(after) or len(before) % 4:
        raise ValueError('equal nonempty RGBA buffers required')
    raw_sum = sum(abs(a-b) for a, b in zip(before, after))
    changed = visible = maximum = total = alpha_maximum = 0
    for i in range(0, len(before), 4):
        a, b = before[i:i+4], after[i:i+4]
        changed += a != b
        alpha_maximum = max(alpha_maximum, abs(a[3]-b[3]))
        pixel_maximum = 0
        for channel in range(3):
            # Source-over difference on black/white bounds every uniform RGB background.
            black = a[channel]*a[3] - b[channel]*b[3]
            white = black + 255*(b[3]-a[3])
            delta = max(abs(black), abs(white))
            pixel_maximum = max(pixel_maximum, delta)
            maximum = max(maximum, delta)
            total += delta
        visible += pixel_maximum != 0
    return {'rawChangedPixels': changed, 'rawRgbaAbsoluteDifference': raw_sum,
            'visibleChangedPixels': visible, 'maxAlphaDifference': alpha_maximum,
            'maxCompositeDifference': round(maximum/255, 6),
            'meanCompositeDifference': round(total/(255*3*(len(before)//4)), 6)}


def visible_hash(data):
    normalized = bytearray(data)
    for i in range(0, len(data), 4):
        if data[i+3] == 0:
            normalized[i:i+3] = b'\0\0\0'
    return hashlib.sha256(normalized).hexdigest()


def measure_clip(code):
    folder = BATCH / code
    spec = json.loads((folder / 'candidate-clip.json').read_text())
    base_path = ROOT / spec['sourceBase']
    name = spec['clip']['name'].lower()
    paths = sorted((folder / 'rigged' / name).glob('*.png'))
    expected = [f'{name}_{i:02}.png' for i in range(spec['clip']['frames'])]
    if not paths or [p.name for p in paths] != expected:
        raise ValueError('complete canonical frame sequence required')
    base = rgba(base_path)
    frames = [rgba(p) for p in paths]
    # Reuse the existing strict validator; supplemental metrics do not replace it.
    validation = measure_parts(folder)
    return {'creatureId': spec['conceptId'], 'action': spec['clip']['name'],
            'candidatePath': str(folder.relative_to(ROOT)),
            'sourceBaseSha256': hashlib.sha256(base_path.read_bytes()).hexdigest(),
            'frameSha256': [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths],
            'uniqueVisibleHashes': len({visible_hash(f) for f in frames}),
            'existingValidatorStatus': validation['automated'],
            'entry': pixel_difference(base, frames[0]),
            'adjacent': [pixel_difference(a, b) for a, b in zip(frames, frames[1:])],
            'exit': pixel_difference(frames[-1], base),
            'lastToFirst': pixel_difference(frames[-1], frames[0]),
            'returnsExactBasePixels': frames[-1] == base,
            'loop': spec['clip']['loop'],
            'assessment': 'MEASURED_ONLY_NO_NEW_PASS_THRESHOLD',
            'appearance': 'HUMAN_REVIEW_REQUIRED',
            'naturalMotion': 'HUMAN_REVIEW_REQUIRED',
            'productionApproved': False, 'runtimeEnabled': False}


def report():
    return {'schemaVersion': 1, 'scope': 'PR131 only; external PR clips are not imported or counted',
            'clips': [measure_clip(code) for code in CASES],
            'productionRegistrations': 0, 'runtimeConnections': 0,
            'nativeGui': 'DEFERRED_GUI'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = json.dumps(report(), indent=2) + '\n'
    if args.output:
        args.output.write_text(result)
    else:
        print(result, end='')
