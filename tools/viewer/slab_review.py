"""Local, versioned slab review. Geometry edits never inherit certification."""
import argparse
import ast
import hashlib
import http.server
import json
import math
import sqlite3
import sys
import threading
from datetime import datetime, timezone
from contextlib import closing
from decimal import Decimal, ROUND_CEILING
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import jnj_takeoff as engine
from slab_outputs import calculate_outputs, construction_trade_draft, estimate_csv, profile_hash, validate_profile


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':'))


def historical_formula(formula, qty):
    """Restricted arithmetic; round-up is an observed replay rule, not certification."""
    tree = ast.parse(formula.replace('{QTY}', 'quantity'), mode='eval')

    def visit(node):
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return Decimal(str(node.value))
        if isinstance(node, ast.Name) and node.id == 'quantity':
            return Decimal(str(qty))
        if isinstance(node, ast.BinOp):
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Add): return left + right
            if isinstance(node.op, ast.Sub): return left - right
            if isinstance(node.op, ast.Mult): return left * right
            if isinstance(node.op, ast.Div): return left / right
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id.lower() == 'round' and len(node.args) == 1
                and not node.keywords):
            return visit(node.args[0]).to_integral_value(rounding=ROUND_CEILING)
        raise ValueError('Unsupported historical formula')

    result = visit(tree)
    if not result.is_finite() or result < 0:
        raise ValueError('Invalid historical quantity')
    return result


def validate_polygon(points, width, height):
    if not isinstance(points, list) or not 3 <= len(points) <= 100:
        raise ValueError('A boundary needs 3 to 100 corners')
    for pt in points:
        if (not isinstance(pt, list) or len(pt) != 2
                or any(type(v) not in (int, float) or not math.isfinite(v) for v in pt)):
            raise ValueError('Each corner needs two finite coordinates')
        if not (0 <= pt[0] <= width and 0 <= pt[1] <= height):
            raise ValueError('Keep every corner on the drawing')
    if len(set(map(tuple, points))) != len(points):
        raise ValueError('Corners cannot overlap')

    def orientation(a, b, c):
        return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])

    def on_segment(a, b, c):
        return (min(a[0], b[0])-1e-9 <= c[0] <= max(a[0], b[0])+1e-9
                and min(a[1], b[1])-1e-9 <= c[1] <= max(a[1], b[1])+1e-9)

    n = len(points)
    for i in range(n):
        a, b = points[i], points[(i+1) % n]
        for j in range(i+1, n):
            if j == i+1 or (i == 0 and j == n-1): continue
            c, d = points[j], points[(j+1) % n]
            oa, ob, oc, od = orientation(a,b,c), orientation(a,b,d), orientation(c,d,a), orientation(c,d,b)
            if ((oa*ob < 0 and oc*od < 0)
                    or any(abs(o) <= 1e-9 and on_segment(p,q,r)
                           for o,p,q,r in [(oa,a,b,c),(ob,a,b,d),(oc,c,d,a),(od,c,d,b)])):
                raise ValueError('Boundary edges cannot cross or touch')
    area, perimeter = engine._poly_area_perim_pts(points)
    if area <= 1e-6:
        raise ValueError('The boundary must enclose an area')
    return area, perimeter


def calculate(config, points):
    area_pts, perimeter_pts = validate_polygon(points, config['width_pt'], config['height_pt'])
    ppf = config['scale']['ppf']
    net = area_pts / (ppf * ppf)
    waste = config['waste_percent']
    # Nine decimal SF removes binary arithmetic noise before whole-unit rounding.
    order_decimal = Decimal(str(round(net, 9))) * (1 + Decimal(str(waste)) / 100)
    order = float(order_decimal)
    historical_parent = order_decimal.to_integral_value(rounding=ROUND_CEILING)
    candidates = []
    for line in config['assembly']['lines']:
        qty = historical_formula(line['formula'], historical_parent)
        candidates.append({'id': line['estimate_item_id'], 'name': line['name'],
                           'unit': line['unit'], 'formula': line['formula'],
                           'candidate_quantity': float(qty), 'current_amount': None})
    return {'net_sf': net, 'perimeter_lf': perimeter_pts / ppf,
            'waste_percent': waste, 'waste_sf': order-net, 'order_sf': order,
            'historical_assembly_quantity': float(historical_parent),
            'assembly_candidates': candidates, 'current_total': None,
            'concrete_volume_cy': None, 'status': 'more information required',
            'verification_valid': False,
            'reasons': config['required_information']}


class Conflict(ValueError):
    pass


class ReviewStore:
    def __init__(self, folder):
        self.folder = Path(folder).resolve()
        self.config = json.loads((self.folder/'review_config.json').read_text(encoding='utf-8'))
        self.config_hash = digest(self.folder/'review_config.json')
        self.profile_path = self.folder/'construction_profile.json'
        self.profile = json.loads(self.profile_path.read_text(encoding='utf-8')) if self.profile_path.exists() else None
        self.profile_file_hash = digest(self.profile_path) if self.profile else None
        if self.profile: validate_profile(self.config,self.profile)
        self.lock = threading.RLock()
        self.check_source()
        self.database = self.folder/'review.sqlite3'
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS versions (version INTEGER PRIMARY KEY, snapshot TEXT NOT NULL)')
            count = db.execute('SELECT COUNT(*) FROM versions').fetchone()[0]
            if not count:
                snap = self.snapshot(1, self.config['initial_points'], 'Initial engine boundary', 0)
                db.execute('INSERT INTO versions VALUES (?,?)', (1, encoded(snap)))
        self.read()

    def check_source(self):
        if self.profile_path.exists()!=bool(self.profile) or (self.profile and digest(self.profile_path)!=self.profile_file_hash):
            raise Conflict('Construction rules changed. Reload the review server before saving another version.')
        if digest(self.folder/'review_config.json') != self.config_hash:
            raise Conflict('Review configuration changed. Start a new review.')
        if digest(self.folder/'plan.pdf') != self.config['plan_sha256']:
            raise Conflict('Drawing revision changed. Start a new review for that drawing.')
        for name, expected in self.config['asset_hashes'].items():
            if digest(self.folder/name) != expected:
                raise Conflict('A displayed drawing image changed. Rebuild this review.')

    def snapshot(self, version, points, note, base, outline='red'):
        snap = {'version': version, 'base_version': base, 'outline': outline,
                'created_at': datetime.now(timezone.utc).isoformat(), 'note': note,
                'plan_sha256': self.config['plan_sha256'], 'config_sha256': self.config_hash,
                'page': self.config['page'], 'points': points,
                'results': calculate(self.config, points)}
        if self.profile and outline==self.profile['outline']:
            snap['construction']={'profile':self.profile,'profile_sha256':profile_hash(self.profile),
                                  'outputs':calculate_outputs(self.config,points,self.profile)}
        return snap

    def preview(self, points, outline='red'):
        if outline not in ('red','blue'):raise ValueError('Choose the red or blue measurement')
        result=calculate(self.config,points)
        if self.profile and outline==self.profile['outline']:
            result['construction']=calculate_outputs(self.config,points,self.profile)
        return result

    def read(self, version=None):
        self.check_source()
        with closing(sqlite3.connect(self.database)) as db, db:
            row = (db.execute('SELECT snapshot FROM versions WHERE version=?', (version,)).fetchone()
                   if version is not None else db.execute('SELECT snapshot FROM versions ORDER BY version DESC LIMIT 1').fetchone())
        if not row: raise ValueError('Saved version not found')
        snap = json.loads(row[0])
        snap.setdefault('outline', 'red')
        if snap['outline'] not in ('red', 'blue'):
            raise Conflict('Unknown saved measurement')
        if snap['config_sha256'] != self.config_hash or snap['plan_sha256'] != self.config['plan_sha256']:
            raise Conflict('Saved measurement belongs to a different drawing or configuration')
        if snap['results'] != calculate(self.config, snap['points']):
            raise Conflict('Saved calculations do not match the boundary')
        if 'construction' in snap:
            attachment=snap['construction']; profile=attachment['profile']
            if snap['outline']!=profile['outline'] or attachment['profile_sha256']!=profile_hash(profile):
                raise Conflict('Saved construction identity does not match')
            if attachment['outputs']!=calculate_outputs(self.config,snap['points'],profile):
                raise Conflict('Saved material outputs do not match the measurement')
        return snap

    def history(self):
        self.check_source()
        with closing(sqlite3.connect(self.database)) as db, db:
            records = [json.loads(r[0]) for r in db.execute('SELECT snapshot FROM versions ORDER BY version DESC')]
        return [dict({k: r[k] for k in ['version','created_at','note','base_version']},
                     outline=r.get('outline', 'red')) for r in records]

    def state(self):
        with self.lock:
            history = self.history()
            measurements = {}
            for item in history:
                if item['outline'] not in measurements:
                    measurements[item['outline']] = self.read(item['version'])
            if 'blue' not in measurements and 'comparison_outer_points' in self.config:
                measurements['blue'] = self.snapshot(0, self.config['comparison_outer_points'],
                                                     'Save blue outline', 0, 'blue')
            return {'config': self.config, 'snapshot': self.read(), 'construction_profile':self.profile,
                    'history': history, 'measurements': measurements}

    def save(self, payload):
        if set(payload) not in ({'base_version','plan_sha256','points','note'},
                                {'base_version','plan_sha256','points','note','outline'}):
            raise ValueError('Save needs a base version, drawing identity, boundary and note')
        if payload.get('outline', 'red') not in ('red', 'blue'):
            raise ValueError('Choose the red or blue measurement')
        if type(payload['base_version']) is not int:
            raise ValueError('Invalid base version')
        if payload['plan_sha256'] != self.config['plan_sha256']:
            raise Conflict('The drawing revision does not match')
        if not isinstance(payload['note'], str) or not 1 <= len(payload['note'].strip()) <= 240:
            raise ValueError('Enter a change note of 1 to 240 characters')
        with self.lock:
            self.check_source()
            with closing(sqlite3.connect(self.database)) as db, db:
                db.execute('BEGIN IMMEDIATE')
                current = db.execute('SELECT MAX(version) FROM versions').fetchone()[0]
                if current != payload['base_version']:
                    raise Conflict('A newer version was saved. Reload before saving your changes.')
                snap = self.snapshot(current+1, payload['points'], payload['note'].strip(), current,
                                     payload.get('outline', 'red'))
                db.execute('INSERT INTO versions VALUES (?,?)', (current+1, encoded(snap)))
            return snap


def trade_draft(config, snap):
    if 'construction' in snap:return construction_trade_draft(config,snap)
    result = snap['results']
    return '\n'.join([
        '# DRAFT — garage slab scope review', '', 'Not ready to send for bidding.', '',
        f"Drawing: {config['plan_name']} / page {config['page']+1}",
        f"Drawing SHA-256: {config['plan_sha256']}", f"Measurement version: {snap['version']}",
        f"Measurement: {snap.get('outline', 'red')} outline",
        f"Change note: {snap['note']}", '',
        f"Candidate net area: {result['net_sf']:.2f} SF",
        f"Waste factor from historical assembly: {result['waste_percent']}%",
        f"Candidate area including waste: {result['order_sf']:.2f} SF", '',
        'Scope: garage slab only. Porch, footings and other foundation areas are outside this trial.',
        'Boundary and specifications require confirmation before these quantities can be used.', '',
        '## Resolve before requesting prices', '',
        *['- '+reason for reason in config['required_information']], '',
        '## Bid response fields', '',
        '- Confirm included labor, material, equipment, delivery and disposal.',
        '- List exclusions, allowances and the scope behind each allowance.',
        '- Confirm slab/base thickness, concrete strength, reinforcement and vapor barrier.',
        '- State pumping/access requirements, schedule, lead time and price expiry.',
        '- Identify drawing conflicts and unit prices for agreed changes.', '',
        'Current price: not established. No bid request has been sent.', ''])


def make_server(store, port):
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            sys.stderr.write((fmt % args)+'\n')

        def respond(self, status, value, content_type='application/json; charset=utf-8'):
            raw = value if isinstance(value, bytes) else encoded(value).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(raw)

        def trusted(self):
            hosts = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            return self.headers.get('Host') in hosts

        def do_GET(self):
            try:
                if not self.trusted(): return self.respond(403, {'error':'Local access only'})
                store.check_source()
                if self.path == '/api/state':
                    return self.respond(200, store.state())
                if self.path.startswith('/api/version/'):
                    return self.respond(200, store.read(int(self.path.rsplit('/',1)[1])))
                if self.path.startswith('/draft/') and self.path.endswith('.md'):
                    v = int(self.path[7:-3]); snap = store.read(v)
                    return self.respond(200, trade_draft(store.config,snap).encode('utf-8'), 'text/markdown; charset=utf-8')
                if self.path.startswith('/estimate/') and self.path.endswith('.csv'):
                    v=int(self.path[10:-4]); snap=store.read(v)
                    return self.respond(200,estimate_csv(snap).encode('utf-8-sig'),'text/csv; charset=utf-8')
                if self.path == '/':
                    return self.respond(200, (Path(__file__).with_name('slab_review.html')).read_bytes(), 'text/html; charset=utf-8')
                checks = {'/boundary-check/': ('boundary_check.html','text/html; charset=utf-8'),
                          '/boundary-check/evidence.json': ('boundary_check.json','application/json; charset=utf-8'),
                          '/foundation-check/': ('foundation_check.html','text/html; charset=utf-8'),
                          '/foundation-check/evidence.json': ('foundation_check.json','application/json; charset=utf-8')}
                if self.path in checks:
                    name, content_type = checks[self.path]
                    path = store.folder/name
                    if not path.exists(): return self.respond(404, {'error':'No independent boundary check is available yet'})
                    return self.respond(200, path.read_bytes(), content_type)
                if self.path[1:] in store.config['asset_hashes']:
                    return self.respond(200, (store.folder/self.path[1:]).read_bytes(), 'image/png')
                return self.respond(404, {'error':'Not found'})
            except Conflict as exc: self.respond(409, {'error':str(exc)})
            except (ValueError, OSError) as exc: self.respond(400, {'error':str(exc)})

        def do_POST(self):
            try:
                origins = {f'http://127.0.0.1:{self.server.server_port}', f'http://localhost:{self.server.server_port}'}
                if (not self.trusted() or self.headers.get('Origin') not in origins
                        or self.headers.get('Content-Type') != 'application/json'):
                    return self.respond(403, {'error':'Use this review window to save changes'})
                n = int(self.headers.get('Content-Length', '0'))
                if not 0 < n <= 64000: raise ValueError('Invalid request size')
                payload = json.loads(self.rfile.read(n))
                if not isinstance(payload, dict): raise ValueError('Expected a JSON object')
                store.check_source()
                if self.path == '/api/save': return self.respond(200, store.save(payload))
                if self.path == '/api/preview':
                    if set(payload) not in ({'points'},{'points','outline'}): raise ValueError('Preview accepts boundary points and measurement identity')
                    return self.respond(200, store.preview(payload['points'],payload.get('outline','red')))
                return self.respond(404, {'error':'Not found'})
            except Conflict as exc: self.respond(409, {'error':str(exc)})
            except (ValueError, OSError, ArithmeticError) as exc: self.respond(400, {'error':str(exc)})

    return http.server.ThreadingHTTPServer(('127.0.0.1', port), Handler)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', required=True)
    parser.add_argument('--port', type=int, default=5812)
    args = parser.parse_args()
    review = ReviewStore(args.job)
    server = make_server(review, args.port)
    print(f'Garage slab review: http://127.0.0.1:{server.server_port}/', flush=True)
    server.serve_forever()
