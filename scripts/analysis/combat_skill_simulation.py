#!/usr/bin/env python3
"""Read-only Combat & Skill simulation; candidates are assumptions, not approved rules.

Run with Python 3.9+: this script prints results and never connects to a DB.
--self-test checks probability transitions without running the scenario matrix.
The complete run evaluates 2.7 million joint scenario rows; it may take a minute.
"""
from pathlib import Path
import os
import sys
import hashlib
import unittest

ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)

def verify_baseline():
    expected = {
        "CombatRules.java": [
            "companionHp() {return 100;}",
            "companionAttack(int level) {return Math.addExact(10,Math.multiplyExact(level,2));}",
            "monsterHp(int level) {return Math.addExact(20,Math.multiplyExact(level,10));}",
            "monsterAttack(int level) {return Math.addExact(3,Math.multiplyExact(level,2));}",
            "MAX_LEVEL = 20", "return 50L*level*(level-1);",
            "return level*20L;",
            "baseCaptureRate()+(1-(double)hp/maxHp)*0.50,0.05,0.95)",
        ],
        "BattleDecision.java": [
            "case BALANCED -> 85", "case AGGRESSIVE -> 100",
            "case DEFENSIVE -> 45", "case ERRATIC -> completedTurns%2==0?25:90",
        ],
        "BattleService.java": [
            "if(monster==0)", "else {hp=counter(b,e,events)",
            "Math.round(chance*1_000_000)",
            'else if(b.status.equals("VICTORY")) {resolve(e.id,"DEFEATED");}',
        ],
    }
    for name, snippets in expected.items():
        path = ROOT / "server/src/main/java/dev/luma/game" / name
        source = path.read_text()
        for snippet in snippets:
            if snippet not in source:
                raise RuntimeError("Baseline changed; review simulation before reuse: " + name)
        print("SOURCE_SHA256", name, hashlib.sha256(path.read_bytes()).hexdigest())
    defaults = json.loads((ROOT / "server/src/main/resources/content/rarity-defaults.json").read_text())
    rates = {key: value["baseCaptureRate"] for key, value in defaults.items()}
    if rates != {"COMMON": .35, "UNCOMMON": .25, "RARE": .15, "EPIC": .10, "SPECIAL": .05}:
        raise RuntimeError("Capture defaults changed; review simulation before reuse")
    if len(dex) != 30 or len(active) != 15:
        raise RuntimeError("Dex coverage changed; review scenario labels")
    print("SOURCE_SHA256", "monster-dex.json", hashlib.sha256((ROOT / "src/entities/monster-dex.json").read_bytes()).hexdigest())
    print("SCOPE: source-derived Python replica, not execution of Java service/DB.")
    print("ASSUMPTIONS: independent uniform RNG; no items, expiry or action latency; one skill replaces first attack.")
    print("ASSUMPTIONS: candidate M=L, HP=100+15*(L-1), normal HP=20+5*M, hard HP=40+12*M.")
    print("WEIGHTS: equal scenario weights, not spawn-weighted live encounter probabilities.")
    print("METRICS: TTK is required kill actions if alive; HP is expected percent conditional on victory (0 if impossible).")
    print("COVERAGE: all 3 species share stats; all 5 stages are sensitivity cases, not reachable evolution claims.")
    print("COVERAGE: 15 provisional dex slots use all 4 personalities as brackets, not confirmed definitions.")
    print("CAP tuple: per-attempt chance, cumulative success, HP% given capture, expected counters, expected capture attempts.")
    print("CAPTURE: repeated attempts until death/success; expiry excluded; EPIC unsupported by current capture rules.")
    print("DECISION: all candidate constants are unapproved. High difficulty survival target remains unspecified.")

import math,json,collections
dex=json.load(open("src/entities/monster-dex.json"))
active=[x for x in dex if x["enabled"] and x["contentReady"]]
ps=["BALANCED","AGGRESSIVE","DEFENSIVE","ERRATIC"]
def prob(p,t): return {"BALANCED":.85,"AGGRESSIVE":1,"DEFENSIVE":.45,"ERRATIC":.25 if t%2==0 else .9}[p]
def fight(h,a,m,d,p,skill=1):
    dist={0:1.}; counter=0.; t=0
    while m>0:
        m-=math.floor(a*skill) if t==0 else a
        if m<=0: break
        out=collections.defaultdict(float)
        for k,v in dist.items():
            q=prob(p,t);counter+=v*q
            out[k]+=v*(1-q)
            if (k+1)*d<h:out[k+1]+=v*q
        dist=out;t+=1
    win=sum(dist.values())
    hp=sum(v*(h-k*d) for k,v in dist.items())/win/h*100 if win else 0
    return t+1,win,hp,counter
def report(label,rows,target):
    n=len(rows);print(label,"n",n,"TTK",min(r[0] for r in rows),max(r[0] for r in rows),
    "target%",round(100*sum(target[0]<=r[0]<=target[1] for r in rows)/n,3),
    "win%",round(100*sum(r[1] for r in rows)/n,3),
    "minWin%",round(100*min(r[1] for r in rows),3),
    "HPwin%range",tuple(round(f(r[2] for r in rows),3) for f in (min,max)),
    "counters",round(sum(r[3] for r in rows)/n,3))

def cap(h,a,m,d,p,b,chip):
 dist={0:1.};counter=0.;t=0;initial=m
 while chip and m>a:
  m-=a;out=collections.defaultdict(float)
  for k,v in dist.items():
   q=prob(p,t);counter+=v*q;out[k]+=v*(1-q)
   if (k+1)*d<h:out[k+1]+=v*q
  dist=out;t+=1
 chance=math.floor(min(.95,max(.05,b+(1-m/initial)*.5))*1_000_000+.5)/1_000_000;success=0.;hpp=0.;attempts=0
 for i in range(1000):
  if sum(dist.values())<1e-14:break
  out=collections.defaultdict(float)
  for k,v in dist.items():
   success+=v*chance;hpp+=v*chance*(h-k*d);attempts+=v
   q=prob(p,t);counter+=v*(1-chance)*q;out[k]+=v*(1-chance)*(1-q)
   if (k+1)*d<h:out[k+1]+=v*(1-chance)*q
  dist=out;t+=1
 return round(chance,4),round(success,6),round(hpp/success/h*100,2),round(counter,3),round(attempts,3)

def run():
    print("BASELINE ACTUAL FORMULAS L1-20,M1-3,15 ACTIVE")
    rows=[fight(100,10+2*l,20+10*m,3+2*m,x["battlePersonality"]) for l in range(1,21) for m in range(1,4) for x in active]
    report("base",rows,(2,4))
    for l in [1,5,10,15,20]:
     r=[fight(100,10+2*l,20+10*m,3+2*m,x["battlePersonality"]) for m in range(1,4) for x in active];report("base L"+str(l),r,(2,4))
    print("HP CANDIDATES equal M=L original monster HP")
    for slope in [0,10,15,20]:
     r=[fight(100+slope*(l-1),10+2*l,20+10*l,3+2*l,p) for l in range(1,101) for p in ps];report("slope"+str(slope),r,(2,4))
    print("MONSTER LEVEL CANDIDATES hp slope15 original monster HP")
    for mode in ["fixed","0.6L","L","1.2L"]:
     r=[]
     for l in range(1,101):
      ms=range(1,4) if mode=="fixed" else [max(1,math.floor(.6*l)) if mode=="0.6L" else l if mode=="L" else min(100,math.ceil(1.2*l))]
      r += [fight(100+15*(l-1),10+2*l,20+10*m,3+2*m,p) for m in ms for p in ps]
     report(mode,r,(2,4))
    print("PROPOSED CANDIDATE M=L hp15 attack unchanged species/stage neutral")
    for tier in ["normal","hard"]:
     for skill in [1,1.5,2,3]:
      r=[fight(100+15*(l-1),10+2*l,(20+5*l) if tier=="normal" else (40+12*l),3+2*l,p,skill) for l in range(1,101) for p in ps]
      report(tier+" skill"+str(skill),r,(2,4) if tier=="normal" else (5,8))
    for l in [1,20,40,60,80,100]:
     for tier in ["normal","hard"]:
      rs=[fight(100+15*(l-1),10+2*l,20+5*l if tier=="normal" else 40+12*l,3+2*l,p) for p in ps]
      print("MATRIX",l,tier,"HP",100+15*(l-1),"A",10+2*l,"MHP",20+5*l if tier=="normal" else 40+12*l,"TTK",rs[0][0],"win",min(r[1] for r in rs),"HP% by B,A,D,E",[round(r[2],2) for r in rs],"counter",[round(r[3],2) for r in rs])
    print("STAGE SENSITIVITY 100 levels x 5 stages x30 slots (species symmetry collapsed), missing personality bracket")
    for growth in [0,.05,.1]:
     for tier in ["normal","hard"]:
      r=[]
      for l in range(1,101):
       for s in range(1,6):
        a=((10+2*l)*(100+round(growth*100)*(s-1)))//100
        for x in dex:
         for p in ([x["battlePersonality"]] if x["battlePersonality"] else ps):
          r.append(fight(100+15*(l-1),a,20+5*l if tier=="normal" else 40+12*l,3+2*l,p))
      report("stage"+str(growth)+" "+tier,r,(2,4) if tier=="normal" else (5,8))
    print("LEVEL OFFSET proposed")
    for delta in [-5,0,5,10]:
     for tier in ["normal","hard"]:
      r=[fight(100+15*(l-1),10+2*l,20+5*m if tier=="normal" else 40+12*m,3+2*m,p) for l in range(1,101) for m in [min(100,max(1,l+delta))] for p in ps]
      report(str(delta)+tier,r,(2,4) if tier=="normal" else (5,8))
    print("REGRESSION new vs old all L1-20 M1-3")
    for what in ["hpOnly","full"]:
     changed=0
     for l in range(1,21):
      for m in range(1,4):
       old=math.ceil((20+10*m)/(10+2*l));new=math.ceil((20+5*m)/(10+2*l))
       changed+=old!=new if what=="full" else 0
     print(what,"TTK changed",changed,"/60")
    print("EXP next cost100L; battles reset at threshold and M=L")
    for l in [1,20,40,60,80,99]:
     print(l,[math.ceil(100*l/r) for r in [40,20*l,round(20*l**1.2)]])
    for mode in ["fixed40","linear","power1.2"]:
     l=1;xp=0;n=0
     while l<100:
      xp+=40 if mode=="fixed40" else 20*l if mode=="linear" else round(20*l**1.2)
      n+=1
      while l<100 and xp>=50*l*(l+1):l+=1
     print("EXP total L1to100",mode,n)
    for name,h,a,m,d in [("base L1M3",100,12,50,9),("new L100normal",1585,210,520,203),("new L100hard",1585,210,1240,203)]:
     for rarity,b in [("COMMON",.35),("RARE",.15),("SPECIAL",.05)]:
      print("CAP",name,rarity,"aggressive full",cap(h,a,m,d,"AGGRESSIVE",b,False),"chip",cap(h,a,m,d,"AGGRESSIVE",b,True),"after",min(.95,b+.5))
    print("JOINT 3species x100levels x5stage x30dex with provisional four-personality brackets; both tiers")
    for stageg in [0,.05,.1]:
     for skill in [1,1.5,2,3]:
      for tier in ["normal","hard"]:
       r=[]
       for species in ["MOA","RUU","NOX"]:
        for l in range(1,101):
         for s in range(1,6):
          a=((10+2*l)*(100+round(stageg*100)*(s-1)))//100
          for x in dex:
           for p in ([x["battlePersonality"]] if x["battlePersonality"] else ps):
            r.append(fight(100+15*(l-1),a,20+5*l if tier=="normal" else 40+12*l,3+2*l,p,skill))
       report(str(stageg)+" "+str(skill)+" "+tier,r,(2,4) if tier=="normal" else (5,8))


class ProbabilityTests(unittest.TestCase):
    def test_killing_blow_never_counters(self):
        self.assertEqual(fight(100,12,12,999,"AGGRESSIVE"), (1,1.,100.,0.))
    def test_fatal_counter(self):
        self.assertEqual(fight(5,1,2,5,"AGGRESSIVE"), (2,0,0,1.))
    def test_balanced_survival(self):
        result=fight(5,1,2,5,"BALANCED")
        self.assertAlmostEqual(result[1],.15)
        self.assertEqual(result[2],100)
        self.assertAlmostEqual(result[3],.85)
    def test_erratic_turn_parity(self):
        self.assertAlmostEqual(fight(100,1,3,1,"ERRATIC")[3],1.15)
    def test_capture_two_attempts(self):
        result=cap(10,1,10,5,"AGGRESSIVE",.5,False)
        self.assertEqual(result,(.5,.75,83.33,.75,1.5))
    def test_current_level_one_aggressive(self):
        self.assertEqual(fight(100,12,50,9,"AGGRESSIVE"),(5,1.,64.,4.))
    def test_skill_replaces_attack(self):
        self.assertEqual(fight(100,10,30,9,"AGGRESSIVE",3),(1,1.,100.,0.))

if __name__ == "__main__":
    if "--self-test" in sys.argv:
        unittest.main(argv=[sys.argv[0]], verbosity=2)
    else:
        verify_baseline()
        run()
