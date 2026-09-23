"""Calculate retained trim intervals from measured wall lengths and exclusions.

All positions use feet along one wall face. This does not choose finish scope,
add corner/casing allowances, or turn linear feet into a purchase order.
"""
import math


def net_run(length_ft, deductions):
    if type(length_ft) not in (int,float) or not math.isfinite(length_ft) or length_ft<=0:
        raise ValueError('Wall-face length must be positive and finite')
    intervals=[];ids=set()
    for deduction in deductions:
        identity=deduction['id'];start=deduction['start_ft'];end=deduction['end_ft']
        if not isinstance(identity,str) or not identity or identity in ids:
            raise ValueError('Deduction identities must be unique and nonempty')
        ids.add(identity)
        if (any(type(v) not in (int,float) or not math.isfinite(v) for v in (start,end))
                or not 0<=start<end<=length_ft):
            raise ValueError('Deduction must lie within its measured wall face')
        intervals.append((start,end,identity))
    merged=[]
    for start,end,identity in sorted(intervals):
        if merged and start<=merged[-1]['end_ft']:
            merged[-1]['end_ft']=max(end,merged[-1]['end_ft'])
            merged[-1]['deduction_ids'].append(identity)
        else:merged.append({'start_ft':start,'end_ft':end,'deduction_ids':[identity]})
    retained=[];cursor=0
    for interval in merged:
        if interval['start_ft']>cursor:retained.append({'start_ft':cursor,'end_ft':interval['start_ft']})
        cursor=interval['end_ft']
    if cursor<length_ft:retained.append({'start_ft':cursor,'end_ft':length_ft})
    net=math.fsum(i['end_ft']-i['start_ft'] for i in retained)
    return {'gross_lf':length_ft,'deducted_lf':length_ft-net,'net_lf':net,
            'deductions':merged,'retained':retained,'purchase_quantity':None}
