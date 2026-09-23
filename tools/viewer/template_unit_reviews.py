"""Apply explicitly sourced unit corrections without rewriting the source template."""
import copy
import hashlib
import json
from pathlib import Path


def reviewed_template(template, config, folder, plan_sha256):
    root = Path(folder).resolve()
    if (config.get('plan_sha256') != plan_sha256 or config.get('reviewed') is not True
            or hashlib.sha256((root / 'template_rows.json').read_bytes()).hexdigest()
            != config.get('template_rows_sha256')):
        raise ValueError('Template unit review needs the matching plan and original template')
    result = copy.deepcopy(template)
    rows = {r['row_id']: r for r in result['rows']}
    seen = set()
    for review in config['corrections']:
        identity = review['row_id']
        if identity in seen or identity not in rows:
            raise ValueError('Unit correction target missing or duplicated')
        seen.add(identity)
        row = rows[identity]
        if (any(row.get(k) != review.get(k) for k in ('name', 'cost_type'))
                or row.get('unit') != review.get('original_unit')
                or row.get('completion_status', '').startswith('not_applicable')
                or review.get('unit') not in ('LF', 'SF', 'EA') or not review.get('basis')
                or row['cost_type'] not in ('ASSEMBLY', 'ALLOWANCE', 'MATERIAL', 'SUBCONTRACTOR', 'LABOR')):
            raise ValueError('Unit correction must identify an applicable row and its original unit')
        source = review['source']
        path = (root / source['file']).resolve()
        if (not path.is_relative_to(root) or not path.is_file()
                or hashlib.sha256(path.read_bytes()).hexdigest() != source.get('sha256')):
            raise ValueError('Unit correction source missing or changed')
        try:
            value = json.loads(path.read_bytes())
            pointer = source['json_pointer']
            if not isinstance(pointer, str) or not pointer.startswith('/'):
                raise ValueError('Unit source requires an explicit JSON pointer')
            for token in pointer[1:].split('/'):
                token = token.replace('~1', '/').replace('~0', '~')
                if isinstance(value, list):
                    if not token.isdecimal() or str(int(token)) != token:
                        raise ValueError('Invalid unit source array index')
                    value = value[int(token)]
                else:
                    value = value[token]
        except (KeyError, IndexError, TypeError) as error:
            raise ValueError('Unit source location is missing or invalid') from error
        if value != review['unit']:
            raise ValueError('Unit correction does not match the saved answer')
        row['unit'] = review['unit']
        row['unit_review'] = copy.deepcopy(review)
    return result
