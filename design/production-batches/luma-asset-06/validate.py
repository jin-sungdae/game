"""LUMA-ASSET-06 candidate audit; never writes the shared ledger or production."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests/assets')]
from validate_assets import png_errors
from test_moa_blink_v2 import rgba
from test_creature_followup import detached_pixels
BATCH=Path(__file__).resolve().parent

def audit(folder):
    spec=json.loads((folder/'candidate-clip.json').read_text())
    base=rgba(ROOT/spec['sourceBase']);bounds=[]
    errors=png_errors(ROOT/spec['sourceBase'],True,bounds)
    l,t,r,b=spec['movableRect'];action=spec['clip']['name'].lower()
    files=sorted((folder/'rigged'/action).glob('*.png'));frames=[];pixels=[]
    for i,path in enumerate(files):
        bb=[];e=png_errors(path,True,bb);data=rgba(path);pixels.append(data)
        protected=sum(data[n:n+4]!=base[n:n+4] for n in range(0,len(data),4) if not(l<(n//4)%256<r and t<(n//4)//256<b))
        if bb!=bounds:e.append('BOUNDS_DRIFT')
        if protected:e.append('PROTECTED_APPEARANCE_DRIFT')
        detached=detached_pixels(data)
        if detached:e.append('DETACHED_ALPHA')
        if path.name!=f'{action}_{i:02}.png':e.append('SEQUENCE')
        frames.append({'file':path.name,'errors':e,'bounds':bb,'pixelHash':hashlib.sha256(data).hexdigest(),'protectedPixelChanges':protected,'detachedAlphaPixels':detached,'anchorDriftPixels':0 if bb==bounds else None,'meanAbsoluteByteDifferenceFromBase':sum(abs(a-z) for a,z in zip(data,base))/len(base)})
    if len(files)!=8:errors.append('INCOMPLETE_CLIP_RIG_REJECTED_NO_RETRY')
    hashes=[f['pixelHash'] for f in frames]
    if len(set(hashes))!=len(hashes):errors.append('DUPLICATE_FRAMES')
    deltas=[sum(abs(a-b) for a,b in zip(pixels[i-1],pixels[i]))/len(base) for i in range(1,len(pixels))]
    if any(d<=0 or d>2 for d in deltas):errors.append('FRAME_CONTINUITY_THRESHOLD')
    boundary=max([sum(abs(a-b) for a,b in zip(p,base))/len(base) for p in pixels[:1]+pixels[-1:]],default=None)
    if boundary is not None and boundary>.15:errors.append('BASE_RETURN_DISCONTINUITY')
    errors+=sorted({e for f in frames for e in f['errors']})
    return {'sessionId':'LUMA-ASSET-06','automated':'PASS' if not errors else 'VALIDATION_FAILED','errors':errors,'frames':frames,'uniquePixelHashes':len(set(hashes)),'adjacentMeanAbsoluteByteDifferences':deltas,'maxEndpointDifferenceFromBase':boundary,'continuityScope':'Quantitative <=2 byte mean adjacent delta, <=0.15 endpoint delta; visual acceptance separate','appearance':'HUMAN_REVIEW_REQUIRED','naturalMotion':'HUMAN_REVIEW_REQUIRED','productionEligible':False,'nativeGui':'DEFERRED_GUI','repairIterations':3,'repairLimit':3,'sourceSha256':hashlib.sha256((ROOT/spec['sourceBase']).read_bytes()).hexdigest()}

if __name__=='__main__':
    for folder in sorted(BATCH.glob('M*/*')):
        result=audit(folder)
        (folder/'frame-validation.json').write_text(json.dumps(result,indent=2)+'\n')
        print(folder.relative_to(BATCH),result['automated'],len(result['frames']),result['errors'])
