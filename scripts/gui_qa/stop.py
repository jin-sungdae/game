"""Stop only QA-owned PIDs after checking their current command; preserve save/evidence."""
import argparse,json,os,signal,subprocess as sp,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args();r=a.directory.resolve();cfg=json.loads((r/'session.json').read_text())
pid=cfg.get('appPid')
if pid:
    cmd=sp.run(['ps','-p',str(pid),'-o','command='],capture_output=True,text=True).stdout
    if str(Path(cfg['appBundle']).resolve())+'/Contents/MacOS/' in cmd:
        os.kill(pid,signal.SIGTERM)
f=r/'server-process-group'
if f.exists():
    pid=int(f.read_text());cmd=sp.run(['ps','-p',str(pid),'-o','command='],capture_output=True,text=True).stdout
    if 'luma-game-server-0.1.0.jar' in cmd or ('GradleWrapperMain' in cmd and 'liveValidation' in cmd):
        os.killpg(pid,signal.SIGTERM)
pg=Path(cfg.get('pgBin','/opt/homebrew/opt/postgresql@16/bin'))
if (r/'pg/postmaster.pid').exists():sp.run([pg/'pg_ctl','-D',r/'pg','stop'],check=True)
print('Owned QA shutdown requested; save/evidence retained. Verify process and listener absence before reporting completion.')
