from pathlib import Path
from PIL import Image
import sys,json,hashlib
root=Path(__file__).resolve().parents[4];sys.path.insert(0,str(root/'scripts'));import validate_assets as v
batch=root/'design/production-batches/monsters/batch06';rows=[]
for code in ['M053', 'M059', 'M060']:
 p=batch/code;base=Image.open(p/'base-v2.png');bb=[];v.png_errors(p/'base-v2.png',True,bb,[]);frames=sorted((p/'rigged/idle').glob('*.png'));decoded=[];results=[];hashes=[]
 for f in frames:
  bounds=[];errors=v.png_errors(f,True,bounds,hashes);im=Image.open(f);data=list(im.getdata());decoded.append(data)
  if bounds!=bb:errors.append('BOUNDS_DRIFT')
  if any(data[y*256+x][3] for y in range(256) for x in range(256) if x in (0,255) or y in (0,255)):errors.append('CANVAS_BORDER_ALPHA')
  # Record alpha changes separately; fixed-region preservation is checked by the rig.
  base_data=list(base.getdata());alpha_changes=sum(a[3]!=b[3] for a,b in zip(data,base_data))
  results.append({'file':str(f.relative_to(root)),'bounds':bounds,'anchorDriftPixels':{'bottom':bounds[3]-bb[3],'boundsCenterX':(bounds[0]+bounds[2]-bb[0]-bb[2])/2},'alphaChanges':alpha_changes,'errors':errors})
 diffs=[sum(a!=b for a,b in zip(decoded[i],decoded[(i+1)%len(decoded)])) for i in range(len(decoded))]
 report={'conceptId':code,'automated':'PASS' if all(not x['errors'] for x in results) and len(set(hashes))==6 and all(diffs) else 'FAIL','frames':results,'uniquePixelHashes':len(set(hashes)),'adjacentChangedPixelsIncludingLoop':diffs,'naturalMotionReview':'NOT_VERIFIED','artworkApproval':'HUMAN_REVIEW_REQUIRED','nativeGui':'NOT_VERIFIED','productionEligible':False}
 (p/'frame-validation.json').write_text(json.dumps(report,indent=2)+'\n');rows.append(report);print(code,report['automated'],'alpha',set(x['alphaChanges'] for x in results),'loop',diffs)
 assert report['automated']=='PASS'
