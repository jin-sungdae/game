const sharp=require(process.env.LUMA_SHARP_MODULE || 'sharp'),fs=require('fs');
(async()=>{
 const root='design/production-candidates-v4/ruu/stage03',file=root+'/base-v2.png';
 const {data,info}=await sharp(file).raw().toBuffer({resolveWithObject:true});if(info.width!==256||info.height!==256||info.channels!==4)throw Error('unexpected format');
 const seen=new Uint8Array(65536),groups=[];
 for(let n=0;n<65536;n++)if(data[n*4+3]>0&&!seen[n]){let q=[n],maxAlpha=0;seen[n]=1;for(let k=0;k<q.length;k++){const p=q[k];maxAlpha=Math.max(maxAlpha,data[p*4+3]);const x=p%256,y=Math.floor(p/256);for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){const xx=x+dx,yy=y+dy,j=yy*256+xx;if(xx>=0&&xx<256&&yy>=0&&yy<256&&!seen[j]&&data[j*4+3]>0){seen[j]=1;q.push(j);}}}groups.push({pixels:q,maxAlpha});}
 groups.sort((a,b)=>b.pixels.length-a.pixels.length);
 const output=Buffer.from(data),removed=[];
 for(const g of groups.slice(1)){if(g.maxAlpha>=128)continue;for(const n of g.pixels){output[n*4+3]=0;removed.push({x:n%256,y:Math.floor(n/256),alpha:data[n*4+3]});}}
 for(const n of groups[0].pixels)for(let c=0;c<4;c++)if(output[n*4+c]!==data[n*4+c])throw Error('body altered');
 await sharp(output,{raw:{width:256,height:256,channels:4}}).png().toFile(root+'/base-v3.png');
 fs.writeFileSync(root+'/alpha-repair.json',JSON.stringify({method:'Remove only disconnected components with max alpha <128; preserve all RGB and every pixel in largest connected component',input:'base-v2.png',output:'base-v3.png',preservedBodyPixels:groups[0].pixels.length,bodyPixelChanges:0,removedPixelCount:removed.length,retainedDisconnectedComponents:groups.slice(1).filter(x=>x.maxAlpha>=128).map(x=>({size:x.pixels.length,maxAlpha:x.maxAlpha})),removedPixels:removed,repairIteration:2,productionEligible:false},null,2));
 console.log({removed:removed.length,body:groups[0].pixels.length,remaining:groups.slice(1).filter(x=>x.maxAlpha>=128).length});
})();
