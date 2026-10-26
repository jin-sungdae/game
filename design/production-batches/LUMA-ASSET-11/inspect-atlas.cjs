// Session-local extraction and diagnostics. Reuses repository eight-connected alpha>0 policy.
// Raw failed cells are retained; never cleaned, normalized or animated.
const sharp=require(process.env.LUMA_SHARP_MODULE||'sharp'),fs=require('fs'),crypto=require('crypto');
function measure(data,w,h,threshold=0){
 let seen=new Uint8Array(w*h), comps=[];
 for(let seed=0;seed<w*h;seed++){if(seen[seed]||data[4*seed+3]<=threshold)continue;let stack=[seed],n=0,minA=255,maxA=0,hist={},bounds=[w,h,0,0];seen[seed]=1;
 while(stack.length){const p=stack.pop(),x=p%w,y=Math.floor(p/w),a=data[4*p+3];n++;minA=Math.min(minA,a);maxA=Math.max(maxA,a);hist[a]=(hist[a]||0)+1;bounds=[Math.min(bounds[0],x),Math.min(bounds[1],y),Math.max(bounds[2],x),Math.max(bounds[3],y)];
 for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){const xx=x+dx,yy=y+dy,q=yy*w+xx;if(xx<0||yy<0||xx>=w||yy>=h||seen[q]||data[4*q+3]<=threshold)continue;seen[q]=1;stack.push(q);}}
 comps.push({n,minA,maxA,hist,bounds});}
 comps.sort((a,b)=>b.n-a.n);const main=comps.shift(), hist={};for(const c of comps)for(const[a,n]of Object.entries(c.hist))hist[a]=(hist[a]||0)+n;
 return {threshold,width:w,height:h,mainPixels:main?.n||0,mainBounds:main?.bounds,detachedPixels:comps.reduce((s,c)=>s+c.n,0),detachedComponents:comps.length,detachedAlphaHistogram:hist,largestDetached:comps.slice(0,8).map(({hist,...c})=>c)};
}


(async()=>{
 const root=__dirname+'/'+process.argv[2],source=root+'/source-keyposes.png';
 const {data,info}=await sharp(source).ensureAlpha().raw().toBuffer({resolveWithObject:true});
 const actions=JSON.parse(fs.readFileSync(root+'/actions.json'));
 const rows=Math.ceil(actions.length/4);
 const results=[];
 for(let i=0;i<actions.length;i++){
  const left=Math.floor(i%4*info.width/4),top=Math.floor(Math.floor(i/4)*info.height/rows);
  const width=Math.floor((i%4+1)*info.width/4)-left,height=Math.floor((Math.floor(i/4)+1)*info.height/rows)-top;
  const folder=root+'/'+actions[i].toLowerCase();fs.mkdirSync(folder,{recursive:true});
  const cell=await sharp(data,{raw:info}).extract({left,top,width,height}).raw().toBuffer();
  await sharp(cell,{raw:{width,height,channels:4}}).png().toFile(folder+'/keypose-tool-reference.png');
  const alpha=measure(cell,width,height);
  let edges=0;for(let y=0;y<height;y++)for(let x=0;x<width;x++)if((x===0||x===width-1||y===0||y===height-1)&&cell[(y*width+x)*4+3])edges++;
  const errors=[];if(alpha.detachedPixels)errors.push('RAW_DETACHED_ALPHA');if(edges)errors.push('CELL_EDGE_CLIPPING');
  const result={action:actions[i],sourceAtlas:'source-keyposes.png',cell:{left,top,width,height},rawPixelSha256:crypto.createHash('sha256').update(cell).digest('hex'),sourceAlpha:alpha,edgePixels:edges,errors,status:errors.length?'VALIDATION_FAILED':'RAW_ALPHA_PASS',normalizationPerformed:false,riggingPerformed:false,productionEligible:false,appearanceReview:'HUMAN_REVIEW_REQUIRED',repairIterations:3,repairLimit:3};
  fs.writeFileSync(folder+'/keypose-validation.json',JSON.stringify(result,null,2)+'\n');results.push(result);
 }
 fs.writeFileSync(root+'/atlas-validation.json',JSON.stringify({sourceSha256:crypto.createHash('sha256').update(fs.readFileSync(source)).digest('hex'),width:info.width,height:info.height,results},null,2)+'\n');
 console.log(results.map(r=>({action:r.action,status:r.status,detached:r.sourceAlpha.detachedPixels,edges:r.edgePixels})));
})().catch(e=>{console.error(e);process.exitCode=1});
