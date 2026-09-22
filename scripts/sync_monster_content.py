#!/usr/bin/env python3
"""Materialize server rarity defaults into the desktop/Dex projection; no runtime formula."""
import argparse
import json
from pathlib import Path

root = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--check', action='store_true')
args = parser.parse_args()
policy = json.loads((root / 'server/src/main/resources/content/rarity-defaults.json').read_text())
path = root / 'src/entities/monster-dex.json'
content = json.loads(path.read_text())
for monster in content:
    if monster['alphaCandidate']:
        expected = policy[monster['rarity']]
        if args.check:
            for key, value in expected.items():
                if monster[key] != value:
                    raise SystemExit(f"Stale Domain projection: {monster['monsterCode']}.{key}")
        else:
            monster.update(expected)
if not args.check:
    path.write_text(json.dumps(content, indent=2) + '\n')
