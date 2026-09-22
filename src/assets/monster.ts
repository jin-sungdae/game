import { baseSize } from './base';
import { validMonsterScale, type MonsterAssetDefinition } from '../entities/monsters';
// The existing PIP gameplay wrapper already applies .8; do not apply it twice.
// Cap scale inside the same 82pt envelope that reserves existing motion headroom.
export function monsterVisualSize(code:string, visualScale:number, width:number, height:number) {
  const bounds=baseSize(Number.isFinite(width)?Math.max(0,width):0,Number.isFinite(height)?Math.max(0,height):0);
  const scale=code==='PIP' ? 1 : validMonsterScale(visualScale) ? visualScale : 1;
  const edge=Math.min(82*scale,bounds.width,bounds.height);
  return {width:edge,height:edge};
}
export interface MonsterAnimationFrame { monsterCode:string; clip:string; url:string }
// Timing/clip loading stays with the animation producer. Never display another monster's frame.
export function monsterAnimationUrl(code:string, definition:MonsterAssetDefinition|null, frame?:MonsterAnimationFrame):string|null {
  if(!definition || !frame || frame.monsterCode!==code || !definition.animationClips ||
    !Object.hasOwn(definition.animationClips,frame.clip)) return null;
  const directory=definition.animationClips[frame.clip as keyof NonNullable<MonsterAssetDefinition['animationClips']>];
  if(!directory || !directory.startsWith(`${definition.assetRoot}/`) ||
    !/^\/assets\/monsters\/[a-z][a-z0-9_]*\/[a-z][a-z0-9_-]*$/.test(directory)) return null;
  const prefix=`${directory}/`;
  return frame.url.startsWith(prefix) && /^[a-z][a-z0-9_-]*_\d{2,3}\.png$/.test(frame.url.slice(prefix.length)) ? frame.url : null;
}
