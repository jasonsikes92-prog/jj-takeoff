"""Read linked, editable roof-edge references without authorizing purchases."""
import hashlib
import json
from pathlib import Path
from measurement_store import MeasurementStore
from measurement_quantities import geometry_digest


def linked_folder(folder,config):
    folder=Path(folder).resolve();linked=(folder/config['job']).resolve()
    if not linked.is_relative_to(folder.parent) or linked==folder:
        raise ValueError('Roof edges must use a separate review inside this job')
    return linked


def from_folder(folder,plan_sha256,version):
    folder=Path(folder);path=folder/'roof_edge_review.json'
    if not path.exists():return None
    raw=path.read_bytes();config=json.loads(raw);parent=MeasurementStore(folder);state=parent.read()
    if config['plan_sha256']!=plan_sha256 or state['plan_sha256']!=plan_sha256 or state['version']!=version:
        raise ValueError('Roof edge review belongs to a different plan or revision')
    if not config.get('basis') or not config.get('roof_measurements'):
        raise ValueError('Roof edges require source basis and roof-face bindings')
    for identity,digest in config['roof_measurements'].items():
        if identity not in state['measurements'] or geometry_digest(state['measurements'][identity])!=digest:
            raise ValueError('Roof faces changed; reconcile the edge review')
    store=MeasurementStore(linked_folder(folder,config));edges=store.read()
    if edges['plan_sha256']!=plan_sha256 or edges['config_sha256']!=config['config_sha256']:
        raise ValueError('Linked roof-edge plan or configuration changed')
    items=[]
    for identity,m in edges['measurements'].items():
        if m['kind']!='length' or m.get('edge_role') not in ('eave','rake','ridge','valley','hip','wall_flashing'):
            raise ValueError('Explicit roof-edge length and role required')
        items.append({'id':'roof-edge:'+identity,'measurement_id':identity,'label':m['label'],
            'plan_pdf_page':m['page'],'surface':'roof_edge','edge_role':m['edge_role'],
            'reference_quantity':m['result']['quantity'],'reference_unit':'LF',
            'quantity_basis':m['result'].get('length_basis','projected level edge length'),
            'purchase_quantity':None,'bidder_status':None,'quoted_quantity':None,'quoted_unit':None,
            'unit_price':None,'quote_page_line':None,'inclusion_exclusion_notes':None})
    if path.read_bytes()!=raw or parent.read()!=state or store.read()!=edges:
        raise ValueError('Roof edge sources changed during calculation')
    return {'items':items,'mapping_sha256':hashlib.sha256(raw).hexdigest(),
        'edge_measurement_version':edges['version'],'edge_config_sha256':edges['config_sha256'],
        'basis':config['basis'],'complete_accessory_scope':False,'purchase_quantity':None}
