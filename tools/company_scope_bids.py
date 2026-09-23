"""Produce unsent trade scope additions from current company-practice inputs."""
import copy
import json
from bid_comparison import scope_digest

TRADES={'exterior-hose-bibbs':'Plumbing','attic-hvac-walkway-platform':'Framing'}
TILE_RULES={
    'tile.material_waste_percent':('tile-material-waste','Add the saved tile cutting allowance to floor tile, wall tile and shower mosaic before rounding to whole purchase units.',
        'Pool identical products once; use actual box or sheet coverage and keep installation labor on its applicable measured-area basis.'),
    'tile.floor_underlayment_by_substrate':('tile-floor-underlayment','Where floor tile occurs, apply the saved underlayment practice for each substrate.',
        'Confirm floor areas by substrate, product and thickness, substrate preparation and installation requirements before pricing or ordering.'),
    'tile.shower_wall_backer':('tile-shower-wall-backer','Where tiled shower walls occur, apply the saved backer specification.',
        'Confirm shower wall areas, exact product and thickness, compatible waterproofing, joint and fastener treatment and installation requirements before pricing or ordering.'),
    'tile.shower_floor':('tile-shower-floor','Where tiled shower floors occur, apply the saved shower-floor assembly.',
        'Confirm floor geometry, drain location, slope, bed thickness, waterproofing and drain compatibility before calculating material quantities or pricing.'),
    'tile.edge_finish':('tile-edge-finish','Where tile has exposed edges, apply the saved edge finish.',
        'Measure exposed edges and identify profile, size, finish, corners, stock lengths and waste before pricing or ordering. Edge trim does not specify a shower waterproofing system.'),
}


FOUNDATION_RULES={
    'foundation.cmu_vertical_core_reinforcement':('cmu-vertical-reinforcement',
        'Include vertical bars and fill at the specified CMU cores.',
        'Confirm actual wall lengths, heights, openings, core layout, fill product and yield, bar lengths, laps, anchorage and project structural details before fixing quantities.'),
    'foundation.cmu_horizontal_reinforcement':('cmu-horizontal-reinforcement',
        'Include horizontal joint reinforcement in CMU walls.',
        'Confirm actual course count, ladder mesh product, laps, corners, intersections, openings and whole-piece purchasing.'),
    'foundation.cmu_caps_within_overall_height':('cmu-cap-height',
        'Account for caps within the specified overall masonry height.',
        'Confirm cap thickness and wall or pier height. Do not add cap height above the specified overall height.'),
}


def specification_items(review,rules,applicability):
    items=[];seen=set()
    def display(value):
        if value is None:return 'unconfirmed'
        if isinstance(value,bool):return 'yes' if value else 'no'
        if isinstance(value,dict):return '; '.join(k.replace('_',' ') + ': ' + display(v) for k,v in value.items())
        if isinstance(value,(str,int,float)):return str(value).replace('_',' ')
        raise ValueError('Unsupported trade specification value')
    for spec in review.get('specifications',[]):
        key=spec['source_rule']
        if key not in TILE_RULES.keys()|FOUNDATION_RULES.keys() or key in seen:raise ValueError('Trade specification is duplicate or unsupported')
        seen.add(key)
        if spec.get('intake_sha256')!=review['intake_sha256'] or not spec.get('provenance'):
            raise ValueError('Trade specification needs its frozen intake provenance')
        if key not in rules:continue
        identity,intro,remaining=rules[key]
        items.append({'id':identity,'label':intro+' Saved specification: '+display(spec['value'])+'. '+remaining,
            'reference_quantity':None,'reference_unit':None,'purchase_quantity':None,
            'source_rule':key,'specification':copy.deepcopy(spec['value']),
            'provenance':copy.deepcopy(spec['provenance']),'remaining':[remaining],
            'applicability':applicability})
    return items

def building_area_items(draft):
    items=[]
    for row in draft['rows']:
        if row.get('parent','').strip().upper()!='INPUTS':continue
        sources=row.get('quantity_sources',[])+[q for q in draft.get('pending_quantities',[])
            if str(row['excel_row']) in list(map(str,q.get('template_rows',[])))]
        sources=[q for q in sources if q['id'].startswith('candidate-building-area-')]
        if not sources:continue
        if len(sources)!=1:raise ValueError('Ambiguous building area source in framing bid')
        source=sources[0];quantity=row.get('draft_quantity')
        amount='Pending boundary and scope review' if quantity is None else f'{quantity:,.2f} SF reviewed draft reference'
        total=source['id']=='candidate-building-area-total'
        remaining=['Confirm complete building coverage and contractor billing basis. Identify framed decks separately from slab porches; gross area does not establish labor layers.']
        if total:remaining.append('This total includes the listed component areas; do not add the total to its components.')
        items.append({'id':'building-area-'+str(row['excel_row']),
            'label':row['name']+': '+amount+'. '+' '.join(remaining),
            'reference_quantity':quantity,'reference_unit':'SF','purchase_quantity':None,
            'source_row_id':row['row_id'],'measurement_ids':copy.deepcopy(source['measurement_ids']),
            'remaining':remaining,'applicability':'scope_review_required' if quantity is None else 'reviewed_draft_reference'})
    return items


def build_scopes(draft):
    review=draft.get('company_scope_review')
    if not review or not draft.get('plan_sha256') or type(draft.get('measurement_version')) is not int:
        raise ValueError('Company bid scope needs a source-bound company scope review')
    if draft['measurement_version']<1 or not review.get('intake_sha256'):
        raise ValueError('Company bid scope requires a positive revision and intake source')
    identities=review['scope_ids']
    if len(set(identities))!=len(identities) or any(i not in TRADES for i in identities):
        raise ValueError('Company scope identities are duplicate or unsupported')
    tile=specification_items(review,TILE_RULES,'conditional_on_project_tile_scope')
    underlayment=draft.get('tile_underlayment_review')
    if underlayment:
        if (underlayment['plan_sha256']!=draft['plan_sha256']
                or underlayment['measurement_version']!=draft['measurement_version']
                or underlayment['intake_sha256']!=review['intake_sha256']):
            raise ValueError('Tile underlayment quantities belong to another source revision')
        matches=[item for item in tile if item['id']=='tile-floor-underlayment']
        if len(matches)!=1:raise ValueError('Measured tile fields need their saved underlayment specification')
        item=matches[0];item['measured_fields']=copy.deepcopy(underlayment)
        for field in underlayment['fields']:
            item['label']+=f" Measured field {field['id']}: {field['net_sf']:.2f} SF on {field['substrate'].replace('_',' ')}; {field['underlayment'].replace('_',' ')}."
        item['label']+=' These fields do not establish complete house coverage or purchase quantities.'
    groups={'Tile':tile} if tile else {}
    foundation=specification_items(review,FOUNDATION_RULES,'confirmed_cmu_material_practice_requires_project_detail_review')
    if foundation:groups['Foundation']=foundation
    inputs=[(row['row_id'],q) for row in draft['rows'] for q in row.get('assembly_inputs',[])]
    inputs += [(None,q) for q in draft.get('pending_quantities',[])]
    for identity in identities:
        matches=[(row,q) for row,q in inputs if q['id']==identity]
        if len(matches)!=1:raise ValueError('Company bid scope needs exactly one current input: '+identity)
        row,item=matches[0]
        if item.get('source_snapshot',{}).get('intake_sha256')!=review['intake_sha256']:
            raise ValueError('Company scope input belongs to another intake revision')
        if item.get('measured_from_plan') is not False or item.get('locations')!=[]:
            raise ValueError('Company allowance cannot claim measured locations')
        count=item['quantity']
        if identity=='exterior-hose-bibbs':
            if type(count) is not int or count<0 or item['unit']!='EA':raise ValueError('Whole hose-bibb reference count required')
            request=(f'Include {count} exterior hose bibbs. Confirm locations, product, piping, connections and installation, '
                     'and whether these are already included in the base plumbing contract.' if count else
                     'The saved exterior hose-bibb count is zero. Exclude these from material and installation charges unless the project scope changes.')
        else:
            if count is not None:raise ValueError('Attic platform dimensions are not established by a company practice')
            request=('Include the walkway from attic access to the HVAC equipment and an equipment platform in framing. '
                     'Provide the route, dimensions, materials, supports and installation scope before fixing the quantity or price.')
        groups.setdefault(TRADES[identity],[]).append({'id':identity,'label':request,
            'reference_quantity':count,'reference_unit':item['unit'],'purchase_quantity':None,
            'source_row_id':row,'source_rule':item['source_rule'],'provenance':copy.deepcopy(item.get('provenance')),
            'remaining':copy.deepcopy(item['remaining']),'applicability':'included' if count!=0 else 'zero_saved_count'})
    conditions=review.get('unresolved_conditions',[])
    if any(c!='attic_HVAC' for c in conditions):raise ValueError('Unsupported company-scope condition')
    if 'attic_HVAC' in conditions:
        if 'attic-hvac-walkway-platform' in identities:raise ValueError('Attic scope cannot be both included and unresolved')
        groups.setdefault('Framing',[]).append({'id':'attic-hvac-applicability',
            'label':'Confirm whether HVAC equipment is in the attic. If applicable, include the access walkway and equipment platform in framing and supply the route, dimensions, materials and supports. Otherwise identify why this scope does not apply.',
            'reference_quantity':None,'reference_unit':None,'purchase_quantity':None,'applicability':'unresolved'})
    areas=building_area_items(draft)
    if areas:groups.setdefault('Framing',[]).extend(areas)
    scopes=[]
    for trade,items in sorted(groups.items()):
        scope={'title':trade+' — company scope additions','trade':trade,'status':'unsent_draft','sent':False,
            'plan_sha256':draft['plan_sha256'],'measurement_version':draft['measurement_version'],
            'company_intake_sha256':review['intake_sha256'],'items':items,
            'scope_requirements':[
                {'id':'package-inclusion','request':'Identify which listed items are included in the base trade contract. Do not charge a listed item again if it is already included.','bidder_response':None},
                {'id':'quantity-and-price-basis','request':'State quantity, billing unit and rate or the exact scope of a lump sum. Identify unresolved dimensions and allowances; do not treat missing quantities as zero.','bidder_response':None},
                {'id':'exclusions-and-additions','request':'List exclusions, delivery, tax and installation inclusions, and conditions that could change the price.','bidder_response':None}],
            'limitations':['These additions supplement the full plans and trade scope; they are not a complete trade bid request.',
                'Company allowance counts are not located plan measurements. Product specifications and current prices remain unconfirmed.'],
            'scope_coverage_certified':False,'ready_to_order':False,'purchase_authorized':False}
        scope['scope_sha256']=scope_digest(scope);scopes.append(scope)
    return {'plan_sha256':draft['plan_sha256'],'measurement_version':draft['measurement_version'],
        'company_intake_sha256':review['intake_sha256'],'scopes':scopes,'sent':False}

def render_markdown(scope):
    lines=['# '+scope['title'],'','Unsent draft. Use with the full plans and trade scope.','']
    for item in scope['items']:
        lines += ['- **'+item['id']+'**: '+item['label']]
    lines += ['','## Bid response','',
        'For every item, identify inclusion, exclusion or allowance and cite the quote page or line. Resolve conditional scope explicitly.','']
    lines += ['- '+r['request'] for r in scope['scope_requirements']]
    lines += ['','No order or final purchase quantity is authorized.','']
    return '\n'.join(lines)

def from_folder(folder):
    import sys
    import threading
    import urllib.request
    from pathlib import Path
    sys.path.insert(0,str(Path(__file__).resolve().parent/'viewer'))
    from measurement_store import MeasurementStore
    from measurement_review import make_server
    server=make_server(MeasurementStore(folder));worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/api/company-scope-bids',timeout=60) as response:
            result=json.load(response)
    finally:server.shutdown();server.server_close();worker.join()
    return result

def write_drafts(result,output):
    from pathlib import Path
    out=Path(output)
    if out.exists():raise FileExistsError('Existing bid drafts preserved; choose a new output folder')
    out.mkdir(parents=True)
    (out/'index.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    for scope in result['scopes']:
        name=scope['trade'].lower()
        (out/(name+'.json')).write_text(json.dumps(scope,indent=2)+'\n',encoding='utf-8')
        (out/(name+'_DRAFT.md')).write_text(render_markdown(scope),encoding='utf-8')
    return [scope['trade'].lower()+'_DRAFT.md' for scope in result['scopes']]

def main():
    import argparse
    from pathlib import Path
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();out=Path(args.output)
    if out.exists():raise FileExistsError('Existing bid drafts preserved; choose a new output folder')
    result=from_folder(args.job);write_drafts(result,out)
    print(json.dumps({'drafts':len(result['scopes']),'sent':False,'output':str(out.resolve())}))

if __name__=='__main__':main()
