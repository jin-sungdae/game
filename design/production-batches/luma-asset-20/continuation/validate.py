"""Session-scoped independent checks for eyelid and articulated pose candidates."""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[4]
SESSION=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
from visual_asset_inventory import candidate

def detached_alpha(alpha):
    remaining=set(np.flatnonzero(alpha).tolist()); sizes=[]
    while remaining:
        group=[remaining.pop()]
        for n in group:
            x,y=n%256,n//256
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    xx,yy=x+dx,y+dy;j=yy*256+xx
                    if 0<=xx<256 and 0<=yy<256 and j in remaining:
                        remaining.remove(j);group.append(j)
        sizes.append(len(group))
    return sum(sizes)-max(sizes,default=0)

def delta(a,b):
    return {'changedPixels':int(np.any(a!=b,axis=2).sum()),'meanAbsoluteRgbaDelta':float(np.abs(a.astype(float)-b).mean())}

results=[]
for meta_path in sorted(SESSION.glob('M*/*/candidate-clip.json')):
    meta=json.loads(meta_path.read_text());folder=meta_path.parent
    rig=json.loads((folder/'rig-evidence.json').read_text())
    base_path=ROOT/meta['sourceBase'];base=np.array(Image.open(base_path))
    frames=sorted((ROOT/meta['framesDirectory']).glob('*.png'))
    errors=[];evidence=[];decoded=[];hashes=[]
    if len(frames)!=8:errors.append('FRAME_COUNT')
    y,x=np.mgrid[:256,:256];allowed=np.zeros((256,256),dtype=bool)
    for p in meta['parts']:
        allowed|=((x-p['x'])/(p['rx']+2))**2+((y-p['y'])/(p['ry']+2))**2<1
    for eye in meta['eyes']:
        u=(x-eye['x'])*np.cos(eye['angle'])+(y-eye['y'])*np.sin(eye['angle'])
        v=-(x-eye['x'])*np.sin(eye['angle'])+(y-eye['y'])*np.cos(eye['angle'])
        allowed|=(u/eye['rx'])**2+(v/eye['ry'])**2<1
    for i,f in enumerate(frames):
        im=Image.open(f);a=np.array(im);decoded.append(a)
        check=candidate(f,base_path);fail=list(check['errors'])
        if im.mode!='RGBA' or im.size!=(256,256):fail.append('FORMAT')
        changed=np.any(a!=base,axis=2);outside=int((changed & ~allowed).sum())
        if outside:fail.append('OUTSIDE_PART_MASK')
        detached=detached_alpha(a[:,:,3])
        if detached:fail.append('DETACHED_ALPHA')
        if np.any(a[0,:,3]) or np.any(a[-1,:,3]) or np.any(a[:,0,3]) or np.any(a[:,-1,3]):fail.append('CANVAS_ALPHA')
        digest=hashlib.sha256(im.tobytes()).hexdigest();hashes.append(digest)
        if digest!=rig['frames'][i]['pixelSha256']:fail.append('PIXEL_HASH')
        if i<7 and not np.any(changed):fail.append('NO_PART_MOTION')
        if i==7 and np.any(changed):fail.append('BASE_RETURN')
        evidence.append({'file':str(f.relative_to(ROOT)),'errors':fail,'bounds':check['image']['bounds'],
            'anchorDriftPixels':check['driftPixels'],'pixelSha256':digest,'outsidePartMaskChanges':outside,
            'detachedAlphaPixels':detached,'changedPixels':int(changed.sum()),
            'alphaChangedPixels':int((a[:,:,3]!=base[:,:,3]).sum())})
        errors+=fail
    if len(set(hashes))!=8:errors.append('DUPLICATE_FRAMES')
    transitions=[delta(a,b) for a,b in zip([base]+decoded,decoded+[base])]
    if any(t['changedPixels']>=7000 or t['meanAbsoluteRgbaDelta']>=3 for t in transitions):errors.append('CONTINUITY_ENVELOPE')
    key=candidate(folder/'keypose.png',base_path);errors+=key['errors']
    if not np.array_equal(np.array(Image.open(folder/'keypose.png')),decoded[3]):errors.append('KEYPOSE_MISMATCH')
    report={'conceptId':meta['conceptId'],'action':meta['clip']['name'],'automated':'FAIL' if errors else 'PASS',
        'errors':errors,'frames':evidence,'baseEntryAndReturnContinuity':transitions,'exactBaseReturn':np.array_equal(decoded[-1],base),
        'uniquePixelHashes':len(set(hashes)),'appearanceReview':'HUMAN_REVIEW_REQUIRED','naturalMotion':'HUMAN_REVIEW_REQUIRED',
        'scope':'Eye-only BLINK legitimately preserves Alpha; body pose candidates require local RGBA changes. Exact BASE endpoint allowed, no duplicate frames. Natural motion/Species acceptance not inferred.',
        'productionEligible':False,'runtimeConnected':False,'gui':'DEFERRED_GUI'}
    (folder/'frame-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    results.append({k:report[k] for k in ['conceptId','action','automated','errors']})
(SESSION/'validation.json').write_text(json.dumps({'clips':results,'productionEligible':False},indent=2)+'\n')
print(json.dumps(results,indent=2));raise SystemExit(any(r['errors'] for r in results))
