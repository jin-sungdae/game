const {test}=require('node:test'),assert=require('node:assert/strict'),path=require('node:path'),fs=require('node:fs');
const load=f=>require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,f));
const {monsterDex}=load('entities/monsterDex.js'),{resolveMonster}=load('entities/monsters.js'),{pilotDefinition,PilotAssets}=load('animation/pilot.js'),{AssetLoader,browserIO}=load('animation/loader.js');
const profiles={GROUND:['PIP','MOSSY','PEBB','TIKKI'],JUMP:['MELLO','BUBU'],FLYING:['CHIRP'],FLOATING:['PUFF','WISP','LUNET'],STATIC:['MIMI'],EDGE:['SHADE','NOCT'],FREE_2D:['EMBER','NOVA']};
const required={GROUND:['IDLE','MOVE'],JUMP:['JUMP'],FLYING:['HOVER','FLY'],FLOATING:['HOVER','FLOAT'],STATIC:['IDLE'],EDGE:['IDLE','EDGE_MOVE'],FREE_2D:['FLICKER','FLOW']};
const keys={GROUND:'groundProfile',JUMP:'jumpProfile',FLYING:'flyingProfile',FLOATING:'floatingProfile',STATIC:'staticProfile',EDGE:'edgeProfile',FREE_2D:'free2dProfile'};
test('Active Alpha content + asset + animation coverage is exactly 15/15; provisional excluded',async()=>{
 const active=monsterDex.filter(m=>m.enabled&&m.contentReady&&m.alphaCandidate&&m.productionStatus==='PRODUCTION');
 assert.equal(active.length,15);assert.deepEqual(active.map(m=>m.monsterCode).sort(),Object.values(profiles).flat().sort());const rows=[];
 for(const m of active){
  const code=m.monsterCode,asset=resolveMonster(code),p=pilotDefinition(code);assert.ok(p);assert.notEqual(p.status,'NOT_SUPPLIED');assert.ok(profiles[m.movementProfile].includes(code));assert.equal(p[keys[m.movementProfile]],m.movementProfile);assert.equal(p.species,m.assetIdentity);assert.equal(p.base,asset.baseAsset);assert.ok(fs.existsSync(path.join('public',p.base)));assert.equal(p.sourceFacing,'RIGHT');
  const io={...browserIO,image:async u=>{assert.ok(u.startsWith(asset.assetRoot+'/'));const b=fs.readFileSync(path.join('public',u));return {width:b.readUInt32BE(16),height:b.readUInt32BE(20)}}};const a=new PilotAssets(new AssetLoader(io));
  for(const state of required[m.movementProfile]){assert.ok(await a.load(p,state),code+' '+state);assert.equal(await new PilotAssets(new AssetLoader({...io,image:async()=>{throw Error('missing')}})).load(p,state),null);}
  rows.push({monster:code,profile:m.movementProfile,behavior:m.behaviorProfile,states:required[m.movementProfile],base:p.base,coverage:'COMPLETE'});
 }
 const provisional=monsterDex.filter(m=>m.productionStatus==='PROVISIONAL');assert.equal(provisional.length,15);for(const m of provisional){assert.equal(m.enabled,false);assert.equal(m.contentReady,false);assert.equal(pilotDefinition(m.monsterCode),null);}
 if(process.env.LUMA_COVERAGE_OUTPUT)fs.writeFileSync(process.env.LUMA_COVERAGE_OUTPUT,JSON.stringify({active:15,complete:15,notSupplied:0,coveragePercent:100,provisionalExcluded:15,rows},null,2)+'\n');
});
