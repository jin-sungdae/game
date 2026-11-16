// M004 concept only. Offline part-weighted breathing rig, not a runtime animation engine.
// Concept-derived candidate base; no whole-image translation, rotation, scaling, or duplicated frames.
const sharp=require(process.env.LUMA_SHARP_MODULE || 'sharp'),fs=require('fs'),crypto=require('crypto');
const root='design/production-batches/luma-asset-04/M004/rest-pilot';
const eyes=[{"x": 175, "y": 102, "rx": 5, "ry": 5}, {"x": 192.5, "y": 108, "rx": 2.7, "ry": 3.3}],closure=[.48,.52,.58,.63,.60,.55,.50,.46];
const parts=[{"name": "trunk-flex", "x": 145, "y": 148, "rx": 23, "ry": 29, "dx": 0.15, "dy": -0.35, "phase": 0}, {"name": "leaf-shoulder-root", "x": 111, "y": 117, "rx": 18, "ry": 16, "dx": -0.25, "dy": -0.5, "phase": -1.0471975511965976}];
const fixed=(x,y)=>y>=182||y<=100||x<=80||x>=188||(x>=151&&y<=123);
function displacement(x,y,theta){if(fixed(x,y))return [0,0];let dx=0,dy=0;for(const p of parts){const r=((x-p.x)/p.rx)**2+((y-p.y)/p.ry)**2;if(r>=1)continue;const weight=(1-r)**3*(1-Math.cos(theta+p.phase))/2;dx+=p.dx*weight;dy+=p.dy*weight;}return[dx*1.1,dy*1.1];}
(async()=>{
 const {data,info}=await sharp('design/production-batches/monsters/batch01/M004/base-v2.png').raw().toBuffer({resolveWithObject:true});if(info.width!==256||info.height!==256||info.channels!==4)throw Error('base format');
 fs.mkdirSync(root+'/rigged/rest',{recursive:true});const evidence=[];
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
  const file=`rest_${String(frame).padStart(2,'0')}.png`;await sharp(output,{raw:{width:256,height:256,channels:4}}).png().toFile(root+'/rigged/rest/'+file);
  if(frame===3)await sharp(output,{raw:{width:256,height:256,channels:4}}).png().toFile(root+'/keypose.png');
  evidence.push({file,pixelSha256:crypto.createHash('sha256').update(output).digest('hex'),changedPixels:changed,fixedRegionChanges:fixedChanges,maxInverseDisplacementPixels:maxShift});
 }
 if(new Set(evidence.map(x=>x.pixelSha256)).size!==8)throw Error('duplicate rig frames');
 fs.writeFileSync(root+'/rig-evidence.json',JSON.stringify({reference:'base-v2.png',referenceApproval:'User authorized concept-based sequential artwork and part rigging; final artwork review pending',parts,eyes,closure,protectedRegions:"y>=182||y<=100||x<=80||x>=188||(x>=151&&y<=123)",wholeImageTransform:false,frames:evidence,repairIteration:3,productionEligible:false},null,2));
})();
