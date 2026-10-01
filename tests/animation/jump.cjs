const {test}=require('node:test');const assert=require('node:assert/strict');const path=require('node:path');
const load=f=>require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,f));
const {jumpFrame}=load('animation/jump.js');const {pilotDefinition,PilotAssets,AnimationStateResolver}=load('animation/pilot.js');const {AssetLoader}=load('animation/loader.js');
const p=pilotDefinition('MELLO');const manifest=require('../../public'+p.manifest);
const sample=(phase,vy=1,grounded=false)=>({phase,vy,grounded,progress:.2,x:100,y:20,vx:10,timestamp:1,facing:1});
test('native phases select frames without elapsed playback, ground gate fails closed',()=>{
 for(const [phase,i,vy,g] of [['LAUNCH',2,20,false],['ASCEND',3,10,false],['APEX',4,0,false],['DESCEND',5,-10,false],['LAND',6,0,true]]){
  assert.equal(jumpFrame(sample(phase,vy,g),false,false),i);
  assert.equal(jumpFrame(sample(phase,vy,g),true,false),null);assert.equal(jumpFrame(sample(phase,vy,g),false,true),null);
 }
 for(const s of [null,sample('CROUCH'),sample('SETTLE'),sample('NEUTRAL'),sample('LAND',0,false),sample('DESCEND',-2,true),sample('ASCEND',-1),sample('DESCEND',1),sample('APEX',NaN)])assert.equal(jumpFrame(s,false,false),null);
});
test('registered JUMP production; IDLE REACT BLINK unavailable; all failures own base',async()=>{
 assert.equal(p.status,'JUMP_PRODUCTION');
 assert.equal(p.jumpProfile,'JUMP');
 assert.equal(p.base,'/assets/monsters/mello/base.png');
 for(const failure of [null,'manifest','image','identity','phase','dimensions']){
  const assets=new PilotAssets(new AssetLoader({json:async()=>{if(failure==='manifest')throw Error();return {...manifest,species:failure==='identity'?'pip':'mello',jumpPhases:failure==='phase'?[]:manifest.jumpPhases}},image:async()=>{if(failure==='image')throw Error();return {width:failure==='dimensions'?128:256,height:256}}}));
  const c=await assets.load(p,'JUMP');
  if(failure)assert.equal(c,null);else{assert.equal(c.urls.length,8);assert.equal(c.urls[0],'/assets/monsters/mello/jump/jump_01.png');assert.equal(c.urls[7],'/assets/monsters/mello/jump/jump_08.png');}
  for(const state of ['IDLE','MOVE','REACT','BLINK'])assert.equal(await assets.load(p,state),null);
 }
});
test('existing priority and cleanup suppress jump for encounter and presentation',()=>{
 for(const state of ['ENGAGED','BATTLE','EVOLVING','DRAGGING','SLEEPING']){const r=new AnimationStateResolver();r.observe({state,speed:20,suppressed:false},0);assert.equal(jumpFrame(sample('ASCEND'),r.sample(0).suppressed,false),null);}
 const r=new AnimationStateResolver();r.observe({state:'SPAWNING',speed:20,suppressed:true},0);assert.equal(r.sample(0).suppressed,true);
});
