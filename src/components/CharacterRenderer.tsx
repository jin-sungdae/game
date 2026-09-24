import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { animationClock } from '../animation/clock';
import { AnimationStateResolver, CharacterAnimator, PilotAssets, type AnimationInput, type AnimationState, type Pilot } from '../animation/pilot';
import type { LoadedClip } from '../animation/loader';
import { useBaseAsset } from '../assets/useBaseAsset';
import { baseSize } from '../assets/base';
import { directionScale } from '../animation/model';
import { useVisualBounds } from './BaseVisual';
const assets=new PilotAssets();
export function CharacterRenderer({pilot,input,facing,name,entityId}:{pilot:Pilot;input:AnimationInput;facing:number;name:string;entityId:string}) {
  const runtime=useMemo(()=>({resolver:new AnimationStateResolver(),animator:new CharacterAnimator(),clips:new Map<AnimationState,LoadedClip|null>()}),[entityId,pilot.character]);
  const [view,setView]=useState<{runtime:object;state:AnimationState;frame:number;suppressed:boolean;asset:LoadedClip|null}>({runtime,state:'IDLE',frame:0,suppressed:false,asset:null});
  const [failed,setFailed]=useState<string|null>(null);
  const reduced=useRef(false);
  const base=useBaseAsset(pilot.base);
  const {container,bounds}=useVisualBounds();
  useLayoutEffect(()=>{runtime.resolver.observe(input,performance.now());},[runtime,input]);
  useEffect(()=>{
    let disposed=false;
    const media=matchMedia('(prefers-reduced-motion: reduce)');
    const change=()=>{reduced.current=media.matches;};change();media.addEventListener('change',change);
    for(const state of ['IDLE','MOVE','REACT'] as const) void assets.load(pilot,state).then(clip=>{if(!disposed)runtime.clips.set(state,clip);});
    const stop=animationClock.subscribe(time=>{
      const sample=runtime.resolver.sample(time);
      const clip=sample.suppressed?null:runtime.clips.get(sample.state)??null;
      const frame=runtime.animator.sample(sample.state+':'+Boolean(clip)+':'+sample.suppressed,clip,time,sample.rate,reduced.current);
      setView(old=>old.runtime===runtime && old.state===sample.state && old.frame===frame && old.suppressed===sample.suppressed && old.asset===clip?old:{runtime,state:sample.state,frame,suppressed:sample.suppressed,asset:clip});
    });
    return ()=>{disposed=true;stop();media.removeEventListener('change',change);runtime.clips.clear();};
  },[runtime,pilot.character,pilot.status]);
  const current=view.runtime===runtime?view:{state:'IDLE' as const,frame:0,suppressed:true};
  const asset=current.suppressed||input.suppressed?null:runtime.clips.get(current.state);
  const clipId=entityId+':'+pilot.character+':'+current.state;
  const animation=asset?.urls[current.frame]??null;
  const url=animation && clipId!==failed?animation:base.url;
  return <div ref={container} className="companion-visual character-renderer" role="group" aria-label={`${name} ${current.state.toLowerCase()}`} data-character={pilot.character} data-animation-state={current.state} data-animation-source={url===base.url?'base':'animation'}>
    {url ? <div className="character-facing" style={{...baseSize(bounds.width,bounds.height),transform:`scaleX(${directionScale(facing)})`}}>
      <div className={`character-animation ${(!animation || clipId===failed) && current.state==='IDLE' && !current.suppressed && !input.suppressed?'character-breathing':''}`}>
        <img className="sprite-frame" src={url} alt={name} draggable={false} style={baseSize(bounds.width,bounds.height)} onError={()=>{if(url===base.url)base.fail();else setFailed(clipId);}}/>
      </div>
    </div> : <span className="name" role="img" aria-label={`${name} asset missing`}>{name} · asset missing</span>}
  </div>;
}
