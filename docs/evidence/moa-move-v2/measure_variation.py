"""Measure supplied RGBA bytes only; no image transformation or production writes."""
from pathlib import Path
import sys,json,hashlib,zipfile,tempfile
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tests/assets'));from test_moa_blink_v2 import rgba
ann=json.loads((ROOT/'docs/evidence/moa-move-anatomy/measurements.json').read_text())
rois={k:ann['regions'][k]['visible_alpha128'] for k in ['FRONT_PAW_NEAR','REAR_PAW_NEAR']}
rois['BODY_INTERIOR']=ann['safe_deformation_proposals']['BODY_INTERIOR']['bounds']
def analyze(frames):
 data=[rgba(f) for f in frames];result={}
 for name,b in rois.items():
  ids=[(y*256+x)*4 for y in range(b['y_min'],b['y_max']+1) for x in range(b['x_min'],b['x_max']+1)]
  rows=[]
  for i,(a,z) in enumerate(zip(data,data[1:]+data[:1])):
   visible=[j for j in ids if a[j+3] or z[j+3]]
   rows.append({'from':i+1,'to':(i+1)%8+1,'changedRGBPixels':sum(a[j:j+3]!=z[j:j+3] for j in visible),'changedAlphaPixels':sum(a[j+3]!=z[j+3] for j in ids),'meanAbsoluteRGBDifference':sum(abs(a[j+c]-z[j+c]) for j in visible for c in range(3))/(3*len(visible))})
  result[name]={'inclusiveROI':b,'roiPixels':len(ids),'adjacentPairs':rows}
 return {'uniqueByteHashes':len(set(hashlib.sha256(f.read_bytes()).hexdigest() for f in frames)),'uniqueDecodedFrames':len(set(data)),'regions':result,'wholeFrameAdjacentRGBChanges':[sum(a[j:j+3]!=b[j:j+3] for j in range(0,len(a),4) if a[j+3] or b[j+3]) for a,b in zip(data,data[1:]+data[:1])]}
with tempfile.TemporaryDirectory() as t:
 with zipfile.ZipFile('/Users/jinseongdae/Downloads/moa_move_v1_registered.zip') as z:
  files=[]
  for i in range(1,9):
   f=Path(t)/f'move_{i:02}.png';f.write_bytes(z.read(f.name));files.append(f)
  v1=analyze(files)
v2=analyze([ROOT/f'public/assets/creatures/moa/stage01/walk/walk_{i:02}.png' for i in range(8)])
report={'method':'Adjacent pairs including08→01; visible RGB changes counted only when either pixel has nonzero alpha; raw8-bit RGB MAE, bounding-box ROIs from prior annotation (not semantic segmentation).','V1':v1,'V2':v2}
(OUT/'pixel-variation.json').write_text(json.dumps(report,indent=2)+'\n')
for label,a in [('V1',v1),('V2',v2)]:
 print(label,'unique',a['uniqueDecodedFrames'])
 for name,v in a['regions'].items():print(name,[p['changedRGBPixels'] for p in v['adjacentPairs']])
