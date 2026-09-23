"""Select reviewed public requirement evidence without transferring private site facts."""
from datetime import date


def requirements_context(project, records, as_of):
    today=date.fromisoformat(as_of);candidates=[];unresolved=[];seen=set()
    basis=date.fromisoformat(project['code_basis_date']) if project.get('code_basis_date') else None
    for record in records:
        identity=record['id']
        if not identity or identity in seen:raise ValueError('Requirement record IDs must be unique')
        seen.add(identity)
        if record['state']!=project.get('state'):continue
        # User answers and parcel approvals are never reusable public rules.
        if record.get('source_kind')!='official_public' or record.get('review_status')!='reviewed':continue
        if record.get('parcel_specific') is not False:continue
        scope=record['jurisdiction_scope']
        if scope not in ('state','local'):raise ValueError('Unknown jurisdiction scope')
        reasons=[]
        if scope=='local':
            if record['authority_id']!=project.get('authority_id'):continue
            if project.get('authority_verified') is not True:
                reasons.append('Confirm permitting authority; mailing city is insufficient')
        checked=date.fromisoformat(record['checked_on']);due=date.fromisoformat(record['review_due'])
        if due<checked:raise ValueError('Review due date precedes verification')
        if checked>today or due<today:reasons.append('Refresh official source')
        start=date.fromisoformat(record['effective_from']) if record.get('effective_from') else None
        end=date.fromisoformat(record['effective_to']) if record.get('effective_to') else None
        if start is not None and end is not None and end<start:raise ValueError('Invalid effective date range')
        if start is None:reasons.append('Confirm effective dates and applicability of this published document')
        if basis is None:reasons.append('Confirm project code-basis date and transition provisions')
        elif (start is not None and basis<start) or (end is not None and basis>end):continue
        for key,expected in record.get('conditions',{}).items():
            actual=project.get('conditions',{}).get(key)
            if actual is None:reasons.append('Confirm site condition: '+key)
            elif type(expected) is bool and type(actual) is not bool:
                reasons.append('Confirm site condition as true or false: '+key)
            elif actual!=expected:break
        else:
            item={'id':identity,'topic':record['topic'],'summary':record['summary'],
                'source_url':record['source_url'],'authority':record['authority'],
                'checked_on':record['checked_on'],'effective_from':record.get('effective_from'),
                'effective_to':record.get('effective_to'),'review_issues':reasons,
                'status':'needs_review' if reasons else 'dated_source_candidate'}
            for key in ('authority_id','source_page','source_sha256','published_revision','effective_date_note'):
                if key in record:item[key]=record[key]
            (unresolved if reasons else candidates).append(item)
    return {'state':project.get('state'),'as_of':as_of,'candidates':candidates,'needs_review':unresolved,
        'missing_project_fields':[key for key in ('state','code_basis_date','authority_id') if not project.get(key)],
        'local_authority_verified':project.get('authority_verified') is True and bool(project.get('authority_id')),
        'coverage_complete':False,'permit_compliance_verified':False,
        'note':'Candidate source evidence is not an approved code basis or a complete permit checklist.'}
