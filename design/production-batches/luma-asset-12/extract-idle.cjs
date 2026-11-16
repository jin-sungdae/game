// Uniform cell extraction only; preserve all Alpha and source failures. No per-frame realignment.
const sharp=require(process.env.LUMA_SHARP_MODULE||'sharp'),fs=require('fs'),path=require('path');
(async()=>{const root=path.join(__dirname,'M043/idle'); const source=path.join(root,'source-sheet.png');
const meta=await sharp(source).metadata();const cells=[];
for(let i=0;i<8;i++){
 const left=Math.round(i%4*meta.width/4),top=Math.round(Math.floor(i/4)*meta.height/2);
 const width=Math.round((i%4+1)*meta.width/4)-left,height=Math.round((Math.floor(i/4)+1)*meta.height/2)-top;
 const file=`idle_${String(i).padStart(2,'0')}.png`;if(fs.existsSync(path.join(root,file)))throw Error('No replacement allowed');
 await sharp(source).extract({left,top,width,height}).resize(256,256,{fit:'contain',background:{r:0,g:0,b:0,alpha:0}}).ensureAlpha().png().toFile(path.join(root,file));
 cells.push({file,left,top,width,height});
}
fs.writeFileSync(path.join(root,'extraction.json'),JSON.stringify({tool:'built-in image_gen',sourceSize:[meta.width,meta.height],cells,normalization:'Uniform cell fit only; no Alpha cleanup, alignment repair, or pose fabrication',repairIterations:3,repairLimit:3,productionEligible:false,runtimeEnabled:false},null,2)+'\n');})();
