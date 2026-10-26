// Independent M029 INTERACT candidate. Reuses the existing offline part-weighted inverse-sampling rig.
// Local RGBA parts move, including their silhouette; no global transform or new runtime engine.
const sharp=require(process.env.LUMA_SHARP_MODULE || 'sharp'),fs=require('fs'),crypto=require('crypto');
const root="design/production-batches/luma-asset-09/M029/hit";
const parts=[{"x": 103, "y": 160, "rx": 28, "ry": 30, "dx": 2.6, "dy": 1.4, "name": "near-wing-brace", "samples": [0, 0.65, 1, 0.78, 0.44, 0.15, 0.03, 0]}, {"x": 198, "y": 164, "rx": 19, "ry": 29, "dx": -2.2, "dy": 1.6, "name": "far-wing-fold", "samples": [0, 0.12, 0.52, 1, 0.74, 0.35, 0.08, 0]}, {"x": 85, "y": 82, "rx": 23, "ry": 29, "dx": 1.8, "dy": 1.2, "name": "ear-flinch", "samples": [0, 0.04, 0.18, 0.56, 1, 0.54, 0.12, 0]}, {"x": 67, "y": 198, "rx": 25, "ry": 12, "dx": 1.4, "dy": -0.8, "name": "tail-recover", "samples": [0, 0.65, 1, 0.78, 0.44, 0.15, 0.03, 0]}];
const fixed=(x,y)=>y>=211||y<=52||x<=38||x>=224;
function displacement(x,y,frame){if(fixed(x,y))return [0,0];let dx=0,dy=0;for(const p of parts){const r=((x-p.x)/p.rx)**2+((y-p.y)/p.ry)**2;if(r>=1)continue;const weight=(1-r)**3*p.samples[frame];dx+=p.dx*weight;dy+=p.dy*weight;}return[dx,dy];}
(async()=>{
 const {data,info}=await sharp("design/production-batches/monsters/batch03/M029/base-v2.png").raw().toBuffer({resolveWithObject:true});if(info.width!==256||info.height!==256||info.channels!==4)throw Error('base format');
 fs.mkdirSync(root+'/rigged/hit',{recursive:true});const evidence=[];
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
  if(fixedChanges || (frame>0 && frame<7 && (!changed||!alphaChanges)))throw Error('invalid part rig');
  const file='hit_'+String(frame).padStart(2,'0')+'.png';await sharp(output,{raw:{width:256,height:256,channels:4}}).png().toFile(root+'/rigged/hit/'+file);

  evidence.push({file,pixelSha256:crypto.createHash('sha256').update(output).digest('hex'),changedPixels:changed,fixedRegionChanges:fixedChanges,alphaChangedPixels:alphaChanges,maxInverseDisplacementPixels:maxShift});
 }
 if(new Set(evidence.map(x=>x.pixelSha256)).size!==7 || evidence[0].pixelSha256!==evidence[7].pixelSha256)throw Error('expected BASE endpoints and six distinct poses');
 fs.writeFileSync(root+'/rig-evidence.json',JSON.stringify({reference:"design/production-batches/monsters/batch03/M029/base-v2.png",referenceApproval:'User authorized sequential candidate production and existing part rigging; final appearance/motion pending',parts,protectedRegions:"y>=211||y<=52||x<=38||x>=224",wholeImageTransform:false,silhouetteMotion:true,frames:evidence,repairIterations:3,repairScope:'Inherited 3/3 preserved; LUMA-ASSET-09 independent first attempt; no failure recovery',productionEligible:false},null,2)+'\n');
})();
