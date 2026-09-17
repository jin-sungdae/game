#!/usr/bin/env python3
"""Sample explicit process IDs. ps %CPU is OS's decaying average, RSS is KiB.
Include WebKit helper PIDs after identifying them in Activity Monitor.
Usage: python3 scripts/measure.py PID [HELPER_PID ...] --seconds 30
"""
import argparse, subprocess, time, json, statistics
p=argparse.ArgumentParser();p.add_argument('pids',type=int,nargs='+');p.add_argument('--seconds',type=int,default=30);a=p.parse_args()
rows=[]
for _ in range(a.seconds):
    output=subprocess.check_output(['ps','-p',','.join(map(str,a.pids)),'-o','pid=,%cpu=,rss='],text=True)
    processes=[dict(zip(('pid','cpu_percent','rss_kib'),map(float,line.split()))) for line in output.splitlines()]
    rows.append({'time':time.time(),'processes':processes,'cpu_percent':sum(x['cpu_percent'] for x in processes),'rss_mib':sum(x['rss_kib'] for x in processes)/1024})
    time.sleep(1)
print(json.dumps({'pids':a.pids,'samples':rows,'cpu_mean':statistics.mean(r['cpu_percent'] for r in rows),'cpu_max':max(r['cpu_percent'] for r in rows),'rss_mean_mib':statistics.mean(r['rss_mib'] for r in rows),'rss_max_mib':max(r['rss_mib'] for r in rows)},indent=2))
