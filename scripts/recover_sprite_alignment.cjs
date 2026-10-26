// Candidate-only integer translation. Never modifies the production validator or source PNGs.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
function translate(data, width, height, dx, dy) {
  if (!Number.isInteger(dx) || !Number.isInteger(dy)) throw Error('integer translation required');
  const out = Buffer.alloc(data.length);
  for (let y=0;y<height;y++) for(let x=0;x<width;x++) {
    const i=(y*width+x)*4, xx=x+dx, yy=y+dy;
    if(xx<0 || xx>=width || yy<0 || yy>=height) {
      if(data[i+3]) throw Error('translation would clip visible pixels');
    } else data.copy(out,(yy*width+xx)*4,i,i+4);
  }
  return out;
}
function bounds(points) {
  return points.length ? [Math.min(...points.map(p=>p[0])),Math.min(...points.map(p=>p[1])),
    Math.max(...points.map(p=>p[0])),Math.max(...points.map(p=>p[1]))] : null;
}
function measure(data) {
  const alpha={}, feet=[[],[]], edge=[];
  for(const threshold of [1,16,128,240]) {
    const points=[];
    for(let y=0;y<256;y++) for(let x=0;x<256;x++) if(data[(y*256+x)*4+3]>=threshold) points.push([x,y]);
    alpha[threshold]=bounds(points);
  }
  for(let y=0;y<256;y++) for(let x=0;x<256;x++) {
    const i=(y*256+x)*4, [r,g,b,a]=data.subarray(i,i+4);
    if(a && (x===0||y===0||x===255||y===255)) edge.push({x,y,alpha:a});
    // RUU-specific gold-toe measurement, NOT an anatomical or identity validator.
    if(y>=230 && a>=200 && r>=140 && g>=65 && g<=225 && b<130 && r-b>65) feet[x<160?0:1].push([x,y]);
  }
  const contacts=feet.map(points=>{
    if(!points.length) throw Error('toe landmark unavailable');
    const box=bounds(points), bottom=points.filter(p=>p[1]>=box[3]-1);
    return {bounds:box,pixels:points.length,point:[bottom.reduce((s,p)=>s+p[0],0)/bottom.length,box[3]]};
  });
  return {alphaBounds:alpha,edgePixels:edge,contacts,
    contactAnchor:[(contacts[0].point[0]+contacts[1].point[0])/2,Math.max(...contacts.map(f=>f.point[1]))]};
}
function visibleHash(data) {
  const pixels=[];
  for(let i=0;i<data.length;i+=4) if(data[i+3]) pixels.push(data.subarray(i,i+4).toString('hex'));
  return crypto.createHash('sha256').update(pixels.sort().join('')).digest('hex');
}
async function run(root, output) {
  const allowed=path.resolve(__dirname,'../design/production-candidates-v1');
  root=path.resolve(root);output=path.resolve(output);
  if(!root.startsWith(allowed+path.sep)||!output.startsWith(allowed+path.sep)) throw Error('candidate directory required');
  if(fs.existsSync(output)) throw Error('output already exists; preserve prior evidence');
  const sharp=require(process.env.LUMA_SHARP_MODULE||'sharp');
  async function read(file) {
    const {data,info}=await sharp(file).ensureAlpha().raw().toBuffer({resolveWithObject:true});
    if(info.width!==256||info.height!==256||info.channels!==4) throw Error('256x256 RGBA required');
    return data;
  }
  const base=measure(await read(path.join(root,'base.png')));
  const report={status:'VALIDATION_PENDING',productionEligible:false,gui:'DEFERRED_GUI',
    method:'Gold toe contact proxy, manually inspect against anatomical feet. Integer translation only; no resampling or alpha cleanup.',
    landmarkApproval:'MANUAL_REQUIRED',base,frames:[]};
  fs.mkdirSync(output,{recursive:true});
  for(const [revision,source] of [['v1',''],['v2','revision2']]) {
    const dir=path.join(output,revision);fs.mkdirSync(path.join(dir,'idle'),{recursive:true});
    const manifest=JSON.parse(fs.readFileSync(path.join(root,source,'manifest.json')));
    manifest.sourceImage=path.relative(dir,path.join(root,source,'source-idle.png'));
    manifest.validationStatus='VALIDATION_PENDING';
    fs.writeFileSync(path.join(dir,'manifest.json'),JSON.stringify(manifest,null,2)+'\n');
    for(let index=0;index<8;index++) {
      const name=`idle_${String(index).padStart(2,'0')}.png`;
      const file=path.join(root,source,'idle',name),data=await read(file),before=measure(data);
      const dx=Math.round(base.contactAnchor[0]-before.contactAnchor[0]);
      const dy=Math.round(base.contactAnchor[1]-before.contactAnchor[1]);
      const shifted=translate(data,256,256,dx,dy),after=measure(shifted);
      if(visibleHash(data)!==visibleHash(shifted)) throw Error('visible RGBA changed');
      await sharp(shifted,{raw:{width:256,height:256,channels:4}}).png().toFile(path.join(dir,'idle',name));
      report.frames.push({revision,index,source:path.relative(allowed,file),translation:[dx,dy],
        before,after,remainingContactOffset:after.contactAnchor.map((v,i)=>v-base.contactAnchor[i]),
        sourceSha256:crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'),
        visibleRgbaPreserved:true,visualIdentity:'MANUAL_REQUIRED',continuity:'MANUAL_REQUIRED'});
    }
  }
  fs.writeFileSync(path.join(output,'measurements.json'),JSON.stringify(report,null,2)+'\n');
}
module.exports={translate,measure,visibleHash};
if(require.main===module) run(process.argv[2]||'',process.argv[3]||'').catch(e=>{console.error(e.message);process.exitCode=1;});
