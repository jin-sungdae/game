"""Correlate actual ScreenCaptureKit pixels with independent renderer AX observations."""
import argparse,json,hashlib,collections,statistics,re,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();root=a.root
reference=root/'1800ms';r=json.loads((reference/'frames/frames.json').read_text())['frames'];trace=[json.loads(s) for s in (reference/'renderer-trace.jsonl').read_text().splitlines()]
votes=collections.defaultdict(collections.Counter)
for row in r:
 digest=hashlib.sha256((reference/'frames'/row['file']).read_bytes()).hexdigest()
 # Use observations safely inside the 300ms held frame, not its capture boundary.
 for t in trace:
  if row['wallTime']+.04<t['before'] and t['after']<row['wallTime']+.26:
   for image in t['images']:
    match=re.fullmatch(r'MOA IDLE frame ([1-6]) animation',image['AXDescription'])
    if match:votes[digest][int(match[1])]+=1
mapping={h:c.most_common(1)[0][0] for h,c in votes.items()};assert set(mapping.values())==set(range(1,7)),votes
report={'method':'PNG SHA256 equality across four recordings; labels correlated inside 1800ms frame holds using AX intervals. PTS from ScreenCaptureKit, not simulated clock.', 'pixelHashFrameMapping':mapping,'mappingVotes':{h:dict(c) for h,c in votes.items()},'candidates':[]}
for cycle in [600,900,1500,1800]:
 directory=root/f'{cycle}ms';r=json.loads((directory/'frames/frames.json').read_text())['frames'];trace=[json.loads(s) for s in (directory/'renderer-trace.jsonl').read_text().splitlines()];sequence=[]
 for row in r:
  frame=mapping[hashlib.sha256((directory/'frames'/row['file']).read_bytes()).hexdigest()]
  if not sequence or sequence[-1]['frame']!=frame:sequence.append({'frame':frame,'pts':row['pts'],'file':row['file']})
 intervals=[b['pts']-a['pts'] for a,b in zip(sequence,sequence[1:])]
 windows={json.dumps(w['kCGWindowBounds'],sort_keys=True) for t in trace for w in t['windows']};positions={tuple(i['AXPosition']) for t in trace for i in t['images']};sizes={tuple(i['AXSize']) for t in trace for i in t['images']}
 summary={'cycleMs':cycle,'captureSeconds':r[-1]['pts']-r[0]['pts'],'capturedFrames':len(r),'orderPass':all(b['frame']==a['frame']%6+1 for a,b in zip(sequence,sequence[1:])),'loopBoundaries':sum(a['frame']==6 and b['frame']==1 for a,b in zip(sequence,sequence[1:])),'medianFrameMs':statistics.median(intervals)*1000,'minFrameMs':min(intervals)*1000,'maxFrameMs':max(intervals)*1000,'windowBounds':[json.loads(w) for w in windows],'imagePositions':list(positions),'imageSizes':list(sizes),'panelAndCanvasStable':len(windows)==len(positions)==len(sizes)==1,'sequence':sequence}
 report['candidates'].append(summary)
(root/'analysis.json').write_text(json.dumps(report,indent=2)+'\n')
for c in report['candidates']:print({k:v for k,v in c.items() if k!='sequence'})
