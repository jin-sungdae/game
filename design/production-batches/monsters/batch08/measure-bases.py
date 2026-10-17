from pathlib import Path
from PIL import Image
import json,hashlib,sys
root=Path(__file__).resolve().parents[4];sys.path.insert(0,str(root/'scripts'));import validate_assets as validator
batch=root/'design/production-batches/monsters/batch08'
rows=[]
for code in [f'M{n:03}' for n in range(71,81)]:
 p=batch/code;source=Image.open(p/'source-base-v1.png');original=source.copy();source.thumbnail((224,224),Image.Resampling.LANCZOS)
 im=Image.new('RGBA',(256,256));im.paste(source,((256-source.width)//2,240-source.height));dest=p/'base-v1.png';im.save(dest)
 data=list(im.getdata());seen=set();groups=[]
 for i,v in enumerate(data):
  if not v[3] or i in seen:continue
  q=[i];seen.add(i)
  for n in q:
   x,y=n%256,n//256
   for dy in (-1,0,1):
    for dx in (-1,0,1):
     xx,yy=x+dx,y+dy;j=yy*256+xx
     if 0<=xx<256 and 0<=yy<256 and data[j][3] and j not in seen:seen.add(j);q.append(j)
  groups.append(q)
 groups.sort(key=len,reverse=True)
 bounds=[];hashes=[];errors=validator.png_errors(dest,True,bounds,hashes)
 a=original.getchannel('A');w,h=original.size;border=list(a.crop((0,0,w,1)).getdata())+list(a.crop((0,h-1,w,h)).getdata())+list(a.crop((0,0,1,h)).getdata())+list(a.crop((w-1,0,w,h)).getdata())
 row={'conceptId':code,'sourceSize':list(original.size),'mode':original.mode,'canvas':[256,256],'normalization':'uniform fit224 into256; bottom margin16; no crop','bounds':bounds,'pixelHash':hashes,'pngErrors':errors,'componentCount':len(groups),'detachedPixels':sum(map(len,groups[1:])),'detachedMaxAlpha':max([data[n][3] for g in groups[1:] for n in g],default=0),'sourceBorderMaxAlpha':max(border),'sourceSha256':hashlib.sha256((p/'source-base-v1.png').read_bytes()).hexdigest(),'productionEligible':False,'runtimeEnabled':False,'artworkReview':'REQUIRED','gui':'NOT_VERIFIED'}
 (p/'base-measurement.json').write_text(json.dumps(row,indent=2)+'\n');rows.append(row)
print(json.dumps(rows,indent=2))
