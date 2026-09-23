"""Prepare an unsent room-by-room flooring request without guessing selections."""
import copy
import json
import math
from pathlib import Path
from shapely.geometry import Polygon
from bid_comparison import scope_digest
from room_region_candidates import from_folder as room_regions
from company_scope_review import read_decisions

PRACTICES=('flooring.floating_excludes_fixed_cabinets_and_island',
           'flooring.floating_material_waste_pct','flooring.floating_labor_quantity_basis',
           'tile.floor_underlayment_by_substrate','tile.material_waste_percent')


def build_scope(rooms,practices=None,selection_review=None):
    if not rooms.get('plan_sha256') or type(rooms.get('measurement_version')) is not int or rooms['measurement_version']<1:
        raise ValueError('Flooring scope needs a plan and current measurement revision')
    selection_review=selection_review or {'selections':{},'unresolved':[]}
    items=[];seen=set();shapes=[]
    for region in rooms['regions']:
        identity=region['id'];scale=region['points_per_foot'];page=region['page']
        if identity in seen or not identity:raise ValueError('Flooring regions must have unique identities')
        seen.add(identity)
        if type(scale) not in (int,float) or not math.isfinite(scale) or scale<=0:
            raise ValueError('Flooring regions require a positive finite scale')
        polygon=Polygon(region['points'],region['holes'])
        if not polygon.is_valid or polygon.is_empty or polygon.area<=0:
            raise ValueError('Flooring region geometry is invalid')
        for other_page,other_scale,other in shapes:
            if page==other_page and (not math.isclose(scale,other_scale,rel_tol=1e-12)
                                    or polygon.intersection(other).area>1e-7):
                raise ValueError('Flooring regions overlap or disagree on scale')
        shapes.append((page,scale,polygon))
        printed=[label['text'] for label in region['printed_labels']]
        reviewed=region.get('room_use_review',{}) if region.get('room_use_confirmed') else {}
        name=reviewed.get('name') or ' / '.join(printed) or 'Unlabeled region'
        area=None if region.get('boundary_source_issues') else polygon.area/scale**2
        items.append({'id':identity+':floor','region_id':identity,'label':name+' — floor',
            'room_name':name,'room_name_basis':'source_review' if reviewed else 'printed_labels' if printed else 'unresolved',
            'plan_pdf_page':page,'reference_quantity':area,'reference_unit':'boundary floor SF',
            'reference_basis':'Enclosed region geometry; finish faces, thresholds, fixtures and transitions still require review.',
            'finish_selection':copy.deepcopy(selection_review['selections'].get(identity)),
            'substrate':None,'finish_scope_confirmed':False,
            'purchase_quantity':None,'bidder_status':None,'quoted_quantity':None,'quoted_unit':None,
            'unit_price':None,'quote_page_line':None,'inclusion_exclusion_notes':None})
    requirements=[
        ('room-selections','Identify each room finish, exact product, substrate and installation scope from the plans and selections. List undecided rooms as explicit alternatives or allowances; a bathroom label alone does not specify tile.'),
        ('finish-boundaries','Identify material transitions, thresholds, closets, cabinets, islands, shower and tub footprints. State each deduction and whether flooring continues underneath fixed cabinets. Do not count open-plan labels as separate copies of one area.'),
        ('substrate-preparation','Identify leveling, moisture testing, preparation, underlayment/backer, bedding, fasteners, joint treatment, waterproofing and transitions included for each substrate. Keep shower assemblies distinct from ordinary floor underlayment.'),
        ('purchase-basis','State product coverage, cutting waste, carton/sheet rounding and shared-product pooling. Keep measured installation labor separate from material purchase overage.'),
        ('scope-inclusions','Identify adhesives, grout, trim, profiles, installation, protection, cleanup and waste removal included or excluded. Coordinate baseboard and shoe molding ownership with the trim quote.'),
        ('price-and-delivery','State unit rates or the exact lump-sum coverage, delivery, tax, lead time and quote date. Identify conditions that could change the price.'),
        ('complete-coverage','Review the complete plan and selections, including areas absent from this room schedule. List omitted, unmeasured and separately quoted work.')]
    result={'title':'Flooring supply and installation quote request','trade':'Flooring','status':'unsent_draft','sent':False,
        'plan_sha256':rooms['plan_sha256'],'measurement_version':rooms['measurement_version'],
        'room_source_sha256':rooms['source_sha256'],'items':items,
        'estimating_practices':copy.deepcopy(practices or {}),
        'selection_review':copy.deepcopy(selection_review),
        'unresolved_finish_region_ids':[i['region_id'] for i in items if i['finish_selection'] is None],
        'unmeasured_region_ids':[i['region_id'] for i in items if i['reference_quantity'] is None],
        'source_exceptions':{'no_closed_room_regions':not items,
            'unresolved_wall_measurements':copy.deepcopy(rooms.get('unresolved_wall_measurements',[])),
            'unresolved_gap_ids':copy.deepcopy(rooms.get('unresolved_gap_ids',[]))},
        'scope_requirements':[{'id':key,'request':text,'bidder_response':None} for key,text in requirements],
        'whole_house_flooring_quantity':None,'scope_coverage_certified':False,'ready_to_order':False}
    result['scope_sha256']=scope_digest(result)
    return result


def from_folder(folder,state):
    folder=Path(folder);path=folder/'company_scope_review.json';practices={}
    if path.exists():
        config=json.loads(path.read_bytes());decisions=read_decisions(folder,config,state['plan_sha256'])
        practices={key:{'value':copy.deepcopy(decisions['settings'][key]),
                       'provenance':copy.deepcopy(decisions['provenance'][key]),
                       'intake_sha256':config['intake_sha256']}
                   for key in PRACTICES if key in decisions['settings']}
    rooms=room_regions(folder,state,include_surfaces=False)
    from flooring_selection_review import read_selections
    return build_scope(rooms,practices,read_selections(folder,rooms))


def render_markdown(scope):
    def cell(value):return str(value).replace('|','\\|').replace('\n',' ')
    lines=['# '+scope['title'],'','Unsent draft. Room geometry is a reference, not a finished-floor purchase quantity.','',
           '| Room | PDF page | Boundary SF | Finish / substrate | Scope ID |',
           '| --- | ---: | ---: | --- | --- |']
    for item in scope['items']:
        quantity=item['reference_quantity'];area=f'{quantity:.2f}' if quantity is not None else 'Unresolved'
        selection=item['finish_selection']
        finish=(selection['product']+' (saved selection '+selection['captured_at']+'); substrate unconfirmed') if selection else 'Unconfirmed'
        lines.append('| '+' | '.join(cell(v) for v in (item['room_name'],item['plan_pdf_page'],area,finish,item['id']))+' |')
    if not scope['items']:lines+=['','No enclosed room geometry is available. An empty schedule does not mean zero flooring.']
    lines+=['','For every scope ID, identify included, excluded, allowance or unknown and cite the quote page/line.',
            'Do not infer material selections from room names. List additional plan scope. Avoid charging both a package and its components.','',
            'Saved selections are dated source records; confirm they still apply. Historical selection quantities and prices are not included in this request.',
            '## Saved estimating practices','']
    lines += ['- '+key+': '+json.dumps(value['value'],ensure_ascii=False) for key,value in scope['estimating_practices'].items()]
    if not scope['estimating_practices']:lines+=['No frozen company practices were available for this draft.']
    lines+=['','Apply practices only to the matching selected finish and substrate; they do not establish a room selection.','',
            '## Scope response','']+['- '+r['request'] for r in scope['scope_requirements']]
    lines+=['','Complete-house scope, finish quantities and purchase quantities remain unresolved.',
            'Scope fingerprint: '+scope['scope_sha256'],'']
    return '\n'.join(lines)
