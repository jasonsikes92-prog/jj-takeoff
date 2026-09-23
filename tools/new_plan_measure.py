"""Run the existing measurement engine on source-bound intake page candidates.

Produces a reviewable draft, never automatic semantic approval or pricing.
"""
import hashlib
import json
import shutil
import sys
import uuid
from pathlib import Path
import fitz

sys.path.insert(0,str(Path(__file__).resolve().parent/'viewer'))
from measurement_store import calculate
from new_plan_template import read_template,initial_rules
from plan_sheet_review import read_sheet_review
from door_specifications import read_door_specifications
from door_hardware_specifications import read_hardware_specifications
from wall_view_review import read_wall_view_review
from wall_classification_review import read_review as read_wall_classification
from wall_depth_basis import read_wall_depth_basis
from roof_view_review import read_roof_view_review
from roof_dormer_review import read_review as read_dormer_review,reviewed_candidates as reviewed_dormers
from roof_coverage_review import read_review as read_roof_coverage_review
from roof_outline_pitch_review import read_review as read_outline_pitch_review, reviewed_candidates as reviewed_roof_outlines


def measure_job(job):
    """Publish a complete preparation together; retain failed attempts for diagnosis."""
    job = Path(job)
    target = job / 'draft_takeoff'
    attempt = job / ('.takeoff-attempt-' + uuid.uuid4().hex)
    try:
        summary = _prepare_job(job, attempt)
        if target.exists():
            raise FileExistsError('Another draft was published; existing draft preserved')
        attempt.rename(target)
        return summary
    except Exception as exc:
        if attempt.exists():
            (attempt / 'preparation_failure.json').write_text(json.dumps({
                'status': 'preparation_failed', 'error_type': type(exc).__name__,
                'estimate_released': False,
            }, indent=2) + '\n', encoding='utf-8')
        raise


def _prepare_job(job, out):
    from jnj_takeoff import run_takeoff
    job=Path(job);plan=job/'plan.pdf'
    inventory=json.loads((job/'plan_inventory.json').read_text(encoding='utf-8'))
    digest=hashlib.sha256(plan.read_bytes()).hexdigest()
    if digest!=inventory['plan_sha256']:raise ValueError('Intake drawing has changed')
    dormer_review=read_dormer_review(job,digest)
    wall_classification=read_wall_classification(job)
    outline_pitch_review=read_outline_pitch_review(job,digest)
    door_specs = read_door_specifications(job) if (job/'door_core_specifications.json').exists() else None
    hardware_specs = read_hardware_specifications(job)
    if (job/'draft_takeoff').exists():
        raise FileExistsError('Existing draft preserved; create a new job/revision')
    reviewed=read_sheet_review(job)
    if not reviewed.get('measurement_allowed', reviewed['coverage_passed']):
        raise ValueError('Sheet coverage review failed; resolve the recorded missing sheets and issues')
    if (reviewed.get('measurement_scope')=='reviewed_set'
            and reviewed.get('roles_requiring_disambiguation',{}).get('floor')):
        raise ValueError('Multiple floor-plan pages require explicit level/view routing; a single-floor draft would omit scope')
    selected_roles = reviewed.get('measurement_role_pages', reviewed['unique_role_pages'])
    from window_cross_view_review import sources_from_sheet_review,from_plan as cross_view_windows
    window_sources=sources_from_sheet_review(reviewed)
    window_cross_view=cross_view_windows(plan,window_sources) if window_sources is not None else None
    roof_view=read_roof_view_review(job,selected_roles.get('roof'))
    roof_coverage=read_roof_coverage_review(job,digest,selected_roles.get('roof'))
    wall_view=read_wall_view_review(job,selected_roles.get('floor'))
    wall_depth=read_wall_depth_basis(job,digest) if wall_view is not None else None
    if reviewed.get('measurement_scope') == 'reviewed_subset':
        for name in ('electrical_symbol_definitions.json', 'electrical_template_definitions.json',
                     'electrical_vector_definitions.json', 'electrical_stroke_definitions.json'):
            path = job / name
            if path.exists():
                config = json.loads(path.read_text(encoding='utf-8'))
                if 'electrical' not in selected_roles or any(
                        item.get('page') != selected_roles['electrical'] for item in config.get('pages', [])):
                    raise ValueError('Electrical definitions are outside the reviewed partial scope')
    template=read_template()
    symbol_file=job/'electrical_symbol_definitions.json'
    symbol_result=None
    if symbol_file.exists():
        from text_symbol_candidates import plan_symbol_candidates
        symbol_config=json.loads(symbol_file.read_text(encoding='utf-8'))
        with fitz.open(plan) as doc:
            symbol_result=plan_symbol_candidates(doc,symbol_config,digest)
    template_file=job/'electrical_template_definitions.json'
    template_result=None
    if template_file.exists():
        from template_symbol_candidates import plan_template_candidates
        template_config=json.loads(template_file.read_text(encoding='utf-8'))
        with fitz.open(plan) as doc:
            template_result=plan_template_candidates(doc,template_config,digest)
    vector_file=job/'electrical_vector_definitions.json'
    vector_result=None
    if vector_file.exists():
        from vector_outlet_candidates import plan_vector_outlets
        vector_config=json.loads(vector_file.read_text(encoding='utf-8'))
        with fitz.open(plan) as doc:vector_result=plan_vector_outlets(doc,vector_config,digest)
    stroke_file=job/'electrical_stroke_definitions.json'
    stroke_result=None
    if stroke_file.exists():
        from vector_stroke_candidates import plan_stroke_candidates
        stroke_config=json.loads(stroke_file.read_text(encoding='utf-8'))
        with fitz.open(plan) as doc:stroke_result=plan_stroke_candidates(doc,stroke_config,digest)
    # Engine uses zero-based PDF page indices; intake exposes one-based pages.
    roles={'area_schedule':'sqft_schedule','foundation':'foundation','floor':'floor_area','roof':'roof'}
    sheet_map={engine:selected_roles[role]-1 for role,engine in roles.items()
               if role in selected_roles}
    with fitz.open(plan) as doc:
        sizes=[(p.rect.width,p.rect.height) for p in doc]
    if any(type(page) is not int or not 0<=page<len(sizes) for page in sheet_map.values()):
        raise ValueError('Intake page mapping is outside this drawing')
    out.mkdir()
    result=run_takeoff(str(plan),sheet_map,evidence_dir=str(out/'engine_evidence'))
    if result.get('evidence_json'):
        # This file moves with the completed attempt; its public reference must
        # still resolve after publication under the stable draft directory.
        result['evidence_json']=str(job/'draft_takeoff/engine_evidence/takeoff_evidence.json')
    if hashlib.sha256(plan.read_bytes()).hexdigest()!=digest:raise ValueError('Drawing changed during measurement')
    measurements=[];rejected=[];by_geometry={}
    from dimension_scale import split_dimension_scale
    from sheet_scale_labels import scale_labels,corroborate_dimension_scale
    region_scales={}
    with fitz.open(plan) as doc:
        for line in result['lines']:
            if (line.get('geometry') or {}).get('kind')!='polygon':continue
            page=line['page']
            if page in region_scales:continue
            printed=scale_labels(doc[page])
            review=corroborate_dimension_scale(split_dimension_scale(doc[page]),printed)
            region_scales[page]={**review,'mixed_view_scales':printed['mixed_view_scales']}
    palette=['#0e7490','#7c3aed','#b45309','#15803d','#be123c']
    for line in result['lines']:
        geometry=line.get('geometry')
        if not geometry or geometry.get('kind')!='polygon':continue
        page=line['page'];scale=(result['pages'].get(page) or {}).get('ppf')
        review=region_scales[page]
        if (scale is None or not review['usable_candidate'] or review['mixed_view_scales']
                or abs(scale/review['points_per_foot']-1)>.005):
            rejected.append({'line_id':line['id'],'page':page+1,
                'reason':'Engine region scale lacks agreeing two-axis dimension controls',
                'engine_points_per_foot':scale});continue
        points=[list(p) for p in geometry['points']]
        if len(points)>1 and points[0]==points[-1]:points.pop()
        key=json.dumps([page,scale,points],sort_keys=True)
        if key in by_geometry:
            by_geometry[key]['engine_line_ids'].append(line['id']);continue
        measurement={'id':'candidate-'+hashlib.sha256(key.encode()).hexdigest()[:16],
            'label':f'Page {page+1} region candidate {len(measurements)+1}',
            'page':page+1,'kind':'area','points':points,'points_per_foot':scale,
            'width_pt':sizes[page][0],'height_pt':sizes[page][1],
            'color':palette[len(measurements)%len(palette)],'dependent_rows':[],
            'engine_line_ids':[line['id']],'scope_status':'Unclassified geometry; verify boundary and intended scope',
            'source_method':line['method'],'scale_source':review['method']}
        try:calculate(measurement)
        except ValueError as exc:
            rejected.append({'line_id':line['id'],'reason':str(exc)});continue
        by_geometry[key]=measurement;measurements.append(measurement)
    roof_candidates={'measurements':[],'unmatched_or_ambiguous_pitch_labels':[]}
    roof_cutout_groups=[]
    roof_page=sheet_map.get('roof')
    roof_scale=(result['pages'].get(roof_page) or {}).get('ppf')
    roof_scale_review=None
    roof_printed_scales=None
    roof_extraction_status='page_unresolved'
    if roof_page is not None:
        from roof_face_candidates import candidates
        from dimension_scale import split_dimension_scale
        from sheet_scale_labels import scale_labels,corroborate_dimension_scale
        with fitz.open(plan) as doc:
            bounds=roof_view['view_bounds_pt'] if roof_view is not None else None
            roof_printed_scales=scale_labels(doc[roof_page],bounds)
            roof_scale_review=split_dimension_scale(doc[roof_page],bounds)
            roof_scale_review=corroborate_dimension_scale(roof_scale_review,roof_printed_scales)
            if roof_view is not None and not roof_scale_review['controls'] and not roof_scale_review['usable_candidate']:
                from arrow_dimension_scale import arrow_dimension_scale
                arrows=arrow_dimension_scale(doc[roof_page],bounds,roof_printed_scales)
                roof_scale_review=({**arrows,'split_line_review':roof_scale_review} if arrows['usable_candidate']
                    else {**roof_scale_review,'opposed_arrow_review':arrows})
            if roof_view is not None:roof_scale=None
            if roof_scale_review['usable_candidate']:roof_scale=roof_scale_review['points_per_foot']
            if roof_view is not None or roof_printed_scales['mixed_view_scales']:
                for measurement in measurements:
                    if measurement['page']==roof_page+1:
                        rejected.append({'line_ids':measurement['engine_line_ids'],
                            'reason':'Roof view requires view-specific geometry and calibration'})
                measurements=[m for m in measurements if m['page']!=roof_page+1]
            if roof_printed_scales['mixed_view_scales']:
                roof_extraction_status='view_scale_assignment_required'
            elif roof_view is not None:
                roof_candidates=candidates(doc[roof_page],roof_scale if roof_scale is not None else 1,bounds,
                    roof_view.get('allowed_styles'))
                if roof_scale is None:
                    # Preserve only page geometry; do not export nominal-scale areas.
                    roof_candidates['uncalibrated_geometry']=[{key:m[key] for key in (
                        'id','page','points','pitch_candidate','pitch_candidates','source_cad_paths','source_method','source_view_bounds_pt') if key in m}
                        for m in roof_candidates['measurements']]
                    roof_candidates['measurements']=[]
                    roof_extraction_status='geometry_requires_calibration'
                else:
                    roof_extraction_status='candidates_require_review' if roof_candidates['measurements'] else 'no_faces_extracted'
                    from roof_cutout_candidates import component_candidates
                    roof_cutout_groups=[component_candidates(face,roof_scale,*sizes[roof_page])
                        for face in roof_candidates['complex_face_candidates']]
                    roof_candidates['complex_face_components']=roof_cutout_groups
                    if roof_cutout_groups:roof_extraction_status='candidates_require_review'
            elif roof_scale is not None:
                roof_candidates=candidates(doc[roof_page],roof_scale)
                roof_extraction_status='candidates_require_review' if roof_candidates['measurements'] else 'no_faces_extracted'
            else:roof_extraction_status='scale_unresolved'
        if outline_pitch_review is not None:
            frame=({'page':roof_page+1,'points_per_foot':roof_scale,'width_pt':sizes[roof_page][0],
                'height_pt':sizes[roof_page][1]} if roof_page is not None and roof_view is not None and roof_scale is not None else None)
            added=reviewed_roof_outlines(plan,roof_candidates,outline_pitch_review,frame)
            resolved={m['source_pitch_evidence']['source_outline_sha256'] for m in added}
            roof_candidates['reviewed_source_outlines']=[o for o in roof_candidates['unresolved_source_outlines']
                if o['source_sha256'] in resolved]
            roof_candidates['unresolved_source_outlines']=[o for o in roof_candidates['unresolved_source_outlines']
                if o['source_sha256'] not in resolved]
            roof_candidates['outline_pitch_review']=outline_pitch_review
            replaced={r['measurement_id'] for m in added for r in m['source_pitch_evidence'].get('superseded_measurements',[])}
            if replaced:
                roof_candidates['superseded_measurements']=[m for m in roof_candidates['measurements'] if m['id'] in replaced]
                roof_candidates['measurements']=[m for m in roof_candidates['measurements'] if m['id'] not in replaced]
            roof_candidates['measurements'].extend(added)
            if added:roof_extraction_status='candidates_require_review'
        for measurement in roof_candidates['measurements']:
            measurement['color']=palette[len(measurements)%len(palette)]
            measurement['scale_source']=roof_scale_review['method'] if roof_scale_review['usable_candidate'] else 'legacy engine scale candidate'
            measurements.append(measurement)
        for group in roof_cutout_groups:
            measurements.extend(group['measurements'])
    dormer_groups=[]
    if dormer_review is not None:
        frame=({'page':roof_page+1,'points_per_foot':roof_scale,'width_pt':sizes[roof_page][0],
            'height_pt':sizes[roof_page][1],'plan_sha256':digest}
            if roof_page is not None and roof_view is not None and roof_scale is not None else None)
        dormer_groups=reviewed_dormers(plan,roof_candidates,dormer_review,frame)
        roof_candidates['inferred_dormer_components']=dormer_groups
        roof_candidates['dormer_pitch_review']=dormer_review
        for index,group in enumerate(dormer_groups,1):
            for measurement in group['measurements']:
                measurement['label']=f'Dormer {index} / '+measurement['label']
                measurement['color']=palette[len(measurements)%len(palette)]
                measurements.append(measurement)
    wall_candidates={'measurements':[], 'length_candidates':0, 'short_piece_candidates':0}
    wall_scale_review=None
    wall_printed_scales=None
    wall_status='floor_page_unresolved'
    floor_page=sheet_map.get('floor_area')
    if floor_page is not None:
        from wall_segment_candidates import candidates as wall_segments
        from dimension_scale import split_dimension_scale
        from sheet_scale_labels import scale_labels,corroborate_dimension_scale
        with fitz.open(plan) as doc:
            if wall_view is not None:
                bounds=wall_view['view_bounds_pt']
                wall_printed_scales=scale_labels(doc[floor_page],bounds)
                wall_scale_review=corroborate_dimension_scale(split_dimension_scale(doc[floor_page],bounds),wall_printed_scales)
            else:
                wall_printed_scales=scale_labels(doc[floor_page])
                wall_scale_review=corroborate_dimension_scale(split_dimension_scale(doc[floor_page]),wall_printed_scales)
            if wall_printed_scales['mixed_view_scales']:
                wall_status='view_scale_assignment_required'
            elif not wall_scale_review['usable_candidate']:
                wall_status='scale_unresolved'
            elif wall_view is not None:
                from wall_stroke_candidates import candidates as stroke_walls
                wall_candidates=stroke_walls(doc[floor_page],wall_scale_review['points_per_foot'],
                    wall_view['view_bounds_pt'],wall_view['allowed_styles'],
                    wall_depth['depth_inches'] if wall_depth is not None else None)
                if wall_view.get('extraction_method')=='filled_and_stroked':
                    from wall_candidate_merge import merge as merge_wall_candidates
                    wall_candidates=merge_wall_candidates(
                        wall_segments(doc[floor_page],wall_scale_review['points_per_foot']),
                        wall_candidates,wall_view['view_bounds_pt'])
                wall_status=('candidates_require_review' if wall_candidates['measurements'] else
                    'no_wall_pairs_match_stud_depth' if wall_candidates['depth_mismatched_intervals'] else
                    'no_reviewed_style_wall_pairs_found')
            else:
                wall_candidates=wall_segments(doc[floor_page],wall_scale_review['points_per_foot'])
                wall_status='candidates_require_review' if wall_candidates['measurements'] else 'no_filled_wall_rectangles_found'
        for measurement in wall_candidates['measurements']:
            calculate(measurement)
            measurement['scale_source']=wall_scale_review['method']
            if wall_depth is not None:measurement['wall_depth_basis']=wall_depth
            measurements.append(measurement)
    from native_area_candidates import from_review as native_areas
    area_review=native_areas(job,digest,set(selected_roles.values()) if reviewed.get('measurement_scope')=='reviewed_subset' else None)
    if area_review is None and floor_page is not None and selected_roles.get('area_schedule') is not None:
        from native_area_discovery import discover as discover_areas
        with fitz.open(plan) as doc:
            reference=doc[floor_page];target=doc[selected_roles['area_schedule']-1]
            bounds=wall_view['view_bounds_pt'] if wall_view is not None else list(reference.rect)
            calibration={**wall_scale_review,'mixed_view_scales':wall_printed_scales['mixed_view_scales']}
            try:area_review=discover_areas(reference,target,calibration,bounds)
            except ValueError as exc:
                area_review={'status':'automatic_area_discovery_requires_review','reason':str(exc),
                    'measurements':[],'certified':False,'order_released':False}
            if area_review is not None:
                area_review.update(plan_sha256=digest,reference_page=floor_page+1,
                    page=selected_roles['area_schedule'],review_sha256=None)
    if area_review is not None:
        for measurement in area_review['measurements']:calculate(measurement)
        measurements.extend(area_review['measurements'])
        (out/'native_area_candidates.json').write_text(json.dumps(area_review,indent=2)+'\n')
    if hashlib.sha256(plan.read_bytes()).hexdigest()!=digest:raise ValueError('Drawing changed during candidate extraction')
    if read_sheet_review(job)['review_sha256'] != reviewed['review_sha256']:
        raise ValueError('Sheet review changed during candidate extraction')
    if read_wall_view_review(job,selected_roles.get('floor'))!=wall_view:
        raise ValueError('Wall view review changed during candidate extraction')
    if read_roof_view_review(job,selected_roles.get('roof'))!=roof_view:
        raise ValueError('Roof view review changed during candidate extraction')
    if read_dormer_review(job,digest)!=dormer_review:
        raise ValueError('Dormer pitch review changed during candidate extraction')
    if read_outline_pitch_review(job,digest)!=outline_pitch_review:
        raise ValueError('Roof outline pitch review changed during candidate extraction')
    if read_roof_coverage_review(job,digest,selected_roles.get('roof'))!=roof_coverage:
        raise ValueError('Roof outline review changed during candidate extraction')
    if wall_view is not None and read_wall_depth_basis(job,digest)!=wall_depth:
        raise ValueError('Wall-depth assumption changed during candidate extraction')
    if door_specs is not None and read_door_specifications(job) != door_specs:
        raise ValueError('Door specifications changed during candidate extraction')
    if read_hardware_specifications(job) != hardware_specs:
        raise ValueError('Door hardware specifications changed during candidate extraction')
    (out/'takeoff.json').write_text(json.dumps(result,indent=2)+'\n')
    if window_cross_view is not None:
        shutil.copyfile(plan,out/'plan.pdf')
        (out/'window_cross_view_sources.json').write_text(json.dumps(window_sources,indent=2)+'\n')
        (out/'window_cross_view_candidates.json').write_text(json.dumps(window_cross_view,indent=2)+'\n')
    if roof_page is not None:
        (out/'roof_face_candidates.json').write_text(json.dumps({
            'plan_sha256':digest,'status':roof_extraction_status,'scale_review':roof_scale_review,
            'printed_scales':roof_printed_scales,'roof_view_review':roof_view,**roof_candidates},indent=2)+'\n')
    if floor_page is not None:
        (out/'wall_segment_candidates.json').write_text(json.dumps({
            'plan_sha256':digest,'status':wall_status,'scale_review':wall_scale_review,
            'printed_scales':wall_printed_scales,'wall_view_review':wall_view,'wall_depth_basis':wall_depth,**wall_candidates},indent=2)+'\n')
    if symbol_result is not None:
        (out/'electrical_symbol_candidates.json').write_text(json.dumps(symbol_result,indent=2)+'\n')
        (out/'electrical_symbol_definitions.json').write_text(json.dumps(symbol_config,indent=2)+'\n')
    if template_result is not None:
        (out/'electrical_template_candidates.json').write_text(json.dumps(template_result,indent=2)+'\n')
        (out/'electrical_template_definitions.json').write_text(json.dumps(template_config,indent=2)+'\n')
    if vector_result is not None:
        (out/'electrical_vector_candidates.json').write_text(json.dumps(vector_result,indent=2)+'\n')
        (out/'electrical_vector_definitions.json').write_text(json.dumps(vector_config,indent=2)+'\n')
    if stroke_result is not None:
        (out/'electrical_stroke_candidates.json').write_text(json.dumps(stroke_result,indent=2)+'\n')
        (out/'electrical_stroke_definitions.json').write_text(json.dumps(stroke_config,indent=2)+'\n')
    electrical=[]
    for source in (symbol_result,template_result,vector_result,stroke_result):
        if source is not None:electrical.extend(source['measurements'])
    measurements.extend(electrical)
    from wall_run_candidates import from_state as wall_runs
    wall_run_review=wall_runs({'plan_sha256':digest,'version':1,
        'measurements':{m['id']:m for m in measurements}})
    (out/'wall_run_candidates.json').write_text(json.dumps(wall_run_review,indent=2)+'\n')
    from wall_gap_labels import from_plan_state as wall_gap_labels
    wall_gap_review=wall_gap_labels(plan,{'plan_sha256':digest,'version':1,
        'measurements':{m['id']:m for m in measurements}})
    (out/'wall_gap_label_candidates.json').write_text(json.dumps(wall_gap_review,indent=2)+'\n')
    opening_mapping=None
    if measurements:
        rules=initial_rules(digest,measurements,[m['id'] for m in roof_candidates['measurements']],template,
                            electrical_ids=[m['id'] for m in electrical],
                            area_ids=[m['id'] for m in area_review['measurements']] if area_review is not None else ())
        for group in roof_cutout_groups:
            component_ids=[m['id'] for m in group['measurements']]
            rule=initial_rules(digest,measurements,component_ids,template)['rules'][0]
            rule.update(id='candidate-roof-cutouts-'+group['source_complex_face_sha256'][:16],
                label='Roof outer area less interior cutouts; dormer surfaces remain separate',
                surface_components=group['surface_components'],
                remaining=group['remaining']+rule['remaining'])
            rules['rules'].append(rule)
        for group in dormer_groups:
            component_ids=[m['id'] for m in group['measurements']]
            rule=initial_rules(digest,measurements,component_ids,template)['rules'][0]
            rule.update(id='candidate-inferred-dormer-'+group['source_geometry_sha256'][:16],
                label='Dormer surfaces with inferred pitch; partial roof scope',
                basis='Explicit source-bound level-ridge and valley interpretation with verified parent pitch arrow; inferred specification.',
                remaining=group['remaining']+rule['remaining'])
            rules['rules'].append(rule)
        shutil.copyfile(plan,out/'plan.pdf')
        (out/'measurements.json').write_text(json.dumps({'plan_sha256':digest,'measurements':measurements},indent=2)+'\n')
        (out/'template_rows.json').write_text(json.dumps(template,indent=2)+'\n')
        (out/'quantity_rules.json').write_text(json.dumps(rules,indent=2)+'\n')
        from company_scope_review import default_mapping as company_scope_mapping
        company_scope=company_scope_mapping(out,template,digest)
        if company_scope is not None:
            (out/'company_scope_review.json').write_text(json.dumps(company_scope,indent=2)+'\n')
            drywall_practice={key:company_scope[key] for key in ('plan_sha256','intake_path','intake_sha256')}
            (out/'drywall_practice_review.json').write_text(json.dumps(drywall_practice,indent=2)+'\n')
            (out/'wall_plate_reference.json').write_text(json.dumps(drywall_practice,indent=2)+'\n')
        from opening_quantity_review import default_mapping
        opening_mapping=default_mapping(out,template,digest)
        if opening_mapping['mappings']:
            (out/'opening_quantity_review.json').write_text(json.dumps(opening_mapping,indent=2)+'\n')
    roof_partition = None
    partition_measurements=list(roof_candidates['measurements'])
    terms=[{'measurement_id':m['id'],'kind':'area','operation':'add'} for m in partition_measurements]
    for group in roof_cutout_groups:
        partition_measurements.extend(group['measurements']);terms.extend(group['surface_components'])
    for group in dormer_groups:
        partition_measurements.extend(group['measurements'])
        terms.extend({'measurement_id':m['id'],'kind':'area','operation':'add'} for m in group['measurements'])
    if partition_measurements:
        from roof_partition_state import audit_state
        config={'plan_sha256':digest,'measurement_ids':[m['id'] for m in partition_measurements],
            'cutout_terms':terms,'coverage_review_sha256':roof_coverage['review_sha256'] if roof_coverage is not None else None}
        unresolved_roof=[r for r in roof_candidates.get('unresolved_source_outlines',[]) if r['source_style_reviewed']]
        if unresolved_roof:config['unresolved_source_outlines']=unresolved_roof
        (out/'roof_partition_inputs.json').write_text(json.dumps(config,indent=2)+'\n')
        if roof_coverage is not None:shutil.copyfile(job/'roof_coverage_review.json',out/'roof_coverage_review.json')
        roof_partition=audit_state({'plan_sha256':digest,'version':1,
            'measurements':{m['id']:m for m in partition_measurements}},config,roof_coverage)
        (out/'roof_partition_review.json').write_text(json.dumps(roof_partition,indent=2)+'\n')
    summary={'plan_sha256':digest,'sheet_map_candidates':sheet_map,
        'window_cross_view_status':'candidates_require_review' if window_cross_view is not None else 'reviewed_floor_and_elevation_pages_required',
        'window_cross_view_candidate_count':len(window_cross_view['unrepresented_elevation_tags']) if window_cross_view is not None else None,
        **({'native_area_candidates':len(area_review['measurements']),'native_area_review_sha256':area_review['review_sha256'],
            'native_area_status':area_review.get('status','reviewed_view_candidates')} if area_review is not None else {}),
        'sheet_coverage_passed':reviewed['coverage_passed'],
        'measurement_scope':reviewed.get('measurement_scope', 'reviewed_set'),
        'missing_sheet_roles':reviewed.get('missing_roles', []),
        'unresolved_sheet_issues':reviewed.get('unresolved_issues', []),
        'unresolved_page_roles':reviewed['roles_requiring_disambiguation'],
        'sheet_review_sha256':reviewed['review_sha256'],
        'engine_region_scale_reviews':{str(page+1):review for page,review in region_scales.items()},
        'editable_region_candidates':sum(m['kind']=='area' for m in measurements),'rejected_editor_geometry':rejected,
        'editable_count_candidates':len(electrical),'editable_measurements':len(measurements),
        'editable_length_candidates':sum(m['kind']=='length' for m in measurements),
        'wall_segment_candidates':wall_candidates['length_candidates'],
        'wall_short_piece_candidates':wall_candidates['short_piece_candidates'],
        'wall_extraction_status':wall_status,'wall_coverage_certified':False,
        'wall_view_review_sha256':wall_view['review_sha256'] if wall_view is not None else None,
        'wall_stroke_ambiguous_pairs':len({p['pair_index'] for p in wall_candidates.get('ambiguous_pairs',[])}),
        'wall_stroke_ambiguous_intervals':len(wall_candidates.get('ambiguous_pairs',[])),
        'wall_stroke_blocked_intervals':len(wall_candidates.get('blocked_intervals',[])),
        'wall_stroke_short_intervals':len(wall_candidates.get('short_unblocked_intervals',[])),
        'wall_stroke_depth_mismatched_intervals':len(wall_candidates.get('depth_mismatched_intervals',[])),
        'wall_depth_basis':wall_depth,
        'wall_candidate_file':'wall_segment_candidates.json' if floor_page is not None else None,
        'wall_run_candidate_file':'wall_run_candidates.json',
        'wall_gap_label_candidate_file':'wall_gap_label_candidates.json',
        'wall_gap_tag_matches':sum(g['status']=='unique_tag_location_candidate' for g in wall_gap_review['gaps']),
        'wall_short_piece_direction_candidates':sum(p['axis'] is not None for p in wall_gap_review['short_piece_directions']['pieces']),
        'wall_direction_assisted_tag_matches':sum(g['status']=='unique_tag_location_candidate' for g in wall_gap_review['direction_assisted']['gaps']),
        'wall_run_candidates':len(wall_run_review['run_candidates']),
        'wall_run_unresolved_pieces':len(wall_run_review['unresolved_measurements']),
        'wall_network_inferred_pieces':len(wall_run_review['wall_network_inference']['decisions']),
        'wall_network_inferred_short_piece_axes':{i:d['axis'] for i,d in wall_run_review['wall_network_inference']['decisions'].items() if 'axis' in d},
        'wall_network_parallel_layer_ambiguities':wall_run_review['wall_network_inference']['parallel_layer_ambiguities'],
        'roof_face_candidates':len(roof_candidates['measurements']),
        'roof_unresolved_source_outlines':len(roof_candidates.get('unresolved_source_outlines',[])),
        'roof_cutout_face_groups':len(roof_cutout_groups),
        'roof_inferred_dormer_face_candidates':sum(len(g['measurements']) for g in dormer_groups),
        'roof_dormer_review_sha256':dormer_review['review_sha256'] if dormer_review is not None else None,
        'roof_cutout_measurement_candidates':sum(len(g['measurements']) for g in roof_cutout_groups),
        'roof_unpitched_interior_face_candidates':sum(len(g['faces'])
            for network in roof_candidates.get('edge_network_diagnostics',[])
            for g in network.get('unpitched_interior_faces',[])),
        'roof_uncalibrated_geometry_candidates':len(roof_candidates.get('uncalibrated_geometry',[])),
        'roof_view_review_sha256':roof_view['review_sha256'] if roof_view is not None else None,
        'roof_candidate_file':'roof_face_candidates.json' if roof_page is not None else None,
        'roof_partition_file':'roof_partition_review.json' if roof_partition is not None else None,
        'electrical_extraction_status':('candidates_require_review' if symbol_result['measurements'] else 'no_labels_extracted') if symbol_result is not None else 'legend_definitions_required',
        'electrical_count_candidates':len(symbol_result['measurements']) if symbol_result is not None else 0,
        'electrical_candidate_file':'electrical_symbol_candidates.json' if symbol_result is not None else None,
        'electrical_template_status':('candidates_require_review' if template_result['measurements'] else 'no_matches_scope_unresolved') if template_result is not None else 'template_definitions_required',
        'electrical_template_candidate_file':'electrical_template_candidates.json' if template_result is not None else None,
        'electrical_vector_status':('candidates_require_review' if vector_result['measurements'] else 'no_matches_scope_unresolved') if vector_result is not None else 'vector_definitions_required',
        'electrical_vector_candidate_file':'electrical_vector_candidates.json' if vector_result is not None else None,
        'electrical_stroke_status':('candidates_require_review' if stroke_result['measurements'] else 'no_matches_scope_unresolved') if stroke_result is not None else 'stroke_definitions_required',
        'electrical_stroke_candidate_file':'electrical_stroke_candidates.json' if stroke_result is not None else None,
        'electrical_coverage_certified':False,
        'roof_extraction_status':roof_extraction_status,'roof_coverage_certified':False,
        'roof_scale_review':roof_scale_review,
        'roof_printed_scales':roof_printed_scales,
        'roof_pitch_labels_requiring_review':roof_candidates['unmatched_or_ambiguous_pitch_labels'],
        'engine_status':result['status'],'scope_review_required':True,
        'company_intake':'../estimate_intake.json','current_prices':{},'whole_house_total':None,
        'estimate_released':False,'editor_available':bool(measurements)}
    summary['template_draft_available']=bool(measurements)
    from area_schedule_check import compare as compare_area_schedule
    area_check=compare_area_schedule(inventory.get('area_schedule_references',[]),measurements)
    (out/'initial_area_schedule_check.json').write_text(json.dumps(area_check,indent=2)+'\n')
    summary['initial_area_schedule_check_file']='initial_area_schedule_check.json'
    summary['initial_area_schedule_check_status']=area_check['status']
    summary['template_rows']=len(template['rows'])
    summary['opening_quantity_mapping_file']='opening_quantity_review.json' if opening_mapping and opening_mapping['mappings'] else None
    summary['opening_quantity_mapped_template_rows']=len(opening_mapping['mappings']) if opening_mapping else 0
    summary['unresolved_opening_template_scopes']=opening_mapping['unresolved_template_scopes'] if opening_mapping else []
    if door_specs is not None:
        from company_profile import scope_allowances
        intake=json.loads((job/'estimate_intake.json').read_text(encoding='utf-8'))
        summary['unlocated_scope_allowances']=scope_allowances(intake['settings'],intake['provenance'])
        summary['door_core_specifications'] = '../door_core_specifications.json'
        summary['door_core_specifications_sha256'] = hashlib.sha256((job/'door_core_specifications.json').read_bytes()).hexdigest()
        summary['door_core_assigned_openings'] = sum(o['core'] is not None for o in door_specs['openings'])
        summary['door_core_unresolved_opening_ids'] = door_specs['unresolved_opening_ids']
        summary['door_core_schedule_available'] = door_specs['schedule_sha256'] is not None
        summary['door_core_schedule_complete'] = door_specs['complete_door_schedule']
        summary['door_core_schedule_status'] = door_specs['status']
    if hardware_specs is not None:
        summary['door_hardware_specifications'] = '../door_hardware_specifications.json'
        summary['door_hardware_specifications_sha256'] = hashlib.sha256((job/'door_hardware_specifications.json').read_bytes()).hexdigest()
        summary['door_hardware_assigned_openings'] = sum(o['hardware_function'] is not None for o in hardware_specs['openings'])
        summary['door_hardware_unresolved_opening_ids'] = hardware_specs['unresolved_opening_ids']
        summary['door_hardware_schedule_complete'] = hardware_specs['complete_hardware_schedule']
        summary['door_hardware_schedule_status'] = hardware_specs['status']
    if measurements and (out/'company_scope_review.json').exists():
        from company_scope_bids import from_folder as company_bid_scopes,write_drafts
        bids=company_bid_scopes(out)
        files=write_drafts(bids,out/'company_bid_scopes')
        summary['company_scope_bid_files']=['company_bid_scopes/'+name for name in files]
        summary['company_scope_bids_sent']=False
    if roof_partition is not None:
        from roof_bid_scope import from_folder as roof_bid_scope,write_draft
        bid=roof_bid_scope(out)
        files=write_draft(bid,out/'roof_bid_scope')
        summary['roof_bid_scope_files']=['roof_bid_scope/'+name for name in files]
        summary['roof_bid_scope_sha256']=bid['scope_sha256']
        summary['roof_bid_scope_sent']=False
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--job',required=True)
    print(json.dumps(measure_job(parser.parse_args().job)))
