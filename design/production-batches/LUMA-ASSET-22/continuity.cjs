// Supplemental analysis: preserves historical raw-RGBA validation and approval state.
const crypto = require('node:crypto');
function checkBuffer(data) {
 if(!Buffer.isBuffer(data)||!data.length||data.length%4) throw Error('RGBA buffer required');
}
function visibleHash(data) {
 checkBuffer(data);
 const canonical=Buffer.from(data);
 for(let i=0;i<canonical.length;i+=4) if(canonical[i+3]===0) canonical.fill(0,i,i+3);
 return crypto.createHash('sha256').update(canonical).digest('hex');
}
function compare(a,b) {
 checkBuffer(a);checkBuffer(b);if(a.length!==b.length)throw Error('RGBA dimensions differ');
 let rawMax=0,visibleMax=0,premultipliedMax=0,alphaMax=0,compositeMax=0,compositeSum=0,hiddenChanges=0;
 for(let i=0;i<a.length;i+=4) {
  const aa=a[i+3]/255,ba=b[i+3]/255;
  const alphaDelta=Math.abs(a[i+3]-b[i+3]);
  alphaMax=Math.max(alphaMax,alphaDelta);rawMax=Math.max(rawMax,alphaDelta);
  let pixelCompositeMax=alphaDelta;
  for(let c=0;c<3;c++) {
   const raw=Math.abs(a[i+c]-b[i+c]);rawMax=Math.max(rawMax,raw);
   if(aa===0&&ba===0){if(raw)hiddenChanges++;}else visibleMax=Math.max(visibleMax,raw);
   const ap=a[i+c]*aa,bp=b[i+c]*ba;
   premultipliedMax=Math.max(premultipliedMax,Math.abs(ap-bp));
   // For source-over, channel delta is affine in background [0,255].
   // Its absolute maximum is at black or white, including alpha-only changes.
   const overBlack=Math.abs(ap-bp),overWhite=Math.abs(ap+255*(1-aa)-bp-255*(1-ba));
   pixelCompositeMax=Math.max(pixelCompositeMax,overBlack,overWhite);
   compositeSum+=Math.max(overBlack,overWhite);
  }
  compositeMax=Math.max(compositeMax,pixelCompositeMax);compositeSum+=alphaDelta;
 }
 return {rawMax,visibleMax,premultipliedMax,alphaMax,compositeMax,compositeMean:compositeSum/a.length,hiddenChanges};
}
module.exports={compare,visibleHash};
