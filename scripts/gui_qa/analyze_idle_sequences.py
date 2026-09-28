"""Analyze actual release-window pixels and AX sequence; never infer visual approval."""
import argparse,hashlib,json,re,statistics,subprocess as sp
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('root',type=Path);root=p.parse_args().root
capture=json.loads((root/'playback-frames/frames.json').read_text())['frames']
trace=[json.loads(s) for s in (root/'frame-trace.jsonl').read_text().splitlines()]
trace=[r for r in trace if capture[0]['wallTime']<=r['after']<=capture[-1]['wallTime']]
sequence=[]
for row in trace:
    m=re.fullmatch(r'MOA (IDLE|BLINK) frame ([1-4]) animation',row['label']);assert m,row
    state,frame=m[1],int(m[2]);assert frame<= (4 if state=='IDLE' else 3)
    if not sequence or (state,frame)!=(sequence[-1]['state'],sequence[-1]['frame']):sequence.append({'state':state,'frame':frame,'time':row['after']})
errors=[];blink_starts=[];returns=[];cycles=[];loop_start=None
for prev,row in zip(sequence,sequence[1:]):
    if prev['state']==row['state']:
        expected=prev['frame']%4+1 if row['state']=='IDLE' else prev['frame']+1
        if row['frame']!=expected:errors.append([prev,row])
        if row['state']=='IDLE' and row['frame']==1:
            if loop_start is not None:cycles.append((row['time']-loop_start)*1000)
            loop_start=row['time']
    elif row['state']=='BLINK':
        if row['frame']!=1:errors.append([prev,row])
        blink_starts.append(row['time']);loop_start=None
    else:
        if prev['frame']!=3 or row['frame']!=1:errors.append([prev,row])
        returns.append(row['time']);loop_start=row['time']
waiting=[(b-max(r for r in returns if r<b))*1000 for b in blink_starts if any(r<b for r in returns)]
hashes={hashlib.sha256((root/'playback-frames'/f['file']).read_bytes()).hexdigest():f for f in capture};bounds=[]
for h,f in hashes.items():
    w,height=f['width'],f['height'];assert (w,height)==(192,208)
    raw=sp.check_output(['ffmpeg','-v','error','-i',str(root/'playback-frames'/f['file']),'-f','rawvideo','-pix_fmt','rgba','-'])
    ink=[(x,y) for y in range(60,height) for x in range(w) if max(raw[(y*w+x)*4:(y*w+x)*4+3])>40]
    xs=[x for x,y in ink];ys=[y for x,y in ink];b=[min(xs),min(ys),max(xs),max(ys)]
    bounds.append({'file':f['file'],'sha256':h,'bounds':b,'center':(b[0]+b[2])/2,'bottom':b[3],'clipped':b[0]==0 or b[2]==w-1 or b[1]==60 or b[3]==height-1})
slow=[json.loads(s) for s in (root/'runtime-trace.jsonl').read_text().splitlines()]
windows={json.dumps(w['kCGWindowBounds'],sort_keys=True) for t in slow for w in t['windows']}
positions={tuple(i['AXPosition']) for t in slow for i in t['images']};sizes={tuple(i['AXSize']) for t in slow for i in t['images']}
center=max(b['center'] for b in bounds)-min(b['center'] for b in bounds);bottom=max(b['bottom'] for b in bounds)-min(b['bottom'] for b in bounds)
network=[n for r in slow for n in r['network']]
result={'renderer':'actual production WKWebView; unchanged CSP; static registry','recordSeconds':capture[-1]['pts']-capture[0]['pts'],'captureFrames':len(capture),'axSamples':len(trace),'sequenceErrors':errors,'breathingCyclesMs':cycles,'blinkStartsWallTime':blink_starts,'blinkReturnWallTime':returns,'blinkWaitAfterReturnMs':waiting,'blinkStartToStartMs':[(b-a)*1000 for a,b in zip(blink_starts,blink_starts[1:])],'centerDriftCapturePx':center,'horizontalHoppingPt':center/2,'bottomDriftCapturePx':bottom,'bottomHoppingPt':bottom/2,'clipping':any(b['clipped'] for b in bounds),'panelStable':len(windows)==len(positions)==len(sizes)==1,'panelBounds':[json.loads(w) for w in windows],'imagePositions':list(positions),'imageSizes':list(sizes),'pixelBounds':bounds,'sequence':sequence,'networkLast':network[-1] if network else None,'manualVisualReview':['breathing strength','blink naturalness','overall liveliness']}
(root/'playback-analysis.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['pixelBounds','sequence','networkLast']},indent=2))
assert result['recordSeconds']>=15 and len(blink_starts)>=1 and returns and not errors
assert center==bottom==0 and result['panelStable'] and not result['clipping']
assert network and all(n['manifestAttempts']==0 and n['cspViolations']==0 for n in network)
