// Offline ruu/stage04-specific gaze rig using the existing RGBA inverse-sampling approach.
const sharp=require(process.env.LUMA_SHARP_MODULE||'sharp'),fs=require('fs'),crypto=require('crypto');
const root="design/production-batches/luma-asset-02/ruu/stage04/look",source="public/assets/creatures/ruu/stage04/base.png";
const eyes=[{"x": 209.5, "y": 86.5, "rx": 4.5, "ry": 3, "dx": 0.72}],gaze=[0.04, 0.42, 0.94, 0.68, 0.16, -0.42, -0.81, -0.09];
(async()=>{const {data,info}=await sharp(source).raw().toBuffer({resolveWithObject:true});if(info.width!==256||info.height!==256||info.channels!==4)throw Error('invalid base');
fs.mkdirSync(root+'/rigged/look',{recursive:true});const frames=[];
for(let frame=0;frame<gaze.length;frame++){
 const output=Buffer.from(data);
 for(const e of eyes)for(let y=Math.ceil(e.y-e.ry);y<=Math.floor(e.y+e.ry);y++)for(let x=Math.ceil(e.x-e.rx);x<=Math.floor(e.x+e.rx);x++){
  const radius=((x-e.x)/e.rx)**2+((y-e.y)/e.ry)**2;if(radius>=1)continue;
  const sx=x-e.dx*gaze[frame]*(1-radius)**2,x0=Math.floor(sx),t=sx-x0,n=(y*256+x)*4;
  for(let c=0;c<3;c++)output[n+c]=Math.round(data[(y*256+x0)*4+c]*(1-t)+data[(y*256+x0+1)*4+c]*t);
 }
 const file=`look_${String(frame).padStart(2,'0')}.png`;await sharp(output,{raw:{width:256,height:256,channels:4}}).png().toFile(root+'/rigged/look/'+file);
 if(frame===3)await sharp(output,{raw:{width:256,height:256,channels:4}}).png().toFile(root+'/keypose.png');
 frames.push({file,gaze:gaze[frame],pixelSha256:crypto.createHash('sha256').update(output).digest('hex')});
}
if(new Set(frames.map(f=>f.pixelSha256)).size!==8)throw Error('duplicate frames');
fs.writeFileSync(root+'/rig-evidence.json',JSON.stringify({source,eyes,frames,alphaPolicy:'unchanged',fixedAnatomy:'all pixels outside eye ellipses',productionEligible:false,artwork:'HUMAN_REVIEW_REQUIRED',sessionId:"LUMA-ASSET-02",attempt:1,priorRepairLimitPreserved:true,reusedRig:"design/production-batches/action-followup/ruu/stage03/rig-look.cjs"},null,2)+'\n');
})();
