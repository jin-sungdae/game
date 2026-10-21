// Read-only keypose alpha diagnostic. Same alpha>0 and eight-connected foreground rule as existing candidate tests.
// Alternate thresholds/kernels are sensitivity probes, never approval criteria or output images.
// LUMA_SHARP_MODULE uses the same optional local Sharp runtime as existing offline rigs.
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

(async()=>{const result={};const cases=process.argv.slice(2).length?process.argv.slice(2):["design/production-batches/action-followup/M012/move-pilot","design/production-batches/action-followup/moa/stage05/rest-pilot","design/production-batches/action-followup/M016/attack-pilot","design/production-batches/monsters/move-pilot/M005","design/production-batches/monsters/turn-pilot/M005","design/production-batches/monsters/rest-pilot/M005"];
for(const root of cases){const row={};let prepared;
for(const file of ['keypose-tool-reference.png','keypose.png']){
const {data,info}=await sharp(root+'/'+file).ensureAlpha().raw().toBuffer({resolveWithObject:true});
if(file==='keypose.png')prepared=data;
row[file]={sha256:crypto.createHash('sha256').update(fs.readFileSync(root+'/'+file)).digest('hex'),probes:[0,1,2,8].map(t=>measure(data,info.width,info.height,t))};}
row.kernels={};
for(const kernel of ['nearest','linear','cubic','lanczos2','lanczos3']){
const data=await sharp(root+'/keypose-tool-reference.png').resize(256,256,{fit:'contain',background:{r:0,g:0,b:0,alpha:0},kernel}).ensureAlpha().raw().toBuffer();
const m=measure(data,256,256);
row.kernels[kernel]={detachedPixels:m.detachedPixels,detachedComponents:m.detachedComponents,detachedAlphaHistogram:m.detachedAlphaHistogram,preparedPixelsIdentical:data.equals(prepared)};}
result[root]=row;}
console.log(JSON.stringify(result,null,2));})().catch(e=>{console.error(e);process.exitCode=1;});
