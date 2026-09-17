"""Read-only CI summary. No PR text interpolation, credentials, dispatch or merge."""
import json
import os
import subprocess
from pathlib import Path


def human_paths(changes):
    protected = ('AGENTS.md', '.github/', 'docs/ARCHITECTURE.md', 'docs/GAME_DESIGN.md',
                 'docs/REVIEW_RULES.md', 'src-tauri/vendor/', 'src-tauri/native/',
                 'src-tauri/capabilities/', 'src-tauri/tauri.conf.json',
                 'src-tauri/src/overlay.rs', 'src-tauri/src/main.rs', 'scripts/ci/',
                 'package.json', 'package-lock.json', 'src-tauri/Cargo.', 'migrations/')
    flags = sorted({p for status, p in changes if p.startswith(protected)})
    if sum(status == 'D' for status, _ in changes) >= 20:
        flags.append('mass-deletion>=20')
    return flags


def result(needs, changes, event, run_id):
    jobs = ['desktop-static', 'macos-native', 'server-java']
    failed = [j for j in jobs if needs.get(j, {}).get('result') != 'success']
    pr = event['pull_request']
    flags = human_paths(changes)
    return {
        'kind': 'LUMA_REVIEW_RESULT', 'schema_version': 1,
        'status': 'FAIL' if failed else 'PASS', 'iteration': None,
        'auto_review_max_iterations': 3, 'automatic_dispatch': False,
        'pr': pr['number'], 'head_sha': pr['head']['sha'], 'base_sha': pr['base']['sha'],
        'run_id': run_id,
        'findings': [{'severity': 'BLOCKER', 'message': j + ' did not succeed'} for j in failed],
        'required_actions': ['Inspect failed job logs: ' + j for j in failed],
        'human_review_required': True, 'protected_paths': flags,
        'next_action': 'HUMAN_REVIEW_REQUIRED' if flags else ('FIX_REQUIRED' if failed else 'READY_FOR_HUMAN_REVIEW'),
        'checks': [
            {'name': 'desktop-static', 'classification': 'AUTOMATED', 'status': needs.get('desktop-static', {}).get('result', 'missing')},
            {'name': 'AppKit compile / Rust deterministic tests', 'classification': 'PLATFORM_REQUIRED', 'status': needs.get('macos-native', {}).get('result', 'missing')},
            {'name': 'Java 21 / PostgreSQL integration', 'classification': 'AUTOMATED', 'status': needs.get('server-java', {}).get('result', 'missing')},
            {'name': 'Real desktop focus / mouse / typing / visual overlay', 'classification': 'MANUAL_REQUIRED', 'status': 'NOT_RUN'},
        ],
    }


if __name__ == '__main__':
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    # Base SHA is data passed as a git argument, never shell source.
    base = event['pull_request']['base']['sha']
    head = event['pull_request']['head']['sha']
    raw = subprocess.check_output(['git', 'diff', '--no-renames', '--name-status', '-z', base, head]).decode().split('\0')
    changes = list(zip(raw[0:-1:2], raw[1:-1:2]))
    data = result(json.loads(os.environ['NEEDS_JSON']), changes, event, os.environ['GITHUB_RUN_ID'])
    Path('review-result.json').write_text(json.dumps(data, indent=2) + '\n')
    with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as f:
        f.write('## LUMA_REVIEW_RESULT\n\n```json\n' + json.dumps(data, indent=2) + '\n```\n')
    raise SystemExit(0 if data['status'] == 'PASS' else 1)
