"""Analyze real autonomous MOVE recording; never substitutes mock coordinates for native data."""
import argparse,json,re,hashlib,subprocess as sp,statistics,collections
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();root=a.root
capture=json.loads((root/'playback-frames/frames.json').read_text())['frames']
raw=[json.loads(s) for s in (root/'frame-trace.jsonl').read_text().splitlines()]
rows=[r for r in raw if capture[0]['wallTime']<=r['after']<=capture[-1]['wallTime']]
segments=[]
for r in rows:
 m=re.fullmatch(r'MOA (IDLE|BLINK|MOVE|REACT) frame (\d+) (animation|base)',str(r.get('label','')))
 if not m:continue
 state,frame,source=m[1],int(m[2]),m[3]
 if not segments or segments[-1]['state']!=state:segments.append({'state':state,'start':r['after'],'end':r['after'],'samples':0,'frames':[],'panelStart':r['panels'][0] if r['panels'] else None,'panelEnd':None,'sourceKinds':[]})
 s=segments[-1];s['end']=r['after'];s['samples']+=1;s['panelEnd']=r['panels'][0] if r['panels'] else None
 if source not in s['sourceKinds']:s['sourceKinds'].append(source)
 if not s['frames'] or s['frames'][-1]['frame']!=frame:s['frames'].append({'frame':frame,'time':r['after']})
move=[];cycles=[];errors=[];directions=set()
for s in segments:
 if s['state']!='MOVE':continue
 s['seconds']=s['end']-s['start'];delta=s['panelEnd']['X']-s['panelStart']['X'] if s['panelStart'] and s['panelEnd'] else 0;s['deltaX']=delta;s['direction']='RIGHT' if delta>0 else 'LEFT' if delta<0 else 'STILL';directions.add(s['direction'])
 seq=s['frames'];bad=[(x,y) for x,y in zip(seq,seq[1:]) if y['frame']!=x['frame']%8+1];errors+=bad;s['orderErrors']=bad
 starts=[r['time'] for r in seq if r['frame']==1];s['cyclesMs']=[(y-x)*1000 for x,y in zip(starts,starts[1:])];cycles+=s['cyclesMs'];move.append(s)
# Native panel displacement at sampling boundaries: report raw values and speed-bound exceedances.
steps=[];violations=[];sizes=set();canvas=set();offsets=[]
for r in rows:
 for b in r['panels']:sizes.add((b['Width'],b['Height']))
 im=r.get('image',{});sz=im.get('AXSize');pos=im.get('AXPosition')
 if sz:canvas.add(tuple(sz))
 if pos and r['panels']:offsets.append((pos[0]-r['panels'][0]['X'],pos[1]-r['panels'][0]['Y']))
for x,y in zip(rows,rows[1:]):
 if not x['panels'] or not y['panels']:continue
 dt=y['after']-x['after'];dx=y['panels'][0]['X']-x['panels'][0]['X'];dy=y['panels'][0]['Y']-x['panels'][0]['Y']
 if dx or dy:
  step={'time':y['after'],'dt':dt,'dx':dx,'dy':dy,'before':x['label'],'after':y['label']};steps.append(step)
  # Existing native40pt/s ground speed,100ms native dt cap; do not hide jumps >4pt.
  if abs(dx)>4.001 or abs(dy)>4.001:violations.append(step)
# Pixel bounds of every unique captured image; native192x208 canvas, exclude evolution button.
hashes={hashlib.sha256((root/'playback-frames'/f['file']).read_bytes()).hexdigest():f for f in capture};bounds=[]
for h,f in hashes.items():
 w,height=f['width'],f['height'];assert (w,height)==(192,208)
 data=sp.check_output(['ffmpeg','-v','error','-i',str(root/'playback-frames'/f['file']),'-f','rawvideo','-pix_fmt','rgba','-'])
 pts=[(x,y) for y in range(60,height) for x in range(w) if max(data[(y*w+x)*4:(y*w+x)*4+3])>40];xs=[x for x,y in pts];ys=[y for x,y in pts];b=[min(xs),min(ys),max(xs),max(ys)]
 bounds.append({'file':f['file'],'sha256':h,'bounds':b,'center':(b[0]+b[2])/2,'bottom':b[3],'clipped':b[0]==0 or b[2]==w-1 or b[1]==60 or b[3]==height-1})
center=max(b['center'] for b in bounds)-min(b['center'] for b in bounds);bottom=max(b['bottom'] for b in bounds)-min(b['bottom'] for b in bounds)
network=[]
def visit(n):
 label=n.get('AXDescription','')
 if label.startswith('LUMA_METADATA_AUDIT '):network.append(json.loads(label.split(' ',1)[1]))
 for c in n.get('children',[]):visit(c)
for line in (root/'runtime-trace.jsonl').read_text().splitlines():visit(json.loads(line)['ax'])
result={'captureSeconds':capture[-1]['pts']-capture[0]['pts'],'moveSeconds':sum(s['seconds'] for s in move),'moveSegments':move,'directions':sorted(directions),'frameOrderErrors':errors,'cycleMs':cycles,'medianCycleMs':statistics.median(cycles) if cycles else None,'IDLEtoMOVE':sum(x['state']=='IDLE' and y['state']=='MOVE' for x,y in zip(segments,segments[1:])),'MOVEtoIDLE':sum(x['state']=='MOVE' and y['state']=='IDLE' for x,y in zip(segments,segments[1:])),'segments':segments,'panelSizes':sorted(sizes),'canvasSizes':sorted(canvas),'imagePanelOffsetRange':[[min(x[i] for x in offsets),max(x[i] for x in offsets)] for i in [0,1]] if offsets else [],'maxNativeStepX':max([abs(x['dx']) for x in steps],default=0),'maxNativeStepY':max([abs(x['dy']) for x in steps],default=0),'stepsExceedingNativeDtCap':violations,'horizontalVisibleSilhouetteExcursionPt':center/2,'bottomExcursionPt':bottom/2,'clipping':any(b['clipped'] for b in bounds),'pixelBounds':bounds,'networkLast':network[-1] if network else None,'allSamplesUseAnimation':all('base' not in s['sourceKinds'] for s in segments if s['state'] in ['IDLE','BLINK','MOVE']),'thresholdNote':'Silhouette nonblack RGB max>40 below capture y60; excursion includes facing reversal, separate from actual panel/world displacement. AX/panel reads are sequential, so offsets include sampling skew.'}
(root/'move-analysis.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['segments','moveSegments','pixelBounds','stepsExceedingNativeDtCap','frameOrderErrors','networkLast','cycleMs']},indent=2))
