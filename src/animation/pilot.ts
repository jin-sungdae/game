import { staticClips } from './static';
import { floatingClips } from './floating';
import { flyingClips, type FlightMotion } from './flying';
import { jumpPhases, type JumpSample } from './jump';
import { companionBase } from '../assets/base';
import { resolveCompanion } from '../entities/registry';
import { resolveMonster } from '../entities/monsters';
import { AssetLoader, type LoadedClip } from './loader';
export type AnimationState = 'IDLE'|'MOVE'|'REACT';
export type AnimationSequence = AnimationState|'BLINK'|'JUMP'|'HOVER'|'FLY'|'GLIDE'|'FLOAT'|'SETTLE'|'PEEK';
// SLEEP/BATTLE/HAPPY are reserved, not connected to gameplay in v1.
// Readiness describes clip assets, not gameplay triggers (PIP mouse REACT is unavailable).
export interface Pilot { character:'MOA'|'PIP'|'MELLO'|'CHIRP'|'PUFF'|'MIMI'; species:string; stage:number; manifest:string; base:string; status:'NOT_SUPPLIED'|'SUPPLIED'|'IDLE_PRODUCTION'|'JUMP_PRODUCTION'|'FLYING_PRODUCTION'|'PRODUCTION_PILOT'; sourceFacing:'RIGHT'; jumpProfile?:'JUMP'; flyingProfile?:'FLYING'; floatingProfile?:'FLOATING'; staticProfile?:'STATIC'; moveStatus?:'PRODUCTION'; reactStatus?:'PRODUCTION'|'SUPPLIED' }
export function pilotDefinition(character:string,stage=1):Pilot|null {
  if(character==='moa' && stage===1) return {character:'MOA',species:'moa',stage:1,manifest:resolveCompanion('moa',1)!.assetManifest,base:companionBase('moa',1)!,status:'IDLE_PRODUCTION',sourceFacing:'RIGHT',moveStatus:'PRODUCTION',reactStatus:'PRODUCTION'};
  if(character==='PIP') return {character:'PIP',species:'pip',stage:1,manifest:resolveMonster('PIP')!.assetRoot+'/manifest.json',base:resolveMonster('PIP')!.baseAsset!,status:'IDLE_PRODUCTION',sourceFacing:'RIGHT',moveStatus:'PRODUCTION',reactStatus:'SUPPLIED'};
  if(character==='MELLO') return {character:'MELLO',species:'mello',stage:1,manifest:resolveMonster('MELLO')!.assetRoot+'/manifest.json',base:resolveMonster('MELLO')!.baseAsset!,status:'JUMP_PRODUCTION',sourceFacing:'RIGHT',jumpProfile:'JUMP'};
  if(character==='PUFF') return {character:'PUFF',species:'puff',stage:1,manifest:resolveMonster('PUFF')!.assetRoot+'/manifest.json',base:resolveMonster('PUFF')!.baseAsset!,status:'SUPPLIED',sourceFacing:'RIGHT',floatingProfile:'FLOATING'};
  if(character==='CHIRP') return {character:'CHIRP',species:'chirp',stage:1,manifest:resolveMonster('CHIRP')!.assetRoot+'/manifest.json',base:resolveMonster('CHIRP')!.baseAsset!,status:'FLYING_PRODUCTION',sourceFacing:'RIGHT',flyingProfile:'FLYING'};
  if(character==='MIMI') return {character:'MIMI',species:'mimi',stage:1,manifest:resolveMonster('MIMI')!.assetRoot+'/manifest.json',base:resolveMonster('MIMI')!.baseAsset!,status:'SUPPLIED',sourceFacing:'RIGHT',staticProfile:'STATIC'};
  return null;
}
export const pilotFrames = {IDLE:6,MOVE:8,REACT:6} as const;
export const pilotClips = {IDLE:'idle',MOVE:'walk',REACT:'react'} as const;
export const pilotContract = {canvas:256,anchor:{x:.5,y:1},maxFrames:32,minFrameDuration:40,maxFrameDuration:1000,reactDuration:480,minimumRate:.5,maximumRate:2} as const;
export class PilotAssets {
  constructor(private loader=new AssetLoader()) {}
  async load(p:Pilot,state:AnimationSequence):Promise<LoadedClip|null> {
    if(p.staticProfile==='STATIC') {
      if(p.status==='NOT_SUPPLIED' || !Object.hasOwn(staticClips,state)) return null;
      const c=staticClips[state as keyof typeof staticClips];
      const a=await this.loader.loadRegistered(p.species,p.stage,p.manifest,c.name);
      return a && a.manifest.canvas.width===256 && a.manifest.canvas.height===256 && a.clip.frames===c.frames && a.clip.frameDuration===c.frameDuration && a.clip.loop===c.loop?a:null;
    }
    if(state==='PEEK') return null;
    if(p.floatingProfile==='FLOATING') {
      if(p.status==='NOT_SUPPLIED' || !Object.hasOwn(floatingClips,state)) return null;
      const c=floatingClips[state as keyof typeof floatingClips];
      const a=await this.loader.loadRegistered(p.species,p.stage,p.manifest,c.name);
      return a && a.manifest.canvas.width===256 && a.manifest.canvas.height===256 && a.clip.frames===c.frames && a.clip.frameDuration===c.frameDuration && a.clip.loop?a:null;
    }
    if(state==='FLOAT' || state==='SETTLE') return null;
    if(p.flyingProfile==='FLYING') {
      if(p.status==='NOT_SUPPLIED' || !Object.hasOwn(flyingClips,state)) return null;
      const c=flyingClips[state as keyof typeof flyingClips];
      const a=await this.loader.loadRegistered(p.species,p.stage,p.manifest,c.name);
      return a && a.manifest.canvas.width===256 && a.manifest.canvas.height===256 && a.clip.frames===c.frames && a.clip.frameDuration===c.frameDuration && a.clip.loop?a:null;
    }
    if(state==='HOVER' || state==='FLY' || state==='GLIDE') return null;
    if(p.jumpProfile==='JUMP') {
      if(state!=='JUMP' || p.status==='NOT_SUPPLIED') return null;
      const asset=await this.loader.loadRegistered(p.species,p.stage,p.manifest,'jump');
      return asset && asset.clip.frames===8 && asset.clip.frameDuration===80 && !asset.clip.loop && asset.manifest.canvas.width===256 && asset.manifest.canvas.height===256 && JSON.stringify(asset.manifest.jumpPhases)===JSON.stringify(jumpPhases)?asset:null;
    }
    if(state==='JUMP') return null;
    if(state!=='BLINK' && !Object.hasOwn(pilotClips,state)) return null;
    if(p.status==='NOT_SUPPLIED' || (p.status==='IDLE_PRODUCTION' && state!=='IDLE' && state!=='BLINK' && !(state==='MOVE' && p.moveStatus==='PRODUCTION') && !(state==='REACT' && (p.reactStatus==='PRODUCTION' || p.reactStatus==='SUPPLIED')))) return null;
    const sequences=p.character==='MOA' && p.stage===1;
    if(state==='BLINK' && !sequences) return null;
    const name=sequences && state==='IDLE'?'breath':state==='BLINK'?'blink':pilotClips[state];
    const expected=state==='IDLE' && (sequences || p.character==='PIP')?4:state==='BLINK'?3:pilotFrames[state];
    const asset=await this.loader.loadRegistered(p.species,p.stage,p.manifest,name);
    if(!asset || asset.manifest.canvas.width!==256 || asset.manifest.canvas.height!==256 || asset.clip.frames!==expected || asset.clip.frameDuration<40 || asset.clip.frameDuration>1000 || asset.clip.loop!==(state!=='REACT' && state!=='BLINK') || (state==='REACT' && asset.clip.frames*asset.clip.frameDuration!==480)) return null;
    if(sequences && (state==='IDLE' || state==='BLINK') && !asset.manifest.idleSequences) return null;
    return asset;
  }
}
export interface AnimationInput { speed:number;state:string;suppressed:boolean; jump?:JumpSample|null; flight?:FlightMotion|null; floating?:FlightMotion|null }
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
    this.blocked=input.suppressed||input.state==='DRAGGING'||input.state==='SLEEPING'||input.state==='BATTLE'||input.state==='EVOLVING'||input.state==='ENGAGED';
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
