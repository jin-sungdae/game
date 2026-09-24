#!/usr/bin/env python3
"""One macOS Alpha release gate composing existing tests; manual QA never becomes PASS here."""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/analysis'))
from run_alpha_vertical_slice import run as live_run

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,help='new evidence directory; default temporary directory')
    args=parser.parse_args()
    out=args.output.resolve() if args.output else Path(tempfile.mkdtemp(prefix='luma-release-'))/'evidence'
    out.mkdir(parents=True,exist_ok=False)
    rows=[]
    def step(name,cmd):
        print(name,flush=True);start=time.monotonic()
        with (out/(name+'.log')).open('w') as log:
            result=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        rows.append({'name':name,'status':'PASS' if result.returncode==0 else 'FAIL','seconds':round(time.monotonic()-start,2)})
        if result.returncode: raise RuntimeError(f'{name} failed; see {out/name}.log')
    result='FAIL'
    try:
        if platform.system()!='Darwin': raise RuntimeError('macOS required for full native release gate; no partial AUTOMATED_READY')
        for key in ['JAVA_HOME','PG_BIN']:
            if not os.environ.get(key): raise RuntimeError(key+' required (Java21 / PostgreSQL16)')
        step('frontend-build',['npm','run','build'])
        step('animation-content',['npm','run','test:animation'])
        step('presentation',['npm','run','test:presentation'])
        step('asset-tests',['npm','run','test:assets'])
        step('optional-assets',['npm','run','validate:assets','--','--allow-missing'])
        step('strict-alpha',['npm','run','validate:alpha:strict'])
        step('required-bases',['python3','scripts/validate_assets.py','--release'])
        step('automation-policy',['python3','-m','unittest','discover','-s','tests/automation','-v'])
        step('release-static',['python3','scripts/alpha_release_policy.py'])
        step('tao-integrity',['python3','scripts/check_tao_patch.py'])
        step('rust-fmt',['cargo','fmt','--manifest-path','src-tauri/Cargo.toml','-p','luma-spike','--','--check'])
        step('rust-tests-native-link',['cargo','test','--locked','--manifest-path','src-tauri/Cargo.toml'])
        step('rust-clippy',['cargo','clippy','--locked','--manifest-path','src-tauri/Cargo.toml','--no-deps','--','-D','warnings'])
        for harness in ['launch_audit','single_instance_audit']:
            step(harness,['clang','-fobjc-arc','-framework','AppKit','scripts/'+harness+'.m','-o',str(out/harness)])
        step('bootJar',['./server/gradlew','-p','server','bootJar','--no-daemon'])
        print('Isolated PostgreSQL16 server regression, fresh/persistence/network/DB smoke',flush=True)
        live_run(out/'live',release=True)
        rows.append({'name':'server-fresh-persistence-failures','status':'PASS'})
        step('whitespace',['git','diff','--check'])
        result='AUTOMATED_READY'
    finally:
        report={'status':result,'manualGate':'MANUAL_QA_REQUIRED','head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'workingTreeDirty':bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()),'checks':rows}
        (out/'release-result.json').write_text(json.dumps(report,indent=2)+'\n')
        print(result,'MANUAL_QA_REQUIRED',out,flush=True)

if __name__=='__main__': main()
