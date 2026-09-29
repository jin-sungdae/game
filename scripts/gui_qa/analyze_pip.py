"""Offline measurements of actual PIP ScreenCaptureKit + native AX evidence."""
import argparse,collections,csv,hashlib,json,re,statistics,subprocess as sp
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();root=a.root
cap=json.loads((root/'playback-frames/frames.json').read_text())['frames']
events=json.loads((root/'events.json').read_text());cut=events[0]['time']-.3
rows=[json.loads(s) for s in (root/'frame-trace.jsonl').read_text().splitlines()];rows=[r for r in rows if cap[0]['wallTime']<=r['after']<cut]
segments=[];trace=[];previous=None
for r in rows:
 m=re.fullmatch(r'PIP (IDLE|MOVE) frame (\d+) (animation|base)',r.get('label',''))
 if not m or not r['panels']:continue
 b=r['panels'][0];dt=r['after']-previous['after'] if previous else 0;dx=b['X']-previous['panels'][0]['X'] if previous else 0
 direction='RIGHT' if dx>0 else 'LEFT' if dx<0 else 'STILL'
 trace.append({'timestamp':r['after'],'velocityXFromPanelPtPerSec':dx/dt if dt else 0,'movementDirection':direction,'animationState':m[1],'frame':int(m[2]),'nativeFacing':-1,'rendererScaleX':-1,'expectedFacing':1 if dx>0 else -1 if dx<0 else '', 'panelX':b['X'],'panelY':b['Y'],'sampleDt':dt})
 previous=r
 if not segments or segments[-1]['state']!=m[1]:segments.append({'state':m[1],'start':r['after'],'end':r['after'],'frames':[],'sources':[]})
 s=segments[-1];s['end']=r['after']
 if m[3] not in s['sources']:s['sources'].append(m[3])
 if not s['frames'] or s['frames'][-1]['frame']!=int(m[2]):s['frames'].append({'frame':int(m[2]),'time':r['after']})
with (root/'facing-trace.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=trace[0].keys());w.writeheader();w.writerows(trace)
bounds=[];cache={}
for f in cap:
 if f['wallTime']>=cut:continue
 path=root/'playback-frames'/f['file'];h=hashlib.sha256(path.read_bytes()).hexdigest()
 if h not in cache:
  data=sp.check_output(['ffmpeg','-v','error','-i',str(path),'-f','rawvideo','-pix_fmt','rgba','-']);w,height=f['width'],f['height']
  pts=[(x,y) for y in range(height) for x in range(w) if max(data[(y*w+x)*4:(y*w+x)*4+3])>40]
  xs,ys=zip(*pts);cache[h]=[min(xs),min(ys),max(xs),max(ys)]
 b=cache[h];bounds.append({'file':f['file'],'time':f['wallTime'],'bounds':b,'center':(b[0]+b[2])/2,'bottom':b[3]})
cycles={};order={}
for state,count in [('IDLE',4),('MOVE',8)]:
 cs=[];issues=[];seen=set()
 for s in segments:
  if s['state']!=state:continue
  seq=s['frames'];seen.update(x['frame'] for x in seq)
  starts=[x['time'] for x in seq if x['frame']==1];cs.extend((y-x)*1000 for x,y in zip(starts,starts[1:]))
  for x,y in zip(seq,seq[1:]):
   if y['frame']!=x['frame']%count+1:issues.append({'from':x,'to':y,'note':'Observed label skipped; source timestamps retained, not claimed as complete frame delivery.'})
 cycles[state]={'samplesMs':cs,'medianMs':statistics.median(cs) if cs else None};order[state]={'seen':sorted(seen),'observationGaps':issues}
result={'scope':'Actual ambient interval before mouse interaction; battle squash/base suppression reported separately','captureWallSeconds':cap[-1]['wallTime']-cap[0]['wallTime'],'ambientSeconds':cut-cap[0]['wallTime'],'centerDriftPt':(max(b['center'] for b in bounds)-min(b['center'] for b in bounds))/2,'bottomDriftPt':(max(b['bottom'] for b in bounds)-min(b['bottom'] for b in bounds))/2,'clipping':any(b['bounds'][0]==0 or b['bounds'][1]==0 or b['bounds'][2]==191 or b['bounds'][3]==207 for b in bounds),'panelSizes':sorted(set((r['panels'][0]['Width'],r['panels'][0]['Height']) for r in rows if r['panels'])),'canvasAXSizes':sorted(set(tuple(r['image']['AXSize']) for r in rows if r.get('image',{}).get('AXSize'))),'fallback':any('base' in s['sources'] for s in segments),'cycles':cycles,'frameOrder':order,'segments':segments,'pixelBounds':bounds,'facing':{'native':'All Roaming log entries report -1; held between existing state-change log entries. Not a newly instrumented per-frame field.','renderer':'scaleX(-1) from unchanged directionScale(nativeFacing), corroborated by LEFT-looking recorded pixels; no DOM transform probe injected.','velocity':'Signed velocity derived from sequential rounded CGWindow positions/time; quantized, not exact physics velocity.','RIGHT':'KNOWN_ISSUE expected+1 actual-1','LEFT':'PASS expected-1 actual-1'},'measurement':'All pixels RGB max>40 on black ScreenCaptureKit background; physical pixels /2 = pt. AX reads and panel snapshots are sequential. No alpha-exact framebuffer claim.'}
(root/'pip-analysis.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['segments','pixelBounds','frameOrder','cycles']},indent=2))
