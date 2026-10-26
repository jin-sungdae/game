"""Read-only candidate checks. Measurements are not visual or Production approval."""
import hashlib
import json
from pathlib import Path
import sys
from PIL import Image
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
BATCH = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
from validate_assets import png_errors

def detached_pixels(alpha):
    occupied = set(zip(*np.nonzero(alpha)))
    sizes = []
    while occupied:
        seed = occupied.pop()
        todo, size = [seed], 1
        while todo:
            y, x = todo.pop()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    other = (y + dy, x + dx)
                    if other in occupied:
                        occupied.remove(other)
                        todo.append(other)
                        size += 1
        sizes.append(size)
    return sum(sizes) - max(sizes, default=0)

def validate_clip(file):
    clip = json.loads(file.read_text())
    base = np.array(Image.open(ROOT / clip['sourceBase']))
    base_bounds = Image.fromarray(base[:, :, 3]).getbbox()
    base_detached = detached_pixels(base[:, :, 3])
    yy, xx = np.mgrid[:256, :256]
    mutable = np.zeros((256, 256), dtype=bool)
    for p in clip['parts'] + clip['eyes']:
        mutable |= ((xx-p['x'])/p['rx'])**2 + ((yy-p['y'])/p['ry'])**2 < 1
    rows, decoded, errors = [], [], []
    for frame in clip['frames']:
        path = file.parent / frame['file']
        bounds, visible_hashes = [], []
        frame_errors = png_errors(path, True, bounds, visible_hashes)
        pixels = np.array(Image.open(path))
        decoded.append(pixels)
        changed = np.any(base != pixels, axis=2)
        fixed_changes = int(np.count_nonzero(changed & ~mutable))
        detached = detached_pixels(pixels[:, :, 3])
        bbox = Image.fromarray(pixels[:, :, 3]).getbbox()
        drift = [a-b for a,b in zip(bbox, base_bounds)]
        raw_hash = hashlib.sha256(pixels.tobytes()).hexdigest()
        if raw_hash != frame['pixelSha256']: frame_errors.append('PIXEL_HASH_MISMATCH')
        if fixed_changes: frame_errors.append('FIXED_ANATOMY_CHANGED')
        if max(map(abs, drift)) > 1 or drift[3]: frame_errors.append('BOUNDS_OR_ANCHOR_DRIFT')
        if detached > base_detached: frame_errors.append('NEW_DETACHED_ALPHA')
        if np.any(pixels[[0,-1],:,3]) or np.any(pixels[:,[0,-1],3]): frame_errors.append('BORDER_ALPHA')
        if np.count_nonzero(changed) > 65536*.1: frame_errors.append('EXCESSIVE_APPEARANCE_DRIFT')
        if not np.array_equal(base[240:,:,:], pixels[240:,:,:]): frame_errors.append('GROUND_ANCHOR_CHANGED')
        rows.append(dict(file=frame['file'],pixelSha256=raw_hash,visiblePixelSha256=visible_hashes[0],
            bounds=bounds,boundsDriftPixels=drift,anchorDriftPixels=drift[3],
            changedPixels=int(np.count_nonzero(changed)),fixedRegionChanges=fixed_changes,
            detachedAlphaPixels=detached,errors=frame_errors))
        errors.extend(frame_errors)
    transitions = list(zip(decoded[:-1], decoded[1:]))
    if clip['clip']['loop']: transitions.append((decoded[-1], decoded[0]))
    continuity = [dict(changedPixels=int(np.count_nonzero(np.any(a!=b,axis=2))),
        meanAbsoluteRgbaDelta=float(np.abs(a.astype(float)-b).mean()),
        maxChannelDelta=int(np.abs(a.astype(int)-b.astype(int)).max())) for a,b in transitions]
    # Structural discontinuity threshold; smoothness still requires human animation review.
    if any(t['meanAbsoluteRgbaDelta'] > 1.5 for t in continuity): errors.append('FRAME_DISCONTINUITY')
    unique = len({row['pixelSha256'] for row in rows})
    if unique < 5: errors.append('INSUFFICIENT_DISTINCT_POSES')
    if not clip['clip']['loop'] and (not np.array_equal(decoded[0],base) or not np.array_equal(decoded[-1],base)):
        errors.append('ONE_SHOT_ENDPOINT_NOT_BASE')
    if clip['productionEligible'] or clip['runtimeEnabled']: errors.append('APPROVAL_BOUNDARY')
    return dict(conceptId=clip['conceptId'],action=clip['clip']['name'],
        status='FAIL' if errors else 'PASS',errors=sorted(set(errors)),frames=rows,
        uniquePixelHashes=unique,baseDetachedAlphaPixels=base_detached,transitions=continuity,
        repeatedEndpointPolicy='One-shot neutral start/end/hold is intentional; no unique-frame claim',
        appearanceDrift='FIXED_REGIONS_AND_NUMERIC_LOCALITY_ONLY',naturalMotion='MANUAL_REQUIRED',
        productionEligible=False,runtimeConnected=False)

def run():
    return [validate_clip(path) for path in sorted(BATCH.glob('M*/**/candidate-clip.json'))]

if __name__ == '__main__':
    results = run()
    report = dict(sessionId='LUMA-ASSET-12',status='FAIL' if any(r['status']=='FAIL' for r in results) else 'PASS',
        clipCount=len(results),pngCount=sum(len(r['frames']) for r in results),results=results,
        artworkApproval='HUMAN_REVIEW_REQUIRED',nativeGui='NOT_RUN',productionEligible=False)
    (BATCH/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    for r in results: print(r['conceptId'],r['action'],r['status'],r['errors'],r['uniquePixelHashes'])
    raise SystemExit(report['status']=='FAIL')
