"""Retain filled wall evidence and withhold overlapping stroke alternatives."""
import copy
from shapely.geometry import box, Polygon


def merge(filled, stroked, bounds):
    result=copy.deepcopy(stroked)
    fills=[copy.deepcopy(m) for m in filled['measurements']
           if box(*bounds).covers(box(*m['source_bounds_pt']))]
    depth=stroked.get('expected_depth_inches')
    excluded=[]
    if depth is not None:
        excluded=[m for m in fills if abs(m['drawn_thickness_inches']-depth)>.125]
        for m in excluded:
            m['requires_wall_classification']=True
            m['expected_depth_inches']=depth
            m['scope_status']='Drawn wall thickness differs from the saved depth; review the plan wall type before quantity use'
    kept=list(fills);duplicates=[];conflicts=[]
    for candidate in stroked['measurements']:
        shape=(Polygon(candidate['source_outline_pt']) if candidate.get('source_outline_pt')
               else box(*candidate['source_bounds_pt']))
        overlaps=[m for m in fills if m['page']==candidate['page']
                  and box(*m['source_bounds_pt']).intersection(shape).area>1e-6]
        exact=[m for m in overlaps if box(*m['source_bounds_pt']).symmetric_difference(shape).area<1e-6]
        if exact:
            exact[0].setdefault('alternative_source_measurements',[]).append(copy.deepcopy(candidate))
            duplicates.append({'retained_id':exact[0]['id'],'duplicate_id':candidate['id']})
        elif overlaps:
            conflicts.append({'candidate':copy.deepcopy(candidate),
                              'overlapping_filled_ids':[m['id'] for m in overlaps],
                              'reason':'Overlapping source interpretations; withheld pending geometry review'})
        else:kept.append(copy.deepcopy(candidate))
    result.update(method='filled_and_stroked_wall_candidates_v1',measurements=kept,
                  length_candidates=sum(m['kind']=='length' for m in kept),
                  short_piece_candidates=sum(m['kind']=='area' for m in kept),
                  duplicate_source_candidates=duplicates,withheld_overlap_candidates=conflicts,
                  filled_depth_mismatches=excluded,
                  coverage_certified=False)
    return result
