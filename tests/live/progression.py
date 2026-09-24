"""Explicit isolated test server only; see docs/companion-progression-v02.md.
Run phases in separate processes with actual Spring restarts between phases.
"""
import json
import os
import sys
import urllib.request
from urllib.parse import urlparse

base = os.environ['LUMA_PROGRESSION_TEST_URL']
assert urlparse(base).hostname in ('127.0.0.1', 'localhost')
assert os.environ.get('LUMA_ISOLATED_TEST') == '1'

def call(path, post=False, body=None):
    data = json.dumps(body).encode() if body is not None else (b'' if post else None)
    request = urllib.request.Request(base+'/api/v1'+path, data=data,
                                     headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.load(response)

def snapshot():
    b = call('/game/bootstrap')
    c = b['activeCompanion']
    return b, (c['evolutionStage'], c['level'], c['exp'], c['bond'])

phase = sys.argv[1]
if phase == 'reward':
    assert snapshot()[1] == (2, 5, 1480, 10)
    e = call('/encounters', True)
    b = call('/encounters/'+e['encounterId']+'/battle', True)
    while b['status'] == 'ACTIVE':
        b = call('/battles/'+b['battleId']+'/attack', True)
    assert b['status'] == 'VICTORY'
    assert b['reward'] == {'gold': 10, 'exp': 20, 'bond': 0}
    call('/encounters/'+e['encounterId']+'/ignore', True)
    assert snapshot()[1] == (2, 6, 1500, 10)
    assert call('/companions/active/interact', True)['bondDelta'] == 1
    assert snapshot()[1] == (2, 6, 1500, 11)
    assert call('/companions/active/evolution')['status'] == 'LOCKED'
elif phase == 'berry-evolve':
    assert snapshot()[1] == (2, 6, 1500, 11)
    assert call('/companions/active/evolution')['status'] == 'LOCKED'
    call('/shop/purchases', True, {'itemCode': 'BOND_BERRY', 'quantity': 1})
    item = call('/inventory/items/BOND_BERRY/use', True)
    assert (item['bondBefore'], item['bondAfter']) == (11, 12)
    assert call('/companions/active/evolution')['status'] == 'AVAILABLE'
    before = snapshot()[0]
    result = call('/companions/active/evolve', True)
    assert result['result'] == 'EVOLVED'
    assert snapshot()[1] == (3, 6, 1500, 12)
    assert result['bootstrap']['player'] == before['player']
    assert result['bootstrap']['activeCompanion']['evolutionName'] == 'NEBLA'
elif phase == 'restored':
    assert snapshot()[1] == (3, 6, 1500, 12)
    assert snapshot()[0]['activeCompanion']['evolutionName'] == 'NEBLA'
    assert call('/companions/active/evolve', True)['result'] == 'ALREADY_EVOLVED'
else:
    raise ValueError('unknown phase')
print(json.dumps({'phase': phase, 'result': 'PASS', 'bootstrap': snapshot()[0]}))
