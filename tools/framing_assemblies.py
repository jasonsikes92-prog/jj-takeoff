"""Resolve classified framing assemblies from saved company practices.

Inputs require stable physical IDs and source references. Quantities are component
allowances until geometry, bearing and stock-length checks release an order.
"""
if __package__:
    from .company_profile import resolve, DEFAULT_PROFILE
else:
    from company_profile import resolve, DEFAULT_PROFILE


def openings_from_schedule(schedule, source, *, schedule_scope):
    """Convert a reviewed interior schedule without treating all tags as doors."""
    if schedule_scope!='interior_and_garage_entries':
        raise ValueError('Explicit reviewed interior/garage schedule scope required')
    if not isinstance(source,str) or not source.strip():raise ValueError('Schedule source required')
    classifications={'hinged':'ordinary_interior_door','pocket':'pocket_door',
        'bypass':'bypass_door','open_passage':'open_passage','garage_entry':'garage_entry'}
    openings=[];seen=set()
    for item in schedule['openings']:
        identity=item['opening_id']
        if not isinstance(identity,str) or not identity.strip() or identity in seen:
            raise ValueError('Unique physical opening IDs required')
        seen.add(identity)
        kind=item.get('opening_type')
        opening={'id':identity,'source':source+'#'+identity,
            'classification':classifications.get(kind,'unresolved_opening'),
            'reviewed_opening_type':kind,'room_served':item.get('room_served'),
            'plan_tag':item.get('plan_tag'),'bearing_verified':False}
        if 'studs_per_side' in item:opening['studs_per_side']=item['studs_per_side']
        if 'estimating_allowance' in item:opening['estimating_allowance']=item['estimating_allowance']
        openings.append(opening)
    return openings


def calculate(profile, openings, junctions):
    seen = set()
    components, pending = [], []
    totals = {'king_studs': 0, 'jack_studs': 0, 'junction_studs': 0, 'pocket_frame_kits': 0}

    def register(item):
        if item['id'] in seen:
            raise ValueError('Physical assembly counted twice: '+item['id'])
        if not item.get('source'):
            raise ValueError('Assembly needs a source: '+item['id'])
        seen.add(item['id'])

    for opening in openings:
        register(opening)
        kind = opening.get('classification')
        if kind == 'pocket_door':
            qty = {'pocket_frame_kits': 1}
            pending.append({'id': opening['id'], 'reason': 'Select frame kit and reconcile split studs, track, rough opening and supporting lumber'})
            basis = 'Source-classified pocket door; ordinary king/jack default not applied'
        elif kind in ('ordinary_interior_door','ordinary_exterior_opening','wide_garage_opening'):
            key = 'framing.'+kind+'_studs_per_side'
            overrides = {key: opening['studs_per_side']} if 'studs_per_side' in opening else {}
            resolved = resolve(profile, {'opening_class':kind}, overrides)
            rule = resolved['settings'].get(key)
            if rule is None:
                pending.append({'id':opening['id'],'reason':'No confirmed support allowance for this opening class'})
                continue
            if (not isinstance(rule,dict) or set(rule)!={'king','jack'}
                    or any(type(n) is not int or n<0 for n in rule.values())):
                raise ValueError('Opening support allowance needs whole nonnegative king and jack counts')
            qty = {'king_studs': 2*rule['king'], 'jack_studs': 2*rule['jack']}
            basis = resolved['provenance'][key]
            if not opening.get('bearing_verified', False):
                pending.append({'id':opening['id'],'reason':'Verify bearing support requirements before releasing component counts'})
        elif kind in ('bypass_door','garage_entry','open_passage') and 'estimating_allowance' in opening:
            allowance=opening['estimating_allowance']
            if resolve(profile)['settings'].get('framing.tight_door_corner_quantity_basis')!='documented_estimating_allowances':
                raise ValueError('Documented estimating allowance practice required')
            if any(not isinstance(allowance.get(key),str) or not allowance[key].strip() for key in ('source','basis')):
                raise ValueError('Special opening allowance needs a source and basis')
            rule=allowance['studs_per_side']
            if set(rule)!={'king','jack'} or any(type(n) is not int or n<0 for n in rule.values()):
                raise ValueError('Invalid special opening allowance piece count')
            qty={'king_studs':2*rule['king'],'jack_studs':2*rule['jack']}
            basis={'quantity_basis':'Documented estimating allowance','source':allowance['source'],
                'assumption':allowance['basis']}
            pending.append({'id':opening['id'],'reason':'Estimating allowance only; verify final opening, header bearing and shared members before purchase release'})
        else:
            pending.append({'id':opening['id'],'reason':'Classify opening and specify its support assembly; no ordinary-door fallback'})
            continue
        components.append({'id':opening['id'],'source':opening['source'],'quantities':qty,'basis':basis})
        for name, count in qty.items():
            if not isinstance(count,int) or count<0:raise ValueError('Invalid piece count')
            totals[name] += count

    rules = resolve(profile)['settings'].get('framing.solid_backing_assembly_allowance', {})
    for junction in junctions:
        register(junction)
        rule = rules.get(junction.get('classification')) if junction.get('backing')=='solid_stud_backing' else None
        if 'whole_assembly_studs' in junction:
            count, basis = junction['whole_assembly_studs'], 'Project-specific assembly detail'
        elif rule:
            count, basis = rule['whole_assembly_studs'], rule['basis']
        else:
            pending.append({'id':junction['id'],'reason':'No applicable junction assembly detail'})
            continue
        if not isinstance(count,int) or count<0:raise ValueError('Invalid junction piece count')
        totals['junction_studs'] += count
        components.append({'id':junction['id'],'source':junction['source'],
                           'quantities':{'junction_studs':count},'basis':basis})
    return {'company_profile_version':profile['version'],'components':components,'component_totals':totals,
            'pending':pending,'purchase_order_released':False,
            'counting_rule':'Merge overlapping physical members with field/end/jamb schedules before summing a complete order.'}


def documented_group_allowances(settings, components, groups):
    """Budget each physical assembly once; make unresolved members explicit."""
    if settings.get('framing.tight_door_corner_quantity_basis')!='documented_estimating_allowances':
        raise ValueError('Documented estimating allowance practice required')
    by_id={item['id']:item for item in components['components']}
    if len(by_id)!=len(components['components']):raise ValueError('Duplicate component assembly')
    seen=set();result=[]
    for group in groups:
        identities=group['assemblies']
        if len(set(identities))!=len(identities) or seen.intersection(identities):
            raise ValueError('Physical assembly occurs in more than one allowance group')
        seen.update(identities)
        included=[by_id[i] for i in identities if i in by_id]
        missing=[i for i in identities if i not in by_id]
        totals={}
        for item in included:
            for name,count in item['quantities'].items():totals[name]=totals.get(name,0)+count
        result.append({'assemblies':identities,'component_allowances':totals,'component_sources':included,
            'unquantified_assemblies':missing,'shared_member_credit':0,
            'status':'partial_component_allowance' if missing else 'documented_component_allowance',
            'basis':'Retain each documented whole-assembly allowance once. No speculative credit for possible shared members; field/end counts must exclude these reserved assemblies.'})
    if set(by_id)-seen:raise ValueError('Component assemblies missing from allowance groups')
    return {'groups':result,'exact_combined_layout_required_for_estimating':False,
        'component_detail_issues':components['pending'],'complete_order_quantity':None,
        'purchase_order_released':False,
        'remaining':'Complete unquantified framing components and stock cuts; apply plan-specific support details when known.'}


def main(argv=None):
    import argparse,hashlib,json
    from pathlib import Path
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True,help='JSON with source-linked openings and junctions')
    parser.add_argument('--output',required=True,help='New result JSON; existing files are preserved')
    parser.add_argument('--profile',default=str(DEFAULT_PROFILE))
    args=parser.parse_args(argv)
    profile_bytes=Path(args.profile).read_bytes();input_bytes=Path(args.input).read_bytes()
    inputs=json.loads(input_bytes)
    result=calculate(json.loads(profile_bytes),inputs.get('openings',[]),inputs.get('junctions',[]))
    result.update(company_profile_sha256=hashlib.sha256(profile_bytes).hexdigest(),input_sha256=hashlib.sha256(input_bytes).hexdigest())
    with Path(args.output).open('x',encoding='utf-8') as target:
        target.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'output':str(Path(args.output).resolve()),'assemblies':len(result['components']),'purchase_order_released':False}))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
