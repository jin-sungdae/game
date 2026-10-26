from pathlib import Path
import sys,json,tempfile,os
root=Path(__file__).resolve().parents[3];sys.path.insert(0,str(root/'scripts'));import build_creature_review as review
batch=root/'design/production-batches/luma-asset-06'
with tempfile.TemporaryDirectory(prefix='luma-asset06-catalog-') as tmp:
 t=Path(tmp);(t/'design').mkdir();(t/'design/production-batches').mkdir()
 target=t/'design/production-batches/luma-asset-06'
 for source in batch.rglob('*'):
  destination=target/source.relative_to(batch)
  if source.is_dir():destination.mkdir(parents=True,exist_ok=True)
  else:
   destination.parent.mkdir(parents=True,exist_ok=True);os.symlink(source,destination)
 for name in ['creature-production-queue.json']:os.symlink(root/'design'/name,t/'design'/name)
 for name in ['src','public']:os.symlink(root/name,t/name)
 review.ROOT=t;data=review.build()
data['creatures']=[r for r in data['creatures'] if r['id'] in ['M011','M012','M013','M014','M015']]
for row in data['creatures']:
 for clip in row['clips']:
  folder=root/clip['directory'].lstrip('/');validation=json.loads((folder.parent.parent/'frame-validation.json').read_text())
  clip['sessionValidation']=validation['automated'];clip['sessionErrors']=validation['errors']
  if validation['errors']:clip['automated']='VALIDATION_FAILED';clip['errors']+=validation['errors']
source=json.loads((root/'design/visual-reference-v1/catalog.json').read_text())
def entries(value):
 if isinstance(value,dict):
  if 'conceptId' in value and 'speciesBehavior' in value:yield value
  for v in value.values():yield from entries(v)
 elif isinstance(value,list):
  for v in value:yield from entries(v)
contracts={r['conceptId']:r for r in entries(source)}
for row in data['creatures']:
 contract=contracts[row['id']]
 row['proposedContract']={k:contract.get(k) for k in ['observedForm','speciesIdentity','personality','movementProfile','speciesBehavior','skillIdentity']}
 row['sessionActionCoverage']=[]
 for action in row['actions']:
  folder=batch/row['id']/action['action'].lower();result=folder/'frame-validation.json'
  status=json.loads(result.read_text())['automated'] if result.exists() else ('EXISTING_CANDIDATE_PRESERVED' if action.get('frameCount',0)>0 else 'FAILED_PRESERVED_NO_REPAIR' if action['animationStatus']=='VALIDATION_FAILED' else 'NOT_PRODUCED_REQUIRES_ANATOMY_OR_CONTRACT')
  row['sessionActionCoverage'].append({'action':action['action'],'status':status,'productionComplete':False})
 row['blockedActionRequirements']={
  'MOVE':'Approved gait/contact keyposes required; M012 failed MOVE remains untouched.',
  'TURN':'Approved opposite-facing anatomy/keyposes required.',
  'REST':'Approved lowered-body keypose required; M011 failed REST remains untouched.',
  'SLEEP':'Approved resting posture and sustained eyelid keypose required; BLINK is not SLEEP.',
  'ATTACK':'Approved attack/contact keyposes and server event contract required.',
  'SKILL_CAST':'Species skill identity and server contract unapproved.',
  'VICTORY':'Distinct approved celebratory pose required; do not relabel INTERACT.',
  'DEFEAT':'Approved grounded terminal pose required.'}
 row['additionalActionReview']={
  'JUMP':'Approved crouch, airborne and landing contact poses required; M013 proposed JUMP is not approval.',
  'FLY':'Approved wing spread/upstroke/downstroke poses required; M012/M014 proposed FLYING is not approval.',
  'HOVER':'Approved airborne body/wing cycle required; M015 FLOATING proposal conflicts with BASE identity.',
  'LAND':'Approved airborne-to-ground contact transition required.',
  'CHARGE':'Approved anticipation/charge and gameplay timing contract required.',
  'RECOVERY':'Approved terminal-pose-to-BASE transition required; failed HIT/INTERACT cannot be repaired under a new action.'}
 row['eyeReview']={'status':'HUMAN_REVIEW_REQUIRED','notes':'Inspect eyelid edge/rim and residual dark pixels at closure; numerical PASS does not approve appearance. M014 BLINK duplicate frames preserved without retry.'}
data.pop('coverageSummary',None);data.pop('legacyProductionAudit',None)
data['scope']='LUMA-ASSET-06 isolated catalog; existing build_creature_review parser; shared ledger untouched; PNG-only result does not override continuity failure'
(batch/'catalog.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
