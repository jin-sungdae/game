const {test}=require('node:test');const assert=require('node:assert/strict');const path=require('node:path');
const load=f=>require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,'animation',f));
const {PilotAssets,pilotDefinition,AnimationStateResolver,CharacterAnimator}=load('pilot.js');const {AssetLoader,browserIO}=load('loader.js');const {IdleSequencer}=load('idle.js');
test('MOVE pilot is explicit, atomic and isolated from approved IDLE and REACT',async()=>{
 const p=pilotDefinition('moa');assert.equal(p.status,'IDLE_PRODUCTION');assert.equal(p.moveStatus,'PRODUCTION');assert.equal(pilotDefinition('PIP').status,'PRODUCTION_PILOT');let requests=[];
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
