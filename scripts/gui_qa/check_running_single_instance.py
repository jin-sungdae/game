"""Validate a running release app against three real secondary launches; no domain mutation."""
import argparse,json,os,signal,subprocess as sp,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--primary-log',type=Path,required=True);p.add_argument('--helper',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
def audits(path):return [json.loads(s[len('LUMA_AUDIT '):]) for s in path.read_text().splitlines() if s.startswith('LUMA_AUDIT ')] if path.exists() else []
primary=audits(a.primary_log)[0]['pid'];initial=json.loads(sp.check_output([a.helper,'snapshot',str(primary)],text=True));children=[]
with (a.output/'foreground.jsonl').open('w') as log:
 observer=sp.Popen([a.helper,'observe',str(primary),'8'],stdout=log)
 for index in range(3):
  path=a.output/f'secondary-{index}.log'
  if index==1:
   with path.open('w') as stream:r=sp.run([a.bundle/'Contents/MacOS/luma-spike'],env=dict(os.environ,LUMA_FOCUS_AUDIT='1'),stdout=stream,stderr=sp.STDOUT,timeout=5)
  else:r=sp.run(['open','-n','--stdout',str(path),'--stderr',str(path),'--env','LUMA_FOCUS_AUDIT=1',str(a.bundle)],timeout=5)
  time.sleep(.7);rows=audits(path);text=path.read_text() if path.exists() else '';pid=rows[0]['pid'] if rows else None
  alive=None
  if pid:
   try:os.kill(pid,0);alive=True
   except ProcessLookupError:alive=False
  children.append({'exitCode':r.returncode,'pid':pid,'aliveAfterLaunch':alive,'worldCreated':'[LUMA STATE]' in text,'panelsCreated':'[LUMA PANEL]' in text,'audit':rows})
 observer.wait()
final=json.loads(sp.check_output([a.helper,'snapshot',str(primary)],text=True));rows=audits(a.primary_log);front=[json.loads(s) for s in (a.output/'foreground.jsonl').read_text().splitlines()];owned={primary}|{c['pid'] for c in children if c['pid']}
result={'primaryPid':primary,'primaryWindowIdsBefore':[w['kCGWindowNumber'] for w in initial['windows']],'primaryWindowIdsAfter':[w['kCGWindowNumber'] for w in final['windows']],'secondaries':children,'primaryAudit':rows,'noLumaForeground':all(x['frontPid'] not in owned for x in front),'focusPass':bool(rows) and all(x['activations']==0 and x['keyWindows']==0 for x in rows) and all(x['frontPid'] not in owned for x in front)}
result['singleInstancePass']=result['primaryWindowIdsBefore']==result['primaryWindowIdsAfter'] and all(c['exitCode']==0 and c['aliveAfterLaunch'] is False and not c['worldCreated'] and not c['panelsCreated'] for c in children)
(a.output/'report.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));os.kill(primary,signal.SIGTERM)
