"""Restore the newest pipeline checkpoint, including failed runs with a published artifact.
Never fall back to older state on expiry/corruption: that could regenerate processed HEADs.
"""
import argparse
import json
from pathlib import Path
import subprocess
from pr_pipeline import GitHub

NAME = 'luma-pr-pipeline'


def restore(api, destination):
    workflow = api.get('actions/workflows/luma-pr-watch-15min.yml')
    default = api.get('')['default_branch']
    artifacts = api.pages(f'actions/artifacts?name={NAME}', 'artifacts')
    for artifact in sorted(artifacts, key=lambda a: (a['created_at'], a['id']), reverse=True):
        run = api.get(f'actions/runs/{artifact["workflow_run"]["id"]}')
        if run['workflow_id'] != workflow['id'] or run['event'] not in ('schedule', 'workflow_dispatch', 'pull_request_target', 'workflow_run'):
            continue
        if run['event'] == 'pull_request_target':
            if not run.get('pull_requests') or any(p['base']['ref'] != default for p in run['pull_requests']):
                raise RuntimeError('Unverified checkpoint base; manual recovery required')
        elif run['head_branch'] != default:
            raise RuntimeError('Non-default checkpoint source; manual recovery required')
        if artifact['expired']:
            raise RuntimeError('Checkpoint expired: explicit recovery required, do not bootstrap again')
        subprocess.run(['gh', 'run', 'download', str(run['id']), '--repo', api.repo,
                        '--name', NAME, '--dir', str(destination)], check=True, timeout=120)
        state = destination / 'state.json'
        value = json.loads(state.read_text())
        if value.get('version') != 1 or value.get('repository') != api.repo:
            raise ValueError('Checkpoint invalid: explicit recovery required')
        return state
    # Workflow requires an existing checkpoint except an explicit first-deployment bootstrap.
    return None


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--require-existing', action='store_true')
    args = parser.parse_args()
    state = restore(GitHub(args.repo), args.destination)
    if args.require_existing and state is None:
        raise RuntimeError('Required checkpoint missing: fail closed')
    print(state or '')
