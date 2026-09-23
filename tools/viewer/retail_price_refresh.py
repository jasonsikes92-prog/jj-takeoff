"""Prepare dated observations for existing retail products without changing scope."""
import copy
from datetime import date
import hashlib
import json
import math
from urllib.parse import urlsplit


def prepare_refresh(pricing, observations, as_of):
    """Return updated pricing and immutable evidence bytes; perform no file writes.

    Callers supply observations read from the retailer and validate the prepared
    result with price_draft before replacing the active reviewed-price file.
    Existing owner rates, tax evidence, quantities and product choices are retained.
    """
    date.fromisoformat(as_of)
    result=copy.deepcopy(pricing)
    rates={r['row_id']:r for r in result['rates']}
    if len(rates)!=len(result['rates']):raise ValueError('Duplicate existing price owners')
    seen=set(); files={}
    for item in observations:
        identity=item['row_id']; record=copy.deepcopy(item['record'])
        allowed={'date','product_id','product_name','unit','currency','unit_basis','tax_included','source',
                 'unit_price','observation_method','local_store_price_verified','availability_verified',
                 'checkout_price_verified','job_delivery_availability_verified','store','displayed_delivery_zip',
                 'displayed_store_stock','displayed_delivery_available','observed_at_utc','observation_timezone',
                 'limitation','model','store_sku'}
        if set(record)-allowed:raise ValueError('Observation contains non-observation fields')
        if identity in seen or identity not in rates:raise ValueError('Unknown or repeated retail price owner')
        seen.add(identity); previous=rates[identity]
        if previous.get('evidence_kind')!='retail_listing':raise ValueError('Refresh cannot replace an owner rate or supplier quote')
        if record.get('date')!=as_of or date.fromisoformat(previous['date'])>date.fromisoformat(as_of):
            raise ValueError('Observation must match the pricing date and cannot predate saved evidence')
        for key in ('product_id','unit','currency','unit_basis','tax_included'):
            if record.get(key)!=previous.get(key):raise ValueError('Product, purchase unit or tax basis changed: '+key)
        source=urlsplit(record.get('source','')); old_source=urlsplit(previous['source'])
        if source.scheme!='https' or source.hostname!=old_source.hostname or source.username or source.password:
            raise ValueError('Retailer source changed or is invalid')
        if source.path.rstrip('/').split('/')[-1]!=old_source.path.rstrip('/').split('/')[-1]:
            raise ValueError('Retail product URL changed')
        for key in ('product_name','unit_basis','observation_method'):
            if not isinstance(record.get(key),str) or not record[key].strip():raise ValueError('Missing observation '+key)
        amount=record.get('unit_price')
        if type(amount) not in (int,float) or not math.isfinite(amount) or amount<0:
            raise ValueError('Observed price must be finite and nonnegative')
        for key in ('local_store_price_verified','availability_verified','checkout_price_verified','job_delivery_availability_verified'):
            if type(record.get(key)) is not bool:raise ValueError('Observation must state verification limits: '+key)
        raw=(json.dumps(record,indent=2,allow_nan=False)+'\n').encode('utf-8')
        digest=hashlib.sha256(raw).hexdigest()
        filename=f'retail_observation_{as_of}_{digest}.json'
        files[filename]=raw
        # Clear optional availability details from an earlier observation.
        for key in ('store','displayed_delivery_zip','displayed_store_stock','displayed_delivery_available',
                    'observed_at_utc','observation_timezone','limitation','model','store_sku'):
            previous.pop(key,None)
        previous.update(record)
        previous.update(row_id=identity,evidence_kind='retail_listing',pricing_basis='unit_rate',
                        validity_policy='observation_date_only',valid_through=as_of,
                        scope_reviewed=True,source_file=filename,source_sha256=digest)
    return result, files
