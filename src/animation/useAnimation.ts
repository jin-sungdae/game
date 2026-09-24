import { animationClock } from './clock';
import { useEffect, useMemo, useState } from 'react';
import type { CompanionState } from '../types/entity';
import { AnimationController } from './controller';
import { AssetLoader, type LoadedClip } from './loader';
import { stateClips } from './model';
const loader=new AssetLoader();
export function useAnimation(species:string, stage:number, state:CompanionState) {
  const clipName=stateClips[state];
  // State is included so IDLE -> DRAGGING also restarts its shared idle clip.
  const identity=`${species}:${stage}:${state}:${clipName}`;
  const token=useMemo(()=>({identity}),[identity]);
  const [view,setView]=useState<{token:object; identity:string; asset:LoadedClip; frame:number}|null>(null);
  useEffect(()=>{
    let disposed=false;let stop=()=>{};
    void loader.load(species,stage,clipName).then(asset=>{
      if(disposed || !asset) return;
      const controller=new AnimationController(); controller.select(identity,asset.clip);
      let previous=-1;
      const tick=()=>{
        if(disposed) return;
        const sample=controller.sample();
        if(sample.frame!==previous) { previous=sample.frame; setView({token,identity,asset,frame:sample.frame}); }
        if(sample.finished) stop();
      };
      tick();
      if(!controller.sample().finished) stop=animationClock.subscribe(tick);
    });
    return ()=>{ disposed=true; stop(); };
  },[identity,species,stage,clipName,token]);
  return view?.token===token ? view : null;
}
