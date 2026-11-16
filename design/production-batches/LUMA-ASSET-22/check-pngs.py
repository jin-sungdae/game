"""Validate all scoped PNGs without rewriting earlier evidence or shared files."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from visual_asset_inventory import candidate

folder = Path(__file__).resolve().parent
results = []
for identity in ['M092', 'M095']:
    base = ROOT / 'design/production-batches/monsters/batch10' / identity / 'base-v2.png'
    for image in sorted((folder / identity).rglob('*.png')):
        result = candidate(image, base)
        result['candidate'] = str(image.relative_to(ROOT))
        result['reference'] = str(base.relative_to(ROOT))
        results.append(result)
print(json.dumps({'scope': 'PNG format and registration only; no animation or Production approval', 'files': results}, indent=2))
sys.exit(1 if any(result['errors'] for result in results) else 0)
