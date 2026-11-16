// Independent M061 VICTORY candidate with exact BASE terminal frame. Reuses the existing offline part-weighted inverse-sampling rig.
// Local RGBA parts move, including their silhouette; no global transform or new runtime engine.
const sharp=require(process.env.LUMA_SHARP_MODULE || 'sharp'),fs=require('fs'),crypto=require('crypto');
const root="design/production-batches/luma-asset-16/M061/victory-candidate";
const parts=[{"name": "near-tentacle-flourish", "x": 108, "y": 165, "rx": 22, "ry": 26, "dx": -2.8, "dy": -2.1, "samples": [0.03, 0.25, 0.65, 1, 0.72, 0.32, 0.6, 0.95, 0.7, 0.33, 0.08, 0]}, {"name": "far-tentacle-answer-flourish", "x": 163, "y": 165, "rx": 20, "ry": 24, "dx": 2.6, "dy": -1.7, "samples": [0.02, 0.08, 0.3, 0.65, 0.96, 0.72, 0.4, 0.66, 1, 0.56, 0.13, 0]}, {"name": "oral-arm-release", "x": 136, "y": 143, "rx": 15, "ry": 18, "dx": 0, "dy": 1.1, "samples": [0.02, 0.08, 0.3, 0.65, 0.96, 0.72, 0.4, 0.66, 1, 0.56, 0.13, 0]}];
const fixed=(x,y)=>y>=196||y<=122||x<=65||x>=195;
function displacement(x,y,frame){if(fixed(x,y))return [0,0];let dx=0,dy=0;for(const p of parts){const r=((x-p.x)/p.rx)**2+((y-p.y)/p.ry)**2;if(r>=1)continue;const weight=(1-r)**3*p.samples[frame];dx+=p.dx*weight;dy+=p.dy*weight;}return[dx,dy];}
(async()=>{
 if(fs.existsSync(root+'/rigged'))throw Error('Existing frames protected; no implicit retry');
 const {data,info}=await sharp("design/production-batches/monsters/batch07/M061/base-v2.png").raw().toBuffer({resolveWithObject:true});if(info.width!==256||info.height!==256||info.channels!==4)throw Error('base format');
 fs.mkdirSync(root+'/rigged/victory',{recursive:true});const evidence=[];
 for(let frame=0;frame<12;frame++){
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
  if(fixedChanges||(frame<11&&(!changed||!alphaChanges))||(frame===11&&changed))throw Error('invalid impact rig');
  const file='victory_'+String(frame).padStart(2,'0')+'.png';await sharp(output,{raw:{width:256,height:256,channels:4}}).png().toFile(root+'/rigged/victory/'+file);
  evidence.push({file,pixelSha256:crypto.createHash('sha256').update(output).digest('hex'),changedPixels:changed,fixedRegionChanges:fixedChanges,alphaChangedPixels:alphaChanges,maxInverseDisplacementPixels:maxShift});
 }
 if(new Set(evidence.map(x=>x.pixelSha256)).size!==12)throw Error('duplicate rig frames');
 fs.writeFileSync(root+'/rig-evidence.json',JSON.stringify({reference:"design/production-batches/monsters/batch07/M061/base-v2.png",referenceApproval:'User authorized sequential candidate production and existing part rigging; final appearance/motion pending',parts,protectedRegions:"y>=196||y<=122||x<=65||x>=195",wholeImageTransform:false,silhouetteMotion:true,frames:evidence,repairIterations:3,repairScope:'LUMA-ASSET-16 independent first attempt; inherited 3/3 remains locked; no recovery authorized',productionEligible:false},null,2)+'\n');
})();
