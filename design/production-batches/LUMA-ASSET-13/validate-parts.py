"""Validate independent body-response candidates without repairing failed frames."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests/assets')]
from validate_assets import png_errors
from test_moa_blink_v2 import rgba
from test_creature_followup import detached_pixels
OUT=ROOT/'design/production-batches/LUMA-ASSET-13'
for p in sorted(OUT.glob('M*/*/candidate-clip.json')):
 spec=json.loads(p.read_text())
 if 'parts' not in spec:continue
 base=rgba(ROOT/spec['sourceBase']);bb=[];errors=png_errors(ROOT/spec['sourceBase'],True,bb)
 l,t,r,b=spec['movableRect'];action=spec['clip']['name'].lower();frames=[];decoded=[];hashes=[]
 for i,path in enumerate(sorted((p.parent/'rigged'/action).glob('*.png'))):
  bounds=[];err=png_errors(path,True,bounds,hashes);data=rgba(path);decoded.append(data)
  protected=sum(data[n:n+4]!=base[n:n+4] for n in range(0,len(data),4) if not(l<(n//4)%256<r and t<(n//4)//256<b))
  detached=detached_pixels(data);alpha=sum(a!=z for a,z in zip(base[3::4],data[3::4]))
  if bounds!=bb:err.append('BOUNDS_DRIFT')
  if protected:err.append('PROTECTED_ANATOMY_CHANGED')
  if detached:err.append('DETACHED_ALPHA')
  if not alpha:err.append('NO_SILHOUETTE_MOTION')
  if path.name!=f'{action}_{i:02}.png':err.append('SEQUENCE')
  frames.append({'file':path.name,'errors':err,'bounds':bounds,'pixelHash':hashlib.sha256(data).hexdigest(),'protectedPixelChanges':protected,'alphaChangedPixels':alpha,'detachedAlphaPixels':detached,'anchorDriftPixels':{'bottom':bounds[3]-bb[3],'boundsCenterX':(bounds[0]+bounds[2]-bb[0]-bb[2])/2}})
 deltas=[sum(abs(a-b) for a,b in zip(decoded[i],decoded[(i+1)%len(decoded)])) for i in range(len(decoded))]
 passed=not errors and len(frames)==spec['clip']['frames'] and len(set(hashes))==len(frames) and all(deltas) and all(not f['errors'] for f in frames)
 result={'automated':'PASS' if passed else 'VALIDATION_FAILED','frames':frames,'sourceSha256':hashlib.sha256((ROOT/spec['sourceBase']).read_bytes()).hexdigest(),'baseErrors':errors,'uniquePixelHashes':len(set(hashes)),'adjacentPixelDifferenceSumsIncludingLoop':deltas,'loopContract':'ONE_SHOT; preview loop is not approved','appearance':'HUMAN_REVIEW_REQUIRED','naturalMotion':'HUMAN_REVIEW_REQUIRED','nativeGui':'DEFERRED_GUI','productionEligible':False,'repairIterations':3,'repairLimit':3}
 (p.parent/'frame-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(spec['conceptId'],action,result['automated'],len(frames),flush=True)
