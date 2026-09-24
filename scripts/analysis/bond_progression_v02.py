#!/usr/bin/env python3
"""Deterministic v0.2 timing scenarios. No runtime imports, DB, RNG or file writes."""
import json
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[2]
JAVA = ROOT / 'server/src/main/java/dev/luma/game'

def rules():
    interaction = (JAVA/'CompanionInteractionService.java').read_text()
    cooldown = int(re.search(r'COOLDOWN_SECONDS=(\d+)', interaction)[1])
    gain = int(re.search(r'BOND_GAIN=(\d+)', interaction)[1])
    battle = (JAVA/'BattleService.java').read_text()
    assert 'VALUES(?,?,1,?,?,0)' in battle and 'bond=bond+1' not in battle
    combat = (JAVA/'CombatRules.java').read_text()
    assert 'return level*20L' in combat and 'return level*10L' in combat
    assert 'return 50L*level*(level-1)' in combat and 'MAX_LEVEL = 20' in combat
    evolution = (JAVA/'EvolutionRules.java').read_text()
    assert 'new Rule("MOA", 1, 2, 3, 5)' in evolution and 'new Rule("MOA", 2, 3, 6, 12)' in evolution
    assert 'BERRY_BOND=1' in (JAVA/'ItemRules.java').read_text()
    assert "'COMPANION_CONSUMABLE',30,99" in (ROOT/'server/src/main/resources/db/migration/V5__inventory_items.sql').read_text()
    return cooldown, gain

def scenario(battle, interaction, berries, duration=6000):
    cooldown, gain = rules()
    exp = bond = gold = stage = spent = 0
    stage = 1
    timing = {'MOKORI': None, 'NEBLA': None}
    for second in range(duration+1):
        # Controlled best-level/shortest-interval case, not a population mean.
        if battle and second > 0 and second % 120 == 0:
            exp += 60
            gold += 30
        if interaction and second % cooldown == 0:
            bond += gain
        level = max(l for l in range(1, 21) if exp >= 50*l*(l-1))
        for target, needed_level, needed_bond, name in [(2,3,5,'MOKORI'),(3,6,12,'NEBLA')]:
            if stage != target-1 or level < needed_level:
                continue
            if berries:
                shortage = max(0, needed_bond-bond)
                if gold >= shortage*30:
                    bond += shortage
                    gold -= shortage*30
                    spent += shortage
            if bond >= needed_bond:
                stage = target
                timing[name] = second//60
    return {'level': level, 'exp': exp, 'bond': bond, 'gold': gold, 'stage': stage, 'berries_used': spent, 'evolution_minute': timing}

def analysis():
    cooldown, gain = rules()
    return {'cooldown_seconds':cooldown, 'interaction_gain':gain, 'battle_bond':0,
            'bond5_minutes':(5-1)*cooldown/60, 'bond12_minutes':(12-1)*cooldown/60,
            'scenarios_at_100_minutes':{name:scenario(*args) for name,args in {
                'A battle only':(True,False,False),'B interaction only':(False,True,False),
                'C battle + interaction':(True,True,False),'D battle + Berry':(True,False,True),
                'E battle + interaction + Berry':(True,True,True)}.items()}}

if __name__ == '__main__':
    print(json.dumps(analysis(), indent=2, sort_keys=True))
