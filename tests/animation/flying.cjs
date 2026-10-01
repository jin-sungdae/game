const {test}=require('node:test');const assert=require('node:assert/strict');const path=require('node:path');
const load=f=>require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,f));
const {resolveFlying,glideApplicability}=load('animation/flying.js');const {PilotAssets,pilotDefinition,CharacterAnimator}=load('animation/pilot.js');const {AssetLoader}=load('animation/loader.js');
const p=pilotDefinition('CHIRP');const m=require('../../public'+p.manifest);
function input(vx,vy=0,state='ROAMING',suppressed=false){return {state,suppressed,flight:{timestamp:1,x:100,y:100,vx,vy,speed:Math.hypot(vx,vy),active:vx!==0||vy!==0,facing:vx<0?-1:1}};}
test('FLYING observes full velocity magnitude; stationary hover and hysteresis',()=>{
 let state='HOVER';for(const [vx,expected] of [[0,'HOVER'],[7.9,'HOVER'],[8,'FLY'],[4,'FLY'],[3,'FLY'],[2.99,'HOVER'],[-30,'FLY'],[30,'FLY']]){const s=resolveFlying(input(vx),state);assert.equal(s.state,expected);state=s.state;}
 assert.equal(resolveFlying(input(0,10),'HOVER').state,'FLY');assert.equal(resolveFlying(input(0,0),'FLY').state,'HOVER');
 assert.equal(resolveFlying(input(10),'HOVER').rate,.5);assert.equal(resolveFlying(input(200),'FLY').rate,2);assert.equal(glideApplicability,'NOT_APPLICABLE');
 for(const v of [0,20,100,200])assert.notEqual(resolveFlying(input(v),'FLY').state,'GLIDE');
});
test('arrival battle capture despawn lifecycle and invalid signal fail closed',()=>{
 for(const state of ['SPAWNING','ENGAGED','BATTLE','DESPAWNING','DRAGGING'])assert.equal(resolveFlying(input(20,0,state),'FLY').suppressed,true);
 assert.equal(resolveFlying(input(20,0,'ROAMING',true),'FLY').suppressed,true);
 for(const x of [{},input(NaN),input(Infinity),input(257),{...input(20),flight:null}])assert.equal(resolveFlying(x,'FLY').suppressed,true);
 const frozen=input(40);Object.freeze(frozen.flight);resolveFlying(frozen,'HOVER');assert.equal(frozen.flight.x,100);
});
test('all supplied states use own registry, original filenames and approved Alpha timing',async()=>{
 assert.equal(p.status,'FLYING_PRODUCTION');assert.equal(p.base,'/assets/monsters/chirp/base.png');const urls=[];
 const assets=new PilotAssets(new AssetLoader({json:async()=>m,image:async u=>{urls.push(u);return {width:256,height:256}}}));
 for(const [state,count,cycle] of [['HOVER',4,1600],['FLY',6,540],['GLIDE',2,600]]){
  const c=await assets.load(p,state);assert.equal(c.clip.frames,count);assert.equal(c.clip.frameDuration*count,cycle);assert.ok(c.urls[0].endsWith('_01.png'));
  const a=new CharacterAnimator();assert.equal(a.sample(state,c,0,1,false),0);assert.equal(a.sample(state,c,90,1,true),0);
 }
 for(const state of ['IDLE','MOVE','REACT','BLINK','JUMP'])assert.equal(await assets.load(p,state),null);
 assert.ok(urls.every(u=>u.startsWith('/assets/monsters/chirp/')));
});
test('missing frame/manifest, wrong identity/canvas/timing fail closed for every flight clip',async()=>{
 for(const mode of ['missing','image','identity','canvas','timing'])for(const state of ['HOVER','FLY','GLIDE']){
  const a=new PilotAssets(new AssetLoader({json:async()=>{if(mode==='missing')throw Error();return {...m,species:mode==='identity'?'pip':'chirp',animations:mode==='timing'?Object.fromEntries(Object.entries(m.animations).map(([n,c])=>[n,{...c,frameDuration:1}])):m.animations}},image:async()=>{if(mode==='image')throw Error();return {width:mode==='canvas'?128:256,height:256}}}));assert.equal(await a.load(p,state),null);
 }
});
