"""Source-bound stud scenarios with an optional verified owner height selection."""
import hashlib
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from measurement_store import MeasurementStore
from wall_field_stud_review import from_folder as field_layout
from framing_component_review import import_components
from framing_assemblies import calculate as assembly_counts
from historical_material_rates import checked_catalog
from stud_stock import calculate


def from_folder(folder):
    folder=Path(folder).resolve();path=folder/'stud_stock_review.json'
    raw=path.read_bytes();config=json.loads(raw);checked=[(path,raw)]
    def load(ref):
        source=(folder/ref['path']).resolve()
        if not source.is_relative_to(folder):raise ValueError('Stud evidence must stay inside its job')
        data=source.read_bytes()
        if hashlib.sha256(data).hexdigest()!=ref['sha256']:raise ValueError('Stud stock source changed: '+ref['path'])
        checked.append((source,data));return json.loads(data)
    framing=load(config['framing']);basis=load(config['basis']);material=load(config['material'])
    state=MeasurementStore(folder).read()
    if config['plan_sha256']!=state['plan_sha256'] or basis['plan_sha256']!=state['plan_sha256']:
        raise ValueError('Stud stock sources belong to another drawing')
    selection=load(config['selection']) if config.get('selection') else None
    if selection is not None:
        matching=[s for s in basis['scenarios'] if s['id']==selection.get('selected_scenario')]
        if (selection.get('source_kind')!='owner_confirmation' or selection.get('plan_sha256')!=state['plan_sha256']
                or len(matching)!=1 or matching[0]['wall_height_inches']!=selection.get('wall_height_inches')):
            raise ValueError('Stud height selection requires matching owner evidence and one scenario')
    source_inputs=load(framing['assembly_inputs']);profile=load(framing['profile'])
    dummy={'plan_sha256':state['plan_sha256'],'rows':[{'excel_row':str(framing['template_row']),
        'cost_type':'MATERIAL','completion_status':'evidence_in_progress','line_cost':None,'draft_quantity':None}]}
    reviewed=import_components(dummy,state,framing,folder)['wall_component_review']
    field=field_layout(folder)
    if {r['job']:r['version'] for r in field['measurement_dependencies']}!={r['job']:r['version'] for r in reviewed['measurement_dependencies']}:
        raise ValueError('Stud sources changed during calculation; retry')
    authorization=load(material['authorization'])
    if authorization.get('answer')!='Use saved rates as dated allowances':
        raise ValueError('Dated stud rates require saved authorization')
    load(material['ledger'])
    pdfs=(folder/material['pdf_directory']).resolve()
    if not pdfs.is_relative_to(folder):raise ValueError('Stud invoice sources must stay inside the job')
    catalog=checked_catalog(folder/material['ledger']['path'],pdfs,as_of=date.today().isoformat())
    result={'plan_sha256':state['plan_sha256'],'measurement_dependencies':field['measurement_dependencies'],
        'source_geometry_sha256':field['geometry_sha256'],'exterior_geometry_sha256':field['exterior_geometry_sha256'],
        'config_sha256':hashlib.sha256(raw).hexdigest(),'source_hashes':{str(p.relative_to(folder)):hashlib.sha256(b).hexdigest() for p,b in checked},
        'source_pdf_hashes':catalog['source_pdf_hashes'],'selected_scenario':None,
        'complete_framing_cost':None,'purchase_order_released':False,'current_price_certified':False,
        'assumptions':basis['assumptions'],'remaining':basis['remaining'],'scenarios':[]}
    if reviewed['changed_measurements']:
        result.update(status='withheld_geometry_changed',changed_measurements=reviewed['changed_measurements'])
    else:
        assemblies=assembly_counts(profile,source_inputs['openings'],source_inputs['junctions'])
        aliases={j['id']:j.get('aliases',[]) for j in source_inputs['junctions']}
        rates={(r['sku'],r['unit']):r for r in catalog['rates']}
        for scenario in basis['scenarios']:
            study=calculate(field,assemblies,aliases,basis['run_height_offsets_inches'],
                scenario['wall_height_inches'],basis['plate_inches'],basis['stocks'],
                jack_stock_allowance=basis.get('jack_stock_allowance',False))
            priced=[];unpriced=[]
            for sku,count in study['stock_quantities'].items():
                rate=rates.get((sku,'EA'))
                if rate is None or rate['status']!='dated_allowance_candidate' or rate['unit_price'] is None:
                    unpriced.append(sku);continue
                priced.append({'sku':sku,'quantity':count,'unit':'EA','unit_price':rate['unit_price'],
                    'pretax_extension':str((Decimal(rate['unit_price'])*count).quantize(Decimal('.01'))),
                    'date':rate['date'],'sources':rate['selected_sources']})
            study.update(id=scenario['id'],priced_stock=priced,unpriced_stock=unpriced,
                partial_material_allowance_before_tax_delivery_markup=(None if unpriced else
                    str(sum((Decimal(p['pretax_extension']) for p in priced),Decimal('0.00')))))
            result['scenarios'].append(study)
        result.update(status='unselected_height_scenarios',assembly_component_totals=assemblies['component_totals'],
            assembly_detail_issues=assemblies['pending'])
        if selection is not None:
            result.update(status='selected_height_scenario',selected_scenario=selection['selected_scenario'],
                height_selection_source=config['selection'])
            for scenario in result['scenarios']:
                scenario['selected']=scenario['id']==selection['selected_scenario']
                scenario['status']='Selected partial stud-stock allowance' if scenario['selected'] else 'Unselected comparison only'
    if any(p.read_bytes()!=data for p,data in checked):raise ValueError('Stud stock sources changed during calculation')
    if any(MeasurementStore(r['job']).read()['version']!=r['version'] for r in field['measurement_dependencies']):
        raise ValueError('Stud measurements changed during calculation; retry')
    return result
