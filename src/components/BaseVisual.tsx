import { baseMotion } from '../presentation/baseMotion';
import { useLayoutEffect, useRef, useState } from 'react';
import { baseSize } from '../assets/base';
import { directionScale } from '../animation/model';
export function useVisualBounds() {
  const container=useRef<HTMLDivElement>(null);
  const [bounds,setBounds]=useState({width:0,height:0});
  useLayoutEffect(()=>{
    const observer=new ResizeObserver(([entry])=>setBounds({width:entry.contentRect.width,height:entry.contentRect.height}));
    observer.observe(container.current!);return ()=>observer.disconnect();
  },[]);
  return {container,bounds};
}
export function BaseSprite({url,name,facing,bounds,onError,character,state}:{url:string;name:string;facing:number;character:string;state:string;bounds:{width:number;height:number};onError:()=>void}) {
  const motion=baseMotion(character,state);
  return <div className={motion.className} style={baseSize(bounds.width,bounds.height)}><img className="sprite-frame base-sprite" src={url} alt={name} draggable={false}
    style={{...baseSize(bounds.width,bounds.height),transform:`scaleX(${directionScale(facing)})`}} onError={onError}/>{motion.sleep && <span className="base-sleep" aria-label="Sleeping">Zz</span>}</div>;
}
