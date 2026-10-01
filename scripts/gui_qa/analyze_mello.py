"""Analyze actual native-window recordings and native-owned AX phase samples."""
import json,re,statistics,argparse,bisect
from pathlib import Path
from PIL import Image
p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();root=a.root
raw=[json.loads(s) for s in (root/'pip-trace.jsonl').read_text().splitlines()];rows=[];issues=[];trans=[];cycles=[];cycle=[]
indices={'LAUNCH':3,'ASCEND':4,'APEX':5,'DESCEND':6,'LAND':7}
for r in raw:
 m=re.fullmatch(r'MELLO (IDLE|JUMP) frame (\d+) (animation|base) trace (.*)',r.get('label',''))
 if not m:continue
 sample=json.loads(m[4]);row={'wallTime':r['after'],'state':m[1],'frame':int(m[2]),'source':m[3],'sample':sample,'panels':r['panels'],'canvas':{'position':r['image'].get('AXPosition'),'size':r['image'].get('AXSize')}};rows.append(row)
 phase=sample['phase'] if sample else 'IDLE'
 if not trans or phase!=trans[-1]['phase']:
  trans.append({'phase':phase,'wallTime':r['after'],'nativeTime':sample['timestamp'] if sample else None})
 if not sample:continue
 if rows and len(rows)>1 and rows[-2]['sample'] and sample['timestamp']==rows[-2]['sample']['timestamp']:continue
 if sample['phase']=='LAUNCH' and cycle and cycle[-1]['phase']!='LAUNCH':cycle=[]
 cycle.append(sample)
 if sample['phase']=='LAND':
  if cycle[0]['phase']=='LAUNCH':cycles.append(cycle)
  cycle=[]
 if int(m[2])!=indices.get(phase) or m[3]!='animation':issues.append({'kind':'frame mapping','row':row})
 if (phase=='LAND')!=sample['grounded']:issues.append({'kind':'ground gate','row':row})
 if phase=='ASCEND' and sample['vy']<=0 or phase=='DESCEND' and sample['vy']>=0:issues.append({'kind':'velocity','row':row})
 if abs(sample['vx'])>3 and sample['facing']!=(1 if sample['vx']>0 else -1):issues.append({'kind':'facing','row':row})
cap=json.loads((root/'pip-frames/frames.json').read_text())['frames'];times=[r['wallTime'] for r in rows];pixels=[]
for f in cap:
 im=Image.open(root/'pip-frames'/f['file']).convert('RGBA');points=[(x,y) for y in range(60,im.height) for x in range(im.width) if max(im.getpixel((x,y))[:3])>40];xs,ys=zip(*points);b=[min(xs),min(ys),max(xs),max(ys)];t=(f['before']+f['wallTime'])/2;i=min(range(len(times)),key=lambda i:abs(times[i]-t));r=rows[i]
 upper=[x for x,y in points if y<135];flip=1 if statistics.mean(upper)>96 else -1
 pixels.append({'file':f['file'],'time':t,'bounds':b,'center':(b[0]+b[2])/2,'bottom':b[3],'phase':r['sample']['phase'] if r['sample'] else 'IDLE','nativeFacing':r['sample']['facing'] if r['sample'] else None,'pixelFacing':flip})
groups={}
for pix in pixels:
 key=pix['phase']+'_'+str(pix['pixelFacing']);groups.setdefault(key,[]).append(pix)
bounds={k:{'samples':len(v),'centerDriftPt':(max(p['center'] for p in v)-min(p['center'] for p in v))/2,'bottomDriftPt':(max(p['bottom'] for p in v)-min(p['bottom'] for p in v))/2} for k,v in groups.items()}
summary=[]
for c in cycles:
 # Native progress yields true movement duration even when first sample is after p=0.
 duration=(c[-1]['timestamp']-c[0]['timestamp'])/(1-c[0]['progress']);phaseDur={}
 for x,y in zip(c,c[1:]):phaseDur[x['phase']]=phaseDur.get(x['phase'],0)+y['timestamp']-x['timestamp']
 summary.append({'durationSeconds':duration,'observedSeconds':c[-1]['timestamp']-c[0]['timestamp'],'phases':list(dict.fromkeys(x['phase'] for x in c)),'phaseObservedSeconds':phaseDur,'nativeStart':c[0]['timestamp'],'nativeEnd':c[-1]['timestamp']})
result={'rows':len(rows),'completeJumps':summary,'issues':issues,'transitions':trans,'phaseBounds':bounds,'allCenterDriftPt':(max(p['center'] for p in pixels)-min(p['center'] for p in pixels))/2,'allBottomDriftPt':(max(p['bottom'] for p in pixels)-min(p['bottom'] for p in pixels))/2,'clipping':any(p['bounds'][0]<=0 or p['bounds'][2]>=191 or p['bounds'][3]>=207 for p in pixels),'pixelFacingMismatch':sum(p['nativeFacing'] is not None and p['nativeFacing']!=p['pixelFacing'] for p in pixels),'captureSeconds':cap[-1]['pts']-cap[0]['pts'],'captureFrames':len(cap),'medianCaptureIntervalMs':statistics.median((y['pts']-x['pts'])*1000 for x,y in zip(cap,cap[1:])),'panelSizes':sorted(set((b['Width'],b['Height']) for r in rows for b in r['panels'])),'canvasSizes':sorted(set(tuple(r['canvas']['size']) for r in rows))}
(root/'analysis.json').write_text(json.dumps(result,indent=2)+'\n');(root/'phase-trace.json').write_text(json.dumps(rows,indent=2)+'\n');(root/'pixel-trace.json').write_text(json.dumps(pixels,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ('transitions','issues')},indent=2));print('issues',len(issues))
