from pathlib import Path
from PIL import Image
import json,hashlib
root=Path('design/production-batches/monsters/idle-revision/M005')
im=Image.open(root/'keypose-v2-256.png'); pixels=list(im.getdata());a=[p[3] for p in pixels];unseen={i for i,v in enumerate(a) if v};components=[]
while unseen:
 seed=unseen.pop();todo=[seed];part=[seed]
 while todo:
  i=todo.pop();x,y=i%256,i//256
  for dx in [-1,0,1]:
   for dy in [-1,0,1]:
    xx,yy=x+dx,y+dy;j=yy*256+xx
    if 0<=xx<256 and 0<=yy<256 and j in unseen:unseen.remove(j);todo.append(j);part.append(j)
 components.append(part)
components.sort(key=len,reverse=True);residue=[i for c in components[1:] for i in c]
assert len(residue)==17 and max(a[i] for i in residue)==1
out=pixels.copy()
for i in residue:out[i]=(*out[i][:3],0)
assert all(out[i]==pixels[i] for i in components[0])
clean=Image.new('RGBA',(256,256));clean.putdata(out);clean.save(root/'keypose-clean.png')
# Align the existing bottom-center canvas convention by integer translation only.
bounds=clean.getbbox();base=Image.open('design/production-batches/monsters/batch01/M005/base-v2.png');reference=base.getbbox();dx=round((reference[0]+reference[2]-bounds[0]-bounds[2])/2);dy=reference[3]-bounds[3]
normalized=Image.new('RGBA',(256,256));normalized.paste(clean,(dx,dy));normalized.save(root/'keypose.png')
assert sum(p[3]>0 for p in normalized.getdata())==len(components[0])
json.dump({'designDirection':'APPROVED','productionArtworkApproval':'PENDING','cleanupApprovedPixels':17,'changedAlphaPixels':len(residue),'bodyPixelChanges':0,'rgbChanges':0,'translation':[dx,dy],'boundsBefore':bounds,'boundsAfter':normalized.getbbox(),'baseBounds':reference,'anchor':{'x':0.5,'y':1},'source256Sha256':hashlib.sha256((root/'keypose-v2-256.png').read_bytes()).hexdigest(),'productionRegistered':False,'rejectedToolEdit':'alpha-tool-rejected.png','rejectionReason':'APPEARANCE_DRIFT'},open(root/'preparation.json','w'),indent=2)
print('bounds',bounds,'translation',dx,dy,'normalized',normalized.getbbox())
