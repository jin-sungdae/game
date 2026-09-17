#!/usr/bin/env python3
"""Offline integrity check: only the documented files may differ from Tao 0.35.3."""
from pathlib import Path
import hashlib, json
root = Path(__file__).resolve().parents[1]
vendor = root / 'src-tauri/vendor/tao'
baseline = json.loads((root / 'docs/evidence/tao-0.35.3-sha256.json').read_text())
allowed = {'Cargo.toml', 'Cargo.toml.orig', 'src/platform_impl/macos/app_state.rs'}
changed = set()
for name, digest in baseline.items():
    data = (vendor / name).read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        changed.add(name)
assert changed == allowed, f'Unexpected vendor changes: {changed ^ allowed}'
assert {str(p.relative_to(vendor)) for p in vendor.rglob('*') if p.is_file()} == set(baseline), 'Unexpected added/removed vendor files'
source = (vendor / 'src/platform_impl/macos/app_state.rs').read_text()
assert '#[cfg(not(feature = "macos-no-activate-on-launch"))]' in source
print('PASS: Tao differs from registry source in exactly 3 documented files')
