const {test}=require('node:test');const assert=require('node:assert/strict');const path=require('node:path');
const {AnimationStateResolver}=require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,'animation/pilot.js'));
const trace=require('../live/caplet-living/native-trace.json');
test('Rust World sleep trace selects registered sleep and preserves world anchor until wake',()=>{
 const first=trace[0],last=trace.at(-1);assert.equal(first.state,'SLEEPING');assert.equal(last.state,'ROAMING');
 const resolver=new AnimationStateResolver();let previous=first.time;
 for(const row of trace){assert.ok(row.time>=previous);previous=row.time;
  const result=resolver.sampleCompanion({state:row.state,speed:0,suppressed:false},row.time*1000);
  if(row.state==='SLEEPING'){assert.deepEqual([row.x,row.y,row.facing],[first.x,first.y,first.facing]);assert.equal(result.state,'SLEEP');}
  else assert.equal(result.state,'IDLE');
 }
});
