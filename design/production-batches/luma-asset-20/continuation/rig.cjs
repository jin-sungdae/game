// Session-local continuation of the existing part-weighted inverse RGBA sampler.
// Explicit eye masks use BASE palette; no whole-image translation or scaling.
const sharp=require(process.env.LUMA_SHARP_MODULE||'sharp');
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const folder=process.argv[2],spec=JSON.parse(fs.readFileSync(path.join(folder,'candidate-clip.json')));
const digest=data=>crypto.createHash('sha256').update(data).digest('hex');
function displacement(x,y,frame){let dx=0,dy=0;for(const p of spec.parts){const r=((x-p.x)/p.rx)**2+((y-p.y)/p.ry)**2;if(r<1){const w=(1-r)**3*p.samples[frame];dx+=p.dx*w;dy+=p.dy*w;}}return[dx,dy];}
function sample(data,x,y){const x0=Math.floor(x),y0=Math.floor(y),fx=x-x0,fy=y-y0;let a=0,rgb=[0,0,0];for(let oy=0;oy<2;oy++)for(let ox=0;ox<2;ox++){const xx=x0+ox,yy=y0+oy;if(xx<0||xx>=256||yy<0||yy>=256)continue;const n=(yy*256+xx)*4,w=(ox?fx:1-fx)*(oy?fy:1-fy),v=data[n+3]/255;a+=v*w;for(let c=0;c<3;c++)rgb[c]+=data[n+c]*v*w;}return [...rgb.map(v=>a?Math.round(v/a):0),Math.round(a*255)];}
(async()=>{
 const {data,info}=await sharp(spec.sourceBase).raw().toBuffer({resolveWithObject:true});if(info.width!==256||info.height!==256||info.channels!==4)throw Error('BASE format');
 fs.mkdirSync(spec.framesDirectory,{recursive:true});let frames=[];
 for(let f=0;f<8;f++){
  const posed=Buffer.from(data),closure=spec.eyeClosureSamples[f];
  for(const eye of spec.eyes){
   const cos=Math.cos(eye.angle),sin=Math.sin(eye.angle),n=(eye.skin[1]*256+eye.skin[0])*4;
   const skin=[data[n],data[n+1],data[n+2]];
   for(let y=0;y<256;y++)for(let x=0;x<256;x++){
    const dx=x-eye.x,dy=y-eye.y,u=dx*cos+dy*sin,v=-dx*sin+dy*cos;
    const r=(u/eye.rx)**2+(v/eye.ry)**2;if(r>=1||closure===0)continue;
    const edge=Math.min(1,(1-r)*5),cover=Math.max(0,Math.min(1,(Math.abs(v)/eye.ry-(1-closure))/.14+closure*.2));
    const seam=Math.exp(-(((v-.5*(1-(u/eye.rx)**2))/.7)**2))*closure;
    const weight=edge*Math.max(cover,seam);const i=(y*256+x)*4;
    for(let c=0;c<3;c++){const target=skin[c]*(1-.65*seam);posed[i+c]=Math.round(data[i+c]*(1-weight)+target*weight);}
   }
  }
  const output=Buffer.from(posed);
  for(let y=0;y<256;y++)for(let x=0;x<256;x++){
   let sx=x,sy=y;for(let k=0;k<4;k++){const [dx,dy]=displacement(sx,sy,f);sx=x-dx;sy=y-dy;}
   if(Math.hypot(sx-x,sy-y)<1e-9)continue;
   const rgba=sample(posed,sx,sy),n=(y*256+x)*4;for(let c=0;c<4;c++)output[n+c]=rgba[c];
  }
  const name=spec.clip.name.toLowerCase()+'_'+String(f).padStart(2,'0')+'.png';
  await sharp(output,{raw:{width:256,height:256,channels:4}}).png().toFile(path.join(spec.framesDirectory,name));
  if(f===3)await sharp(output,{raw:{width:256,height:256,channels:4}}).png().toFile(path.join(folder,'keypose.png'));
  frames.push({file:name,pixelSha256:digest(output)});
 }
 if(frames[7].pixelSha256!==digest(data))throw Error('BASE return failed');
 fs.writeFileSync(path.join(folder,'rig-evidence.json'),JSON.stringify({sourceBase:spec.sourceBase,sourceBasePixelSha256:digest(data),sourceRig:spec.sourceRig,frames,wholeImageTransform:false,exactBaseReturnFrame:7,eyelidMask:spec.eyes,parts:spec.parts,productionEligible:false},null,2)+'\n');
})();
