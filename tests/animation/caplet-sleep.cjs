const {test}=require('node:test');const assert=require('node:assert/strict');const path=require('node:path');
const load=f=>require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,f));
const {AssetLoader}=load('animation/loader.js');
const {CharacterAnimator,AnimationStateResolver,PilotAssets,pilotDefinition}=load('animation/pilot.js');
const {directionScale}=load('animation/model.js');
const manifest=require('../../public/assets/monsters/caplet/manifest.json');
test('candidate complete SLEEP clip uses existing loader and animator; missing frame fails closed',async()=>{
 const loader=new AssetLoader({json:async()=>manifest,image:async()=>({width:256,height:256})});
 const clip=await loader.loadRegistered('caplet',1,'/candidate/manifest.json','sleep');assert.ok(clip);
 const animator=new CharacterAnimator();const frames=new Set();
 for(let t=0;t<=2400;t+=10)frames.add(animator.sample('caplet:sleep',clip,t,1,false));
 assert.equal(frames.size,6);assert.equal(animator.sample('caplet:sleep',clip,2400,1,false),0);
 assert.equal(animator.sample('caplet:sleep',clip,2500,1,true),0);
 const bad=new AssetLoader({json:async()=>manifest,image:async url=>{if(url.endsWith('03.png'))throw Error('missing');return {width:256,height:256};}});
 assert.equal(await bad.loadRegistered('caplet',1,'/candidate/manifest.json','sleep'),null);
});
test('existing behavior resolver preserves sleep identity and suppression',()=>{
 const r=new AnimationStateResolver();const input={state:'SLEEPING',speed:0,suppressed:false};
 assert.equal(r.sampleCompanion(input,0).state,'SLEEP');
 assert.equal(r.sampleCompanion({...input,suppressed:true},0).suppressed,true);
 assert.deepEqual([directionScale(-1),directionScale(1)],[-1,1]);
});

test('approved CAPLET pilot loads only SLEEP and keeps unknown identity inactive',async()=>{
 const assets=new PilotAssets(new AssetLoader({json:async()=>manifest,image:async()=>({width:256,height:256})}));
 const pilot=pilotDefinition('CAPLET');assert.ok(pilot);
 assert.equal((await assets.load(pilot,'SLEEP')).urls.length,6);
 for(const state of ['IDLE','MOVE','REACT','REST','TURN'])assert.equal(await assets.load(pilot,state),null);
 assert.equal(pilotDefinition('M005'),null);assert.equal(pilotDefinition('CAPLET',2),null);
 assert.equal(await assets.load({...pilot,status:'NOT_SUPPLIED'},'SLEEP'),null);
 assert.equal(await assets.load({...pilot,species:'pip'},'SLEEP'),null);
});
