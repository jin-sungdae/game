"""Recheck isolated candidates using existing PNG checks and local rig regression."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from visual_asset_inventory import candidate

folder = Path(__file__).resolve().parent
subprocess.run(['node', str(folder / 'validate.cjs')], cwd=ROOT, check=False)
failed = False
for identity in ['M092', 'M095']:
    evidence = folder / identity / 'frame-validation.json'
    result = json.loads(evidence.read_text())
    checks = []
    for frame in sorted((folder / identity / 'rigged/breath').glob('*.png')):
        check = candidate(frame, ROOT / 'design/production-batches/monsters/batch10' / identity / 'base-v2.png')
        check['candidate'] = str(frame.relative_to(ROOT))
        check['reference'] = str(Path(check['reference']).relative_to(ROOT))
        checks.append(check)
    result['existingPngValidator'] = checks
    if len(checks) != 8 or any(check['errors'] for check in checks):
        result['automated'] = 'FAIL'
    failed |= result['automated'] != 'PASS'
    evidence.write_text(json.dumps(result, indent=2) + '\n')
    print(identity, result['automated'], flush=True)
sys.exit(1 if failed else 0)
