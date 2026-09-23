"""Map agreed stud-stock scenarios to existing component counts exactly once."""
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP


COMPONENTS = {'field':'wall-component-field-studs',
              'king_studs':'wall-component-king_studs',
              'junction_studs':'wall-component-junction_studs'}


def apply(study, components, review):
    component_kinds=dict(COMPONENTS)
    scenarios=review['scenarios']
    selected=review.get('selected_scenario')
    if selected is not None:
        scenarios=[s for s in scenarios if s['id']==selected]
        if review['status']!='selected_height_scenario' or len(scenarios)!=1:
            raise ValueError('One current selected stud-height scenario required')
    jack_modes={s.get('jack_stock_allowance',False) for s in scenarios}
    if jack_modes=={True}:component_kinds['jack_studs']='wall-component-jack_studs'
    summary={key:review[key] for key in ('status','selected_scenario','config_sha256',
        'measurement_dependencies','source_hashes','source_pdf_hashes','assumptions','remaining')}
    summary.update(applied=False, included_component_ids=[], scenario_ids=[])
    study['stud_stock_mapping']=summary
    def withhold(reason):
        summary['reason']=reason
        for item in study['unpriced_components']:
            if item['component_id'] in component_kinds.values():item['reason']=reason
    if len(jack_modes)>1:
        withhold('Stud scenarios disagree on jack stock scope');return
    if review['status'] not in ('unselected_height_scenarios','selected_height_scenario') or not scenarios:
        withhold('Current geometry has no reviewed stud-stock scenarios');return
    if review['status']=='selected_height_scenario' and selected is None:
        raise ValueError('Selected stud-height status requires a scenario')
    sources={c['id']:c for c in components}
    signatures=[]
    for scenario in scenarios:
        if scenario['pending_members'] or scenario['unpriced_stock']:
            withhold('Stud members or stock prices remain unresolved');return
        members=scenario['members'];by_id={m['id']:m for m in members}
        if len(by_id)!=len(members):raise ValueError('Duplicate stud stock member')
        if any(m['kind'] not in component_kinds for m in members):raise ValueError('Unexpected stud stock scope')
        for kind,identity in component_kinds.items():
            matching_members=[m for m in members if m['kind']==kind];source=sources.get(identity)
            locations={m['source_id'] for m in matching_members}
            if (source is None or source['unit']!='EA' or type(source['quantity']) is not int
                    or source['quantity']!=len(matching_members)
                    or len(source['component_ids'])!=len(set(source['component_ids']))
                    or set(source['component_ids'])!=locations):
                withhold('Stud-stock locations or counts no longer match the current framing inputs');return
        cuts=[c['piece_id'] for b in scenario['boards'] for c in b['cuts']]
        if len(cuts)!=len(set(cuts)) or set(cuts)!=set(by_id):
            raise ValueError('Stud boards must cover each member exactly once')
        for board in scenario['boards']:
            if any(by_id[c['piece_id']]['sku']!=board['sku'] for c in board['cuts']):
                raise ValueError('Stud board product does not match its members')
        counts=dict(Counter(b['sku'] for b in scenario['boards']))
        rates={r['sku']:r for r in scenario['priced_stock']}
        if (counts!=scenario['stock_quantities'] or set(counts)!=set(rates)
                or len(rates)!=len(scenario['priced_stock'])
                or any(r['unit']!='EA' or r['quantity']!=counts[sku] for sku,r in rates.items())):
            raise ValueError('Stud purchase counts or units do not match the boards')
        signatures.append((Counter((m['kind'],m['source_id'],m['sku']) for m in members),
                           counts,scenario['priced_stock']))
    if any(s!=signatures[0] for s in signatures[1:]):
        withhold('Wall-height scenarios require different stock or prices; keep them separate');return
    ids=set(component_kinds.values())
    if any(ids.intersection([c['component_id'],*c.get('source_component_ids',[])])
           for c in study['priced_components']+study.get('separately_owned_components',[])):
        raise ValueError('Stud component already has a material cost owner')
    scenario=scenarios[0];purchases=[]
    for rate in scenario['priced_stock']:
        price=Decimal(rate['unit_price'])
        if not price.is_finite() or price<=0:raise ValueError('Positive finite stud rate required')
        extension=(rate['quantity']*price).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
        if extension!=Decimal(rate['pretax_extension']):raise ValueError('Stud price extension differs')
        allocations=Counter(component_kinds[m['kind']] for m in scenario['members'] if m['sku']==rate['sku'])
        purchases.append({'component_id':'stud-stock-'+rate['sku'], 'label':'Stud stock: '+rate['sku'],
            'sku':rate['sku'],'quantity':rate['quantity'],'quantity_unit':'stick','supplier_sales_unit':'EA',
            'dated_unit_price':str(price),'pretax_extension':str(extension),'source_date':rate['date'],
            'rate_sources':rate['sources'],'source_component_ids':sorted(allocations),
            'member_allocations':dict(allocations),'quantity_source':summary,
            'product_match_basis':('Owner-selected height scenario; exact stock and dated rates.' if selected is not None else
                'All reviewed height scenarios agree on stock and dated rates; no height selected.'),
            'quantity_certified_for_order':False})
    study['unpriced_components']=[c for c in study['unpriced_components'] if c['component_id'] not in ids]
    study['priced_components'].extend(purchases)
    study['priced_component_subtotal_before_tax_delivery_markup']=str(sum(
        (Decimal(p['pretax_extension']) for p in study['priced_components']),Decimal('0.00')))
    summary.update(applied=True,included_component_ids=sorted(ids),
        scenario_ids=[s['id'] for s in scenarios],reason=('Owner-selected stud-height allowance' if selected is not None else
            'Agreed stock allowance; wall-height decision remains open'))
