"""Convert reviewed roof-face allocations to whole field-shingle bundles."""
import copy
import hashlib
import json
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path
from bid_comparison import scope_digest
from roof_bid_scope import from_folder as roof_scope


def number(value, positive=True):
    try:
        parsed=Decimal(str(value))
    except InvalidOperation:
        raise ValueError('Finite numeric material quantity required') from None
    if isinstance(value,bool) or not parsed.is_finite() or (parsed<=0 if positive else parsed<0):
        raise ValueError('Positive coverage/area and nonnegative waste required')
    return Fraction(parsed)


def calculate(scope,review=None):
    if scope_digest(scope)!=scope.get('scope_sha256'):
        raise ValueError('Roof scope fingerprint does not match its contents')
    faces={};seen=set()
    for item in scope['items']:
        identity=item['id']
        if identity in seen:
            raise ValueError('Roof scope item IDs must be unique')
        seen.add(identity)
        dimension=(item.get('surface'),item.get('reference_unit'))
        if dimension==('roof','SF'):
            faces[identity]=item
        elif dimension!=('roof_edge','LF'):
            raise ValueError('Roof material scope requires roof faces in SF or roof edges in LF')
    result={'plan_sha256':scope['plan_sha256'],'scope_sha256':scope['scope_sha256'],
        'measurement_version':scope['measurement_version'],'groups':[],
        'pending_face_ids':list(faces),'status':'Material selections not reviewed',
        'source_exceptions':copy.deepcopy(scope['source_exceptions']),
        'accessories_included':False,'whole_roof_order_quantity':None,
        'ready_to_order':False,'scope_coverage_certified':False,'reviewer_authenticated':False}
    if review is None:return result
    if (review.get('plan_sha256')!=scope['plan_sha256'] or
            review.get('scope_sha256')!=scope['scope_sha256']):
        result['status']='Material quantities withheld: roof scope changed; review allocations again'
        return result
    if not review.get('reviewer') or not review.get('basis') or not review.get('groups'):
        raise ValueError('Material allocations need a named reviewer, basis and groups')
    claimed=set();products=set();group_ids=set()
    for group in review['groups']:
        identity=group['id'];product=group['product_id'];ids=group['face_ids']
        if (not identity or identity in group_ids or not product or product in products or
                not ids or len(ids)!=len(set(ids)) or any(i not in faces or i in claimed for i in ids)):
            raise ValueError('Use unique product groups with nonoverlapping known roof faces')
        if group.get('roofing_system')!='shingle' or group.get('purchase_unit')!='bundle':
            raise ValueError('Area conversion supports shingle bundles; metal needs a reviewed panel cut list')
        if not group.get('selection_source_ref') or not group.get('waste_source_ref') or not group.get('coverage_source_ref'):
            raise ValueError('Product selection, waste and package coverage each need a source reference')
        area=sum((number(faces[i]['reference_quantity']) for i in ids),Fraction(0))
        waste=number(group['waste_percent'],positive=False)
        coverage=number(group['package_coverage']['area_sf'])/number(group['package_coverage']['bundles'])
        required=area*(1+waste/100);raw_bundles=required/coverage
        bundles=-(-raw_bundles.numerator//raw_bundles.denominator)
        purchased=coverage*bundles
        result['groups'].append({**copy.deepcopy(group),'measured_surface_sf':float(area),
            'waste_area_sf':float(required-area),'required_with_waste_sf':float(required),
            'purchase_quantity':bundles,'purchased_coverage_sf':float(purchased),
            'rounding_surplus_sf':float(purchased-required),
            'measured_roofing_squares':float(area/100),
            'waste_inclusive_roofing_squares':float(required/100),
            'purchased_roofing_squares':float(purchased/100),
            'billing_basis':None,'unit_price':None,'line_cost':None})
        claimed.update(ids);products.add(product);group_ids.add(identity)
    result['pending_face_ids']=[i for i in faces if i not in claimed]
    result['status']='Draft field-shingle quantities; accessories, billing and full scope remain separate'
    result['material_review_sha256']=hashlib.sha256(json.dumps(review,sort_keys=True,allow_nan=False).encode()).hexdigest()
    return result


def from_folder(folder):
    folder=Path(folder);scope=roof_scope(folder)
    path=folder/'roof_material_review.json'
    raw=path.read_bytes() if path.exists() else None
    review=json.loads(raw) if raw is not None else None
    if review is not None:
        references=review.get('evidence',[])
        if not references:raise ValueError('Material review needs local source evidence')
        names=set()
        for ref in references:
            source=(folder/ref['file']).resolve()
            if (not source.is_relative_to(folder.resolve()) or not source.is_file() or
                    hashlib.sha256(source.read_bytes()).hexdigest()!=ref['sha256']):
                raise ValueError('Material source missing, changed or outside the job')
            names.add(ref['file'])
        for group in review.get('groups',[]):
            for key in ('selection_source_ref','waste_source_ref','coverage_source_ref'):
                ref=group.get(key,{})
                if not isinstance(ref,dict) or ref.get('file') not in names or not ref.get('location'):
                    raise ValueError('Material source reference needs an evidence file and location')
    result=calculate(scope,review)
    if (path.read_bytes() if path.exists() else None)!=raw:
        raise ValueError('Material review changed during calculation')
    return result
