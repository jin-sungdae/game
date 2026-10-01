import { resolveFloating, type FloatingState } from '../animation/floating';
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { resolveFlying, type FlightState } from '../animation/flying';
import { jumpFrame } from '../animation/jump';
import { IdleSequencer, idleRandom } from '../animation/idle';
import { animationClock } from '../animation/clock';
import { AnimationStateResolver, CharacterAnimator, PilotAssets, type AnimationInput, type AnimationSequence, type Pilot } from '../animation/pilot';
import type { LoadedClip } from '../animation/loader';
import { useBaseAsset } from '../assets/useBaseAsset';
import { baseSize } from '../assets/base';
import { directionScale } from '../animation/model';
import { useVisualBounds } from './BaseVisual';
const assets=new PilotAssets();
export function CharacterRenderer({pilot,input,facing,name,entityId}:{pilot:Pilot;input:AnimationInput;facing:number;name:string;entityId:string}) {
  const runtime=useMemo(()=>({floatingState:'HOVER' as FloatingState,flightState:'HOVER' as FlightState,resolver:new AnimationStateResolver(),animator:new CharacterAnimator(),idle:new IdleSequencer(idleRandom()),clips:new Map<AnimationSequence,LoadedClip|null>()}),[entityId,pilot.character]);
  const [view,setView]=useState<{runtime:object;state:AnimationSequence;frame:number;suppressed:boolean;asset:LoadedClip|null}>({runtime,state:'IDLE',frame:0,suppressed:false,asset:null});
  const [failed,setFailed]=useState<string|null>(null);
  const reduced=useRef(false);
  const latestInput=useRef(input);latestInput.current=input;
  const base=useBaseAsset(pilot.base);
  const {container,bounds}=useVisualBounds();
  useLayoutEffect(()=>{runtime.resolver.observe(input,performance.now());},[runtime,input]);
  useEffect(()=>{
    let disposed=false;
    const media=matchMedia('(prefers-reduced-motion: reduce)');
    const change=()=>{reduced.current=media.matches;};change();media.addEventListener('change',change);
    for(const state of ['IDLE','BLINK','MOVE','REACT','JUMP','HOVER','FLY','GLIDE','FLOAT','SETTLE'] as const) void assets.load(pilot,state).then(clip=>{if(!disposed)runtime.clips.set(state,clip);});
    const stop=animationClock.subscribe(time=>{
      const floating=resolveFloating(latestInput.current,runtime.floatingState);
      if(pilot.floatingProfile) runtime.floatingState=floating.state;
      const flight=resolveFlying(latestInput.current,runtime.flightState);
      if(pilot.flyingProfile) runtime.flightState=flight.state;
      const resolved=runtime.resolver.sample(time);
      const breath=runtime.clips.get('IDLE');
      const sequence=runtime.idle.sample(time,resolved.state==='IDLE' && !resolved.suppressed,reduced.current,breath?.manifest.idleSequences,
        (breath?.manifest.animations.blink?.frames??3)*(breath?.manifest.animations.blink?.frameDuration??90));
      const phaseFrame=jumpFrame(latestInput.current.jump,resolved.suppressed,reduced.current);
      const sample:{state:AnimationSequence;suppressed:boolean;rate:number}=pilot.floatingProfile?floating:pilot.flyingProfile?flight:{...resolved,state:pilot.jumpProfile==='JUMP'?(phaseFrame===null?'IDLE':'JUMP'):resolved.state==='IDLE'?sequence:resolved.state};
      const clip=sample.suppressed?null:runtime.clips.get(sample.state)??null;
      const frame=sample.state==='JUMP'?phaseFrame!:runtime.animator.sample(sample.state+':'+Boolean(clip)+':'+sample.suppressed,clip,time,sample.rate,reduced.current);
      setView(old=>old.runtime===runtime && old.state===sample.state && old.frame===frame && old.suppressed===sample.suppressed && old.asset===clip?old:{runtime,state:sample.state,frame,suppressed:sample.suppressed,asset:clip});
    });
    return ()=>{disposed=true;stop();media.removeEventListener('change',change);runtime.clips.clear();runtime.idle.reset();};
  },[runtime,pilot.character,pilot.status]);
  // Movement phases render from the same native snapshot as telemetry/position,
  // without waiting one extra shared-clock callback at ground contact.
  const nativeFrame=jumpFrame(input.jump,input.suppressed || input.state!=='ROAMING',reduced.current);
  const floating=resolveFloating(input,runtime.floatingState);
  const flight=resolveFlying(input,runtime.flightState);
  const current=pilot.floatingProfile?{state:floating.state,frame:view.runtime===runtime && view.state===floating.state?view.frame:0,suppressed:floating.suppressed}:pilot.flyingProfile?{state:flight.state,frame:view.runtime===runtime && view.state===flight.state?view.frame:0,suppressed:flight.suppressed}:pilot.jumpProfile==='JUMP'?{state:(nativeFrame===null?'IDLE':'JUMP') as AnimationSequence,frame:nativeFrame??0,suppressed:input.suppressed || input.state!=='ROAMING'}:view.runtime===runtime?view:{state:'IDLE' as const,frame:0,suppressed:true};
  const asset=current.suppressed||input.suppressed?null:runtime.clips.get(current.state);
  const clipId=entityId+':'+pilot.character+':'+current.state;
  const animation=asset?.urls[current.frame]??null;
  const url=animation && clipId!==failed?animation:base.url;
  return <div ref={container} className="companion-visual character-renderer" role="group" aria-label={`${name} ${current.state.toLowerCase()}`} data-character={pilot.character} data-animation-state={current.state} data-animation-source={url===base.url?'base':'animation'}>
    {url ? <div className="character-facing" style={{...baseSize(bounds.width,bounds.height),transform:`scaleX(${directionScale(facing)})`}}>
      <div className={`character-animation ${(!animation || clipId===failed) && current.state==='IDLE' && !current.suppressed && !input.suppressed?'character-breathing':''}`}>
        <img className="sprite-frame" src={url} alt={`${name} ${current.state} frame ${current.frame+1} ${url===base.url?'base':'animation'}${pilot.floatingProfile?' trace '+JSON.stringify({...input.floating,domainState:input.state,suppressed:current.suppressed,animation:floating.state,rate:floating.rate,rendererFlip:directionScale(facing)}):pilot.jumpProfile==='JUMP'?' trace '+JSON.stringify(input.jump??null):pilot.flyingProfile?' trace '+JSON.stringify({...input.flight,animation:flight.state,rate:flight.rate,rendererFlip:directionScale(facing)}):''}`} draggable={false} style={baseSize(bounds.width,bounds.height)} onError={()=>{if(url===base.url)base.fail();else setFailed(clipId);}}/>
      </div>
    </div> : <span className="name" role="img" aria-label={`${name} asset missing`}>{name} · asset missing</span>}
  </div>;
}
