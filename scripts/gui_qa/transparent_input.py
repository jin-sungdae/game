#!/usr/bin/env python3
"""QA-only manual transparent-input trials, reusing the #54 environment/launch/recorder.

No event injection, user-window mutation, AX text collection, or replacement panel.
preflight: compile/read metadata only; BLOCKED never launches app or receiver.
run: launch an isolated production bundle via run.py, then a QA-owned receiver.
Manually select the receiver and wait for READY before clicking the supplied point.
Each run is ONE gesture. Inspect the captured production-window frame before review.
review: attach an explicit human coordinate classification; never bypass missing evidence.
Artifacts must be outside the checkout. Requires the existing JAVA_HOME/PG_BIN setup.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess as sp
import sys
import time

from environment import compile_probe, prepare, observe, gate, fingerprint, verify_contract
from cleanup_environment import cleanup, identity
from input_evidence import analyze_trial

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PROFILE = HERE / 'profiles/moa.json'
BLOCKED = 'GUI_ENVIRONMENT_BLOCKED'


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def read_rows(path, final=False):
    rows = []
    if path.exists():
        lines = path.read_text().splitlines(keepends=True)
        for index, line in enumerate(lines):
            if not line.endswith('\n') and index == len(lines)-1 and not final:
                continue  # Only an unfinished final flush can be deferred.
            rows.append(json.loads(line))
    return rows


def output_directory(path):
    path = path.resolve()
    if path == ROOT or ROOT in path.parents:
        raise ValueError('Artifacts must be outside the checkout')
    path.mkdir(parents=True, exist_ok=False)
    return path


def preflight(root, countdown):
    probe = root / 'environment-probe'
    compile_probe(probe)
    result = prepare(probe, json.loads(PROFILE.read_text()), root / 'preflight.json', countdown)
    return probe, result


def sanitized_environment(sample, luma_windows, receiver_id):
    """Exclude only exact session-owned IDs, never an arbitrary process or window."""
    sample = dict(sample)
    actual = {w['id'] for w in sample.get('lumaWindows', [])}
    if (sample.get('lumaProcessCount') != 1 or not luma_windows
            or actual != set(luma_windows)):
        raise ValueError('LUMA identity/window inventory changed')
    sample['lumaProcessCount'] = 0
    sample['lumaWindows'] = []
    sample['obstacles'] = [w for w in sample['obstacles'] if w['id'] != receiver_id]
    return sample


def native_snapshot(helper, pid):
    return json.loads(sp.check_output([str(helper), 'observe', str(pid)], text=True, timeout=5))


def stop_owned(child):
    # Popen ownership, never kill an arbitrary PID or a user's existing app.
    if child is not None and child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=8)
        except sp.TimeoutExpired:
            child.kill()
            child.wait(timeout=5)


def parse_luma(text, action_start):
    actions = []
    audits = []
    offset = 0
    for line in text.splitlines(keepends=True):
        if line.startswith('LUMA_AUDIT '):
            try:
                audits.append(json.loads(line[len('LUMA_AUDIT '):]))
            except ValueError:
                raise ValueError('Malformed production focus audit')
        if offset >= action_start and line.startswith('[LUMA INPUT] '):
            actions.append(line[len('[LUMA INPUT] '):].strip())
        offset += len(line)
    return actions, audits


def capture_frames(capture, start, end):
    rows = []
    for frame in capture['frames']:
        stamp = frame.get('captureWallTime')
        if type(stamp) not in (float, int) or not math.isfinite(stamp):
            raise ValueError('Capture clock correlation unavailable')
        if start <= stamp <= end:
            rows.append({**frame, 'observedWallTime': frame['wallTime'], 'wallTime': stamp})
    return rows


def owned_contains(frame, point):
    x, y, w, h = frame
    return x <= point[0] < x+w and y <= point[1] < y+h


def run_trial(args, root, probe, initial):
    session = root / 'session'
    cfg = {}
    receiver = recorder = None
    files = []
    trial = {'version': 1, 'kind': args.kind, 'preflight': {'status': initial['status']},
             'coordinate': {'x': args.x, 'y': args.y, 'classification': args.kind,
                            'visualVerified': False},
             'events': [], 'actions': [], 'focus': {'complete': False, 'activations': 0, 'keyWindows': 0},
             'recording': {'complete': False, 'windowId': 0, 'frames': []},
             'identity': {}, 'interval': {'start': 0, 'end': 0},
             'coverage': {'complete': False, 'geometryStable': False, 'receiverFrontmost': False, 'monitorInstalled': False},
             'expectedAction': args.action, 'expectedButton': args.button, 'completed': False, 'runtimeSafe': False}
    try:
        if initial['status'] != 'READY':
            return trial  # No launch/compile receiver on BLOCKED.
        bundle = args.bundle.resolve()
        executable = bundle / 'Contents/MacOS/luma-spike'
        if not executable.is_file():
            raise ValueError('Expected production bundle Contents/MacOS/luma-spike')
        trial['provenance'] = {'sourceHead': sp.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                               'bundleSHA256': hashlib.sha256(executable.read_bytes()).hexdigest(),
                               'bundleRevisionDeclared': args.bundle_revision,
                               'productionContractMatches': verify_contract()}
        if not trial['provenance']['productionContractMatches']:
            raise ValueError('Production contract changed')
        # Existing isolated database/server launcher. It reruns preflight before app launch.
        sp.run([sys.executable, str(HERE/'run.py'), '--bundle', str(bundle), '--output', str(session),
                '--environment-profile', str(PROFILE), '--capture-only', '--keep-running'], check=True)
        cfg = json.loads((session/'session.json').read_text())
        pid = cfg['appPid']
        helper = root/'input-receiver'
        sp.run(['clang', '-fobjc-arc', '-framework', 'AppKit', '-framework', 'ApplicationServices',
                str(HERE/'input_receiver.m'), '-o', str(helper)], check=True)
        record_bin = root/'record-window'
        sp.run(['swiftc', '-parse-as-library', str(HERE/'record_window.swift'), '-o', str(record_bin)], check=True)
        print('Manually prepare the intended LUMA character/menu. Keep the target panel open throughout the trial; Close is not a supported button trial. Then press Enter.', flush=True)
        input()
        snap = native_snapshot(helper, pid)
        target = next(w for w in snap['windows'] if w.get('label') == args.window)
        print('Actual production target (AppKit x/y/width/height):', target['frame'], flush=True)
        if args.x is None:
            args.x, args.y = map(float, input('Enter the actual test point as global AppKit x y: ').split())
        if not all(math.isfinite(v) for v in (args.x,args.y)):
            raise ValueError('Non-finite coordinate')
        trial['coordinate'].update(x=args.x, y=args.y)
        if args.expected_target is not None:
            trial['expectedTarget'] = args.expected_target
        if not owned_contains(target['frame'], (args.x, args.y)):
            raise ValueError('Requested point is not inside the actual production panel')
        # Receiver uses only the existing primary visible frame; no unrelated window changes.
        env = observe(probe)
        f = env['visibleFrame']
        frame = [f[k] for k in ('x', 'y', 'w', 'h')]
        if not owned_contains(frame, (args.x, args.y)):
            raise ValueError('Point is outside receiver coverage')
        log = (root/'receiver.jsonl').open('w'); files.append(log)
        receiver = sp.Popen([str(helper), str(pid), *map(str, frame), str(args.seconds+60)], stdout=log)
        deadline = time.monotonic()+5
        ready = None
        while time.monotonic() < deadline:
            ready = next((r for r in read_rows(root/'receiver.jsonl') if r.get('type') == 'ready'), None)
            if ready: break
            if receiver.poll() is not None: raise RuntimeError('receiver exited before ready')
            time.sleep(.05)
        if not ready or ready['pid'] != receiver.pid or not ready.get('monitorInstalled'):
            raise RuntimeError('No owned receiver identity')
        receiver_id = ready['windowId']
        print('Select ONLY the QA receiver manually, then press Enter here. Do not click the test point yet.', flush=True)
        input()
        print('Return focus to the QA receiver during the countdown. Test starts only after READY.', flush=True)
        time.sleep(args.countdown)
        checks = []
        in_trial = False
        def sample():
            raw = observe(probe)
            current = native_snapshot(helper, pid)
            windows = {w['id'] for w in current['windows']}
            if current['frontPid'] != receiver.pid:
                raise ValueError('QA receiver is not frontmost')
            owned = next((w for w in current['windows'] if w['id'] == target['id']), None)
            frame_valid = owned and (owned['frame'] == target['frame'] or (in_trial and args.kind == 'drag' and owned['frame'][2:] == target['frame'][2:]))
            if not frame_valid:
                raise ValueError('Target geometry changed; prepare a new trial')
            clean = sanitized_environment(raw, windows, receiver_id)
            if fingerprint(clean) != initial['fingerprint']:
                raise ValueError('External desktop geometry changed')
            checks.append(current)
            return clean
        stable = gate(sample, json.loads(PROFILE.read_text()))
        save(root/'ready-gate.json', stable)
        if stable['status'] != 'READY':
            trial['preflight'] = {'status': BLOCKED}
            return trial
        recording_dir = root/'frames'
        record_log = (root/'record.log').open('w'); files.append(record_log)
        recorder = sp.Popen([str(record_bin), str(pid), str(args.seconds+5), str(recording_dir), args.window], stdout=record_log, stderr=record_log)
        # No input is requested until recording has produced actual frames.
        deadline = time.monotonic()+10
        while time.monotonic() < deadline:
            if list(recording_dir.glob('frame-*.png')): break
            if recorder.poll() is not None: raise RuntimeError('recording failed')
            time.sleep(.1)
        else: raise RuntimeError('No actual recorded frames')
        sample()
        app_log = session/'app.log'
        action_start = len(app_log.read_text())
        start = time.time()
        in_trial = True
        trial['coordinate']['panelFrame'] = dict(zip(('x','y','width','height'), target['frame']))
        trial['interval']['start'] = start
        trial['identity'] = {'lumaPid': pid, 'lumaWindowId': target['id'],
                             'receiverPid': receiver.pid, 'receiverWindowId': receiver_id}
        action_rows = []
        action_seen = 0
        print(f'READY: perform exactly ONE {args.kind} gesture at AppKit point ({args.x}, {args.y}) in the next {args.seconds}s.', flush=True)
        runtime_safe = True
        until = time.monotonic()+args.seconds
        while time.monotonic() < until:
            if receiver.poll() is not None or recorder.poll() is not None:
                raise RuntimeError('Observer/recorder stopped during trial')
            if identity(pid) != cfg['appPidIdentity']:
                raise RuntimeError('Production process identity changed')
            rows = read_rows(root/'receiver.jsonl')
            heartbeat = next((r for r in reversed(rows) if r.get('type') == 'heartbeat'), None)
            if not heartbeat or time.time() - heartbeat.get('wallTime', 0) > 0.5:
                raise RuntimeError('Receiver observation coverage lost')
            if heartbeat.get('windowId') != receiver_id or heartbeat.get('frame') != ready['frame']:
                raise RuntimeError('Receiver geometry changed')
            try:
                sample()
            except ValueError:
                runtime_safe = False
                break
            actions, _ = parse_luma(app_log.read_text(), action_start)
            action_rows.extend({'kind': kind, 'wallTime': time.time(), 'timestampSource': 'log-observed'} for kind in actions[action_seen:])
            action_seen = len(actions)
            time.sleep(.1)
        end = time.time()
        print('Trial ended. No further test input.', flush=True)
        # Drain pending messages while still validating geometry/focus/process coverage.
        for _ in range(2):
            time.sleep(.1)
            sample()
            tail = read_rows(root/'receiver.jsonl')
            beat = next((r for r in reversed(tail) if r.get('type') == 'heartbeat'), None)
            if not beat or time.time()-beat['wallTime'] > .5 or identity(pid) != cfg['appPidIdentity']:
                raise RuntimeError('Tail observation coverage lost')
        end = time.time()
        actions, audits = parse_luma(app_log.read_text(), action_start)
        action_rows.extend({'kind': kind, 'wallTime': end, 'timestampSource': 'log-observed'} for kind in actions[action_seen:])
        trial['interval']['end'] = end
        trial['actions'] = action_rows
        trial['events'] = [r for r in read_rows(root/'receiver.jsonl') if r.get('type') == 'input' and start <= r['wallTime'] <= end]
        trial['coverage'] = {'complete': runtime_safe, 'geometryStable': runtime_safe,
                             'receiverFrontmost': runtime_safe and all(s['frontPid'] == receiver.pid for s in checks),
                             'monitorInstalled': ready['monitorInstalled']}
        own_audits = [r for r in audits if r.get('pid') == pid]
        trial['focus'] = {'complete': any(r.get('event') == 'before-tauri' for r in own_audits) and runtime_safe,
                          'activations': max((r.get('activations', 0) for r in own_audits), default=0),
                          'keyWindows': max((r.get('keyWindows', 0) for r in own_audits), default=0)}
        (recording_dir/'stop').touch()
        recorder.wait(timeout=10)
        capture = json.loads((recording_dir/'frames.json').read_text())
        trial['recording'] = {'complete': recorder.returncode == 0 and capture['windowId'] == target['id'] and len(capture['frames']) >= 2,
                              'windowId': capture['windowId'], 'frames': capture_frames(capture, start, end)}
        trial['completed'] = True
        trial['runtimeSafe'] = runtime_safe
        if not runtime_safe: trial['preflight'] = {'status': BLOCKED}
    except (OSError, ValueError, KeyError, StopIteration, RuntimeError, EOFError, KeyboardInterrupt, sp.SubprocessError) as exc:
        trial['error'] = str(exc)
        if (session/'preflight.json').exists() and json.loads((session/'preflight.json').read_text()).get('status') == BLOCKED:
            trial['preflight'] = {'status': BLOCKED}
        if 'geometry' in str(exc) or 'frontmost' in str(exc): trial['preflight'] = {'status': BLOCKED}
    finally:
        if cfg.get('appPid') and (session/'app.log').exists():
            try:
                _, audit_rows = parse_luma((session/'app.log').read_text(), 0)
                own = [r for r in audit_rows if r.get('pid') == cfg['appPid']]
                for key in ('activations','keyWindows'):
                    trial['focus'][key] = max((r.get(key, 0) for r in own), default=trial['focus'][key])
            except (OSError, ValueError, TypeError):
                trial['focus']['complete'] = False
        stop_owned(recorder)
        stop_owned(receiver)
        if (root/'receiver.jsonl').exists():
            try:
                final_rows = read_rows(root/'receiver.jsonl', final=True)
                begin, finish = trial['interval']['start'], trial['interval']['end']
                trial['events'] = [r for r in final_rows if r.get('type') == 'input' and begin <= r['wallTime'] <= finish]
            except (ValueError, KeyError):
                trial['coverage']['complete'] = False
                trial['error'] = 'Incomplete receiver event log'
        for f in files: f.close()
        if (session/'session.json').exists():
            try:
                trial['cleanup'] = cleanup(session)
            except (OSError, ValueError, sp.SubprocessError) as exc:
                trial['cleanup'] = {'status': 'NOT_VERIFIED', 'processes': [], 'userWindowMutations': 0}
                trial['error'] = 'Cleanup needs review: '+str(exc)
    return trial


def review(args):
    path = args.evidence.resolve()
    trial = json.loads(path.read_text())
    capture = trial['recording']
    selected = next((f for f in capture['frames'] if f['file'] == args.frame), None)
    if not selected: raise ValueError('Frame is not in this capture')
    trial['coordinate']['captureDimensions'] = {'width': selected['width'], 'height': selected['height']}
    frame_path = path.parent/'frames'/args.frame
    if frame_path.parent.resolve() != (path.parent/'frames').resolve() or not frame_path.is_file():
        raise ValueError('Missing or unsafe frame path')
    trial['coordinate'].update(visualVerified=True, frameFile=args.frame, frameWallTime=selected['wallTime'])
    if args.alpha is not None:
        trial['coordinate']['alphaEvidence'] = {'verified': True, 'alpha': args.alpha}
    panel = trial['coordinate'].get('panelFrame')
    if panel:
        trial['coordinate']['capturePoint'] = {
            'x': (trial['coordinate']['x']-panel['x'])*selected['width']/panel['width'],
            'y': (panel['y']+panel['height']-trial['coordinate']['y'])*selected['height']/panel['height']}
        print('Reviewed point in captured image (top-left origin):', trial['coordinate']['capturePoint'])
    trial['coordinate']['reviewMethod'] = 'human inspected captured production frame at the recorded point'
    trial['coordinate']['frameSHA256'] = hashlib.sha256(frame_path.read_bytes()).hexdigest()
    save(path.parent/'reviewed-evidence.json', trial)
    result = analyze_trial(trial)
    save(path.parent/'reviewed-result.json', result)
    print(json.dumps(result))
    return result_exit(result)


def result_exit(result):
    return {'PASS':0, 'FAIL':1, BLOCKED:2, 'NOT_VERIFIED':3}[result['status']]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='command', required=True)
    for name in ('preflight', 'run'):
        q = sub.add_parser(name)
        q.add_argument('--output', type=Path, required=True)
        q.add_argument('--countdown', type=int, default=5)
        if name == 'run':
            q.add_argument('--bundle', type=Path, required=True)
            q.add_argument('--bundle-revision', required=True, help='Declared build SHA, recorded separately from binary hash')
            q.add_argument('--kind', choices=['transparent','character','boundary','button','drag'], required=True)
            q.add_argument('--window', choices=['moa','pip','interaction'], default='moa')
            q.add_argument('--x', type=float, help='Actual AppKit global point, not guessed image center')
            q.add_argument('--y', type=float)
            q.add_argument('--button', type=int, choices=[0,1,2], default=0, help='0 left, 1 right, 2 middle; all gesture events must match')
            q.add_argument('--action', choices=['drag','interact','encounter','attack','capture','evolution','battle','ignore','refresh','dex'])
            q.add_argument('--expected-target', choices=['receiver','luma'], help='Declare boundary expectation BEFORE recording; omitted means characterization only')
            q.add_argument('--seconds', type=int, default=8)
    q = sub.add_parser('review', help='Explicitly confirm classification ONLY after inspecting the actual captured point')
    q.add_argument('--evidence', type=Path, required=True)
    q.add_argument('--frame', required=True)
    q.add_argument('--confirm-visual-classification', action='store_true', required=True,
                   help='Confirm point class in the actual frame within 100ms before mouse-down; no screenshot-only PASS')
    q.add_argument('--alpha', type=float)
    args = p.parse_args(argv)
    if args.command == 'review':
        return review(args)
    if not 3 <= args.countdown <= 60: p.error('countdown must be 3..60')
    if args.command == 'run':
        if (args.x is None) != (args.y is None): p.error('x/y must be supplied together')
        if not 5 <= args.seconds <= 60 or (args.x is not None and not all(math.isfinite(v) for v in (args.x,args.y))):
            p.error('finite coordinates and 5..60 seconds required')
        if args.kind == 'button' and args.action is None: p.error('button requires explicit --action')
        if args.action is None: args.action = 'interact' if args.window == 'pip' else 'drag'
    root = output_directory(args.output)
    probe, initial = preflight(root, args.countdown)
    if initial['status'] != 'READY' or args.command == 'preflight':
        result = {'status': BLOCKED if initial['status'] != 'READY' else 'NOT_VERIFIED',
                  'reason': initial['reason'], 'inputInjected': False, 'userWindowMutations': 0}
    else:
        trial = run_trial(args, root, probe, initial)
        save(root/'evidence.json', trial)
        result = analyze_trial(trial)
    save(root/'result.json', result)
    print(json.dumps(result))
    return result_exit(result)


if __name__ == '__main__':
    raise SystemExit(main())
