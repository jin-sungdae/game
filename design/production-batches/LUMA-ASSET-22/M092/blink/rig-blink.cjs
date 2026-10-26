// Offline M091-M095 scoped eye rig. Uses the existing sharp RGBA candidate pipeline.
// Unapproved candidate BASE supplies all frame pixels; no Production approval inferred.
const sharp=require(process.env.LUMA_SHARP_MODULE||'sharp'),fs=require('fs'),crypto=require('crypto');
const root="design/production-batches/LUMA-ASSET-22/M092/blink",source="design/production-batches/monsters/batch10/M092/base-v2.png";
const eyes=[{"x": 176, "y": 94, "rx": 8, "ry": 6}],closure=[0,0.06,0.18,0.36,0.58,0.8,1,0.82,0.6,0.38,0.2,0.08];
(async()=>{const {data,info}=await sharp(source).raw().toBuffer({resolveWithObject:true});if(info.width!==256||info.height!==256||info.channels!==4)throw Error('invalid base');
if(fs.existsSync(root+'/rigged'))throw Error('Existing candidate preserved');
fs.mkdirSync(root+'/rigged/blink',{recursive:true});const frames=[];
for(let frame=0;frame<closure.length;frame++){
 const output=Buffer.from(data),amount=closure[frame];
 for(const e of eyes)for(let y=Math.ceil(e.y-e.ry);y<=Math.floor(e.y+e.ry);y++)for(let x=Math.ceil(e.x-e.rx);x<=Math.floor(e.x+e.rx);x++){
  const nx=(x-e.x)/e.rx,ny=(y-e.y)/e.ry;if(nx*nx+ny*ny>=1||amount===0)continue;
  const n=(y*256+x)*4,scale=1-.94*amount,sy=e.y+(y-e.y)/scale;
  const y0=Math.max(0,Math.min(255,Math.floor(sy))),y1=Math.min(255,y0+1),t=sy-Math.floor(sy);
  const top=(Math.floor(e.y-e.ry)*256+x)*4,bottom=(Math.ceil(e.y+e.ry)*256+x)*4;
  const inside=Math.abs(sy-e.y)<e.ry;
  const edge=Math.min(1,Math.max(0,(1-nx*nx-ny*ny)*5));
  for(let c=0;c<3;c++){
   const skin=data[top+c]*(1-(ny+1)/2)+data[bottom+c]*(ny+1)/2;
   const value=inside?data[(y0*256+x)*4+c]*(1-t)+data[(y1*256+x)*4+c]*t:skin;
   output[n+c]=Math.round(data[n+c]*(1-edge)+value*edge);
  }
 }
 const file=`blink_${String(frame).padStart(2,'0')}.png`;
 await sharp(output,{raw:{width:256,height:256,channels:4}}).png().toFile(root+'/rigged/blink/'+file);
 if(amount===1)await sharp(output,{raw:{width:256,height:256,channels:4}}).png().toFile(root+'/keypose.png');
 frames.push({file,closure:amount,pixelSha256:crypto.createHash('sha256').update(output).digest('hex')});
}
if(new Set(frames.map(x=>x.pixelSha256)).size!==12)throw Error('duplicate frames');
fs.writeFileSync(root+'/rig-evidence.json',JSON.stringify({source,eyes,frames,alphaPolicy:'unchanged source alpha',fixedAnatomy:'all pixels outside eye ellipses',productionEligible:false,artwork:'HUMAN_REVIEW_REQUIRED',inheritedRepairIterations:3,repairLimit:3,failedCandidateRecovery:false},null,2)+'\n');
})();
