"""Import owner-confirmed or document-reviewed counts without fabricated geometry."""
import copy
import hashlib
import json
import math
from pathlib import Path


def import_counts(draft,config,folder):
    if config.get('plan_sha256')!=draft['plan_sha256'] or config.get('reviewed') is not True:
        raise ValueError('Owner item mapping requires the matching plan and review')
    root=Path(folder).resolve();result=copy.deepcopy(draft)
    rows={r['row_id']:r for r in result['rows']};seen=set();direct=set();claims=set()
    for item in config['items']:
        identity=item['id'];targets=item['row_ids'];source=item['source']
        if not identity or identity in seen or not targets or len(set(targets))!=len(targets):
            raise ValueError('Owner item IDs and target rows must be unique')
        seen.add(identity)
        path=(root/source['file']).resolve()
        if not path.is_relative_to(root) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=source['sha256']:
            raise ValueError('Owner item evidence missing or changed')
        record=json.loads(path.read_bytes())
        source_kind=item.get('source_kind','owner_confirmation')
        if (source_kind not in ('owner_confirmation','documented_scope_count')
                or record.get('source_kind')!=source_kind or record.get('plan_sha256')!=draft['plan_sha256']):
            raise ValueError('Item count needs matching source type and plan')
        if source_kind=='documented_scope_count':
            documents=record.get('documents')
            if not isinstance(documents,list) or not documents or not record.get('review_basis'):
                raise ValueError('Document count requires original sources and review basis')
            document_paths=set();located_counts=[]
            for document in documents:
                original=(root/document['file']).resolve()
                if (not original.is_relative_to(root) or original==path or original in document_paths
                        or not original.is_file() or hashlib.sha256(original.read_bytes()).hexdigest()!=document.get('sha256')
                        or not document.get('source_ref')):
                    raise ValueError('Document count original source is missing, changed or unlocated')
                if 'json_pointer' in document:
                    pointer=document['json_pointer']
                    if 'page' in document or not isinstance(pointer,str) or not pointer.startswith('/'):
                        raise ValueError('Document count JSON location must be an explicit pointer without a page')
                    try:
                        value=json.loads(original.read_bytes())
                        for token in pointer[1:].split('/'):
                            token=token.replace('~1','/').replace('~0','~')
                            if isinstance(value,list):
                                if not token.isascii() or not token.isdecimal() or (len(token)>1 and token.startswith('0')):
                                    raise ValueError('Invalid array index')
                                value=value[int(token)]
                            else:value=value[token]
                    except (ValueError,KeyError,IndexError,TypeError) as error:
                        raise ValueError('Document count JSON location is missing or invalid') from error
                    if type(value) is not int or value<0:
                        raise ValueError('Document count JSON location must reference a whole count')
                    located_counts.append(value)
                elif type(document.get('page')) is not int or document['page']<1:
                    raise ValueError('Document count original source is missing, changed or unlocated')
                document_paths.add(original)
            if 'include_assembly_input_ids' in item:
                raise ValueError('Document counts cannot use an owner-count combination')
        count=record
        for key in source['field'].split('.'):
            if not isinstance(count,dict) or key not in count:raise ValueError('Owner item count source field is missing')
            count=count[key]
        if type(count) is not int or count<0:raise ValueError('Owner item count must be a nonnegative whole number')
        if source_kind=='documented_scope_count' and any(value!=count for value in located_counts):
            raise ValueError('Document count differs from the original JSON quantity')
        if item['use'] not in ('template_quantity','assembly_input','supplemental_purchase','project_input') or not item.get('basis') or not item.get('label'):
            raise ValueError('Owner item needs a label, basis and quantity use')
        if 'include_assembly_input_ids' in item and item['use']!='template_quantity':
            raise ValueError('Combined counts must supply a template quantity')
        q={'id':identity,'label':item['label'],'quantity':count,'unit':'EA','use':item['use'],
            'source_kind':source_kind,'source':copy.deepcopy(source),'basis':item['basis'],
            'remaining':item.get('remaining',[]),'measurement_ids':[],
            'certified':False,'current_price':None,'order_released':False}
        if source_kind=='documented_scope_count':q['documents']=copy.deepcopy(documents)
        for target in targets:
            claim=(target,str(path),source['field'])
            if claim in claims:raise ValueError('Owner source count already assigned to this row')
            claims.add(claim)
            if target not in rows:raise ValueError('Unknown owner item target')
            row=rows[target]
            if item['use']=='project_input':
                if (source_kind!='owner_confirmation' or len(targets)!=1
                        or row.get('parent','').strip().upper()!='INPUTS'
                        or row.get('pricing_role')!='input_only'
                        or row.get('unit')!='month' or item.get('unit')!='month'
                        or record.get('unit')!='month' or count<=0
                        or row.get('completion_status','').startswith('not_applicable')
                        or row.get('draft_quantity') is not None or target in direct
                        or row.get('quantity_sources') or row.get('assembly_inputs')
                        or row.get('covered_by_package') or row.get('cost_owner_row_id')
                        or any(row.get(k) is not None for k in ('unit_cost','line_cost','line_price'))):
                    raise ValueError('Project duration requires an unassigned, unpriced month input and matching owner source')
                direct.add(target);row['draft_quantity']=count
                row.setdefault('quantity_sources',[]).append({**copy.deepcopy(q),'unit':'month'})
                continue
            if item['use']=='supplemental_purchase':
                purchase=item.get('purchase',{});parent=rows.get(purchase.get('parent_row_id'),{})
                extras=result.setdefault('additional_cost_rows',[])
                if (len(targets)!=1 or not purchase.get('row_id') or purchase['row_id'] in rows
                        or any(r['row_id']==purchase['row_id'] for r in extras)
                        or not purchase.get('name') or not purchase.get('product_id') or not purchase.get('model')
                        or purchase.get('selection_status') not in ('selected','estimating_candidate')
                        or record.get('purchase')!=purchase):
                    raise ValueError('Supplemental purchase needs a unique identified product matching the reviewed source')
                if (row.get('cost_type') not in ('MATERIAL','ALLOWANCE') or row.get('unit') not in ('each','EA')
                        or row.get('completion_status','').startswith('not_applicable')
                        or parent.get('cost_type')!='ASSEMBLY' or row.get('parent')!=parent.get('name')
                        or parent.get('completion_status','').startswith('not_applicable') or parent.get('covered_by_package')
                        or any(parent.get(k) is not None for k in ('unit_cost','line_cost','line_price'))):
                    raise ValueError('Supplemental purchase needs a matching unpriced parent and material markup source')
                try:markup=float(row['markup_pct'])
                except (ValueError,TypeError,KeyError) as error:raise ValueError('Invalid supplemental purchase markup') from error
                if not math.isfinite(markup) or markup<0:raise ValueError('Invalid supplemental purchase markup')
                extras.append({'row_id':purchase['row_id'],'parent_row_id':purchase['parent_row_id'],
                    'name':purchase['name'],'parent':parent['name'],'cost_type':row['cost_type'],'unit':'each',
                    'markup_pct':row['markup_pct'],'markup_source_row_id':target,
                    'draft_quantity':count,'unit_cost':None,'line_cost':None,'line_price':None,
                    'pricing_role':'cost_line','completion_status':'evidence_in_progress',
                    'certified':False,'current_price_certified':False,'assembly_inputs':[],
                    'quantity_sources':[{**copy.deepcopy(q),'kind':'reviewed_item_purchase',
                        'product_id':purchase['product_id'],'model':purchase['model'],
                        'selection_status':purchase['selection_status']}],
                    'scope_note':item['basis']})
                continue
            partial_reference=(item['use']=='assembly_input' and bool(row.get('assembly_input_cost_owners'))
                               and identity not in row['assembly_input_cost_owners'])
            if (row['cost_type'] not in ('MATERIAL','LABOR','ALLOWANCE','SUBCONTRACTOR')
                    or (row.get('pricing_role')=='input_only' and not partial_reference)
                    or row.get('parent','').strip().upper()=='INPUTS'
                    or row['completion_status'].startswith('not_applicable')
                    or row.get('covered_by_package') or row.get('cost_owner_row_id') or row.get('line_cost') is not None):
                raise ValueError('Owner item target is not an available cost scope')
            if any(v.get('id')==identity for v in row.get('quantity_sources',[])+row.get('assembly_inputs',[])):
                raise ValueError('Owner item already assigned to this row')
            if item['use']=='template_quantity':
                if row['unit'] not in ('each','EA') or row.get('draft_quantity') is not None or target in direct:
                    raise ValueError('Owner item direct count requires an unassigned each row')
                combined=copy.deepcopy(q)
                if 'include_assembly_input_ids' in item:
                    identities=item['include_assembly_input_ids']
                    if not isinstance(identities,list) or not identities or len(identities)!=len(set(identities)):
                        raise ValueError('Combined count needs unique assembly input IDs')
                    parts=[];measured=set();pending_parts=[]
                    for part_id in identities:
                        matches=[v for v in row.get('assembly_inputs',[]) if v.get('id')==part_id]
                        pending=[v for v in result.get('pending_quantities',[]) if v.get('id')==part_id
                                 and str(row.get('excel_row')) in map(str,v.get('template_rows',[]))]
                        if not matches and len(pending)==1:
                            pending_parts.append(part_id);continue
                        if len(matches)!=1:raise ValueError('Combined count assembly input missing or duplicated')
                        part=matches[0];value=part.get('quantity')
                        if (part.get('unit')!='EA' or type(value) not in (int,float)
                                or not math.isfinite(value) or value<0 or int(value)!=value):
                            raise ValueError('Combined count requires complete whole EA inputs')
                        markers=set(part.get('measurement_ids',[]))
                        if measured & markers:raise ValueError('Combined count repeats a measured item')
                        measured.update(markers);parts.append(copy.deepcopy(part))
                    if pending_parts:
                        result.setdefault('pending_quantities',[]).append({**combined,'quantity':None,
                            'owner_confirmed_count':count,'template_rows':[str(row['excel_row'])],
                            'missing_assembly_input_ids':pending_parts,
                            'reason':'Combined count awaits review of its measured inputs'})
                        direct.add(target);continue
                    combined.update(quantity=count+sum(int(p['quantity']) for p in parts),
                        owner_confirmed_count=count,source_kind='owner_and_measured_count',
                        included_assembly_inputs=parts,measurement_ids=sorted(measured))
                direct.add(target);row['draft_quantity']=combined['quantity']
                row.setdefault('quantity_sources',[]).append(combined)
            else:row.setdefault('assembly_inputs',[]).append(copy.deepcopy(q))
    return result
