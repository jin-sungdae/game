// Offline candidate only. RGBA inverse sampling reused from M057 HIT pilot.
// Run from repository root: node .../produce.cjs path/to/candidate-clip.json
const sharp=require(process.env.LUMA_SHARP_MODULE || 'sharp'),fs=require('fs'),crypto=require('crypto'),path=require('path');
const spec=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const root=path.dirname(process.argv[2]),parts=spec.parts,action=spec.clip.name.toLowerCase();
if(fs.existsSync(root+'/rigged'))throw Error('Preserve first-attempt output; automatic repair limit 3/3');
const [left,top,right,bottom]=spec.movableRect;
const fixed=(x,y)=>x<=left||x>=right||y<=top||y>=bottom;
function displacement(x,y,frame){if(fixed(x,y))return [0,0];let dx=0,dy=0;for(const p of parts){const r=((x-p.x)/p.rx)**2+((y-p.y)/p.ry)**2;if(r>=1)continue;const weight=(1-r)**3*p.samples[frame];dx+=p.dx*weight;dy+=p.dy*weight;}return[dx,dy];}
(async()=>{
 const {data,info}=await sharp(spec.sourceBase).raw().toBuffer({resolveWithObject:true});if(info.width!==256||info.height!==256||info.channels!==4)throw Error('base format');
 fs.mkdirSync(root+'/rigged/'+action,{recursive:true});const evidence=[];
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
  const file=action+'_' +String(frame).padStart(2,'0')+'.png';await sharp(output,{raw:{width:256,height:256,channels:4}}).png().toFile(root+'/rigged/'+action+'/'+file);

  evidence.push({file,pixelSha256:crypto.createHash('sha256').update(output).digest('hex'),changedPixels:changed,fixedRegionChanges:fixedChanges,alphaChangedPixels:alphaChanges,maxInverseDisplacementPixels:maxShift});
 }
 if(new Set(evidence.map(x=>x.pixelSha256)).size!==8)throw Error('duplicate rig frames');
 fs.writeFileSync(root+'/rig-evidence.json',JSON.stringify({reference:spec.sourceBase,referenceApproval:'User authorized sequential candidate production and existing part rigging; final appearance/motion pending',parts,protectedRegions:spec.movableRect,wholeImageTransform:false,silhouetteMotion:true,frames:evidence,repairIterations:3,repairLimit:3,repairScope:'LUMA-ASSET-15 independent first attempt only; no failure recovery',productionEligible:false},null,2)+'\n');
})();
