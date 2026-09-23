"""Keep workbook rows and unresolved-scope notes bound to one calculated draft."""
import copy
import hashlib
from measurement_store import encode
from estimate_readiness import readiness


def export_snapshot(draft, template):
    body={'draft':copy.deepcopy(draft),'readiness':readiness(draft,template)}
    return {**body,'snapshot_sha256':hashlib.sha256(encode(body).encode()).hexdigest()}


def verify_snapshot(snapshot):
    body={key:snapshot[key] for key in ('draft','readiness')}
    if hashlib.sha256(encode(body).encode()).hexdigest()!=snapshot['snapshot_sha256']:
        raise ValueError('Export snapshot content changed')
    return body
