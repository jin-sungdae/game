import { companionBase, rendererSource } from '../assets/base';
import { useBaseAsset } from '../assets/useBaseAsset';
import { BaseSprite, useVisualBounds } from './BaseVisual';
import { resolveCompanion } from '../entities/registry';
import { memo, useState } from 'react';
import type { CompanionState } from '../types/entity';
import { useAnimation } from '../animation/useAnimation';
import { directionScale, spriteSize } from '../animation/model';
export function PlaceholderRenderer({facing}:{facing:number}) {
  return <div className="body" style={{transform:`scaleX(${directionScale(facing)})`}}><i/><i/><span className="mouth"/></div>;
}
export const CompanionVisual=memo(function CompanionVisual({state,facing,species='moa',evolutionStage=1}:{state:CompanionState;facing:number;species?:string;evolutionStage?:number}) {
  const view=useAnimation(species,evolutionStage,state);
  const name=resolveCompanion(species,evolutionStage)?.name ?? 'Companion';
  const {container,bounds}=useVisualBounds();
  const base=useBaseAsset(companionBase(species,evolutionStage));
  const [failed,setFailed]=useState<string|null>(null);
  const sprite=view && failed!==view.identity ? view : null;
  const size=sprite ? spriteSize(sprite.asset.manifest,bounds.width,bounds.height) : null;
  const source=rendererSource(sprite?.asset.urls[sprite.frame] ?? null,base.url);
  return <div ref={container} className={`companion-visual ${source.kind!=='css'?'has-sprite':'has-placeholder'}`}>
    {sprite && size ? <img className="sprite-frame" alt={name} draggable={false}
      src={sprite.asset.urls[sprite.frame]} style={{...size,transform:`scaleX(${directionScale(facing)})`}}
      onError={()=>setFailed(sprite.identity)}/> : source.kind==='base' ? <BaseSprite character={species} state={state} url={source.url} name={name} facing={facing} bounds={bounds} onError={base.fail}/> : <><PlaceholderRenderer facing={facing}/><span className="name">{name}</span><span className="state">{state}</span></>}
  </div>;
});
