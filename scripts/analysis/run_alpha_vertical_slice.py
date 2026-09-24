#!/usr/bin/env python3
"""Opt-in bootJar + compiled World certification in newly created PostgreSQL16 DBs.
Requires PG_BIN, JAVA_HOME and built server bootJar; never accepts an existing database.
No production defaults, RNG, progression, prices, thresholds or rewards are overwritten.
"""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess as sp
import tempfile
import time
import urllib.request
import urllib.error

ROOT=Path(__file__).resolve().parents[2]

def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0))
        return s.getsockname()[1]

def run(output, release=False):
    pg=Path(os.environ['PG_BIN']);java=Path(os.environ['JAVA_HOME'])/'bin/java'
    assert ' 16.' in sp.check_output([pg/'postgres','--version'],text=True), 'PostgreSQL16 required'
    jar=ROOT/'server/build/libs/luma-game-server-0.1.0.jar'
    assert jar.is_file(), 'Build actual bootJar first'
    output.mkdir(parents=True,exist_ok=False)  # Refuse overwriting evidence or prior state.
    db_port,server_port=free_port(),free_port()
    while server_port == db_port: server_port=free_port()
    clean_env={k:v for k,v in os.environ.items() if not k.startswith(('SPRING_', 'LUMA_DB_', 'LUMA_TEST_DB_'))}
    env=dict(clean_env,LUMA_DB_USER='luma',LUMA_DB_PASSWORD='',LUMA_TEST_DB_USER='luma',LUMA_TEST_DB_PASSWORD='',LUMA_GAME_SERVER_URL=f'http://127.0.0.1:{server_port}',LUMA_ALPHA_OUTPUT=str(output))
    server=None
    with tempfile.TemporaryDirectory(prefix='luma-alpha-pg-') as data:
        def command(args,name,extra=None):
            with (output/name).open('w') as log:
                sp.run([str(a) for a in args],cwd=ROOT,env=extra or env,stdout=log,stderr=sp.STDOUT,check=True)
        def sql(query):
            return sp.check_output([pg/'psql','-h','127.0.0.1','-p',str(db_port),'-U','luma','-d','luma_alpha_slice_test','-At','-v','ON_ERROR_STOP=1','-c',query],text=True).strip()
        def start(label):
            nonlocal server
            with (output/f'spring-{label}.log').open('w') as log:
                server=sp.Popen([str(java),'-jar',str(jar)],cwd=ROOT,
                    env=dict(env,LUMA_SERVER_PORT=str(server_port),LUMA_DB_URL=f'jdbc:postgresql://127.0.0.1:{db_port}/luma_alpha_slice_test'),stdout=log,stderr=sp.STDOUT)
            deadline=time.monotonic()+40
            while time.monotonic()<deadline:
                if server.poll() is not None:raise RuntimeError('bootJar stopped')
                try:
                    with urllib.request.urlopen(env['LUMA_GAME_SERVER_URL']+'/api/v1/game/bootstrap',timeout=1):return
                except (OSError,TimeoutError):time.sleep(.2)
            raise TimeoutError('bootJar startup')
        def stop():
            nonlocal server
            if server is not None:
                server.terminate();server.wait(timeout=15);server=None
        def phase(name):
            command(['cargo','test','--locked','--manifest-path','src-tauri/Cargo.toml','live_alpha_vertical_slice','--','--ignored','--nocapture'],f'world-{name}.log',dict(env,LUMA_ALPHA_PHASE=name))
        def history():
            return json.loads(sql("SELECT coalesce(json_agg(row_to_json(h) ORDER BY evolved_at),'[]') FROM (SELECT from_stage,to_stage,level_at_evolution,bond_at_evolution,evolved_at FROM game.t_companion_evolution_history ORDER BY evolved_at) h"))
        started=False
        try:
            command([pg/'initdb','-D',data,'-U','luma','-A','trust'],'initdb.log')
            command([pg/'pg_ctl','-D',data,'-l',output/'postgres.log','-o',f'-p {db_port} -h 127.0.0.1','start'],'pg-start.log');started=True
            command([pg/'createdb','-h','127.0.0.1','-p',str(db_port),'-U','luma','luma_alpha_slice_test'],'createdb.log')
            if release:
                command([pg/'createdb','-h','127.0.0.1','-p',str(db_port),'-U','luma','luma_alpha_regression_test'],'regression-db.log')
                command(['./server/gradlew','-p','server','test','bootJar','--rerun-tasks','--no-daemon'],'server-tests.log',dict(env,LUMA_TEST_DB_URL=f'jdbc:postgresql://127.0.0.1:{db_port}/luma_alpha_regression_test'))
            start('fresh');phase('fresh');stop();phase('offline')
            # Explicit authorized clock fixture only: no EXP/Bond/Gold/stage/inventory SQL updates.
            start('discovery-restart')
            sql("UPDATE game.t_player_companion SET last_bond_interaction_at=clock_timestamp()-interval '300 seconds' WHERE active")
            phase('progress')
            before=history();assert [(r['from_stage'],r['to_stage']) for r in before]==[(1,2),(2,3)]
            (output/'history-before.json').write_text(json.dumps(before,indent=2))
            masters=json.loads(sql("SELECT json_agg(row_to_json(m) ORDER BY monster_id) FROM (SELECT monster_id,code,rarity,min_level,max_level,encounter_weight,use_yn FROM game.m_monster WHERE use_yn) m"))
            assert len(masters)==15 and sum(r['encounter_weight'] for r in masters)==961
            (output/'masters.json').write_text(json.dumps(masters,indent=2))
            stop();start('nebla-restart');phase('restored');assert before==history()
            (output/'history-after.json').write_text(json.dumps(history(),indent=2))
            (output/'run.json').write_text(json.dumps({'result':'PASS','head':sp.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'postgresVersion':sp.check_output([pg/'postgres','--version'],text=True).strip(),'db':'new isolated luma_alpha_slice_test','clockInjection':'last_bond_interaction_at only, after first restart','progressionSqlWrites':False,'serverRestarts':2,'worldProcesses':['fresh','offline','progress','restored']},indent=2))
            if release:
                # Only our disposable cluster is stopped. Real bootJar must return a bounded 503.
                command([pg/'pg_ctl','-D',data,'stop'],'db-runtime-stop.log');started=False
                began=time.monotonic()
                try:
                    urllib.request.urlopen(env['LUMA_GAME_SERVER_URL']+'/api/v1/game/bootstrap',timeout=12)
                    raise AssertionError('unavailable DB unexpectedly succeeded')
                except urllib.error.HTTPError as error:
                    assert error.code == 503
                    body=json.loads(error.read())
                    assert body['code']=='GAME_UNAVAILABLE'
                elapsed=time.monotonic()-began
                stop()
                canary='luma-release-ephemeral-canary'
                with (output/'db-startup-failure.log').open('w') as log:
                    bad=sp.run([str(java),'-jar',str(jar)],cwd=ROOT,env=dict(env,LUMA_SERVER_PORT=str(server_port),LUMA_DB_URL=f'jdbc:postgresql://127.0.0.1:{db_port}/luma_alpha_slice_test',LUMA_DB_PASSWORD=canary),stdout=log,stderr=sp.STDOUT,timeout=40)
                assert bad.returncode != 0
                text=(output/'db-startup-failure.log').read_text()
                assert 'Connection refused' in text or 'connection attempt failed' in text
                assert canary not in text
                (output/'db-failure.json').write_text(json.dumps({'runtimeStatus':503,'runtimeSeconds':elapsed,'startupExit':bad.returncode,'credentialCanaryAbsent':True},indent=2))
            print((output/'summary.json').read_text(),flush=True)
        finally:
            stop()
            if started:command([pg/'pg_ctl','-D',data,'stop'],'pg-stop.log')
    print('ALPHA PASS; isolated Spring/PostgreSQL stopped; evidence:',output,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path)
    run(p.parse_args().output.resolve())
