// Offline candidate renderer; reuses M002 eye compression and M041 HIT inverse sampling.
// No shared manifest, registry, ledger, runtime, BASE or previous failure is writable here.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const sharp = require(process.env.LUMA_SHARP_MODULE || 'sharp');
const root = __dirname;
const repository = path.resolve(root, '../../..');
const configs = JSON.parse(fs.readFileSync(path.join(root, 'rig-config.json')));
const hash = data => crypto.createHash('sha256').update(data).digest('hex');
const impact=[0,.65,1,.81,.59,.38,.21,.09,.025,0];
const envelope = [0, .10, .35, .72, 1, .91, .70, .43, .20, .07, .015, 0];
const blink = [0, .16, .6, 1, .88, .37, .08, 0];
function eyeFrame(data, eyes, amount) {
  const output = Buffer.from(data);
  for (const e of eyes) for (let y=Math.ceil(e.y-e.ry); y<=Math.floor(e.y+e.ry); y++) {
    for (let x=Math.ceil(e.x-e.rx); x<=Math.floor(e.x+e.rx); x++) {
      const nx=(x-e.x)/e.rx, ny=(y-e.y)/e.ry;
      if (nx*nx+ny*ny>=1 || amount===0) continue;
      const n=(y*256+x)*4, sy=e.y+(y-e.y)/(1-.94*amount);
      const y0=Math.max(0,Math.min(255,Math.floor(sy))), y1=Math.min(255,y0+1), t=sy-Math.floor(sy);
      const top=(Math.floor(e.y-e.ry)*256+x)*4, bottom=(Math.ceil(e.y+e.ry)*256+x)*4;
      const edge=Math.min(1,Math.max(0,(1-nx*nx-ny*ny)*5));
      for (let c=0;c<3;c++) {
        const skin=data[top+c]*(1-(ny+1)/2)+data[bottom+c]*(ny+1)/2;
        const value=Math.abs(sy-e.y)<e.ry ? data[(y0*256+x)*4+c]*(1-t)+data[(y1*256+x)*4+c]*t : skin;
        output[n+c]=Math.round(data[n+c]*(1-edge)+value*edge);
      }
    }
  }
  return output;
}
function partFrame(data, parts, amounts) {
  const output=Buffer.from(data);
  function displacement(x,y) {
    let dx=0,dy=0;
    parts.forEach((p,i)=>{
      const r=((x-p.x)/p.rx)**2+((y-p.y)/p.ry)**2;
      if(r>=1)return;
      const weight=(1-r)**3*amounts[i];dx+=p.dx*weight;dy+=p.dy*weight;
    });
    return [dx,dy];
  }
  for(let y=0;y<256;y++) for(let x=0;x<256;x++) {
    if(!parts.some(p=>((x-p.x)/p.rx)**2+((y-p.y)/p.ry)**2<1))continue;
    let sx=x,sy=y;
    for(let k=0;k<4;k++){const [dx,dy]=displacement(sx,sy);sx=x-dx;sy=y-dy;}
    if(Math.hypot(sx-x,sy-y)<1e-9)continue;
    const x0=Math.floor(sx),y0=Math.floor(sy),fx=sx-x0,fy=sy-y0;
    let alpha=0,rgb=[0,0,0];
    for(let oy=0;oy<2;oy++)for(let ox=0;ox<2;ox++){
      const xx=x0+ox,yy=y0+oy;if(xx<0||xx>=256||yy<0||yy>=256)continue;
      const w=(ox?fx:1-fx)*(oy?fy:1-fy),n=(yy*256+xx)*4,a=data[n+3]/255;
      alpha+=a*w;for(let c=0;c<3;c++)rgb[c]+=data[n+c]*a*w;
    }
    const n=(y*256+x)*4;output[n+3]=Math.round(alpha*255);
    for(let c=0;c<3;c++)output[n+c]=alpha>0?Math.round(rgb[c]/alpha):0;
  }
  return output;
}
(async()=>{
 for(const [code,config] of Object.entries(configs)) {
  const source=path.join(repository,config.source);
  const {data,info}=await sharp(source).raw().toBuffer({resolveWithObject:true});
  if(info.width!==256||info.height!==256||info.channels!==4)throw Error('Invalid BASE '+code);
  const hitOnly=process.argv.includes('--hit');
  if(hitOnly && !['M042','M044'].includes(code))continue;
  const actions=hitOnly?['HIT']:['BLINK'];
  if(!hitOnly && config.breathRig)actions.unshift('BREATH');
  if(!hitOnly && config.gesture.length)actions.push('CURSOR_REACT','INTERACT');
  for(const action of actions) {
   const dir=path.join(root,code,action.toLowerCase());
   // A rerun must never silently repair or replace a candidate.
   if(fs.existsSync(dir))throw Error('Candidate already exists; repair gate required: '+dir);
   fs.mkdirSync(dir,{recursive:true});
   const breath=action==='BREATH',eyes=action==='BLINK'||action==='INTERACT';
   const parts=breath?JSON.parse(fs.readFileSync(path.join(repository,config.breathRig))).parts:
     action==='HIT'?config.hit:action==='CURSOR_REACT'?config.gesture:action==='INTERACT'?config.acknowledge:[];
   const count=action==='BLINK'?8:16;
   const frames=[];
   for(let i=0;i<count;i++) {
    const amounts=parts.map(p=>breath?(1-Math.cos(i*2*Math.PI/count+(p.phase||0)))/2*1.45:
      (action==='HIT'?impact:envelope)[i-(p.delay||0)]||0);
    let output=partFrame(data,parts,amounts);
    const closure=action==='BLINK'?blink[i]:action==='INTERACT'?(blink[i-3]||0)*.85:0;
    if(eyes)output=eyeFrame(output,config.eyes,closure);
    const name=`${action.toLowerCase()}_${String(i).padStart(2,'0')}.png`;
    await sharp(output,{raw:{width:256,height:256,channels:4}}).png().toFile(path.join(dir,name));
    frames.push({file:name,pixelSha256:hash(output),partAmounts:amounts,eyeClosure:closure});
   }
   const clip={sessionId:'LUMA-ASSET-12',conceptId:code,species:null,status:'CANDIDATE_ONLY',
    sourceBase:config.source,sourcePixelSha256:hash(data),reuse:breath?config.breathRig:
      eyes?'design/production-batches/action-followup/M002/rig-blink.cjs':'design/production-batches/action-followup/M041/hit-pilot/rig-hit.cjs',
    canvas:{width:256,height:256},anchor:{x:.5,y:1},sourceFacing:'RIGHT',
    clip:{name:action,frames:count,frameDuration:action==='BLINK'?90:config.timing,loop:breath},
    parts,eyes:eyes?config.eyes:[],wholeImageTransform:false,frames,
    repairIterations:3,repairLimit:3,attempt:'INDEPENDENT_FIRST_ATTEMPT_NO_REPAIR',
    productionEligible:false,runtimeEnabled:false,artworkReview:'HUMAN_REVIEW_REQUIRED',
    naturalMotion:'MANUAL_REQUIRED',gui:'NOT_VERIFIED',
    scope:action==='HIT'?'Local shoulder recoil and delayed flank/tail response; planted feet and face fixed. No combat/runtime connection':action==='CURSOR_REACT'?'Stationary attention gesture only; cursor tracking/approach not implemented':
      action==='INTERACT'?'Stationary acknowledgement with delayed blink and local body gesture; no gameplay effect':
      breath?'Local ribcage/shoulder cycle; original face, limbs and silhouette landmarks protected':'Local eyelid closure; rigid plates and all non-eye pixels fixed'};
   fs.writeFileSync(path.join(dir,'candidate-clip.json'),JSON.stringify(clip,null,2)+'\n');
   console.log(code,action,count);
  }
 }
})().catch(error=>{console.error(error);process.exitCode=1;});
