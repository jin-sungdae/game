import { resolveCompanion } from '../entities/registry';
import { frameUrls, parseManifest, type Manifest, type Clip } from './model';
export interface LoadedClip { manifest:Manifest; clip:Clip; urls:string[] }
export interface AssetIO { json:(url:string)=>Promise<unknown>; image:(url:string)=>Promise<{width:number;height:number}> }
export const browserIO:AssetIO = {
  json:async url => { const r=await fetch(url); if(!r.ok) throw new Error('Missing manifest'); return r.json(); },
  image:url => new Promise((resolve,reject) => {
    const img=new Image(); img.onload=()=>resolve({width:img.naturalWidth,height:img.naturalHeight});
    img.onerror=()=>reject(new Error('Missing frame')); img.src=url;
  }),
};
export class AssetLoader {
  private manifests=new Map<string,Promise<Manifest|null>>();
  private clips=new Map<string,Promise<LoadedClip|null>>();
  constructor(private io:AssetIO = browserIO) {}
  load(species:string, stage:number, name:string):Promise<LoadedClip|null> {
    const companion=resolveCompanion(species,stage);
    if(!companion) return Promise.resolve(null);
    return this.loadRegistered(species,stage,companion.assetManifest,name);
  }
  // Call only with a trusted registry path; identity still validated against the manifest.
  loadRegistered(species:string,stage:number,manifestUrl:string,name:string):Promise<LoadedClip|null> {
    const base=manifestUrl.slice(0,-'/manifest.json'.length), key=`${base}/${name}`;
    if(!this.manifests.has(base)) this.manifests.set(base,
      this.io.json(manifestUrl).then(m=>parseManifest(m,species,stage)).catch(()=>null));
    if(!this.clips.has(key)) this.clips.set(key, this.manifests.get(base)!.then(async manifest => {
      const clip=manifest?.animations[name];
      if(!manifest || !clip) return null;
      const urls=frameUrls(base,name,clip);
      try {
        const sizes=await Promise.all(urls.map(url=>this.io.image(url)));
        if(sizes.some(s=>s.width!==manifest.canvas.width || s.height!==manifest.canvas.height)) return null;
        return {manifest,clip,urls};
      } catch { return null; }
    }));
    return this.clips.get(key)!;
  }
}
