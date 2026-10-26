// Read-only measurements for LUMA-ASSET-01 candidates. Does not approve artwork.
const sharp=require(process.env.LUMA_SHARP_MODULE||'sharp');
const fs=require('fs'),path=require('path');
const root=__dirname;
// Continuity threshold is an inspection heuristic, not natural-motion acceptance.
function detached(data){
 const seen=new Uint8Array(65536),sizes=[];
 for(let i=0;i<65536;i++){if(seen[i]||!data[i*4+3])continue;
 const todo=[i];seen[i]=1;let count=0;
 while(todo.length){const n=todo.pop();count++;const x=n%256,y=Math.floor(n/256);
 for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){const xx=x+dx,yy=y+dy;if(xx<0||xx>=256||yy<0||yy>=256)continue;const j=yy*256+xx;if(!seen[j]&&data[j*4+3]){seen[j]=1;todo.push(j);}}}
 sizes.push(count);}
 return sizes.reduce((a,b)=>a+b,0)-Math.max(0,...sizes);
}
(async()=>{const results=[];
 for(const stage of ['stage01','stage02','stage04']){
 const action=stage==='stage04'?'interact':'hit',dir=path.join(root,'moa',stage,action);
 const base=await sharp(`public/assets/creatures/moa/${stage}/base.png`).raw().toBuffer();
 const frames=[];let previous=base;
 for(let i=0;i<8;i++){
 const file=path.join(dir,'rigged',action,`${action}_${String(i).padStart(2,'0')}.png`);
 const data=await sharp(file).raw().toBuffer();let changed=0,delta=0,alpha=0;
 for(let p=0;p<65536;p++){let different=false;for(let c=0;c<4;c++){const n=p*4+c;different ||= data[n]!==base[n];delta+=Math.abs(data[n]-previous[n]);}if(different)changed++;if(data[p*4+3]!==base[p*4+3])alpha++;}
 frames.push({frame:i,changedPixels:changed,alphaChangedPixels:alpha,detachedAlphaPixels:detached(data),adjacentMeanAbsoluteChannelDelta:delta/data.length});previous=data;
 }
 const baseDetached=detached(base),valid=frames.every(f=>f.detachedAlphaPixels<=baseDetached&&f.adjacentMeanAbsoluteChannelDelta<1);
 results.push({stage,action,baseDetachedAlphaPixels:baseDetached,alphaReadiness:baseDetached===0?'PASS':'BLOCKED_SOURCE_ALPHA_RESIDUE',frames,automatedContinuity:valid?'PASS':'FAIL',appearanceDrift:'MANUAL_REVIEW_REQUIRED',anatomicalContinuity:'MANUAL_REVIEW_REQUIRED',productionEligible:false});
 }
 fs.writeFileSync(path.join(root,'measurements.json'),JSON.stringify(results,null,2)+'\n');
 if(results.some(r=>r.automatedContinuity!=='PASS'))process.exitCode=1;
})();
