"""Build four release apps with identical source PNGs; restore manifest afterwards.
Only QA bundle timing differs. No gameplay/state/clock overrides, no timing approval.
"""
import argparse,json,os,subprocess,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[2];manifest=root/'public/assets/creatures/moa/stage01/manifest.json';original=manifest.read_bytes()
generated=root/'src/animation/generated-manifests.ts'; original_generated=generated.read_bytes()
config=json.dumps({'bundle':{'active':True}}) # Production CSP unchanged.
target=Path(os.environ['CARGO_TARGET_DIR']).resolve();a.output.mkdir(parents=True,exist_ok=True)
try:
 for cycle in [600,900,1500,1800]:
  m=json.loads(original);m['animations']['idle']['frameDuration']=cycle/6;manifest.write_text(json.dumps(m,indent=2)+'\n')
  subprocess.run(['python3','scripts/sync_animation_manifests.py'],cwd=root,check=True)
  dest=a.output/str(cycle);dest.mkdir(exist_ok=True)
  with (dest/'build.log').open('w') as log:
   subprocess.run(['npm','run','tauri','--','build','--bundles','app','--config',config],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
  shutil.copytree(target/'release/bundle/macos/LUMA Spike.app',dest/'LUMA Spike.app',dirs_exist_ok=True)
  (dest/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
finally:
 manifest.write_bytes(original)
 generated.write_bytes(original_generated)
