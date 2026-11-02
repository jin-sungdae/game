"""Validate this session's isolated candidates; never update shared approval state."""
from pathlib import Path
import hashlib
import json
import sys
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from visual_asset_inventory import candidate

SESSION = Path(__file__).resolve().parent
def detached_alpha(pixels):
    remaining = {i for i, pixel in enumerate(pixels) if pixel[3]}
    groups = []
    while remaining:
        start = remaining.pop()
        group = [start]
        for n in group:
            x, y = n % 256, n // 256
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    xx, yy = x + dx, y + dy
                    j = yy * 256 + xx
                    if 0 <= xx < 256 and 0 <= yy < 256 and j in remaining:
                        remaining.remove(j)
                        group.append(j)
        groups.append(group)
    groups.sort(key=len, reverse=True)
    return sum(map(len, groups[1:])), max((pixels[i][3] for g in groups[1:] for i in g), default=0)

results = []
for meta_path in sorted(SESSION.glob('M*/*/candidate-clip.json')):
    meta = json.loads(meta_path.read_text())
    folder = meta_path.parent
    rig = json.loads((folder / 'rig-evidence.json').read_text())
    base_path = ROOT / meta['sourceBase']
    base = Image.open(base_path)
    base_pixels = list(base.getdata())
    left, top, right, bottom = meta['movableRect']
    frames = sorted((ROOT / meta['framesDirectory']).glob('*.png'))
    errors = []
    if len(frames) != meta['clip']['frames']:
        errors.append('FRAME_COUNT')
    frame_results, decoded, hashes = [], [], []
    for index, frame in enumerate(frames):
        check = candidate(frame, base_path)
        im = Image.open(frame)
        pixels = list(im.getdata())
        decoded.append(pixels)
        digest = hashlib.sha256(im.tobytes()).hexdigest()
        hashes.append(digest)
        protected_changes = sum(pixels[y*256+x] != base_pixels[y*256+x]
            for y in range(256) for x in range(256)
            if x <= left or x >= right or y <= top or y >= bottom)
        border = sum(pixels[y*256+x][3] != 0 for y in range(256) for x in range(256)
            if x in (0,255) or y in (0,255))
        alpha_changes = sum(a[3] != b[3] for a,b in zip(pixels, base_pixels))
        changed = sum(a != b for a,b in zip(pixels, base_pixels))
        detached, detached_max = detached_alpha(pixels)
        failures = list(check['errors'])
        if detached: failures.append('DETACHED_ALPHA')
        if im.mode != 'RGBA' or im.size != (256,256): failures.append('FORMAT')
        if protected_changes or border: failures.append('PROTECTED_PIXELS_OR_BORDER')
        if not alpha_changes or not changed: failures.append('NO_LOCAL_SILHOUETTE_MOTION')
        if digest != rig['frames'][index]['pixelSha256']: failures.append('PIXEL_HASH_MISMATCH')
        frame_results.append({'file':str(frame.relative_to(ROOT)), 'errors':failures,
            'bounds':check['image']['bounds'], 'pixelSha256':digest,
            'anchorDriftPixels':check['driftPixels'], 'protectedPixelChanges':protected_changes,
            'detachedAlphaPixels':detached, 'detachedMaxAlpha':detached_max,
            'alphaChangedPixels':alpha_changes, 'changedPixels':changed,
            'unchangedPixelFraction':1-changed/(256*256)})
        errors.extend(failures)
    pairs = list(zip(decoded, decoded[1:]))
    if meta['clip']['loop']: pairs.append((decoded[-1],decoded[0]))
    continuity = [{'changedPixels':sum(x!=y for x,y in zip(a,b)),
        'meanAbsoluteRgbaDelta':sum(abs(x[c]-y[c]) for x,y in zip(a,b) for c in range(4))/(256*256*4)} for a,b in pairs]
    if len(set(hashes)) != len(frames): errors.append('DUPLICATE_FRAMES')
    if not all(0 < row['changedPixels'] < 7000 and row['meanAbsoluteRgbaDelta'] < 3 for row in continuity):
        errors.append('CONTINUITY_ENVELOPE')
    keypose_check = candidate(folder/'keypose.png', base_path)
    errors.extend(keypose_check['errors'])
    if Image.open(folder/'keypose.png').tobytes() != Image.open(frames[3]).tobytes(): errors.append('KEYPOSE_MISMATCH')
    report={'keypose':keypose_check,'conceptId':meta['conceptId'],'action':meta['clip']['name'],
        'automated':'FAIL' if errors else 'PASS','errors':errors,'frames':frame_results,
        'uniquePixelHashes':len(set(hashes)),'continuity':continuity,
        'continuityScope':'Adjacent decoded-pixel change bounds; includes seam only for loop. Does not certify natural motion or cross-clip transitions.',
        'appearanceDrift':'Protected regions exact; bounds anchored. Visual species identity requires human review.',
        'naturalMotionReview':'HUMAN_REVIEW_REQUIRED','productionEligible':False,'runtimeConnected':False,'gui':'DEFERRED_GUI'}
    (folder/'frame-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    results.append({'conceptId':meta['conceptId'],'action':meta['clip']['name'],'automated':report['automated'], 'errors':errors})
(SESSION/'validation.json').write_text(json.dumps({'sessionId':'LUMA-ASSET-20','clips':results,'productionEligible':False,'gui':'DEFERRED_GUI'},indent=2)+'\n')
print(json.dumps(results,indent=2))
raise SystemExit(any(r['errors'] for r in results))
