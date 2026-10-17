const {test}=require('node:test');const assert=require('node:assert/strict');const path=require('node:path');
const load=f=>require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,'animation',f));
const {PilotAssets,pilotDefinition,AnimationStateResolver,CharacterAnimator}=load('pilot.js');const {AssetLoader,browserIO}=load('loader.js');const {IdleSequencer}=load('idle.js');
test('MOVE pilot is explicit, atomic and isolated from approved IDLE and REACT',async()=>{
 const p=pilotDefinition('moa');assert.equal(p.status,'IDLE_PRODUCTION');assert.equal(p.moveStatus,'PRODUCTION');assert.equal(pilotDefinition('PIP').status,'IDLE_PRODUCTION');let requests=[];
 const assets=new PilotAssets(new AssetLoader({json:browserIO.json,image:async u=>{requests.push(u);if(u.endsWith('walk_03.png'))throw Error('missing MOVE');return {width:256,height:256};}}));
 assert.equal(await assets.load(p,'MOVE'),null);assert.equal((await assets.load(p,'IDLE')).urls.length,4);assert.equal((await assets.load(p,'BLINK')).urls.length,3);assert.equal((await assets.load(p,'REACT')).urls.length,6);
 assert.equal(await assets.load({...p,moveStatus:undefined},'MOVE'),null);assert.equal(await assets.load({...pilotDefinition('PIP'),status:'NOT_SUPPLIED'},'MOVE'),null);
 assert.ok(requests.every(u=>u.startsWith('/assets/creatures/moa/stage01/')));assert.equal(p.base,'/assets/creatures/moa/stage01/base.png');
});
test('real resolver hysteresis selects MOVE; frame order and bounded slow/normal rates',async()=>{
 const p=pilotDefinition('moa');const asset=await new PilotAssets(new AssetLoader({json:browserIO.json,image:async()=>({width:256,height:256})})).load(p,'MOVE');
 assert.equal(asset.clip.frameDuration,80);assert.equal(asset.clip.frames,8);
 const resolver=new AnimationStateResolver();
 for(const [speed,state,rate] of [[0,'IDLE',1],[7,'IDLE',1],[8,'MOVE',.5],[5,'MOVE',.5],[40,'MOVE',1],[1000,'MOVE',2],[2,'IDLE',1]]){
  resolver.observe({speed,state:'WALKING',suppressed:false},0);assert.deepEqual(resolver.sample(0),{state,suppressed:false,rate});
 }
 for(const [rate,duration] of [[.5,1280],[1,640],[2,320]]){
  const a=new CharacterAnimator(),observed=[];let prior=-1;
  for(let t=0;t<=duration;t+=10){const f=a.sample('MOVE',asset,t,rate,false);if(f!==prior){observed.push(f);prior=f;}}
  assert.deepEqual(observed,[0,1,2,3,4,5,6,7,0]);assert.equal(a.sample('MOVE',asset,duration+10,rate,true),0);
 }
});
test('MOVE cancels due/in-progress blink; IDLE resumes breath and fresh interval; priority suppresses MOVE',()=>{
 const r=new AnimationStateResolver(),idle=new IdleSequencer(()=>0);const cfg={breath:'breath',blink:'blink',blinkIntervalMs:[3000,7000]};
 assert.equal(idle.sample(0,true,false,cfg,270),'IDLE');assert.equal(idle.sample(3000,true,false,cfg,270),'BLINK');
 r.observe({speed:40,state:'WALKING',suppressed:false},3050);assert.equal(r.sample(3050).state,'MOVE');idle.sample(3050,false,false,cfg,270);
 assert.equal(idle.sample(10000,true,false,cfg,270),'IDLE');assert.equal(idle.sample(12999,true,false,cfg,270),'IDLE');assert.equal(idle.sample(13000,true,false,cfg,270),'BLINK');
 r.observe({speed:40,state:'REACTING',suppressed:false},14000);assert.equal(r.sample(14000).state,'REACT');
 for(const state of ['BATTLE','EVOLVING','DRAGGING']){r.observe({speed:40,state,suppressed:true},15000);assert.equal(r.sample(15000).suppressed,true);}
});

test('walking intent without measured motion stays idle; unavailable air clips never reuse walk',async()=>{
 const r=new AnimationStateResolver();
 for(const speed of [0,40,0,0,40,0]) {
  r.observe({state:'WALKING',speed,suppressed:false},0);
  assert.equal(r.sample(0).state,speed===0?'IDLE':'MOVE');
 }
 const p=pilotDefinition('moa');
 const assets=new PilotAssets(new AssetLoader({json:browserIO.json,image:async()=>({width:256,height:256})}));
 for(const action of ['JUMP','HOVER','FLY','GLIDE']) assert.equal(await assets.load(p,action),null);
 for(const stage of [2,3,4,5]) assert.equal(pilotDefinition('moa',stage),null);
});

test('companion native snapshot stops WALK before the next animation clock and gates behavior',()=>{
 const r=new AnimationStateResolver();const input={state:'WALKING',speed:40,suppressed:false};
 r.observe(input,0);assert.equal(r.sampleCompanion(input,0).state,'MOVE');
 for(const speed of [0,NaN,Infinity,-1])assert.equal(r.sampleCompanion({...input,speed},1).state,'IDLE');
 for(const [state,expected] of [['IDLE','IDLE'],['SITTING','REST'],['LOOKING','LOOK_AROUND'],['SLEEPING','SLEEP']])assert.equal(r.sampleCompanion({...input,state},1).state,expected);
 for(const state of ['BATTLE','EVOLVING','DRAGGING','ENGAGED'])assert.equal(r.sampleCompanion({...input,state},1).suppressed,true);
 assert.equal(r.sampleCompanion({...input,suppressed:true},1).suppressed,true);
 assert.equal(r.sampleCompanion(input,2).state,'MOVE');
});
test('companion reaction requires a real native edge and cannot leak into rest or battle',()=>{
 const r=new AnimationStateResolver(),input={state:'IDLE',speed:0,suppressed:false};
 assert.equal(r.sampleCompanion(input,0).state,'IDLE');
 r.observe({...input,state:'REACTING'},0);
 assert.equal(r.sampleCompanion({...input,state:'REACTING'},479).state,'REACT');
 assert.equal(r.sampleCompanion({...input,state:'REACTING',speed:40},480).state,'IDLE');
 assert.equal(r.sampleCompanion({...input,state:'SITTING'},100).state,'REST');
 assert.equal(r.sampleCompanion({...input,state:'BATTLE'},100).suppressed,true);
});
test('all fifteen companion identities fail closed except supplied MOA stage one and RUU stage three; missing actions never borrow idle',async()=>{
 const assets=new PilotAssets(new AssetLoader({json:browserIO.json,image:async()=>assert.fail('unsupplied action must not request another clip')}));
 for(const species of ['moa','ruu','nox'])for(let stage=1;stage<=5;stage++){
  const pilot=pilotDefinition(species,stage);
  if(species==='moa' && stage===1){for(const action of ['REST','SLEEP','LOOK_AROUND','TURN'])assert.equal(await assets.load(pilot,action),null);}
  else if(species==='ruu' && stage===3){for(const action of ['REST','SLEEP','LOOK_AROUND','TURN','MOVE','REACT','BLINK','FLY','GLIDE'])assert.equal(await assets.load(pilot,action),null);}
  else assert.equal(pilot,null);
 }
});
test('cached manifest and frames never authorize a different species or evolution stage',async()=>{
 const p=pilotDefinition('moa'),loader=new AssetLoader({json:browserIO.json,image:async()=>({width:256,height:256})});
 const original=await loader.loadRegistered('moa',1,p.manifest,'walk');assert.ok(original);
 assert.equal(await loader.loadRegistered('ruu',1,p.manifest,'walk'),null);
 assert.equal(await loader.loadRegistered('moa',2,p.manifest,'walk'),null);
 assert.equal(await loader.loadRegistered('moa',1,p.manifest,'walk'),original);
});

test('RUU stage three IDLE is atomic, identity-bound, and uses the existing clock',async()=>{
 const p=pilotDefinition('ruu',3),requests=[];
 const assets=new PilotAssets(new AssetLoader({json:browserIO.json,image:async url=>{requests.push(url);return {width:256,height:256};}}));
 const clip=await assets.load(p,'IDLE');assert.ok(clip);assert.equal(clip.urls.length,8);
 assert.ok(requests.every(url=>url.startsWith('/assets/creatures/ruu/stage03/idle/')));
 const animator=new CharacterAnimator();const frames=[];
 for(let t=0;t<=1440;t+=180)frames.push(animator.sample('IDLE',clip,t,1,false));
 assert.deepEqual(frames,[0,1,2,3,4,5,6,7,0]);
 assert.equal(animator.sample('IDLE',clip,1500,1,true),0);
 const missing=new PilotAssets(new AssetLoader({json:browserIO.json,image:async url=>{if(url.endsWith('idle_07.png'))throw Error('incomplete clip');return {width:256,height:256};}}));
 assert.equal(await missing.load(p,'IDLE'),null);
 for(const stage of [1,2,4,5])assert.equal(pilotDefinition('ruu',stage),null);
 assert.equal(await assets.load({...p,stage:2},'IDLE'),null);
 assert.equal(await assets.load({...p,species:'nox'},'IDLE'),null);
 const resolver=new AnimationStateResolver(),input={state:'WALKING',speed:40,suppressed:false};resolver.observe(input,0);
 assert.equal(await assets.load(p,resolver.sampleCompanion(input,0).state),null);
 assert.equal(resolver.sampleCompanion({...input,speed:0},1).state,'IDLE');
 assert.equal(resolver.sampleCompanion({...input,state:'BATTLE'},1).suppressed,true);
});
