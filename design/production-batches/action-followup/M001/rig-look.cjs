// Offline M001-specific gaze rig using the existing RGBA inverse-sampling approach.
const sharp=require(process.env.LUMA_SHARP_MODULE||'sharp'),fs=require('fs'),crypto=require('crypto');
const root="design/production-batches/action-followup/M001",source="design/production-batches/monsters/batch01/M001/base-v2.png";
const eyes=[{"x": 153, "y": 132, "rx": 9, "ry": 12, "dx": 1.3}, {"x": 188, "y": 131, "rx": 4.5, "ry": 10, "dx": 0.5}],gaze=[0.12, 0.5, 0.9, 0.65, -0.1, -0.55, -0.85, -0.4];
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
fs.writeFileSync(root+'/rig-evidence.json',JSON.stringify({source,eyes,frames,alphaPolicy:'unchanged',fixedAnatomy:'all pixels outside eye ellipses',productionEligible:false,artwork:'HUMAN_REVIEW_REQUIRED',repairIterations:0},null,2)+'\n');
})();
