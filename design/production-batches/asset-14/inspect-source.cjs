// Read-only raw candidate inspection. No pixel cleanup, resampling, frame export or retry.
const fs = require('fs'), path = require('path'), crypto = require('crypto');
const sharp = require(process.env.LUMA_SHARP_MODULE || 'sharp');
(async()=>{
 for(const id of ['M051','M052']) {
  const root=path.join(__dirname,id), source=path.join(root,'source-idle.png');
  const {data,info}=await sharp(source).raw().toBuffer({resolveWithObject:true});
  const frames=[];
  for(let i=0;i<8;i++) {
   const x0=Math.round(i%4*info.width/4),x1=Math.round((i%4+1)*info.width/4);
   const y0=Math.round(Math.floor(i/4)*info.height/2),y1=Math.round((Math.floor(i/4)+1)*info.height/2);
   const w=x1-x0,h=y1-y0,pixels=Buffer.alloc(w*h*4);
   for(let y=0;y<h;y++)data.copy(pixels,y*w*4,((y+y0)*info.width+x0)*4,((y+y0)*info.width+x1)*4);
   const seen=new Uint8Array(w*h), components=[];let minX=w,minY=h,maxX=-1,maxY=-1;
   for(let p=0;p<w*h;p++)if(pixels[p*4+3]) {
    const x=p%w,y=Math.floor(p/w);minX=Math.min(minX,x);maxX=Math.max(maxX,x);minY=Math.min(minY,y);maxY=Math.max(maxY,y);
    if(seen[p])continue;
    const queue=[p];seen[p]=1;
    for(let q=0;q<queue.length;q++) {
     const n=queue[q],xx=n%w,yy=Math.floor(n/w);
     for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++) {
      const nx=xx+dx,ny=yy+dy;if(nx<0||nx>=w||ny<0||ny>=h)continue;
      const k=ny*w+nx;if(!seen[k]&&pixels[k*4+3]){seen[k]=1;queue.push(k);}
     }
    }
    components.push(queue.length);
   }
   components.sort((a,b)=>b-a);
   frames.push({index:i,rawCellSize:[w,h],bounds:[minX,minY,maxX,maxY],
    pixelSha256:crypto.createHash('sha256').update(pixels).digest('hex'),
    detachedAlphaPixels:components.slice(1).reduce((a,b)=>a+b,0),componentCount:components.length});
  }
  const errors=[];
  if(info.channels!==4)errors.push('RGBA_REQUIRED');
  if(info.width!==1024||info.height!==512)errors.push('REQUESTED_256_CELL_GRID_NOT_DELIVERED');
  if(frames.some(f=>f.detachedAlphaPixels))errors.push('DETACHED_RAW_ALPHA');
  if(frames.some(f=>JSON.stringify(f.bounds)!==JSON.stringify(frames[0].bounds)))errors.push('BOUNDS_AND_ANCHOR_VARY');
  const result={status:errors.length?'VALIDATION_FAILED':'RAW_CHECKS_PASS',sourceSize:[info.width,info.height],channels:info.channels,
   sourceSha256:crypto.createHash('sha256').update(fs.readFileSync(source)).digest('hex'),errors,frames,
   completedClips:0,exported256Frames:0,repairIterations:3,repairLimit:3,repairsPerformed:0,
   appearanceDrift:'MANUAL_REQUIRED: markings and proportions vary across raw poses',
   frameContinuity:'NOT_ACCEPTED: fixed head/body/foot registration not preserved; no playback validation',
   productionEligible:false,runtimeConnected:false};
  fs.writeFileSync(path.join(root,'source-validation.json'),JSON.stringify(result,null,2)+'\n');
  console.log(id,JSON.stringify({errors,detachedAlphaPixels:frames.map(f=>f.detachedAlphaPixels)}));
 }
})().catch(e=>{console.error(e);process.exitCode=1;});
