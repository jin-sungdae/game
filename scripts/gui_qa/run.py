#!/usr/bin/env python3
"""Opt-in actual GUI smoke. Owns a NEW isolated save; never grants permissions or hides user apps.
Requires Java21/PG_BIN, built production app and bootJar. Run on an interactive macOS session.
The --keep-running option retains only owned processes for further QA; stop via stop.py.
"""
import argparse,json,os,subprocess as sp,time,urllib.request,socket
from pathlib import Path
from session import Session
ROOT=Path(__file__).resolve().parents[2]
def free_port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--keep-running',action='store_true');a=p.parse_args()
    root=a.output.resolve();root.mkdir(parents=True,exist_ok=False);(root/'screenshots').mkdir();(root/'access').mkdir()
    helper=root/'native-qa';sp.run(['clang','-fobjc-arc','-framework','AppKit','-framework','ApplicationServices',str(ROOT/'scripts/gui_qa/native.m'),'-o',str(helper)],check=True)
    caps=json.loads(sp.check_output([helper,'probe'],text=True));(root/'capabilities.json').write_text(json.dumps(caps,indent=2))
    if not all(caps[k] for k in ['accessibility','screenRecording','postEvent']):
        raise SystemExit('PERMISSION_REQUIRED: authorize the launching Codex/Terminal app in Accessibility and Screen Recording, then use a new output directory.')
    pg=Path(os.environ['PG_BIN']);java=Path(os.environ['JAVA_HOME'])/'bin/java';db=free_port();port=free_port()
    while port==db:port=free_port()
    cfg={'helper':str(helper),'serverUrl':f'http://127.0.0.1:{port}','dbPort':db,'headSha':sp.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'appBundle':str(a.bundle.resolve()),'bundleId':'dev.luma.spike','pgBin':str(pg)}
    (root/'session.json').write_text(json.dumps(cfg,indent=2))
    try:
        for args in [[pg/'initdb','-D',root/'pg','-U','luma','-A','trust'],[pg/'pg_ctl','-D',root/'pg','-l',root/'postgres.log','-o',f'-p {db} -h 127.0.0.1','start'],[pg/'createdb','-h','127.0.0.1','-p',str(db),'-U','luma','luma_gui_qa_test']]:
            sp.run(list(map(str,args)),check=True,stdout=sp.DEVNULL)
        env={k:v for k,v in os.environ.items() if not k.startswith(('SPRING_','LUMA_'))}
        env.update(LUMA_DB_URL=f'jdbc:postgresql://127.0.0.1:{db}/luma_gui_qa_test',LUMA_DB_USER='luma',LUMA_DB_PASSWORD='',LUMA_SERVER_PORT=str(port),SERVER_TOMCAT_ACCESSLOG_ENABLED='true',SERVER_TOMCAT_ACCESSLOG_DIRECTORY=str(root/'access'))
        with (root/'server.log').open('w') as log:server=sp.Popen([str(java),'-jar',str(ROOT/'server/build/libs/luma-game-server-0.1.0.jar')],cwd=ROOT,env=env,stdout=log,stderr=sp.STDOUT,start_new_session=True)
        (root/'server-process-group').write_text(str(server.pid))
        for _ in range(80):
            if server.poll() is not None:raise RuntimeError('bootJar exited')
            try:
                with urllib.request.urlopen(cfg['serverUrl']+'/api/v1/game/bootstrap',timeout=1) as response:(root/'fresh.json').write_bytes(response.read())
                break
            except OSError:time.sleep(.25)
        else:raise TimeoutError('server bootstrap')
        sp.run(['open','-n','--stdout',str(root/'app.log'),'--stderr',str(root/'app.log'),'--env','LUMA_GAME_SERVER_URL='+cfg['serverUrl'],'--env','LUMA_FOCUS_AUDIT=1',cfg['appBundle']],check=True)
        for _ in range(80):
            text=(root/'app.log').read_text() if (root/'app.log').exists() else ''
            rows=[json.loads(x[len('LUMA_AUDIT '):]) for x in text.splitlines() if x.startswith('LUMA_AUDIT ')]
            if rows and '[LUMA STATE]' in text:break
            time.sleep(.25)
        else:raise RuntimeError('new World did not start; quit another LUMA primary before retrying')
        cfg['appPid']=rows[0]['pid'];(root/'session.json').write_text(json.dumps(cfg,indent=2))
        s=Session(root);s.save('launch-ax',s.ax());s.capture('01-launch')
        # Create a dedicated scratch document; never overwrite an existing user document.
        sp.run(['osascript','-e','tell application "TextEdit" to make new document with properties {text:""}'],check=True)
        s.focus('movement',6);s.save('click-before',{'server':s.api('game/bootstrap'),'gui':s.snapshot()});s.click('moa');time.sleep(1);s.save('click-after',{'server':s.api('game/bootstrap'),'gui':s.snapshot()})
        print('Actual GUI smoke complete:',root,'; manual/sweep/evolution/soak require their own evidence.')
    finally:
        if not a.keep_running:sp.run(['python3',str(ROOT/'scripts/gui_qa/stop.py'),str(root)],check=False)
if __name__=='__main__':main()
