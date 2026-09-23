"""Assign source-reviewed gross wall boundaries to nonbillable floor inputs."""
import copy
import hashlib
import json
from pathlib import Path
from shapely.geometry import Polygon
from wall_enclosure_candidates import from_folder

INPUT_NAMES=('SF BASEMENT','SF FIRST FLOOR','SF SECOND FLOOR','SF THIRD FLOOR','SF GARAGE')


def binding(enclosure):
    return hashlib.sha256(json.dumps(enclosure,sort_keys=True,allow_nan=False).encode()).hexdigest()


def apply_quantities(draft,enclosures,review):
    if review['plan_sha256']!=draft['plan_sha256'] or enclosures['plan_sha256']!=draft['plan_sha256']:
        raise ValueError('Floor scope belongs to another drawing')
    if enclosures['measurement_version']!=draft['measurement_version']:
        raise ValueError('Floor scope uses another measurement revision')
    if 'enclosure_quantity_review' in draft:raise ValueError('Floor scope already applied')
    if any(not isinstance(review.get(k),str) or not review[k].strip() for k in ('reviewer','basis')):
        raise ValueError('Floor scope requires reviewer and source basis')
    if not isinstance(review.get('mappings'),list) or not review['mappings']:
        raise ValueError('Floor scope mappings required')
    result=copy.deepcopy(draft);rows={r['row_id']:r for r in result['rows']}
    candidates={e['id']:e for e in enclosures['candidate_enclosures']}
    if len(rows)!=len(result['rows']) or len(candidates)!=len(enclosures['candidate_enclosures']):
        raise ValueError('Floor scope needs unique row and enclosure identities')
    used=set();claimed=set();summaries=[]
    for mapping in review['mappings']:
        row=rows[mapping['row_id']]
        if (row['row_id'] in claimed or row['parent']!='INPUTS' or row['name'] not in INPUT_NAMES
                or row['name']!=mapping['name'] or row['unit'] not in ('ft2','SF','sq ft')
                or row['cost_type']!='MATERIAL' or row.get('pricing_role')!='input_only'
                or row.get('completion_status','').startswith('not_applicable')
                or row.get('covered_by_package') or row.get('cost_owner_row_id')
                or row.get('draft_quantity') is not None or row.get('quantity_sources') or row.get('assembly_inputs')
                or any(row.get(k) is not None for k in ('unit_cost','line_cost','line_price'))):
            raise ValueError('Floor target must be an unassigned, nonbillable gross floor input')
        if not isinstance(mapping.get('enclosures'),list) or not mapping['enclosures']:
            raise ValueError('Floor mapping needs source enclosures')
        selected=[];missing=[]
        for reference in mapping['enclosures']:
            identity=reference['id']
            if identity in used:raise ValueError('An enclosure cannot be counted in multiple floor inputs')
            if not isinstance(reference.get('sha256'),str) or len(reference['sha256'])!=64:
                raise ValueError('Floor scope requires its enclosure source hash')
            used.add(identity);candidate=candidates.get(identity)
            if candidate is None or binding(candidate)!=reference['sha256']:missing.append(identity)
            else:selected.append(candidate)
        for index,a in enumerate(selected):
            for b in selected[index+1:]:
                if a['page']==b['page'] and Polygon(a['points']).intersection(Polygon(b['points'])).area>1e-8:
                    raise ValueError('Floor input boundaries overlap on the drawing')
        quantity=sum(e['gross_boundary_sf'] for e in selected) if not missing else None
        source={'id':'enclosure-quantity-'+row['row_id'],'label':row['name']+' - gross wall-face boundary',
            'unit':'SF','use':'direct','quantity':quantity,'template_rows':[row['excel_row']],
            'enclosure_sources':copy.deepcopy(mapping['enclosures']),
            'measurement_ids':sorted({i for e in selected for i in e['source_measurement_ids']}),
            'source_pages':sorted({e['page'] for e in selected}),
            'reviewer':review['reviewer'],'basis':review['basis'],
            'quantity_basis':'gross wall-face floor boundary, including interior walls',
            'certified':False,'purchase_released':False,
            'remaining':['This input is not a floor-finish purchase area or a total-framed area.',
                'Plan area-schedule differences, complete coverage and downstream trade scopes remain separate reviews.']}
        if quantity is None:
            result.setdefault('pending_quantities',[]).append({**source,
                'reason':'Reviewed floor boundary is missing or changed; renew its source/scope association'})
        else:
            row['draft_quantity']=quantity;row.setdefault('quantity_sources',[]).append(source)
            result['mapped_quantity_rows']+=1
        claimed.add(row['row_id']);summaries.append({'row_id':row['row_id'],'quantity':quantity,
            'missing_or_changed_enclosure_ids':missing,'status':'current_gross_floor_input' if quantity is not None else 'withheld_pending_review'})
    result['enclosure_quantity_review']={'mappings':summaries,'review_sha256':binding(review),
        'unassigned_enclosure_ids':sorted(set(candidates)-used),'whole_floor_coverage_certified':False,
        'purchase_released':False,'limitations':copy.deepcopy(enclosures['limitations'])}
    return result


def import_quantities(draft,state,review,folder):
    if hashlib.sha256((Path(folder)/'template_rows.json').read_bytes()).hexdigest()!=review['template_sha256']:
        raise ValueError('Floor scope template source changed')
    return apply_quantities(draft,from_folder(folder,state),review)
