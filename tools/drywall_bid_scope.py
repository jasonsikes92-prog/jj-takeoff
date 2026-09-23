"""Build an unsent drywall quote request with explicit measurement and scope gaps."""
import copy
import hashlib
import json
import math
from pathlib import Path
from room_region_candidates import from_folder as room_regions
from company_scope_review import read_decisions


PRACTICE_KEYS=('drywall.deduct_window_door_openings','drywall.billing_waste_percent')


def estimating_practice(decisions=None,source=None):
    settings=decisions['settings'] if decisions is not None else {}
    deductions=settings.get(PRACTICE_KEYS[0]);waste=settings.get(PRACTICE_KEYS[1])
    if deductions is not None and type(deductions) is not bool:
        raise ValueError('Drywall opening deduction practice must be a boolean')
    if waste is not None and (type(waste) not in (int,float) or not math.isfinite(waste) or waste<0):
        raise ValueError('Drywall billing waste must be a finite nonnegative percentage')
    return {'deduct_window_door_openings':deductions,'billing_waste_percent':waste,
        'unresolved_settings':[key for key in PRACTICE_KEYS if settings.get(key) is None],
        'provenance':{key:decisions['provenance'][key] for key in PRACTICE_KEYS if settings.get(key) is not None},
        'source':source,'applied_to_reference_quantities':False,
        'supplier_acceptance_confirmed':False,'material_purchase_waste_percent':None}


def build_scope(rooms,practice=None):
    regions=rooms['regions'];ids=[r['id'] for r in regions]
    if not rooms.get('plan_sha256') or type(rooms.get('measurement_version')) is not int or rooms['measurement_version']<1:
        raise ValueError('Drywall bid scope needs a drawing and measurement revision')
    if len(ids)!=len(set(ids)):raise ValueError('Drywall bid scope needs unique room regions')
    items=[];unmeasured=[]
    for r in regions:
        name=r.get('room_use_review',{}).get('name') if r.get('room_use_confirmed') else None
        wall=r['wall_surface_reference'];ceiling=r['ceiling_surface']
        for surface,source,current,quantity in (
                ('walls',wall,'constant_height_geometric_reference','gross_wall_surface_sf'),
                ('ceiling',ceiling,'current_source_review','surface_area_sf')):
            amount=source.get(quantity) if source['status']==current else None
            identity=r['id']+':'+surface
            if amount is None:unmeasured.append(identity)
            items.append({'id':identity,'label':(name or 'Unconfirmed room')+' — '+surface,'region_id':r['id'],'room_name':name,'plan_pdf_page':r['page'],
                'surface':surface,'reference_quantity':amount,'reference_unit':'gross wall SF' if surface=='walls' else 'ceiling surface SF',
                'height_note_inches':r['ceiling_reference']['noted_height_inches'],
                'ceiling_note_status':r['ceiling_reference']['status'],'finish_scope_confirmed':False,
                'purchase_quantity':None,'bidder_status':None,'quoted_quantity':None,'quoted_unit':None,'unit_price':None,
                'quote_page_line':None,'inclusion_exclusion_notes':None})
            if surface=='ceiling' and amount is not None and source.get('surface_type')=='partitioned':
                items[-1]['ceiling_parts']=copy.deepcopy(source['parts'])
    requirements=[
        ('billing-basis','State whether pricing uses floor SF, actual wall-and-ceiling SF, sheets or a lump sum. Show the quantity and its basis; separate materials and labor or identify the complete package inclusions.'),
        ('board-specification','Identify board thickness, type, sheet size and location. List wet-area, fire-rated and other specialty-board inclusions or exclusions against the plans.'),
        ('finish-level','State the finish level, texture and included preparation for each area, including wet-area backer and any surfaces receiving another finish.'),
        ('complete-coverage','Verify the entire plan, including rooms without measured quantities, ceiling transitions, closets, soffits, returns and access openings. List omitted or separately priced areas.'),
        ('scope-inclusions','Identify hanging, fastening, tape, compound, corner bead, finishing, sanding, protection, cleanup and waste removal included in the quote.'),
        ('measurement-adjustments','State opening deductions and waste or overage separately. These references are gross geometry with no opening deductions or waste applied; they are not sheet counts.'),
        ('delivery-tax-access','State delivery, unloading, tax, lifts/scaffolding, access limitations and other additional charges.'),
        ('schedule-changes','State quote date, lead time and working duration. Identify assumptions that could cause a price change and price unresolved scope as explicit options or allowances.')]
    result={'title':'Drywall supply and installation quote request','status':'unsent_draft','sent':False,
        'plan_sha256':rooms['plan_sha256'],'measurement_version':rooms['measurement_version'],
        'room_source_sha256':rooms['source_sha256'],'items':items,'unmeasured_surface_ids':unmeasured,
        'scope_requirements':[{'id':key,'request':text,'bidder_response':None} for key,text in requirements],
        'source_exceptions':{'no_closed_room_regions':not regions,
            'unresolved_wall_measurement_count':len(rooms.get('unresolved_wall_measurements',[])),
            'unresolved_gap_ids':rooms.get('unresolved_gap_ids',[]),
            'unreviewed_ceiling_region_ids':rooms['ceiling_surface_review']['unreviewed_region_ids']},
        'quote_instructions':['For every surface ID, mark included, excluded, allowance or unknown and cite the quote page/line.',
            'A package price must identify all covered surface IDs and remaining plan scope. Do not add package and component prices for the same work.',
            'Measured surfaces do not establish that drywall is the selected finish. Confirm the material scope before using a reference quantity as a billable quantity.',
            'Missing quantities are unresolved, not zero. A subtotal of measured rooms is not complete-house scope.'],
        'requires_pricing_basis_review':True,'required_work':'complete',
        'estimating_practice':practice if practice is not None else estimating_practice(),
        'whole_house_drywall_quantity':None,'scope_coverage_certified':False,'ready_to_order':False}
    result['scope_sha256']=hashlib.sha256(json.dumps(result,sort_keys=True,allow_nan=False).encode()).hexdigest()
    return result


def from_folder(folder,state):
    folder=Path(folder);path=folder/'drywall_practice_review.json'
    raw=path.read_bytes() if path.exists() else None
    config=json.loads(raw) if raw is not None else None
    decisions=read_decisions(folder,config,state['plan_sha256']) if config is not None else None
    source=({'plan_sha256':state['plan_sha256'],'intake_sha256':config['intake_sha256'],
        'review_sha256':hashlib.sha256(raw).hexdigest()} if config is not None else None)
    practice=estimating_practice(decisions,source)
    result=build_scope(room_regions(folder,state),practice)
    if (path.read_bytes() if path.exists() else None)!=raw:
        raise ValueError('Drywall practice review changed during bid preparation')
    if config is not None and read_decisions(folder,config,state['plan_sha256'])!=decisions:
        raise ValueError('Drywall decisions changed during bid preparation')
    return result


def render_markdown(scope):
    def cell(value):return str(value if value is not None else 'Unconfirmed').replace('|','\\|').replace('\n',' ')
    def area(value):return f'{value:,.2f}' if value is not None else 'Not measured'
    lines=['# '+scope['title'],'','**Unsent draft. Complete plan scope and finish selections require confirmation.**','',
        'Measured quantities below are partial geometric references. Missing quantities are not zero.','',
        '| Room | PDF page | Surface | Reference quantity | Unit | Scope ID |',
        '| --- | ---: | --- | ---: | --- | --- |']
    for item in scope['items']:
        lines.append('| '+' | '.join(map(cell,[item['room_name'],item['plan_pdf_page'],item['surface'],
            area(item['reference_quantity']),item['reference_unit'],item['id']]))+' |')
    partitioned=[item for item in scope['items'] if item.get('ceiling_parts')]
    if partitioned:
        lines+=['','## Mixed ceiling breakdown','',
            'These parts are included in the ceiling quantities above; do not add them again.','',
            '| Scope ID | Part | Rise per 12 | Projected SF | Ceiling surface SF | Source basis |',
            '| --- | --- | ---: | ---: | ---: | --- |']
        for item in partitioned:
            for part in item['ceiling_parts']:
                lines.append('| '+' | '.join(map(cell,[item['id'],part['id'],part['rise_per_12'],
                    area(part['projected_area_sf']),area(part['surface_area_sf']),part['basis']]))+' |')
    practice=scope.get('estimating_practice',estimating_practice())
    deduction=practice['deduct_window_door_openings'];waste=practice['billing_waste_percent']
    deduction_text=('Do not deduct windows or doors from the estimating quantity.' if deduction is False else
        'Deduct windows and doors from the estimating quantity; opening areas still need measurement.' if deduction is True else
        'Opening-deduction practice is not established for this job.')
    waste_text=(f'Added billing waste: {waste:g}%.' if waste is not None else 'Added billing waste is not established for this job.')
    lines+=['','## Estimating basis','',deduction_text,waste_text,
        'These job estimating practices do not change the gross geometric references above. State whether your quote follows this basis and identify any difference explicitly.',
        'Billing waste is separate from material cutting waste and whole-sheet purchasing. No purchase-waste factor or sheet order is established here.']
    lines+=['','## Quote response','']+['- '+s for s in scope['quote_instructions']]
    lines+=['','## Scope and pricing questions','']+['- `requirement:'+r['id']+'`: '+r['request'] for r in scope['scope_requirements']]
    exceptions=scope['source_exceptions']
    if exceptions.get('no_closed_room_regions'):
        lines+=['','**No enclosed room geometry is currently available. All wall and ceiling quantities remain unresolved; an empty schedule does not mean zero drywall.**']
    lines+=['','## Remaining measurement work','',
        f"{len(scope['unmeasured_surface_ids'])} listed surface quantities remain unmeasured. "
        f"{len(exceptions['unreviewed_ceiling_region_ids'])} ceiling regions require scope review. "
        f"{exceptions['unresolved_wall_measurement_count']} drawn wall candidates remain unresolved. "
        f"{len(exceptions['unresolved_gap_ids'])} wall gaps require resolution.",'',
        'Review vault transitions and any partial-height walls against the plans. No complete-house quantity or order authorization is issued.','',
        f"Reference revision: {scope['measurement_version']}. Scope fingerprint: `{scope['scope_sha256']}`.",'']
    return '\n'.join(lines)
