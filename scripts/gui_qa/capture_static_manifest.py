"""Actual production window recording plus document-start fetch/XHR/CSP trace, no CSP override."""
import argparse,json,subprocess as sp,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--recorder',type=Path,required=True);a=p.parse_args();root=a.root.resolve();cfg=json.loads((root/'session/session.json').read_text());helper=cfg['helper'];pid=cfg['appPid']
def native(*args):return json.loads(sp.check_output([helper,*map(str,args)],text=True))
snap=native('snapshot',pid);window=next(w for w in snap['windows'] if w.get('kCGWindowName')=='moa');b=window['kCGWindowBounds'];sp.run([helper,'move',str(b['X']+b['Width']+40),str(b['Y']+60)],check=True);time.sleep(2)
frames=root/'playback-frames';recorder=sp.Popen([a.recorder,str(pid),'8',frames],stdout=(root/'record.log').open('w'),stderr=sp.STDOUT)
with (root/'runtime-trace.jsonl').open('w') as log:
 while recorder.poll() is None:
  row={'time':time.time(),'images':[],'network':[]};ax=native('ax',pid)
  def visit(n):
   label=n.get('AXDescription','')
   if label.startswith('MOA ' ) and n.get('AXRole')=='AXImage':row['images'].append({k:v for k,v in n.items() if k!='children'})
   if label.startswith('LUMA_METADATA_AUDIT '):row['network'].append(json.loads(label[len('LUMA_METADATA_AUDIT '):]))
   for child in n.get('children',[]):visit(child)
  visit(ax);log.write(json.dumps(row)+'\n');log.flush();time.sleep(.025)
if recorder.returncode:raise RuntimeError('recording failed')
rows=json.loads((frames/'frames.json').read_text())['frames'];assert rows[-1]['pts']-rows[0]['pts']>=5
lines=['ffconcat version 1.0']
for i,row in enumerate(rows):
 lines += ["file 'playback-frames/"+row['file']+"'",'option framerate 1000','duration '+str(rows[i+1]['pts']-row['pts'] if i+1<len(rows) else 1/60)]
lines += ["file 'playback-frames/"+rows[-1]['file']+"'",'option framerate 1000'];concat=root/'playback.ffconcat';concat.write_text('\n'.join(lines)+'\n')
sp.run(['ffmpeg','-y','-v','error','-safe','0','-i',str(concat),'-vf','scale=iw*3:ih*3:flags=neighbor','-r','60','-c:v','libx264','-crf','15','-pix_fmt','yuv420p','-movflags','+faststart',str(root/'production-static-playback.mp4')],check=True)
print('Production capture complete',root)
