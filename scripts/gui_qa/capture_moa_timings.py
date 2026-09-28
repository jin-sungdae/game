"""Capture actual candidate apps against one isolated QA backend. Requires run.py session."""
import argparse,json,os,signal,subprocess as sp,time,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root.resolve();session=root/'session/session.json';cfg=json.loads(session.read_text());helper=Path(cfg['helper']);repo=Path(__file__).resolve().parents[2]
sp.run(['clang','-fobjc-arc','-framework','AppKit','-framework','ApplicationServices',str(repo/'scripts/gui_qa/native.m'),'-o',helper],check=True)
def native(*args):return json.loads(sp.check_output([helper,*map(str,args)],text=True))
def moa(ax):
 result=[]
 def walk(n):
  if n.get('AXRole')=='AXImage' and n.get('AXDescription','').startswith('MOA '):result.append({k:v for k,v in n.items() if k!='children'})
  for child in n.get('children',[]):walk(child)
 walk(ax);return result
for cycle in [600,900,1500,1800]:
 bundle=root/f'playback-candidates/{cycle}/LUMA Spike.app'
 deadline=time.time()+600
 while not (bundle.parent/'manifest.json').exists():
  if time.time()>deadline:raise TimeoutError(str(bundle))
  time.sleep(1)
 pid=cfg.get('appPid');command=sp.run(['ps','-p',str(pid),'-o','command='],capture_output=True,text=True).stdout
 if cfg['appBundle']+'/Contents/MacOS/' in command:os.kill(pid,signal.SIGTERM);time.sleep(1)
 out=root/f'{cycle}ms';out.mkdir(exist_ok=False);log=out/'app.log'
 sp.run(['open','-n','--stdout',str(log),'--stderr',str(log),'--env','LUMA_GAME_SERVER_URL='+cfg['serverUrl'],'--env','LUMA_FOCUS_AUDIT=1',str(bundle)],check=True)
 for _ in range(100):
  lines=log.read_text().splitlines() if log.exists() else []
  rows=[json.loads(s[len('LUMA_AUDIT '):]) for s in lines if s.startswith('LUMA_AUDIT ')]
  if rows:break
  time.sleep(.1)
 else:raise RuntimeError('app failed to launch')
 pid=rows[0]['pid'];cfg.update(appPid=pid,appBundle=str(bundle));session.write_text(json.dumps(cfg,indent=2))
 time.sleep(1)
 snap=native('snapshot',pid);window=next(w for w in snap['windows'] if w.get('kCGWindowName')=='moa');b=window['kCGWindowBounds']
 # Same real pointer proximity for all candidates keeps the native companion looking/idle.
 sp.run([helper,'move',str(b['X']+b['Width']+40),str(b['Y']+60)],check=True);time.sleep(2)
 fast=sp.Popen([helper,'frames',str(pid),'9'],stdout=(out/'frame-trace.jsonl').open('w'))
 frames=out/'frames';recorder=sp.Popen([root/'record-window',str(pid),'8',frames],stdout=(out/'record.log').open('w'),stderr=sp.STDOUT)
 with (out/'renderer-trace.jsonl').open('w') as trace:
  while recorder.poll() is None:
   before=time.time();images=moa(native('ax',pid));snapshot=native('snapshot',pid)
   trace.write(json.dumps({'before':before,'after':time.time(),'images':images,'windows':[w for w in snapshot['windows'] if w.get('kCGWindowName')=='moa'],'frontBundle':snapshot['frontBundle']})+'\n');trace.flush();time.sleep(.01)
 fast.wait()
 if recorder.returncode or fast.returncode:raise RuntimeError('record/AX trace failed')
 rows=json.loads((frames/'frames.json').read_text())['frames'];assert rows[-1]['pts']-rows[0]['pts']>=5
 concat=out/'capture.ffconcat';lines=['ffconcat version 1.0']
 for i,row in enumerate(rows):
  lines += ["file 'frames/"+row['file']+"'",'option framerate 1000','duration '+str(rows[i+1]['pts']-row['pts'] if i+1<len(rows) else 1/60)]
 lines += ["file 'frames/"+rows[-1]['file']+"'"];concat.write_text('\n'.join(lines)+'\n')
 sp.run(['ffmpeg','-y','-v','error','-safe','0','-i',str(concat),'-vf','scale=iw*3:ih*3:flags=neighbor','-r','60','-c:v','libx264','-crf','15','-pix_fmt','yuv420p','-movflags','+faststart',str(out/f'moa-idle-{cycle}ms.mp4')],check=True)
 metadata={'cycleMs':cycle,'frameDurationMs':cycle/6,'sourceFirstFrame':'idle_01.png -> idle_00.png','bundle':str(bundle),'binarySHA256':hashlib.sha256((bundle/'Contents/MacOS/luma-spike').read_bytes()).hexdigest(),'captureSeconds':rows[-1]['pts']-rows[0]['pts'],'captureFrames':len(rows),'renderer':'actual release WKWebView CharacterRenderer','qaOnlyCspSelf':False,'productionTimingApproved':False}
 (out/'metadata.json').write_text(json.dumps(metadata,indent=2));print(cycle,'complete',flush=True)
