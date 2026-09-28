from pathlib import Path
import sys,json,hashlib,struct,zlib,collections
repo=Path(__file__).resolve().parents[3];sys.path.insert(0,str(repo/'tests/assets'))
from test_moa_blink_v2 import rgba
source=repo/'public/assets/creatures/moa/stage01/base.png';out=Path(__file__).parent;raw=rgba(source)
def bounds(points):
 xs=[p[0] for p in points];ys=[p[1] for p in points];a,b,c,d=min(xs),min(ys),max(xs),max(ys)
 return {'x':a,'y':b,'x_max_inclusive':c,'y_max_inclusive':d,'width':c-a+1,'height':d-b+1,'center':[(a+c)/2,(b+d)/2]}
def expand(b,n):return bounds([(b['x']-n,b['y']-n),(b['x_max_inclusive']+n,b['y_max_inclusive']+n)])
def components(s):
 s=set(s);result=[]
 while s:
  comp={s.pop()};q=list(comp)
  while q:
   x,y=q.pop()
   for n in [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]:
    if n in s:s.remove(n);comp.add(n);q.append(n)
  result.append(comp)
 return sorted(result,key=len,reverse=True)
def pixel(x,y):return raw[(y*256+x)*4:(y*256+x)*4+4]
report={'source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'coordinateConvention':'Image left/right, top-left (0,0), pixel-index extrema inclusive; center is midpoint of extreme pixel indices, not an anatomical label or intensity centroid.','method':'Within broad visually identified face ROIs select alpha>=128, max(RGB)<230, R-G<35; take largest 4-connected component. Enclosed white highlights are included by the bounding rectangle. Thresholds operationally define raster edge; no authored eye mask exists. Bright exterior antialias rim is conservatively covered by one-pixel expansion, not claimed as exact semantic segmentation. Safe rectangle adds one more pixel and is a work ROI, not a rectangular repaint instruction.','eyes':{}}
overlay=bytearray(raw)
def put(x,y,color):overlay[(y*256+x)*4:(y*256+x)*4+4]=bytes(color)
for name,roi,color in [('LEFT_EYE',(185,130,218,170),(255,0,255,255)),('RIGHT_EYE',(225,130,240,160),(0,170,255,255))]:
 candidates=[]
 for y in range(roi[1],roi[3]):
  for x in range(roi[0],roi[2]):
   r,g,b,a=pixel(x,y)
   if a>=128 and max(r,g,b)<230 and r-g<35:candidates.append((x,y))
 comp=components(candidates)[0];core=bounds(comp);dark=bounds([(x,y) for x,y in comp if max(pixel(x,y)[:3])<110])
 full=expand(core,1);safe=expand(core,2)
 report['eyes'][name]={'searchROIExclusive':roi,'segmentedIrisAndBoundary':core,'darkRGBUnder110':dark,'fullEyeIncludingBrightRimConservative':full,'blinkSafeRegionProposed':safe,'segmentedPixelCount':len(comp),'rowExtents':{str(y):[min(x for x,yy in comp if yy==y),max(x for x,yy in comp if yy==y)] for y in sorted({y for x,y in comp})}}
 # Overlay contains only full-eye box and center marker, no repaint or safe-region shading.
 for x in range(full['x'],full['x_max_inclusive']+1):put(x,full['y'],color);put(x,full['y_max_inclusive'],color)
 for y in range(full['y'],full['y_max_inclusive']+1):put(full['x'],y,color);put(full['x_max_inclusive'],y,color)
 cx,cy=full['center']
 for x in {int(cx),int(cx+.5)}:
  for y in {int(cy),int(cy+.5)}:put(x,y,color)
def png(path,pixels):
 def chunk(k,v):return struct.pack('>I',len(v))+k+v+struct.pack('>I',zlib.crc32(k+v)&0xffffffff)
 scan=b''.join(b'\0'+pixels[y*1024:(y+1)*1024] for y in range(256))
 path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',256,256,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(scan))+chunk(b'IEND',b''))
png(out/'eye-box-overlay.png',overlay)
(out/'measurement.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:{n:v for n,v in x.items() if n not in ['rowExtents']} for k,x in report['eyes'].items()},indent=2))
