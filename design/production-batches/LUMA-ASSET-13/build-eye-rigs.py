"""Instantiate existing offline eye rigs; never writes shared manifests or production assets."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path('design/production-batches/LUMA-ASSET-13')
EYES = {
    'M046': [dict(x=152,y=77,rx=6,ry=7,dx=.8),dict(x=171,y=79,rx=3,ry=5,dx=.35)],
    'M047': [dict(x=143,y=105,rx=12,ry=14,dx=1.5),dict(x=180,y=110,rx=5,ry=10,dx=.6)],
    'M050': [dict(x=214,y=88,rx=4.5,ry=4,dx=.6)],
}
if any((ROOT/OUT).glob('M*/**/rig-*.cjs')):
    raise SystemExit('Existing candidates preserved; refusing regeneration at inherited 3/3 limit')

for code, eyes in EYES.items():
    for action, template, oldcode in [('blink','M003/rig-blink.cjs','M003'),('look','M008/rig-look.cjs','M008')]:
        root=OUT/code/action
        (ROOT/root).mkdir(parents=True,exist_ok=True)
        text=(ROOT/'design/production-batches/action-followup'/template).read_text()
        text=text.replace('design/production-batches/action-followup/'+oldcode,str(root))
        text=text.replace('design/production-batches/monsters/batch01/'+oldcode+'/base-v2.png','design/production-batches/monsters/batch05/'+code+'/base-v2.png')
        a=text.index('const eyes=');b=text.index(',closure=' if action=='blink' else ',gaze=',a)
        text=text[:a]+'const eyes='+json.dumps(eyes)+text[b:]
        text=text.replace('repairIterations:0','repairIterations:3,repairLimit:3')
        text=text.replace('PR #114; no reset or failure recovery','Inherited 3/3; independent first attempt, no reset or failure recovery')
        text=text.replace('approved BASE','candidate BASE').replace('Offline M003-specific','Offline '+code+'-specific')
        (ROOT/root/('rig-'+action+'.cjs')).write_text(text)
        spec={'conceptId':code,'species':None,'evolutionStage':None,'sessionId':'LUMA-ASSET-13','status':'CANDIDATE_ONLY','runtimeEnabled':False,'productionEligible':False,'sourceBase':'design/production-batches/monsters/batch05/'+code+'/base-v2.png','canvas':{'width':256,'height':256},'anchor':{'x':.5,'y':1},'sourceFacing':'RIGHT','clip':{'name':action.upper(),'frames':6 if action=='blink' else 8,'frameDuration':90 if action=='blink' else 125,'loop':False},'eyes':eyes,'artworkReview':'HUMAN_REVIEW_REQUIRED','naturalMotion':'HUMAN_REVIEW_REQUIRED','repairIterations':3,'repairLimit':3,'reusedRig':'design/production-batches/action-followup/'+template}
        (ROOT/root/'candidate-clip.json').write_text(json.dumps(spec,indent=2)+'\n')
