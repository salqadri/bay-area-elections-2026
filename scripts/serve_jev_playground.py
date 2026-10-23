"""Local House-candidate Jev playground. Serves UI + same-origin run API on loopback.

python3 scripts/serve_jev_playground.py --jev-key-file /secure/path/key
No API credential reaches the browser. Runs never change published research.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import re
import threading
from urllib.parse import urlsplit, parse_qs
import uuid

from grade_gaza import (ROOT, DATASET, MODEL, DEFAULT_CRITERIA, candidates, build_state,
                        validate_questions, validate_response, jev_call, digest, dump, save, now)

ASSETS = ROOT / 'src/jev-playground'
BASELINE = ROOT / 'research/gaza-grading/house-all-focused-2026-10-23/results.json'
WORK = ROOT / '.research/jev-playground'


def row_id(position_id, candidate, roster):
    return digest(dump([position_id, candidate, roster]).encode())[:24]


def snapshot(data):
    races, rows = {}, []
    for p, c, roster in candidates(data, 'house-all'):
        state = build_state(p, c, data)
        races[p['id']] = {k: p.get(k) for k in ('id', 'office', 'jurisdiction', 'district_or_seat', 'ocd_division_id', 'counties')}
        races[p['id']]['state'] = state['state']
        rows.append({'id': row_id(p['id'], c['name'], roster), 'position_id': p['id'], 'candidate': c['name'],
                     'party': c.get('party'), 'roster': roster, 'state': state})
    return {'dataset_sha256': digest(dump(data).encode()), 'state_version': 'house-evidence-v3-focused',
            'publication_version': data['election']['publication_version'], 'races': list(races.values()), 'candidates': rows}


def stored_run(batch, current):
    rows = []
    for result in batch['results']:
        decision = batch.get('decisions', {}).get(result['request_sha256'])
        request = decision['request'] if decision else {'model': batch['model'], 'state': result.get('state', {}), 'questions': batch['questions']}
        if digest(dump(request).encode()) != result['request_sha256']:
            raise ValueError('Stored request hash does not match its content')
        if decision:
            validate_response(request['questions'], decision['response'])
        rows.append({'id': row_id(result['position_id'], result['candidate'], result['roster']),
                     'position_id': result['position_id'], 'candidate': result['candidate'],
                     'party': result.get('party'), 'roster': result['roster'], 'request': request,
                     'request_sha256': result['request_sha256'], 'response': decision['response'] if decision else None,
                     'status': 'error' if result.get('error') else 'complete', 'error': result.get('error'), 'revision': 0})
    return {'format': 'jev-playground-run/v1', 'id': 'stored-house-all-focused-2026-10-23', 'label': 'Stored results · Oct 23',
            'created_at': batch['run_on'], 'model': batch['model'], 'questions': batch['questions'], 'status': 'complete',
            'dataset_sha256': batch.get('dataset_sha256'), 'state_version': batch['state_version'],
            'races': current['races'], 'rows': rows, 'revision': 0, 'completed': len(rows),
            'errors': sum(r['status'] == 'error' for r in rows)}


class RunManager:
    def __init__(self, dataset_path=DATASET, work=WORK, key='', baseline=BASELINE, transport=jev_call, workers=3):
        self.dataset_path = Path(dataset_path); self.work = Path(work); self.key = key; self.baseline = Path(baseline)
        self.transport = transport; self.workers = workers; self.lock = threading.RLock(); self.jobs = {}; self.stops = {}
        self.active = None; self.work.mkdir(parents=True, exist_ok=True)

    def current(self):
        return snapshot(json.loads(self.dataset_path.read_text()))

    def bootstrap(self):
        current = self.current()
        batch = json.loads(self.baseline.read_text())
        baseline = stored_run(batch, current)
        return {'snapshot': current, 'baseline': baseline, 'questions': batch['questions'],
                'key_configured': bool(self.key), 'history': self.history()}

    def history(self):
        result = []
        for path in sorted((self.work / 'runs').glob('*/run.json'), reverse=True):
            run = json.loads(path.read_text())
            status = run['status']
            if run['id'] not in self.jobs and status in {'running', 'cancelling'}:
                status = 'interrupted'
            result.append({'id': run['id'], 'created_at': run['created_at'], 'status': status,
                           'completed': run['completed'], 'total': len(run['rows']), 'errors': run['errors'],
                           'scope': run.get('scope', 'all'), 'candidate': run['rows'][0]['candidate'] if run.get('scope') == 'candidate' else None})
        return result

    def _persist(self, run):
        save(self.work / 'runs' / run['id'] / 'run.json', run)

    def start(self, questions, candidate_id=None):
        validate_questions(questions)
        if candidate_id is not None and (not isinstance(candidate_id, str) or not candidate_id):
            raise ValueError('candidate_id must be a nonempty candidate ID')
        with self.lock:
            if self.active:
                raise RuntimeError('A run is already in progress; stop it or wait for completion')
            if not self.key:
                raise PermissionError('Start the local server with --jev-key-file or TYPESAFE_API_KEY')
            current = self.current(); questions = deepcopy(questions)
            targets = current['candidates']
            if candidate_id is not None:
                targets = [c for c in targets if c['id'] == candidate_id]
                if not targets:
                    raise ValueError('Selected candidate is no longer in the current active House roster. Reload the page.')
            run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + uuid.uuid4().hex[:8]
            rows = []
            for c in targets:
                request = {'model': MODEL, 'state': c['state'], 'questions': questions}
                rows.append({k: v for k, v in c.items() if k != 'state'} | {
                    'request': request, 'request_sha256': digest(dump(request).encode()), 'status': 'queued', 'revision': 0})
            run = {'format': 'jev-playground-run/v1', 'id': run_id, 'created_at': now(), 'model': MODEL,
                   'questions': questions, 'scope': 'candidate' if candidate_id is not None else 'all',
                   'dataset_sha256': current['dataset_sha256'], 'state_version': current['state_version'],
                   'races': current['races'], 'rows': rows, 'status': 'running', 'revision': 0, 'completed': 0, 'errors': 0}
            self.jobs[run_id] = run; self.active = run_id; self.stops[run_id] = threading.Event(); self._persist(run)
            initial = deepcopy(run)
            threading.Thread(target=self._execute, args=(run_id,), daemon=True).start()
            return initial

    def _execute(self, run_id):
        run = self.jobs[run_id]; stop = self.stops[run_id]
        def one(index):
            if stop.is_set():
                return index, {'status': 'cancelled'}
            row = run['rows'][index]
            try:
                response = self.transport(self.work / 'requests' / run_id, row['request'], self.key, force=True)
                validate_response(run['questions'], response)
                return index, {'status': 'complete', 'response': response, 'finished_at': now()}
            except PermissionError:
                stop.set()
                return index, {'status': 'error', 'error': 'Jev authentication failed. Check the local server key.', 'fatal': True}
            except Exception as error:
                # Never serialize provider bodies, credentials, headers or tracebacks.
                message = 'Jev did not return a valid response for this candidate.'
                if isinstance(error, ValueError):
                    message = 'Jev returned incomplete or invalid answers for the submitted questions.'
                return index, {'status': 'error', 'error': message}
        try:
            with ThreadPoolExecutor(max_workers=self.workers) as pool:
                futures = [pool.submit(one, i) for i in range(len(run['rows']))]
                for future in as_completed(futures):
                    index, update = future.result()
                    with self.lock:
                        run['revision'] += 1
                        run['rows'][index].update(update, revision=run['revision'])
                        run['completed'] = sum(r['status'] in {'complete', 'error'} for r in run['rows'])
                        run['errors'] = sum(r['status'] == 'error' for r in run['rows'])
                        self._persist(run)
            with self.lock:
                run['status'] = ('error' if any(r.get('fatal') for r in run['rows']) else 'cancelled') if stop.is_set() else 'complete'
        finally:
            with self.lock:
                run['finished_at'] = now(); run['revision'] += 1; self._persist(run); self.active = None

    def get(self, run_id, after=None):
        if not re.fullmatch(r'[0-9]{8}T[0-9]{6}Z-[a-f0-9]{8}', run_id):
            raise FileNotFoundError('Unknown run')
        with self.lock:
            if run_id in self.jobs:
                run = self.jobs[run_id]
            else:
                run = json.loads((self.work / 'runs' / run_id / 'run.json').read_text())
                if run['status'] in {'running', 'cancelling'}:
                    run['status'] = 'interrupted'
            if after is None:
                return deepcopy(run)
            keys = ('id', 'status', 'revision', 'completed', 'errors', 'finished_at')
            result = {k: run[k] for k in keys if k in run}
            result['changes'] = [{k: deepcopy(v) for k, v in row.items() if k != 'request'}
                                 for row in run['rows'] if row['revision'] > after]
            return result

    def cancel(self, run_id):
        with self.lock:
            if self.active != run_id:
                raise ValueError('This run is not active')
            self.stops[run_id].set(); self.jobs[run_id]['status'] = 'cancelling'
            self.jobs[run_id]['revision'] += 1
            self._persist(self.jobs[run_id])
            return {'status': 'cancelling'}


def handler_for(manager):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass  # no request/credential logging

        def send(self, status, value, content_type='application/json'):
            body = json.dumps(value, ensure_ascii=False, allow_nan=False).encode() if content_type == 'application/json' else value
            self.send_response(status); self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body))); self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff'); self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('X-Frame-Options', 'DENY'); self.end_headers(); self.wfile.write(body)

        def local_request(self, post=False):
            port = self.server.server_port
            hosts = {f'127.0.0.1:{port}', f'localhost:{port}'}
            host = self.headers.get('Host', '')
            if host not in hosts:
                self.send(403, {'error': 'Loopback Host required'}); return False
            origin = self.headers.get('Origin')
            if (origin and origin != 'http://' + host) or (post and not origin):
                self.send(403, {'error': 'Same-origin local request required'}); return False
            return True

        def do_GET(self):
            if not self.local_request():
                return
            url = urlsplit(self.path)
            try:
                if url.path == '/api/bootstrap':
                    return self.send(200, manager.bootstrap())
                if url.path == '/api/snapshot':
                    return self.send(200, manager.current())
                if url.path == '/api/runs':
                    return self.send(200, manager.history())
                if url.path.startswith('/api/runs/'):
                    after = parse_qs(url.query).get('after', [None])[0]
                    return self.send(200, manager.get(url.path.removeprefix('/api/runs/'), int(after) if after is not None else None))
                paths = {'/': ASSETS / 'index.html', '/app.js': ASSETS / 'app.js', '/core.js': ASSETS / 'core.js',
                         '/style.css': ASSETS / 'style.css', '/contest-label.js': ROOT / 'src/contest-label.js'}
                if url.path not in paths:
                    return self.send(404, {'error': 'Not found'})
                path = paths[url.path]; mime = mimetypes.guess_type(str(path))[0] or 'application/octet-stream'
                self.send(200, path.read_bytes(), mime + '; charset=utf-8')
            except (FileNotFoundError, KeyError):
                self.send(404, {'error': 'Run or baseline not found'})
            except ValueError:
                self.send(400, {'error': 'Invalid request or stored run'})

        def do_POST(self):
            if not self.local_request(post=True):
                return
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                return self.send(415, {'error': 'JSON body required'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 256000:
                    return self.send(413, {'error': 'Request body must be 1–256000 bytes'})
                body = json.loads(self.rfile.read(length)); path = urlsplit(self.path).path
                if path == '/api/runs':
                    if not isinstance(body, dict) or set(body) not in ({'questions'}, {'questions', 'candidate_id'}):
                        raise ValueError('Provide questions and optionally candidate_id only')
                    if 'candidate_id' in body and body['candidate_id'] is None:
                        raise ValueError('candidate_id must be a nonempty candidate ID')
                    return self.send(202, manager.start(body['questions'], body.get('candidate_id')))
                match = re.fullmatch(r'/api/runs/([^/]+)/cancel', path)
                if match:
                    return self.send(200, manager.cancel(match.group(1)))
                self.send(404, {'error': 'Not found'})
            except PermissionError as error:
                self.send(401, {'error': str(error)})
            except (json.JSONDecodeError, ValueError, TypeError) as error:
                self.send(400, {'error': str(error)[:240]})
            except RuntimeError as error:
                self.send(409, {'error': str(error)})

        def do_OPTIONS(self):
            self.send(403, {'error': 'Cross-origin access is disabled'})
    return Handler


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--port', type=int, default=8787)
    ap.add_argument('--jev-key-file', type=Path)
    ap.add_argument('--dataset', type=Path, default=DATASET)
    ap.add_argument('--work-dir', type=Path, default=WORK)
    args = ap.parse_args()
    key = args.jev_key_file.read_text().strip() if args.jev_key_file else os.environ.get('TYPESAFE_API_KEY', '').strip()
    manager = RunManager(args.dataset, args.work_dir, key)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), handler_for(manager)); server.daemon_threads = True
    print(f'Jev playground: http://127.0.0.1:{server.server_port}/', flush=True)
    print('Local server key configured.' if key else 'Stored results available; add a server key to run Jev.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
