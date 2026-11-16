"""Reuse the local part inverse sampler for independent body responses."""
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=Path('design/production-batches/LUMA-ASSET-13')
TEMPLATE=ROOT/'design/production-batches/action-followup/M050/hit-pilot/rig-hit.cjs'
SAMPLES={
 'cursor_react':[[.01,.35,.8,1,.75,.4,.14,.03],[.02,.1,.4,.85,1,.6,.25,.04]],
 'interact':[[.01,.5,1,.4,.85,.3,.1,.025],[.02,.1,.45,1,.5,.8,.3,.03]],
 'hit':[[.02,1,.85,.6,.37,.2,.09,.025],[.01,.22,.7,1,.78,.45,.18,.045]],
}
# Coordinates are local anatomy regions inspected on each 256px BASE. Feet/face stay fixed.
CASES={
 'M046':{'rect':[45,130,219,211],'parts':{
  'cursor_react':[('near-wrist-alert',91,186,20,21,-1.2,-2),('far-wrist-follow',201,181,17,22,.7,-1)],
  'interact':[('near-hand-greeting',90,183,22,25,-1.6,-3),('far-shoulder-counterbalance',185,151,23,19,.8,-.6)],
  'hit':[('guardian-shoulder-recoil',179,148,24,23,-2,1),('near-forearm-brace',82,174,23,24,1.2,-1.5)]}},
 'M047':{'rect':[57,133,198,195],'parts':{
  'cursor_react':[('near-wing-root-alert',102,158,27,25,-1.4,-1.7),('far-wing-root-follow',181,161,13,23,.8,-.8)],
  'interact':[('near-wing-feather-greeting',90,167,29,24,-2,-1.4),('far-wing-counterbalance',181,163,14,24,1.2,-.8)],
  'hit':[('near-wing-flinch',97,163,29,26,1.5,1.5),('far-wing-brace',181,164,14,24,-1,.8)]}},
 'M050':{'rect':[24,120,231,205],'parts':{
  'cursor_react':[('curled-tail-alert',57,157,29,30,1.4,-2),('shoulder-attention',183,145,23,21,.7,-.8)],
  'interact':[('curled-tail-greeting',58,157,29,30,-2.2,1.4),('flank-counterbalance',132,154,30,22,.6,-.8)]}},
}
if any((ROOT/OUT).glob('M*/**/rig-*.cjs')):
    raise SystemExit('Existing candidates preserved; refusing regeneration at inherited 3/3 limit')

for code,config in CASES.items():
 for action,parts in config['parts'].items():
  folder=OUT/code/action;(ROOT/folder).mkdir(parents=True,exist_ok=True)
  parsed=[dict(name=p[0],x=p[1],y=p[2],rx=p[3],ry=p[4],dx=p[5],dy=p[6],samples=SAMPLES[action][i]) for i,p in enumerate(parts)]
  text=TEMPLATE.read_text();text=text.replace('design/production-batches/action-followup/M050/hit-pilot',str(folder)).replace('batch05/M050/base-v2.png','batch05/'+code+'/base-v2.png')
  text=re.sub(r'const parts=.*?;\n',lambda _: 'const parts='+json.dumps(parsed)+';\n',text,count=1)
  l,t,r,b=config['rect'];protected=f'y>={b}||y<={t}||x<={l}||x>={r}'
  text=text.replace('y>=205||y<=118||x<=24||x>=231',protected)
  text=text.replace('/rigged/hit','/rigged/'+action).replace("'hit_'","'"+action+"_'")
  text=text.replace('Independent M050 HIT candidate','Independent '+code+' '+action.upper()+' candidate').replace('PR #114 independent first attempt; no failure recovery','Inherited 3/3; independent first attempt; no failure recovery')
  (ROOT/folder/('rig-'+action+'.cjs')).write_text(text)
  spec={'conceptId':code,'sessionId':'LUMA-ASSET-13','species':None,'evolutionStage':None,'runtimeEnabled':False,'productionEligible':False,'status':'CANDIDATE_ONLY','sourceBase':'design/production-batches/monsters/batch05/'+code+'/base-v2.png','canvas':{'width':256,'height':256},'anchor':{'x':.5,'y':1},'sourceFacing':'RIGHT','clip':{'name':action.upper(),'frames':8,'frameDuration':110 if action=='hit' else 125,'loop':False},'parts':parsed,'movableRect':config['rect'],'repairIterations':3,'repairLimit':3,'artworkReview':'HUMAN_REVIEW_REQUIRED','naturalMotion':'HUMAN_REVIEW_REQUIRED','reusedRig':str(TEMPLATE.relative_to(ROOT)),'behaviorContract':'Isolated proposed body response; no Personality, SpeciesBehavior or MovementProfile activation'}
  (ROOT/folder/'candidate-clip.json').write_text(json.dumps(spec,indent=2)+'\n')
