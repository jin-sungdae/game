"""Drive only the existing native Debug PIP menu for a bounded GUI soak workload."""
import argparse,time,json
from session import Session
p=argparse.ArgumentParser();p.add_argument('directory');p.add_argument('--cycles',type=int,default=10);a=p.parse_args();s=Session(a.directory)
with (s.root/'lifecycle.jsonl').open('w') as log:
    for i in range(a.cycles):
        for action,delay in [('Debug: Despawn PIP',3),('Debug: Spawn PIP',75)]:
            result=s.press(action);log.write(json.dumps({'timestamp':time.time(),'pid':s.pid,'cycle':i,'action':action,'result':json.loads(result)})+'\n');log.flush();time.sleep(delay)
