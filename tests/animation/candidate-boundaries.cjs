const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const load=f=>require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,f));
const {AssetLoader}=load('animation/loader.js');
const {CharacterAnimator,PilotAssets,pilotDefinition,AnimationStateResolver}=load('animation/pilot.js');
for(const code of ['M003','M006','ruu/stage03','M004','nox/stage02','M008','ruu/stage04','M009','ruu/stage05','M010','ruu/stage03/interact-pilot','M001/interact-pilot','nox/stage02/interact-pilot','M002/interact-pilot','moa/stage05/interact-pilot','ruu/stage04/cursor-react-pilot','M003/interact-pilot','M004/cursor-react-pilot','M006/interact-pilot','ruu/stage05/interact-pilot','M009/interact-pilot','M011/interact-pilot','M012/cursor-react-pilot','moa/stage05/cursor-react-pilot','M013/hit-pilot','M014/hit-pilot','ruu/stage03/hit-pilot','nox/stage02/hit-pilot','moa/stage04/hit-pilot','M018/hit-pilot','ruu/stage04/hit-pilot','moa/stage05/hit-pilot','M022/interact-pilot','ruu/stage05/hit-pilot','M023/interact-pilot','ruu/stage05/cursor-react-pilot','M024/hit-pilot','M027/hit-pilot','M029/cursor-react-pilot','nox/stage02/cursor-react-pilot','moa/stage04/cursor-react-pilot','M031/hit-pilot','M032/interact-pilot','ruu/stage03/cursor-react-pilot','M041/hit-pilot','M045/hit-pilot','M050/hit-pilot','M057/hit-pilot','M058/hit-pilot','M061/interact-pilot','M062/hit-pilot','M066/hit-pilot','M069/hit-pilot','M070/interact-pilot','M081/hit-pilot','M082/hit-pilot','M085/interact-pilot','M088/interact-pilot'])test(`${code} candidate uses real frames and existing clock only in isolated review`,async()=>{
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
  for(let time=0;time<=cycle*2;time+=10){const frame=animator.sample(code,clip,time,rate,false);seen.add(frame);const n=Math.floor(time*rate/spec.clip.frameDuration);assert.equal(frame,spec.clip.loop?n%spec.clip.frames:Math.min(n,spec.clip.frames-1));}
  assert.equal(seen.size,spec.clip.frames);assert.equal(animator.sample(code,clip,cycle*2+10,rate,true),0);
 }
 const missing=new AssetLoader({json:async()=>manifest,image:async url=>{if(url.endsWith('_03.png'))throw Error('missing candidate frame');return image(url)}});
 assert.equal(await missing.loadRegistered('review',1,`/${root}/rigged/manifest.json`,name),null);
 assert.equal(spec.runtimeEnabled,false);assert.equal(spec.productionEligible,false);
});
test('candidate files cannot activate CAPLET MOVE/TURN or RUU LOOK; native sleep remains stationary',async()=>{
 const assets=new PilotAssets(new AssetLoader({json:async()=>{throw Error('unapproved assets must not be loaded')},image:async()=>{throw Error('unapproved frame')}}));
 for(const state of ['MOVE','TURN','REACT','REST','HIT','VICTORY'])assert.equal(await assets.load(pilotDefinition('CAPLET'),state),null);
 assert.equal(await assets.load(pilotDefinition('ruu',3),'LOOK_AROUND'),null);
 for(const [species,stage,state] of [['nox',2,'LOOK_AROUND'],['nox',2,'BLINK'],['nox',2,'SLEEP'],['nox',2,'REACT'],['moa',5,'REACT'],['ruu',4,'CURSOR_REACT'],['ruu',3,'REACT'],['ruu',4,'BLINK'],['ruu',5,'LOOK_AROUND'],['ruu',5,'REACT'],['moa',5,'CURSOR_REACT'],['ruu',3,'HIT'],['nox',2,'HIT'],['moa',4,'HIT'],['ruu',4,'HIT'],['moa',5,'HIT'],['ruu',5,'HIT'],['ruu',5,'CURSOR_REACT'],['nox',2,'CURSOR_REACT'],['moa',4,'CURSOR_REACT'],['ruu',3,'CURSOR_REACT']])assert.equal(await assets.load(pilotDefinition(species,stage),state),null);
 for(const code of ['M003','M006','M004','M008','M009','M010','M001','M002','M011','M012','M013','M014','M018','M017','M020','M019','M021','M022','M023','M024','M025','M026','M027','M028','M029','M030','M031','M032','M039','M041','M042'])assert.equal(pilotDefinition(code),null);
 const resolver=new AnimationStateResolver();
 const input=Object.freeze({state:'SLEEPING',speed:40,suppressed:false,x:80,y:120,facing:-1});
 assert.equal(resolver.sampleCompanion(input,0).state,'SLEEP');assert.deepEqual([input.x,input.y,input.facing],[80,120,-1]);
 assert.equal(resolver.sampleCompanion({...input,state:'ROAMING',speed:0},10).state,'IDLE');
 assert.equal(resolver.sampleCompanion({...input,suppressed:true},20).suppressed,true);
});
