"""Session-scoped candidate evidence; existing PNG/registration validators remain authoritative."""
from pathlib import Path
import sys,json,hashlib
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from visual_asset_inventory import candidate,inspect_png
HERE=Path(__file__).parent

def detached(a):
    mask=a[:,:,3]>0;seen=np.zeros(mask.shape,bool);sizes=[]
    for y,x in zip(*np.where(mask)):
        if seen[y,x]:continue
        stack=[(y,x)];seen[y,x]=True;n=0
        while stack:
            yy,xx=stack.pop();n+=1
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    ny,nx=yy+dy,xx+dx
                    if 0<=ny<256 and 0<=nx<256 and mask[ny,nx] and not seen[ny,nx]:seen[ny,nx]=True;stack.append((ny,nx))
        sizes.append(n)
    return sum(sizes)-max(sizes,default=0)

def validate():
    results=[]
    for meta in sorted(HERE.glob('M*/*/candidate-clip.json')):
        d=json.loads(meta.read_text());base=ROOT/d['sourceBase'];b=np.array(Image.open(base));rig=json.loads((meta.parent/'rig-evidence.json').read_text())
        frames=[];arrays=[];errors=[];basecheck=inspect_png(base)
        if basecheck['errors'] or detached(b):errors.append('BASE_INVALID')
        for p in sorted((meta.parent/'rigged').rglob('*.png')):
            a=np.array(Image.open(p));check=candidate(p,base);n=detached(a);arrays.append(a)
            evidence=next(r for r in rig['frames'] if r['file']==p.name)
            if check['errors'] or n or evidence['fixedRegionChanges'] or not evidence['alphaChangedPixels']:errors.append(p.name)
            frames.append(dict(file=p.name,errors=check['errors'],bounds=check['image']['bounds'],pixelHash=check['image']['pixelSha256'],anchorDrift=check['driftPixels'],detachedAlphaPixels=n,protectedChanges=evidence['fixedRegionChanges'],alphaChangedPixels=evidence['alphaChangedPixels'],changedPixels=evidence['changedPixels']))
        hashes=[x['pixelHash'] for x in frames]
        if len(frames)!=8 or len(set(hashes))!=8:errors.append('FRAME_COUNT_OR_HASH')
        continuity=[int(np.abs(a.astype(int)-b_.astype(int)).sum()) for a,b_ in zip(arrays,arrays[1:])]
        result=dict(automated='FAIL' if errors else 'PASS',errors=errors,sourceSha256=hashlib.sha256(base.read_bytes()).hexdigest(),frames=frames,uniquePixelHashes=len(set(hashes)),adjacentRgbaDifference=continuity,baseEntryRgbaDifference=int(np.abs(arrays[0].astype(int)-b.astype(int)).sum()),baseExitRgbaDifference=int(np.abs(arrays[-1].astype(int)-b.astype(int)).sum()),continuityScope='Measured only; no numeric threshold substitutes for natural-motion review',appearance='HUMAN_REVIEW_REQUIRED',naturalMotion='HUMAN_REVIEW_REQUIRED',gui='DEFERRED_GUI',productionEligible=False)
        (meta.parent/'frame-validation.json').write_text(json.dumps(result,indent=2)+'\n');results.append((d['conceptId'],d['clip']['name'],result['automated'],errors))
    print(json.dumps(results));return any(x[2]=='FAIL' for x in results)
if __name__=='__main__':sys.exit(validate())
