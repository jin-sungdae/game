const {test}=require('node:test');const assert=require('node:assert/strict');const path=require('node:path');
const load=f=>require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,f));
const {resolveStatic,peekApplicability}=load('animation/static.js');
const {PilotAssets,pilotDefinition,CharacterAnimator}=load('animation/pilot.js');const {AssetLoader}=load('animation/loader.js');
const p=pilotDefinition('MIMI'),m=require('../../public'+p.manifest);
const assets=(json=m,image=async()=>({width:256,height:256}))=>new PilotAssets(new AssetLoader({json:async()=>json,image}));
test('STATIC has no movement or synthetic PEEK regardless of speed/facing; input unchanged',()=>{
 for(const speed of [0,2,40,256,NaN])for(const facing of [-1,1]){
  const i=Object.freeze({state:'ROAMING',suppressed:false,speed,facing,x:111,y:222});
  assert.deepEqual(resolveStatic(i),{state:'IDLE',suppressed:false,rate:1});assert.equal(i.x,111);assert.equal(i.y,222);assert.equal(i.facing,facing);
 }
 assert.equal(peekApplicability,'NOT_APPLICABLE');
});
test('arrival/rarity and all non-roaming lifecycle states suppress immediately, resume IDLE',()=>{
 for(const state of ['SPAWNING','ENGAGED','BATTLE','CAPTURE','CAPTURED','DESPAWNING','EXPIRED','UNKNOWN'])assert.equal(resolveStatic({state,suppressed:false}).suppressed,true);
 assert.equal(resolveStatic({state:'ROAMING',suppressed:true}).suppressed,true);
 assert.equal(resolveStatic({state:'ROAMING',suppressed:false}).suppressed,false);
});
test('IDLE order and 2500ms loop; PEEK asset non-loop coverage without production trigger',async()=>{
 assert.equal(p.status,'IDLE_PRODUCTION');assert.equal(p.staticProfile,'STATIC');assert.equal(p.base,'/assets/monsters/mimi/base.png');
 for(const [state,duration,loop] of [['IDLE',500,true],['PEEK',120,false]]){
  const c=await assets().load(p,state);assert.equal(c.clip.frames,5);assert.equal(c.clip.frameDuration,duration);assert.equal(c.clip.loop,loop);
  assert.deepEqual(c.urls.map(u=>u.slice(-6)),['01.png','02.png','03.png','04.png','05.png']);
  const a=new CharacterAnimator();for(let t=0;t<=5000;t+=20)assert.equal(a.sample(state,c,t,1,false),loop?Math.floor(t/duration)%5:Math.min(4,Math.floor(t/duration)));
  assert.equal(a.sample('suppressed',null,5020,1,false),0);assert.equal(a.sample(state,c,5040,1,false),0);
  assert.equal(a.sample(state,c,5060,1,true),0);
 }
 for(const s of ['MOVE','REACT','BLINK','JUMP','HOVER','FLOAT'])assert.equal(await assets().load(p,s),null);
});
test('invalid identity/timing/loop/registry and missing frame fail closed to own base',async()=>{
 for(const state of ['IDLE','PEEK']){
  for(const bad of [null,{...m,species:'puff'},{...m,animations:{}},{...m,animations:Object.fromEntries(Object.entries(m.animations).map(([n,c])=>[n,{...c,loop:!c.loop}]))}])assert.equal(await assets(bad).load(p,state),null);
  assert.equal(await assets(m,async()=>{throw Error('missing frame')}).load(p,state),null);
 }
});
test('bundled metadata resolves real supplied filenames; invalid offsets are rejected',async()=>{
 const {browserIO}=load('animation/loader.js');const fs=require('node:fs');
 const a=new PilotAssets(new AssetLoader({json:browserIO.json,image:async url=>{const b=fs.readFileSync(path.join(process.cwd(),'public',url));return {width:b.readUInt32BE(16),height:b.readUInt32BE(20)}}}));
 for(const state of ['IDLE','PEEK'])assert.equal((await a.load(p,state)).urls.length,5);
 const {parseManifest}=load('animation/model.js');
 for(const firstFrame of [-1,2,1.5,'1',null])assert.throws(()=>parseManifest({...m,animations:{idle:{...m.animations.idle,firstFrame}}},'mimi',1));
});
