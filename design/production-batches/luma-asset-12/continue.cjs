// Independent missing actions only. Existing frames and failures are read-only.
const fs=require('node:fs'), path=require('node:path'), crypto=require('node:crypto');
const sharp=require(process.env.LUMA_SHARP_MODULE||'sharp');
const {partFrame,eyeFrame}=require('./produce.cjs');
const root=__dirname, repo=path.resolve(root,'../../..');
const config=JSON.parse(fs.readFileSync(path.join(root,'rig-config.json')));
const gaze=[0,.12,.35,.65,.9,1,.72,.3,0,-.25,-.6,-.85,-.7,-.35,-.1,0];
const celebration=[0,.08,.25,.58,.88,1,.78,.42,.18,.32,.68,.82,.6,.28,.07,0];
const settle=[0,.12,.35,.65,.85,1,.87,.64,.4,.2,.05,-.08,-.12,-.06,-.015,0];
function eyeGaze(data, eyes, sample) {
 const out=Buffer.from(data);
 for(const e of eyes) for(let y=Math.ceil(e.y-e.ry);y<=Math.floor(e.y+e.ry);y++)
  for(let x=Math.ceil(e.x-e.rx);x<=Math.floor(e.x+e.rx);x++){
   const r=((x-e.x)/e.rx)**2+((y-e.y)/e.ry)**2;if(r>=1)continue;
   const sx=x-e.dx*sample*(1-r)**2,x0=Math.floor(sx),t=sx-x0,n=(y*256+x)*4;
   for(let c=0;c<3;c++)out[n+c]=Math.round(data[(y*256+x0)*4+c]*(1-t)+data[(y*256+x0+1)*4+c]*t);
  }
 return out;
}
const p=(name,x,y,rx,ry,dx,dy,delay=0)=>({name,x,y,rx,ry,dx,dy,delay});
const victories={
 M044:[p('dragon-neck-plume-extension',192,123,15,20,.5,-1.3),p('dragon-tail-plume-flourish',54,168,19,17,-1.2,-.7,2)],
 M041:[p('stag-neck-proud-extension',172,132,14,21,.5,-1.5),p('stag-tail-celebration',65,162,17,17,1.4,-1.2,1)],
 M042:[p('fox-near-ear-prick',123,82,17,22,-.8,-1.5),p('fox-far-ear-prick',185,88,11,16,.6,-1,1),p('fox-tail-double-flick',77,144,17,22,1.8,-1,2)],
 M045:[p('cat-chest-proud-rise',145,155,17,17,.4,-1.5),p('cat-ear-prick',117,68,17,23,-.5,-1.2,1),p('cat-tail-flourish',88,170,16,20,-1.6,-.8,2)]
};
(async()=>{
 for(const code of ['M041','M042','M044','M045']) {
  const c=config[code], source=path.join(repo,c.source);
  const {data,info}=await sharp(source).raw().toBuffer({resolveWithObject:true});
  if(info.width!==256||info.height!==256||info.channels!==4)throw Error('BASE format');
  const actions=code==='M044'?['VICTORY','RECOVERY']:code==='M041'?['LOOK','VICTORY','RECOVERY','SLEEP']:['LOOK','VICTORY','RECOVERY'];
  for(const action of actions){
   if(process.argv.includes('--remaining') && !((code==='M044'&&action==='VICTORY')||(code==='M041'&&action==='SLEEP')))continue;
   const dir=path.join(root,code,action.toLowerCase());
   if(fs.existsSync(dir))throw Error('Candidate exists; no replacement: '+dir);
   const eyes=action==='SLEEP'?c.eyes:action==='LOOK'?c.eyes.map(e=>({...e,dx:code==='M041'?.85:e.rx>8?1.25:.65})):[];
   const parts=action==='VICTORY'?victories[code]:(action==='RECOVERY'||action==='SLEEP')?
    JSON.parse(fs.readFileSync(path.join(repo,c.breathRig))).parts.map((p,i)=>({...p,name:code+'-settling-'+p.name,dx:p.dx*1.6,dy:p.dy*1.6,delay:i})):[];
   fs.mkdirSync(dir,{recursive:true});const frames=[];const count=action==='SLEEP'?24:16;
   for(let i=0;i<count;i++){
    const amounts=parts.map(p=>{
     // Phase lag is tapered to zero at both endpoints; never reverse existing HIT frames.
     const index=Math.max(0,i-(p.delay||0));
     return action==='SLEEP' ? Math.sin(Math.PI*i/(count-1))**2*(.45+.2*Math.cos(i*Math.PI/6+(p.phase||0))) : (action==='VICTORY'?celebration:settle)[index]*(i===15?0:1);
    });
    let out=partFrame(data,parts,amounts);
    if(action==='LOOK')out=eyeGaze(out,eyes,gaze[i]);
    const closure=action==='SLEEP'?Math.min(1,i/4,(count-1-i)/4):0;
    if(action==='SLEEP')out=eyeFrame(out,eyes,closure);
    const file=`${action.toLowerCase()}_${String(i).padStart(2,'0')}.png`;
    await sharp(out,{raw:{width:256,height:256,channels:4}}).png().toFile(path.join(dir,file));
    frames.push({file,pixelSha256:crypto.createHash('sha256').update(out).digest('hex'),partAmounts:amounts,eyeClosure:closure,gaze:action==='LOOK'?gaze[i]:0});
   }
   const clip={sessionId:'LUMA-ASSET-12',conceptId:code,species:null,status:'CANDIDATE_ONLY',sourceBase:c.source,
    sourcePixelSha256:crypto.createHash('sha256').update(data).digest('hex'),canvas:{width:256,height:256},anchor:{x:.5,y:1},sourceFacing:'RIGHT',
    clip:{name:action,frames:count,frameDuration:action==='SLEEP'?400:action==='LOOK'?130:c.timing,loop:false},parts,eyes,frames,wholeImageTransform:false,
    reuse:action==='LOOK'?'design/production-batches/action-followup/M010/rig-look.cjs':c.breathRig,
    scope:action==='SLEEP'?'Standing stag doze: sustained eye closure with local chest breathing and reopen to BASE; no recumbent sleep or runtime activation':action==='LOOK'?'Stationary eye inspection, not a head turn or locomotion. Original face outline and Alpha fixed.':
      action==='VICTORY'?'Stationary species-specific double gesture. No jump, battle event or rewards.':
      'Stationary composure cycle: chest expansion, damped recoil, BASE return. Not stand-up, landing or reversed HIT. Entry requires BASE; combat transition unapproved.',
    entryContract:'BASE_ONLY',exitContract:'EXACT_BASE',repairIterations:3,repairLimit:3,attempt:'INDEPENDENT_FIRST_ATTEMPT_NO_REPAIR',
    productionEligible:false,runtimeEnabled:false,artworkReview:'HUMAN_REVIEW_REQUIRED',naturalMotion:'MANUAL_REQUIRED',gui:'DEFERRED_GUI'};
   fs.writeFileSync(path.join(dir,'candidate-clip.json'),JSON.stringify(clip,null,2)+'\n');console.log(code,action,count);
  }
 }
})().catch(e=>{console.error(e);process.exitCode=1;});
