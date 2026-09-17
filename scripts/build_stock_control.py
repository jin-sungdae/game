#!/usr/bin/env python3
"""Build a configuration-only control against registry Tao (no local patch).
Uses the same app/behavior/native audit code and Accessory-before-run policy.
Usage: python3 scripts/build_stock_control.py OUTPUT_BINARY
Requires npm run build first. Never changes the working tree or final app bundle.
"""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='luma-stock-') as directory:
    project=Path(directory)
    for name in ('src','native','capabilities','icons'):
        shutil.copytree(root/'src-tauri'/name,project/name)
    shutil.copy2(root/'src-tauri/build.rs',project/'build.rs')
    manifest=(root/'src-tauri/Cargo.toml').read_text().split('# Feature unification')[0]
    (project/'Cargo.toml').write_text(manifest)
    config=json.loads((root/'src-tauri/tauri.conf.json').read_text())
    config['build']={'frontendDist':str(root/'dist')}
    (project/'tauri.conf.json').write_text(json.dumps(config))
    env=os.environ.copy()
    env['CARGO_TARGET_DIR']=str(root/'src-tauri/target')
    subprocess.run(['cargo','build','--offline','--manifest-path',str(project/'Cargo.toml'),'--features','tauri/custom-protocol'],env=env,check=True)
    shutil.copy2(root/'src-tauri/target/debug/luma-spike',sys.argv[1])
    print('Control binary:',sys.argv[1])
