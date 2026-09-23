"""Request opening framing explicitly without inventing lumber quantities."""
import copy
from bid_comparison import scope_digest
from opening_schedule import from_folder as opening_schedule


def build_scope(schedule):
    if not schedule.get('plan_sha256') or type(schedule.get('measurement_version')) is not int or schedule['measurement_version']<1:
        raise ValueError('Opening framing requires a drawing and positive measurement revision')
    records=[];items=[];seen=set();unresolved=[]
    def register(identity):
        if not isinstance(identity,str) or not identity.strip() or identity in seen:
            raise ValueError('Unique physical opening identities required')
        seen.add(identity)
    def add(identity,work,label):
        items.append({'id':identity+':'+work,'opening_id':identity,'work':work,'label':label,
            'reference_quantity':None,'purchase_quantity':None,'cost_owner':'base_framing_package',
            'response_basis':'Identify inclusion in the base framing package and separately price exclusions only.'})
    roles={'window','interior_door','special_interior_door','exterior_door','open_passage'}
    for opening in schedule['openings']:
        identity=opening['opening_id'];register(identity)
        current=opening['review_status']=='current_source_review' and opening.get('role') in roles
        role=opening['role'] if current else None
        configuration=opening.get('door_configuration') if current else None
        record={'opening_id':identity,'location':opening.get('location') if current else None,
            'role':role,'configuration':configuration,'plan_pdf_page':opening['page'],
            'printed_tag':opening['tag'],'printed_nominal_size':copy.deepcopy(opening.get('printed_nominal_size')),
            'source_sha256':opening['source_sha256'],'source_status':opening['review_status'],
            'reference_assembly_count':1 if current else None,'lumber_quantity':None}
        records.append(record)
        if not current:
            unresolved.append(identity)
            add(identity,'source-review','Resolve the opening location, role and full framing assembly from the current drawing.')
            continue
        add(identity,'header','Identify header size, plies, cut length, bearing and connections from the applicable framing detail.')
        add(identity,'jamb-supports','Identify king and jack studs on each side, lengths, support and any shared corner/intersection members.')
        add(identity,'above-opening','Include framing between the header and top plates; identify short studs, blocking and connections, or document why none are needed.')
        if role=='window':
            add(identity,'rough-sill','Include rough sill member size, number, length and connections for this window assembly.')
            add(identity,'below-window','Include short studs below the rough sill; identify sill elevation, spacing and cut lengths.')
        if configuration=='pocket':
            add(identity,'pocket-frame-interface','Reconcile the selected pocket kit, full cavity width, split studs, header and supporting lumber; identify kit ownership and do not buy it twice.')
        elif role=='special_interior_door' and not configuration:
            unresolved.append(identity)
            add(identity,'special-frame-interface','Resolve the door operation and any kit/cavity framing before assigning supporting lumber.')
    for label in schedule['stale_or_missing_label_ids']:
        identity='opening-'+label.removeprefix('printed-tag-');register(identity);unresolved.append(identity)
        add(identity,'source-review','Previously reviewed opening is missing from the current schedule; reconcile its framing scope.')
    for identity,label in (
            ('other-openings','Check all plan sheets for untagged openings, gable windows, attic access and other openings absent from this schedule; identify their framing separately.'),
            ('package-ownership','Confirm these items are included in the overall framing material/labor package; identify supply, installation and separately priced exclusions without duplicating package costs.'),
            ('dimensions-and-details','Reconcile manufacturer rough openings, finished elevations and framing details before cutting. Nominal tags and drawn gaps are not cut dimensions.')):
        items.append({'id':'framing:'+identity,'work':'scope_confirmation','label':label,'purchase_quantity':None})
    result={'title':'Opening framing — draft package scope','trade':'Framing','status':'unsent_draft',
        'plan_sha256':schedule['plan_sha256'],'measurement_version':schedule['measurement_version'],
        'opening_review_sha256':schedule['review_sha256'],'opening_schedule_sha256':scope_digest(schedule),
        'openings':records,'items':items,'unresolved_opening_ids':unresolved,
        'source_enumeration_current':bool(records) and not unresolved,
        'complete_trade_coverage':False,'scope_coverage_certified':False,'ready_to_order':False,'sent':False,
        'instructions':['Respond to every scope ID with included, excluded, allowance or unknown and cite the quote page/line.',
            'Open passages still require framing review even though they do not receive doors or hardware.',
            'Window groups are single framed assemblies; do not multiply framing by the individual window-unit count.',
            'These are scope requirements, not member counts, engineering approval or additional charges. Identify any component that is unnecessary and document the applicable detail.',
            'Include stock lengths, waste, tax and delivery in the framing package basis; identify anything charged separately.'],
        'limitations':copy.deepcopy(schedule['limitations'])}
    result['scope_sha256']=scope_digest(result)
    return result


def from_folder(folder,state):
    return build_scope(opening_schedule(folder,state,include_company_policy=False))


def render_markdown(scope):
    def cell(value):return str(value if value is not None else 'Unconfirmed').replace('|','\\|').replace('\n',' ')
    lines=['# '+scope['title'],'','**Unsent draft — opening framing only; quantities and full trade coverage remain unresolved.**','',
        'Drawing SHA-256: `'+scope['plan_sha256']+'`',
        'Measurement revision: '+str(scope['measurement_version']),
        'Scope fingerprint: `'+scope['scope_sha256']+'`','',
        '| Opening / location | PDF page | Nominal tag | Role | Source status |',
        '| --- | ---: | --- | --- | --- |']
    for row in scope['openings']:
        lines.append('| '+' | '.join(map(cell,[row['opening_id']+' / '+(row['location'] or 'Needs review'),
            row['plan_pdf_page'],row['printed_tag'],row['role'],row['source_status']]))+' |')
    lines+=['','## Required framing responses','']
    lines+=['- `'+i['id']+'`: '+cell(i['label']) for i in scope['items']]
    lines+=['','## Package instructions','']+['- '+i for i in scope['instructions']]
    lines+=['','## Source limitations','']+['- '+i for i in scope['limitations']]
    return '\n'.join(lines)+'\n'
