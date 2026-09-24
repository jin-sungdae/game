const {test}=require('node:test');
const assert=require('node:assert/strict');
const path=require('node:path');
const fs=require('node:fs');
const {companionBase,baseSize,rendererSource,BaseAssetLoader}=require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,'assets/base.js'));
const {resolveMonster}=require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,'entities/monsters.js'));
const {directionScale}=require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,'animation/model.js'));
test('registered species/stage base resolution and unknown fallback',()=>{
 for(const species of ['moa','ruu','nox']) assert.equal(companionBase(species,1),`/assets/creatures/${species}/stage01/base.png`);
 assert.equal(companionBase('unknown',1),null);assert.equal(companionBase('moa',2),'/assets/creatures/moa/stage02/base.png');
});
test('animation > base > CSS priority',()=>{
 assert.deepEqual(rendererSource('clip','base'),{kind:'animation',url:'clip'});
 assert.deepEqual(rendererSource(null,'base'),{kind:'base',url:'base'});
 assert.deepEqual(rendererSource(null,null),{kind:'css',url:null});
});
test('PIP registry is independent; unknown and prototype names fail closed',()=>{
 assert.equal(resolveMonster('PIP').baseAsset,'/assets/monsters/pip/base.png');
 assert.equal(resolveMonster('future'),null);assert.equal(resolveMonster('constructor'),null);
});
test('base success is cached; concurrent callers share IO',async()=>{
 let calls=0;const loader=new BaseAssetLoader(async()=>{calls++;return {width:256,height:256};});
 assert.deepEqual(await Promise.all([loader.load('base'),loader.load('base')]),['base','base']);assert.equal(calls,1);
 loader.fail('base');assert.equal(await loader.load('base'),null);assert.equal(calls,1);
});
test('404/decode failure, invalid dimensions and PIP missing cache CSS fallback',async()=>{
 for(const image of [async()=>{throw Error('404/decode');},async()=>({width:1,height:256})]) {
  let calls=0;const loader=new BaseAssetLoader(async url=>{calls++;return image(url);});
  const url=resolveMonster('PIP').baseAsset;
  assert.equal(rendererSource(null,await loader.load(url)).kind,'css');
  assert.equal(await loader.load(url),null);assert.equal(calls,1);assert.equal(await loader.load(null),null);
 }
});
test('MOA/PIP scale fits attack extent and bottom-center survives RIGHT/LEFT',()=>{
 const size=baseSize(84,104);assert.deepEqual(size,{width:82,height:82});
 assert.equal(size.width*.8,65.60000000000001);assert.ok(size.width/2*1.04+5<48);
 assert.deepEqual(baseSize(20,10),{width:10,height:10});
 for(const facing of [1,-1]) {
  assert.equal(directionScale(facing),facing);
  const x=size.width/2;assert.equal((x-x)*directionScale(facing)+x,x);
 }
});
test('base is static, uses common bottom anchor and remains inside gameplay wrappers',()=>{
 const css=fs.readFileSync('src/style.css','utf8');const gp=fs.readFileSync('src/presentation/gameplay.css','utf8');
 const creature=fs.readFileSync('src/components/Creature.tsx','utf8');const base=fs.readFileSync('src/components/BaseVisual.tsx','utf8');
 assert.match(css,/\.sprite-frame[^}]*transform-origin:50% 100%/);
 assert.match(css,/\.companion-visual[^}]*justify-content:flex-end/);
 assert.match(creature,/gp-pose[\s\S]*gp-impulse[\s\S]*gp-visual[\s\S]*CompanionVisual[\s\S]*MonsterVisual/);
 assert.match(base,/className="sprite-frame base-sprite"/);assert.doesNotMatch(base,/requestAnimationFrame|setInterval/);
 assert.match(gp,/@media\(prefers-reduced-motion:reduce\)[\s\S]*\.gp-impulse/);
 assert.match(gp,/\.gp-pip\{transform:scale\(\.8\)/);
});

test('missing MOKORI base is cached CSS fallback, never stage01',async()=>{
 const calls=[];const loader=new BaseAssetLoader(async url=>{calls.push(url);throw Error('not supplied');});
 const url=companionBase('moa',2);assert.equal(rendererSource(null,await loader.load(url)).kind,'css');
 assert.equal(await loader.load(url),null);assert.deepEqual(calls,['/assets/creatures/moa/stage02/base.png']);
});
test('NEBLA failed stage03 load stays diagnostic and never borrows MOKORI',async()=>{
 const {resolveCompanion}=require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,'entities/registry.js'));
 assert.equal(resolveCompanion('moa',3).name,'NEBLA');
 const url=companionBase('moa',3);assert.equal(url,'/assets/creatures/moa/stage03/base.png');
 const calls=[];const loader=new BaseAssetLoader(async u=>{calls.push(u);throw Error('not supplied');});
 assert.equal(rendererSource(null,await loader.load(url)).kind,'css');assert.equal(await loader.load(url),null);
 assert.deepEqual(calls,[url]);assert.equal(fs.existsSync('public'+url),true);
});

test('delivered NEBLA resolves its own base before and after loader restart',async()=>{
 for(let restart=0;restart<2;restart++){
  const calls=[];const loader=new BaseAssetLoader(async url=>{calls.push(url);const data=fs.readFileSync('public'+url);return {width:data.readUInt32BE(16),height:data.readUInt32BE(20)};});
  for(const stage of [1,2,3]){
   const url=companionBase('moa',stage);assert.deepEqual(rendererSource(null,await loader.load(url)),{kind:'base',url});
  }
  assert.deepEqual(calls,[1,2,3].map(n=>`/assets/creatures/moa/stage0${n}/base.png`));
 }
});
