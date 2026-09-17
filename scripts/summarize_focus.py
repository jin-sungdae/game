#!/usr/bin/env python3
"""Summarize one fresh audit directory; never merge historical runs."""
import argparse
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('bundle', type=Path)
parser.add_argument('report', type=Path)
parser.add_argument('manifest', type=Path, help='bundle manifest captured before tests')
args = parser.parse_args()
expected = json.loads(args.manifest.read_text())
actual = {str(p.relative_to(args.bundle)): hashlib.sha256(p.read_bytes()).hexdigest()
          for p in sorted(args.bundle.rglob('*')) if p.is_file()}
report = json.loads(args.report.read_text())
runs = report['runs']
summary = {
    'artifactUnchanged': actual == expected,
    'artifactFilesSha256': actual,
    'requestedRuns': report['requestedRuns'],
    'completedRuns': len(runs),
    'passRuns': sum(r['pass'] for r in runs),
    'applicationActivations': sum(r['appActivations'] for r in runs),
    'keyWindows': sum(r['keyWindows'] for r in runs),
    'foregroundChangeRuns': sum(r['foregroundChanged'] for r in runs),
    'abnormalOrUnconfirmedExits': sum(r['exitCode'] != 0 or r['timedOut'] or not r['exitSeen'] for r in runs),
}
summary['startupAcceptance'] = (actual == expected and len(runs) >= 20
    and all(r['pass'] for r in runs) and report.get('mode', 'normal') == 'normal')
print(json.dumps(summary, indent=2))
