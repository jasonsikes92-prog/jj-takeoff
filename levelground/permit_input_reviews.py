"""Append reviewer corrections without replacing the original permit intake."""
import hashlib
import json
from datetime import date
from answer_store import encode, now


def validate_jurisdiction(value):
    if not isinstance(value,dict):raise ValueError('Jurisdiction inputs must be an object')
    for key in ('state','authority_id','code_basis_date'):
        if value.get(key) is not None and not isinstance(value[key],str):
            raise ValueError('Jurisdiction '+key+' must be text or unknown')
    if value.get('code_basis_date'):date.fromisoformat(value['code_basis_date'])
    if value.get('authority_verified') is not None and type(value['authority_verified']) is not bool:
        raise ValueError('Jurisdiction authority verification must be true, false or unknown')
    if not isinstance(value.get('conditions',{}),dict):
        raise ValueError('Jurisdiction site conditions must be an object')


class PermitInputReviews:
    def __init__(self,store):
        self.store=store
        with store.connect() as db,db:
            db.execute('''CREATE TABLE IF NOT EXISTS permit_input_reviews (
                case_id TEXT NOT NULL REFERENCES cases(id), workspace_id TEXT NOT NULL,
                revision INTEGER NOT NULL, body TEXT NOT NULL, sha256 TEXT NOT NULL,
                PRIMARY KEY(case_id,workspace_id,revision))''')

    def _read(self,db,case_id,workspace_id,base_sha256):
        rows=db.execute('SELECT * FROM permit_input_reviews WHERE case_id=? AND workspace_id=? ORDER BY revision',
                        (case_id,workspace_id)).fetchall()
        records=[];parent=base_sha256
        for number,row in enumerate(rows,1):
            record=json.loads(row['body'])
            if (hashlib.sha256(row['body'].encode()).hexdigest()!=row['sha256'] or row['revision']!=number
                    or record.get('case_id')!=case_id or record.get('workspace_id')!=workspace_id
                    or record.get('revision')!=number or record.get('parent_sha256')!=parent
                    or record.get('base_context_sha256')!=base_sha256):
                raise ValueError('Permit input review history changed; resolve its source integrity')
            validate_jurisdiction(record['project_basis'])
            for reference in record['evidence_refs']:self.store.read_evidence(case_id,reference)
            records.append({**record,'sha256':row['sha256']});parent=row['sha256']
        return {'revision':len(records),'revision_sha256':parent,'records':records}

    def read(self,case_id,workspace_id,base_sha256):
        with self.store.connect() as db:return self._read(db,case_id,workspace_id,base_sha256)

    def save(self,case_id,workspace_id,base_sha256,reviewer_id,payload):
        if set(payload)!={'expected_revision','jurisdiction','rationale','evidence_refs'}:
            raise ValueError('Supply expected_revision, jurisdiction, rationale and evidence_refs')
        expected=payload['expected_revision']
        if type(expected) is not int or expected<0:raise ValueError('A nonnegative current revision is required')
        if not isinstance(reviewer_id,str) or not reviewer_id.strip():raise ValueError('Reviewer identity required')
        if not isinstance(payload['rationale'],str) or not payload['rationale'].strip():
            raise ValueError('A reason for the jurisdiction correction is required')
        validate_jurisdiction(payload['jurisdiction'])
        refs=payload['evidence_refs']
        if not isinstance(refs,list) or not refs or any(not isinstance(r,str) or not r for r in refs):
            raise ValueError('At least one case evidence reference is required')
        for reference in refs:self.store.read_evidence(case_id,reference)
        with self.store.connect() as db,db:
            db.execute('BEGIN IMMEDIATE')
            prior=self._read(db,case_id,workspace_id,base_sha256)
            if expected!=prior['revision']:raise ValueError('Permit input revision changed; read the current review before saving')
            record={'case_id':case_id,'workspace_id':workspace_id,'revision':expected+1,
                'base_context_sha256':base_sha256,'parent_sha256':prior['revision_sha256'],
                'project_basis':payload['jurisdiction'],'rationale':payload['rationale'].strip(),
                'evidence_refs':refs,'reviewer_id':reviewer_id.strip(),'created_at':now()}
            body=encode(record);digest=hashlib.sha256(body.encode()).hexdigest()
            db.execute('INSERT INTO permit_input_reviews VALUES (?,?,?,?,?)',
                       (case_id,workspace_id,expected+1,body,digest))
            return {'revision':expected+1,'revision_sha256':digest,'records':prior['records']+[{**record,'sha256':digest}]}
