"""Sequential local gate with resource evidence; never terminates other sessions.
Existing validators and assertions run unchanged. Interruption is INCOMPLETE.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    env = dict(os.environ)
    env['CARGO_BUILD_JOBS'] = '2'
    command = ['python3', 'scripts/validate_alpha_release.py', '--output', str(output/'release')]
    began = time.monotonic()
    result = {'head': head, 'command': command, 'status': 'INCOMPLETE', 'exitCode': None,
              'timeoutSeconds': None, 'parallelGatesInThisSession': 1,
              'scope': 'Existing release runner; no validator replacement, no skipped assertions'}
    with (output/'console.log').open('w') as log, (output/'resources.jsonl').open('w') as stats:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        try:
            while process.poll() is None:
                snapshot = subprocess.check_output(['ps', '-Ao', 'pid,ppid,%cpu,rss,etime,command'], text=True)
                rows = [line for line in snapshot.splitlines() if any(word in line for word in
                        ['unittest discover', 'validate_alpha_release', 'cargo ', 'GradleDaemon'])]
                stats.write(json.dumps({'seconds': round(time.monotonic()-began, 1), 'processes': rows})+'\n')
                stats.flush()
                time.sleep(30)
            result['exitCode'] = process.returncode
            result['status'] = 'PASS' if process.returncode == 0 else 'FAIL'
        except KeyboardInterrupt:
            os.killpg(process.pid, signal.SIGINT)
            process.wait()
            result.update(status='INCOMPLETE', exitCode=process.returncode, reason='SIGINT')
        finally:
            result['seconds'] = round(time.monotonic()-began, 2)
            (output/'run-result.json').write_text(json.dumps(result, indent=2)+'\n')
    return 0 if result['status']=='PASS' else 1

if __name__ == '__main__':
    raise SystemExit(main())
