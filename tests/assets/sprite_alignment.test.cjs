const {test}=require('node:test');
const assert=require('node:assert/strict');
const {translate,visibleHash}=require('../../scripts/recover_sprite_alignment.cjs');
test('integer translation preserves visible RGBA and moves exact coordinates',()=>{
  const data=Buffer.alloc(4*4*4);data.set([10,20,30,128],(1*4+1)*4);
  const moved=translate(data,4,4,1,-1);
  assert.deepEqual([...moved.subarray(8,12)],[10,20,30,128]);
  assert.equal(visibleHash(data),visibleHash(moved));assert.equal(data[23],128);
});
test('rejects clipping even one nearly transparent pixel',()=>{
  const data=Buffer.alloc(16);data.set([1,2,3,1],0);
  assert.throws(()=>translate(data,2,2,-1,0),/clip/);
});
test('rejects subpixel resampling and nonfinite offsets',()=>{
  for(const x of [.5,NaN,Infinity]) assert.throws(()=>translate(Buffer.alloc(16),2,2,x,0),/integer/);
});
test('zero translation keeps every byte including transparent RGB',()=>{
  const data=Buffer.from([1,2,3,0,4,5,6,255]);
  assert.deepEqual(translate(data,2,1,0,0),data);
});
