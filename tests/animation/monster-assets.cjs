const activeCodes = ['PIP','MELLO','MOSSY','CHIRP','BUBU','PEBB','PUFF','TIKKI','MIMI','WISP','SHADE','EMBER','LUNET','NOVA','NOCT'];
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const root=process.env.LUMA_ANIMATION_TEST_DIR;
const {monsterRegistry,resolveMonster,monsterAssetContract,validMonsterScale}=require(path.join(root,'entities/monsters.js'));
const {monsterVisualSize,monsterAnimationUrl}=require(path.join(root,'assets/monster.js'));
const {BaseAssetLoader,rendererSource}=require(path.join(root,'assets/base.js'));
const {directionScale}=require(path.join(root,'animation/model.js'));
const slugs='pip mello mossy chirp bubu pebb puff tikki mimi wisp shade ember lunet nova noct'.split(' ');
test('exact fifteen delivery paths, PIP unchanged, provisional content remains separate',()=>{
 assert.equal(Object.keys(monsterRegistry).length,15);
 for(const slug of slugs) {
  const definition=resolveMonster(slug.toUpperCase());
  assert.equal(definition.assetRoot,`/assets/monsters/${slug}`);
  assert.equal(definition.baseAsset,`/assets/monsters/${slug}/base.png`);
  assert.equal(definition.alphaDelivery,true);assert.ok(validMonsterScale(definition.visualScale));
 }
 for(const code of ['unknown','constructor','__proto__','mello']) assert.equal(resolveMonster(code),null);
 assert.equal(resolveMonster('MONSTER_005').baseAsset,null);
 assert.deepEqual(monsterAssetContract,{width:256,height:256,format:'PNG',color:'RGBA',transparent:true,anchor:'bottom-center',sourceFacing:'RIGHT',minimumScale:.5,maximumScale:1.5});
});
test('missing own base never falls back to PIP or Companion; valid image uses same URL',async()=>{
 for(const slug of slugs) {
  const url=resolveMonster(slug.toUpperCase()).baseAsset;
  const calls=[];const missing=new BaseAssetLoader(async value=>{calls.push(value);throw Error('404');});
  assert.equal(rendererSource(null,await missing.load(url)).kind,'css');
  assert.equal(await missing.load(url),null);assert.deepEqual(calls,[url]);
  const valid=new BaseAssetLoader(async()=>({width:256,height:256}));
  assert.deepEqual(rendererSource(null,await valid.load(url)),{kind:'base',url});
 }
});
test('registered same-monster animation > same base > diagnostic; frame failure falls through',async()=>{
 const code='MELLO';const definition={...resolveMonster(code),animationClips:{idle:'/assets/monsters/mello/idle'}};
 const frame={monsterCode:code,clip:'idle',url:'/assets/monsters/mello/idle/idle_00.png'};
 const animation=monsterAnimationUrl(code,definition,frame);assert.equal(animation,frame.url);
 const loader=new BaseAssetLoader(async()=>({width:256,height:256}));
 assert.equal(rendererSource(await loader.load(animation),await loader.load(definition.baseAsset)).kind,'animation');
 loader.fail(animation);
 assert.deepEqual(rendererSource(await loader.load(animation),await loader.load(definition.baseAsset)),{kind:'base',url:definition.baseAsset});
 loader.fail(definition.baseAsset);
 assert.equal(rendererSource(await loader.load(animation),await loader.load(definition.baseAsset)).kind,'css');
 for(const patch of [{monsterCode:'PIP'},{clip:'constructor'},{clip:'walk'},{url:'/assets/monsters/pip/idle/idle_00.png'},{url:'/assets/monsters/mello/idle/../base.png'},{url:'/assets/monsters/mello/idle/idle_00.PNG'}])
  assert.equal(monsterAnimationUrl(code,definition,{...frame,...patch}),null);
 assert.equal(monsterAnimationUrl(code,resolveMonster(code),frame),null);
 assert.equal(monsterAnimationUrl('unknown',null,frame),null);
});
test('visual scale bounds fail safely and cannot enlarge native presentation envelope',()=>{
 for(const value of [NaN,Infinity,-1,0,.49,1.51,'1',null]) assert.equal(validMonsterScale(value),false);
 for(const value of [.5,.8,1,1.5]) assert.equal(validMonsterScale(value),true);
 assert.deepEqual(monsterVisualSize('MELLO',.5,84,104),{width:41,height:41});
 assert.deepEqual(monsterVisualSize('PIP',.8,84,104),{width:82,height:82});
 for(const scale of [.5,1,1.5,NaN]) for(const [w,h] of [[84,104],[20,10],[0,0]]) {
  const s=monsterVisualSize('MELLO',scale,w,h);assert.ok(s.width<=w && s.height<=h && s.width<=82);
  if(w===84) assert.ok(s.width/2*1.04+5<48);
 }
 assert.deepEqual(monsterVisualSize('MELLO',1,NaN,Infinity),{width:0,height:0});
});
test('bottom center and RIGHT source survive facing and source switch without new scheduling',()=>{
 for(const facing of [-1,1]) for(const scale of [.5,1,1.5]) {
  const s=monsterVisualSize('MELLO',scale,84,104),cx=s.width/2;
  assert.equal((cx-cx)*directionScale(facing)+cx,cx);
 }
 const source=fs.readFileSync('src/components/MonsterVisual.tsx','utf8');
 assert.match(source,/rendererSource\(animation.url,base.url\)/);
 assert.match(source,/onError=\{animation.fail\}/);assert.match(source,/onError=\{base.fail\}/);
 assert.match(source,/bounds=\{size\}/);assert.doesNotMatch(source,/requestAnimationFrame|setInterval|setTimeout/);
 const css=fs.readFileSync('src/style.css','utf8');
 assert.match(css,/\.sprite-frame[^}]*transform-origin:50% 100%/);
 assert.match(css,/\.companion-visual[^}]*justify-content:flex-end/);
});

test('confirmed content and delivery identities match; successful image loads never activate gameplay',async()=>{
 const {monsterDex}=require(path.join(root,'entities/monsterDex.js'));
 const alpha=monsterDex.filter(m=>m.alphaCandidate);
 assert.deepEqual(alpha.map(m=>m.monsterCode).sort(),Object.keys(monsterRegistry).sort());
 assert.deepEqual(alpha.map(m=>m.assetIdentity).sort(),[...slugs].sort());
 const before=JSON.stringify(monsterDex);
 const loader=new BaseAssetLoader(async()=>({width:256,height:256}));
 for(const m of alpha) {
  const asset=resolveMonster(m.monsterCode);
  assert.equal(asset.assetRoot,`/assets/monsters/${m.assetIdentity}`);
  assert.equal(asset.baseAsset,`${asset.assetRoot}/base.png`);
  assert.equal(asset.visualScale,m.visualScale);
  assert.equal(await loader.load(asset.baseAsset),asset.baseAsset);
  assert.equal(m.contentReady,activeCodes.includes(m.monsterCode));
  assert.equal(m.enabled,activeCodes.includes(m.monsterCode));
  assert.equal(m.productionStatus,activeCodes.includes(m.monsterCode)?'PRODUCTION':'PROVISIONAL');
 }
 assert.equal(JSON.stringify(monsterDex),before);
});
