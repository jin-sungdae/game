"""Fail-closed merge eligibility. This module never merges or approves a PR."""
import argparse
import json
from pathlib import Path
from codex_followup import POLICY, protected


def decide(evidence):
    reasons = []
    head = evidence.get('head')
    review = evidence.get('review', {})
    if not head or review.get('head') != head or review.get('status') != 'PASS':
        reasons.append('INDEPENDENT_REVIEW_REQUIRED')
    for field in ('ci', 'releaseGate', 'stackDependencies', 'branchProtection', 'productionApproval', 'repairBudget'):
        item = evidence.get(field, {})
        if item.get('head') != head or item.get('status') != 'PASS':
            reasons.append(field.upper() + '_NOT_VERIFIED')
    files = evidence.get('files')
    if not files or any(protected(path) or path.startswith(('src/', 'server/')) for path in files):
        reasons.append('HUMAN_REVIEW_REQUIRED')
    return {'head': head, 'status': 'FAIL' if reasons else 'PASS', 'reasons': reasons,
            'dryRun': True, 'mergeExecuted': False,
            'automaticMergeEnabled': POLICY['automaticMerge']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(decide(json.loads(args.evidence.read_text())), indent=2))
