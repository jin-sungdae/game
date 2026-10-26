"""Session-only measurements reusing existing PNG, eye-rig and alpha validators."""
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests/assets')]
from test_creature_followup import measure
OUT=ROOT/'design/production-batches/LUMA-ASSET-13'
results=[]
for specpath in sorted(OUT.glob('M*/*/candidate-clip.json')):
    spec=json.loads(specpath.read_text())
    if 'eyes' not in spec: continue
    eyes=spec['eyes']
    movable=lambda x,y:any(((x-e['x'])/e['rx'])**2+((y-e['y'])/e['ry'])**2<1 for e in eyes)
    result=measure(specpath.parent,movable)
    result['loopContract']='ONE_SHOT; loop delta measured, seamless loop not claimed'
    (specpath.parent/'frame-validation.json').write_text(json.dumps(result,indent=2)+'\n')
    results.append({'monster':spec['conceptId'],'action':spec['clip']['name'],'automated':result['automated'],'png':len(result['frames'])})
print(json.dumps(results,indent=2))
raise SystemExit(any(r['automated']!='PASS' for r in results))
