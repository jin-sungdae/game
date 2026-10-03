"""Offline QA observations, not a rendering simulator. Null never means PASS."""
import argparse
import bisect
import collections
import json
import math
from pathlib import Path
import statistics


def analyze_trace(rows, profile):
    states=profile['states']; previous=None; issues=[]; facing=[]; flips=[]; agreement=[]
    cycles=collections.defaultdict(list); starts={}; seen=collections.defaultdict(set)
    for row in rows:
        state=row['animationState']; frame=row['animationFrame']; t=row['timestamp']
        if state not in states or not 1<=frame<=states[state]['frames']:
            issues.append({'timestamp':t,'reason':'INVALID_STATE_FRAME'});previous=None;continue
        seen[state].add(frame)
        contiguous=previous and previous['animationState']==state and t>previous['timestamp'] and t-previous['timestamp']<=.15
        if contiguous and frame!=previous['animationFrame']:
            expected=previous['animationFrame']+1
            if states[state].get('loop') and expected>states[state]['frames']: expected=1
            if frame!=expected: issues.append({'timestamp':t,'reason':'OBSERVATION_GAP_OR_ORDER','from':previous['animationFrame'],'to':frame})
        if not contiguous: starts.pop(state,None)
        if frame==1 and (not contiguous or previous['animationFrame']!=1):
            if state in starts: cycles[state].append((t-starts[state])*1000)
            starts[state]=t
        if row.get('vx') is not None and row.get('nativeFacing') is not None and abs(row['vx'])>profile['velocityEpsilon']:
            expected=1 if row['vx']>0 else -1
            facing.append(row['nativeFacing']==expected)
            if row.get('rendererFlip') is not None:
                flips.append(row['rendererFlip']==expected*(1 if profile.get('sourceFacing','RIGHT')=='RIGHT' else -1))
        rule=states[state]
        if 'excursionActive' in rule and row.get('excursionActive') is not None:
            agreement.append(row['excursionActive']==rule['excursionActive'])
        if 'minSpeed' in rule and row.get('speed') is not None: agreement.append(row['speed']>=rule['minSpeed'])
        if 'maxSpeed' in rule and row.get('speed') is not None: agreement.append(row['speed']<=rule['maxSpeed'])
        if row.get('source')!='animation': issues.append({'timestamp':t,'reason':'BASE_FALLBACK'})
        previous=row
    complete=all(seen[s]==set(range(1,v['frames']+1)) for s,v in states.items() if v.get('required',False))
    return {'samples':len(rows),'frameOrder':'FAIL' if issues else 'PASS' if rows and complete else 'NOT_VERIFIED',
        'issues':issues,'seenFrames':{k:sorted(v) for k,v in seen.items()},
        'cycles':{k:{'count':len(v),'medianMs':statistics.median(v)} for k,v in cycles.items()},
        'facing':'FAIL' if (facing and not all(facing)) or (flips and not all(flips)) else 'PASS' if facing and len(flips)==len(facing) else 'NOT_VERIFIED',
        'stateVelocityAgreement':'PASS' if agreement and all(agreement) else 'FAIL' if agreement else 'NOT_VERIFIED'}


def nearest(rows, times, timestamp, tolerance):
    i=bisect.bisect_left(times,timestamp)
    candidates=[rows[k] for k in (i-1,i) if 0<=k<len(rows)]
    if not candidates: return None
    r=min(candidates,key=lambda r:abs(r['timestamp']-timestamp))
    return r if abs(r['timestamp']-timestamp)+r.get('observationDuration',0)/2<=tolerance else None


def measure(root, rows, profile):
    from PIL import Image
    frames=json.loads((root/'frames.json').read_text())['frames']; times=[r['timestamp'] for r in rows]; out=[]; skipped=0
    for f in frames:
        r=nearest(rows,times,f['wallTime'],profile['maxTraceSkewSeconds'])
        if not r or not r.get('panelBounds') or not r.get('canvasBounds'): skipped+=1;continue
        p,c=r['panelBounds'],r['canvasBounds']
        path=(root/f['file']).resolve()
        if not path.is_relative_to(root.resolve()): raise ValueError('frame outside capture directory')
        with Image.open(path) as image:
            image=image.convert('RGBA'); sx=image.width/p['w'];sy=image.height/p['h']
            x0=max(0,math.floor((c['x']-p['x'])*sx)); y0=max(0,math.floor((c['y']-p['y'])*sy))
            x1=min(image.width,math.ceil((c['x']+c['w']-p['x'])*sx)); y1=min(image.height,math.ceil((c['y']+c['h']-p['y'])*sy))
            if x1<=x0 or y1<=y0: skipped+=1;continue
            crop=image.crop((x0,y0,x1,y1));mask=profile['pixelMask']; threshold=mask['threshold']
            if mask['method']=='alpha': values=[255 if a>threshold else 0 for _,_,_,a in crop.getdata()]
            elif mask['method']=='rgb-threshold': values=[255 if a and max(red,green,blue)>threshold else 0 for red,green,blue,a in crop.getdata()]
            else: raise ValueError('unsupported mask')
            bitmap=Image.new('L',crop.size);bitmap.putdata(values);bbox=bitmap.getbbox()
            if not bbox: skipped+=1;continue
            l,t,rr,b=bbox
            out.append({'timestamp':f['wallTime'],'state':r['animationState'],'frame':r['animationFrame'],'flip':r.get('rendererFlip'),
                'centerX':(x0+(l+rr)/2)/sx,'centerY':(y0+(t+b)/2)/sy,'bottom':(y0+b)/sy,
                'edgeContact':l==0 or t==0 or rr==crop.width or b==crop.height,
                'canvasOutsidePanel':c['x']<p['x'] or c['y']<p['y'] or c['x']+c['w']>p['x']+p['w'] or c['y']+c['h']>p['y']+p['h'],
                'panelSize':[p['w'],p['h']],'canvasSize':[c['w'],c['h']]})
    groups=collections.defaultdict(list)
    for row in out: groups[(row['state'],row['flip'])].append(row)
    drift=[]
    for (state,flip),items in groups.items():
        drift.append({'state':state,'flip':flip,'samples':len(items),**{k:max(i[k] for i in items)-min(i[k] for i in items) for k in ('centerX','centerY','bottom')}})
    mirror=[]
    for state in profile['states']:
        left=groups.get((state,-1),[]);right=groups.get((state,1),[])
        if left and right: mirror.append({'state':state,'centerOffsetPt':statistics.median(i['centerX'] for i in right)-statistics.median(i['centerX'] for i in left)})
    source=profile.get('sourceBounds'); predicted=None
    if source: predicted=2*((source[0]+source[2])/2)-profile['sourceCanvas'][0]
    return {'status':'MEASURED' if out else 'NOT_VERIFIED','mask':profile['pixelMask'],'matchedFrames':len(out),'unmatchedFrames':skipped,
        'driftPtByStateFacing':drift,'mirrorOffset':mirror or 'NOT_VERIFIED','sourceMirrorOffsetPx':predicted,
        'clipping':'EDGE_CONTACT_REVIEW_REQUIRED' if any(r['edgeContact'] or r['canvasOutsidePanel'] for r in out) else 'NO_MASK_EDGE_CONTACT' if out else 'NOT_VERIFIED',
        'measurements':out,'caveat':'Threshold mask is not alpha-exact production geometry; edge contact requires visual review. World motion removed by measuring panel-local pixels.'}


def main():
    p=argparse.ArgumentParser();p.add_argument('trace',type=Path);p.add_argument('--profile',type=Path,required=True);p.add_argument('--frames',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    rows=[json.loads(line) for line in a.trace.read_text().splitlines()];profile=json.loads(a.profile.read_text())
    if any(y['timestamp']<=x['timestamp'] for x,y in zip(rows,rows[1:])): raise ValueError('trace must be strictly chronological')
    result=analyze_trace(rows,profile)
    result['renderer']=measure(a.frames,rows,profile) if a.frames else {'status':'NOT_VERIFIED'}
    a.output.write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__': main()
