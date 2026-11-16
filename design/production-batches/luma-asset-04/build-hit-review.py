import json,hashlib,sys,tempfile,os,shutil
from pathlib import Path
root=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root/'scripts'))
import build_creature_review as review
out=root/'design/production-batches/luma-asset-04'
ledger=root/'design/creature-production-queue.json';before=hashlib.sha256(ledger.read_bytes()).hexdigest()
queue=json.loads(ledger.read_text());ids={f'M{i:03}' for i in range(1,6)}
with tempfile.TemporaryDirectory(prefix='luma-asset04-catalog-') as d:
 tmp=Path(d);(tmp/'design').mkdir();(tmp/'src').mkdir()
 (tmp/'src/entities').symlink_to(root/'src/entities',target_is_directory=True);(tmp/'public').symlink_to(root/'public',target_is_directory=True)
 queue['creatures']=[r for r in queue['creatures'] if r['creatureId'] in ids]
 (tmp/'design/creature-production-queue.json').write_text(json.dumps(queue))
 for directory in sorted((root/'design').glob('**/rigged/*')):
  if not directory.is_dir() or not any(i in directory.parts for i in ids):continue
  dest=tmp/directory.relative_to(root);dest.mkdir(parents=True)
  for frame in directory.glob('*.png'):(dest/frame.name).symlink_to(frame)
  for name in ['candidate-clip.json','rig-evidence.json',directory.name+'-rig-evidence.json']:
   file=directory.parent.parent/name;target=dest.parent.parent/name
   if file.exists() and not target.exists():target.symlink_to(file)
 review.ROOT=tmp
 # Existing refresh operations run only against a disposable audit copy, never shared Ledger.
 review.refresh_inventory();catalog=review.build();review.refresh_coverage(catalog)

 for row in catalog['creatures']:
  for clip in row['clips']:
   if '/luma-asset-04/M002/hit-pilot/' in clip['directory']:
    clip['automated']='VALIDATION_FAILED';clip['errors'].append('BASE_RETURN_RESIDUAL: entry/exit >= 0.05 of peak; preserved at 3/3')
 review.add_coverage(catalog)
 (out/'hit-review-catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(catalog['coverageSummary']))
assert hashlib.sha256(ledger.read_bytes()).hexdigest()==before
