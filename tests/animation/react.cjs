const {test}=require('node:test');const assert=require('node:assert/strict');const path=require('node:path');
const load=f=>require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,'animation',f));
const {PilotAssets,pilotDefinition,AnimationStateResolver,CharacterAnimator}=load('pilot.js');const {AssetLoader,browserIO}=load('loader.js');const {IdleSequencer}=load('idle.js');
test('REACT opt-in is atomic, static and own-character only; missing frame isolates failure',async()=>{
 const p=pilotDefinition('moa');assert.equal(p.reactStatus,'PRODUCTION');
 const assets=new PilotAssets(new AssetLoader({json:browserIO.json,image:async u=>{if(u.endsWith('react_03.png'))throw Error('missing');return {width:256,height:256};}}));
 assert.equal(await assets.load(p,'REACT'),null);assert.equal((await assets.load(p,'IDLE')).urls.length,4);assert.equal((await assets.load(p,'MOVE')).urls.length,8);
 assert.equal(p.base,'/assets/creatures/moa/stage01/base.png');assert.equal(await assets.load({...p,reactStatus:undefined},'REACT'),null);assert.equal(await assets.load({...pilotDefinition('PIP'),status:'NOT_SUPPLIED'},'REACT'),null);
});
test('six 80ms frames play once; reduced motion pins neutral; current velocity controls completion',async()=>{
 const asset=await new PilotAssets(new AssetLoader({json:browserIO.json,image:async()=>({width:256,height:256})})).load(pilotDefinition('moa'),'REACT');
 assert.equal(asset.clip.loop,false);const a=new CharacterAnimator();assert.deepEqual([0,80,160,240,320,400,480,560].map(t=>a.sample('REACT',asset,t,1,false)),[0,1,2,3,4,5,5,5]);assert.equal(a.sample('REACT',asset,600,1,true),0);
 for(const [speed,next] of [[0,'IDLE'],[40,'MOVE']]){const r=new AnimationStateResolver();r.observe({state:'REACTING',speed,suppressed:false},0);r.observe({state:'REACTING',speed,suppressed:false},300);assert.equal(r.sample(479).state,'REACT');assert.equal(r.sample(480).state,next);}
});
test('repeated same reaction does not queue; new native edge restarts bounded window; priorities cancel',()=>{
 const r=new AnimationStateResolver();const observe=(state,t,suppressed=false)=>r.observe({state,speed:0,suppressed},t);
 observe('REACTING',0);observe('REACTING',400);assert.equal(r.sample(480).state,'IDLE');
 observe('DRAGGING',500);observe('REACTING',580);assert.equal(r.sample(1059).state,'REACT');assert.equal(r.sample(1060).state,'IDLE');
 for(const state of ['BATTLE','EVOLVING','ENGAGED','DRAGGING']){observe('IDLE',2000);observe('REACTING',2010);observe(state,2020);assert.equal(r.sample(2020).suppressed,true);assert.notEqual(r.sample(2020).state,'REACT');}
 const idle=new IdleSequencer(()=>0),cfg={breath:'breath',blink:'blink',blinkIntervalMs:[3000,7000]};idle.sample(0,true,false,cfg,270);idle.sample(3000,false,false,cfg,270);assert.equal(idle.sample(3480,true,false,cfg,270),'IDLE');assert.equal(idle.sample(6479,true,false,cfg,270),'IDLE');assert.equal(idle.sample(6480,true,false,cfg,270),'BLINK');
});
test('invalid REACT metadata or frame canvas fails closed without manifest fetch',async()=>{
 const p=pilotDefinition('moa'),old=global.fetch;global.fetch=()=>assert.fail('no runtime manifest request');
 try{
  for(const mode of ['identity','loop','duration','dimensions']){
   const assets=new PilotAssets(new AssetLoader({json:async url=>{const m=await browserIO.json(url);if(mode==='identity')m.species='other';if(mode==='loop')m.animations.react.loop=true;if(mode==='duration')m.animations.react.frameDuration=100;return m;},image:async()=>({width:mode==='dimensions'?128:256,height:256})}));
   assert.equal(await assets.load(p,'REACT'),null);
  }
  const asset=await new PilotAssets(new AssetLoader({json:browserIO.json,image:async()=>({width:256,height:256})})).load(p,'REACT');assert.equal(asset.urls.length,6);
 }finally{global.fetch=old;}
});
