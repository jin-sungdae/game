"""Offline real native-window pixel/position measurements; never modifies renderer."""
import argparse,bisect,csv,datetime,hashlib,json,re,statistics,subprocess as sp
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();root=a.root
log=(root/'session/app.log').read_text();native=[]
for line in log.splitlines():
 m=re.search(r't=([\d.]+) .*?Some\(\((\w+), (-?\d+)\)\).*?pip=Some\(\(([\d.e+-]+), ([\d.e+-]+)\)\)',line)
 if m:native.append(dict(t=float(m[1]),state=m[2],facing=int(m[3]),x=float(m[4]),y=float(m[5])))
raw=[json.loads(s) for s in (root/'pip-trace.jsonl').read_text().splitlines()];raw=[r for r in raw if r['panels']]
base=max(datetime.datetime.fromisoformat(m).timestamp() for m in re.findall(r'^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d+) .*\[LUMA PANEL\]',log,re.M))
ts=[r['t'] for r in native]
def predicted(t):
 i=max(0,min(len(native)-2,bisect.bisect_right(ts,t)-1));x,y=native[i:i+2];f=max(0,min(1,(t-x['t'])/(y['t']-x['t'])));return x['x']+(y['x']-x['x'])*f
fits=[]
for k in range(-25,26):
 epoch=base+k/100;errors=[abs(predicted(r['after']-epoch)-(r['panels'][0]['X']+48)) for r in raw[::5]];fits.append((statistics.mean(errors),epoch))
error,epoch=min(fits)
result={'epochFit':{'epoch':epoch,'meanPositionResidualPt':error,'method':'Existing AppKit timestamp +/-250ms fitted to native x and CGWindow centers. Native t precision10ms; sequential sampling and integer CG rounding remain.'},'nativeTrace':native}
for name in ['pip','moa']:
 cap=json.loads((root/(name+'-frames')/'frames.json').read_text())['frames'];cache={};pixels=[]
 for f in cap:
  path=root/(name+'-frames')/f['file'];h=hashlib.sha256(path.read_bytes()).hexdigest()
  if h not in cache:
   data=sp.check_output(['ffmpeg','-v','error','-i',str(path),'-f','rawvideo','-pix_fmt','rgba','-']);w=192;hh=208;pts=[(x,y) for y in range(60,hh) for x in range(w) if max(data[(y*w+x)*4:(y*w+x)*4+3])>40]
   xs,ys=zip(*pts);b=[min(xs),min(ys),max(xs),max(ys)];upper=[x for x,y in pts if y<150];cache[h]={'bounds':b,'center':(b[0]+b[2])/2,'bottom':b[3],'upperCenter':statistics.mean(upper),'sha256':h}
  pixels.append(dict(file=f['file'],time=(f['before']+f['wallTime'])/2,**cache[h]))
 centers=[x['center'] for x in pixels];bottoms=[x['bottom'] for x in pixels]
 result[name]={'captureSeconds':cap[-1]['pts']-cap[0]['pts'],'frames':len(cap),'medianCaptureIntervalMs':statistics.median((y['pts']-x['pts'])*1000 for x,y in zip(cap,cap[1:])),'centerExcursionPt':(max(centers)-min(centers))/2,'bottomExcursionPt':(max(bottoms)-min(bottoms))/2,'centersPx':sorted(set(centers)),'bottomsPx':sorted(set(bottoms)),'clipping':any(x['bounds'][0]==0 or x['bounds'][2]==191 or x['bounds'][1]==60 or x['bounds'][3]==207 for x in pixels),'pixels':pixels}
 if name=='pip':pip=pixels
# Screen-captured PIP head/ears occupy the upper part of the sprite: inspect both
# representative PNGs; upper centroid gives independent LEFT/RIGHT classification.
tr=[];times=[r['after'] for r in raw];segments=[]
for pix in pip:
 idx=min(range(len(raw)),key=lambda i:abs(raw[i]['after']-pix['time']));r=raw[idx];prev=raw[max(0,idx-4)];dt=r['after']-prev['after'];b=r['panels'][0];vx=(b['X']-prev['panels'][0]['X'])/dt if dt else 0
 n=native[max(0,bisect.bisect_right(ts,pix['time']-epoch)-1)];flip=1 if pix['upperCenter']>96 else -1
 direction='RIGHT' if vx>3 else 'LEFT' if vx < -3 else 'STILL';nearChange=any(abs(pix['time']-epoch-x['t'])<.15 for i,x in enumerate(native) if i and x['facing']!=native[i-1]['facing'])
 row={'timestamp':pix['time'],'nativeTime':pix['time']-epoch,'vxPanelPtPerSec':vx,'panelX':b['X'],'panelY':b['Y'],'nativeXAtLastLog':n['x'],'nativeYAtLastLog':n['y'],'nativeFacing':n['facing'],'rendererFacingFromPixels':flip,'rendererScaleXFromContract':flip,'direction':direction,'animation':r['label'],'frameFile':pix['file'],'nearFacingTransition150ms':nearChange};tr.append(row)
 if direction!='STILL':
  if not segments or segments[-1]['direction']!=direction:segments.append({'direction':direction,'start':pix['time'],'end':pix['time'],'samples':0})
  segments[-1]['end']=pix['time'];segments[-1]['samples']+=1
with (root/'facing-trace.csv').open('w') as f:w=csv.DictWriter(f,fieldnames=tr[0].keys());w.writeheader();w.writerows(tr)
result['movementSegments']=segments;result['stableMovingSamples']=sum(r['direction']!='STILL' and not r['nearFacingTransition150ms'] for r in tr)
result['facingMismatches']=[r for r in tr if r['direction']!='STILL' and not r['nearFacingTransition150ms'] and (r['nativeFacing']!=(1 if r['direction']=='RIGHT' else -1) or r['nativeFacing']!=r['rendererFacingFromPixels'])]
result['note']='Base renderer on latest main, PR49 animation NOT_SUPPLIED. Pixel centroid classification independently reviewed in LEFT/RIGHT representative captures. Nominal flip maps source RIGHT using unchanged renderer; no DOM probe. Velocities are rounded CGWindow displacement, not injected physics telemetry.'
(root/'analysis.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:({i:j for i,j in v.items() if i!='pixels'} if k in ['pip','moa'] else v) for k,v in result.items() if k not in ['nativeTrace','facingMismatches']},indent=2));print('mismatches',len(result['facingMismatches']))
