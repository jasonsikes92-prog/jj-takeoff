"""Versioned edits for identified areas, lengths and counts on a fixed plan revision.

Geometry is recalculated on every read. Edits are drafts; dependent estimate rows
require recalculation and review before they can be released.
"""
import hashlib
import json
import math
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from slab_review import validate_polygon


class EditConflict(ValueError):
    pass


def encode(value):
    return json.dumps(value,allow_nan=False,sort_keys=True,separators=(',',':'))


def calculate(measurement):
    points=measurement['points'];width=measurement['width_pt'];height=measurement['height_pt']
    kind=measurement['kind'];scale=measurement.get('points_per_foot')
    dimensions=(width,height) if kind=='count' else (width,height,scale)
    if any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in dimensions):
        raise ValueError('Drawing dimensions and scale must be positive finite numbers')
    if kind=='area':
        area,perimeter=validate_polygon(points,width,height)
        factor=measurement.get('surface_factor',1)
        if type(factor) not in (int,float) or not math.isfinite(factor) or factor<1:
            raise ValueError('Surface factor must be finite and at least one')
        return {'quantity':area/scale**2*factor,'unit':'SF','projected_area_sf':area/scale**2,
                'perimeter_lf':perimeter/scale,'perimeter_basis':'plan projection'}
    if kind not in ('length','count'):raise ValueError('Unknown measurement kind')
    if not isinstance(points,list) or not (2 if kind=='length' else 0)<=len(points)<=1000:
        raise ValueError('Measurement has an invalid point count')
    for point in points:
        if (not isinstance(point,list) or len(point)!=2 or
                any(type(v) not in (int,float) or not math.isfinite(v) for v in point) or
                not 0<=point[0]<=width or not 0<=point[1]<=height):
            raise ValueError('Points must be finite and on the drawing')
    if len(set(map(tuple,points)))!=len(points):raise ValueError('Duplicate measurement points')
    if kind=='length' and 'plane_gradients' in measurement:
        gradients=measurement['plane_gradients']
        if (not isinstance(gradients,list) or len(gradients) not in (1,2) or
                any(not isinstance(g,list) or len(g)!=2 or
                    any(type(v) not in (int,float) or not math.isfinite(v) for v in g) for g in gradients)):
            raise ValueError('Sloped line needs one or two finite roof-plane gradients')
        lengths=[]
        for a,b in zip(points,points[1:]):
            dx,dy=(b[0]-a[0])/scale,(b[1]-a[1])/scale
            rises=[g[0]*dx+g[1]*dy for g in gradients]
            if any(not math.isclose(rises[0],rise,rel_tol=1e-9,abs_tol=1e-6) for rise in rises[1:]):
                raise ValueError('Adjacent roof planes disagree along this edge')
            lengths.append(math.sqrt(dx*dx+dy*dy+rises[0]*rises[0]))
        return {'quantity':math.fsum(lengths),'unit':'LF',
                'projected_length_lf':sum(math.dist(a,b) for a,b in zip(points,points[1:]))/scale,
                'length_basis':'directional roof-plane slope; plane elevations and edge role require separate verification'}
    return ({'quantity':sum(math.dist(a,b) for a,b in zip(points,points[1:]))/scale,'unit':'LF'}
            if kind=='length' else {'quantity':len(points),'unit':'EA'})


class MeasurementStore:
    def __init__(self,folder):
        self.folder=Path(folder)
        self.config_path=self.folder/'measurements.json'
        self.config_hash=hashlib.sha256(self.config_path.read_bytes()).hexdigest()
        self.config=json.loads(self.config_path.read_text())
        self.plan=self.folder/'plan.pdf'
        ids=[m['id'] for m in self.config['measurements']]
        if not ids or len(ids)!=len(set(ids)):raise ValueError('Measurement IDs must be unique')
        self.check_source()
        self.database=self.folder/'measurement_edits.sqlite3'
        with closing(sqlite3.connect(self.database)) as db,db:
            db.execute('CREATE TABLE IF NOT EXISTS versions (version INTEGER PRIMARY KEY, body TEXT NOT NULL)')
            if not db.execute('SELECT 1 FROM versions LIMIT 1').fetchone():
                measurements={m['id']:{**m,'result':calculate(m),'certified':False} for m in self.config['measurements']}
                state={'version':1,'plan_sha256':self.config['plan_sha256'],'config_sha256':self.config_hash,
                    'measurements':measurements,'invalidated_rows':[], 'note':'Initial draft geometry',
                    'created_at':datetime.now(timezone.utc).isoformat(),'estimate_released':False}
                db.execute('INSERT INTO versions VALUES (?,?)',(1,encode(state)))
        self.read()

    def check_source(self):
        if hashlib.sha256(self.config_path.read_bytes()).hexdigest()!=self.config_hash:
            raise EditConflict('Measurement configuration changed; rebuild the review')
        if hashlib.sha256(self.plan.read_bytes()).hexdigest()!=self.config['plan_sha256']:
            raise EditConflict('Drawing changed; start a review for the new revision')

    def verify(self,state):
        if state['plan_sha256']!=self.config['plan_sha256'] or state['config_sha256']!=self.config_hash:
            raise EditConflict('Saved edits belong to a different drawing or configuration')
        if set(state['measurements'])!={m['id'] for m in self.config['measurements']}:
            raise EditConflict('Saved measurement identities changed')
        for original in self.config['measurements']:
            current=state['measurements'][original['id']]
            if any(current.get(k)!=v for k,v in original.items() if k!='points'):
                raise EditConflict('Saved measurement metadata changed')
            if current['result']!=calculate(current) or current['certified'] or state['estimate_released']:
                raise EditConflict('Saved quantities or review status are invalid')
        return state

    def read(self,version=None):
        self.check_source()
        with closing(sqlite3.connect(self.database)) as db:
            row=(db.execute('SELECT body FROM versions ORDER BY version DESC LIMIT 1').fetchone() if version is None
                 else db.execute('SELECT body FROM versions WHERE version=?',(version,)).fetchone())
        if row is None:raise ValueError('Version not found')
        return self.verify(json.loads(row[0]))

    def save(self,measurement_id,points,base_version,plan_sha256,note):
        self.check_source()
        if type(base_version) is not int or not isinstance(note,str) or not note.strip():
            raise ValueError('Save requires the base version and a change note')
        if plan_sha256!=self.config['plan_sha256']:raise EditConflict('Wrong drawing revision')
        rules_path=self.folder/'quantity_rules.json'
        rules_bytes=rules_path.read_bytes() if rules_path.exists() else None
        mapped_rows=set()
        if rules_bytes is not None:
            rules=json.loads(rules_bytes)
            if rules['plan_sha256']!=plan_sha256:
                raise EditConflict('Quantity rules belong to another drawing')
            for rule in rules['rules']:
                if measurement_id in rule['measurement_ids']:
                    mapped_rows.update(rule['template_rows'])
        with closing(sqlite3.connect(self.database)) as db,db:
            db.execute('BEGIN IMMEDIATE')
            state=self.verify(json.loads(db.execute('SELECT body FROM versions ORDER BY version DESC LIMIT 1').fetchone()[0]))
            if state['version']!=base_version:raise EditConflict('Another edit was saved; reload before saving')
            if measurement_id not in state['measurements']:raise ValueError('Unknown measurement ID')
            measurement=state['measurements'][measurement_id]
            measurement['points']=points
            measurement['result']=calculate(measurement)
            measurement['certified']=False
            state['invalidated_rows']=sorted(set(state['invalidated_rows'])|set(measurement['dependent_rows'])|mapped_rows)
            state.update(version=base_version+1,note=note.strip(),changed_measurement=measurement_id,
                         created_at=datetime.now(timezone.utc).isoformat(),estimate_released=False)
            self.check_source()
            if (rules_path.read_bytes() if rules_path.exists() else None)!=rules_bytes:
                raise EditConflict('Quantity rules changed during the edit; reload before saving')
            db.execute('INSERT INTO versions VALUES (?,?)',(state['version'],encode(state)))
        return state
