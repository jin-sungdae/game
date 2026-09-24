#!/usr/bin/env python3
"""Offline analysis only. Read reviewed source contracts; never connect to a game DB.

Exact Fraction renewal/binomial calculations; no random sampling or dependencies.
CLI emits stable JSON, or --markdown for the generated report section.
"""
import argparse
from fractions import Fraction as F
import json
from math import ceil, comb
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
JAVA = ROOT / 'server/src/main/java/dev/luma/game'


def contract():
    def source(name):
        return (JAVA / (name + '.java')).read_text()
    def require(text, fragment):
        if fragment not in text:
            raise ValueError('Production contract changed; re-review analysis: ' + fragment)
    combat = source('CombatRules')
    require(combat, 'return 50L*level*(level-1);')
    require(combat, 'while(level<MAX_LEVEL && exp>=levelThreshold(level+1)) level++;')
    require(combat, 'return level*20L;')
    require(combat, 'return level*10L;')
    require(combat, 'MAX_LEVEL = 20;')
    battle = source('BattleService')
    require(battle, 'bond=bond+1')
    require(battle, 'status="VICTORY";events.add("VICTORY");reward(b,e,events);')
    capture = battle.split('public BattleDtos.Capture capture(')[1].split('public BattleDtos.Resolution ignore(')[0]
    if 'reward(' in capture or 'SET bond' in capture or 'SET exp' in capture:
        raise ValueError('Capture progression changed; re-review analysis')
    require(source('ItemRules'), 'BERRY_BOND=1')
    require(source('EvolutionRules'), 'new Rule("MOA", 1, 2, 3, 5)')
    require(source('EvolutionRules'), 'new Rule("MOA", 2, 3, 6, 12)')
    selector = source('MonsterSelector')
    require(selector, 'random.nextLong(range)')
    require(selector, 'monster.minLevel() + offset')
    migrations = ROOT / 'server/src/main/resources/db/migration'
    sql = '\n'.join(p.read_text() for p in sorted(migrations.glob('*.sql')))
    rows = re.findall(r"\('([A-Z]+)','[A-Z]+','(COMMON|UNCOMMON|RARE|SPECIAL)','[A-Z_0-9]+',([0-9]+),([0-9]+),([0-9]+),true\)", sql)
    dex = json.loads((ROOT / 'src/entities/monster-dex.json').read_text())
    active = {d['monsterCode']: d for d in dex if d['enabled'] and d['contentReady'] and d['productionStatus'] == 'PRODUCTION'}
    if len(rows) != 15 or set(active) != {r[0] for r in rows}:
        raise ValueError('Master roster changed; re-review distribution')
    for code, rarity, low, high, weight in rows:
        if (int(low), int(high)) != (1, 3) or active[code]['rarity'] != rarity or active[code]['encounterWeight'] != int(weight):
            raise ValueError('Master distribution changed')
    prices = dict((code, int(price)) for code, price in re.findall(r"\('(SMALL_POTION|BOND_BERRY|CAPTURE_CHARM)','[^']+','[^']+',([0-9]+),99\)", sql))
    if prices != {'SMALL_POTION': 20, 'BOND_BERRY': 30, 'CAPTURE_CHARM': 40}:
        raise ValueError('Shop seed changed')
    require(sql, "VALUES (1,'LOCAL_PLAYER',0)")
    require(sql, "SELECT 1,species_id,1,1,0,0,true")
    spawn = (ROOT / 'src-tauri/src/spawn/mod.rs').read_text()
    require(spawn, 'minimum_cooldown: Duration::from_secs(120)')
    require(spawn, 'maximum_cooldown: Duration::from_secs(300)')
    return {'max_level': 20, 'exp_per_monster_level': 20, 'gold_per_monster_level': 10,
            'battle_bond': 1, 'berry_bond': 1, 'prices': prices,
            'monsters': [{'code': c, 'rarity': r, 'min': int(lo), 'max': int(hi), 'weight': int(w)} for c, r, lo, hi, w in rows]}


def threshold(level):
    return 50 * level * (level - 1)


def level(exp):
    return max(l for l in range(1, 21) if exp >= threshold(l))


def hitting(units):
    """P(first passage of units at win n), uniform independent steps 1,2,3."""
    transient = {0: F(1)}
    result = {}
    for n in range(1, units + 1):
        following = {}
        for exp, probability in transient.items():
            for step in (1, 2, 3):
                target = exp + step
                if target >= units:
                    result[n] = result.get(n, F(0)) + probability / 3
                else:
                    following[target] = following.get(target, F(0)) + probability / 3
        transient = following
    assert sum(result.values()) == 1
    return result


def expected(distribution):
    return sum(n * probability for n, probability in distribution.items())


def binomial_below(n, required, p):
    return sum(F(comb(n, k)) * p**k * (1-p)**(n-k) for k in range(min(required, n+1)))


def gate(units, required, p):
    passage = hitting(units)
    if p == 0:
        return {'expected_wins': None, 'probability_locked_at_level': 1.0}
    # E[max(T_exp,T_bond)] = E[T_bond] + sum P(T_exp>n,T_bond<=n).
    # Independent hypothetical bond rolls; T_exp <= units, so finite exact sum.
    expected_gate = F(required) / p
    survival = F(1)
    for n in range(units):
        survival -= passage.get(n, F(0))
        expected_gate += survival * (1 - binomial_below(n, required, p))
    locked = sum(probability * binomial_below(n, required, p) for n, probability in passage.items())
    return {'expected_wins': float(expected_gate), 'probability_locked_at_level': float(locked)}


def state(exp, bond, gold):
    lv = level(exp)
    mokori = lv >= 3 and bond >= 5
    nebla = lv >= 6 and bond >= 12 and mokori
    return {'stage': 'NEBLA' if nebla else 'MOKORI' if mokori else 'MOA', 'level': lv,
            'exp': exp, 'bond': bond, 'gold': gold, 'mokori_requirements_met': mokori,
            'nebla_requirements_met': nebla}


def buy_and_use_berry(snapshot, quantity, rules):
    """Analysis event: no active battle, empty inventory, buy then consume all."""
    if quantity < 1 or quantity > 99:
        raise ValueError('Quantity must fit production stack99')
    cost = quantity * rules['prices']['BOND_BERRY']
    if snapshot['gold'] < cost:
        raise ValueError('Insufficient Gold')
    bond = snapshot['bond'] + quantity * rules['berry_bond']
    if bond > 2**31 - 1:
        raise ValueError('Bond overflow')
    return state(snapshot['exp'], bond, snapshot['gold'] - cost)


def simulate(pattern, opportunities=100):
    exp = bond = gold = wins = 0
    timings = {'MOKORI': None, 'NEBLA': None}
    for encounter in range(1, opportunities+1):
        event = pattern[(encounter-1) % len(pattern)]
        if event == 'W':
            monster = wins % 3 + 1  # fixed controlled sequence per victory, not random mean
            exp += monster*20
            gold += monster*10
            wins += 1
            bond += 1
        elif event not in ('C', 'I'):
            raise ValueError(event)
        current = state(exp, bond, gold)
        for name, met in [('MOKORI', current['mokori_requirements_met']), ('NEBLA', current['nebla_requirements_met'])]:
            if met and timings[name] is None:
                timings[name] = encounter
    return dict(state(exp, bond, gold), wins=wins, evolution_opportunity=timings)


def analysis():
    rules = contract()
    passages = {lv: hitting(threshold(lv)//20) for lv in range(2, 7)}
    counts = []
    previous_mean = F(0)
    for lv, dist in passages.items():
        units = (threshold(lv)-threshold(lv-1))//20
        mean = expected(dist)
        counts.append({'level': lv, 'fresh_best': min(dist), 'fresh_expected': float(mean), 'fresh_worst': max(dist),
                       'increment_expected_with_carry': float(mean-previous_mean),
                       'exact_threshold_best': ceil(units/3), 'exact_threshold_expected': float(expected(hitting(units))),
                       'exact_threshold_worst': units})
        previous_mean = mean
    economy = []
    for name, lv in [('MOKORI', 3), ('Lv5', 5), ('Lv6 / NEBLA', 6)]:
        lo, hi = threshold(lv)//2, (threshold(lv)+40)//2
        economy.append({'milestone': name, 'gold_min': lo, 'gold_max': hi,
                        'items': {code: [lo//price, hi//price] for code, price in rules['prices'].items()}})
    return {'rules': rules, 'thresholds': [{'level': l, 'exp': threshold(l), 'increment': 0 if l == 1 else threshold(l)-threshold(l-1)} for l in range(1, 21)],
            'timeline_fixed_level2': [dict(wins=w, **state(w*40, w, w*20)) for w in (0,1,5,10,15,20,25,30,40,50,60,75,100)],
            'battle_counts': counts, 'economy': economy,
            'berry_examples': {str(w): {'before': state(w*40, w, w*20),
                'after_one': buy_and_use_berry(state(w*40, w, w*20), 1, rules)} for w in (8, 38)},
            'natural_lv6_bond': {'min': 25, 'expected': float(expected(passages[6])), 'max': 75},
            'scenarios_100_opportunities': {name: simulate(pattern) for name, pattern in [('A', 'W'), ('B', 'C'), ('C', 'WC'), ('D', 'WIII')]},
            'scenario_nebla_opportunity': {name: simulate(pattern, 300)['evolution_opportunity']['NEBLA'] for name, pattern in [('A', 'W'), ('B', 'C'), ('C', 'WC'), ('D', 'WIII')]},
            'sensitivity': {name: {'mokori': gate(15, b2, p), 'nebla': gate(75, b3, p), 'expected_bond_at_lv6': float(expected(passages[6])*p)}
                for name, p, b2, b3 in [('current', F(1), 5, 12), ('battle_bond_zero', F(0), 5, 12), ('p_0.25', F(1,4), 5, 12), ('nebla_bond_40', F(1), 5, 40)]}}


def table(headers, rows):
    def cell(v):
        if v is None: return '—'
        if isinstance(v, bool): return 'YES' if v else 'NO'
        if isinstance(v, float): return f'{v:.4f}'
        return str(v)
    return '\n'.join(['| '+' | '.join(headers)+' |', '| '+' | '.join(['---']*len(headers))+' |'] + ['| '+' | '.join(map(cell, row))+' |' for row in rows])


def markdown(data):
    parts = ['<!-- BEGIN GENERATED ANALYSIS -->', '### Level Threshold Table',
        table(['Level', 'Cumulative EXP', 'Increment'], [[r['level'], r['exp'], r['increment']] for r in data['thresholds']]),
        '### Timeline: fixed monster Lv2, no items, evolve immediately when eligible',
        'Eligibility columns mean requirements met (including completed transitions), not an API action still available after evolution.',
        table(['Wins', 'Stage', 'Level', 'EXP', 'Bond', 'Gold', 'MOKORI met', 'NEBLA met'], [[r[k] for k in ['wins','stage','level','exp','bond','gold','mokori_requirements_met','nebla_requirements_met']] for r in data['timeline_fixed_level2']]),
        '### Battle Count: uniform Lv1/2/3 victories',
        table(['Target', 'Fresh best', 'Fresh expected', 'Fresh worst', 'Expected increment (carry)', 'From exact prior threshold: best / expected / worst'], [[r['level'], r['fresh_best'],r['fresh_expected'],r['fresh_worst'],r['increment_expected_with_carry'], f"{r['exact_threshold_best']} / {r['exact_threshold_expected']:.4f} / {r['exact_threshold_worst']}"] for r in data['battle_counts']]),
        '### Gold Economy: no spending, first threshold crossing',
        table(['Milestone','Gold range','Potion quantity','Berry quantity','Charm quantity'], [[r['milestone'],f"{r['gold_min']}–{r['gold_max']}"] + [f"{r['items'][code][0]}–{r['items'][code][1]}" for code in ['SMALL_POTION','BOND_BERRY','CAPTURE_CHARM']] for r in data['economy']]),
        '### Scenario Comparison: 100 opportunities',
        table(['Scenario','Wins','Stage','Level','EXP','Bond','Gold','MOKORI opportunity','NEBLA opportunity (continued)'], [[name]+[r[k] for k in ['wins','stage','level','exp','bond','gold']]+[r['evolution_opportunity']['MOKORI'],data['scenario_nebla_opportunity'][name]] for name,r in data['scenarios_100_opportunities'].items()]),
        '### Sensitivity Analysis: no Berry, independent hypothetical Bond rolls',
        table(['Model','E[Bond at Lv6]','E[wins MOKORI]','E[wins NEBLA]','P[Bond locked at Lv6]'], [[name,r['expected_bond_at_lv6'],r['mokori']['expected_wins'],r['nebla']['expected_wins'],r['nebla']['probability_locked_at_level']] for name,r in data['sensitivity'].items()]),
        '<!-- END GENERATED ANALYSIS -->']
    return '\n\n'.join(parts)+'\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--markdown', action='store_true')
    args = parser.parse_args()
    result = analysis()
    print(markdown(result) if args.markdown else json.dumps(result, indent=2, sort_keys=True), end='\n')
