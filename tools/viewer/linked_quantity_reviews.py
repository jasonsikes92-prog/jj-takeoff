"""Read current partial quantities from another review of the same plan."""
import copy
import hashlib
import json
from measurement_store import MeasurementStore,encode
from measurement_quantities import rollup,geometry_digest
from measurement_scope_reviews import ScopeReviews


def import_linked_quantities(draft, links, folder, source_state=None):
    result=copy.deepcopy(draft)
    rows={str(r['excel_row']):r for r in result['rows']}
    claimed=set();sources=[]
    for link in links:
        if 'derived_floor_field' in link:
            if ('derived_from_measurement_version' in link or source_state is None
                    or source_state['version']!=draft.get('measurement_version')
                    or source_state['plan_sha256']!=draft['plan_sha256']):
                raise ValueError('Live derived floor needs the current draft source state and one derivation method')
        if 'derived_from_measurement_version' in link:
            revision=link['derived_from_measurement_version']
            if type(revision) is not int or revision<1 or revision!=draft.get('measurement_version'):
                raise ValueError('Derived review needs recalculation after source measurement changes')
        path=(folder/link['job']).resolve()
        if not (path/'measurement_edits.sqlite3').is_file():
            raise ValueError('Linked review has no saved measurement history')
        for name,key in [('measurements.json','config_sha256'),('quantity_rules.json','rules_sha256')]:
            if hashlib.sha256((path/name).read_bytes()).hexdigest()!=link[key]:
                raise ValueError('Linked review configuration changed; verify its mapping')
        store=MeasurementStore(path);state=store.read()
        if state['plan_sha256']!=draft['plan_sha256']:
            raise ValueError('Linked review belongs to another drawing')
        dependencies=link.get('source_measurements',[])
        if not isinstance(dependencies,list):raise ValueError('Source measurement dependencies must be a list')
        for dependency in dependencies:
            upstream=(folder/dependency['job']).resolve()
            if not (upstream/'measurement_edits.sqlite3').is_file():
                raise ValueError('Source measurement review has no saved history')
            upstream_state=MeasurementStore(upstream).read()
            hashes=dependency.get('geometry_sha256')
            if not isinstance(hashes,dict) or not hashes or upstream_state['plan_sha256']!=draft['plan_sha256']:
                raise ValueError('Source measurement dependency needs matching plan and geometry')
            if any(identity not in upstream_state['measurements'] or geometry_digest(upstream_state['measurements'][identity])!=digest
                   for identity,digest in hashes.items()):
                raise ValueError('Source measurement geometry changed; review the derived layout')
        derived=None
        if 'derived_floor_field' in link:
            from floor_finish_faces import derive_linked_finish_field
            state,derived=derive_linked_finish_field(state,source_state,link['derived_floor_field'],folder)
        rules=json.loads((path/'quantity_rules.json').read_bytes())
        rules=ScopeReviews(store,rules).effective_rules()
        selected=link.get('quantity_rule_ids')
        if selected is not None:
            if not selected or len(selected)!=len(set(selected)) or set(selected)-{r['id'] for r in rules['rules']}:
                raise ValueError('Linked quantity rule selection is missing or duplicated')
            rules={**rules,'rules':[r for r in rules['rules'] if r['id'] in selected]}
        rollup_result=rollup(state,rules)
        mapping=link.get('template_row_mapping')
        if mapping is not None:
            original_targets={str(t) for q in rollup_result['quantities']+rollup_result['pending_quantities']
                              for t in q['template_rows']}
            if (not isinstance(mapping,dict) or set(mapping)!=original_targets
                    or any(not isinstance(t,str) or t not in link['template_rows'] or t not in rows for t in mapping.values())
                    or len(set(mapping.values()))!=len(mapping)):
                raise ValueError('Linked row mapping needs every source target and unique approved destination rows')
            for q in rollup_result['quantities']+rollup_result['pending_quantities']:
                q['source_template_rows']=copy.deepcopy(q['template_rows'])
                q['template_rows']=[mapping[str(t)] for t in q['template_rows']]
        quantities=rollup_result['quantities']
        source={'job':str(path),'measurement_version':state['version'],
                'config_sha256':link['config_sha256'],'rules_sha256':link['rules_sha256']}
        if mapping is not None:source['template_row_mapping']=copy.deepcopy(mapping)
        if dependencies:source['source_measurements']=copy.deepcopy(dependencies)
        source['geometry_sha256']=hashlib.sha256(encode({k:geometry_digest(m) for k,m in state['measurements'].items()}).encode()).hexdigest()
        if derived is not None:source['derived_floor_field']=derived
        if state.get('changed_measurement'):
            source['latest_edit']={'measurement_id':state['changed_measurement'],'note':state['note']}
        entries=[(q,False) for q in quantities]+[(q,True) for q in rollup_result['pending_quantities']]
        link_claimed=set()
        for quantity,is_pending in entries:
            direct=not is_pending and quantity['use']=='template_quantity'
            if not is_pending and quantity['use']!='assembly_input' and not (direct and link.get('template_quantity_rows')):
                raise ValueError('Linked partial review cannot set a purchase quantity')
            for target in quantity['template_rows']:
                target=str(target)
                append_partial=(link.get('append_assembly_inputs') is True and not direct
                                and (is_pending or quantity['use']=='assembly_input'))
                if (target not in link['template_rows'] or target not in rows
                        or (target in claimed and not (append_partial and target in link_claimed))):
                    raise ValueError('Unapproved or duplicate linked template target')
                row=rows[target]
                if append_partial and any(q['id']==quantity['id'] for q in row.get('assembly_inputs',[])):
                    raise ValueError('Duplicate linked assembly input')
                if (row['cost_type'] in ('GROUP','ASSEMBLY') or row['completion_status'].startswith('not_applicable')
                        or row.get('draft_quantity') is not None or row.get('covered_by_package')
                        or (row.get('assembly_inputs') and not append_partial) or row.get('line_cost') is not None):
                    raise ValueError('Linked template target is excluded or already assigned')
                if is_pending:
                    claimed.add(target);link_claimed.add(target)
                    continue
                if direct:
                    units={'ft2':'SF','sq ft':'SF','SF':'SF','LF':'LF','lf':'LF','feet':'LF','each':'EA','EA':'EA'}
                    if target not in link['template_quantity_rows'] or units.get(row['unit'])!=quantity['unit']:
                        raise ValueError('Linked template quantity needs explicit target and matching unit')
                    row['draft_quantity']=quantity['quantity']
                    row.setdefault('quantity_sources',[]).append({**quantity,'linked_review':source})
                else:row.setdefault('assembly_inputs',[]).append({**quantity,'linked_review':source})
                claimed.add(target);link_claimed.add(target)
            if is_pending:
                result.setdefault('pending_quantities',[]).append({**quantity,'linked_review':source})
        sources.append(source)
    result['linked_quantity_reviews']=sources
    return result
