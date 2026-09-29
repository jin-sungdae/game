"""Integrated animation + facing capture on the production release; no domain instrumentation."""
import argparse,json,subprocess as sp,time
from pathlib import Path
from session import Session
p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();root=a.root;s=Session(root/'session');cfg=s.config
assert cfg['captureOnly'] and (s.root/'pg').is_dir()
query="UPDATE game.m_monster SET encounter_weight=CASE WHEN code='PIP' THEN 100 ELSE 0 END;"
sp.run([str(Path(cfg['pgBin'])/'psql'),'-h','127.0.0.1','-p',str(cfg['dbPort']),'-U','luma','-d','luma_gui_qa_test','-v','ON_ERROR_STOP=1','-c',query],check=True)
s.native('right',*s.center('moa'));time.sleep(.3)
for _ in range(80):
 try:
  enc=s.api('encounters/active');panel=s.panel('pip')
  if enc and enc['monster']['code']=='PIP':break
 except (RuntimeError,OSError):pass
 time.sleep(.2)
else:raise RuntimeError('normal safe placement unavailable')
(root/'encounter.json').write_text(json.dumps(enc,indent=2));s.native('move',800,200)
children=[];captures={};windows={}
for name,cmd in [('pip','frames-pip')]:
 children.append(sp.Popen([s.helper,cmd,str(s.pid),'52'],stdout=(root/(name+'-trace.jsonl')).open('w')))
 windows[name]=s.panel(name)['kCGWindowNumber'];captures[name]=[];(root/(name+'-frames')).mkdir()
# Native window screenshots are actual production pixels. Timestamp each completed
# capture; do not synthesize renderer frames or pretend this is a 60fps observation.
started=time.monotonic()
while time.monotonic()-started<50:
 for name in ['pip']:
  file='frame-%05d.png'%len(captures[name]);before=time.time()
  sp.run(['/usr/sbin/screencapture','-x','-l',str(windows[name]),str(root/(name+'-frames')/file)],check=True,timeout=5)
  captures[name].append({'file':file,'pts':time.monotonic()-started,'wallTime':time.time(),'before':before,'width':192,'height':208})
 # Capture as fast as native window capture returns; timestamps preserve real pacing.
for name,rows in captures.items():(root/(name+'-frames')/'frames.json').write_text(json.dumps({'method':'native screencapture window-only','frames':rows},indent=2))
for c in children:c.wait()
s.save('after-capture',s.ax())
for name in ['pip']:
 rows=json.loads((root/(name+'-frames')/'frames.json').read_text())['frames'];lines=['ffconcat version 1.0']
 for i,r in enumerate(rows):lines += ["file '"+name+'-frames/'+r['file']+"'",'option framerate 1000','duration '+str(rows[i+1]['pts']-r['pts'] if i+1<len(rows) else 1/60)]
 lines += ["file '"+name+'-frames/'+rows[-1]['file']+"'",'option framerate 1000'];path=root/(name+'.ffconcat');path.write_text('\n'.join(lines)+'\n')
 sp.run(['ffmpeg','-y','-v','error','-safe','0','-i',str(path),'-vf','scale=iw*3:ih*3:flags=neighbor','-r','60','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(root/(name+'.mp4'))],check=True)
print('Actual release capture complete')
