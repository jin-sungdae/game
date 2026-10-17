"""Offline base normalization only. Preserve originals and all connected body pixels."""
from PIL import Image
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).parent
for stage in (4,5):
 p=ROOT/f'stage{stage:02}'
 source=Image.open(p/'source-base-v1.png').convert('RGBA')
 source.thumbnail((224,224),Image.Resampling.LANCZOS)
 im=Image.new('RGBA',(256,256));im.paste(source,((256-source.width)//2,240-source.height))
 im.save(p/'base-v1.png');data=list(im.getdata());seen=set();groups=[]
 for n,v in enumerate(data):
  if not v[3] or n in seen:continue
  q=[n];seen.add(n)
  for n in q:
   x,y=n%256,n//256
   for dy in (-1,0,1):
    for dx in (-1,0,1):
     xx,yy=x+dx,y+dy;j=yy*256+xx
     if 0<=xx<256 and 0<=yy<256 and data[j][3] and j not in seen:seen.add(j);q.append(j)
  groups.append(q)
 groups.sort(key=len,reverse=True);out=data.copy();removed=[];retained=[]
 for g in groups[1:]:
  maximum=max(data[n][3] for n in g)
  if maximum>=128:retained.append({'pixels':len(g),'maxAlpha':maximum});continue
  for n in g:out[n]=(*data[n][:3],0);removed.append([n%256,n//256,data[n][3]])
 assert all(out[n]==data[n] for n in groups[0])
 result=Image.new('RGBA',(256,256));result.putdata(out);result.save(p/'base-v2.png')
 report={'source':'source-base-v1.png','normalization':'uniform fit 224px into 256px canvas, bottom margin16px; not animation','beforeBounds':im.getbbox(),'afterBounds':result.getbbox(),'removedDisconnectedLowAlphaPixels':removed,'retainedDisconnectedComponents':retained,'connectedBodyPixelChanges':0,'bodyPixels':len(groups[0]),'repairIteration':1,'productionEligible':False,'gui':'NOT_VERIFIED','sha256':hashlib.sha256((p/'base-v2.png').read_bytes()).hexdigest()}
 (p/'base-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(stage,{k:v for k,v in report.items() if k!='removedDisconnectedLowAlphaPixels'},'removed',len(removed))
