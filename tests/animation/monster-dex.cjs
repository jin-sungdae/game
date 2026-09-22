const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = process.env.LUMA_ANIMATION_TEST_DIR;
const dex = require(path.join(root, 'entities/monsterDex.js'));
const {resolveMonster} = require(path.join(root, 'entities/monsters.js'));
const {dexEntry, dexEntries} = require(path.join(root, 'presentation/monsterDex.js'));
const raw = JSON.parse(fs.readFileSync('src/entities/monster-dex.json', 'utf8'));
const progress = (discovered = [], captured = []) => ({discoveredCodes:new Set(discovered), capturedCodes:new Set(captured)});
const invalid = patch => assert.throws(() => dex.parseMonsterDefinitions([{...raw[0], ...patch}]));
test('all thirty slots validate with unique codes/numbers and exact rarity distribution', () => {
 assert.equal(dex.monsterDex.length, 30);
 assert.equal(new Set(dex.monsterDex.map(m => m.monsterCode)).size, 30);
 assert.deepEqual(dex.monsterDex.map(m => m.dexNo), Array.from({length:30}, (_,i) => i+1));
 assert.deepEqual(dex.rarities.map(r => dex.monsterDex.filter(m => m.rarity === r).length), [8,7,6,5,4]);
 assert.ok(Object.isFrozen(dex.monsterDex)); assert.ok(dex.monsterDex.every(Object.isFrozen));
 for (const m of dex.monsterDex.slice(1)) {
  assert.equal(m.displayName, null); assert.equal(m.enabled, false); assert.equal(m.encounterWeight, 0);
  assert.equal(m.baseCaptureRate, null); assert.equal(m.productionStatus, 'PROVISIONAL');
 }
});
test('vocabulary parsers accept every supported value and reject invalid types/unknowns', () => {
 for (const [values, parse] of [[dex.rarities,dex.parseRarity],[dex.archetypes,dex.parseArchetype],
 [dex.movementProfiles,dex.parseMovementProfile],[dex.behaviorProfiles,dex.parseBehaviorProfile],
 [dex.spawnProfiles,dex.parseSpawnProfile],[dex.spawnConditions,dex.parseSpawnCondition]]) {
  for (const value of values) assert.equal(parse(value), value);
  for (const value of ['unknown','constructor','',null,3,{},values[0].toLowerCase()]) assert.throws(() => parse(value));
 }
});
test('movement wire vocabulary matches existing Rust serde enum, including FREE_2D', () => {
 const source = fs.readFileSync('src-tauri/src/movement/mod.rs','utf8');
 const body = source.match(/pub enum MovementProfile \{([\s\S]*?)\}/)[1];
 const names = [...body.matchAll(/(?:#\[serde\(rename = "([^"]+)"\)\]\s*)?([A-Z][A-Za-z0-9]*),/g)]
  .map(m => m[1] ?? m[2].replace(/([a-z])([A-Z])/g,'$1_$2').toUpperCase());
 assert.deepEqual(dex.movementProfiles, names);
});
test('PIP metadata and production asset stay compatible with existing gameplay', () => {
 const pip = dex.resolveMonsterDefinition('PIP');
 assert.deepEqual([pip.rarity,pip.archetype,pip.movementProfile,pip.encounterWeight,pip.baseCaptureRate,pip.visualScale], ['COMMON','BEAST','GROUND',100,.35,.8]);
 assert.deepEqual(dex.enabledMonsterDefinitions().map(m => m.monsterCode), ['PIP']);
 assert.deepEqual(resolveMonster('PIP'), {name:'PIP',assetRoot:'/assets/monsters/pip',baseAsset:'/assets/monsters/pip/base.png',visualScale:.8,alphaDelivery:true});
 const seed = fs.readFileSync('server/src/main/resources/db/migration/V2__local_master_seed.sql','utf8');
 assert.ok(seed.includes("('PIP','PIP','COMMON','GROUND',1,3,100,true)"));
});
test('unknown/prototype names and all unproduced slots have diagnostic fallback', () => {
 for (const code of ['unknown','constructor','__proto__','toString']) {
  assert.equal(resolveMonster(code),null); assert.equal(dex.resolveMonsterDefinition(code),null);
 }
 for (const m of dex.monsterDex.slice(1)) {
  assert.equal(resolveMonster(m.monsterCode).baseAsset,null);
  assert.equal(resolveMonster(m.monsterCode).assetRoot,`/assets/monsters/${m.assetIdentity}`);
 }
});
test('bounds reject nonfinite/fractional values, malformed identities and incomplete definitions', () => {
 for (const visualScale of [0,.49,1.51,NaN,Infinity,'1',null]) invalid({visualScale});
 for (const visualScale of [.5,1,1.5]) assert.equal(dex.parseMonsterDefinitions([{...raw[0],visualScale}])[0].visualScale,visualScale);
 for (const encounterWeight of [-1,.5,NaN,Infinity]) invalid({encounterWeight});
 for (const baseCaptureRate of [-.1,1.1,NaN,Infinity]) invalid({baseCaptureRate});
 for (const dexNo of [0,1.1,NaN,Infinity]) invalid({dexNo});
 invalid({monsterCode:'../pip'}); invalid({assetIdentity:'../pip'}); invalid({enabled:'false'});
 invalid({alphaCandidate:1}); invalid({displayName:''}); invalid({productionStatus:'UNKNOWN'});
 for (const input of [null,{},[null],[{}],[[]]]) assert.throws(() => dex.parseMonsterDefinitions(input));
 for (const key of Object.keys(raw[0])) { const entry={...raw[0]}; delete entry[key]; assert.throws(() => dex.parseMonsterDefinitions([entry]),key); }
});
test('duplicate identity and Dex number are rejected independently', () => {
 assert.throws(() => dex.parseMonsterDefinitions([raw[0],{...raw[1],monsterCode:'PIP'}]));
 assert.throws(() => dex.parseMonsterDefinitions([raw[0],{...raw[1],dexNo:1}]));
});
test('enabled content must have confirmed production metadata', () => {
 invalid({productionStatus:'PROVISIONAL'}); invalid({displayName:null}); invalid({encounterWeight:0}); invalid({baseCaptureRate:null});
 assert.throws(() => dex.parseMonsterDefinitions([{...raw[1],enabled:true}]));
 assert.equal(dex.parseMonsterDefinitions([{...raw[0],enabled:false}])[0].enabled,false);
});
test('Alpha candidates cover silhouettes, movement, rarity and desktop spawn diversity', () => {
 const alpha = dex.monsterDex.filter(m => m.alphaCandidate);
 assert.ok(alpha.length >= 12 && alpha.length <= 15);
 for (const [key, vocabulary] of [['archetype',dex.archetypes],['movementProfile',dex.movementProfiles],['rarity',dex.rarities],['spawnProfile',dex.spawnProfiles]])
  assert.deepEqual([...new Set(alpha.map(m => m[key]))].sort(), [...vocabulary].sort());
 assert.deepEqual(alpha.filter(m => m.enabled).map(m => m.monsterCode), ['PIP']);
});
test('Dex masks undiscovered names/assets and capture supersedes discovery', () => {
 const pip = dex.monsterDex[0];
 assert.deepEqual(dexEntry(pip,progress()), {dexNo:1,monsterCode:'PIP',state:'UNDISCOVERED',displayName:'???',visual:'SILHOUETTE',baseAsset:null,visualScale:.8});
 assert.equal(dexEntry(pip,progress(['PIP'])).state,'DISCOVERED');
 const captured = dexEntry(pip,progress([],['PIP']));
 assert.equal(captured.state,'CAPTURED'); assert.equal(captured.visual,'BASE'); assert.equal(captured.displayName,'PIP');
 const provisional = dexEntry(dex.monsterDex[1],progress(['MONSTER_002']));
 assert.equal(provisional.displayName,'???'); assert.equal(provisional.visual,'DIAGNOSTIC');
 assert.equal(dexEntries(progress([],dex.monsterDex.map(m => m.monsterCode))).length,1);
 assert.equal(dexEntries(progress(['unknown']))[0].state,'UNDISCOVERED');
});
test('documentation includes exactly the same 30 design slots and Alpha flags', () => {
 const doc = fs.readFileSync('docs/monster-dex-v01.md','utf8');
 const rows = doc.split('\n').filter(line => /^\| \d+ \|/.test(line));
 assert.equal(rows.length,30);
 for (const [i,row] of rows.entries()) {
  const cells=row.split('|').slice(1,-1).map(s => s.trim()); const m=dex.monsterDex[i];
  assert.deepEqual(cells,[...['dexNo','monsterCode','workingName','rarity','archetype','movementProfile','behaviorProfile','spawnProfile','spawnCondition','captureDirection','visualTheme','productionStatus'].map(k => String(m[k])),m.alphaCandidate?'candidate':'—']);
 }
});
