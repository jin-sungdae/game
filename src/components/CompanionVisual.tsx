import { memo, useLayoutEffect, useRef, useState } from 'react';
import type { CompanionState } from '../types/entity';
import { useAnimation } from '../animation/useAnimation';
import { directionScale, spriteSize } from '../animation/model';
export function PlaceholderRenderer({facing}:{facing:number}) {
  return <div className="body" style={{transform:`scaleX(${directionScale(facing)})`}}><i/><i/><span className="mouth"/></div>;
}
export const CompanionVisual=memo(function CompanionVisual({state,facing}:{state:CompanionState;facing:number}) {
  const view=useAnimation('moa',1,state);
  const container=useRef<HTMLDivElement>(null);
  const [bounds,setBounds]=useState({width:0,height:0});
  const [failed,setFailed]=useState<string|null>(null);
  useLayoutEffect(()=>{
    const node=container.current!;
    const observer=new ResizeObserver(([entry])=>setBounds({width:entry.contentRect.width,height:entry.contentRect.height}));
    observer.observe(node); return ()=>observer.disconnect();
  },[]);
  const sprite=view && failed!==view.identity ? view : null;
  const size=sprite ? spriteSize(sprite.asset.manifest,bounds.width,bounds.height) : null;
  return <div ref={container} className={`companion-visual ${sprite?'has-sprite':'has-placeholder'}`}>
    {sprite && size ? <img className="sprite-frame" alt="MOA" draggable={false}
      src={sprite.asset.urls[sprite.frame]} style={{...size,transform:`scaleX(${directionScale(facing)})`}}
      onError={()=>setFailed(sprite.identity)}/> : <><PlaceholderRenderer facing={facing}/><span className="name">MOA</span><span className="state">{state}</span></>}
  </div>;
});
