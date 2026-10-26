const fs=require('fs'),path=require('path');
const sharp=require(process.env.LUMA_SHARP_MODULE || 'sharp');
// Offline candidate processing only. sharp is an externally supplied art tool, not a game dependency.
const root=path.resolve(process.argv[2] || '');
const allowed=path.resolve(__dirname,'../design/production-candidates-v1')+path.sep;
if(!root.startsWith(allowed)) throw Error('Output must be inside design/production-candidates-v1');
if(fs.existsSync(path.join(root,'idle'))) throw Error('Refusing to overwrite existing frames');
(async()=>{
 const {data,info}=await sharp(path.join(root,'source-idle.png')).ensureAlpha().raw().toBuffer({resolveWithObject:true});
 const evidence=[];fs.mkdirSync(path.join(root,'idle'),{recursive:true});
 for(let i=0;i<8;i++){
  const x0=Math.round((i%4)*info.width/4),x1=Math.round((i%4+1)*info.width/4),y0=Math.round(Math.floor(i/4)*info.height/2),y1=Math.round((Math.floor(i/4)+1)*info.height/2);
  const w=x1-x0,h=y1-y0,b=Buffer.alloc(w*h*4);
  for(let y=0;y<h;y++)data.copy(b,y*w*4,((y0+y)*info.width+x0)*4,((y0+y)*info.width+x1)*4);
  const seen=new Uint8Array(w*h),components=[];
  for(let p=0;p<w*h;p++)if(!seen[p]&&b[p*4+3]>0){
   const pixels=[p];seen[p]=1;
   for(let q=0;q<pixels.length;q++){const n=pixels[q],x=n%w,y=Math.floor(n/w);for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){const xx=x+dx,yy=y+dy;if(xx>=0&&xx<w&&yy>=0&&yy<h){const k=yy*w+xx;if(!seen[k]&&b[k*4+3]>0){seen[k]=1;pixels.push(k)}}}}
   components.push(pixels);
  }
  components.sort((a,b)=>b.length-a.length);
  // Foreground is contiguous in this generated clip. Preserve the full main component;
  // disconnected components are recorded for visual review, never silently approved.
  for(const c of components.slice(1))for(const p of c)b.fill(0,p*4,p*4+4);
  const output=path.join(root,'idle',`idle_${String(i).padStart(2,'0')}.png`);
  await sharp(b,{raw:{width:w,height:h,channels:4}}).resize(256,256,{fit:'contain',background:{r:0,g:0,b:0,alpha:0}}).png().toFile(output);
  evidence.push({frame:i,sourceBoundingBox:[x0,y0,x1,y1],sourceResolution:[info.width,info.height],foregroundPixels:components[0].length,removedComponents:components.slice(1).map(c=>c.length),normalization:'uniform fit 256x256; no pose fabrication',productionEligible:false,validationStatus:'VALIDATION_PENDING'});
 }
 fs.writeFileSync(path.join(root,'extraction.json'),JSON.stringify(evidence,null,2)+'\n');
})().catch(error=>{console.error(error.message);process.exitCode=1;});
