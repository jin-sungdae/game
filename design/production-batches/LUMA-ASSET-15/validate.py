"""Read-only first-attempt audit; only session-owned measurement JSON is written.
Run with bundled Python containing Pillow/numpy. No asset repair or alpha cleanup.
"""
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
from visual_asset_inventory import candidate, inspect_png


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pixels(path):
    image = Image.open(path)
    if image.mode != 'RGBA':
        raise ValueError(f'RGBA required: {path}')
    return np.array(image)


def raw_components(path):
    data = pixels(path)
    mask = data[:, :, 3] > 0
    height, width = mask.shape
    seen = np.zeros(mask.shape, dtype=bool)
    components = []
    for y, x in zip(*np.nonzero(mask)):
        if seen[y, x]: continue
        stack = [(int(y), int(x))]; seen[y, x] = True; component = []
        while stack:
            cy, cx = stack.pop(); component.append((cy, cx))
            for ny in range(max(0, cy-1), min(height, cy+2)):
                for nx in range(max(0, cx-1), min(width, cx+2)):
                    if mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True; stack.append((ny, nx))
        components.append(component)
    components.sort(key=len, reverse=True)
    detached = np.zeros(mask.shape, dtype=bool)
    for component in components[1:]:
        for y, x in component: detached[y, x] = True
    values, counts = np.unique(data[:, :, 3][detached], return_counts=True)
    return {'threshold': 0, 'width': data.shape[1], 'height': data.shape[0],
            'mainPixels': len(components[0]), 'detachedPixels': int(detached.sum()),
            'detachedComponents': len(components) - 1,
            'detachedAlphaHistogram': {str(v): int(n) for v, n in zip(values, counts)}}


def audit(spec_path):
    spec = json.loads(spec_path.read_text())
    source = ROOT / spec['sourceBase']; base = pixels(source)
    name = spec['clip']['name'].lower()
    files = sorted((spec_path.parent / 'rigged' / name).glob('*.png'))
    errors = []
    if len(files) != spec['clip']['frames']:
        errors.append('FRAME_COUNT_MISMATCH')
    rows = []; hashes = []; previous = None; first = None
    yy, xx = np.indices((256, 256))
    if name == 'blink':
        movable = np.zeros((256, 256), dtype=bool)
        for eye in spec['eyes']:
            movable |= ((xx-eye['x'])/eye['rx'])**2 + ((yy-eye['y'])/eye['ry'])**2 < 1
    else:
        left, top, right, bottom = spec['movableRect']
        movable = (xx > left) & (xx < right) & (yy > top) & (yy < bottom)
    for n, path in enumerate(files):
        check = candidate(path, source)
        if check['errors']: errors.extend(f'{path.name}: {e}' for e in check['errors'])
        if path.name != f'{name}_{n:02}.png': errors.append('NONCANONICAL_SEQUENCE')
        data = pixels(path)
        changed = np.any(data != base, axis=2)
        fixed = int((changed & ~movable).sum())
        support = int(np.count_nonzero((data[:, :, 3] > 0) != (base[:, :, 3] > 0)))
        alpha_changed = int(np.count_nonzero(data[:, :, 3] != base[:, :, 3]))
        if fixed: errors.append(f'{path.name}: FIXED_REGION_CHANGED')
        if not changed.any(): errors.append(f'{path.name}: NO_MOTION')
        if name != 'blink' and not support: errors.append(f'{path.name}: NO_SILHOUETTE_SUPPORT_MOTION')
        if name == 'blink' and alpha_changed: errors.append('BLINK_ALPHA_CHANGED')
        delta = float(np.abs(data.astype(float)-previous.astype(float)).mean()) if previous is not None else None
        if delta is not None and delta > 3: errors.append(f'{path.name}: FRAME_CONTINUITY_DELTA')
        if changed.mean() > .15: errors.append(f'{path.name}: APPEARANCE_CHANGE_AREA')
        pixel_hash = check['image']['pixelSha256']; hashes.append(pixel_hash)
        rows.append({'file':str(path.relative_to(ROOT)), 'sha256':digest(path),'pixelSha256':pixel_hash,
                     'bounds':check['image']['bounds'],'anchorDriftPixels':check['driftPixels'],
                     'changedPixels':int(changed.sum()),'fixedRegionChanges':fixed,
                     'alphaChangedPixels':alpha_changed,'supportChangedPixels':support,
                     'previousFrameMeanRgbaDelta':delta,'pngErrors':check['errors']})
        if first is None:first=data
        previous=data
    if len(set(hashes)) != len(hashes): errors.append('DUPLICATE_PIXELS')
    seam = float(np.abs(first.astype(float)-previous.astype(float)).mean()) if first is not None else None
    if spec['clip']['loop'] and seam is not None and seam > 3: errors.append('LOOP_SEAM_DELTA')
    result={'conceptId':spec['conceptId'],'action':spec['clip']['name'],
            'automated':'VALIDATION_FAILED' if errors else 'PASS','errors':errors,
            'sourceBase':spec['sourceBase'],'sourceSha256':digest(source),'frames':rows,
            'expectedFrames':spec['clip']['frames'],'actualFrames':len(files),
            'loopSeamMeanRgbaDelta':seam,'continuityScope':'Numerical delta only; anatomical and perceived continuity require human review',
            'appearanceScope':'Fixed pixels, local change area and registration only; identity is not automatically approved',
            'repairIterations':3,'repairLimit':3,'repairPerformed':False,
            'productionEligible':False,'runtimeConnected':False,'artworkReview':'HUMAN_REVIEW_REQUIRED','gui':'DEFERRED_GUI'}
    (spec_path.parent/'frame-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result


def main():
    source=HERE/'M056/idle-keypose/source.png'
    components=raw_components(source)
    raw={'status':'VALIDATION_FAILED' if components['detachedPixels'] else 'RAW_ALPHA_PASS_IDENTITY_REVIEW_REQUIRED',
         'sourceSha256':digest(source),'sourceAlpha':components,'normalizationPerformed':False,'riggingPerformed':False,
         'repairIterations':3,'repairLimit':3,'productionEligible':False,'artworkReview':'HUMAN_REVIEW_REQUIRED',
         'appearanceReview':'MANUAL_REQUIRED: image generation is a keypose proposal, not approved joint separation'}
    (source.parent/'keypose-validation.json').write_text(json.dumps(raw,indent=2)+'\n')
    results=[audit(p) for p in sorted(HERE.glob('M*/*/candidate-clip.json'))]
    output={'sessionId':'LUMA-ASSET-15','candidateClips':len(results),
            'automatedPassedClips':sum(r['automated']=='PASS' for r in results),
            'failedClips':sum(r['automated']!='PASS' for r in results),
            'framePngs':sum(r['actualFrames'] for r in results),
            'productionApprovedClips':0,'runtimeConnectedClips':0,'rawKeypose':raw,
            'results':[{k:r[k] for k in ('conceptId','action','automated','errors','expectedFrames','actualFrames')} for r in results]}
    (HERE/'validation.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in output.items() if k!='results'},ensure_ascii=False))

if __name__=='__main__':main()
