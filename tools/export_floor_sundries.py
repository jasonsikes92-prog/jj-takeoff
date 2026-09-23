"""Export pooled draft purchases for separate measured fields sharing products."""
import argparse
import hashlib
import json
from pathlib import Path
from shapely.geometry import shape
from floor_sundries import calculate_pooled_allowance


def export(input_path,output):
    input_path=Path(input_path);output=Path(output)
    if output.exists():raise FileExistsError('Existing purchase calculation preserved; choose a new output')
    raw=input_path.read_bytes();source=json.loads(raw)
    if source.get('coordinate_unit')!='feet' or not source.get('plan_sha256'):
        raise ValueError('Measured field input needs feet coordinates and a drawing hash')
    if type(source.get('measurement_version')) is not int or source['measurement_version']<1:
        raise ValueError('Measured field input needs a positive measurement revision')
    fields=[]
    for field in source['fields']:
        if not field.get('measurement_ids') or not field.get('basis'):
            raise ValueError('Each separate field needs measurement IDs and an installation basis')
        fields.append({'id':field['id'],'geometry':shape(field['geometry_ft'])})
    result=calculate_pooled_allowance(fields,source['products'])
    result.update(plan_sha256=source['plan_sha256'],measurement_version=source['measurement_version'],
        input_sha256=hashlib.sha256(raw).hexdigest(),input_file=str(input_path.resolve()),
        field_sources=[{k:f[k] for k in ('id','measurement_ids','basis')} for f in source['fields']],
        source_geometry_independently_certified=False,published_to_estimate=False)
    if input_path.read_bytes()!=raw:raise ValueError('Measured fields or products changed during calculation')
    with output.open('x',encoding='utf-8') as stream:
        stream.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True,type=Path);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();result=export(args.input,args.output)
    print(json.dumps({'fields':len(result['fields']),'partial_pretax_cost':result['partial_pretax_cost'],
                      'order_released':False,'output':str(args.output.resolve())}))


if __name__=='__main__':main()
