"""Stop recorded QA-owned processes; report identity uncertainty instead of killing it."""
import json
import os
from pathlib import Path
import signal
import subprocess as sp
import time


def identity(pid):
    result=sp.run(['ps','-p',str(pid),'-o','lstart=','-o','command='],text=True,capture_output=True)
    return result.stdout.strip() if result.returncode==0 else None


def cleanup(root):
    cfg=json.loads((root/'session.json').read_text());rows=[]
    for key in ('appPid','serverPid'):
        pid=cfg.get(key)
        if not pid:
            rows.append({'process':key,'status':'NOT_STARTED' if key=='serverPid' or not cfg.get('appLaunchRequested') else 'NOT_VERIFIED'});continue
        current=identity(pid);expected=cfg.get(key+'Identity')
        if current is None: rows.append({'process':key,'status':'STOPPED'});continue
        if not expected or expected!=current:
            rows.append({'process':key,'status':'IDENTITY_MISMATCH'});continue
        os.kill(pid,signal.SIGTERM)
        deadline=time.monotonic()+8
        while identity(pid)==expected and time.monotonic()<deadline: time.sleep(.1)
        rows.append({'process':key,'status':'STOPPED' if identity(pid)!=expected else 'NOT_VERIFIED'})
    # This PGDATA was created exclusively for this session, never an external server.
    data=root/'pg'
    if (data/'postmaster.pid').exists():
        pg=Path(cfg['pgBin'])
        result=sp.run([str(pg/'pg_ctl'),'-D',str(data),'-w','-t','10','stop'],capture_output=True,text=True)
        rows.append({'process':'database','status':'STOPPED' if result.returncode==0 and not (data/'postmaster.pid').exists() else 'NOT_VERIFIED'})
    else: rows.append({'process':'database','status':'NOT_STARTED_OR_STOPPED'})
    report={'status':'PASS' if all(r['status'] in ('STOPPED','NOT_STARTED','NOT_STARTED_OR_STOPPED') for r in rows) else 'NOT_VERIFIED','processes':rows,'userWindowMutations':0}
    (root/'cleanup.json').write_text(json.dumps(report,indent=2)+'\n')
    return report
