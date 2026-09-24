"""Conservative static tripwires for the frozen Alpha runtime; not semantic/native QA."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Inventory catches additions/removals of scheduling, networking and logging call sites.
PATTERN = re.compile(r'thread::spawn|setInterval|requestAnimationFrame|mpsc::(?:sync_)?channel|fetch\(|\.send\(|\.request\(|println!|NSLog\(|LOG\.(?:warn|error|info|debug)')
FORBIDDEN = re.compile(r'activateIgnoringOtherApps|makeKeyAndOrderFront|makeKeyWindow|\.set_focus\(|\.request_user_attention\(')

def sources(root=ROOT):
    result = {}
    for folder in ['src', 'src-tauri/src', 'src-tauri/native', 'server/src/main/java']:
        for path in (root/folder).rglob('*'):
            if path.suffix not in ('.rs','.m','.ts','.tsx','.java'): continue
            if 'tests' in path.parts or path.stem in ('tests','alpha_vertical_slice'): continue
            result[str(path.relative_to(root))] = path.read_text().split('#[cfg(test)]')[0]
    return result

def inventory(code):
    return {path: sorted(line.strip() for line in text.splitlines() if PATTERN.search(line))
            for path,text in sorted(code.items()) if PATTERN.search(text)}

def check(code, baseline):
    errors=[]
    for path,text in code.items():
        if path.startswith(('src-tauri/src/','src-tauri/native/')) and FORBIDDEN.search(text):
            errors.append(f'{path}: focus-sensitive API requires review')
    if inventory(code) != baseline:
        errors.append('runtime scheduling/network/logging inventory differs from reviewed Alpha baseline')
    panel=code.get('src-tauri/native/panel.m','')
    for contract in ['canBecomeKeyWindow { return NO; }','canBecomeMainWindow { return NO; }','NSWindowStyleMaskNonactivatingPanel']:
        if contract not in panel: errors.append('nonactivating panel contract missing: '+contract)
    main=code.get('src-tauri/src/main.rs','')
    plugin='.plugin(tauri_plugin_single_instance::init(|_, _, _| {}))'
    if plugin not in main or main.index(plugin)>main.find('.setup('):
        errors.append('single-instance no-op callback must precede setup')
    backend=code.get('src-tauri/src/backend/mod.rs','')
    for contract in ['mpsc::sync_channel(1)','mpsc::sync_channel(8)', '.connect_timeout(Duration::from_secs(1))','.timeout(Duration::from_secs(3))']:
        if contract not in backend: errors.append('bounded worker contract missing: '+contract)
    return errors

if __name__=='__main__':
    errors=check(sources(),json.loads((ROOT/'docs/evidence/alpha-release-runtime-inventory.json').read_text()))
    for error in errors: print('FAIL:',error)
    print('FAIL' if errors else 'PASS: focus, single-instance order, bounded worker and runtime call-site inventory')
    raise SystemExit(bool(errors))
