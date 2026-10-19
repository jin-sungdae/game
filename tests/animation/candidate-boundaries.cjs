const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const load=f=>require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,f));
const {AssetLoader}=load('animation/loader.js');
const {CharacterAnimator,PilotAssets,pilotDefinition,AnimationStateResolver}=load('animation/pilot.js');
for(const code of ['M003','M006','ruu/stage03'])test(`${code} candidate uses real frames and existing clock only in isolated review`,async()=>{
 const root=`design/production-batches/action-followup/${code}`;
 const spec=JSON.parse(fs.readFileSync(`${root}/candidate-clip.json`));
 const name=spec.clip.name.toLowerCase();
 const manifest={species:'review',stage:1,canvas:spec.canvas,anchor:spec.anchor,display:{width:256},animations:{[name]:{frames:spec.clip.frames,frameDuration:spec.clip.frameDuration,loop:spec.clip.loop}}};
 const image=async url=>{const b=fs.readFileSync(path.join(process.cwd(),url.slice(1)));return {width:b.readUInt32BE(16),height:b.readUInt32BE(20)}};
 const loader=new AssetLoader({json:async()=>manifest,image});
 const clip=await loader.loadRegistered('review',1,`/${root}/rigged/manifest.json`,name);assert.ok(clip);
 assert.equal(clip.urls.length,spec.clip.frames);assert.deepEqual(clip.manifest.anchor,{x:.5,y:1});
 const cycle=spec.clip.frames*spec.clip.frameDuration;
 for(const rate of [1,2]){const animator=new CharacterAnimator();const seen=new Set();
  for(let time=0;time<=cycle*2;time+=10){const frame=animator.sample(code,clip,time,rate,false);seen.add(frame);assert.equal(frame,Math.floor(time*rate/spec.clip.frameDuration)%spec.clip.frames);}
  assert.equal(seen.size,spec.clip.frames);assert.equal(animator.sample(code,clip,cycle*2+10,rate,true),0);
 }
 const missing=new AssetLoader({json:async()=>manifest,image:async url=>{if(url.endsWith('_03.png'))throw Error('missing candidate frame');return image(url)}});
 assert.equal(await missing.loadRegistered('review',1,`/${root}/rigged/manifest.json`,name),null);
 assert.equal(spec.runtimeEnabled,false);assert.equal(spec.productionEligible,false);
});
test('candidate files cannot activate CAPLET MOVE/TURN or RUU LOOK; native sleep remains stationary',async()=>{
 const assets=new PilotAssets(new AssetLoader({json:async()=>{throw Error('unapproved assets must not be loaded')},image:async()=>{throw Error('unapproved frame')}}));
 for(const state of ['MOVE','TURN','REACT','REST'])assert.equal(await assets.load(pilotDefinition('CAPLET'),state),null);
 assert.equal(await assets.load(pilotDefinition('RUU',3),'LOOK_AROUND'),null);
 assert.equal(pilotDefinition('M003'),null);assert.equal(pilotDefinition('M006'),null);
 const resolver=new AnimationStateResolver();
 const input=Object.freeze({state:'SLEEPING',speed:40,suppressed:false,x:80,y:120,facing:-1});
 assert.equal(resolver.sampleCompanion(input,0).state,'SLEEP');assert.deepEqual([input.x,input.y,input.facing],[80,120,-1]);
 assert.equal(resolver.sampleCompanion({...input,state:'ROAMING',speed:0},10).state,'IDLE');
 assert.equal(resolver.sampleCompanion({...input,suppressed:true},20).suppressed,true);
});
