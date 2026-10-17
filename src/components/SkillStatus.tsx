import {useEffect,useRef,useState} from 'react';
import {animationClock} from '../animation/clock';
import {SkillTimeline,type SkillCue} from '../presentation/skill';
export function SkillStatus({cue}:{cue?:SkillCue|null}) {
 const timeline=useRef(new SkillTimeline());const [phase,setPhase]=useState<string|null>(null);
 useEffect(()=>{
  if(!cue)return;timeline.current.observe(cue,performance.now());
  const media=matchMedia('(prefers-reduced-motion: reduce)');
  let stop=()=>{};
  const resume=()=>{stop();stop=()=>{};if(document.hidden){setPhase(null);return;}
   stop=animationClock.subscribe(time=>{const value=timeline.current.sample(time,media.matches,false);setPhase(old=>old===(value?.phase??null)?old:value?.phase??null);if(!value)stop();});};
  resume();document.addEventListener('visibilitychange',resume);
  return ()=>{stop();document.removeEventListener('visibilitychange',resume);};
 },[cue?.commandId]);
 // No body transform or substitute sprite: both body and effect sheets are still required.
 return phase?<small role="status">스킬 사용 완료 · 시각 효과 준비 중</small>:null;
}
