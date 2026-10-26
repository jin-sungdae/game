// M025 concept only. Offline part-weighted breathing rig, not a runtime animation engine.
// Concept-derived candidate base; no whole-image translation, rotation, scaling, or duplicated frames.
const sharp=require(process.env.LUMA_SHARP_MODULE || 'sharp'),fs=require('fs'),crypto=require('crypto');
const root='design/production-batches/luma-asset-08/continuation/M024/breath';
const parts=[{"name": "가슴-호흡", "x": 159, "y": 181, "rx": 18, "ry": 23, "dx": 0.18, "dy": -0.55, "phase": 0}, {"name": "복부-지연", "x": 154, "y": 198, "rx": 13, "ry": 10, "dx": -0.12, "dy": -0.28, "phase": -1.3}];
const fixed=(x,y)=>x<=136||x>=183||y<=158||y>=209;
function displacement(x,y,theta){if(fixed(x,y))return [0,0];let dx=0,dy=0;for(const p of parts){const r=((x-p.x)/p.rx)**2+((y-p.y)/p.ry)**2;if(r>=1)continue;const weight=(1-r)**3*(1-Math.cos(theta+p.phase))/2;dx+=p.dx*weight;dy+=p.dy*weight;}return[dx,dy];}
(async()=>{
 const {data,info}=await sharp('design/production-batches/monsters/batch03/M024/base-v4.png').raw().toBuffer({resolveWithObject:true});if(info.width!==256||info.height!==256||info.channels!==4)throw Error('base format');
 fs.mkdirSync(root+'/rigged/breath',{recursive:true});const evidence=[];
 for(let frame=0;frame<8;frame++){
  const theta=frame*2*Math.PI/8,output=Buffer.from(data);let changed=0,fixedChanges=0,maxShift=0;
  for(let y=0;y<256;y++)for(let x=0;x<256;x++){
   if(fixed(x,y))continue;
   let sx=x,sy=y;for(let k=0;k<4;k++){const [dx,dy]=displacement(sx,sy,theta);sx=x-dx;sy=y-dy;}
   const shift=Math.hypot(sx-x,sy-y);maxShift=Math.max(maxShift,shift);if(shift<1e-9)continue;
   const x0=Math.floor(sx),y0=Math.floor(sy),fx=sx-x0,fy=sy-y0;let alpha=0,rgb=[0,0,0];
   for(let oy=0;oy<2;oy++)for(let ox=0;ox<2;ox++){const xx=x0+ox,yy=y0+oy;if(xx<0||xx>=256||yy<0||yy>=256)continue;const w=(ox?fx:1-fx)*(oy?fy:1-fy),n=(yy*256+xx)*4,a=data[n+3]/255;alpha+=a*w;for(let c=0;c<3;c++)rgb[c]+=data[n+c]*a*w;}
   const n=(y*256+x)*4;output[n+3]=data[n+3];if(alpha>0)for(let c=0;c<3;c++)output[n+c]=Math.round(rgb[c]/alpha);
  }
  for(let y=0;y<256;y++)for(let x=0;x<256;x++){const n=(y*256+x)*4;let diff=false;for(let c=0;c<4;c++)if(data[n+c]!==output[n+c])diff=true;if(diff){changed++;if(fixed(x,y))fixedChanges++;}}
  if(!changed||fixedChanges)throw Error('invalid rig');
  const file=`breath_${String(frame).padStart(2,'0')}.png`;await sharp(output,{raw:{width:256,height:256,channels:4}}).png().toFile(root+'/rigged/breath/'+file);
  evidence.push({file,pixelSha256:crypto.createHash('sha256').update(output).digest('hex'),changedPixels:changed,fixedRegionChanges:fixedChanges,maxInverseDisplacementPixels:maxShift});
 }
 if(new Set(evidence.map(x=>x.pixelSha256)).size!==8)throw Error('duplicate rig frames');
 fs.writeFileSync(root+'/rig-evidence.json',JSON.stringify({reference:'design/production-batches/monsters/batch03/M024/base-v4.png',referenceApproval:'User authorized concept-based sequential artwork and part rigging; final artwork review pending',parts,protectedRegions:"x<=136||x>=183||y<=158||y>=209",wholeImageTransform:false,frames:evidence,repairIterations:3,productionEligible:false},null,2));
})();
