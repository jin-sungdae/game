"""QA-only visible-anatomy annotations and exact alpha measurements. Never writes assets.
Semantic polygons are manual pixel-grid annotations, NOT inferred hidden limb anatomy.
Run from any directory: python3 docs/evidence/moa-move-anatomy/measure.py
"""
from pathlib import Path
import sys,json,hashlib,struct,zlib
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'tests/assets'))
from test_moa_blink_v2 import rgba
SOURCE=ROOT/'public/assets/creatures/moa/stage01/base.png'
original=SOURCE.read_bytes();pixels=rgba(SOURCE)
# Boundary polygons are QA annotations of visible color/occlusion seams, not rig masks.
regions={
 'HEAD_FACE':[(128,151),(133,126),(144,111),(165,101),(180,83),(188,103),(210,93),(216,88),(218,103),(233,112),(241,131),(246,163),(243,174),(224,184),(188,188),(154,192),(154,183),(137,187),(144,177),(128,178),(138,168),(128,163)],
 'HEAD_CROWN':[(90,56),(110,51),(131,55),(161,67),(180,91),(180,71),(196,27),(204,28),(218,50),(232,78),(225,98),(208,106),(188,103),(182,111),(161,104),(140,101),(117,87)],
 'BODY_VISIBLE':[(118,181),(139,175),(158,185),(179,199),(184,216),(169,230),(142,233),(126,222),(114,210)],
 'FRONT_LEG_NEAR':[(151,195),(167,198),(181,208),(193,208),(202,216),(208,235),(205,245),(197,249),(178,249),(165,242),(159,231),(147,218),(145,207)],
 'FRONT_LEG_FAR':[(208,207),(221,207),(221,218),(215,229),(210,238),(205,240),(201,228),(202,218)],
 'REAR_LEG_NEAR':[(112,181),(132,181),(144,190),(146,210),(137,222),(127,227),(125,235),(120,243),(104,246),(95,241),(92,229),(94,219),(94,204),(101,190)],
 'REAR_LEG_FAR':[(129,219),(144,224),(154,226),(160,232),(157,241),(143,243),(132,237),(126,229)],
 'TAIL':[(95,93),(111,96),(127,107),(137,122),(141,140),(135,157),(140,169),(128,177),(114,177),(101,187),(98,211),(85,214),(75,208),(68,198),(65,187),(59,197),(53,180),(39,177),(42,171),(19,170),(12,157),(23,143),(43,133),(65,123),(65,115),(80,104)],
}
# Paw ROIs describe visible distal portions only; their proximal cut is annotated.
paws={'FRONT_PAW_NEAR':[166,229,207,247],'FRONT_PAW_FAR':[205,222,215,238],'REAR_PAW_NEAR':[93,225,126,243],'REAR_PAW_FAR':[131,230,157,241]}
safe={
 'BODY_INTERIOR':[(138,190),(147,191),(153,197),(149,206),(151,213),(143,220),(136,215),(136,204)],
 'FRONT_PAW_NEAR_INTERIOR':[(176,232),(193,232),(198,237),(194,241),(182,240)],
 'FRONT_PAW_FAR_INTERIOR':[(207,224),(211,224),(210,229),(207,231)],
 'REAR_PAW_NEAR_INTERIOR':[(103,227),(115,227),(120,231),(117,236),(105,237),(100,234)],
 'REAR_PAW_FAR_INTERIOR':[(138,232),(150,233),(153,235),(148,237),(140,237)],
}
def inside(x,y,poly):
 yes=False
 for (ax,ay),(bx,by) in zip(poly,poly[1:]+poly[:1]):
  if (ay>y)!=(by>y) and x<(bx-ax)*(y-ay)/(by-ay)+ax:yes=not yes
 return yes
def box(points):
 xs=[p[0] for p in points];ys=[p[1] for p in points];lo,top,hi,bottom=min(xs),min(ys),max(xs),max(ys)
 return dict(x_min=lo,y_min=top,x_max=hi,y_max=bottom,width=hi-lo+1,height=bottom-top+1,center_x=(lo+hi)/2,center_y=(top+bottom)/2)
def selected(poly,threshold):return [(x,y) for y in range(256) for x in range(256) if pixels[(y*256+x)*4+3]>=threshold and inside(x+.5,y+.5,poly)]
def runs(xs):
 out=[]
 for x in xs:
  if not out or x>out[-1][1]+1:out.append([x,x])
  else:out[-1][1]=x
 return out
def contact(points):
 y=max(p[1] for p in points);return {'y':y,'x_runs_inclusive':runs(sorted(x for x,yy in points if yy==y))}
measurements={}
for name,poly in regions.items():
 measurements[name]={'polygon':poly,'visible_alpha128':box(selected(poly,128)),'alpha_nonzero':box(selected(poly,1)),'boundary':'manually annotated visible seam; hidden anatomy not recoverable'}
headpoints=selected(regions['HEAD_FACE'],128)+selected(regions['HEAD_CROWN'],128)
measurements['HEAD_WITH_CROWN']={'visible_alpha128':box(headpoints),'includes':['HEAD_FACE','HEAD_CROWN']}
for name,(l,t,r,b) in paws.items():
 pts=[(x,y) for y in range(t,b+1) for x in range(l,r+1) if pixels[(y*256+x)*4+3]>=128]
 measurements[name]={'visible_alpha128':box(pts),'annotation_roi_inclusive':[l,t,r,b],'local_bottom':contact(pts),'boundary':'manual distal-paw ROI; not an independent anatomical layer'}
ground={str(a):contact([(x,y) for y in range(256) for x in range(256) if pixels[(y*256+x)*4+3]>=a]) for a in [1,128,250]}
report={'source':str(SOURCE.relative_to(ROOT)),'source_sha256':hashlib.sha256(original).hexdigest(),'canvas':[256,256],'coordinates':'origin top-left; x rightward, y downward; min/max inclusive; centers are bounding-box midpoints, NOT center of mass','method':'Manual semantic polygon annotation on 4x nearest-neighbor pixel grid, intersected with actual decoded alpha>=128. Alpha>0 also reported. Exact mask measurements do not imply uniquely determined anatomy seams.','regions':measurements,'ground_baseline_by_alpha_threshold':ground,'safe_deformation_proposals':{name:{'polygon':poly,'bounds':box(selected(poly,128)),'scope':'interior-only conservative proposal; not approved limb translation envelope or rig mask'} for name,poly in safe.items()}}
(HERE/'measurements.json').write_text(json.dumps(report,indent=2)+'\n')
def png(path,buf):
 def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
 raw=b''.join(b'\0'+buf[y*1024:(y+1)*1024] for y in range(256));path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',256,256,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b''))
colors=[(255,65,65),(255,165,30),(30,200,255),(255,70,210),(180,90,255),(30,255,150),(210,255,30),(100,140,255)]
def overlay(name,entries):
 buf=bytearray(pixels)
 def dot(x,y,c):
  if 0<=x<256 and 0<=y<256:buf[(y*256+x)*4:(y*256+x)*4+4]=bytes((*c,255))
 for n,(label,b) in enumerate(entries):
  c=colors[n%len(colors)];l,t,r,bottom=[b[k] for k in ['x_min','y_min','x_max','y_max']]
  for x in range(l,r+1):dot(x,t,c);dot(x,bottom,c)
  for y in range(t,bottom+1):dot(l,y,c);dot(r,y,c)
  cx,cy=round(b['center_x']),round(b['center_y'])
  for d in range(-2,3):dot(cx+d,cy,c);dot(cx,cy+d,c)
 for x in range(256):
  if x%4<2:dot(x,247,(255,255,255))
 png(HERE/name,buf)
 return [{'label':n,'rgb':list(colors[i%len(colors)])} for i,(n,b) in enumerate(entries)]
legend=overlay('anatomy-overlay.png',[(n,v['visible_alpha128']) for n,v in measurements.items() if n in regions])
plegend=overlay('paw-overlay.png',[(n,measurements[n]['visible_alpha128']) for n in paws])
slegend=overlay('safe-regions-overlay.png',[(n,v['bounds']) for n,v in report['safe_deformation_proposals'].items()])
(HERE/'overlay-legend.json').write_text(json.dumps({'anatomy':legend,'paws':plegend,'safe':slegend},indent=2)+'\n')
assert SOURCE.read_bytes()==original
for name,data in measurements.items():print(name,data['visible_alpha128'])
print('GROUND',ground)
