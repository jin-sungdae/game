"""Measure actual window pixels and high-rate AX sequence for registered v2 footage."""
import argparse,collections,hashlib,json,re,subprocess as sp,statistics
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();root=a.root;report={'method':'Actual ScreenCaptureKit RGBA pixels; nonblack RGB max>40 below y60 excludes evolution button. Native192x208 capture at2x. Body bounds compared across every distinct captured bitmap. AX frame labels disambiguate byte-identical source frames.','candidates':[]}
for cycle in [600,900,1500,1800]:
 d=root/f'{cycle}ms';capture=json.loads((d/'frames/frames.json').read_text())['frames'];trace=[json.loads(s) for s in (d/'frame-trace.jsonl').read_text().splitlines()];slow=[json.loads(s) for s in (d/'renderer-trace.jsonl').read_text().splitlines()];sequence=[]
 trace=[t for t in trace if capture[0]['wallTime']<=t['after']<=capture[-1]['wallTime']]
 for row in trace:
  m=re.fullmatch('MOA IDLE frame ([1-6]) animation',row['label']);assert m,row
  frame=int(m[1])
  if not sequence or sequence[-1]['frame']!=frame:sequence.append({'frame':frame,'time':row['after']})
 hashes={hashlib.sha256((d/'frames'/f['file']).read_bytes()).hexdigest():f for f in capture};bounds=[]
 for h,f in hashes.items():
  w,height=f['width'],f['height'];assert (w,height)==(192,208)
  raw=sp.check_output(['ffmpeg','-v','error','-i',str(d/'frames'/f['file']),'-f','rawvideo','-pix_fmt','rgba','-']);ink=[(x,y) for y in range(60,height) for x in range(w) if max(raw[(y*w+x)*4:(y*w+x)*4+3])>40]
  xs=[x for x,y in ink];ys=[y for x,y in ink];b=[min(xs),min(ys),max(xs),max(ys)]
  bounds.append({'sha256':h,'file':f['file'],'bounds':b,'centerX':(b[0]+b[2])/2,'bottom':b[3],'clipped':b[0]==0 or b[2]==w-1 or b[3]==height-1 or b[1]==60})
 cx=[b['centerX'] for b in bounds];bottom=[b['bottom'] for b in bounds]
 windows={json.dumps(w['kCGWindowBounds'],sort_keys=True) for t in slow for w in t['windows']};positions={tuple(i['AXPosition']) for t in slow for i in t['images']};sizes={tuple(i['AXSize']) for t in slow for i in t['images']}
 intervals=[(b['time']-a['time'])*1000 for a,b in zip(sequence,sequence[1:])][1:]
 item={'cycleMs':cycle,'recordSeconds':capture[-1]['pts']-capture[0]['pts'],'captureFrames':len(capture),'axSamples':len(trace),'frameOrderPass':all(b['frame']==a['frame']%6+1 for a,b in zip(sequence,sequence[1:])),'seenFrames':sorted({x['frame'] for x in sequence}),'loopTransitions':sum(a['frame']==6 and b['frame']==1 for a,b in zip(sequence,sequence[1:])),'medianFrameMs':statistics.median(intervals),'centerDeltaCapturePx':max(cx)-min(cx),'horizontalHoppingPt':(max(cx)-min(cx))/2,'bottomDeltaCapturePx':max(bottom)-min(bottom),'bottomHoppingPt':(max(bottom)-min(bottom))/2,'clipping':any(b['clipped'] for b in bounds),'panelBounds':[json.loads(w) for w in windows],'imagePositions':list(positions),'imageSizes':list(sizes),'panelStable':len(windows)==len(positions)==len(sizes)==1,'pixelBounds':bounds,'sequence':sequence}
 report['candidates'].append(item)
 print({k:v for k,v in item.items() if k not in ['pixelBounds','sequence']})
(root/'registration-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
