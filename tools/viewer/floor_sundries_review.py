"""Read-only partial sundries review derived from current linked floor measurements."""
import hashlib
import json
import math
from pathlib import Path
from shapely.geometry import Polygon
from shapely.affinity import scale,translate
from measurement_store import MeasurementStore,encode
from floor_finish_faces import derive_linked_finish_field
from floor_sundries import calculate_allowance


def from_folder(folder, state):
    root=Path(folder).resolve();config=json.loads((root/'floor_sundries_review.json').read_bytes())
    path=(root/config['source_file']).resolve()
    if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest()!=config['source_sha256']:
        raise ValueError('Floor sundries product evidence changed')
    proof=json.loads(path.read_bytes())
    if proof['plan_sha256']!=state['plan_sha256']:
        raise ValueError('Floor sundries belong to another plan')
    links=json.loads((root/'linked_quantity_reviews.json').read_bytes())
    link=next(l for l in links if l['job']==config['linked_job'])
    linked_root=(root/link['job']).resolve()
    for filename,key in [('measurements.json','config_sha256'),('quantity_rules.json','rules_sha256')]:
        if hashlib.sha256((linked_root/filename).read_bytes()).hexdigest()!=link[key]:
            raise ValueError('Linked floor review mapping changed')
    linked=MeasurementStore(linked_root).read()
    derived,basis=derive_linked_finish_field(linked,state,link['derived_floor_field'],root)
    field=derived['measurements'][config['field_id']];excluded=derived['measurements'][config['exclude_id']]
    if field['page']!=excluded['page'] or not math.isclose(field['points_per_foot'],excluded['points_per_foot']):
        raise ValueError('Floor and shower need one calibrated sheet')
    polygon=Polygon(field['points']).difference(Polygon(excluded['points']))
    origin=polygon.bounds[:2]
    polygon=scale(translate(polygon,-origin[0],-origin[1]),1/field['points_per_foot'],1/field['points_per_foot'],origin=(0,0))
    result=calculate_allowance(polygon,proof['products'])
    result.update(plan_sha256=state['plan_sha256'],measurement_version=state['version'],
        linked_measurement_version=linked['version'],source_geometry_sha256=hashlib.sha256(encode(state['measurements']).encode()).hexdigest(),
        linked_geometry_sha256=hashlib.sha256(encode(linked['measurements']).encode()).hexdigest(),
        basis=basis,product_evidence_sha256=config['source_sha256'],
        plan_origin_points=list(origin),points_per_foot=field['points_per_foot'],
        included_in_estimate_total=False)
    return result
