"""Local return-visit records for pre-bid and bid-review reports.

Homeowner answers remain reported evidence, never automatic scope/code approval.
This module is not a public authenticated service.
"""
import hashlib
import copy
import json
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


def encode(value):return json.dumps(value,sort_keys=True,allow_nan=False,separators=(',',':'))
def now():return datetime.now(timezone.utc).isoformat()


class AnswerStore:
    def __init__(self,path):
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db,db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS cases (id TEXT PRIMARY KEY,label TEXT NOT NULL,created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS evidence_objects (id TEXT PRIMARY KEY,case_id TEXT NOT NULL REFERENCES cases(id),
                    filename TEXT NOT NULL,sha256 TEXT NOT NULL,body BLOB NOT NULL,created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS reports (id TEXT PRIMARY KEY,case_id TEXT NOT NULL REFERENCES cases(id),
                    stage TEXT NOT NULL,source_sha256 TEXT NOT NULL,body TEXT NOT NULL,created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS questions (report_id TEXT NOT NULL REFERENCES reports(id),id TEXT NOT NULL,
                    ordinal INTEGER NOT NULL,text TEXT NOT NULL,PRIMARY KEY(report_id,id));
                CREATE TABLE IF NOT EXISTS answers (id INTEGER PRIMARY KEY,report_id TEXT NOT NULL,question_id TEXT NOT NULL,
                    revision INTEGER NOT NULL,text TEXT NOT NULL,evidence_refs TEXT NOT NULL,created_at TEXT NOT NULL,
                    UNIQUE(report_id,question_id,revision),
                    FOREIGN KEY(report_id,question_id) REFERENCES questions(report_id,id));
                CREATE TABLE IF NOT EXISTS answer_reviews (id INTEGER PRIMARY KEY,answer_id INTEGER NOT NULL REFERENCES answers(id),
                    answer_sha256 TEXT NOT NULL,reviewer_id TEXT NOT NULL,decision TEXT NOT NULL,
                    rationale TEXT NOT NULL,evidence_refs TEXT NOT NULL,created_at TEXT NOT NULL);
            ''')

    def connect(self):
        db=sqlite3.connect(self.path);db.row_factory=sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        return closing(db)

    def create_case(self,label):
        if not isinstance(label,str) or not label.strip():raise ValueError('A case label is required')
        identity=str(uuid.uuid4())
        with self.connect() as db,db:db.execute('INSERT INTO cases VALUES (?,?,?)',(identity,label.strip(),now()))
        return identity

    def attach_report(self,case_id,report):
        stage=report['meta']['report_type']
        if stage not in ('pre_bid','bid_gap'):raise ValueError('Report must be pre_bid or bid_gap')
        questions=report.get('questions',[])
        if not isinstance(questions,list) or any(not isinstance(q,str) or not q.strip() for q in questions):
            raise ValueError('Report questions must be nonempty text strings')
        body=encode(report);digest=hashlib.sha256(body.encode()).hexdigest();identity=str(uuid.uuid4())
        with self.connect() as db,db:
            if not db.execute('SELECT 1 FROM cases WHERE id=?',(case_id,)).fetchone():raise ValueError('Unknown case')
            db.execute('INSERT INTO reports VALUES (?,?,?,?,?,?)',(identity,case_id,stage,digest,body,now()))
            for index,text in enumerate(questions):
                qid=hashlib.sha256(encode([digest,index,text]).encode()).hexdigest()[:24]
                db.execute('INSERT INTO questions VALUES (?,?,?,?)',(identity,qid,index,text))
        return identity

    def attach_evidence(self,case_id,filename,content):
        """Store immutable bytes for one case; caller must authorize case access.

        Filename is display metadata, never a filesystem path. Upload scanning,
        public authentication and retention policy belong to the delivery service.
        """
        if not isinstance(filename,str) or not filename.strip():raise ValueError('Evidence filename required')
        if not isinstance(content,bytes) or not 0<len(content)<=25*1024*1024:
            raise ValueError('Evidence must contain 1 byte to 25 MiB')
        identity=str(uuid.uuid4());digest=hashlib.sha256(content).hexdigest()
        with self.connect() as db,db:
            if not db.execute('SELECT 1 FROM cases WHERE id=?',(case_id,)).fetchone():raise ValueError('Unknown case')
            db.execute('INSERT INTO evidence_objects VALUES (?,?,?,?,?,?)',
                       (identity,case_id,filename.strip(),digest,content,now()))
        return {'reference':'evidence:'+identity,'filename':filename.strip(),'sha256':digest,'bytes':len(content)}

    def read_evidence(self,case_id,reference):
        with self.connect() as db:
            return self._evidence(db,case_id,reference)

    @staticmethod
    def _evidence(db,case_id,reference):
        if not isinstance(reference,str) or not reference.startswith('evidence:'):
            raise ValueError('Invalid evidence reference')
        row=db.execute('SELECT * FROM evidence_objects WHERE id=? AND case_id=?',
                       (reference[len('evidence:'):],case_id)).fetchone()
        if not row:raise ValueError('Evidence does not belong to this case')
        record=dict(row)
        if hashlib.sha256(record['body']).hexdigest()!=record['sha256']:
            raise ValueError('Evidence content changed')
        return record

    def _check_evidence_refs(self,db,report_id,refs):
        row=db.execute('SELECT case_id FROM reports WHERE id=?',(report_id,)).fetchone()
        if not row:raise ValueError('Unknown report')
        linked=[]
        for ref in refs:
            if ref.startswith('evidence:'):
                item=self._evidence(db,row['case_id'],ref)
                linked.append({'reference':ref,'filename':item['filename'],'sha256':item['sha256'],
                               'bytes':len(item['body']),'content_integrity_verified':True})
        return linked

    def record_answer(self,report_id,question_id,text,evidence_refs=None):
        if not isinstance(text,str) or not text.strip():raise ValueError('Answer text is required')
        evidence_refs=[] if evidence_refs is None else evidence_refs
        if not isinstance(evidence_refs,list) or any(not isinstance(s,str) or not s.strip() for s in evidence_refs):
            raise ValueError('Evidence references must be nonempty text strings')
        with self.connect() as db,db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM questions WHERE report_id=? AND id=?',(report_id,question_id)).fetchone():
                raise ValueError('Question does not belong to this report')
            self._check_evidence_refs(db,report_id,evidence_refs)
            revision=db.execute('SELECT COALESCE(MAX(revision),0)+1 FROM answers WHERE report_id=? AND question_id=?',
                (report_id,question_id)).fetchone()[0]
            cursor=db.execute('INSERT INTO answers (report_id,question_id,revision,text,evidence_refs,created_at) VALUES (?,?,?,?,?,?)',
                (report_id,question_id,revision,text.strip(),encode(evidence_refs),now()))
            return {'answer_id':cursor.lastrowid,'revision':revision,'verification_status':'homeowner_reported_unverified'}

    def review_answer(self,report_id,answer_id,reviewer_id,decision,rationale,evidence_refs):
        """Record an operator decision; caller must authenticate/authorize the reviewer.

        A local reviewer ID is an audit label, not proof of identity. This does not
        certify an estimate, permit compliance or reusable jurisdiction knowledge.
        """
        if decision not in ('accepted','needs_clarification','rejected'):raise ValueError('Unknown review decision')
        if any(not isinstance(s,str) or not s.strip() for s in (reviewer_id,rationale)):
            raise ValueError('Reviewer identity and rationale are required')
        if not isinstance(evidence_refs,list) or not evidence_refs or any(not isinstance(s,str) or not s.strip() for s in evidence_refs):
            raise ValueError('Review needs supporting evidence references')
        with self.connect() as db,db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM answers WHERE id=? AND report_id=?',(answer_id,report_id)).fetchone()
            if not row:raise ValueError('Answer does not belong to this report')
            self._check_evidence_refs(db,report_id,evidence_refs)
            digest=hashlib.sha256(encode(dict(row)).encode()).hexdigest()
            cursor=db.execute('INSERT INTO answer_reviews (answer_id,answer_sha256,reviewer_id,decision,rationale,evidence_refs,created_at) VALUES (?,?,?,?,?,?,?)',
                (answer_id,digest,reviewer_id.strip(),decision,rationale.strip(),encode(evidence_refs),now()))
            return {'review_id':cursor.lastrowid,'decision':decision,'permit_compliance_verified':False}

    def followup_report(self,case_id,report_id):
        """Build a dated question-status supplement without rewriting the source report.

        Caller must authorize access to this case. This is not an updated price,
        bid-completeness certification or public delivery endpoint.
        """
        case=self.read_case(case_id)
        report=next((r for r in case['reports'] if r['id']==report_id),None)
        if report is None:raise ValueError('Report does not belong to this case')
        questions=[]
        for q in report['questions']:
            answer=q['answers'][-1] if q['answers'] else None
            review=answer['reviews'][-1] if answer and answer['reviews'] else None
            questions.append({'id':q['id'],'question':q['text'],'status':q['status'],
                'resolved':q['resolved'],'latest_answer':None if answer is None else {
                    'id':answer['id'],'revision':answer['revision'],'text':answer['text'],
                    'evidence_refs':answer['evidence_refs'],'created_at':answer['created_at']},
                'latest_review':None if review is None else {
                    k:review[k] for k in ('id','reviewer_id','decision','rationale','evidence_refs','created_at')}})
        return {'case_id':case_id,'report_id':report_id,'stage':report['stage'],
            'generated_at':now(),'source_report_sha256':report['source_sha256'],
            'kind':'question_status_supplement','questions':questions,
            'open_question_ids':[q['id'] for q in questions if not q['resolved']],
            'resolved_question_count':sum(q['resolved'] for q in questions),
            'source_report_changed':False,'estimate_released':False,'permit_compliance_verified':False,
            'notice':'Accepted answers resolve only the listed questions. Original findings, prices and scope remain unchanged until separately re-evaluated.'}

    def updated_report(self,case_id,report_id,finding_updates=None):
        """Regenerate the complete report from a current reviewed-answer snapshot.

        Explicit finding updates require the latest accepted answer and review.
        Prices, measurements and permit conclusions are not updated by this path.
        Caller must authenticate case access and the reviewer before using it.
        """
        case=self.read_case(case_id)
        source=next((r for r in case['reports'] if r['id']==report_id),None)
        if source is None:raise ValueError('Report does not belong to this case')
        report=copy.deepcopy(source['source_report'])
        questions={q['id']:q for q in source['questions']}
        changes=[];seen=set()
        for update in finding_updates or []:
            index=update['finding_index']
            if type(index) is not int or not 0<=index<len(report.get('findings',[])) or index in seen:
                raise ValueError('Unknown or duplicate finding update')
            seen.add(index);finding=report['findings'][index]
            if hashlib.sha256(encode(finding).encode()).hexdigest()!=update['finding_sha256']:
                raise ValueError('Finding changed since review')
            q=questions.get(update['question_id'])
            answer=q['answers'][-1] if q and q['answers'] else None
            review=answer['reviews'][-1] if answer and answer['reviews'] else None
            if (not q or not q['resolved'] or not review or
                    answer['id']!=update['answer_id'] or review['id']!=update['review_id']):
                raise ValueError('Finding update needs the latest accepted answer review')
            replacement=update['replacement']
            if (not isinstance(replacement,dict) or not replacement or
                    set(replacement)-{'title','detail','basis'} or
                    any(not isinstance(v,str) or not v.strip() for v in replacement.values())):
                raise ValueError('Only reviewed finding narrative may change')
            finding.update(replacement)
            changes.append({'finding_index':index,'original_finding_sha256':update['finding_sha256'],
                'question_id':q['id'],'answer_id':answer['id'],'answer_revision':answer['revision'],
                'review_id':review['id'],'reviewer_id':review['reviewer_id'],
                'evidence_refs':review['evidence_refs'],'replacement':copy.deepcopy(replacement)})
        # Keep original question identities in the return-visit section while the
        # normal report question list becomes the homeowner's outstanding actions.
        report['questions']=[q['text'] for q in source['questions'] if not q['resolved']]
        report['return_visit']={'source_report_id':report_id,'source_report_sha256':source['source_sha256'],
            'generated_at':now(),'finding_changes':changes,
            'questions':[{'id':q['id'],'text':q['text'],'status':q['status'],'resolved':q['resolved'],
                'answer':copy.deepcopy(q['answers'][-1]) if q['answers'] else None} for q in source['questions']],
            'prices_recalculated':False,'measurements_recalculated':False,
            'permit_compliance_verified':False,'estimate_released':False}
        report['meta']['revision_of']=report_id
        return report

    def read_case(self,case_id):
        with self.connect() as db:
            case=db.execute('SELECT * FROM cases WHERE id=?',(case_id,)).fetchone()
            if not case:raise ValueError('Unknown case')
            result=dict(case);result['reports']=[]
            for row in db.execute('SELECT * FROM reports WHERE case_id=? ORDER BY created_at,id',(case_id,)).fetchall():
                report=dict(row);body=report.pop('body')
                if hashlib.sha256(body.encode()).hexdigest()!=report['source_sha256']:
                    raise ValueError('Saved report content does not match its source hash')
                report['source_report']=json.loads(body);report['questions']=[]
                qrows=db.execute('SELECT * FROM questions WHERE report_id=? ORDER BY ordinal',(report['id'],)).fetchall()
                source_questions=report['source_report'].get('questions',[])
                if len(qrows)!=len(source_questions):raise ValueError('Saved questions do not match the report')
                for index,qrow in enumerate(qrows):
                    question=dict(qrow);question.pop('report_id');question['answers']=[]
                    expected=hashlib.sha256(encode([report['source_sha256'],index,source_questions[index]]).encode()).hexdigest()[:24]
                    if question['ordinal']!=index or question['text']!=source_questions[index] or question['id']!=expected:
                        raise ValueError('Saved question identity changed')
                    for arow in db.execute('SELECT * FROM answers WHERE report_id=? AND question_id=? ORDER BY revision',
                                          (report['id'],question['id'])).fetchall():
                        answer=dict(arow);digest=hashlib.sha256(encode(answer).encode()).hexdigest()
                        answer['evidence_refs']=json.loads(answer['evidence_refs']);answer['reviews']=[]
                        answer['linked_evidence']=self._check_evidence_refs(db,report['id'],answer['evidence_refs'])
                        for review_row in db.execute('SELECT * FROM answer_reviews WHERE answer_id=? ORDER BY id',(answer['id'],)).fetchall():
                            review=dict(review_row)
                            if review['answer_sha256']!=digest:raise ValueError('Reviewed answer changed')
                            review['evidence_refs']=json.loads(review['evidence_refs'])
                            review['linked_evidence']=self._check_evidence_refs(db,report['id'],review['evidence_refs'])
                            answer['reviews'].append(review)
                        answer['verification_status']='homeowner_reported_unverified';question['answers'].append(answer)
                    question['status']='answer_received_needs_review' if question['answers'] else 'awaiting_answer'
                    question['resolved']=False
                    if question['answers'] and question['answers'][-1]['reviews']:
                        decision=question['answers'][-1]['reviews'][-1]['decision']
                        question['status']='review_'+decision;question['resolved']=decision=='accepted'
                    report['questions'].append(question)
                result['reports'].append(report)
        result['permit_compliance_verified']=False;result['estimate_released']=False
        return result
