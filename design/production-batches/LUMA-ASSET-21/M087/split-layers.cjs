// Offline lossless ownership masks. No missing background is invented behind the eye.
const sharp=require(process.env.LUMA_SHARP_MODULE||'sharp'),fs=require('fs'),crypto=require('crypto');
(async()=>{
 const root='design/production-batches/LUMA-ASSET-21/M087/layers';fs.mkdirSync(root,{recursive:true});
 const source='design/production-batches/monsters/batch09/M087/base-v2.png';
 const {data,info}=await sharp(source).raw().toBuffer({resolveWithObject:true});
 if(info.width!==256||info.height!==256||info.channels!==4)throw Error('base format');
 const eye=Buffer.alloc(data.length),ring=Buffer.alloc(data.length),merged=Buffer.alloc(data.length);
 for(let y=0;y<256;y++)for(let x=0;x<256;x++){
  const n=(y*256+x)*4;const ownsEye=((x-145)/35)**2+((y-128)/37)**2<1;
  data.copy(ownsEye?eye:ring,n,n,n+4);
  for(let c=0;c<4;c++)merged[n+c]=eye[n+c]+ring[n+c];
 }
 if(!merged.equals(data))throw Error('layer roundtrip changed pixels');
 for(const [name,pixels] of [['eye',eye],['ring',ring]])await sharp(pixels,{raw:{width:256,height:256,channels:4}}).png().toFile(root+'/'+name+'.png');
 fs.writeFileSync(root+'/layer-validation.json',JSON.stringify({source,method:'Disjoint elliptical pixel ownership; exact RGBA reconstruction by union',canvas:[256,256],sourcePixelHash:crypto.createHash('sha256').update(data).digest('hex'),roundtripPixelHash:crypto.createHash('sha256').update(merged).digest('hex'),changedPixels:0,independentOcclusionReady:false,limitations:'Mask is an editable layer study; ring has no painted surface behind the eye. Do not translate eye or rotate ring to expose unpainted pixels. Human anatomical mask review required.',productionEligible:false,runtimeEnabled:false},null,2)+'\n');
})();
