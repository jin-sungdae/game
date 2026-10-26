const test=require('node:test'),assert=require('node:assert/strict');
const {compare,visibleHash}=require('./continuity.cjs');
const rgba=(...v)=>Buffer.from(v);
test('hidden RGB differs in storage but not on any background',()=>{
 const a=rgba(255,0,100,0),b=rgba(0,255,0,0),m=compare(a,b);
 assert.equal(m.rawMax,255);assert.equal(m.compositeMax,0);assert.equal(visibleHash(a),visibleHash(b));
});
test('opaque color discontinuity remains a failure at the existing 100 threshold',()=>{
 assert.equal(compare(rgba(0,0,0,255),rgba(255,0,0,255)).compositeMax,255);
});
test('black alpha-only disappearance must not evade premultiplied RGB checks',()=>{
 const m=compare(rgba(0,0,0,255),rgba(0,0,0,0));assert.equal(m.premultipliedMax,0);assert.equal(m.compositeMax,255);
});
test('semitransparent colors are weighted, not treated as invisible',()=>{
 const m=compare(rgba(255,0,0,128),rgba(0,0,0,128));assert.equal(m.compositeMax,128);assert.equal(m.visibleMax,255);
});
test('one-sided transparent pixels still reveal the visible color',()=>{
 const m=compare(rgba(255,255,255,0),rgba(0,0,0,128));assert.equal(m.compositeMax,128);
});
test('canonical hash retains semitransparent RGB and alpha',()=>{
 assert.notEqual(visibleHash(rgba(1,2,3,1)),visibleHash(rgba(2,2,3,1)));
 assert.notEqual(visibleHash(rgba(0,0,0,0)),visibleHash(rgba(0,0,0,1)));
});
test('black/white envelope bounds arbitrary background composites',()=>{
 for(let alpha=0;alpha<=255;alpha+=17)for(let c=0;c<=255;c+=17){
  const a=rgba(c,127,64,alpha),b=rgba(255-c,32,200,255-alpha),m=compare(a,b);
  for(const bg of [0,31,127,200,255])for(let j=0;j<3;j++)assert.ok(Math.abs(a[j]*a[3]/255+bg*(1-a[3]/255)-b[j]*b[3]/255-bg*(1-b[3]/255))<=m.compositeMax+1e-10);
 }
});
test('invalid RGBA layouts are rejected',()=>{
 assert.throws(()=>compare(Buffer.alloc(3),Buffer.alloc(3)));assert.throws(()=>compare(rgba(0,0,0,0),Buffer.alloc(8)));assert.throws(()=>visibleHash(Buffer.alloc(0)));
});
