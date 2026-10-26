"""Loopback control plane. One process, one operation; no new durable queue/database."""
import fcntl
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import signal
import tempfile
import threading
from urllib.parse import urlsplit

from engine import Engine, ROOT, normalize

TOKEN = secrets.token_urlsafe(32)
STATE = {'phase': 'STOPPED', 'github': 'NOT_CHECKED', 'codex': 'NOT_CHECKED',
         'chatgpt': 'BLOCKED_POLICY / 로그인 상태 NOT_VERIFIED', 'pr': None, 'head': None,
         'ci': 'NOT_RUN', 'analysis': 'NOT_RUN', 'codexRun': 'NOT_RUN', 'tests': 'NOT_RUN',
         'merge': {'eligible': False, 'automaticMerge': False}, 'nextTask': 'NOT_RUN',
         'prompt': '', 'repairPrompt': '', 'logs': [], 'busy': False}
mutex = threading.RLock()
halt = threading.Event()
watch = threading.Event()
selected = None
automatic = False
engine = None


def log(message):
    with mutex:
        STATE['logs'] = (STATE['logs'] + [message])[-150:]


def work(action, payload):
    try:
        if action in ('start', 'resume', 'refresh'):
            STATE.update(engine.auth())
            number = payload.get('pr')
            if number is not None and (type(number) is not int or number < 1): raise ValueError('INVALID_PR')
            result, prs = engine.snapshot(number)
            STATE['prs'] = prs
            log(f"PR {result['observed']}개 조회 / 변경 {result['changes']}개")
            if number is not None:
                STATE['prompt'] = engine.inspect(number)
                STATE.update(pr=number, head=engine.analysis['head'], ci=engine.analysis['ci']['status'], analysis='NOT_RUN', merge={'eligible': False, 'automaticMerge': False})
            STATE['phase'] = 'WATCHING'
            if automatic:
                state = __import__('engine').follow.Store(engine.api).load()
                chosen = next((p for p in prs if p['state']=='open' and p.get('ci',{}).get('status') in ('PASS','FAIL')
                    and str(p['number']) in state['prs']
                    and f"analysis:{p['number']}:{p['head']}" not in state['runs']), None)
                if chosen is None:
                    STATE['nextTask']={'status':'BLOCKED','reason':'NO_NEW_ENROLLED_HEAD'}
                else:
                    STATE['prompt']=engine.inspect(chosen['number'])
                    STATE.update(pr=chosen['number'],head=engine.analysis['head'],ci=engine.analysis['ci']['status'])
                    STATE['codexRun']='RUNNING';STATE['analysis']=engine.analyze_codex();STATE['codexRun']='COMPLETED'
                    verdict=engine.review['status']
                    if verdict=='CHANGES_REQUIRED':
                        STATE['repairResult']=engine.repair()
                        STATE['phase']='WAITING_NEW_HEAD_CI'
                    elif verdict=='PASS':
                        STATE['tests']=engine.validate_release();STATE['merge']=engine.gate();STATE['phase']='HUMAN_MERGE_GATE'
                    else:
                        halt.set();watch.clear();STATE['phase']=verdict

        elif action == 'analyze':
            STATE['codexRun'] = 'RUNNING'
            STATE['analysis'] = engine.analyze_codex()
            STATE['codexRun'] = 'COMPLETED'
            STATE['phase'] = 'REVIEWED'
        elif action == 'manual':
            if engine.analysis is None: raise ValueError('SELECT_PR_FIRST')
            engine.review = normalize(payload.get('response', ''), STATE['head'])
            STATE['analysis'] = engine.review
            STATE['phase'] = 'REVIEWED_MANUAL_UNTRUSTED'
        elif action == 'repair':
            STATE['repairPrompt'] = ('기존 PR #' + str(STATE['pr']) + ' / HEAD ' + str(STATE['head']) + '\n'
                + json.dumps(engine.review, ensure_ascii=False) + '\n기존 변수명/메서드명 유지. scope 밖 수정·force push 금지. 관련 회귀 + Release Gate 필수.')
            STATE['repairResult']=engine.repair()
            STATE['phase']='REPAIR_FINISHED_REVIEW_REQUIRED'
        elif action == 'validate':
            STATE['tests']=engine.validate_release()
            STATE['phase']='VALIDATED'
        elif action == 'merge':
            STATE['merge']=engine.merge(payload.get('expectedHead'),payload.get('approval'))
            STATE['phase']='MERGED'
        elif action == 'gate':
            STATE['merge'] = engine.gate()
            STATE['phase'] = 'MERGE_GATE'
        elif action == 'next':
            STATE['nextTask'] = engine.next()
            STATE['phase'] = 'NEXT_TASK_REVIEW'
        else: raise ValueError('UNKNOWN_ACTION')
        if halt.is_set(): STATE['phase'] = 'PAUSED'
    except Exception as error:
        halt.set(); watch.clear()
        STATE['phase'] = 'PAUSED_ERROR'
        if STATE['codexRun'] == 'RUNNING': STATE['codexRun'] = 'FAILED_OR_CANCELLED'
        log(type(error).__name__ + ': ' + str(error)[:1000])
    finally:
        with mutex: STATE['busy'] = False


def dispatch(action, payload):
    global selected, automatic
    with mutex:
        if action in ('pause', 'stop'):
            halt.set(); watch.clear(); engine.cancel_process()
            STATE['phase'] = 'PAUSED' if action == 'pause' else 'STOPPED'
            return
        if STATE['busy']: raise ValueError('OPERATION_ALREADY_RUNNING')
        if action in ('start', 'resume', 'refresh'):
            halt.clear(); selected = payload.get('pr')
            if action!='refresh': automatic=payload.get('automatic') is True
            if action != 'refresh': watch.set()
        elif halt.is_set(): raise ValueError('RESUME_REQUIRED')
        STATE['busy'] = True; STATE['phase'] = action.upper()
        threading.Thread(target=work, args=(action, payload), daemon=True).start()


def watcher():
    while True:
        # Same 15-minute cadence as remote observer; no extra queue or background model calls.
        threading.Event().wait(900)
        if watch.is_set():
            try: dispatch('refresh', {'pr': selected})
            except ValueError: pass


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass
    def response(self, code, data, kind='application/json'):
        raw = data.encode() if isinstance(data, str) else json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', kind + '; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'")
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Length', str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def valid_host(self):
        return self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'
    def authorized(self):
        return self.valid_host() and hmac.compare_digest(self.headers.get('X-Luma-Token', ''), TOKEN)
    def do_GET(self):
        if not self.valid_host(): return self.response(403, {'error': 'HOST_REJECTED'})
        path = urlsplit(self.path).path
        assets = {'/': ('index.html', 'text/html'), '/ui.js': ('ui.js', 'application/javascript'), '/ui.css': ('ui.css', 'text/css')}
        if path in assets:
            file, kind = assets[path]
            return self.response(200, (ROOT/'tools/local-controller'/file).read_text(), kind)
        if path == '/state' and self.authorized():
            with mutex: return self.response(200, STATE)
        self.response(403, {'error': 'AUTH_REQUIRED'})
    def do_POST(self):
        origin = f'http://127.0.0.1:{self.server.server_port}'
        if not self.authorized() or self.headers.get('Origin') != origin:
            return self.response(403, {'error': 'ORIGIN_OR_TOKEN_REJECTED'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length <= 0 or length > 100000: raise ValueError('PAYLOAD_BOUND')
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict): raise ValueError('OBJECT_REQUIRED')
            dispatch(urlsplit(self.path).path.removeprefix('/'), payload)
            self.response(202, {'accepted': True})
        except (ValueError, TypeError) as error: self.response(409, {'error': str(error)})


def main():
    global engine
    # flock is released by the OS after crash; remote CAS lease is deliberately NOT cleared.
    directory = Path.home()/'Library/Application Support/LUMA/controller'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = (directory/'controller.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    run = Path(tempfile.mkdtemp(prefix='run-', dir=directory))
    engine = Engine(run, log, halt.is_set)
    STATE['evidenceDirectory']=str(run)
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    def shutdown(*_):
        halt.set(); engine.cancel_process()
        threading.Thread(target=server.shutdown, daemon=True).start()
    signal.signal(signal.SIGTERM, shutdown); signal.signal(signal.SIGINT, shutdown)
    threading.Thread(target=watcher, daemon=True).start()
    print(f'LUMA_CONTROLLER_URL=http://127.0.0.1:{server.server_port}/#{TOKEN}', flush=True)
    try: server.serve_forever()
    finally: server.server_close(); lock.close()


if __name__ == '__main__': main()
