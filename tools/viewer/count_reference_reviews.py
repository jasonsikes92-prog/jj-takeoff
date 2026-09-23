"""Check package-reference and selected-fixture counts against reviewed sources.

This verifies a count reference, not its owning trade's design, material assembly,
price, or procurement readiness. Selected fixtures additionally require matching
original selected-product counts and plan evidence. Areas and lengths use other gates.
"""
import copy
import hashlib
import json
import math
from pathlib import Path
from urllib.parse import urlsplit
from openpyxl import load_workbook
from jnj_takeoff import Quantity, certify
from measurement_store import encode


def count_digest(row):
    keys=('row_id','name','unit','draft_quantity','quantity_sources','assembly_inputs',
          'covered_by_package','cost_owner_row_id','completion_status')
    return hashlib.sha256(encode({k:row.get(k) for k in keys}).encode()).hexdigest()


def whole(value):
    return type(value) in (int,float) and math.isfinite(value) and value>=0 and int(value)==value


def current_count_review(row, scope='package_count_reference'):
    review=row.get('count_reference_review',{})
    return (review.get('status')=='verified_count_reference'
            and review.get('row_sha256')==count_digest(row)
            and review.get('quantity')==row.get('draft_quantity')
            and review.get('review_scope','package_count_reference')==scope
            and (scope!='selected_fixture_count' or
                 (review.get('product_id')==row.get('price_evidence',{}).get('product_id')
                  and review.get('model')==row.get('price_evidence',{}).get('model')))
            and row.get('unit') in ('each','EA'))


def selected_fixture_matches(record, row, checked):
    selection=record.get('selected_item',{})
    path=checked.get(selection.get('source_id'))
    pointer=selection.get('json_pointer')
    if path is None or not isinstance(pointer,str) or not pointer.startswith('/'):
        return False
    try:
        item=json.loads(path.read_bytes())
        for token in pointer[1:].split('/'):
            token=token.replace('~1','/').replace('~0','~')
            if isinstance(item,list):
                if not token.isascii() or not token.isdecimal() or str(int(token))!=token:
                    return False
                item=item[int(token)]
            else:item=item[token]
        evidence=row.get('price_evidence',{})
        product=selection.get('product_id');model=selection.get('model')
        return (isinstance(item,dict) and item.get('status')=='SELECTED'
                and item.get('id')==selection.get('option_id')
                and whole(item.get('quantity')) and item['quantity']==row['draft_quantity']
                and isinstance(product,str) and bool(product) and bool(model)
                and product==evidence.get('product_id') and model==evidence.get('model')
                and item.get('url')==selection.get('url')
                and urlsplit(item['url']).path.rstrip('/').endswith('/'+product))
    except (KeyError,IndexError,TypeError,ValueError):
        return False


def supplier_schedule_matches(record, row, checked):
    """Reconcile opening identities and component counts to a source-bound supplier schedule."""
    try:
        schedule=json.loads(checked[record['schedule_source_id']].read_bytes())
        specification=checked[record['specification_source_id']]
        if hashlib.sha256(specification.read_bytes()).hexdigest()!=schedule['sources']['specifications.pdf']:
            return False
        basis=record['count_basis']
        kinds={'assembly':'enumerated_window_assemblies','component':'enumerated_window_components',
               'trim_assembly':'enumerated_window_trim_assemblies'}
        if basis not in kinds:return False
        kind=kinds[basis]
        sources=row['quantity_sources']
        if len(sources)!=1 or sources[0]['kind']!=kind:return False
        original=schedule['assemblies'];mapped=sources[0]['assemblies']
        def index(items):
            identities=[p['opening_id'] for p in items]
            if not identities or len(set(identities))!=len(identities):raise ValueError('Duplicate opening identity')
            if any(not whole(p[k]) or p[k]<1 for p in items for k in ('assembly_quantity','component_count','source_plan_sheet')):
                raise ValueError('Invalid supplier assembly count')
            return {p['opening_id']:tuple(p[k] for k in ('assembly_quantity','component_count','source_plan_sheet')) for p in items}
        if basis=='trim_assembly':
            # Installed trim is billed per opening, independently of board cuts.
            # Still require every supplier opening exactly once and its actual count.
            source_index=index(original)
            identities=[p['opening_id'] for p in mapped]
            if len(identities)!=len(set(identities)) or set(identities)!=set(source_index):return False
            if any(not whole(p['assembly_quantity']) or p['assembly_quantity']!=source_index[p['opening_id']][0]
                   for p in mapped):return False
            if (row.get('cost_type')!='SUBCONTRACTOR' or row.get('price_evidence',{}).get('source_unit')!='trimmed opening'
                    or row.get('price_evidence',{}).get('units_per_source_unit')!=1):return False
        elif index(original)!=index(mapped):return False
        count=sum(p['assembly_quantity']*(p['component_count'] if basis=='component' else 1) for p in original)
        return count==row['draft_quantity']
    except (KeyError,TypeError,ValueError):return False


def owner_count_matches(record, row, checked):
    """Bind a simple owner count to the numeric answer in the returned workbook."""
    try:
        binding=record['owner_answer']
        submission=json.loads(checked[binding['submission_source_id']].read_bytes())
        workbook=checked[binding['workbook_source_id']]
        if submission['source_workbook_sha256']!=hashlib.sha256(workbook.read_bytes()).hexdigest():
            return False
        answers=[a for a in submission['records'] if a['question_id']==binding['question_id']]
        if len(answers)!=1:return False
        answer=answers[0]
        if (not whole(answer['answer']) or answer['answer']!=row['draft_quantity']
                or any(answer[k]!=binding[k] for k in ('sheet','cell','question','context'))):
            return False
        book=load_workbook(workbook,read_only=True,data_only=False,keep_links=False)
        try:
            sheet=book[binding['sheet']];cell=sheet[binding['cell']]
            return (cell.column==5 and cell.data_type=='n' and whole(cell.value)
                    and cell.value==answer['answer']
                    and sheet.cell(cell.row,1).value==binding['question_id']
                    and sheet.cell(cell.row,3).value==binding['question']
                    and sheet.cell(cell.row,4).value==binding['context'])
        finally:book.close()
    except (KeyError,TypeError,ValueError):return False


def apply_count_reviews(draft, config, folder):
    result=copy.deepcopy(draft);root=Path(folder).resolve()
    rows={r['row_id']:r for r in result['rows']};seen=set()
    for item in config['rows']:
        identity=item['row_id']
        if identity not in rows or identity in seen:
            raise ValueError('Count review needs unique existing template rows')
        seen.add(identity);row=rows[identity]
        row['count_reference_review']={'status':'review_required','reason':'Source or quantity changed'}
        if config.get('plan_sha256')!=draft['plan_sha256']:
            continue
        path=(root/item['file']).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            continue
        if hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
            continue
        record=json.loads(path.read_bytes())
        scope=record.get('scope')
        if (scope not in ('package_count_reference','selected_fixture_count','supplier_schedule_count','owner_confirmed_count') or record.get('row_id')!=identity
                or record.get('plan_sha256')!=draft['plan_sha256']
                or record.get('measurement_version')!=draft['measurement_version']
                or record.get('row_sha256')!=count_digest(row)):
            continue
        owner=rows.get(row.get('covered_by_package'),{})
        if (row.get('unit') not in ('each','EA')
                or row.get('cost_owner_row_id') or row.get('completion_status','').startswith('not_applicable')
                or not whole(row.get('draft_quantity'))):
            continue
        if scope=='package_count_reference' and (owner.get('row_id') in (None,identity)
                or any(row.get(k) is not None for k in ('unit_cost','line_cost','line_price'))
                or owner.get('pricing_basis') not in ('reviewed_package','dated_package_allowance')
                or owner.get('price_evidence',{}).get('billing_basis')!='fixed_package'
                or identity not in owner.get('price_evidence',{}).get('covered_row_ids',[])):
            continue
        if scope=='selected_fixture_count' and (row.get('cost_type') not in ('MATERIAL','ALLOWANCE')
                or row.get('covered_by_package') or row.get('assembly_inputs')
                or row.get('pricing_role')=='input_only' or not row.get('quantity_sources')
                or record.get('source_type')!='MEASURED'):
            continue
        trim_count=scope=='supplier_schedule_count' and record.get('count_basis')=='trim_assembly'
        if scope=='supplier_schedule_count' and (row.get('cost_type') not in (('SUBCONTRACTOR',) if trim_count else ('MATERIAL','ALLOWANCE','LABOR'))
                or row.get('covered_by_package') or (row.get('assembly_inputs') and not trim_count)
                or row.get('pricing_role')=='input_only' or record.get('source_type')!='MEASURED'):
            continue
        if trim_count and any(q.get('id')!='window-rough-opening-perimeter' or q.get('use')!='assembly_input'
                              for q in row.get('assembly_inputs',[])):
            continue
        if trim_count and (not isinstance(record.get('remaining_scope',[]),list)
                           or any(not isinstance(s,str) or not s.strip() for s in record.get('remaining_scope',[]))):
            continue
        if scope=='owner_confirmed_count' and (row.get('cost_type') not in ('MATERIAL','ALLOWANCE','FEE')
                or row.get('covered_by_package') or row.get('assembly_inputs')
                or row.get('pricing_role')=='input_only' or record.get('source_type')!='GIVEN'
                or not record.get('given_by','').startswith('Jason')
                or len(row.get('quantity_sources',[]))!=1
                or row['quantity_sources'][0].get('source_kind')!='owner_confirmation'
                or row['quantity_sources'][0].get('quantity')!=row['draft_quantity']):
            continue
        if any(str(row['excel_row']) in map(str,p.get('template_rows',[])) for p in draft.get('pending_quantities',[])):
            continue
        sources=record.get('sources',[]);checked={};source_ok=bool(sources)
        for source in sources:
            original=(root/source['file']).resolve()
            if (not original.is_relative_to(root) or original==path or not original.is_file()
                    or source['id'] in checked or not source.get('reference')
                    or hashlib.sha256(original.read_bytes()).hexdigest()!=source.get('sha256')):
                source_ok=False;break
            checked[source['id']]=original
        parts=record.get('check_components',[])
        if not source_ok or not parts or not record.get('reviewer') or not record.get('review_basis'):
            continue
        if scope=='selected_fixture_count':
            plan=checked.get(record.get('plan_source_id'))
            if (plan is None or hashlib.sha256(plan.read_bytes()).hexdigest()!=draft['plan_sha256']
                    or not selected_fixture_matches(record,row,checked)):
                continue
        if scope=='supplier_schedule_count':
            plan=checked.get(record.get('plan_source_id'))
            if (plan is None or hashlib.sha256(plan.read_bytes()).hexdigest()!=draft['plan_sha256']
                    or not supplier_schedule_matches(record,row,checked)):
                continue
        if scope=='owner_confirmed_count':
            plan=checked.get(record.get('plan_source_id'))
            if (plan is None or hashlib.sha256(plan.read_bytes()).hexdigest()!=draft['plan_sha256']
                    or not owner_count_matches(record,row,checked)):
                continue
        if any(not p.get('label') or not whole(p.get('count')) or not p.get('source_ids')
               or set(p['source_ids'])-set(checked) for p in parts):
            continue
        check=sum(p['count'] for p in parts)
        if not whole(record.get('quantity')) or check!=record['quantity'] or check!=row['draft_quantity']:
            continue
        kind=record.get('source_type')
        if kind=='MEASURED':
            view=checked.get(record.get('view_source_id'))
            if view is None or view.suffix.lower() not in ('.png','.jpg','.jpeg') or not record.get('sheet'):
                continue
            quantity=Quantity(row['name'],row['draft_quantity'],'EA','MEASURED',sheet=record['sheet'],view=str(view))
        elif kind=='GIVEN' and record.get('given_by'):
            quantity=Quantity(row['name'],row['draft_quantity'],'EA','GIVEN',given_by=record['given_by'])
        else:
            continue
        # Core Quantity uses relative error and cannot reconcile a zero denominator.
        # Exact whole-count equality above is the zero-count check.
        if check: quantity.reconcile(check,0,against=record['review_basis'])
        ok,report=certify([quantity])
        if not ok:continue
        row['count_reference_review']={'status':'verified_count_reference','row_sha256':count_digest(row),
            'quantity':check,'unit':'EA','source_type':kind,'count_reconciled':True,
            'independent_accuracy_validation':'not_established',
            'record':copy.deepcopy(item),'core_quantity_check':report,
            'scope':'Count reference only; owning package scope, pricing and procurement remain separate.'}
        row['count_reference_review']['review_scope']=scope
        if scope=='selected_fixture_count':
            row['count_reference_review'].update(product_id=record['selected_item']['product_id'],
                model=record['selected_item']['model'],
                scope='Selected fixture count for estimating. Installation, rough-in fit, delivery and procurement remain separate.')
        if scope=='supplier_schedule_count':
            row['count_reference_review'].update(count_basis=record['count_basis'],
                scope='Supplier assembly/component count reconciled to plan openings. Product fit, installation supplies, prices and procurement remain separate.')
            if trim_count:
                row['count_reference_review']['scope']='Installed window trim count only; board quantities and other trimmed openings are separate.'
                row['count_reference_review']['remaining_scope']=copy.deepcopy(record.get('remaining_scope',[]))
        if scope=='owner_confirmed_count':
            row['count_reference_review'].update(question_id=record['owner_answer']['question_id'],
                scope='Owner-confirmed item count for this project. Not independently measured; price and procurement remain separate.')
    return result
