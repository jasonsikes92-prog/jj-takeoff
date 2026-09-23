"""Keep gross wall-face references distinct from floor area and trade billing."""
import copy
import hashlib
import json
import math
from shapely.geometry import Polygon


def attach(result):
    output=copy.deepcopy(result);measured=[];missing=[]
    for r in output['regions']:
        ceiling=r['ceiling_surface'];height=r['ceiling_reference']['noted_height_inches']
        reference={'status':'unresolved_wall_height_or_profile','gross_wall_surface_sf':None,
            'gross_wall_plus_ceiling_sf':None,'drywall_scope_confirmed':False,'purchase_quantity':None}
        if ceiling['status']=='current_source_review' and ceiling['surface_type']=='flat' and height is not None:
            if type(height) not in (int,float) or not math.isfinite(height) or height<=0:
                raise ValueError('Wall reference needs a finite positive ceiling height')
            shape=Polygon(r['points'],r['holes']);perimeter=shape.length/r['points_per_foot']
            wall_sf=perimeter*height/12
            reference.update(status='constant_height_geometric_reference',wall_height_inches=height,
                boundary_perimeter_lf=perimeter,gross_wall_surface_sf=wall_sf,
                gross_wall_plus_ceiling_sf=wall_sf+ceiling['surface_area_sf'],
                opening_deductions_applied=False,waste_applied=False,
                source_ceiling_review_sha256=ceiling['source_sha256'],
                basis='Current room boundary including hole boundaries times its noted height, under a reviewed flat ceiling. '
                    'Virtual opening closures remain in gross area; wall finishes and billing basis require separate scope review.')
            measured.append(reference)
        else:missing.append(r['id'])
        r['wall_surface_reference']=reference
    output['wall_surface_review']={'measured_region_count':len(measured),'unresolved_region_ids':missing,
        'gross_wall_subtotal_sf':math.fsum(m['gross_wall_surface_sf'] for m in measured) if measured else None,
        'gross_wall_plus_ceiling_subtotal_sf':math.fsum(m['gross_wall_plus_ceiling_sf'] for m in measured) if measured else None,
        'whole_house_drywall_quantity':None,'billing_quantity':None,'purchase_quantity':None,'estimate_released':False}
    output['source_sha256']=hashlib.sha256(json.dumps([result['source_sha256'],
        output['wall_surface_review'],[r['wall_surface_reference'] for r in output['regions']]],sort_keys=True,allow_nan=False).encode()).hexdigest()
    return output
