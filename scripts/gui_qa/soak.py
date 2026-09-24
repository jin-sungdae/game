"""Actual elapsed-time observer. Does not accelerate time or mutate gameplay."""
import argparse,json,subprocess as sp,time
from pathlib import Path
from session import Session
p=argparse.ArgumentParser();p.add_argument('directory');p.add_argument('--seconds',type=float,default=1800);a=p.parse_args()
s=Session(a.directory);start=time.monotonic();rows=[]
with (s.root/'resource-trace.jsonl').open('w') as log:
    while True:
        elapsed=time.monotonic()-start
        state=sp.run(['ps','-p',str(s.pid),'-o','%cpu=,rss=,etime='],capture_output=True,text=True)
        row={'timestamp':time.time(),'elapsedSeconds':elapsed,'pid':s.pid,'alive':state.returncode==0,'process':state.stdout.strip()}
        if state.returncode==0:
            parts=state.stdout.split();row.update(cpuPercent=float(parts[0]),rssKB=int(parts[1]))
            row['threads']=max(0,len(sp.check_output(['ps','-M','-p',str(s.pid)],text=True).splitlines())-1)
            row['openFiles']=len(sp.check_output(['lsof','-p',str(s.pid)],text=True).splitlines())-1
            row['windows']=s.snapshot()['windows']
            row['requestCount']=sum(len(f.read_text().splitlines()) for f in (s.root/'access').glob('*') if f.is_file())
        rows.append(row);log.write(json.dumps(row)+'\n');log.flush()
        if elapsed>=a.seconds or not row['alive']:break
        time.sleep(min(15,a.seconds-(time.monotonic()-start)))
s.save('soak-result',{'pid':s.pid,'elapsedSeconds':rows[-1]['elapsedSeconds'],'requiredSeconds':a.seconds,'completed30Minutes':rows[-1]['elapsedSeconds']>=1800 and all(r['alive'] for r in rows),'samples':len(rows),'rssFirstKB':rows[0].get('rssKB'),'rssLastKB':rows[-1].get('rssKB'),'rssPeakKB':max(r.get('rssKB',0) for r in rows),'threadsFirst':rows[0].get('threads'),'threadsLast':rows[-1].get('threads'),'windowMax':max(len(r.get('windows',[])) for r in rows),'notes':'Resource evidence only; inspect trend and workload before classification.'})
