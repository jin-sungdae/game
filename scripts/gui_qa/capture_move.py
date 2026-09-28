"""Observe unchanged release-app autonomous walking; no forced state, velocity or seed."""
import argparse,json,subprocess as sp,time,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--seconds',type=int,default=1200);a=p.parse_args();root=a.root.resolve();cfg=json.loads((root/'session/session.json').read_text());helper=cfg['helper'];pid=cfg['appPid'];frames=root/'playback-frames';frames.mkdir()
# Pointer stays away from the ground companion, without any click/focus changes.
sp.run([helper,'move','800','200'],check=True)
fast=sp.Popen([helper,'frames',str(pid),str(a.seconds+5)],stdout=(root/'frame-trace.jsonl').open('w'))
rec=sp.Popen([root/'record-window',str(pid),str(a.seconds),frames],stdout=(root/'record.log').open('w'),stderr=sp.STDOUT)
last=None;move_seconds=0.;directions=set();rows=0;had_move=False;returned=False;blink_return=False;start=time.monotonic();reader=(root/'frame-trace.jsonl').open();network=(root/'runtime-trace.jsonl').open('w')
try:
 while rec.poll() is None:
  for line in reader:
   try:row=json.loads(line)
   except json.JSONDecodeError:continue
   rows+=1;label=row.get('label','');moving=' MOVE ' in label
   if moving:had_move=True;returned=False
   elif had_move and ' IDLE ' in label:returned=True
   elif returned and ' BLINK ' in label:blink_return=True
   if last:
    dt=row['after']-last['after']
    if moving and ' MOVE ' in last.get('label','') and 0<dt<.2:
     move_seconds+=dt
     if row.get('panels') and last.get('panels'):
      dx=row['panels'][0]['X']-last['panels'][0]['X']
      if abs(dx)>.05:directions.add('RIGHT' if dx>0 else 'LEFT')
   last=row
  (root/'progress.json').write_text(json.dumps({'elapsed':time.monotonic()-start,'moveSeconds':move_seconds,'directions':sorted(directions),'returnedToIdle':returned,'blinkAfterMove':blink_return,'samples':rows,'last':last},indent=2))
  if move_seconds>=22 and len(directions)==2 and returned and blink_return:
   (frames/'stop').touch()
  # Low-rate full AX read retains network observer without altering app execution.
  ax=json.loads(sp.check_output([helper,'ax',str(pid)],text=True));network.write(json.dumps({'time':time.time(),'ax':ax})+'\n');network.flush();time.sleep(.5)
finally:
 fast.terminate();fast.wait();network.close();reader.close()
if rec.returncode:raise RuntimeError('capture failed')
rows=json.loads((frames/'frames.json').read_text())['frames'];lines=['ffconcat version 1.0']
for i,row in enumerate(rows):lines += ["file 'playback-frames/"+row['file']+"'",'option framerate 1000','duration '+str(rows[i+1]['pts']-row['pts'] if i+1<len(rows) else 1/60)]
lines += ["file 'playback-frames/"+rows[-1]['file']+"'",'option framerate 1000'];(root/'playback.ffconcat').write_text('\n'.join(lines)+'\n')
sp.run(['ffmpeg','-y','-v','error','-safe','0','-i',str(root/'playback.ffconcat'),'-vf','scale=iw*3:ih*3:flags=neighbor','-r','60','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(root/'production-move.mp4')],check=True)
print('Actual autonomous capture complete',root,flush=True)
