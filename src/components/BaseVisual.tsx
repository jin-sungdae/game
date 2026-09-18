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
export function BaseSprite({url,name,facing,bounds,onError}:{url:string;name:string;facing:number;bounds:{width:number;height:number};onError:()=>void}) {
  return <img className="sprite-frame base-sprite" src={url} alt={name} draggable={false}
    style={{...baseSize(bounds.width,bounds.height),transform:`scaleX(${directionScale(facing)})`}} onError={onError}/>;
}
