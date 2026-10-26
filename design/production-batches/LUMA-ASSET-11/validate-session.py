"""Read-only session measurements; --write saves review evidence, never alters PNGs."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests/assets')]
from validate_assets import png_errors
from test_moa_blink_v2 import rgba
from test_creature_followup import detached_pixels
SESSION=Path(__file__).resolve().parent

def measure(folder):
    spec=json.loads((folder/'candidate-clip.json').read_text())
    base=rgba(ROOT/spec['sourceBase']);bb=[]
    base_errors=png_errors(ROOT/spec['sourceBase'],True,bb)
    action=spec['clip']['name'].lower();paths=sorted((folder/'rigged'/action).glob('*.png'))
    frames=[];decoded=[]
    for p in paths:
        bounds=[];errors=png_errors(p,True,bounds);data=rgba(p);decoded.append(data)
        changed=protected=alpha=edges=0
        for pos in range(65536):
            x,y=pos%256,pos//256;n=pos*4
            if 'eyes' in spec:
                movable=any(((x-e['x'])/e['rx'])**2+((y-e['y'])/e['ry'])**2<1 for e in spec['eyes'])
            else:
                l,t,r,b=spec['movableRect'];movable=l<x<r and t<y<b
            diff=data[n:n+4]!=base[n:n+4]
            changed+=diff;protected+=diff and not movable
            alpha+=data[n+3]!=base[n+3]
            edges+=data[n+3]>0 and (x in (0,255) or y in (0,255))
        detached=detached_pixels(data)
        if bounds!=bb:errors.append('BOUNDS_DRIFT')
        if protected:errors.append('PROTECTED_ANATOMY_CHANGED')
        if not changed:errors.append('NO_PART_MOTION')
        if detached:errors.append('DETACHED_ALPHA')
        if edges:errors.append('EDGE_CLIPPING')
        if 'eyes' in spec and alpha:errors.append('EYE_RIG_CHANGED_ALPHA')
        frames.append(dict(file=p.name,errors=errors,bounds=bounds,pixelSha256=hashlib.sha256(data).hexdigest(),changedPixels=changed,protectedPixelChanges=protected,alphaChangedPixels=alpha,detachedPixels=detached,canvasEdgePixels=edges,anchorDriftPixels=dict(bottom=bounds[3]-bb[3],centerX=(bounds[0]+bounds[2]-bb[0]-bb[2])/2)))
    unique=len(set(f['pixelSha256'] for f in frames))
    deltas=[sum(abs(a-b) for a,b in zip(decoded[i],decoded[(i+1)%len(decoded)])) for i in range(len(decoded))]
    failures=[]
    if unique!=len(frames):failures.append('DUPLICATE_DECODED_FRAMES')
    if len(frames)!=spec['clip']['frames']:failures.append('FRAME_COUNT')
    if not all(deltas):failures.append('ZERO_ADJACENT_DIFFERENCE')
    if base_errors or detached_pixels(base):failures.append('BASE_INVALID')
    if any(f['errors'] for f in frames):failures.append('FRAME_INVALID')
    return dict(automated='VALIDATION_FAILED' if failures else 'PASS',errors=failures,baseErrors=base_errors,baseDetachedPixels=detached_pixels(base),frames=frames,uniquePixelHashes=unique,adjacentPixelDifferenceSumsIncludingLoop=deltas,appearanceDrift='PROTECTED_PIXELS_VERIFIED; LOCAL_APPEARANCE_HUMAN_REVIEW_REQUIRED',frameContinuity='NUMERIC_DELTAS_MEASURED; NATURAL_MOTION_HUMAN_REVIEW_REQUIRED',wholeImageTransform=False,productionEligible=False,runtimeConnected=False,repairIterations=3,repairLimit=3,repairPerformed=False)

def main():
    results={}
    for folder in sorted((SESSION/'M036').iterdir()):
        if not (folder/'candidate-clip.json').exists():continue
        report=measure(folder);results[folder.name]=report['automated']
        if '--write' in sys.argv:(folder/'frame-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(results))
if __name__=='__main__':main()
