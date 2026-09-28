"""Actual server-owned PIP on the release renderer. Fixture changes only a new isolated QA DB's encounter weights."""
import argparse,json,subprocess as sp,time
from pathlib import Path
from session import Session
p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--ambient-seconds',type=int,default=30);a=p.parse_args();root=a.root.resolve();s=Session(root/'session');cfg=s.config
assert (s.root/'pg').is_dir() and cfg['captureOnly']
# Never touch a developer/production DB. run.py owns this new fixed-name database.
query="UPDATE game.m_monster SET encounter_weight=CASE WHEN code='PIP' THEN 100 ELSE 0 END; SELECT code,encounter_weight FROM game.m_monster ORDER BY code;"
result=sp.check_output([str(Path(cfg['pgBin'])/'psql'),'-h','127.0.0.1','-p',str(cfg['dbPort']),'-U','luma','-d','luma_gui_qa_test','-At','-v','ON_ERROR_STOP=1','-c',query],text=True)
(root/'fixture.json').write_text(json.dumps({'scope':'fresh run.py-owned luma_gui_qa_test only','query':query,'result':result,'productionDefaultsChanged':False},indent=2))
# Existing native right-click requests a server encounter; no debug-PIP entity.
s.native('right',*s.center('moa'));time.sleep(1)
for _ in range(80):
 try:enc=s.api('encounters/active');s.panel('pip');break
 except (RuntimeError,OSError):time.sleep(.2)
else:raise RuntimeError('server PIP did not appear')
assert enc and enc['monster']['code']=='PIP',enc
(root/'encounter.json').write_text(json.dumps(enc,indent=2));s.save('spawn-ax',s.ax())
def labels(n):
 return [n.get('AXTitle',''),n.get('AXDescription','')]+[x for c in n.get('children',[]) for x in labels(c)]
if 'Close panel' in labels(s.ax()):s.press('Close panel')
s.native('move',800,200)
frames=root/'playback-frames';fast=sp.Popen([s.helper,'frames-pip',str(s.pid),str(a.ambient_seconds+25)],stdout=(root/'frame-trace.jsonl').open('w'))
rec=sp.Popen([str(root/'record-window'),str(s.pid),str(a.ambient_seconds+15),str(frames),'pip'],stdout=(root/'record.log').open('w'),stderr=sp.STDOUT)
start=time.monotonic();events=[]
try:
 while rec.poll() is None:
  elapsed=time.monotonic()-start
  # After ambient movement evidence, use existing mouse/menu to exercise priority.
  if elapsed>a.ambient_seconds and not events:
   s.click('pip');time.sleep(.3);events.append({'name':'encounter-engaged','time':time.time(),'ax':s.ax()});
   if 'Start battle' in labels(s.ax()):s.press('Start battle')
   time.sleep(.7);events.append({'name':'battle','time':time.time(),'ax':s.ax()});
   if 'CAPTURE' in labels(s.ax()):s.press('CAPTURE')
   time.sleep(1.5);events.append({'name':'capture','time':time.time(),'ax':s.ax()})
  time.sleep(.2)
finally:
 fast.terminate();fast.wait();(root/'events.json').write_text(json.dumps(events,indent=2));(root/'final-ax.json').write_text(json.dumps(s.ax(),indent=2))
if rec.returncode:raise RuntimeError('capture failed')
rows=json.loads((frames/'frames.json').read_text())['frames'];lines=['ffconcat version 1.0']
for i,row in enumerate(rows):lines += ["file 'playback-frames/"+row['file']+"'",'option framerate 1000','duration '+str(rows[i+1]['pts']-row['pts'] if i+1<len(rows) else 1/60)]
lines += ["file 'playback-frames/"+rows[-1]['file']+"'",'option framerate 1000'];(root/'playback.ffconcat').write_text('\n'.join(lines)+'\n')
sp.run(['ffmpeg','-y','-v','error','-safe','0','-i',str(root/'playback.ffconcat'),'-vf','scale=iw*3:ih*3:flags=neighbor','-r','60','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(root/'production-pip.mp4')],check=True)
print('Actual server PIP capture complete',root)
