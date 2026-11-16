"""기존 Validator 결과를 독립 후보 디렉터리에만 저장한다."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tests/assets'))
from test_creature_new_pose_quality import measure_parts
from test_moa_blink_v2 import rgba
OUT=Path(__file__).resolve().parent
for spec_path in sorted(OUT.glob('M*/*/candidate-clip.json')):
    folder=spec_path.parent
    report=measure_parts(folder)
    (folder/'frame-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(folder.relative_to(OUT),report['automated'],len(report['frames']))
