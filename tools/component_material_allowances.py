"""Price explicitly mapped stock candidates; never turn a subset into a trade total."""
from decimal import Decimal,ROUND_HALF_UP
from datetime import date
from urllib.parse import urlsplit
import hashlib
import json
import math


def public_allowance_catalog(catalog, records, as_of):
    """Add reviewed public unit prices without presenting them as supplier quotes."""
    rates=list(catalog['rates']);keys={(r['sku'],r['unit']) for r in rates}
    day=date.fromisoformat(as_of)
    for record in records:
        observed=date.fromisoformat(record['observed_on'])
        price=Decimal(str(record['unit_price']))
        sku=record['sku'];unit=record['unit'];url=record['price_url']
        if (observed>day or not isinstance(sku,str) or not sku.strip() or unit!='EA'
                or not price.is_finite() or price<=0 or record.get('currency')!='USD'
                or record.get('price_kind')!='public_dated_allowance'
                or record.get('tax_included') is not False or record.get('delivery_included') is not False
                or not record.get('description') or not record.get('location_limit')
                or not isinstance(url,str) or urlsplit(url).scheme!='https' or not urlsplit(url).netloc):
            raise ValueError('Reviewed public material allowance needs dated USD each price, source and explicit limits')
        if (sku,unit) in keys:raise ValueError('Public material allowance duplicates an existing product rate')
        keys.add((sku,unit))
        rates.append({'sku':sku,'unit':unit,'date':record['observed_on'],'unit_price':str(price),
            'status':'dated_allowance_candidate','selected_sources':[dict(record)]})
    return {**catalog,'rates':rates}


def calculate(components, mappings, catalog):
    by_id={c['id']:c for c in components};rates={(r['sku'],r['unit']):r for r in catalog['rates']}
    if len(by_id)!=len(components) or len(rates)!=len(catalog['rates']):
        raise ValueError('Unique material components and rate keys required')
    if len({m['component_id'] for m in mappings})!=len(mappings):
        raise ValueError('A material component may have only one rate mapping')
    priced=[];unpriced=[];mapped=set()
    for mapping in mappings:
        identity=mapping['component_id'];mapped.add(identity);component=by_id.get(identity)
        if component is None:
            unpriced.append({'component_id':identity,'reason':'Component not present in current cut candidates; no quantity assumed'})
            continue
        purchase_unit=component['unit']
        if 'scheduled_piece_sha256' in mapping:
            digest=hashlib.sha256(json.dumps(component,sort_keys=True,allow_nan=False).encode()).hexdigest()
            length=component.get('stock_length_ft')
            if (component['unit']!='EA' or mapping['quantity_unit']!='stick'
                    or digest!=mapping['scheduled_piece_sha256']
                    or not component.get('source_snapshot',{}).get('supplier_layout_sha256')
                    or type(length) not in (int,float) or not math.isfinite(length) or length<=0
                    or component.get('scheduled_lf')!=component['quantity']*length):
                raise ValueError('Scheduled piece mapping needs unchanged supplier evidence and consistent whole-stock footage')
            purchase_unit='stick'
        if (mapping['quantity_unit'] not in ('sheet','stick') or purchase_unit!=mapping['quantity_unit']
                or mapping['rate_unit']!='EA' or not mapping.get('basis')):
            raise ValueError('Material allowance needs explicit whole-piece unit and product basis')
        if component.get('sku')!=mapping.get('source_sku'):
            raise ValueError('Material component SKU differs from its reviewed mapping')
        if component.get('stock_length_ft')!=mapping.get('stock_length_ft'):
            raise ValueError('Material component stock length differs from its reviewed mapping')
        quantity=component['quantity']
        if type(quantity) is not int or quantity<0:raise ValueError('Whole nonnegative material pieces required')
        rate=rates.get((mapping['sku'],mapping['rate_unit']))
        if rate is None or rate['status']!='dated_allowance_candidate' or rate['unit_price'] is None:
            unpriced.append({'component_id':identity,'quantity':quantity,'unit':component['unit'],
                             'reason':'No unambiguous compatible dated rate'})
            continue
        price=Decimal(rate['unit_price'])
        if not price.is_finite() or price<=0:raise ValueError('Positive finite material rate required')
        extension=(quantity*price).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
        priced.append({'component_id':identity,'label':component['label'],'sku':mapping['sku'],
            'quantity':quantity,'quantity_unit':purchase_unit,'supplier_sales_unit':mapping['rate_unit'],
            'dated_unit_price':str(price),'pretax_extension':str(extension),'source_date':rate['date'],
            'rate_sources':rate['selected_sources'],'product_match_basis':mapping['basis'],
            'quantity_source':component.get('source_snapshot'),'quantity_certified_for_order':False})
    for component in components:
        if component['id'] not in mapped:
            unpriced.append({'component_id':component['id'],'quantity':component['quantity'],
                             'unit':component['unit'],
                             'reason':('No reviewed product/rate mapping' if component['unit'] in ('sheet','stick')
                                       else 'Measured assembly input needs a purchase-unit/product mapping; no stock quantity or price assumed')})
    return {'status':'Partial dated material allowance; incomplete framing scope',
        'priced_components':priced,'unpriced_components':unpriced,
        'priced_component_subtotal_before_tax_delivery_markup':str(sum(
            (Decimal(r['pretax_extension']) for r in priced),Decimal('0.00'))),
        'full_framing_total':None,'current_price_certified':False,'purchase_authorized':False,
        'tax_included':False,'delivery_included':False,'markup_included':False}
