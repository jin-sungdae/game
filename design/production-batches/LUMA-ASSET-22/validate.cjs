// Offline candidate regression only; never writes Production or shared registries.
const fs = require('fs'), path = require('path'), crypto = require('crypto');
const sharp = require(process.env.LUMA_SHARP_MODULE || 'sharp');
const root = 'design/production-batches/LUMA-ASSET-22';
const hash = data => crypto.createHash('sha256').update(data).digest('hex');
(async () => {
 const results=[];
 for(const id of ['M092','M095']) {
  const source=`design/production-batches/monsters/batch10/${id}`;
  const base=await sharp(`${source}/base-v2.png`).raw().toBuffer();
  const rig=JSON.parse(fs.readFileSync(`${root}/${id}/rig-evidence.json`));
  const frames=[], decoded=[];
  const oldHashes=new Set();
  for(const name of fs.readdirSync(`${source}/rigged/idle`)) oldHashes.add(hash(await sharp(`${source}/rigged/idle/${name}`).raw().toBuffer()));
  const protectedPixel=id==='M092' ? (x,y)=>y<=148||y>=174||x<=98||x>=140 : (x,y)=>y<=138||y>=164||x<=124||x>=166;
  for(let i=0;i<8;i++) {
   const file=`${root}/${id}/rigged/breath/breath_${String(i).padStart(2,'0')}.png`;
   const {data,info}=await sharp(file).raw().toBuffer({resolveWithObject:true});
   let changed=0, protectedChanges=0, alphaChanges=0, totalDelta=0;
   for(let n=0;n<data.length;n+=4) {
    const x=(n/4)%256,y=Math.floor(n/1024);
    const different=data.subarray(n,n+4).some((v,c)=>v!==base[n+c]);
    if(different){changed++;if(protectedPixel(x,y))protectedChanges++;}
    if(data[n+3]!==base[n+3])alphaChanges++;
    for(let c=0;c<4;c++)totalDelta+=Math.abs(data[n+c]-base[n+c]);
   }
   const pixelSha256=hash(data);
   const pass=info.width===256&&info.height===256&&info.channels===4&&changed>0&&changed<600&&protectedChanges===0&&alphaChanges===0&&!oldHashes.has(pixelSha256)&&pixelSha256===rig.frames[i].pixelSha256;
   frames.push({file,pixelSha256,changedPixels:changed,protectedChanges,alphaChanges,meanAbsoluteChannelDelta:totalDelta/data.length,duplicatesExistingIdle:oldHashes.has(pixelSha256),pass});
   decoded.push(data);
  }
  const continuity=decoded.map((a,i)=>{
   const b=decoded[(i+1)%8];let delta=0,max=0;
   for(let n=0;n<a.length;n++){const d=Math.abs(a[n]-b[n]);delta+=d;max=Math.max(max,d);}
   return {from:i,to:(i+1)%8,meanAbsoluteChannelDelta:delta/a.length,maxChannelDelta:max};
  });
  const unique=new Set(frames.map(f=>f.pixelSha256)).size===8;
  // Conservative numerical guard; perceptual motion and species approval remain manual.
  const pass=frames.every(f=>f.pass)&&unique&&continuity.every(c=>c.meanAbsoluteChannelDelta<0.12&&c.maxChannelDelta<100);
  const result={conceptId:id,automated:pass?'PASS':'FAIL',frames,continuity,uniqueFrames:unique,alphaAndAnchor:'UNCHANGED_FROM_UNAPPROVED_BASE',appearanceScope:'Protected regions pixel-identical; local ribcage/shoulder changes only. Semantic identity NOT_VERIFIED.',naturalMotion:'MANUAL_REQUIRED',productionEligible:false};
  fs.writeFileSync(`${root}/${id}/frame-validation.json`,JSON.stringify(result,null,2)+'\n');results.push({id,status:result.automated});
 }
 console.log(JSON.stringify(results));if(results.some(r=>r.status!=='PASS'))process.exitCode=1;
})();
