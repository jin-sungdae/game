const activeCodes = ['PIP','MELLO','MOSSY','CHIRP','BUBU','PEBB','PUFF','TIKKI','MIMI','WISP'];
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {monsterDex,parseMonsterDefinitions}=require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,'entities/monsterDex.js'));
const {resolveMonster}=require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,'entities/monsters.js'));
const expected=`1 PIP COMMON BEAST GROUND PLAYFUL NEAR_DOCK ANY_TIME
2 MELLO COMMON SLIME JUMP CURIOUS BOTTOM ANY_TIME
3 MOSSY COMMON PLANT GROUND SLEEPY LOWER_CORNER ANY_TIME
4 CHIRP COMMON BIRD FLYING CURIOUS TOP ANY_TIME
6 BUBU COMMON AQUATIC JUMP PLAYFUL BOTTOM ANY_TIME
7 PEBB COMMON ROCK GROUND PASSIVE NEAR_DOCK ANY_TIME
8 PUFF COMMON SPIRIT FLOATING CURIOUS FREE_AREA ANY_TIME
10 TIKKI UNCOMMON MECHANICAL GROUND CURIOUS BOTTOM ANY_TIME
13 MIMI UNCOMMON MIMIC STATIC TRICKSTER EDGE ANY_TIME
14 WISP UNCOMMON SPIRIT FLOATING TIMID FREE_AREA ANY_TIME
15 SHADE UNCOMMON SHADOW EDGE TRICKSTER EDGE NIGHT
16 EMBER RARE FIRE FREE_2D AGGRESSIVE FREE_AREA ANY_TIME
19 LUNET RARE MOON FLOATING TIMID FREE_AREA NIGHT
21 NOVA RARE COSMIC FREE_2D CURIOUS FREE_AREA ANY_TIME
28 NOCT SPECIAL NIGHT EDGE TIMID EDGE NIGHT`.split('\n').map(s=>s.split(' '));
const alpha=monsterDex.filter(m=>m.alphaCandidate);
test('exact 15 confirmed Alpha identities and all approved profile mappings',()=>{
 assert.deepEqual(alpha.map(m=>[String(m.dexNo),m.monsterCode,m.rarity,m.archetype,m.movementProfile,m.behaviorProfile,m.spawnProfile,m.spawnCondition]),expected);
 assert.equal(new Set(alpha.map(m=>m.monsterCode)).size,15);
 assert.equal(new Set(alpha.map(m=>m.dexNo)).size,15);
 for(const m of alpha) assert.equal(m.displayName,m.monsterCode);
});
test('only SHADE LUNET NOCT have Alpha night conditions',()=>{
 assert.deepEqual(alpha.filter(m=>m.spawnCondition==='NIGHT').map(m=>m.monsterCode),['SHADE','LUNET','NOCT']);
 assert.equal(alpha.filter(m=>m.spawnCondition==='ANY_TIME').length,12);
});
test('static economic projections exactly match single server Domain defaults',()=>{
 const defaults=JSON.parse(fs.readFileSync('server/src/main/resources/content/rarity-defaults.json','utf8'));
 for(const m of alpha) {
  assert.equal(m.encounterWeight,defaults[m.rarity].encounterWeight);
  assert.equal(m.baseCaptureRate,defaults[m.rarity].baseCaptureRate);
 }
});
test('only validated Batch 1 is ready and enabled; other Alpha remains diagnostic',()=>{
 assert.deepEqual(monsterDex.filter(m=>m.contentReady).map(m=>m.monsterCode),activeCodes);
 assert.deepEqual(monsterDex.filter(m=>m.enabled).map(m=>m.monsterCode),activeCodes);
 for(const m of alpha) {
  assert.equal(m.visualScale,m.monsterCode==='PIP'?.8:1);
  assert.equal(m.assetIdentity,m.monsterCode.toLowerCase());
  assert.equal(resolveMonster(m.monsterCode).assetRoot,`/assets/monsters/${m.assetIdentity}`);
  if(!activeCodes.includes(m.monsterCode)) {
   // A canonical delivery URL is not evidence of delivered art or gameplay readiness.
   assert.equal(resolveMonster(m.monsterCode).baseAsset,`/assets/monsters/${m.assetIdentity}/base.png`);
   assert.throws(()=>parseMonsterDefinitions([{...m,enabled:true}]));
   assert.throws(()=>parseMonsterDefinitions([{...m,contentReady:true}]));
  }
 }
});
test('the other fifteen stable slots remain provisional non-Alpha and not playable',()=>{
 const slots=monsterDex.filter(m=>!m.alphaCandidate);assert.equal(slots.length,15);
 for(const m of slots) {assert.equal(m.monsterCode,`MONSTER_${String(m.dexNo).padStart(3,'0')}`);assert.equal(m.displayName,null);assert.equal(m.encounterWeight,0);assert.equal(m.contentReady,false);}
});
