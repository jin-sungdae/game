"""Analyze real mouse REACT capture; AX timing is sampled, not GPU presentation timing."""
import argparse,json,re,statistics,hashlib,subprocess as sp
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();root=a.root
capture=json.loads((root/'playback-frames/frames.json').read_text())['frames'];rows=[json.loads(x) for x in (root/'frame-trace.jsonl').read_text().splitlines()];rows=[x for x in rows if capture[0]['wallTime']<=x['after']<=capture[-1]['wallTime']];segments=[]
for row in rows:
 m=re.fullmatch(r'MOA (IDLE|BLINK|MOVE|REACT) frame (\d+) (animation|base)',row['label'])
 if not m:continue
 state,frame,source=m[1],int(m[2]),m[3]
 if not segments or (segments[-1]['state'],segments[-1]['source'])!=(state,source):
  if segments:segments[-1]['end']=row['after']
  segments.append({'state':state,'source':source,'start':row['after'],'end':row['after'],'frames':[],'panels':[]})
 seg=segments[-1];seg['end']=row['after']
 if not seg['frames'] or seg['frames'][-1]['frame']!=frame:seg['frames'].append({'frame':frame,'time':row['after']})
 for b in row['panels']:
  if b not in seg['panels']:seg['panels'].append(b)
react=[];pixel_cache={}
for i,seg in enumerate(segments):
 if seg['state']!='REACT':continue
 item={**seg,'durationMs':(seg['end']-seg['start'])*1000,'before':segments[i-1]['state'] if i else None,'after':segments[i+1]['state'] if i+1<len(segments) else None}
 item['sequence']=[f['frame'] for f in seg['frames']];item['fullOrderPass']=item['sequence']==[1,2,3,4,5,6];item['panelStable']=len(seg['panels'])==1;bounds=[]
 for f in capture:
  if not seg['start']+.025<=f['wallTime']<=seg['end']-.025:continue
  file=root/'playback-frames'/f['file'];h=hashlib.sha256(file.read_bytes()).hexdigest()
  if h not in pixel_cache:
   w,height=f['width'],f['height'];data=sp.check_output(['ffmpeg','-v','error','-i',str(file),'-f','rawvideo','-pix_fmt','rgba','-']);ink=[(x,y) for y in range(60,height) for x in range(w) if max(data[(y*w+x)*4:(y*w+x)*4+3])>40];xs=[p[0] for p in ink];ys=[p[1] for p in ink];b=[min(xs),min(ys),max(xs),max(ys)];pixel_cache[h]={'file':f['file'],'bounds':b,'center':(b[0]+b[2])/2,'bottom':b[3],'clipped':b[0]==0 or b[2]==w-1 or b[1]==60 or b[3]==height-1}
  if pixel_cache[h] not in bounds:bounds.append(pixel_cache[h])
 item['pixels']=bounds
 if bounds:item.update(centerDriftPt=(max(b['center'] for b in bounds)-min(b['center'] for b in bounds))/2,bottomDriftPt=(max(b['bottom'] for b in bounds)-min(b['bottom'] for b in bounds))/2,clipping=any(b['clipped'] for b in bounds))
 react.append(item)
network=[]
def visit(n):
 label=n.get('AXDescription','')
 if label.startswith('LUMA_METADATA_AUDIT '):network.append(json.loads(label.split(' ',1)[1]))
 for c in n.get('children',[]):visit(c)
visit(json.loads((root/'runtime-ax.json').read_text()))
events=json.loads((root/'events.json').read_text())
for e in events:
 if 'before' in e:e['bondDelta']=e['after']['activeCompanion']['bond']-e['before']['activeCompanion']['bond']
 e['reactSegments']=[i for i,s in enumerate(react) if e.get('beforeTime',e.get('start',0))<=s['start']<=e.get('afterTime',e.get('end',0))+.5]
report={'captureSeconds':capture[-1]['pts']-capture[0]['pts'],'react':react,'medianCompleteReactMs':statistics.median([x['durationMs'] for x in react if x['fullOrderPass']]) if any(x['fullOrderPass'] for x in react) else None,'panelSizes':sorted(set((b['Width'],b['Height']) for r in rows for b in r['panels'])),'canvasSizes':sorted(set(tuple(r['image']['AXSize']) for r in rows if 'AXSize' in r['image'])),'network':network,'events':events,'segments':segments,'method':'20ms AX sampling + ScreenCaptureKit native192x208; silhouette RGB max>40 below y60; no mock. Sources01/06 identical; AX disambiguates them. React panel continuity excludes native mouse-down Dragging gesture.'}
(root/'react-analysis.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['react','events','segments','network']},indent=2));print('REACT sequences:',[(x['sequence'],x['durationMs'],x.get('centerDriftPt'),x.get('bottomDriftPt')) for x in react])
