"""Compare current opening widths with source header cuts; never size supports."""
import hashlib
import json
import math
from pathlib import Path


def positive(value):
    if type(value) not in (int,float) or not math.isfinite(value) or value<=0:
        raise ValueError('Opening and header dimensions must be finite and positive')
    return value


def review(state,bindings,headers,products,supplier_headers=None):
    header_by_id={h['id']:h for h in headers}
    product_by_id={p['opening_id']:p for p in products}
    if len(header_by_id)!=len(headers) or len(product_by_id)!=len(products):
        raise ValueError('Duplicate header or product opening ID')
    supplier_headers=supplier_headers or []
    supplier_by_id={h['opening_id']:h for h in supplier_headers}
    if len(supplier_by_id)!=len(supplier_headers) or not set(supplier_by_id)<=set(b['opening_id'] for b in bindings):
        raise ValueError('Supplier header alternatives need unique mapped openings')
    seen=set();rows=[];geometry=[];opening_geometry={}
    for binding in bindings:
        identity=binding['opening_id']
        if not isinstance(identity,str) or not identity.strip() or identity in seen:
            raise ValueError('Unique opening IDs required')
        seen.add(identity)
        if not binding.get('source'):raise ValueError('Opening/header mapping source required')
        measured=None;flags=[];geometry_start=len(geometry)
        measurement_id=binding.get('measurement_id')
        span_ids=binding.get('span_measurement_ids',[measurement_id] if measurement_id is not None else [])
        if len(span_ids)!=len(set(span_ids)) or (measurement_id is not None and measurement_id not in span_ids):
            raise ValueError('Opening span needs unique measurements including its selected opening')
        if span_ids:
            spans=[];reference_line=None
            for span_id in span_ids:
                m=state['measurements'][span_id]
                if m['kind']!='length' or len(m['points'])!=2 or m['page']!=binding['measurement_page']:
                    raise ValueError('Opening width requires a straight length on the mapped sheet')
                scale=positive(m['points_per_foot']);a,b=m['points']
                positive(math.dist(a,b))
                if len(span_ids)>1:
                    axis=0 if abs(a[1]-b[1])<1e-6 else 1
                    if abs(a[1-axis]-b[1-axis])>=1e-6:
                        raise ValueError('Combined opening spans must be collinear')
                    line=(axis,a[1-axis],scale)
                    if reference_line is not None and (line[0]!=reference_line[0]
                            or abs(line[1]-reference_line[1])>1e-6 or line[2]!=reference_line[2]):
                        raise ValueError('Combined opening spans must share a line and scale')
                    reference_line=line;spans.append(sorted((a[axis],b[axis])))
                else:measured=positive(math.dist(a,b)/scale*12)
                geometry.append({'id':span_id,'page':m['page'],'points':m['points'],'points_per_foot':scale})
            if spans:
                spans.sort();start,end=spans[0]
                for next_start,next_end in spans[1:]:
                    if abs(next_start-end)>1e-6:
                        raise ValueError('Combined opening spans must meet without a gap or overlap')
                    end=next_end
                measured=positive((end-start)/scale*12)
        else:flags.append('opening_geometry_not_linked')
        opening_geometry[identity]=(hashlib.sha256(json.dumps(geometry[geometry_start:],
            sort_keys=True,separators=(',',':')).encode()).hexdigest() if span_ids else None)
        product=product_by_id.get(identity)
        specified=positive(product['rough_opening_width_in']) if product else None
        if product and not product.get('source'):raise ValueError('Product dimension source required')
        if product is None:flags.append('product_rough_opening_unverified')
        if measured is not None and specified is not None and abs(measured-specified)>.125:
            flags.append('drawn_width_differs_from_product_reference')
        header_id=binding.get('header_id')
        header=header_by_id[header_id] if header_id is not None else None
        length=positive(header['length_inches']) if header else None
        widths=[v for v in (measured,specified) if v is not None]
        reference=max(widths) if widths else None
        remaining=length-reference if length is not None and reference is not None else None
        status=('header_not_documented' if header is None else 'opening_width_unresolved' if reference is None else
            'header_shorter_than_opening_reference' if remaining<0 else
            'no_length_left_for_end_support' if remaining==0 else 'end_support_length_unverified')
        rows.append({'opening_id':identity,'header_id':header_id,'measurement_id':measurement_id,
            'drawn_width_inches':measured,'product_rough_opening_width_inches':specified,
            'comparison_width_inches':reference,'header_cut_length_inches':length,
            'length_remaining_for_both_supports_inches':remaining,'status':status,'flags':flags,
            'mapping_source':binding['source'],'product_source':product['source'] if product else None,
            'king_stud_count':None,'jack_stud_count':None,'purchase_order_released':False})
        if len(span_ids)>1:rows[-1]['span_measurement_ids']=span_ids
        supplier=supplier_by_id.get(identity)
        if supplier is not None:
            if (header is None or supplier.get('header_id')!=header_id
                    or positive(supplier['plan_cut_length_inches'])!=length
                    or any(not isinstance(supplier.get(k),str) or not supplier[k].strip()
                           for k in ('member_id','product','source'))):
                raise ValueError('Supplier header alternative needs matching plan cut and source')
            stock=positive(supplier['stock_length_inches'])
            supplier_remaining=stock-reference if reference is not None else None
            supplier_flags=[]
            if stock<length:supplier_flags.append('supplier_stock_shorter_than_plan_cut')
            if supplier_remaining is not None and supplier_remaining<=0:
                supplier_flags.append('supplier_stock_has_no_end_support_length')
            rows[-1]['supplier_alternative']={
                'member_id':supplier['member_id'],'product':supplier['product'],'source':supplier['source'],
                'stock_length_inches':stock,'stock_minus_plan_cut_inches':stock-length,
                'length_remaining_for_both_supports_inches':supplier_remaining,'flags':supplier_flags,
                'revision_matches_plan_verified':False,'adopted_as_replacement':False,
                'structural_adequacy_verified':False,'purchase_order_released':False}
    digest=hashlib.sha256(json.dumps(sorted(geometry,key=lambda m:m['id']),sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return {'method':'source_header_opening_width_review_v1','plan_sha256':state['plan_sha256'],
        'measurement_version':state['version'],'measurement_inputs_sha256':digest,'openings':rows,
        'opening_geometry_sha256':opening_geometry,
        'structural_adequacy_verified':False,'purchase_order_released':False,
        'limitations':['Header cut length is not clear span. Positive remaining length does not prove bearing capacity, king/jack counts or structural adequacy.',
            'Drawn and product widths remain separate. The larger is used only to screen the documented header length.',
            'The one-eighth-inch discrepancy threshold is a drawing comparison tolerance, not an installation tolerance.']}


def from_folder(folder,state):
    folder=Path(folder).resolve();path=folder/'opening_header_review.json';raw=path.read_bytes();config=json.loads(raw)
    if config['plan_sha256']!=state['plan_sha256']:raise ValueError('Opening/header review source plan changed')
    loaded={};hashes={};checked=[]
    def evidence(reference):
        source=(folder/reference['path']).resolve()
        if not source.is_relative_to(folder):raise ValueError('Opening/header evidence must remain inside the job')
        data=source.read_bytes();digest=hashlib.sha256(data).hexdigest()
        if digest!=reference['sha256']:raise ValueError('Opening/header evidence changed; reconcile its mapping')
        checked.append((source,digest))
        return data
    for key in ('headers','products')+ (('supplier_headers',) if 'supplier_headers' in config else ()):
        data=evidence(config[key]);loaded[key]=json.loads(data);hashes[key]=hashlib.sha256(data).hexdigest()
    if loaded['headers']['sha256']!=state['plan_sha256']:
        raise ValueError('Header inventory belongs to a different drawing')
    linked=[];merged={**state,'measurements':dict(state['measurements'])}
    for reference in config.get('linked_measurements',[]):
        from measurement_store import MeasurementStore
        job=(folder/reference['job']).resolve()
        if not job.is_relative_to(folder.parent) or job==folder:
            raise ValueError('Linked header measurements must belong to a neighboring job')
        source=job/'measurements.json'
        if hashlib.sha256(source.read_bytes()).hexdigest()!=reference['config_sha256']:
            raise ValueError('Linked header measurement configuration changed')
        store=MeasurementStore(job);current=store.read()
        if current['plan_sha256']!=state['plan_sha256']:
            raise ValueError('Linked header measurements belong to another drawing')
        if not reference['measurement_ids'] or len(reference['measurement_ids'])!=len(set(reference['measurement_ids'])):
            raise ValueError('Linked header measurements need unique identities')
        for identity in reference['measurement_ids']:
            if identity in merged['measurements']:raise ValueError('Linked header measurement identity is duplicated')
            merged['measurements'][identity]=current['measurements'][identity]
        linked.append((store,current['version']))
        checked.append((source,reference['config_sha256']))
    supplier=loaded.get('supplier_headers')
    if supplier is not None:
        if supplier['plan_sha256']!=state['plan_sha256'] or not supplier.get('documents'):
            raise ValueError('Supplier headers need matching plan and original documents')
        for document in supplier['documents']:evidence(document)
    result=review(merged,config['bindings'],loaded['headers']['headers'],loaded['products']['openings'],
                  supplier['openings'] if supplier is not None else None)
    result.update(mapping_sha256=hashlib.sha256(raw).hexdigest(),evidence_sha256=hashes)
    if linked:
        result['linked_measurement_versions']=[{'job':str(store.folder),'version':version} for store,version in linked]
        if any(store.read()['version']!=version for store,version in linked):
            raise ValueError('Linked header measurements changed during review; retry')
    if path.read_bytes()!=raw:raise ValueError('Opening/header mapping changed during review')
    for source,digest in checked:
        if hashlib.sha256(source.read_bytes()).hexdigest()!=digest:
            raise ValueError('Opening/header evidence changed during review')
    return result
