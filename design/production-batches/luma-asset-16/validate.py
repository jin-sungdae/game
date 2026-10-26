"""Session-local, read-only candidate checks; existing PNG decoder remains authoritative.
Run from repository root with Pillow installed. Writes no shared ledger or manifest.
"""
import hashlib
import json
import sys
from collections import deque
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from visual_asset_inventory import candidate

DIRECTORY = Path(__file__).resolve().parent

def detached_pixels(pixels):
    remaining = {i for i, p in enumerate(pixels) if p[3] > 0}
    total = len(remaining)
    largest = 0
    while remaining:
        queue = deque([remaining.pop()])
        count = 0
        while queue:
            i = queue.popleft()
            count += 1
            x, y = i % 256, i // 256
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    xx, yy = x+dx, y+dy
                    j = yy*256+xx
                    if 0 <= xx < 256 and 0 <= yy < 256 and j in remaining:
                        remaining.remove(j)
                        queue.append(j)
        largest = max(largest, count)
    return total-largest

def delta(a, b):
    changed = sum(x != y for x, y in zip(a,b))
    mean = sum(sum(abs(x[c]-y[c]) for c in range(4)) for x,y in zip(a,b))/(256*256*4)
    return {'changedPixels':changed,'meanAbsoluteChannelDelta':round(mean,6)}

def main():
    clips = []
    for contract in sorted(DIRECTORY.glob('M*/*/candidate-clip.json')):
        spec = json.loads(contract.read_text())
        base_path = ROOT/spec['sourceBase']
        with Image.open(base_path) as im:
            base = list(im.convert('RGBA').getdata())
        left,top,right,bottom = spec['movableRect']
        name = spec['clip']['name'].lower()
        files = sorted((contract.parent/'rigged'/name).glob('*.png'))
        errors, frames, decoded = [], [], []
        if len(files) != spec['clip']['frames']:
            errors.append('FRAME_COUNT_MISMATCH')
        for i,path in enumerate(files):
            result = candidate(path,base_path)
            with Image.open(path) as im:
                if im.size != (256,256) or im.mode != 'RGBA': errors.append('FORMAT_MISMATCH')
                pixels = list(im.convert('RGBA').getdata())
            decoded.append(pixels)
            protected = sum(a!=b for n,(a,b) in enumerate(zip(base,pixels))
                            if n%256<=left or n%256>=right or n//256<=top or n//256>=bottom)
            alpha_changes = sum(a[3]!=b[3] for a,b in zip(base,pixels))
            support_changes = sum((a[3]>0)!=(b[3]>0) for a,b in zip(base,pixels))
            detached = detached_pixels(pixels)
            if protected: errors.append(f'{path.name}: PROTECTED_REGION_CHANGED')
            terminal = spec.get('terminalFrame')
            is_base_return = terminal is not None and i == terminal.get('index')
            if is_base_return:
                if i != len(files)-1 or terminal.get('role') != 'EXACT_BASE_RETURN' or pixels != base:
                    errors.append(f'{path.name}: INVALID_BASE_RETURN')
            elif not alpha_changes or not support_changes:
                errors.append(f'{path.name}: NO_SILHOUETTE_MOTION')
            if detached: errors.append(f'{path.name}: DETACHED_ALPHA:{detached}')
            if result['image']['bounds'] != result['referenceImage']['bounds']: errors.append(f'{path.name}: BOUNDS_CHANGED')
            if path.name != f'{name}_{i:02}.png': errors.append('SEQUENCE_ERROR')
            errors.extend(f'{path.name}: {e}' for e in result['errors'])
            frames.append({'file':str(path.relative_to(ROOT)),'pixelSha256':result['image']['pixelSha256'],
                           'bounds':result['image']['bounds'],'anchorDrift':result['driftPixels'],
                           'protectedPixelChanges':protected,'alphaChangedPixels':alpha_changes,
                           'silhouetteSupportChangedPixels':support_changes,'detachedAlphaPixels':detached,
                           'appearanceDelta':delta(base,pixels), 'exactBaseReturn':is_base_return and pixels==base})
        if len({f['pixelSha256'] for f in frames}) != len(files): errors.append('DUPLICATE_FRAME')
        edges = [delta(a,b) for a,b in zip(decoded,decoded[1:])]
        if spec['clip']['loop']: edges.append(delta(decoded[-1],decoded[0]))
        # Conservative numeric discontinuity screen, not a natural-motion approval.
        if any(edge['meanAbsoluteChannelDelta'] > 2 for edge in edges): errors.append('CONTINUITY_DELTA_EXCEEDS_2')
        clips.append({'conceptId':spec['conceptId'],'action':spec['clip']['name'],
                      'automated':'FAIL' if errors else 'PASS','errors':errors,'frames':frames,
                      'continuityEdges':edges,'continuityThreshold':2,
                      'baseReturn':delta(decoded[-1],base), 'baseEntry':delta(base,decoded[0]),
                      'appearanceDrift':'Protected pixels unchanged; local motion measured; HUMAN_REVIEW_REQUIRED',
                      'naturalMotion':'HUMAN_REVIEW_REQUIRED','anchorApproval':'NOT_APPROVED'})
    result={'sessionId':'LUMA-ASSET-16','clips':clips,'newPngCount':sum(len(c['frames']) for c in clips),
            'newClipCount':len(clips),'automated':'FAIL' if any(c['errors'] for c in clips) else 'PASS',
            'productionEligible':False,'runtimeConnected':False,'gui':'DEFERRED_GUI'}
    print(json.dumps(result,indent=2))
    return 1 if result['automated']=='FAIL' else 0

if __name__=='__main__': raise SystemExit(main())
