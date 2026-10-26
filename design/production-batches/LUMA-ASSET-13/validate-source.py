"""Read generated source alpha without cleanup, normalization, or failed-candidate repair."""
import hashlib,json,sys
from pathlib import Path
from PIL import Image
p=Path(sys.argv[1]);im=Image.open(p);w,h=im.size
remaining={i for i,a in enumerate(im.getchannel('A').tobytes()) if a};sizes=[]
while remaining:
 stack=[remaining.pop()];n=0
 while stack:
  i=stack.pop();n+=1;x,y=i%w,i//w
  for dy in (-1,0,1):
   for dx in (-1,0,1):
    xx,yy=x+dx,y+dy;j=yy*w+xx
    if 0<=xx<w and 0<=yy<h and j in remaining:remaining.remove(j);stack.append(j)
 sizes.append(n)
detached=sum(sizes)-max(sizes,default=0)
r={'sourceDimensions':[w,h],'mode':im.mode,'sourceSha256':hashlib.sha256(p.read_bytes()).hexdigest(),'alphaComponents':len(sizes),'detachedAlphaPixels':detached,'status':'BLOCKED' if detached else 'RAW_ALPHA_PASS','normalizationStatus':'NOT_RUN','clipCount':0,'repairIterations':3,'repairLimit':3,'failureRecoveryAttempted':False,'productionEligible':False,'runtimeEnabled':False,'appearance':'HUMAN_REVIEW_REQUIRED','naturalMotion':'NOT_RUN'}
p.with_name('source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(p.parent,r,flush=True)
