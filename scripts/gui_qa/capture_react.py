"""Observe existing native mouse click/drag in the release app; never inject animation state."""
import argparse,json,subprocess as sp,time
from pathlib import Path
from session import Session
p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--seconds',type=int,default=90);p.add_argument('--walking-first',action='store_true');a=p.parse_args();root=a.root.resolve();s=Session(root/'session');frames=root/'playback-frames';frames.mkdir()
fast=sp.Popen([s.helper,'frames',str(s.pid),str(a.seconds+5)],stdout=(root/'frame-trace.jsonl').open('w'))
rec=sp.Popen([str(root/'record-window'),str(s.pid),str(a.seconds),str(frames)],stdout=(root/'record.log').open('w'),stderr=sp.STDOUT)
s.native('move',800,200)
events=[]
def click(name):
 # Let existing native cursor sampling observe pointer placement before mouse-down.
 s.native('move',*s.center('moa'));time.sleep(.2)
 e={'name':name,'beforeTime':time.time(),'before':s.api('game/bootstrap'),'panelBefore':s.panel('moa')};s.click('moa');e['releasedAt']=time.time();time.sleep(.8);e.update(after=s.api('game/bootstrap'),panelAfter=s.panel('moa'),afterTime=time.time());events.append(e);(root/'events.json').write_text(json.dumps(events,indent=2))
try:
 if not a.walking_first:
  time.sleep(2);click('first-idle-click');time.sleep(1);click('cooldown-click');time.sleep(1)
  s.native('move',*s.center('moa'));time.sleep(.2);events.append({'name':'repeated-clicks','start':time.time()});s.click('moa');time.sleep(.12);s.click('moa');events[-1]['end']=time.time();time.sleep(2)
  x,y=s.center('moa');events.append({'name':'drag','start':time.time()});s.native('drag',x,y,x+35,y);events[-1]['end']=time.time();time.sleep(2)
  s.native('move',800,200)
 # Wait for actual autonomous movement; no state/API movement injection.
 reader=(root/'frame-trace.jsonl').open();clicked_move=False
 while rec.poll() is None:
  latest=None
  for line in reader:
   try:latest=json.loads(line)
   except json.JSONDecodeError:pass
  if latest and not clicked_move and ' MOVE ' in latest.get('label',''):
   time.sleep(.5);click('moving-click');clicked_move=True;time.sleep(2);click('post-move-idle-click');time.sleep(2);click('cooldown-stationary-click')
   if a.walking_first:
    time.sleep(2);s.native('move',*s.center('moa'));time.sleep(.2);events.append({'name':'repeated-clicks','start':time.time()});s.click('moa');time.sleep(.12);s.click('moa');events[-1]['end']=time.time();time.sleep(2)
    x,y=s.center('moa');events.append({'name':'drag','start':time.time()});s.native('drag',x,y,x+35,y);events[-1]['end']=time.time();s.native('move',800,200)
  if clicked_move and rec.poll() is None and time.time()-events[-1].get('afterTime',events[-1].get('end',time.time()))>8:(frames/'stop').touch()
  time.sleep(.1)
 reader.close()
finally:
 fast.terminate();fast.wait();(root/'events.json').write_text(json.dumps(events,indent=2));(root/'runtime-ax.json').write_text(json.dumps(s.ax(),indent=2))
if rec.returncode:raise RuntimeError('recording failed')
rows=json.loads((frames/'frames.json').read_text())['frames'];lines=['ffconcat version 1.0']
for i,row in enumerate(rows):lines += ["file 'playback-frames/"+row['file']+"'",'option framerate 1000','duration '+str(rows[i+1]['pts']-row['pts'] if i+1<len(rows) else 1/60)]
lines += ["file 'playback-frames/"+rows[-1]['file']+"'",'option framerate 1000'];(root/'playback.ffconcat').write_text('\n'.join(lines)+'\n')
sp.run(['ffmpeg','-y','-v','error','-safe','0','-i',str(root/'playback.ffconcat'),'-vf','scale=iw*3:ih*3:flags=neighbor','-r','60','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(root/'production-react.mp4')],check=True)
print('Actual mouse recording complete',root)
