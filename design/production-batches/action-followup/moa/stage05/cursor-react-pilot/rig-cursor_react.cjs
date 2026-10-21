// Independent CURSOR_REACT candidate. Existing offline part-weighted inverse-sampling rig, not a runtime animation engine.
// Concept-derived candidate base; no whole-image translation, rotation, scaling, or duplicated frames.
const sharp=require(process.env.LUMA_SHARP_MODULE || 'sharp'),fs=require('fs'),crypto=require('crypto');
const root='design/production-batches/action-followup/moa/stage05/cursor-react-pilot';
const parts=[{"name": "mature-crown-leaf-attention", "x": 122, "y": 49, "rx": 14, "ry": 11, "dx": -0.55, "dy": 0.65, "samples": [0.02, 0.08, 0.23, 0.55, 0.92, 1, 0.51, 0.08]}, {"name": "upper-shoulder-leaf-return", "x": 130, "y": 128, "rx": 20, "ry": 11, "dx": 0.65, "dy": -0.45, "samples": [0.01, 0.03, 0.12, 0.31, 0.66, 0.96, 0.72, 0.14]}];
const fixed=(x,y)=>y>=144||y<=33||x<=102||x>=158;
function displacement(x,y,theta){if(fixed(x,y))return [0,0];let dx=0,dy=0;for(const p of parts){const r=((x-p.x)/p.rx)**2+((y-p.y)/p.ry)**2;if(r>=1)continue;const weight=(1-r)**3*p.samples[theta];dx+=p.dx*weight;dy+=p.dy*weight;}return[dx,dy];}
(async()=>{
 const {data,info}=await sharp('public/assets/creatures/moa/stage05/base.png').raw().toBuffer({resolveWithObject:true});if(info.width!==256||info.height!==256||info.channels!==4)throw Error('base format');
 fs.mkdirSync(root+'/rigged/cursor_react',{recursive:true});const evidence=[];
 for(let frame=0;frame<8;frame++){
  const theta=frame,output=Buffer.from(data);let changed=0,fixedChanges=0,maxShift=0;
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
  const file=`cursor_react_${String(frame).padStart(2,'0')}.png`;await sharp(output,{raw:{width:256,height:256,channels:4}}).png().toFile(root+'/rigged/cursor_react/'+file);
  if(frame===3)await sharp(output,{raw:{width:256,height:256,channels:4}}).png().toFile(root+"/keypose.png");
  evidence.push({file,pixelSha256:crypto.createHash('sha256').update(output).digest('hex'),changedPixels:changed,fixedRegionChanges:fixedChanges,maxInverseDisplacementPixels:maxShift});
 }
 if(new Set(evidence.map(x=>x.pixelSha256)).size!==8)throw Error('duplicate rig frames');
 fs.writeFileSync(root+'/rig-evidence.json',JSON.stringify({reference:'public/assets/creatures/moa/stage05/base.png',referenceApproval:'User authorized concept-based sequential artwork and part rigging; final artwork review pending',parts,protectedRegions:"y>=144||y<=33||x<=102||x>=158",wholeImageTransform:false,frames:evidence,repairIteration:3,repairScope:"PR #114; independent first attempt; no failure recovery",productionEligible:false},null,2));
})();
