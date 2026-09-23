"""Attach live roof, plate and header candidates without changing billing quantities."""
import copy
from collections import defaultdict
from roof_panel_review import from_folder as roof_panels
from plate_stock_review import from_folder as plate_stock
from header_cut_review import from_folder as header_cuts
from subfloor_panel_review import from_folder as subfloor_panels
from rafter_cut_review import from_folder as rafter_cuts
from window_sill_stock_review import from_folder as window_sills
from below_window_stock_review import from_folder as below_windows
from above_door_stock_review import from_folder as above_doors


def import_stock(draft, folder, config):
    if 'framing_stock_review' in draft:raise ValueError('Framing stock already imported')
    if config['plan_sha256']!=draft['plan_sha256']:
        raise ValueError('Framing stock mapping belongs to another drawing')
    target=str(config['template_row'])
    matches=[r for r in draft['rows'] if str(r['excel_row'])==target]
    if len(matches)!=1:raise ValueError('One framing stock template owner required')
    row=matches[0]
    if (row['cost_type']!='MATERIAL' or row['completion_status'].startswith('not_applicable')
            or row.get('covered_by_package') or row.get('line_cost') is not None
            or row.get('draft_quantity') is not None):
        raise ValueError('Framing stock target is excluded, assigned or priced')
    if any(q['id'].startswith('framing-stock-') for r in draft['rows'] for q in r.get('assembly_inputs',[])):
        raise ValueError('Framing stock component already assigned')
    readers={'roof':roof_panels,'plates':plate_stock,'headers':header_cuts}
    if 'subfloor' in config['mapping_sha256']:readers['subfloor']=subfloor_panels
    if 'rafters' in config['mapping_sha256']:readers['rafters']=rafter_cuts
    if 'sills' in config['mapping_sha256']:readers['sills']=window_sills
    if 'below_windows' in config['mapping_sha256']:readers['below_windows']=below_windows
    if 'above_doors' in config['mapping_sha256']:readers['above_doors']=above_doors
    if set(config['mapping_sha256'])!=set(readers):
        raise ValueError('Roof, plate and header source mappings required')
    reviews={key:reader(folder) for key,reader in readers.items()}
    for key,review in reviews.items():
        if (review['plan_sha256']!=draft['plan_sha256']
                or review['mapping_sha256']!=config['mapping_sha256'][key]):
            raise ValueError('Framing stock drawing or source mapping changed: '+key)
    if reviews['roof']['source_version']!=reviews['plates']['source_version']:
        raise ValueError('Roof and plate source versions differ; retry')
    if reviews['headers']['measurement_version']!=draft['measurement_version']:
        raise ValueError('Header and estimate measurement versions differ; retry')
    if 'sills' in reviews and reviews['sills']['measurement_version']!=draft['measurement_version']:
        raise ValueError('Sill and estimate measurement versions differ; retry')
    if 'above_doors' in reviews and (reviews['above_doors']['measurement_version']!=draft['measurement_version']
            or reviews['above_doors']['source_version']!=reviews['roof']['source_version']):
        raise ValueError('Upper-door and framing source revisions differ; retry')
    if 'below_windows' in reviews:
        lower=reviews['below_windows']
        if (lower['measurement_version']!=draft['measurement_version']
                or lower['source_version']!=reviews['roof']['source_version']
                or 'sills' not in reviews or lower['sill_mapping_sha256']!=reviews['sills']['mapping_sha256']):
            raise ValueError('Below-window and framing source revisions differ; retry')
    if 'subfloor' in reviews and reviews['subfloor']['source_version']!=reviews['roof']['source_version']:
        raise ValueError('Subfloor and roof source versions differ; retry')
    if 'rafters' in reviews and reviews['rafters']['source_version']!=reviews['roof']['source_version']:
        raise ValueError('Rafter and roof source versions differ; retry')
    result=copy.deepcopy(draft);row=next(r for r in result['rows'] if str(r['excel_row'])==target)
    summaries={};items=[]
    for key,review in reviews.items():
        # Keep provenance and unresolved scope; detailed stock cuts remain in their live review.
        excluded={'faces','sheets','boards','runs','pieces','segments','reuse_sheets','dedicated_sheet_modules','junctions'}
        source=copy.deepcopy({k:v for k,v in review.items() if k not in excluded})
        summaries[key]=source
        if key in ('roof','subfloor'):
            ids=([f['face_id'] for f in review['faces']] if key=='roof'
                 else [p['id'] for p in review['pieces']])
            groups=[(key,key.title()+' sheathing cut candidate',review['candidate_sheets'],'sheet',ids,{})]
        else:
            stock=defaultdict(list)
            for board in review['boards']:stock[(board['sku'],board['length_ft'])].append(board['id'])
            label_prefix='Upper-door blank allowance' if key=='above_doors' else key.title()+' cut candidate'
            groups=[(f'{key}-{sku}-{length:g}',f'{label_prefix}: {sku}, {length:g} ft',
                     len(ids),'stick',ids,{'sku':sku,'stock_length_ft':length})
                    for (sku,length),ids in sorted(stock.items())]
        for identity,label,quantity,unit,ids,details in groups:
            items.append({'id':'framing-stock-'+identity,'label':label,'quantity':quantity,
                'unit':unit,'use':'assembly_input','template_rows':[target],
                'certified':False,'order_released':False,'component_ids':ids,
                'source_snapshot':source,'basis':review['basis'],'remaining':review['remaining'],**details})
    row.setdefault('assembly_inputs',[]).extend(items);row['certified']=False
    result['framing_stock_review']={'status':'partial_stock_candidates','sources':summaries,
        'complete_framing_quantity':None,'price_applied':False,
        'cross_scope_offcut_credit':False}
    oversized=reviews.get('rafters',{}).get('requires_splice_layout',[])
    if reviews.get('above_doors',{}).get('pending'):
        result.setdefault('pending_quantities',[]).append({
            'id':'above-door-source-review','label':'Remaining upper-door framing',
            'template_rows':[target],'unit':'EA','use':'assembly_input','quantity':None,'certified':False,
            'reason':'Resolve upper-door header fit, height or shared station ownership before completing this scope.',
            'component_ids':[p['id'] for p in reviews['above_doors']['pending']]})
    if reviews.get('below_windows',{}).get('pending'):
        result.setdefault('pending_quantities',[]).append({
            'id':'below-window-source-review','label':'Remaining below-window framing',
            'template_rows':[target],'unit':'EA','use':'assembly_input','quantity':None,'certified':False,
            'reason':'Resolve unlocated or conflicting below-window members before completing this scope.',
            'component_ids':[i['id'] for i in reviews['below_windows']['pending']]})
    if reviews.get('sills',{}).get('changed_measurements'):
        result.setdefault('pending_quantities',[]).append({
            'id':'window-sill-source-review','label':'Rough window sill stock',
            'template_rows':[target],'unit':'stick','use':'assembly_input','quantity':None,'certified':False,
            'reason':'Window geometry changed; reconcile the supplier opening widths before reusing sill cuts.',
            'component_ids':reviews['sills']['changed_measurements']})
    if oversized:
        result.setdefault('pending_quantities',[]).append({
            'id':'rafter-supported-splice-layout','label':'Rafters exceeding available stock',
            'template_rows':[target],'unit':'EA','use':'assembly_input','quantity':None,'certified':False,
            'reason':f'{len(oversized)} rafter segments need a reviewed supported splice layout; their boards and supports are not quantified.',
            'component_ids':[p['id'] for p in oversized]})
    return result
