"""Fail-closed merge eligibility. This module never merges or approves a PR."""
import argparse
import json
from pathlib import Path
from codex_followup import API, POLICY, protected
import pr_pipeline


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


def collect(api, pr_number):
    # A model report cannot supply release/protection/approval evidence. Unknown
    # controls remain blocked until a trusted, exact-HEAD evidence adapter exists.
    pr = api.get(f'pulls/{pr_number}')
    head = pr['head']['sha']
    files = api.pages(f'pulls/{pr_number}/files')
    complete = len(files) == pr['changed_files']
    return {'head': head, 'pr': pr_number,
            'files': [item['filename'] for item in files] if complete else [],
            'ci': {'head': head, 'status': pr_pipeline.ci(api, head)['status']},
            'review': {'head': head, 'status': 'NOT_VERIFIED'},
            'releaseGate': {'head': head, 'status': 'NOT_VERIFIED'},
            'stackDependencies': {'head': head, 'status': 'NOT_VERIFIED'},
            'branchProtection': {'head': head, 'status': 'NOT_VERIFIED'},
            'productionApproval': {'head': head, 'status': 'NOT_VERIFIED'},
            'repairBudget': {'head': head, 'status': 'NOT_VERIFIED'}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, help='Local fixture only; never authorization')
    parser.add_argument('--repo')
    parser.add_argument('--pr', type=int)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    evidence = json.loads(args.evidence.read_text()) if args.evidence else collect(API(args.repo), args.pr)
    args.output.write_text(json.dumps({'evidence': evidence, 'gate': decide(evidence)}, indent=2))
