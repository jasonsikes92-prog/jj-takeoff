"""Validate reviewed partitions of original invoices before package pricing."""
import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path


def _source(root, reference):
    path=(root/reference.get('source_file','')).resolve()
    if (not path.is_relative_to(root) or not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest()!=reference.get('source_sha256')):
        raise ValueError('Invoice allocation evidence is missing or changed')
    return path


def _money(value):
    try:
        amount=Decimal(str(value))
        if not amount.is_finite() or amount<=0 or amount!=amount.quantize(Decimal('.01')):
            raise ValueError('Invoice allocations require positive whole-cent amounts')
        return amount
    except InvalidOperation as exc:
        raise ValueError('Invalid invoice allocation amount') from exc


def validate_allocations(binding, quote, evidence_root):
    root=Path(evidence_root).resolve()
    ledger=json.loads(_source(root,binding).read_text(encoding='utf-8'))
    invoices={};documents=set();settlements={}
    for invoice in ledger.get('invoices',[]):
        identity=invoice.get('id');digest=invoice.get('source_sha256')
        if not identity or identity in invoices or digest in documents:
            raise ValueError('Duplicate or missing invoice identity')
        _source(root,invoice)
        if 'allocation_source' in invoice:_source(root,invoice['allocation_source'])
        parts={}
        for part in invoice.get('allocations',[]):
            part_id=part.get('id')
            if not part_id or part_id in parts:
                raise ValueError('Duplicate or missing invoice allocation identity')
            parts[part_id]=_money(part.get('amount'))
            if 'settles' in part:settlements[(identity,part_id)]=part['settles']
        if sum(parts.values(),Decimal(0))!=_money(invoice.get('total')):
            raise ValueError('Invoice allocations must reconcile to the original total')
        invoices[identity]=(invoice,parts);documents.add(digest)
    settled_totals={}
    for (identity,part_id),reference in settlements.items():
        if not isinstance(reference,dict) or set(reference)!={'invoice_id','allocation_id'}:
            raise ValueError('Settlement requires an explicit original contract allocation')
        target=(reference['invoice_id'],reference['allocation_id'])
        if (target[0] not in invoices or target[1] not in invoices[target[0]][1] or target in settlements
                or target[0]==identity or invoices[identity][1][part_id]>invoices[target[0]][1][target[1]]):
            raise ValueError('Settlement must refer to another contract amount that includes it')
        settled_totals[target]=settled_totals.get(target,Decimal(0))+invoices[identity][1][part_id]
        if settled_totals[target]>invoices[target[0]][1][target[1]]:
            raise ValueError('Combined settlements exceed the referenced contract allocation; reconcile additional scope or duplicate entries')
    claims=[];seen=set();total=Decimal(0)
    for claim in binding.get('claims',[]):
        identity=claim.get('invoice_id');part_id=claim.get('allocation_id')
        key=(identity,part_id)
        if identity not in invoices or key in seen:
            raise ValueError('Unknown or duplicate invoice allocation claim')
        invoice,parts=invoices[identity]
        if part_id not in parts:raise ValueError('Unknown invoice allocation claim')
        if key in settlements:raise ValueError('Invoice settlement is already included in its contract; do not charge it again')
        amount=parts[part_id];total+=amount;seen.add(key)
        claims.append({'invoice_id':identity,'allocation_id':part_id,'amount':str(amount),
                       'source_file':invoice['source_file'],'source_sha256':invoice['source_sha256']})
    if not claims or total!=_money(quote['quoted_total']):
        raise ValueError('Invoice allocation claims must equal the package total')
    if quote['source_sha256'] not in {claim['source_sha256'] for claim in claims}:
        raise ValueError('Primary quote document must belong to its allocation claims')
    return {'source_file':binding['source_file'],'source_sha256':binding['source_sha256'],'claims':claims}
