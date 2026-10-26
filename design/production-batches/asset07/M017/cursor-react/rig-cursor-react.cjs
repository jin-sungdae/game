// LUMA-ASSET-07: existing offline part rig reuse. Candidate only; no paid API.
// Offline single-direction cursor attention cue; existing inverse-sampling eye rig.
const sharp=require(process.env.LUMA_SHARP_MODULE||'sharp'),fs=require('fs'),crypto=require('crypto');
const root="design/production-batches/asset07/M017/cursor-react",source="design/production-batches/monsters/batch02/M017/base-v2.png";
const eyes=[{"x": 198, "y": 136, "rx": 7.5, "ry": 7, "dx": 1}, {"x": 217, "y": 133, "rx": 3, "ry": 5, "dx": 0.45}],gaze=[0.08, 0.35, 0.8, 1, 0.85, 0.5, 0.22, 0.04];
if(fs.existsSync(root+'/rigged'))throw Error('existing candidate must be preserved');
(async()=>{const {data,info}=await sharp(source).raw().toBuffer({resolveWithObject:true});if(info.width!==256||info.height!==256||info.channels!==4)throw Error('invalid base');
fs.mkdirSync(root+'/rigged/cursor_react',{recursive:true});const frames=[];
for(let frame=0;frame<gaze.length;frame++){
 const output=Buffer.from(data);
 for(const e of eyes)for(let y=Math.ceil(e.y-e.ry);y<=Math.floor(e.y+e.ry);y++)for(let x=Math.ceil(e.x-e.rx);x<=Math.floor(e.x+e.rx);x++){
  const radius=((x-e.x)/e.rx)**2+((y-e.y)/e.ry)**2;if(radius>=1)continue;
  const sx=x-e.dx*gaze[frame]*(1-radius)**2,x0=Math.floor(sx),t=sx-x0,n=(y*256+x)*4;
  for(let c=0;c<3;c++)output[n+c]=Math.round(data[(y*256+x0)*4+c]*(1-t)+data[(y*256+x0+1)*4+c]*t);
 }
 const file=`cursor_react_${String(frame).padStart(2,'0')}.png`;await sharp(output,{raw:{width:256,height:256,channels:4}}).png().toFile(root+'/rigged/cursor_react/'+file);
 if(frame===3)await sharp(output,{raw:{width:256,height:256,channels:4}}).png().toFile(root+'/keypose.png');
 frames.push({file,gaze:gaze[frame],pixelSha256:crypto.createHash('sha256').update(output).digest('hex')});
}
if(new Set(frames.map(f=>f.pixelSha256)).size!==8)throw Error('duplicate frames');
fs.writeFileSync(root+'/rig-evidence.json',JSON.stringify({source,eyes,frames,alphaPolicy:'unchanged',fixedAnatomy:'all pixels outside eye ellipses',productionEligible:false,artwork:'HUMAN_REVIEW_REQUIRED',repairIterations:3,repairScope:"LUMA-ASSET-07; inherited 3/3; independent first attempt"},null,2)+'\n');
})();
