// Independent M090 REST candidate. Reuses the existing offline part-weighted inverse-sampling rig.
// Local RGBA parts move, including their silhouette; no global transform or new runtime engine.
const sharp=require(process.env.LUMA_SHARP_MODULE || 'sharp'),fs=require('fs'),crypto=require('crypto');
const root="design/production-batches/LUMA-ASSET-21/continuation-02/M090/rest";
const parts=[{"x": 97, "y": 161, "rx": 16, "ry": 19, "dx": 0.9, "dy": 0.8, "name": "wing-upper-relax", "samples": [0.04, 0.22, 0.58, 1, 0.76, 0.31, 0.08, 0]}, {"x": 84, "y": 190, "rx": 17, "ry": 14, "dx": 1, "dy": 0.5, "name": "wing-lower-relax", "samples": [0.025, 0.13, 0.39, 0.72, 1, 0.45, 0.1, 0]}];
const fixed=(x,y)=>y>=210||y<=138||x<=64||x>=118;
function displacement(x,y,frame){if(fixed(x,y))return [0,0];let dx=0,dy=0;for(const p of parts){const r=((x-p.x)/p.rx)**2+((y-p.y)/p.ry)**2;if(r>=1)continue;const weight=(1-r)**3*p.samples[frame];dx+=p.dx*weight;dy+=p.dy*weight;}return[dx,dy];}
(async()=>{
 const {data,info}=await sharp("design/production-batches/monsters/batch09/M090/base-v2.png").raw().toBuffer({resolveWithObject:true});if(info.width!==256||info.height!==256||info.channels!==4)throw Error('base format');
 fs.mkdirSync(root+'/rigged/rest',{recursive:true});const evidence=[];
 for(let frame=0;frame<8;frame++){
  const output=Buffer.from(data);let changed=0,fixedChanges=0,maxShift=0,alphaChanges=0;
  for(let y=0;y<256;y++)for(let x=0;x<256;x++){
   if(fixed(x,y))continue;
   let sx=x,sy=y;for(let k=0;k<4;k++){const [dx,dy]=displacement(sx,sy,frame);sx=x-dx;sy=y-dy;}
   const shift=Math.hypot(sx-x,sy-y);maxShift=Math.max(maxShift,shift);if(shift<1e-9)continue;
   const x0=Math.floor(sx),y0=Math.floor(sy),fx=sx-x0,fy=sy-y0;let alpha=0,rgb=[0,0,0];
   for(let oy=0;oy<2;oy++)for(let ox=0;ox<2;ox++){const xx=x0+ox,yy=y0+oy;if(xx<0||xx>=256||yy<0||yy>=256)continue;const w=(ox?fx:1-fx)*(oy?fy:1-fy),n=(yy*256+xx)*4,a=data[n+3]/255;alpha+=a*w;for(let c=0;c<3;c++)rgb[c]+=data[n+c]*a*w;}
   const n=(y*256+x)*4;output[n+3]=Math.round(alpha*255);for(let c=0;c<3;c++)output[n+c]=alpha>0?Math.round(rgb[c]/alpha):0;
  }
  for(let y=0;y<256;y++)for(let x=0;x<256;x++){const n=(y*256+x)*4;let diff=false;for(let c=0;c<4;c++)if(data[n+c]!==output[n+c])diff=true;if(diff){changed++;if(fixed(x,y))fixedChanges++;}if(data[n+3]!==output[n+3])alphaChanges++;}
  if(fixedChanges || (frame<7 && (!changed||!alphaChanges)) || (frame===7 && !output.equals(data)))throw Error('invalid local motion or BASE return');
  const file='rest_'+String(frame).padStart(2,'0')+'.png';await sharp(output,{raw:{width:256,height:256,channels:4}}).png().toFile(root+'/rigged/rest/'+file);
  if(frame===3)await sharp(output,{raw:{width:256,height:256,channels:4}}).png().toFile(root+'/keypose.png');
  evidence.push({file,pixelSha256:crypto.createHash('sha256').update(output).digest('hex'),changedPixels:changed,fixedRegionChanges:fixedChanges,alphaChangedPixels:alphaChanges,maxInverseDisplacementPixels:maxShift});
 }
 if(new Set(evidence.map(x=>x.pixelSha256)).size!==8)throw Error('duplicate rig frames');
 fs.writeFileSync(root+'/rig-evidence.json',JSON.stringify({reference:"design/production-batches/monsters/batch09/M090/base-v2.png",referenceApproval:'User authorized sequential candidate production and existing part rigging; final appearance/motion pending',parts,protectedRegions:"y>=210||y<=138||x<=64||x>=118",wholeImageTransform:false,silhouetteMotion:true,frames:evidence,repairIterations:3,repairScope:'LUMA-ASSET-21 independent first attempt; inherited 3/3 limit; no failure recovery',productionEligible:false},null,2)+'\n');
})();
