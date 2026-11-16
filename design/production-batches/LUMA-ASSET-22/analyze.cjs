// Read-only PNG analysis, with supplemental output separate from historical evidence.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const sharp=require(process.env.LUMA_SHARP_MODULE||'sharp');
const {compare,visibleHash}=require('./continuity.cjs');
const root=__dirname,repo=path.resolve(root,'../../..');
(async()=>{
 const results=[];
 for(const id of ['M092','M095']) {
  const basePath=path.join(repo,'design/production-batches/monsters/batch10',id,'base-v2.png');
  const base=await sharp(basePath).raw().toBuffer();
  for(const action of ['breath','blink','look']) {
   const dir=path.join(root,id,action==='breath'?'':action),rig=JSON.parse(fs.readFileSync(path.join(dir,'rig-evidence.json')));
   const clip=JSON.parse(fs.readFileSync(path.join(dir,'candidate-clip.json'))).clip;
   const frames=[],buffers=[];
   for(let i=0;i<clip.frames;i++) {
    const file=path.join(dir,'rigged',action,`${action}_${String(i).padStart(2,'0')}.png`);
    const {data,info}=await sharp(file).raw().toBuffer({resolveWithObject:true});
    let protectedChanges=0,changed=0;
    const eyes=rig.eyes;
    for(let n=0;n<data.length;n+=4){
     const x=(n/4)%256,y=Math.floor(n/1024);
     if(data.subarray(n,n+4).some((v,c)=>v!==base[n+c])){
      changed++;
      if(eyes&&!eyes.some(e=>((x-e.x)/e.rx)**2+((y-e.y)/e.ry)**2<1))protectedChanges++;
     }
    }
    frames.push({file:path.relative(repo,file),fileSha256:crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'),visiblePixelHash:visibleHash(data),format:info.width===256&&info.height===256&&info.channels===4,changedPixels:changed,protectedChanges,baseDifference:compare(base,data)});
    buffers.push(data);
   }
   const transitions=buffers.map((a,i)=>({from:i,to:(i+1)%buffers.length,...compare(a,buffers[(i+1)%buffers.length])}));
   const baseEntry=compare(base,buffers[0]),baseReturn=compare(buffers.at(-1),base);
   const numericPass=[...transitions,baseEntry,baseReturn].every(t=>t.compositeMax<100&&t.compositeMean<0.12);
   const uniqueVisibleFrames=new Set(frames.map(f=>f.visiblePixelHash)).size;
   const anatomyPass=frames.every(f=>f.format&&f.protectedChanges===0&&f.baseDifference.alphaMax===0);
   results.push({id,action,frames,transitions,baseEntry,baseReturn,uniqueVisibleFrames,numericPass,anatomyPass,
    status:action==='breath'?'SUPPLEMENTAL_ONLY':numericPass&&anatomyPass&&uniqueVisibleFrames===clip.frames?'AUTOMATED_CANDIDATE':'VALIDATION_FAILED',
    historicalStatus:action==='breath'?JSON.parse(fs.readFileSync(path.join(dir,'frame-validation.json'))).automated:null,
    approval:'HUMAN_REVIEW_REQUIRED',productionEligible:false,runtimeEnabled:false});
  }
 }
 const output=path.join(root,'continuation-analysis.json');
 fs.writeFileSync(output,JSON.stringify({schemaVersion:1,scope:'LUMA-ASSET-22 only; original evidence and thresholds unchanged',thresholds:{max:100,mean:0.12},results},null,2)+'\n');
 for(const r of results)console.log(r.id,r.action,r.status,'max',Math.max(...r.transitions.map(t=>t.compositeMax)),'return',r.baseReturn.compositeMax,'unique',r.uniqueVisibleFrames);
})();
