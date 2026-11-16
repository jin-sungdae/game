// Read-only pixel verification of this session's existing-part-rig candidates.
const sharp=require(process.env.LUMA_SHARP_MODULE||'sharp'),fs=require('fs'),crypto=require('crypto');
(async()=>{
 const results=[];
 for(const code of ['M031','M032']){
  const root=`design/production-batches/LUMA-ASSET-10/${code}/breath`;
  const base=await sharp(`design/production-batches/monsters/batch04/${code}/base-v2.png`).raw().toBuffer();
  const protectedPixel=code==='M031'?(x,y)=>y<=143||y>=191||x<=68||x>=151:(x,y)=>y<=145||y>=185||x<=88||x>=153;
  const frames=[];const records=[];
  for(let i=0;i<8;i++){
   const {data,info}=await sharp(`${root}/rigged/breath/breath_${String(i).padStart(2,'0')}.png`).raw().toBuffer({resolveWithObject:true});
   let protectedChanges=0,alphaChanges=0,changedPixels=0;
   for(let y=0;y<256;y++)for(let x=0;x<256;x++){
    const n=(y*256+x)*4;const changed=[0,1,2,3].some(c=>base[n+c]!==data[n+c]);
    if(changed){changedPixels++;if(protectedPixel(x,y))protectedChanges++;}
    if(base[n+3]!==data[n+3])alphaChanges++;
   }
   if(info.width!==256||info.height!==256||info.channels!==4||protectedChanges||alphaChanges||!changedPixels)throw Error(`${code} frame ${i} invalid`);
   frames.push(data);records.push({frame:i,changedPixels,protectedChanges,alphaChanges,pixelHash:crypto.createHash('sha256').update(data).digest('hex')});
  }
  if(new Set(records.map(r=>r.pixelHash)).size!==8)throw Error('duplicate frame');
  const continuity=frames.map((a,i)=>{
   const b=frames[(i+1)%8];let total=0,max=0;
   for(let n=0;n<a.length;n++){const delta=Math.abs(a[n]-b[n]);total+=delta;max=Math.max(max,delta);}
   return{from:i,to:(i+1)%8,meanChannelDelta:total/a.length,maxChannelDelta:max};
  });
  if(continuity.some(r=>r.meanChannelDelta>.5||r.maxChannelDelta>90))throw Error('continuity threshold exceeded; preserve candidate without repair');
  results.push({conceptId:code,status:'PASS',wholeImageTransform:false,frameCount:8,frames:records,continuity,appearanceDrift:'Protected head, eyes, feet, tail, silhouette unchanged; visual approval still required',productionEligible:false,runtimeEnabled:false});
 }
 console.log(JSON.stringify({sessionId:'LUMA-ASSET-10',results},null,2));
})().catch(e=>{console.error(e);process.exit(1)});
