export interface SkillCue {commandId:string;skillCode:string;species:string;castMotion:string;element:string;assetStatus:string;phases:{phase:string;durationMs:number}[]}
const phases=['CAST_START','CHARGE','RELEASE','PROJECTILE','IMPACT','RECOVERY'];
export function validSkillCue(c:SkillCue):boolean {
 return !!c && Array.isArray(c.phases) && typeof c.commandId==='string' && c.commandId.length===36 && c.phases.length===6 && c.phases.every((p,i)=>(p && (p.phase===phases[i] || i===3&&p.phase==='AREA'))&&Number.isFinite(p.durationMs)&&p.durationMs>0&&p.durationMs<=2000);
}
// Pure presentation timeline: server owns effects, damage, cooldown and turn. No speculative impact.
export class SkillTimeline {
 private battle:string|null=null;private seen=new Set<string>();private start=0;private cue:SkillCue|null=null;
 selectBattle(id:string){if(id===this.battle)return;this.battle=id;this.seen.clear();this.cue=null;}
 observe(c:SkillCue,time:number){if(!validSkillCue(c)||!Number.isFinite(time)||this.seen.has(c.commandId))return;this.seen.add(c.commandId);this.start=time;this.cue={...c,phases:c.phases.map(p=>({...p}))};}
 sample(time:number,reduced:boolean,hidden:boolean){
  if(!this.cue||hidden||!Number.isFinite(time))return null;
  let elapsed=Math.max(0,time-this.start);
  for(const p of this.cue.phases){if(elapsed<p.durationMs)return {phase:reduced?'IMPACT':p.phase,bodyMotion:this.cue.castMotion,effect:this.cue.element,assetStatus:this.cue.assetStatus};elapsed-=p.durationMs;}
  return null;
 }
}
