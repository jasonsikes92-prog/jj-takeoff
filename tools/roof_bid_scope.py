"""Build an unsent roofing quote request from current net surface references."""
import hashlib
import json
import math
from roof_partition_state import from_folder as roof_partition


def build_scope(audit):
    if (not audit.get('plan_sha256') or type(audit.get('measurement_version')) is not int
            or audit['measurement_version']<1 or not audit.get('measurements_sha256')):
        raise ValueError('Roof bid needs a source drawing and current measurement revision')
    faces=audit.get('face_references',[]);ids=[f['measurement_id'] for f in faces]
    if not faces or len(ids)!=len(set(ids)):raise ValueError('Unique resolved roof faces required')
    items=[]
    for f in faces:
        area=f['surface_area_sf']
        if type(area) not in (int,float) or not math.isfinite(area) or area<=0:
            raise ValueError('Roof references require finite positive surface areas')
        items.append({'id':'roof:'+f['measurement_id'],'measurement_id':f['measurement_id'],
            'label':f['label'],'plan_pdf_page':f['page'],'surface':'roof','reference_quantity':area,'reference_unit':'SF',
            'quantity_basis':'net sloped roof surface; parent cutouts already deducted',
            'reference_roofing_squares':area/100,'square_definition_sf':100,
            'deducted_cutout_ids':f['cutout_ids'],'pitch_is_inferred':f['pitch_is_inferred'],
            'pitch_evidence':f['pitch_evidence'],
            **({'pitch_candidates':f['pitch_candidates']} if 'pitch_candidates' in f else {}),
            'roofing_system':None,'manufacturer_product':None,'waste_percent':None,
            'purchase_unit':None,'coverage_per_purchase_unit':None,'purchase_quantity':None,
            'bidder_status':None,'quoted_quantity':None,'quoted_unit':None,'unit_price':None,
            'quote_page_line':None,'inclusion_exclusion_notes':None})
    requirements=[
        ('material-allocation','Identify the roofing system and manufacturer/product for every face ID. '
            'Group identical systems explicitly; identify shingle, metal or other portions and any options.'),
        ('waste-and-purchase-units','State material waste separately from measured area. For shingles, state bundles per square '
            'or exact bundle coverage; for metal, supply panel profiles, coverage widths and cut lengths. '
            'Round each material to its actual sold unit. Area divided by nominal panel area is not a panel cut list.'),
        ('billing-basis','State whether each price is per measured roofing square, shingle quantity including waste, '
            'purchased bundles/panels, installed LF or lump sum. One roofing square is 100 SF. '
            'Show quoted quantity, unit and rate; do not treat these geometric references as purchase quantities.'),
        ('package-inclusions','Identify labor, underlayment, starter, ridge/hip caps, fasteners, flashing, ventilation, '
            'sealants, protection and cleanup included in each package. Identify drip edge and pipe boots explicitly. '
            'Avoid charging separately for an item already covered by the package.'),
        ('edges-and-penetrations','Confirm eave/rake/valley/ridge lengths, wall transitions and penetration counts, '
            'including pipe boots, roof vents and any special flashing. These accessory quantities are not established by roof area.'),
        ('substrate-and-access','Identify roof-deck/sheathing work, repair allowances, substrate requirements, '
            'lifts/scaffolding and other access or equipment charges. Distinguish framing work from roofing scope.'),
        ('source-and-coverage-review','Check the whole plan and all roof levels. Review inferred pitches, unresolved '
            'coverage regions and any overlaps; identify missing faces or quantities. State exclusions rather than treating missing scope as zero.'),
        ('delivery-tax-schedule','State delivery, unloading, tax, quote date, lead time, installation duration and '
            'conditions that could change the price. Give separately identified options or allowances for unresolved selections.')]
    overlaps=audit.get('overlap_cells',[])
    overlap_ids=[r.get('id') for r in overlaps]
    if len(set(overlap_ids))!=len(overlap_ids) or any(not i for i in overlap_ids):
        raise ValueError('Located roof overlap regions require unique IDs')
    for region in overlaps:
        sources=region['source_ids']
        if len(set(sources))<2 or not set(sources).issubset(ids):
            raise ValueError('Roof overlap references missing roof faces')
        requirements.append((region['id'],
            f"PDF page {region['page']}, overlap {region['id']}: {region['area_sf']:.6f} projected SF "
            f"shared by {', '.join(sources)}. Identify whether these are separate roof levels or duplicate "
            'traces. For each face, state the included installed material boundary, underlap and flashing, '
            'and cite the drawing/detail or quote clarification. Do not deduct projected overlap automatically.'))
    result={'title':'Roofing supply and installation quote request','status':'unsent_draft','sent':False,
        'plan_sha256':audit['plan_sha256'],'measurement_version':audit['measurement_version'],
        'source_geometry_sha256':audit['measurements_sha256'],
        'coverage_review_sha256':audit.get('coverage_review_sha256'),'items':items,
        'scope_requirements':[{'id':key,'request':request,'bidder_response':None} for key,request in requirements],
        'source_exceptions':{'coverage':audit['coverage'],'overlap_excess_sf':audit['overlap_excess_sf'],
            **({'overlap_regions':overlaps,'overlapped_footprint_sf':audit['overlapped_footprint_sf']} if overlaps else {}),
            **({'unresolved_source_outlines':audit['unresolved_source_outlines']} if 'unresolved_source_outlines' in audit else {}),
            'inferred_pitch_face_ids':[i['id'] for i in items if i['pitch_is_inferred']],
            'material_allocations_unconfirmed':True,'accessory_quantities_unconfirmed':True},
        'quote_instructions':['For each face and scope requirement, mark included, excluded, allowance or unknown and cite the quote page/line.',
            'A package price must identify its covered face IDs, accessories and remaining plan scope.',
            'Cutout outlines are deductions from their parent face, not additional roof faces to purchase.',
            'Missing specifications, quantities and rates remain unresolved, not zero.'],
        'requires_pricing_basis_review':True,'required_work':'complete','purchase_quantity':None,'whole_roof_order_quantity':None,
        'scope_coverage_certified':False,'ready_to_order':False}
    result['scope_sha256']=hashlib.sha256(json.dumps(result,sort_keys=True,allow_nan=False).encode()).hexdigest()
    return result


def from_folder(folder):
    scope=build_scope(roof_partition(folder))
    from roof_edge_scope import from_folder as edge_scope
    edges=edge_scope(folder,scope['plan_sha256'],scope['measurement_version'])
    if edges is not None:
        scope['items'].extend(edges['items'])
        scope['edge_reference_review']={k:v for k,v in edges.items() if k!='items'}
        from bid_comparison import scope_digest
        scope['scope_sha256']=scope_digest(scope)
    return scope


def render_markdown(scope):
    def cell(value):return str(value).replace('|','\\|').replace('\n',' ')
    lines=['# '+scope['title'],'','**Unsent draft. Roofing selections and complete installed scope require confirmation.**','',
        'Net sloped areas below already exclude parent cutouts. A roofing square is 100 SF. '
        'No waste, purchase-unit rounding, accessory quantity or price has been applied.','',
        '| Roof face | PDF page | Net sloped SF | Roofing squares | Pitch basis | Scope ID |',
        '| --- | ---: | ---: | ---: | --- | --- |']
    for item in scope['items']:
        if item.get('surface')=='roof_edge':continue
        lines.append('| '+' | '.join(map(cell,[item['label'],item['plan_pdf_page'],
            f"{item['reference_quantity']:,.2f}",f"{item['reference_roofing_squares']:,.4f}",
            ('Repeated agreeing labels; face ownership unresolved' if len(item.get('pitch_candidates',[]))>1
                else 'Inferred; review required' if item['pitch_is_inferred'] else 'Source measurement; review required'),item['id']]))+' |')
    edges=[item for item in scope['items'] if item.get('surface')=='roof_edge']
    if edges:
        lines+=['','## Roof-edge references','',
            'Lengths include the reviewed slope correction. Product, laps, cuts, waste and whole-piece purchasing remain unresolved. These are partial accessory references.','',
            '| Edge | PDF page | Role | Reference LF | Scope ID |','| --- | ---: | --- | ---: | --- |']
        for item in edges:
            lines.append('| '+' | '.join(map(cell,[item['label'],item['plan_pdf_page'],item['edge_role'],
                f"{item['reference_quantity']:,.2f}",item['id']]))+' |')
    lines+=['','## Quote response','']+['- '+text for text in scope['quote_instructions']]
    lines+=['','## Material, quantity and pricing questions','']+[
        '- `requirement:'+r['id']+'`: '+r['request'] for r in scope['scope_requirements']]
    coverage=scope['source_exceptions']['coverage']
    note=(f"Uncovered projected area: {coverage['missing_projected_sf']:.6f} SF. "
        f"Outside the traced contour: {coverage['outside_projected_sf']:.6f} SF."
        if coverage is not None else 'Complete roof coverage has no independently reviewed outer contour.')
    lines+=['','## Source exceptions','',note,
        f"Overlapping projected roof area: {round(scope['source_exceptions']['overlap_excess_sf'],6)+0.0:.6f} SF; "
        'resolve roof levels and surface ownership before using a complete roof total.',
        f"{len(scope['source_exceptions']['inferred_pitch_face_ids'])} face pitches are inferred. "
        'Roofing materials, waste, accessory counts and purchase quantities remain unconfirmed.','',
        f"Reference revision: {scope['measurement_version']}. Scope fingerprint: `{scope['scope_sha256']}`.",'']
    unresolved=scope['source_exceptions'].get('unresolved_source_outlines',[])
    if unresolved:
        lines+=['','## Roof outlines still requiring measurement','',
            'These source outlines have no resolved roof quantity. Review their pitches and exposure; '
            'a matching pitch elsewhere does not close this scope. Do not treat them as zero or add them blindly to overlapping faces.','',
            '| Source outline | PDF page | Reason |','| --- | ---: | --- |']
        lines += ['| '+' | '.join(map(cell,[r['id'],r['page'],r['reason']]))+' |' for r in unresolved]
    return '\n'.join(lines)


def write_draft(scope,output):
    """Save an immutable bid snapshot without sending it or changing the estimate."""
    from pathlib import Path
    from bid_comparison import scope_digest
    if scope_digest(scope)!=scope.get('scope_sha256'):
        raise ValueError('Roof bid contents do not match their source fingerprint')
    if scope.get('sent') is not False or scope.get('status')!='unsent_draft':
        raise ValueError('Only an unsent roof bid draft may be exported')
    text=render_markdown(scope)
    out=Path(output)
    if out.exists():raise FileExistsError('Existing roof bid preserved; use a new revision folder')
    out.mkdir(parents=True)
    (out/'roofing.json').write_text(json.dumps(scope,indent=2)+'\n',encoding='utf-8')
    (out/'roofing_DRAFT.md').write_text(text,encoding='utf-8')
    return ['roofing_DRAFT.md','roofing.json']
