"""Assign reviewed kit or individual-item counts to one supplemental cost owner."""
import copy
import hashlib
import json
import math
from pathlib import Path


def import_kit_purchases(draft, config, folder):
    if config['plan_sha256']!=draft['plan_sha256']:
        raise ValueError('Kit mapping belongs to another drawing')
    result=copy.deepcopy(draft);root=Path(folder).resolve()
    rows={r['row_id']:r for r in result['rows']}
    extras=result.setdefault('additional_cost_rows',[])
    occupied=set(rows)|{r['row_id'] for r in extras}
    for reference in config['purchases']:
        path=(root/reference['file']).resolve()
        if not path.is_relative_to(root) or not path.is_file():raise ValueError('Kit evidence must be inside the job')
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=reference['sha256']:raise ValueError('Kit evidence changed')
        purchase=json.loads(raw)
        if purchase['plan_sha256']!=draft['plan_sha256']:raise ValueError('Kit evidence belongs to another drawing')
        for dependency in purchase.get('evidence_files',[]):
            evidence=(root/dependency['file']).resolve()
            if (not evidence.is_relative_to(root) or not evidence.is_file()
                    or hashlib.sha256(evidence.read_bytes()).hexdigest()!=dependency['sha256']):
                raise ValueError('Purchase source evidence is missing or changed')
        ownership=purchase.get('ownership','row')
        if ownership not in ('row','assembly_input'):raise ValueError('Unknown kit ownership mode')
        identity=purchase['row_id'];original=rows[purchase['replaces_row_id']];parent=rows[purchase['parent_row_id']]
        if identity in occupied:raise ValueError('Duplicate kit cost owner')
        if (original['cost_type'] not in ('MATERIAL','ALLOWANCE','SUBCONTRACTOR') or original['completion_status'].startswith('not_applicable')
                or original.get('cost_owner_row_id') or original.get('covered_by_package')
                or any(original.get(k) is not None for k in ('draft_quantity','unit_cost','line_cost','line_price'))):
            raise ValueError('Kit reference is excluded or already assigned')
        if (parent['cost_type'] not in ('GROUP','ASSEMBLY') or original['parent']!=parent['name']
                or parent.get('completion_status','').startswith('not_applicable')
                or parent.get('covered_by_package') or any(parent.get(k) is not None for k in ('unit_cost','line_cost','line_price'))):
            raise ValueError('Kit needs its unpriced template parent')
        pending_item = purchase['unit']=='each' and purchase.get('product_status')=='specification_pending'
        packed_item = purchase['unit']=='pack' and purchase.get('product_status')=='identified'
        identified_item = purchase['unit'] in ('each','pack') and purchase.get('product_status')=='identified'
        if packed_item and (type(purchase.get('units_per_pack')) is not int
                or purchase['units_per_pack']<=0 or not purchase.get('evidence_files')):
            raise ValueError('Pack purchase needs a positive whole pack size and source evidence')
        if not packed_item and 'units_per_pack' in purchase:
            raise ValueError('Pack size requires an identified pack purchase')
        assortment = purchase['unit']=='each' and purchase.get('product_status')=='reviewed_assortment'
        installed_scope = purchase['unit']=='each' and purchase.get('product_status')=='installed_scope'
        if installed_scope:
            if (original['cost_type']!='SUBCONTRACTOR' or ownership!='assembly_input'
                    or not purchase.get('installed_scope') or not purchase.get('evidence_files')
                    or purchase.get('product_id') or purchase.get('model')):
                raise ValueError('Installed scope needs subcontract markup, an explicit assembly input and source-backed specification')
        elif original['cost_type']=='SUBCONTRACTOR':
            raise ValueError('Subcontract count needs an installed-scope mapping')
        elif assortment:
            members=purchase.get('items',[])
            if (ownership!='assembly_input' or purchase.get('product_id') or purchase.get('model')
                    or purchase.get('selection_status') not in ('selected','estimating_candidate')
                    or not purchase.get('evidence_files') or not members
                    or any(not p.get('id') or not p.get('model') or not p.get('source_ref')
                           or type(p.get('quantity')) is not int or p['quantity']<=0 for p in members)
                    or len({p['id'] for p in members})!=len(members)):
                raise ValueError('Assortment needs source-backed individual models and positive whole counts')
        elif pending_item:
            if ownership!='assembly_input' or purchase.get('product_id') or purchase.get('model'):
                raise ValueError('Unspecified individual item needs an assembly input, without an invented product')
        elif identified_item:
            if (ownership!='assembly_input' or not purchase.get('product_id') or not purchase.get('model')
                    or purchase.get('selection_status') not in ('selected','estimating_candidate')):
                raise ValueError('Identified item needs an assembly input, product, model and explicit selection status')
        elif purchase['unit']!='kit' or not purchase.get('product_id') or not purchase.get('model'):
            raise ValueError('Kit needs a reviewed product and purchase-unit basis')
        if not purchase.get('basis') or not purchase.get('source'):
            raise ValueError('Count purchase needs a reviewed source and purchase-unit basis')
        inputs=[q for q in original.get('assembly_inputs',[]) if q['id']==purchase['assembly_input_id']]
        pending=[q for q in result.get('pending_quantities',[]) if q['id']==purchase['assembly_input_id']
                 and str(original['excel_row']) in map(str,q['template_rows'])]
        if len(inputs)>1 or (inputs and pending) or (not inputs and len(pending)!=1):
            raise ValueError('Kit needs exactly one live count or pending count reference')
        owners=original.get('assembly_input_cost_owners',{})
        if purchase['assembly_input_id'] in owners:raise ValueError('Assembly input already has a purchase owner')
        other_inputs=[q for q in original.get('assembly_inputs',[]) if q['id']!=purchase['assembly_input_id']]
        other_pending=[q for q in result.get('pending_quantities',[]) if q['id']!=purchase['assembly_input_id']
                       and str(original['excel_row']) in map(str,q['template_rows'])]
        if ownership=='row' and (owners or other_inputs or other_pending):
            raise ValueError('Whole-row kit mapping would hide other assembly scope')
        quantity=None
        if inputs:
            value=inputs[0]
            quantity=value['quantity']
            if (value['unit']!='EA' or type(quantity) not in (int,float) or not math.isfinite(quantity)
                    or quantity<0 or int(quantity)!=quantity):
                raise ValueError('Kit purchase requires a whole nonnegative EA count')
            quantity=int(quantity)
        if ownership=='row':
            original.update(cost_owner_row_id=identity,pricing_role='cost_reference')
            mapping={'replaces_row_id':original['row_id']}
        else:
            original['pricing_role']='input_only'
            original.setdefault('assembly_input_cost_owners',{})[purchase['assembly_input_id']]=identity
            mapping={'source_row_id':original['row_id'],'source_assembly_input_id':purchase['assembly_input_id']}
        source={'file':str(path),'sha256':reference['sha256']}
        remaining=list(purchase.get('remaining',[]))
        if pending_item:
            remaining.append('Product specification unresolved; no price assigned' if purchase.get('supply_status')=='separate' and purchase.get('evidence_files')
                else 'Product specification and supplier package inclusion unresolved; no price assigned')
        if pending:remaining.append('Linked measurement scope review outstanding; kit quantity withheld')
        if assortment and quantity is not None and sum(p['quantity'] for p in members)!=quantity:
            quantity=None
            remaining.append('Measured count differs from the reviewed product assortment; revise the item schedule before pricing')
        count_reference=copy.deepcopy(inputs[0] if inputs else pending[0])
        pack_basis={}
        if packed_item:
            size=purchase['units_per_pack'];required=quantity
            quantity=None if required is None else (required+size-1)//size
            pack_basis={'units_per_pack':size,'required_units':required,'rounding':'whole_up',
                'product':f"{purchase['model']} ({size} items per pack)",
                'quantity':quantity,'unit':'pack','required_quantity':required,'coverage_unit':'EA',
                'source':purchase['source'],
                'purchased_units':None if quantity is None else quantity*size,
                'surplus_units':None if quantity is None else quantity*size-required}
        if inputs:
            inputs[0]['remaining']=remaining
            inputs[0]['purchase_cost_owner']=identity
            if pending_item:inputs[0]['label']=purchase['name']
        extras.append({'row_id':identity,**mapping,'parent_row_id':parent['row_id'],
          'name':purchase['name'],'parent':parent['name'],'cost_type':original['cost_type'],
          'unit':purchase['unit'],'markup_pct':original['markup_pct'],'markup_source_row_id':original['row_id'],
          'draft_quantity':quantity,'unit_cost':None,'line_cost':None,'line_price':None,
          'pricing_role':'cost_line','completion_status':'evidence_in_progress','certified':False,
          'current_price_certified':False,'assembly_inputs':[],
          'quantity_sources':[{'id':purchase['assembly_input_id']+'-purchase','quantity':quantity,'unit':purchase['unit'],
            'kind':'reviewed_assortment_purchase' if assortment else ('reviewed_installed_scope' if installed_scope else ('reviewed_item_purchase' if identified_item else ('reviewed_count_purchase' if pending_item else 'reviewed_kit_purchase'))),
            'source':source,'basis':purchase['basis'],'remaining':remaining,
            **({'purchase_pack':pack_basis} if packed_item else {}),
            **({'selection_status':purchase['selection_status']} if identified_item else {}),
            **({'selection_status':purchase['selection_status'],'items':copy.deepcopy(members)} if assortment else {}),
            **({'installed_scope':purchase['installed_scope']} if installed_scope else {}),
            'product_id':purchase.get('product_id'),'model':purchase.get('model'),
            'count_reference':count_reference}]})
        occupied.add(identity)
    result.update(whole_house_total=None,estimate_released=False)
    return result
