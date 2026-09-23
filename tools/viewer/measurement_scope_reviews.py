"""Local, source-bound draft scope decisions with append-only history."""
import copy
import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

from measurement_store import EditConflict, encode
from measurement_quantities import geometry_digest


class ScopeReviews:
    def __init__(self, store, rules):
        self.store=store
        self.rules=copy.deepcopy(rules)
        self.rules_sha256=hashlib.sha256(encode(rules).encode()).hexdigest()
        with closing(sqlite3.connect(store.database)) as db,db:
            db.execute('CREATE TABLE IF NOT EXISTS scope_reviews (id INTEGER PRIMARY KEY, body TEXT NOT NULL)')

    def save(self, rule_id, measurement_id, decision, scope, reviewer,
             base_version, plan_sha256, rules_sha256):
        if decision not in ('approved_for_draft','not_suitable_for_estimate'):
            raise ValueError('Choose a draft scope decision')
        if any(not isinstance(v,str) or not v.strip() for v in (scope,reviewer)):
            raise ValueError('Scope explanation and reviewer name required')
        if type(base_version) is not int:
            raise ValueError('Measurement version required')
        if rules_sha256!=self.rules_sha256 or plan_sha256!=self.rules['plan_sha256']:
            raise EditConflict('Review belongs to different rules or drawing')
        rule=next((r for r in self.rules['rules'] if r['id']==rule_id),None)
        if rule is None or measurement_id not in rule['measurement_ids']:
            raise ValueError('Measurement is not part of this quantity rule')
        self.store.check_source()
        with closing(sqlite3.connect(self.store.database)) as db,db:
            db.execute('BEGIN IMMEDIATE')
            state=self.store.verify(json.loads(db.execute('SELECT body FROM versions ORDER BY version DESC LIMIT 1').fetchone()[0]))
            if state['version']!=base_version:
                raise EditConflict('Measurements changed; review the current version')
            record={'rule_id':rule_id,'measurement_id':measurement_id,'decision':decision,
                    'scope':scope.strip(),'reviewer':reviewer.strip(),'measurement_version':base_version,
                    'plan_sha256':plan_sha256,'rules_sha256':rules_sha256,
                    'geometry_sha256':geometry_digest(state['measurements'][measurement_id]),
                    'created_at':datetime.now(timezone.utc).isoformat(),
                    'reviewer_identity_authenticated':False,'estimate_released':False}
            self.store.check_source()
            cursor=db.execute('INSERT INTO scope_reviews (body) VALUES (?)',(encode(record),))
            record['review_id']=cursor.lastrowid
        return record

    def history(self):
        self.store.check_source()
        with closing(sqlite3.connect(self.store.database)) as db:
            return [{**json.loads(body),'review_id':identity}
                    for identity,body in db.execute('SELECT id,body FROM scope_reviews ORDER BY id')]

    def effective_rules(self):
        rules=copy.deepcopy(self.rules)
        by_id={r['id']:r for r in rules['rules']}
        for record in self.history():
            if record['rules_sha256']!=self.rules_sha256 or record['plan_sha256']!=rules['plan_sha256']:
                continue
            rule=by_id[record['rule_id']]
            rule.setdefault('geometry_reviews',{})[record['measurement_id']]=record
        return rules
