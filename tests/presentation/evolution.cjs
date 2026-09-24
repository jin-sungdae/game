const {test}=require('node:test');const assert=require('node:assert/strict');const path=require('node:path');const fs=require('node:fs');
const {evolutionModel,renderIdentity}=require(path.join(process.env.LUMA_PRESENTATION_TEST_DIR,'presentation/evolution.js'));
const view=status=>({eligibility:{status,nextName:'MOKORI',requirements:{level:{current:0,required:3,met:false}}},phase:'IDLE',busy:false,error:null,previous:null,success:null});
test('server enum controls AVAILABLE, LOCKED and MAX_STAGE, not client progression',()=>{
 assert.equal(evolutionModel(view('AVAILABLE')).available,true);assert.equal(evolutionModel(view('AVAILABLE')).canEvolve,true);
 for(const status of ['LOCKED','MAX_STAGE'])assert.equal(evolutionModel(view(status)).canEvolve,false);
 assert.equal(evolutionModel(undefined).canEvolve,false);
});
test('busy, gameplay request and acknowledged presentation prevent another evolve',()=>{
 for(const extra of [{busy:true},{phase:'GLOW'},{phase:'REVEAL'}])assert.equal(evolutionModel({...view('AVAILABLE'),...extra}).canEvolve,false);
 assert.equal(evolutionModel(view('AVAILABLE'),true).canEvolve,false);
});
test('failure and success feedback are server-derived',()=>{
 assert.equal(evolutionModel({...view('LOCKED'),error:'offline'}).message,'offline');
 assert.equal(evolutionModel({...view('LOCKED'),success:'MOKORI'}).message,'MOKORI 진화 완료');
});
test('stage identity switches only during acknowledged timeline; bootstrap restores directly',()=>{
 const moa={species:'MOA',evolutionStage:1},mokori={species:'MOA',evolutionStage:2};
 assert.equal(renderIdentity(mokori,{phase:'GLOW',previous:moa}),moa);
 assert.equal(renderIdentity(mokori,{phase:'REVEAL',previous:moa}),mokori);
 assert.equal(renderIdentity(mokori),mokori);
});
test('explicit interaction, reduced motion, diagnostic identity and focus policy',()=>{
 const creature=fs.readFileSync('src/components/Creature.tsx','utf8');const panel=fs.readFileSync('src/components/EvolutionInteraction.tsx','utf8');
 assert.match(creature,/stopPropagation\(\).*action\('evolution'\)/);assert.match(panel,/onClick=.*action\('evolve'\)/);
 assert.match(fs.readFileSync('src/presentation/evolution.css','utf8'),/prefers-reduced-motion:reduce[^]*animation:none/);
 assert.match(fs.readFileSync('src/components/CompanionVisual.tsx','utf8'),/Stage \{evolutionStage\} · asset pending/);
 for(const source of [creature,panel,fs.readFileSync('src/presentation/evolution.ts','utf8')])assert.doesNotMatch(source,/setFocus|\.focus\(|activateIgnoringOtherApps|WebviewWindow/);
});
test('NEBLA keeps MOKORI during acknowledged glow then reveals Stage3 diagnostic identity',()=>{
 const old={species:'MOA',evolutionStage:2,evolutionName:'MOKORI'},next={species:'MOA',evolutionStage:3,evolutionName:'NEBLA'};
 assert.equal(renderIdentity(next,{phase:'GLOW',previous:old}),old);
 assert.equal(renderIdentity(next,{phase:'REVEAL',previous:old}),next);
 assert.equal(renderIdentity(next),next);
});
test('relationship feedback stays in existing entity panel and reward zero is hidden',()=>{
 const creature=fs.readFileSync('src/components/Creature.tsx','utf8');
 assert.match(creature,/bond\?\.feedback/);assert.match(creature,/className="bond-feedback" role="status"/);
 assert.doesNotMatch(creature,/Bond\s*\+\s*1|setTimeout|nextAvailableAt.*Date/);
 assert.match(fs.readFileSync('src/components/Interaction.tsx','utf8'),/v.reward.bond>0/);
 assert.match(fs.readFileSync('src/presentation/evolution.css','utf8'),/\.bond-feedback[^}]*pointer-events:none/);
});
