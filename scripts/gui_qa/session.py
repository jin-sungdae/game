"""QA-only helpers for real macOS processes. Artifacts stay outside the repository."""
import json,os,subprocess as sp,time,urllib.request
from pathlib import Path

class Session:
    def __init__(self, root):
        self.root=Path(root);self.config=json.loads((self.root/'session.json').read_text())
        self.pid=self.config.get('appPid',0);self.helper=self.config['helper'];self.url=self.config['serverUrl']
    def native(self,*args):
        return sp.check_output([self.helper,*map(str,args)],text=True)
    def snapshot(self):return json.loads(self.native('snapshot',self.pid))
    def ax(self):return json.loads(self.native('ax',self.pid))
    def save(self,name,data):
        (self.root/(name+'.json')).write_text(json.dumps(data,indent=2));return data
    def api(self,path,post=False):
        req=urllib.request.Request(self.url+'/api/v1/'+path,method='POST' if post else 'GET')
        with urllib.request.urlopen(req,timeout=8) as r:
            data=r.read();return json.loads(data) if data else None
    def capture(self,name):
        snap=self.snapshot();self.save(name+'-windows',snap)
        files=[]
        for index,w in enumerate(snap['windows']):
            if w.get('kCGWindowLayer')!=3: continue
            path=self.root/'screenshots'/f'{name}-{index}.png'
            result=sp.run(['/usr/sbin/screencapture','-x','-l',str(w['kCGWindowNumber']),str(path)],capture_output=True,text=True)
            files.append({'windowId':w['kCGWindowNumber'],'path':str(path),'exit':result.returncode,'error':result.stderr})
        self.save(name+'-capture',{'timestamp':time.time(),'pid':self.pid,'files':files});return files
    def panel(self,name):
        for w in self.snapshot()['windows']:
            if w.get('kCGWindowName')==name:return w
        raise RuntimeError('panel not found: '+name)
    def center(self,name):
        b=self.panel(name)['kCGWindowBounds'];return (b['X']+b['Width']/2,b['Y']+b['Height']*.65)
    def click(self,name):self.native('click',*self.center(name))
    def press(self,label):return self.native('press',self.pid,label)
    def focus(self,name,seconds=8):
        # TextEdit activation is test setup, never production focus restoration.
        sp.run(['osascript','-e','tell application "TextEdit" to activate'],check=True,stdout=sp.DEVNULL)
        time.sleep(.2)
        with (self.root/(name+'-focus.jsonl')).open('w') as log:
            observer=sp.Popen([self.helper,'observe',str(self.pid),str(seconds)],stdout=log)
            marker='';start=time.monotonic();i=0
            while time.monotonic()-start<seconds-.4:
                line=f'LUMA_FOCUS_{name}_{i:04d}\n';self.native('type',line);marker+=line;i+=1
            observer.wait()
        time.sleep(.25)  # Allow the last posted native key-up to be consumed.
        actual=sp.check_output(['osascript','-e','tell application "TextEdit" to get text of front document'],text=True)
        rows=[json.loads(x) for x in (self.root/(name+'-focus.jsonl')).read_text().splitlines()]
        self.save(name+'-typing',{'expected':marker,'documentContainsAll':marker in actual,'frontmostAlwaysTextEdit':all(x['frontBundle']=='com.apple.TextEdit' for x in rows),'focusedRoles':sorted(set(x['focused'].get('AXRole','') for x in rows)),'sampleCount':len(rows)})
        return rows
