"""Manually prepared Desktop launcher. Never move windows or automate Mission Control."""
import argparse
import json
from pathlib import Path
import subprocess as sp
import sys
import time
from common_trace import normalize
from cleanup_environment import cleanup as cleanup_owned
from environment import compile_probe, prepare, observe, fingerprint

HERE=Path(__file__).resolve().parent


def stop_child(child):
    if child and child.poll() is None:
        child.terminate()
        try: child.wait(timeout=8)
        except sp.TimeoutExpired: child.kill();child.wait(timeout=5)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--profile',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--encounter-code');p.add_argument('--seconds',type=float,default=20);a=p.parse_args()
    if not 5<=a.seconds<=120: p.error('recording duration must be 5..120 seconds')
    profile=json.loads(a.profile.read_text());root=a.output.resolve();root.mkdir(parents=True,exist_ok=False)
    probe=root/'environment-probe';compile_probe(probe)
    report=prepare(probe,profile,root/'preflight.json')
    if report['status']!='READY': return 2
    recorder=root/'record-window'
    sp.run(['swiftc','-parse-as-library',str(HERE/'record_window.swift'),'-o',str(recorder)],check=True)
    session=root/'session';trace=None;capture=None;launch=None;status='NOT_VERIFIED';failure=None;cleanup={}
    try:
        cmd=[sys.executable,str(HERE/'run.py'),'--bundle',str(a.bundle.resolve()),'--output',str(session),'--capture-only','--keep-running','--environment-profile',str(a.profile.resolve())]
        if a.encounter_code: cmd+=['--encounter-code',a.encounter_code]
        with (root/'launcher.log').open('w') as log:
            launch=sp.Popen(cmd,stdout=log,stderr=sp.STDOUT);launch.wait(timeout=180)
        if launch.returncode: raise RuntimeError('launch/preflight failed; see session/preflight.json')
        cfg=json.loads((session/'session.json').read_text());pid=cfg['appPid']
        baseline=observe(probe); initial=json.loads((session/'preflight.json').read_text())['fingerprint']
        def external(s):
            s=dict(s,lumaWindows=[],lumaProcessCount=0)
            return fingerprint(s)
        if external(baseline)!=initial: raise RuntimeError('GUI_ENVIRONMENT_BLOCKED: geometry changed at launch')
        with (root/'raw-trace.jsonl').open('w') as raw, (root/'record.log').open('w') as log:
            trace=sp.Popen([cfg['helper'],'frames-character',str(pid),str(a.seconds),profile['label'],profile['window']],stdout=raw)
            capture=sp.Popen([str(recorder),str(pid),str(a.seconds),str(root/'frames'),profile['window']],stdout=log,stderr=sp.STDOUT)
            deadline=time.monotonic()+a.seconds+15
            with (root/'environment.jsonl').open('w') as env:
                while capture.poll() is None:
                    s=observe(probe);env.write(json.dumps(s)+'\n');env.flush()
                    if external(s)!=initial: raise RuntimeError('GUI_ENVIRONMENT_BLOCKED: geometry changed during capture')
                    if time.monotonic()>deadline: raise TimeoutError('capture deadline')
                    time.sleep(.5)
            trace.wait(timeout=8)
        if trace.returncode or capture.returncode: raise RuntimeError('actual window/AX capture failed')
        rows=[normalize(json.loads(line),profile,baseline) for line in (root/'raw-trace.jsonl').read_text().splitlines()]
        rows=[r for r in rows if r]
        (root/'trace.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
        frames=json.loads((root/'frames/frames.json').read_text())['frames']
        if not rows or len(frames)<2 or frames[-1]['pts']-frames[0]['pts']<a.seconds-.5: raise RuntimeError('insufficient actual playback evidence')
        status='RECORDED'
    except (OSError,ValueError,RuntimeError,sp.SubprocessError) as exc:
        failure=str(exc);status='GUI_ENVIRONMENT_BLOCKED' if 'geometry' in failure or 'preflight' in failure else 'NOT_VERIFIED'
    finally:
        for child in (launch,trace,capture): stop_child(child)
        if (session/'session.json').exists():
            cleanup=cleanup_owned(session)
        (root/'result.json').write_text(json.dumps({'status':status,'failure':failure,'cleanup':cleanup,'userWindowMutations':0},indent=2)+'\n')
    return 0 if status=='RECORDED' and cleanup.get('status')=='PASS' else 2


if __name__=='__main__': raise SystemExit(main())
