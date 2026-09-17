import type { CompanionState } from '../types/entity';
export const stateClips: Record<CompanionState, string> = {
  IDLE:'idle', WALKING:'walk', SITTING:'sit', LOOKING:'look',
  SLEEPING:'sleep', REACTING:'react', DRAGGING:'idle',
};
export interface Clip { frames:number; frameDuration:number; loop:boolean }
export interface Manifest {
  species:string; stage:number;
  canvas:{width:number;height:number}; anchor:{x:number;y:number};
  display:{width:number}; animations:Record<string,Clip>;
}
const positive = (n:unknown): n is number => typeof n === 'number' && Number.isFinite(n) && n > 0;
export function parseManifest(value:unknown, species:string, stage:number): Manifest {
  const m = value as Manifest | null;
  if(!m || m.species !== species || m.stage !== stage ||
    !positive(m.canvas?.width) || !positive(m.canvas?.height) ||
    !Number.isInteger(m.canvas.width) || !Number.isInteger(m.canvas.height) ||
    m.anchor?.x !== .5 || m.anchor?.y !== 1 || !positive(m.display?.width) ||
    !m.animations || typeof m.animations !== 'object') throw new Error('Invalid bottom-center manifest');
  for(const [name,c] of Object.entries(m.animations)) {
    if(!/^[a-z][a-z0-9_-]*$/.test(name) || !c || !positive(c.frames) ||
      !Number.isInteger(c.frames) || c.frames > 256 || !positive(c.frameDuration) ||
      typeof c.loop !== 'boolean') throw new Error('Invalid clip');
  }
  return m;
}
export function assetBase(species:string, stage:number) {
  if(!/^[a-z][a-z0-9_-]*$/.test(species) || !Number.isSafeInteger(stage) || stage < 1)
    throw new Error('Invalid asset identity');
  return `/assets/creatures/${species}/stage${String(stage).padStart(2,'0')}`;
}
export function frameUrls(base:string, name:string, clip:Clip): string[] {
  return Array.from({length:clip.frames}, (_,i) => `${base}/${name}/${name}_${String(i).padStart(2,'0')}.png`);
}
export function directionScale(facing:number) { return facing < 0 ? -1 : 1; }
// Fit the full canonical canvas; its bottom-center remains the world anchor.
export function spriteSize(m:Manifest, panelWidth:number, panelHeight:number) {
  const scale = Math.max(0, Math.min(m.display.width/m.canvas.width, panelWidth/m.canvas.width, panelHeight/m.canvas.height));
  return { width:m.canvas.width*scale, height:m.canvas.height*scale };
}
