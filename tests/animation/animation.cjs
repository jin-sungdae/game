const {test}=require('node:test');
const assert=require('node:assert/strict');
const path=require('node:path');
const {stateClips,parseManifest,spriteSize,directionScale}=require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,'animation/model.js'));
const {AnimationController}=require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,'animation/controller.js'));
const {AssetLoader}=require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,'animation/loader.js'));
const manifest=require('../../public/assets/creatures/moa/stage01/manifest.json');
for(const [state,clip] of Object.entries({IDLE:'idle',WALKING:'walk',SITTING:'sit',LOOKING:'look',SLEEPING:'sleep',REACTING:'react',DRAGGING:'idle'}))
 test(`${state} -> ${clip}`,()=>assert.equal(stateClips[state],clip));
const idle=manifest.animations.idle;
test('state change resets, including shared idle drag clip',()=>{
 let now=0;const c=new AnimationController(()=>now);c.select('IDLE',idle);now=350;assert.equal(c.sample().frame,3);
 c.select('DRAGGING',idle);assert.equal(c.sample().frame,0);
});
test('identical snapshots do not reset time',()=>{
 let now=0;const c=new AnimationController(()=>now);c.select('IDLE',idle);
 for(now=33;now<330;now+=33)c.select('IDLE',{...idle});
 assert.equal(c.sample().frame,3);
});
test('loop wraps using elapsed time, including a delayed tick',()=>{
 let now=0;const c=new AnimationController(()=>now);c.select('idle',idle);now=600;assert.equal(c.sample().frame,0);
 now=1930;assert.equal(c.sample().frame,1);
});
test('react holds final frame and reports completion without changing game state',()=>{
 let now=0;const c=new AnimationController(()=>now);c.select('react',manifest.animations.react);
 now=479;assert.equal(c.sample().frame,5);assert.equal(c.sample().finished,false);
 now=480;assert.equal(c.sample().finished,true);now=10000;assert.equal(c.sample().frame,5);
});
test('LEFT flip',()=>assert.equal(directionScale(-1),-1));
test('RIGHT normal',()=>assert.equal(directionScale(1),1));
test('missing manifest fallback',async()=>{
 const l=new AssetLoader({json:async()=>{throw Error();},image:async()=>{throw Error('must not load');}});
 assert.equal(await l.load('moa',1,'idle'),null);
});
test('missing frame rejects whole clip',async()=>{
 const l=new AssetLoader({json:async()=>manifest,image:async u=>{if(u.endsWith('02.png'))throw Error();return {width:256,height:256};}});
 assert.equal(await l.load('moa',1,'idle'),null);
});
test('complete clip loads with canonical filenames and caches requests',async()=>{
 const calls=[];const l=new AssetLoader({json:async()=>manifest,image:async u=>{calls.push(u);return {width:256,height:256};}});
 const clip=await l.load('moa',1,'idle');assert.equal(clip.urls[0],'/assets/creatures/moa/stage01/idle/idle_00.png');
 assert.equal(await l.load('moa',1,'idle'),clip);assert.equal(calls.length,6);
});
test('inconsistent frame canvas falls back',async()=>{
 const l=new AssetLoader({json:async()=>manifest,image:async()=>({width:128,height:256})});
 assert.equal(await l.load('moa',1,'idle'),null);
});
test('missing clip falls back',async()=>{
 const l=new AssetLoader({json:async()=>manifest,image:async()=>({width:256,height:256})});
 assert.equal(await l.load('moa',1,'future'),null);
});
test('bottom-center fit is unchanged by frame/direction and stays within panel',()=>{
 const size=spriteSize(manifest,104,108);assert.deepEqual(size,{width:104,height:104});
 for(const facing of [-1,1]) {
   // At transform origin (width/2, height), horizontal scaling leaves anchor fixed.
   const anchor={x:size.width/2,y:size.height};
   assert.equal((anchor.x-size.width/2)*directionScale(facing)+size.width/2,anchor.x);
   assert.equal(anchor.y,size.height);
 }
 assert.deepEqual(spriteSize(manifest,500,50),{width:50,height:50});
});
test('manifest rejects incompatible anchor or invalid timing',()=>{
 assert.throws(()=>parseManifest({...manifest,anchor:{x:0,y:1}},'moa',1));
 assert.throws(()=>parseManifest({...manifest,animations:{idle:{...idle,frameDuration:0}}},'moa',1));
});
const {resolveCompanion}=require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,'entities/registry.js'));
for(const species of ['moa','ruu','nox']) {
 test(`${species} stage01 manifest resolves`,()=>{
  assert.deepEqual(resolveCompanion(species,1),{species,evolutionStage:1,assetManifest:`/assets/creatures/${species}/stage01/manifest.json`,name:species.toUpperCase()});
  const m=require(`../../public/assets/creatures/${species}/stage01/manifest.json`);
  assert.equal(parseManifest(m,species,1).species,species);
 });
 test(`${species} missing assets fall back and failure is cached`,async()=>{
  let attempts=0;const m=require(`../../public/assets/creatures/${species}/stage01/manifest.json`);
  const loader=new AssetLoader({json:async()=>m,image:async()=>{attempts++;throw Error('not supplied');}});
  assert.equal(await loader.load(species,1,'idle'),null);
  assert.equal(await loader.load(species,1,'idle'),null);assert.equal(attempts,6);
 });
}
test('unknown species/stage returns fallback without IO or throwing',async()=>{
 const loader=new AssetLoader({json:async()=>{assert.fail('unexpected IO');},image:async()=>{assert.fail('unexpected IO');}});
 for(const [species,stage] of [['unknown',1],['../moa',1],['constructor',1],['moa',4],['ruu',5],['nox',0],['moa',NaN]]) {
  assert.equal(resolveCompanion(species,stage),null);assert.equal(await loader.load(species,stage,'idle'),null);
 }
});

test('MOKORI resolves stage02; missing frames never load stage01',async()=>{
 assert.equal(resolveCompanion('moa',2).name,'MOKORI');
 const manifest=require('../../public/assets/creatures/moa/stage02/manifest.json');const calls=[];
 const loader=new AssetLoader({json:async url=>{calls.push(url);return manifest;},image:async url=>{calls.push(url);throw Error('missing');}});
 assert.equal(await loader.load('moa',2,'idle'),null);assert.equal(await loader.load('moa',2,'idle'),null);
 assert.ok(calls.length>1);assert.ok(calls.every(url=>url.includes('/stage02/')));
});

test('NEBLA missing animation is cached and never requests earlier stages',async()=>{
 const calls=[];const loader=new AssetLoader({json:async url=>{calls.push(url);throw Error('not supplied');},image:async()=>{assert.fail('unexpected image');}});
 assert.equal(await loader.load('moa',3,'idle'),null);assert.equal(await loader.load('moa',3,'idle'),null);
 assert.deepEqual(calls,['/assets/creatures/moa/stage03/manifest.json']);
});
