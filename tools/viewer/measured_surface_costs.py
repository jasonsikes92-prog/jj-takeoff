"""Keep measured material scope outside the template as explicit unpriced cost lines."""
import copy
import hashlib
import json
import math
from pathlib import Path
from area_overlap import overlapping_measurements
from measurement_store import MeasurementStore,calculate
from measurement_quantities import geometry_digest


def import_surfaces(draft,config,folder):
    if config.get('plan_sha256')!=draft['plan_sha256']:
        raise ValueError('Supplemental surfaces belong to another drawing')
    root=Path(folder).resolve();result=copy.deepcopy(draft)
    rows={r['row_id']:r for r in result['rows']};extras=result.setdefault('additional_cost_rows',[])
    occupied=set(rows)|{r['row_id'] for r in extras};claimed=set()
    for item in config['surfaces']:
        identity=item['row_id'];parent=rows[item['parent_row_id']];markup=rows[item['markup_source_row_id']]
        if identity in occupied:raise ValueError('Duplicate supplemental surface cost owner')
        if (parent['cost_type'] not in ('GROUP','ASSEMBLY') or parent.get('completion_status','').startswith('not_applicable')
                or parent.get('covered_by_package') or parent.get('line_cost') is not None
                or markup['cost_type']!='MATERIAL' or markup['unit'] not in ('SF','sq ft','ft2')
                or not item.get('name') or not item.get('basis')):
            raise ValueError('Surface needs an unpriced parent and matching material markup source')
        evidence=(root/item['scope_source']['file']).resolve()
        if (not evidence.is_relative_to(root) or not evidence.is_file()
                or hashlib.sha256(evidence.read_bytes()).hexdigest()!=item['scope_source']['sha256']):
            raise ValueError('Surface scope evidence changed')
        proof=json.loads(evidence.read_bytes())
        if proof.get('plan_sha256')!=draft['plan_sha256'] or proof.get('row_id')!=identity or not proof.get('basis'):
            raise ValueError('Surface scope evidence does not match its row and plan')
        for source in proof['documents']:
            path=(root/source['file']).resolve()
            if (not path.is_relative_to(root) or not path.is_file()
                    or hashlib.sha256(path.read_bytes()).hexdigest()!=source['sha256']):
                raise ValueError('Surface original evidence changed')
        if not proof['documents']:raise ValueError('Surface scope needs original evidence')
        job=(root/item['job']).resolve()
        if not (job/'measurement_edits.sqlite3').is_file():raise ValueError('Surface review has no saved history')
        if hashlib.sha256((job/'measurements.json').read_bytes()).hexdigest()!=item['config_sha256']:
            raise ValueError('Surface review configuration changed')
        state=MeasurementStore(job).read()
        if state['plan_sha256']!=draft['plan_sha256']:raise ValueError('Surface review belongs to another drawing')
        ids=item['measurement_ids'];others=item.get('other_surface_ids',[])
        if not ids or len(set(ids+others))!=len(ids+others):raise ValueError('Surface measurement identities must be unique')
        claims={(str(job),i) for i in ids}
        for row in result['rows']+extras:
            for q in row.get('quantity_sources',[])+row.get('assembly_inputs',[]):
                source_job=q.get('linked_review',{}).get('job')
                if source_job:claimed.update((str(Path(source_job).resolve()),i) for i in q.get('measurement_ids',[]))
        if claims&claimed:raise ValueError('Measured surface already has a quantity owner')
        surfaces=[state['measurements'][i] for i in ids+others]
        overlaps=[pair for pair in overlapping_measurements(surfaces) if set(pair)&set(ids)]
        unreviewed=[m['id'] for m in surfaces if m['id'] in ids and m.get('engine_line_ids')]
        remaining=list(item['remaining'])
        raw=math.fsum(calculate(state['measurements'][i])['quantity'] for i in ids)
        quantity=math.ceil(raw)
        if overlaps or unreviewed:
            quantity=None
            remaining.append('Surface overlap or unreviewed engine boundary requires correction')
        source={'job':str(job),'measurement_version':state['version'],'config_sha256':item['config_sha256'],
                'geometry_sha256':{i:geometry_digest(state['measurements'][i]) for i in ids+others}}
        q={'id':identity+'-surface','kind':'measured_supplemental_surface','measurement_ids':ids,
           'unit':'SF','measured_quantity':raw,'quantity':quantity,'rounding':'whole_up',
           'basis':item['basis'],'remaining':remaining,'linked_review':source,
           'scope_source':copy.deepcopy(item['scope_source']),'overlapping_measurement_ids':overlaps,
           'unreviewed_measurement_ids':unreviewed,'certified':False,'order_released':False}
        extras.append({'row_id':identity,'measured_surface_scope_id':q['id'],
            'parent_row_id':parent['row_id'],'name':item['name'],'parent':parent['name'],
            'cost_type':'MATERIAL','unit':'sq ft','markup_pct':markup['markup_pct'],'markup_source_row_id':markup['row_id'],
            'draft_quantity':quantity,'unit_cost':None,'line_cost':None,'line_price':None,
            'pricing_role':'cost_line','completion_status':'evidence_in_progress','certified':False,
            'current_price_certified':False,'assembly_inputs':[],'quantity_sources':[q]})
        occupied.add(identity);claimed.update(claims)
    result.update(whole_house_total=None,estimate_released=False)
    return result
