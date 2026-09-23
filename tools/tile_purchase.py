"""Calculate whole tile packages from installed areas and owner waste."""
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
import copy
import hashlib
import json
from pathlib import Path


def purchase(areas_sf, coverage_sf, waste_percent, package_price):
    """Pool one product once; installation areas remain separate from ordering."""
    values=[*areas_sf,coverage_sf,waste_percent,package_price]
    if not areas_sf or any(type(v) not in (int,float) for v in values):
        raise ValueError('Tile purchasing requires numeric areas, coverage, waste and package price')
    numbers=[Decimal(str(v)) for v in values]
    if any(not v.is_finite() for v in numbers):
        raise ValueError('Tile purchase inputs must be finite')
    areas,coverage,waste,price=numbers[:-3],*numbers[-3:]
    if any(a<0 for a in areas) or coverage<=0 or waste<0 or price<0:
        raise ValueError('Tile areas, waste and price must be nonnegative; coverage must be positive')
    installed=sum(areas)
    required=installed*(1+waste/100)
    units=int((required/coverage).to_integral_value(rounding=ROUND_CEILING))
    return {'installed_sf':float(installed),'required_sf':float(required),
            'purchase_units':units,'purchased_sf':float(units*coverage),
            'package_price':float(price),
            'pretax_material_cost':float((units*price).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)),
            'installation_area_sf':float(installed)}


def apply_purchase(draft, folder):
    root=Path(folder).resolve();path=root/'tile_material_purchase.json'
    if not path.exists():return draft
    raw=path.read_bytes();config=json.loads(raw)
    if config['plan_sha256']!=draft['plan_sha256']:raise ValueError('Tile purchase belongs to another plan')
    result=copy.deepcopy(draft);rows={r['row_id']:r for r in result['rows']};seen=set()
    for item in config['purchases']:
        identity=item['row_id']
        if identity in seen:raise ValueError('Duplicate tile purchase owner')
        seen.add(identity)
        if not item.get('sources'):raise ValueError('Tile purchase requires source evidence')
        saved_niches=[];saved_waste=[]
        for source in item['sources']:
            original=(root/source['file']).resolve()
            if not original.is_relative_to(root):
                raise ValueError('Tile purchase evidence changed')
            evidence=original.read_bytes()
            if hashlib.sha256(evidence).hexdigest()!=source['sha256']:
                raise ValueError('Tile purchase evidence changed')
            if original.suffix.lower()=='.json':
                document=json.loads(evidence)
                if document.get('plan_sha256',draft['plan_sha256'])!=draft['plan_sha256']:
                    raise ValueError('Tile purchase evidence belongs to another plan')
                for answer in document.get('answers',[])+document.get('records',[]):
                    decision=answer.get('normalized_decision',{})
                    niches=decision.get('shower_niches')
                    if niches is not None:saved_niches.append(niches)
                    if 'tile_waste_fraction' in decision:
                        fraction=decision['tile_waste_fraction']
                        if type(fraction) not in (int,float) or not Decimal(str(fraction)).is_finite() or fraction<0:
                            raise ValueError('Invalid saved owner waste')
                        saved_waste.append(Decimal(str(fraction))*100)
        if any(waste!=Decimal(str(item['waste_percent'])) for waste in saved_waste):
            raise ValueError('Tile purchase differs from saved owner waste')
        row=rows[identity]
        if (row['cost_type'] not in ('MATERIAL','ALLOWANCE') or row['unit'] not in ('sq ft','ft2','SF','each')
                or row.get('draft_quantity') is not None or row.get('covered_by_package')
                or row.get('cost_owner_row_id') or row.get('line_cost') is not None):
            raise ValueError('Tile purchase must own one unpriced material row')
        fields=row.get('assembly_inputs',[])
        if len(fields)!=1 or fields[0]['id']!=item['assembly_input_id'] or fields[0]['unit']!='SF':
            raise ValueError('Tile purchase needs its complete live installed area')
        areas=[fields[0]['quantity']]
        if 'niche_inches' in item:
            dims=item['niche_inches']
            numbers=[dims[k] for k in ('width','height','depth','count')]
            if any(type(v) not in (int,float) or not Decimal(str(v)).is_finite() or v<=0 for v in numbers) or type(dims['count']) is not int:
                raise ValueError('Niche requires positive dimensions and a whole count')
            w,h,d,n=numbers
            expected=[{'finished_width_inches':w,'finished_height_inches':h,
                       'finished_depth_inches':d,'count':n}]
            if not saved_niches or any(niches!=expected for niches in saved_niches):
                raise ValueError('Niche dimensions must match saved owner evidence')
            areas.append(n*(w*h+2*(w+h)*d)/144)
        calculated=purchase(areas,item['coverage_sf'],item['waste_percent'],item['package_price'])
        included=[]
        if item.get('niche_row_id') is not None:
            covered_id=item['niche_row_id']
            if 'niche_inches' not in item or covered_id in seen or covered_id not in rows:
                raise ValueError('Niche purchase needs one distinct included material row')
            covered=rows[covered_id]
            if (covered['cost_type'] not in ('MATERIAL','ALLOWANCE')
                    or covered.get('covered_by_package') or covered.get('cost_owner_row_id')
                    or covered.get('completion_status','').startswith('not_applicable')
                    or any(covered.get(k) is not None for k in ('unit_cost','line_cost','line_price'))):
                raise ValueError('Niche material already has pricing or another owner')
            seen.add(covered_id)
            covered.update(cost_owner_row_id=identity,pricing_role='cost_reference')
            included.append(covered_id)
        quantity=calculated['purchase_units'] if row['unit']=='each' else calculated['purchased_sf']
        reference=copy.deepcopy(fields[0])
        reference.update(quantity=quantity,unit='EA' if row['unit']=='each' else 'SF',measured_quantity=calculated['installed_sf'],
            use='template_quantity',kind='whole_tile_packages',rounding='whole_packages_after_waste',
            purchase=calculated,product_sku=item['product_sku'],sources=item['sources'],
            basis='Whole purchase units after owner waste; purchased SF is used for SF-priced rows. Niche back and four returns are pooled when specified. Installation area is retained separately.',
            order_released=False)
        if included:reference['included_row_ids']=included
        row.update(draft_quantity=quantity,quantity_sources=[reference])
    if path.read_bytes()!=raw:raise ValueError('Tile purchase configuration changed during calculation')
    result['tile_purchase_config_sha256']=hashlib.sha256(raw).hexdigest()
    return result
