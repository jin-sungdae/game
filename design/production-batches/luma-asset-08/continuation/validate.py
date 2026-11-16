"""기존 측정기를 재사용하고 BASE 복귀 오차를 별도 기록한다."""
import json,sys,hashlib,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tests/assets'))
from test_creature_new_pose_quality import measure_parts
from test_creature_followup import measure,detached_pixels
from test_moa_blink_v2 import rgba
from test_assets import validator

def measured(folder):
    spec=json.loads((folder/'candidate-clip.json').read_text())
    if 'eyes' in spec:
        report=measure(folder,lambda x,y:any(((x-e['x'])/e['rx'])**2+((y-e['y'])/e['ry'])**2<1 for e in spec['eyes']))
    elif spec['clip']['name']=='BREATH':
        l,t,r,b=spec['movableRect']
        report=measure(folder,lambda x,y:l<x<r and t<y<b)
    else: report=measure_parts(folder)
    base=rgba(ROOT/spec['sourceBase']);name=spec['clip']['name'].lower()
    frames=[rgba(p) for p in sorted((folder/'rigged'/name).glob('*.png'))]
    differences=[sum(abs(a-b) for a,b in zip(base,f)) for f in frames]
    return report,{'rgbaL1DistanceFromBase':differences,'lastToBaseLessThanPeak':bool(differences and differences[-1]<max(differences)),
        'lastToBaseNormalizedMean':differences[-1]/(256*256*4*255) if differences else None,
        'exactBaseReturn':bool(frames and frames[-1]==base),'visualContinuity':'HUMAN_REVIEW_REQUIRED','productionEligible':False}
if __name__=='__main__':
    for p in sorted(OUT.glob('M*/*/candidate-clip.json')):
        report,continuity=measured(p.parent)
        (p.parent/'frame-validation.json').write_text(json.dumps(report,indent=2)+'\n')
        (p.parent/'base-return.json').write_text(json.dumps(continuity,indent=2)+'\n')
        print(p.parent.relative_to(OUT),report['automated'],flush=True)
