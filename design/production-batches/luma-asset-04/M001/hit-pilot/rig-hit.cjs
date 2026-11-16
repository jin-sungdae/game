// M001 concept only. Offline part-weighted impact-response rig, not a runtime animation engine.
// Concept-derived candidate base; no whole-image translation, rotation, scaling, or duplicated frames.
const sharp=require(process.env.LUMA_SHARP_MODULE || 'sharp'),fs=require('fs'),crypto=require('crypto');
const root='design/production-batches/luma-asset-04/M001/hit-pilot';
const eyes=[{"x": 153, "y": 132, "rx": 9, "ry": 12}, {"x": 188, "y": 131, "rx": 4.5, "ry": 10}],closure=[.01,.72,.60,.38,.19,.085,.03,.008];
const parts=[{"name": "belly-breath", "x": 147, "y": 192, "rx": 23, "ry": 15, "dx": -2.5, "dy": 1.0, "samples": [0.015, 1, 0.76, 0.43, 0.21, 0.09, 0.035, 0.008]}, {"name": "leaf-root", "x": 115, "y": 177, "rx": 20, "ry": 12, "dx": 1.2, "dy": -0.6, "samples": [0.01, 0.18, 0.8, 1, 0.62, 0.28, 0.09, 0.015]}];
const fixed=(x,y)=>y<=165||y>=207||x<=87||x>=181;
function displacement(x,y,frame){if(fixed(x,y))return [0,0];let dx=0,dy=0;for(const p of parts){const r=((x-p.x)/p.rx)**2+((y-p.y)/p.ry)**2;if(r>=1)continue;const weight=(1-r)**3*p.samples[frame];dx+=p.dx*weight;dy+=p.dy*weight;}return[dx,dy];}
(async()=>{
 const {data,info}=await sharp('design/production-batches/monsters/batch01/M001/base-v2.png').raw().toBuffer({resolveWithObject:true});if(info.width!==256||info.height!==256||info.channels!==4)throw Error('base format');
 fs.mkdirSync(root+'/rigged/hit',{recursive:true});const evidence=[];
 for(let frame=0;frame<8;frame++){
  const theta=frame*2*Math.PI/8,output=Buffer.from(data);let changed=0,fixedChanges=0,maxShift=0;
  for(let y=0;y<256;y++)for(let x=0;x<256;x++){
   if(fixed(x,y))continue;
   let sx=x,sy=y;for(let k=0;k<4;k++){const [dx,dy]=displacement(sx,sy,frame);sx=x-dx;sy=y-dy;}
   const shift=Math.hypot(sx-x,sy-y);maxShift=Math.max(maxShift,shift);if(shift<1e-9)continue;
   const x0=Math.floor(sx),y0=Math.floor(sy),fx=sx-x0,fy=sy-y0;let alpha=0,rgb=[0,0,0];
   for(let oy=0;oy<2;oy++)for(let ox=0;ox<2;ox++){const xx=x0+ox,yy=y0+oy;if(xx<0||xx>=256||yy<0||yy>=256)continue;const w=(ox?fx:1-fx)*(oy?fy:1-fy),n=(yy*256+xx)*4,a=data[n+3]/255;alpha+=a*w;for(let c=0;c<3;c++)rgb[c]+=data[n+c]*a*w;}
   const n=(y*256+x)*4;output[n+3]=data[n+3];if(alpha>0)for(let c=0;c<3;c++)output[n+c]=Math.round(rgb[c]/alpha);
  }
  const amount=closure[frame];
 for(const e of eyes)for(let y=Math.ceil(e.y-e.ry);y<=Math.floor(e.y+e.ry);y++)for(let x=Math.ceil(e.x-e.rx);x<=Math.floor(e.x+e.rx);x++){
  const nx=(x-e.x)/e.rx,ny=(y-e.y)/e.ry;if(nx*nx+ny*ny>=1||amount===0)continue;
  const n=(y*256+x)*4,scale=1-.94*amount,sy=e.y+(y-e.y)/scale;
  const y0=Math.max(0,Math.min(255,Math.floor(sy))),y1=Math.min(255,y0+1),t=sy-Math.floor(sy);
  const top=(Math.floor(e.y-e.ry)*256+x)*4,bottom=(Math.ceil(e.y+e.ry)*256+x)*4;
  const inside=Math.abs(sy-e.y)<e.ry;
  const edge=Math.min(1,Math.max(0,(1-nx*nx-ny*ny)*5));
  for(let c=0;c<3;c++){
   const skin=data[top+c]*(1-(ny+1)/2)+data[bottom+c]*(ny+1)/2;
   const value=inside?data[(y0*256+x)*4+c]*(1-t)+data[(y1*256+x)*4+c]*t:skin;
   output[n+c]=Math.round(data[n+c]*(1-edge)+value*edge);
  }
 }

  for(let y=0;y<256;y++)for(let x=0;x<256;x++){const n=(y*256+x)*4;let diff=false;for(let c=0;c<4;c++)if(data[n+c]!==output[n+c])diff=true;if(diff){changed++;if(fixed(x,y)&&!eyes.some(e=>((x-e.x)/e.rx)**2+((y-e.y)/e.ry)**2<1))fixedChanges++;}}
  if(!changed||fixedChanges)throw Error('invalid rig');
  const file=`hit_${String(frame).padStart(2,'0')}.png`;await sharp(output,{raw:{width:256,height:256,channels:4}}).png().toFile(root+'/rigged/hit/'+file);
  if(frame===1)await sharp(output,{raw:{width:256,height:256,channels:4}}).png().toFile(root+'/keypose.png');
  evidence.push({file,pixelSha256:crypto.createHash('sha256').update(output).digest('hex'),changedPixels:changed,fixedRegionChanges:fixedChanges,maxInverseDisplacementPixels:maxShift});
 }
 if(new Set(evidence.map(x=>x.pixelSha256)).size!==8)throw Error('duplicate rig frames');
 fs.writeFileSync(root+'/rig-evidence.json',JSON.stringify({reference:'base-v2.png',referenceApproval:'User authorized concept-based sequential artwork and part rigging; final artwork review pending',parts,eyes,closure,motion:'impact then delayed secondary recoil and recovery',protectedRegions:"y<=165||y>=207||x<=87||x>=181",wholeImageTransform:false,frames:evidence,repairIterations:3,repairLimit:3,repairScope:"독립 미완성 REST 최초 후보; 기존 실패 복구 없음",productionEligible:false},null,2));
})();
