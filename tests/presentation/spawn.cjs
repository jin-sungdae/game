const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');
const {spawnPresentation}=require(path.join(process.env.LUMA_PRESENTATION_TEST_DIR,'spawn.js'));
test('common/debug/unknown remain unchanged; explicit rarity tiers use shared durations',()=>{
 for(const rarity of ['COMMON','EPIC','UNKNOWN',undefined])assert.equal(spawnPresentation(rarity,'SPAWNING',false),null);
 for(const [rarity,duration] of [['UNCOMMON',400],['RARE',750],['SPECIAL',1000]])assert.deepEqual(spawnPresentation(rarity,'SPAWNING',false),{tier:rarity.toLowerCase(),duration});
});
test('cleanup on state exit, battle/capture interruption, restored arrival same contract',()=>{
 for(const rarity of ['UNCOMMON','RARE','SPECIAL']){
  for(const state of ['ROAMING','ENGAGED','DESPAWNING'])assert.equal(spawnPresentation(rarity,state,false),null);
  assert.equal(spawnPresentation(rarity,'SPAWNING',true),null);
  assert.deepEqual(spawnPresentation(rarity,'SPAWNING',false),spawnPresentation(rarity,'SPAWNING',false));
 }
});
test('all fifteen content identities use rarity only with no species/time inference',()=>{
 const defs=JSON.parse(fs.readFileSync('src/entities/monster-dex.json'));
 assert.equal(defs.filter(x=>x.alphaCandidate).length,15);
 for(const m of defs.filter(x=>x.alphaCandidate))assert.equal(spawnPresentation(m.rarity,'SPAWNING',false)?.tier,m.rarity==='COMMON'?undefined:m.rarity.toLowerCase());
});
test('compact opacity layer, reduced motion, no timers/focus or transform collision',()=>{
 const css=fs.readFileSync('src/presentation/spawn.css','utf8');const ts=fs.readFileSync('src/presentation/spawn.ts','utf8');const ui=fs.readFileSync('src/components/Creature.tsx','utf8');
 assert.match(css,/pointer-events:none/);assert.match(css,/prefers-reduced-motion:reduce/);assert.match(css,/spawn-minimal/);assert.match(css,/100%\{opacity:0\}/);
 assert.doesNotMatch(css,/transform:|scale:|position:fixed|infinite/);
 assert.doesNotMatch(ts+ui,/requestAnimationFrame|setInterval|setTimeout|activateApp|makeKey|orderFrontRegardless/);
 assert.match(ui,/aria-hidden="true"/);assert.match(ui,/gp-pose/);assert.match(ui,/gp-impulse/);
});
