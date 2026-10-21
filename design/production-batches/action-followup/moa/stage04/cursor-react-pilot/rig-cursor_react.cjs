// Independent companion:moa:4 CURSOR_REACT candidate. Reuses the existing offline part-weighted inverse-sampling rig.
// Local RGBA parts move, including their silhouette; no global transform or new runtime engine.
const sharp=require(process.env.LUMA_SHARP_MODULE || 'sharp'),fs=require('fs'),crypto=require('crypto');
const root="design/production-batches/action-followup/moa/stage04/cursor-react-pilot";
const parts=[{"name": "leaf-ear-attention", "x": 164, "y": 81, "rx": 18, "ry": 13, "dx": 1.6, "dy": -0.8, "samples": [0.02, 0.29, 0.76, 1, 0.87, 0.53, 0.24, 0.04]}, {"name": "gentle-neck-incline", "x": 185, "y": 128, "rx": 22, "ry": 24, "dx": 1.7, "dy": -0.7, "samples": [0.01, 0.08, 0.32, 0.79, 1, 0.88, 0.46, 0.06]}, {"name": "mantle-delayed-settle", "x": 111, "y": 136, "rx": 32, "ry": 27, "dx": -1.3, "dy": 0.7, "samples": [0.01, 0.03, 0.14, 0.44, 0.83, 1, 0.65, 0.09]}, {"name": "leaf-tail-counterbalance", "x": 68, "y": 181, "rx": 29, "ry": 19, "dx": 1, "dy": -1.2, "samples": [0.01, 0.04, 0.22, 0.61, 0.94, 1, 0.59, 0.07]}];
const fixed=(x,y)=>y>=206||y<=67||x<=40||x>=224;
function displacement(x,y,frame){if(fixed(x,y))return [0,0];let dx=0,dy=0;for(const p of parts){const r=((x-p.x)/p.rx)**2+((y-p.y)/p.ry)**2;if(r>=1)continue;const weight=(1-r)**3*p.samples[frame];dx+=p.dx*weight;dy+=p.dy*weight;}return[dx,dy];}
(async()=>{
 const {data,info}=await sharp("public/assets/creatures/moa/stage04/base.png").raw().toBuffer({resolveWithObject:true});if(info.width!==256||info.height!==256||info.channels!==4)throw Error('base format');
 fs.mkdirSync(root+'/rigged/cursor_react',{recursive:true});const evidence=[];
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
  if(!changed||fixedChanges||!alphaChanges)throw Error('invalid impact rig');
  const file='cursor_react_'+String(frame).padStart(2,'0')+'.png';await sharp(output,{raw:{width:256,height:256,channels:4}}).png().toFile(root+'/rigged/cursor_react/'+file);
  if(frame===3)await sharp(output,{raw:{width:256,height:256,channels:4}}).png().toFile(root+'/keypose.png');
  evidence.push({file,pixelSha256:crypto.createHash('sha256').update(output).digest('hex'),changedPixels:changed,fixedRegionChanges:fixedChanges,alphaChangedPixels:alphaChanges,maxInverseDisplacementPixels:maxShift});
 }
 if(new Set(evidence.map(x=>x.pixelSha256)).size!==8)throw Error('duplicate rig frames');
 fs.writeFileSync(root+'/rig-evidence.json',JSON.stringify({reference:"public/assets/creatures/moa/stage04/base.png",referenceApproval:'User authorized sequential candidate production and existing part rigging; final appearance/motion pending',parts,protectedRegions:"y>=206||y<=67||x<=40||x>=224",wholeImageTransform:false,silhouetteMotion:true,frames:evidence,repairIterations:3,repairScope:'PR #114 independent first attempt; no failure recovery',productionEligible:false},null,2)+'\n');
})();
