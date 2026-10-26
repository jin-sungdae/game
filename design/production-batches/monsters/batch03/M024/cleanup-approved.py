"""One user-approved recovery; preserves all original files and body RGBA pixels."""
from pathlib import Path
import hashlib
import json
import sys
from PIL import Image

folder = Path(__file__).resolve().parent
root = folder.parents[4]
sys.path.insert(0, str(root / 'scripts'))
import validate_assets

source = folder / 'base-v3.png'
target = folder / 'base-v4.png'
assert not target.exists(), 'Approved correction already consumed; never overwrite'
im = Image.open(source)
assert im.mode == 'RGBA' and im.size == (256, 256)
pixels = list(im.getdata())
seen, groups = set(), []
for index, pixel in enumerate(pixels):
    if not pixel[3] or index in seen:
        continue
    group = [index]
    seen.add(index)
    for i in group:
        x, y = i % 256, i // 256
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                xx, yy = x + dx, y + dy
                j = yy * 256 + xx
                if 0 <= xx < 256 and 0 <= yy < 256 and pixels[j][3] and j not in seen:
                    seen.add(j)
                    group.append(j)
    groups.append(group)
groups.sort(key=len, reverse=True)
removed = [i for group in groups[1:] for i in group]
assert len(removed) == 52 and max(pixels[i][3] for i in removed) == 2
out = pixels.copy()
for i in removed:
    out[i] = (*pixels[i][:3], 0)
assert all(out[i] == pixels[i] for i in groups[0])
assert sum(a != b for a, b in zip(pixels, out)) == 52
result = Image.new('RGBA', im.size)
result.putdata(out)
result.save(target)
assert list(Image.open(target).getdata()) == out
bounds = []
errors = validate_assets.png_errors(target, True, bounds, [])
assert not errors, errors
assert sum(bool(pixel[3]) for pixel in out) == len(groups[0])
report = {
    'conceptId': 'M024', 'approval': 'User approved one detached-residue cleanup',
    'approvedExtraCorrectionsUsed': 1, 'automaticRepairIterations': 3,
    'source': source.name, 'result': target.name,
    'sourceSha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'resultSha256': hashlib.sha256(target.read_bytes()).hexdigest(),
    'removedPixels': [[i % 256, i // 256, pixels[i][3]] for i in removed],
    'beforeDetachedPixels': 52, 'afterDetachedPixels': 0,
    'connectedBodyPixelChanges': 0, 'rgbPixelChanges': 0,
    'canvas': [256, 256], 'anchor': {'x': 0.5, 'y': 1},
    'coordinateTranslation': [0, 0],
    'beforeAlphaBoundsExclusive': im.getbbox(), 'afterAlphaBoundsExclusive': result.getbbox(),
    'pngErrors': errors, 'automatedCleanup': 'PASS',
    'artworkApproval': 'HUMAN_REVIEW_REQUIRED', 'gui': 'NOT_VERIFIED',
    'productionEligible': False, 'runtimeEnabled': False,
}
(folder / 'cleanup-approved-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k:v for k,v in report.items() if k != 'removedPixels'}, indent=2))
