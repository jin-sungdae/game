"""Session-only evidence; never updates shared approval or runtime state."""
from pathlib import Path
import hashlib
import json
import sys
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from validate_assets import png_errors

SESSION = Path(__file__).resolve().parent
results = []
for evidence in sorted(SESSION.glob('M*/ */rig-evidence.json'.replace(' ', ''))):
    directory = evidence.parent
    rig = json.loads(evidence.read_text())
    base = Image.open(ROOT / rig['reference']).convert('RGBA')
    base_pixels = list(base.getdata())
    bounds = []
    base_errors = png_errors(ROOT / rig['reference'], True, bounds, [])
    action = directory.name
    frames = sorted((directory / 'rigged' / action).glob('*.png'))
    pixels, rows, hashes = [], [], []
    for frame in frames:
        box = []
        errors = png_errors(frame, True, box, hashes)
        im = Image.open(frame)
        data = list(im.getdata())
        pixels.append(data)
        if im.mode != 'RGBA' or im.size != (256, 256): errors.append('FORMAT')
        if box != bounds: errors.append('BOUNDS_DRIFT')
        # Feet/contact and upper identity features must remain pixel-identical.
        anchor_changes = sum(data[y*256+x] != base_pixels[y*256+x]
                             for y in range(210, 256) for x in range(256))
        if anchor_changes: errors.append('ANCHOR_CHANGED')
        digest = hashlib.sha256(im.tobytes()).hexdigest()
        item = next(r for r in rig['frames'] if r['file'] == frame.name)
        if digest != item['pixelSha256']: errors.append('HASH_MISMATCH')
        if item['fixedRegionChanges']: errors.append('PROTECTED_REGION_CHANGED')
        rows.append(dict(file=str(frame.relative_to(ROOT)), errors=errors,
                         pixelSha256=digest, bounds=box, anchorChangedPixels=anchor_changes,
                         changedPixels=item['changedPixels']))
    adjacency = [sum(a != b for a, b in zip(pixels[i], pixels[(i+1) % len(pixels)])) for i in range(len(pixels))]
    max_channel = [max(abs(a[c]-b[c]) for a,b in zip(pixels[i],pixels[(i+1)%len(pixels)]) for c in range(4)) for i in range(len(pixels))]
    errors = base_errors + [e for row in rows for e in row['errors']]
    if len(frames) != 8 or len(set(hashes)) != 8 or not all(adjacency): errors.append('FRAME_SET')
    # Compare decoded hashes with pre-existing candidates to reject duplicate production.
    old_hashes = set()
    for old in (ROOT/'design/production-batches').glob('**/'+directory.parent.name+'/**/rig-evidence.json'):
        if SESSION in old.parents: continue
        old_hashes.update(r['pixelSha256'] for r in json.loads(old.read_text()).get('frames', []) if 'pixelSha256' in r)
    if any(row['pixelSha256'] in old_hashes for row in rows): errors.append('EXISTING_CANDIDATE_DUPLICATED')
    results.append(dict(monster=directory.parent.name,action=action.upper(),automated='FAIL' if errors else 'PASS',
        errors=errors,frames=rows,adjacentChangedPixelsIncludingLoop=adjacency,
        adjacentMaxChannelDeltaIncludingLoop=max_channel,appearanceDrift='PROTECTED_PIXELS_VERIFIED; MANUAL_REQUIRED',
        frameContinuity='MEASURED; NATURAL_MOTION_MANUAL_REQUIRED',productionEligible=False))
(SESSION/'validation.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
print([(r['monster'],r['action'],r['automated'],r['errors']) for r in results])
raise SystemExit(1 if len(results)!=3 or any(r['automated']!='PASS' for r in results) else 0)
