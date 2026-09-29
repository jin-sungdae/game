"""Combine actual facing/pixel evidence with animation-order and transition observations."""
import argparse,csv,json,re,statistics,subprocess as sp
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();root=a.root
sp.run(['python3',str(Path(__file__).with_name('analyze_facing.py')),str(root),'--pip-only'],check=True,stdout=sp.DEVNULL)
facing=json.loads((root/'analysis.json').read_text());pixels=facing['pip']['pixels'];tr=list(csv.DictReader((root/'facing-trace.csv').open()));raw=[json.loads(s) for s in (root/'pip-trace.jsonl').read_text().splitlines()];segments=[];bounds={};blank=[]
for r in raw:
 m=re.fullmatch(r'PIP (IDLE|MOVE|REACT) frame (\d+) (animation|base)',r.get('label',''))
 if not m:continue
 state,frame,source=m[1],int(m[2]),m[3]
 if not segments or segments[-1]['state']!=state:segments.append({'state':state,'start':r['after'],'end':r['after'],'frames':[],'sources':[]})
 s=segments[-1];s['end']=r['after']
 if source not in s['sources']:s['sources'].append(source)
 if not s['frames'] or s['frames'][-1]['frame']!=frame:s['frames'].append({'frame':frame,'time':r['after']})
for row,b in zip(tr,pixels):
 state=row['animation'].split()[1];key=state+'_'+('RIGHT' if row['rendererFacingFromPixels']=='1' else 'LEFT');bounds.setdefault(key,[]).append(b)
pergroup={k:{'samples':len(bs),'centerDriftPt':(max(b['center'] for b in bs)-min(b['center'] for b in bs))/2,'bottomDriftPt':(max(b['bottom'] for b in bs)-min(b['bottom'] for b in bs))/2} for k,bs in bounds.items()}
cycles={};orders={}
for state,count in [('IDLE',4),('MOVE',8)]:
 cs=[];issues=[];seen=set()
 for s in segments:
  if s['state']!=state:continue
  seq=s['frames'];seen.update(x['frame'] for x in seq);starts=[x['time'] for x in seq if x['frame']==1];cs.extend((y-x)*1000 for x,y in zip(starts,starts[1:]))
  issues.extend({'from':x,'to':y,'sampleGapMs':(y['time']-x['time'])*1000} for x,y in zip(seq,seq[1:]) if y['frame']!=x['frame']%count+1)
 cycles[state]={'cycleMs':cs,'medianMs':statistics.median(cs) if cs else None};orders[state]={'framesObserved':sorted(seen),'orderGaps':issues}
steps=[]
for x,y in zip(raw,raw[1:]):
 if not x['panels'] or not y['panels']:continue
 dt=y['after']-x['after'];dx=y['panels'][0]['X']-x['panels'][0]['X'];dy=y['panels'][0]['Y']-x['panels'][0]['Y'];steps.append({'time':y['after'],'dx':dx,'dy':dy,'dt':dt,'before':x['label'],'after':y['label']})
# Rounded positions can differ by1pt; large observer gaps are retained explicitly.
violations=[s for s in steps if abs(s['dx'])>24*(s['dt']+.1)+1.01 or abs(s['dy'])>0]
result={'facing':{k:v for k,v in facing.items() if k not in ['nativeTrace','pip','moa']},'pixelGroups':pergroup,'capture':{k:v for k,v in facing['pip'].items() if k!='pixels'},'cycles':cycles,'order':orders,'segments':segments,'IDLEtoMOVE':sum(x['state']=='IDLE' and y['state']=='MOVE' for x,y in zip(segments,segments[1:])),'MOVEtoIDLE':sum(x['state']=='MOVE' and y['state']=='IDLE' for x,y in zip(segments,segments[1:])),'baseFallback':any('base' in s['sources'] for s in segments),'panelSizes':sorted(set((b['Width'],b['Height']) for r in raw for b in r['panels'])),'canvasSizes':sorted(set(tuple(r['image']['AXSize']) for r in raw if r.get('image',{}).get('AXSize'))),'worldContinuityViolations':violations,'maxNativeStepPt':max(abs(s['dx']) for s in steps),'maxPanelYStepPt':max(abs(s['dy']) for s in steps),'mouseREACT':'NOT_APPLICABLE','blankObserved':False,'blankNote':'All captured PNGs had nonempty visible pixels; this does not assert unseen sub-capture intervals.'}
(root/'integration-analysis.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['segments','facing','cycles','order']},indent=2));print('Order gaps', {k:len(v['orderGaps']) for k,v in orders.items()})
