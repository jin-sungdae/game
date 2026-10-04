"""Read-only conservative preflight. READY is eligibility, not native spawn proof."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
BLOCKED = 'GUI_ENVIRONMENT_BLOCKED'


def finite(values):
    return all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in values)


def rect(r):
    return isinstance(r, dict) and finite([r.get(k) for k in ('x', 'y', 'w', 'h')]) and r['w'] > 0 and r['h'] > 0


def overlap(a, b):
    return a['x'] < b['x']+b['w'] and a['x']+a['w'] > b['x'] and a['y'] < b['y']+b['h'] and a['y']+a['h'] > b['y']


def fingerprint(s):
    # Exclude time/cursor; cursor safety is checked separately on every sample.
    keys = ('screenId', 'frame', 'visibleFrame', 'displays', 'obstacles', 'lumaWindows', 'lumaProcessCount', 'docks', 'space')
    d = {k:s[k] for k in keys}
    for k in ('obstacles', 'lumaWindows', 'docks', 'displays'):
        d[k] = sorted(d[k], key=lambda x: json.dumps(x, sort_keys=True))
    return hashlib.sha256(json.dumps(d, sort_keys=True, allow_nan=False).encode()).hexdigest()


def verify_contract():
    expected=json.loads(Path(__file__).with_name('environment_contract.json').read_text())
    return all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in expected.items())


def assess(s, profile):
    result = {'status': BLOCKED, 'reason': 'UNKNOWN_METADATA', 'userWindowMutations': 0}
    try:
        if not s['complete'] or not s['screenRecording'] or not s['accessibility']:
            return result
        if not rect(s['frame']) or not rect(s['visibleFrame']) or not s['screenId']:
            return result
        if not finite(s['cursor']) or len(s['cursor']) != 2:
            return result
        if len(s['obstacles']) > 64 or len(s['docks']) > 32:
            return dict(result, reason='METADATA_CAPACITY')
        if any(not rect(w['bounds']) for w in s['obstacles']+s['lumaWindows']) or any(not rect(d) for d in s['docks']):
            return result
        if s['lumaProcessCount'] or s['lumaWindows']:
            return dict(result, reason='EXISTING_LUMA')
        f, v = s['frame'], s['visibleFrame']
        # Same cold-start reservations as desktop::SafeAreaTracker. A stricter
        # union of ALL intersecting dock bounds avoids optimistic dock filtering.
        left=max(192, v['x']-f['x']); right=max(192, f['x']+f['w']-v['x']-v['w'])
        bottom=max(192, v['y']-f['y']); top=max(0, f['y']+f['h']-v['y']-v['h'])
        for d in s['docks']:
            if not overlap(f,d): continue
            if d['w'] >= 2*d['h'] and d['h'] <= f['h']*.35 and abs(d['y']-f['y']) <= 24:
                bottom=max(bottom,min(f['y']+f['h'],d['y']+d['h'])-f['y'])
            elif d['h'] >= 2*d['w'] and d['w'] <= f['w']*.35:
                if abs(d['x']-f['x']) <= 24: left=max(left,d['x']+d['w']-f['x'])
                elif abs(d['x']+d['w']-f['x']-f['w']) <= 24: right=max(right,f['x']+f['w']-d['x'])
        w,h=profile['panelSize']; zone=profile['zone']
        if not finite([w,h]) or min(w,h)<=0 or zone not in ('FREE_AREA','BOTTOM','TOP','EDGE'):
            return dict(result, reason='INVALID_PROFILE')
        lo_x=math.ceil(f['x']+left+8); hi_x=math.floor(f['x']+f['w']-right-8-w)
        lo_y=math.ceil(f['y']+bottom+8); hi_y=math.floor(f['y']+f['h']-top-8-h)
        if lo_x>hi_x or lo_y>hi_y: return dict(result, reason='SCREEN_TOO_SMALL')
        cx,cy=s['cursor']; exclusions=[r['bounds'] for r in s['obstacles']]+s['docks']+[dict(x=cx-100,y=cy-100,w=200,h=200)]
        # Conservative finite search: absence of a witness can be a false negative.
        # Never sent to the app, and never predicts its 16 seeded spawn attempts.
        count=0
        for ix in range(33):
            for iy in range(33):
                x=round(lo_x+(hi_x-lo_x)*ix/32); y=round(lo_y+(hi_y-lo_y)*iy/32)
                if zone=='BOTTOM': y=lo_y
                if zone=='TOP': y=hi_y
                if zone=='EDGE': x=lo_x if ix<16 else hi_x
                if not any(overlap(dict(x=x,y=y,w=w,h=h),e) for e in exclusions): count+=1
        return dict(result,status='READY' if count else BLOCKED,reason='CANDIDATE_SPACE_OBSERVED' if count else 'NO_SAFE_CANDIDATE',fingerprint=fingerprint(s),candidateSamples=count,obstacleCount=len(s['obstacles']),spaceIdentity='NOT_VERIFIED')
    except (KeyError, TypeError, ValueError, OverflowError):
        return result


def gate(sample, profile, duration=3.0, interval=.25, clock=time.monotonic, sleep=time.sleep):
    if duration<2 or interval<=0 or interval>duration: raise ValueError('minimum stability window is 2 seconds')
    start=clock(); rows=[]; first=None
    while True:
        s=sample(); verdict=assess(s,profile); rows.append({'environment':s,'assessment':verdict})
        if verdict['status']!='READY': return dict(verdict,samples=rows)
        current=verdict['fingerprint']
        if first is not None and current!=first: return dict(verdict,status=BLOCKED,reason='UNSTABLE_GEOMETRY',samples=rows)
        first=current
        if clock()-start>=duration: return dict(verdict,stableSeconds=clock()-start,samples=rows)
        sleep(interval)


def compile_probe(output):
    subprocess.run(['clang','-fobjc-arc','-framework','AppKit','-framework','ApplicationServices',str(Path(__file__).with_name('environment_probe.m')),'-o',str(output)],check=True)


def observe(probe):
    return json.loads(subprocess.check_output([str(probe)],text=True,timeout=5))


def prepare(probe, profile, output, countdown=5):
    print(f'Prepare an empty Desktop manually: {countdown}s. No windows will be moved.',flush=True)
    time.sleep(countdown)
    try:
        if not verify_contract(): report={'status':BLOCKED,'reason':'PRODUCTION_CONTRACT_CHANGED','userWindowMutations':0}
        else: report=gate(lambda:observe(probe),profile)
    except (subprocess.SubprocessError,OSError,ValueError): report={'status':BLOCKED,'reason':'OBSERVER_UNAVAILABLE','userWindowMutations':0}
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'],report['reason'],flush=True)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--profile',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False);probe=a.output/'environment-probe';compile_probe(probe)
    report=prepare(probe,json.loads(a.profile.read_text()),a.output/'preflight.json')
    raise SystemExit(0 if report['status']=='READY' else 2)
