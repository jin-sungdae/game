import { companionBase } from '../assets/base';
import { resolveCompanion } from '../entities/registry';
import { resolveMonster } from '../entities/monsters';
import { AssetLoader, type LoadedClip } from './loader';
export type AnimationState = 'IDLE'|'MOVE'|'REACT';
// SLEEP/BATTLE/HAPPY are reserved, not connected to gameplay in v1.
export interface Pilot { character:'MOA'|'PIP'; species:string; stage:number; manifest:string; base:string; status:'NOT_SUPPLIED'|'SUPPLIED'; sourceFacing:'RIGHT' }
export function pilotDefinition(character:string,stage=1):Pilot|null {
  if(character==='moa' && stage===1) return {character:'MOA',species:'moa',stage:1,manifest:resolveCompanion('moa',1)!.assetManifest,base:companionBase('moa',1)!,status:'NOT_SUPPLIED',sourceFacing:'RIGHT'};
  if(character==='PIP') return {character:'PIP',species:'pip',stage:1,manifest:resolveMonster('PIP')!.assetRoot+'/manifest.json',base:resolveMonster('PIP')!.baseAsset!,status:'NOT_SUPPLIED',sourceFacing:'RIGHT'};
  return null;
}
export const pilotFrames = {IDLE:6,MOVE:8,REACT:6} as const;
export const pilotClips = {IDLE:'idle',MOVE:'walk',REACT:'react'} as const;
export const pilotContract = {canvas:256,anchor:{x:.5,y:1},maxFrames:32,minFrameDuration:40,maxFrameDuration:1000,reactDuration:480,minimumRate:.5,maximumRate:2} as const;
export class PilotAssets {
  constructor(private loader=new AssetLoader()) {}
  async load(p:Pilot,state:AnimationState):Promise<LoadedClip|null> {
    if(p.status==='NOT_SUPPLIED') return null;
    const asset=await this.loader.loadRegistered(p.species,p.stage,p.manifest,pilotClips[state]);
    if(!asset || asset.manifest.canvas.width!==256 || asset.manifest.canvas.height!==256 || asset.clip.frames!==pilotFrames[state] || asset.clip.frameDuration<40 || asset.clip.frameDuration>1000 || asset.clip.loop!==(state!=='REACT') || (state==='REACT' && asset.clip.frames*asset.clip.frameDuration!==480)) return null;
    return asset;
  }
}
export interface AnimationInput { speed:number;state:string;suppressed:boolean }
export class AnimationStateResolver {
  private speed=0;
  private moving=false;
  private reacting=false;
  private reactUntil=0;
  private blocked=false;
  observe(input:AnimationInput,time:number) {
    const reacting=input.state==='REACTING'||input.state==='ENGAGED';
    if(reacting && !this.reacting && !input.suppressed) this.reactUntil=time+480;
    this.reacting=reacting;
    this.blocked=input.suppressed||input.state==='DRAGGING'||input.state==='SLEEPING';
    this.speed=Number.isFinite(input.speed)?Math.max(0,input.speed):0;
    if(this.blocked) {this.reactUntil=0;this.moving=false;return;}
    this.moving=this.speed>=(this.moving?3:8);
  }
  sample(time:number) {
    const state:AnimationState=!this.blocked && time<this.reactUntil?'REACT':this.moving?'MOVE':'IDLE';
    return {state,suppressed:this.blocked,rate:state==='MOVE'?Math.max(.5,Math.min(2,this.speed/40)):1};
  }
}
// Owns clip phase only, never world coordinates. Rate integrates without phase jumps.
export class CharacterAnimator {
  private identity='';private elapsed=0;private last:number|null=null;
  sample(identity:string,asset:LoadedClip|null,time:number,rate:number,reduced:boolean) {
    if(identity!==this.identity) {this.identity=identity;this.elapsed=0;this.last=time;}
    this.elapsed+=Math.max(0,Math.min(100,time-(this.last??time)))*Math.max(.5,Math.min(2,rate));this.last=time;
    if(!asset || reduced) return 0;
    const n=Math.floor(this.elapsed/asset.clip.frameDuration);
    return asset.clip.loop?n%asset.clip.frames:Math.min(n,asset.clip.frames-1);
  }
}
