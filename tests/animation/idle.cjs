const {test}=require('node:test');const assert=require('node:assert/strict');const path=require('node:path');
const {IdleSequencer,seededRandom}=require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,'animation/idle.js'));
const {PilotAssets,pilotDefinition,AnimationStateResolver}=require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,'animation/pilot.js'));
const {AssetLoader,browserIO}=require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,'animation/loader.js'));
const {parseManifest}=require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,'animation/model.js'));
const config={breath:'breath',blink:'blink',blinkIntervalMs:[3000,7000]};
test('blink bounded varied intervals, three frames then breath, deterministic RNG',()=>{
 const a=seededRandom(46),b=seededRandom(46);const seq=new IdleSequencer(a);let now=0;
 for(let n=0;n<8;n++){
  const interval=3000+b()*4000;assert.ok(interval>=3000&&interval<=7000);
  assert.equal(seq.sample(now,true,false,config,270),'IDLE');
  assert.equal(seq.sample(now+interval-.01,true,false,config,270),'IDLE');
  assert.equal(seq.sample(now+interval,true,false,config,270),'BLINK');
  for(const dt of [90,180,269])assert.equal(seq.sample(now+interval+dt,true,false,config,270),'BLINK');
  now+=interval+270;assert.equal(seq.sample(now,true,false,config,270),'IDLE');
 }
 const r=seededRandom(46);assert.notEqual(r(),r());
});
test('MOVE REACT suppression and reduced motion cancel; fresh idle reschedules without catchup',()=>{
 for(const mode of ['MOVE','REACT','BATTLE','EVOLVING','REDUCED','UNMOUNT']){
  const s=new IdleSequencer(()=>0);s.sample(0,true,false,config,270);assert.equal(s.sample(3000,true,false,config,270),'BLINK');
  if(mode==='UNMOUNT')s.reset();else assert.equal(s.sample(3050,mode==='REDUCED',mode==='REDUCED',config,270),'IDLE');
  assert.equal(s.sample(10000,true,false,config,270),'IDLE');assert.equal(s.sample(12999,true,false,config,270),'IDLE');assert.equal(s.sample(13000,true,false,config,270),'BLINK');
 }
 const r=new AnimationStateResolver();
 for(const state of ['BATTLE','EVOLVING','ENGAGED','DRAGGING','SLEEPING']){r.observe({state,speed:0,suppressed:false},0);assert.equal(r.sample(0).suppressed,true);}
 r.observe({state:'REACTING',speed:40,suppressed:false},1000);assert.equal(r.sample(1000).state,'REACT');
});
test('static breath and blink loaded atomically per clip; missing blink uses own base, no fetch',async()=>{
 const p=pilotDefinition('moa');const old=global.fetch;global.fetch=()=>assert.fail('fetch');
 try{
  const assets=new PilotAssets(new AssetLoader({json:browserIO.json,image:async()=>({width:256,height:256})}));
  const breath=await assets.load(p,'IDLE'),blink=await assets.load(p,'BLINK');
  assert.equal(breath.urls.length,4);assert.equal(breath.clip.frameDuration*4,1800);assert.equal(blink.urls.length,3);assert.equal(blink.clip.loop,false);
  assert.ok(blink.urls.every(u=>u.includes('/moa/stage01/blink/')));
  const missing=new PilotAssets(new AssetLoader({json:browserIO.json,image:async u=>{if(u.endsWith('blink_01.png'))throw Error();return {width:256,height:256};}}));
  assert.equal(await missing.load(p,'BLINK'),null);assert.equal(p.base,'/assets/creatures/moa/stage01/base.png');
  assert.equal(await assets.load(pilotDefinition('PIP'),'BLINK'),null);
  for(const change of [{blinkIntervalMs:[0,99999]},{breath:'walk'},{blink:'react'}]){
   const m=await browserIO.json(p.manifest);m.idleSequences={...config,...change};assert.throws(()=>parseManifest(m,'moa',1));
  }
 }finally{global.fetch=old;}
});
