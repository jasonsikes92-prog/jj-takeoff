"""Loopback-only authenticated case API for local homeowner workflow validation.

This is not an internet deployment. Access credentials are issued by the local
operator; every credential belongs to one case and expires or can be revoked.
"""
import argparse
import base64
import binascii
import hashlib
import json
import secrets
import time
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from answer_store import AnswerStore
from document_processing import DocumentProcessing
from plan_workspaces import PlanWorkspaces
from report_download import render_download
from reviewer_queue import case_review_queue
from bid_package_review import prepare_bid_package
from bid_document_reviews import BidDocumentReviews
from case_trade_quote import prepare_trade_quote, current_report_view


class CaseAccess:
    def __init__(self, store):
        self.store = store
        with store.connect() as db, db:
            db.execute('''CREATE TABLE IF NOT EXISTS case_access (
                token_sha256 TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id),
                actor_id TEXT NOT NULL, role TEXT NOT NULL, expires_at REAL NOT NULL,
                revoked INTEGER NOT NULL DEFAULT 0)''')

    def issue(self, case_id, actor_id, role='homeowner', lifetime_seconds=86400):
        if role not in ('homeowner', 'reviewer'):
            raise ValueError('Unknown access role')
        if not isinstance(actor_id, str) or not actor_id.strip():
            raise ValueError('An actor identity is required')
        if type(lifetime_seconds) is not int or not 0 < lifetime_seconds <= 30 * 86400:
            raise ValueError('Access lifetime must be between one second and 30 days')
        token = secrets.token_urlsafe(32)
        with self.store.connect() as db, db:
            if not db.execute('SELECT 1 FROM cases WHERE id=?', (case_id,)).fetchone():
                raise ValueError('Unknown case')
            db.execute('INSERT INTO case_access VALUES (?,?,?,?,?,0)',
                       (self.digest(token), case_id, actor_id.strip(), role, time.time() + lifetime_seconds))
        return token

    @staticmethod
    def digest(token):
        return hashlib.sha256(token.encode()).hexdigest()

    def authenticate(self, token):
        if not isinstance(token, str) or not 1 <= len(token) <= 200:
            return None
        with self.store.connect() as db:
            row = db.execute('SELECT * FROM case_access WHERE token_sha256=? AND revoked=0 AND expires_at>?',
                             (self.digest(token), time.time())).fetchone()
        return None if row is None else dict(row)

    def revoke(self, token):
        with self.store.connect() as db, db:
            db.execute('UPDATE case_access SET revoked=1 WHERE token_sha256=?', (self.digest(token),))


def make_server(database, port=5819):
    store = AnswerStore(database)
    access = CaseAccess(store)
    processing = DocumentProcessing(store)
    bid_reviews = BidDocumentReviews(store, processing)
    workspaces = PlanWorkspaces(store, Path(database).resolve().parent / 'plan_workspaces')

    class CaseServer(ThreadingHTTPServer):
        daemon_threads = True

        def __init__(self, address, handler):
            super().__init__(address, handler)
            self.worker = ThreadPoolExecutor(max_workers=1)
            self.pending = None

        def service_actions(self):
            if self.pending is not None and not self.pending.done():
                return
            if self.pending is not None and self.pending.exception() is not None:
                print('Document preparation interrupted; queued work remains available for retry.', flush=True)
            self.pending = self.worker.submit(processing.process_next)

        def server_close(self):
            super().server_close()
            self.worker.shutdown(wait=True)

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(15)

        def log_message(self, *_):
            pass  # Do not log document names, answer text or credentials.

        def respond(self, status, value, content_type='application/json', attachment=False):
            body = value if isinstance(value, bytes) else json.dumps(value, allow_nan=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
            if attachment:
                self.send_header('Content-Disposition', 'attachment; filename="level-ground-review.html"')
            elif content_type == 'application/octet-stream':
                self.send_header('Content-Disposition', 'attachment; filename="evidence-download"')
            self.end_headers()
            self.wfile.write(body)

        def handle_api(self):
            expected_host = f'127.0.0.1:{self.server.server_port}'
            if self.headers.get('Host') != expected_host:
                return self.respond(403, {'error': 'Unrecognized host'})
            origin = self.headers.get('Origin')
            if origin is not None and origin != 'http://' + expected_host:
                return self.respond(403, {'error': 'Unrecognized origin'})
            route = urlsplit(self.path)
            if route.query or route.fragment:
                return self.respond(400, {'error': 'Use credentials in the authorization header, not the URL'})
            path = route.path
            assets = {'/': ('portal.html', 'text/html; charset=utf-8'),
                      '/portal.css': ('portal.css', 'text/css; charset=utf-8'),
                      '/portal.js': ('portal.js', 'text/javascript; charset=utf-8')}
            if self.command == 'GET' and path in assets:
                filename, content_type = assets[path]
                return self.respond(200, Path(__file__).with_name(filename).read_bytes(), content_type)
            header = self.headers.get('Authorization', '')
            principal = access.authenticate(header[7:] if header.startswith('Bearer ') else '')
            if principal is None:
                return self.respond(401, {'error': 'Valid case access is required'})
            payload = {}
            if self.command == 'POST':
                if self.headers.get('Transfer-Encoding') or self.headers.get_content_type() != 'application/json':
                    return self.respond(415, {'error': 'Send a JSON body with Content-Length'})
                try:
                    length = int(self.headers.get('Content-Length', '0'))
                except ValueError:
                    return self.respond(400, {'error': 'Invalid content length'})
                limit = 35 * 1024 * 1024 if path == '/api/evidence' else 1024 * 1024
                if not 0 < length <= limit:
                    return self.respond(413, {'error': 'Request body exceeds the accepted size'})
                try:
                    payload = json.loads(self.rfile.read(length))
                except (ValueError, UnicodeDecodeError):
                    return self.respond(400, {'error': 'Invalid JSON'})
                if not isinstance(payload, dict):
                    return self.respond(400, {'error': 'JSON object required'})
                for field in ('report_id', 'question_id'):
                    if field in payload and (not isinstance(payload[field], str) or not payload[field].strip()):
                        return self.respond(400, {'error': 'Invalid record identity'})
                if path == '/api/reviews' and (type(payload.get('answer_id')) is not int or payload['answer_id'] <= 0):
                    return self.respond(400, {'error': 'Invalid answer identity'})

            case_id = principal['case_id']
            if self.command == 'GET' and path == '/api/session':
                return self.respond(200, {'role': principal['role']})
            # A supplied report ID never grants access to another case.
            report_id = payload.get('report_id')
            if path.startswith('/api/reports/'):
                report_id = path[len('/api/reports/'):]
                if report_id.endswith('/download'):
                    report_id = report_id[:-len('/download')]
            if report_id is not None:
                with store.connect() as db:
                    owned = db.execute('SELECT 1 FROM reports WHERE id=? AND case_id=?',
                                       (report_id, case_id)).fetchone()
                if not owned:
                    return self.respond(404, {'error': 'Report not found'})
            if self.command == 'GET' and path == '/api/reviewer-queue':
                if principal['role'] != 'reviewer':
                    return self.respond(403, {'error': 'Reviewer access required'})
                return self.respond(200, case_review_queue(store, processing, workspaces, case_id))
            if self.command == 'POST' and path == '/api/bid-document-reviews':
                if principal['role'] != 'reviewer':
                    return self.respond(403, {'error': 'Reviewer access required'})
                return self.respond(201, bid_reviews.save(case_id, principal['actor_id'], payload))
            if self.command == 'POST' and path == '/api/bid-package-draft':
                if principal['role'] != 'reviewer':
                    return self.respond(403, {'error': 'Reviewer access required'})
                return self.respond(200, prepare_bid_package(bid_reviews, case_id, principal['actor_id'], payload))
            if self.command == 'POST' and path == '/api/trade-quote-draft':
                if principal['role'] != 'reviewer':
                    return self.respond(403, {'error': 'Reviewer access required'})
                return self.respond(200, prepare_trade_quote(bid_reviews, workspaces, case_id, principal['actor_id'], payload))
            if self.command == 'GET' and path.startswith('/api/bid-document-reviews/'):
                if principal['role'] != 'reviewer':
                    return self.respond(403, {'error': 'Reviewer access required'})
                identity = path[len('/api/bid-document-reviews/'):]
                if identity.endswith('/draft'):
                    return self.respond(200, bid_reviews.draft(case_id, identity[:-len('/draft')]))
                return self.respond(200, bid_reviews.read(case_id,identity))
            if self.command == 'GET' and path == '/api/case':
                result = store.read_case(case_id)
                for report in result['reports']:
                    if 'trade_quote_review' in report['source_report']:
                        report['current_report_view']=current_report_view(bid_reviews,workspaces,case_id,report['source_report'])
                with store.connect() as db:
                    result['documents'] = [dict(row) for row in db.execute(
                        '''SELECT e.id,e.filename,e.sha256,length(e.body) AS bytes,e.created_at,
                           COALESCE(p.status,'queued') AS processing_status FROM evidence_objects e
                           LEFT JOIN document_processing p ON p.evidence_id=e.id
                           WHERE e.case_id=? ORDER BY e.created_at,e.id''',
                        (case_id,))]
                result['access_role'] = principal['role']
                return self.respond(200, result)
            if self.command == 'GET' and path.startswith('/api/document-processing/'):
                identity = path[len('/api/document-processing/'):]
                if identity.endswith('/bid-preparation'):
                    if principal['role'] != 'reviewer':
                        return self.respond(403, {'error': 'Reviewer access required for document preparation'})
                    return self.respond(200, bid_reviews.prepare(case_id, identity[:-len('/bid-preparation')]))
                try:
                    result = processing.read(case_id, identity)
                except ValueError:
                    return self.respond(404, {'error': 'Document processing is unavailable or failed integrity verification'})
                return self.respond(200, result)
            if self.command == 'POST' and path == '/api/plan-workspaces':
                if principal['role'] != 'reviewer':
                    return self.respond(403, {'error': 'Reviewer access required to select the governing plan'})
                return self.respond(200, workspaces.initialize(case_id, payload['source_reference'], principal['actor_id'],
                                                              jurisdiction=payload.get('jurisdiction')))
            if path.startswith('/api/plan-workspaces/') and path.endswith('/permit-inputs') and self.command in ('GET','POST'):
                if principal['role'] != 'reviewer':
                    return self.respond(403, {'error':'Reviewer access required for permit input corrections'})
                identity=path[len('/api/plan-workspaces/'):-len('/permit-inputs')]
                if self.command=='GET':return self.respond(200,workspaces.permit_inputs(case_id,identity))
                return self.respond(201,workspaces.revise_permit_inputs(case_id,identity,principal['actor_id'],payload))
            if self.command == 'POST' and path.startswith('/api/plan-workspaces/') and path.endswith('/measure'):
                if principal['role'] != 'reviewer':
                    return self.respond(403, {'error': 'Reviewer access required to prepare measurements'})
                if set(payload) != {'sheet_review_sha256'}:
                    return self.respond(400, {'error': 'Supply the current sheet-review revision'})
                identity = path[len('/api/plan-workspaces/'):-len('/measure')]
                try:
                    result = workspaces.measure(case_id, identity, principal['actor_id'], payload['sheet_review_sha256'])
                except OSError:
                    return self.respond(409, {'error': 'Measurement preparation could not complete; existing workspace files are preserved for review'})
                return self.respond(200, result)
            if self.command == 'GET' and path.startswith('/api/plan-workspaces/'):
                identity = path[len('/api/plan-workspaces/'):]
                if identity.endswith('/trade-bid-drafts'):
                    if principal['role'] != 'reviewer':
                        return self.respond(403, {'error': 'Reviewer access required for unsent trade drafts'})
                    try:
                        result = workspaces.trade_bid_drafts(case_id, identity[:-len('/trade-bid-drafts')])
                    except OSError:
                        return self.respond(409, {'error': 'Bid drafts unavailable; verify the retained workspace sources'})
                    return self.respond(200, result)
                if identity.endswith('/prebid-draft'):
                    if principal['role'] != 'reviewer':
                        return self.respond(403, {'error': 'Reviewer access required for unpublished report drafts'})
                    return self.respond(200, workspaces.prebid_draft(case_id, identity[:-len('/prebid-draft')]))
                try:
                    result = workspaces.read(case_id, identity)
                except ValueError:
                    return self.respond(404, {'error': 'Workspace unavailable or source verification failed'})
                return self.respond(200, result)
            if self.command == 'GET' and path.startswith('/api/evidence/'):
                try:
                    evidence = store.read_evidence(case_id, 'evidence:' + path[len('/api/evidence/'):])
                except ValueError:
                    return self.respond(404, {'error': 'Evidence not found'})
                return self.respond(200, evidence['body'], 'application/octet-stream')
            if self.command == 'GET' and path.startswith('/api/reports/'):
                report=current_report_view(bid_reviews,workspaces,case_id,store.updated_report(case_id,report_id))
                if path.endswith('/download'):
                    return self.respond(200, render_download(report),
                                        'application/octet-stream', attachment=True)
                return self.respond(200, report)
            if self.command == 'POST' and path == '/api/evidence':
                try:
                    content = base64.b64decode(payload['content_base64'], validate=True)
                except (ValueError, TypeError, binascii.Error):
                    return self.respond(400, {'error': 'Invalid file encoding'})
                evidence = store.attach_evidence(case_id, payload['filename'], content)
                processing.discover()
                return self.respond(201, evidence)
            if self.command == 'POST' and path == '/api/answers':
                return self.respond(201, store.record_answer(payload['report_id'], payload['question_id'],
                    payload['text'], payload.get('evidence_refs')))
            if self.command == 'POST' and path in ('/api/reports', '/api/reviews'):
                if principal['role'] != 'reviewer':
                    return self.respond(403, {'error': 'Reviewer access required'})
                if path == '/api/reports':
                    report = payload['report']
                    if 'trade_quote_review' in report:
                        regenerated=prepare_trade_quote(bid_reviews,workspaces,case_id,principal['actor_id'],
                            report['trade_quote_review']['request'])
                        if report!=regenerated:
                            raise ValueError('Regenerate the current trade quote draft before attaching it')
                    if 'package_review' in report:
                        sources = report['source_documents']
                        if not isinstance(sources, list) or not 2 <= len(sources) <= 21:
                            raise ValueError('Package report requires the primary bid and selected attachments')
                        regenerated = prepare_bid_package(bid_reviews, case_id, principal['actor_id'], {
                            'primary_review_id':sources[0]['review_id'],
                            'attachments':[{key:s[key] for key in ('review_id','relationship','rationale')} for s in sources[1:]]})
                        if report != regenerated:
                            raise ValueError('Regenerate the current package draft before attaching it')
                    identity = store.attach_report(case_id, payload['report'])
                    return self.respond(201, {'report_id': identity})
                return self.respond(201, store.review_answer(payload['report_id'], payload['answer_id'],
                    principal['actor_id'], payload['decision'], payload['rationale'], payload['evidence_refs']))
            return self.respond(404, {'error': 'Route not found'})

        def dispatch(self):
            try:
                self.handle_api()
            except (ValueError, KeyError, TypeError):
                self.respond(400, {'error': 'Invalid request or evidence failed verification'})
            except (TimeoutError, ConnectionError):
                self.close_connection = True

        do_GET = dispatch
        do_POST = dispatch

    server = CaseServer(('127.0.0.1', port), Handler)
    server.store = store
    server.access = access
    server.processing = processing
    server.bid_reviews = bid_reviews
    server.workspaces = workspaces
    return server


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True)
    parser.add_argument('--port', type=int, default=5819)
    args = parser.parse_args()
    with make_server(args.database, args.port) as server:
        print(f'Local case API: http://127.0.0.1:{server.server_port}', flush=True)
        server.serve_forever()
