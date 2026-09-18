import { resolveCompanion } from '../entities/registry';
import { browserIO, type AssetIO } from '../animation/loader';
export function companionBase(species:string,stage:number):string|null {
  const resolved=resolveCompanion(species,stage);
  return resolved ? resolved.assetManifest.replace(/manifest\.json$/, 'base.png') : null;
}
// Fits current 96pt panels even during the existing 5pt / 1.04 attack impulse.
// PIP receives its 0.8 scale from the existing gameplay wrapper exactly once.
export const BASE_DISPLAY_WIDTH=82;
export function baseSize(width:number,height:number) {
  const edge=Math.max(0,Math.min(BASE_DISPLAY_WIDTH,width,height));
  return {width:edge,height:edge};
}
export function rendererSource(animation:string|null,base:string|null) {
  return animation ? {kind:'animation' as const,url:animation}
    : base ? {kind:'base' as const,url:base} : {kind:'css' as const,url:null};
}
export class BaseAssetLoader {
  private cache=new Map<string,Promise<string|null>>();
  constructor(private image:AssetIO['image']=browserIO.image) {}
  load(url:string|null):Promise<string|null> {
    if(!url) return Promise.resolve(null);
    if(!this.cache.has(url)) this.cache.set(url,Promise.resolve().then(()=>this.image(url))
      .then(size=>size.width===256 && size.height===256 ? url : null).catch(()=>null));
    return this.cache.get(url)!;
  }
  fail(url:string) { this.cache.set(url,Promise.resolve(null)); }
}
