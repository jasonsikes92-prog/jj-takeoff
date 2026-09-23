"""Read a job's resolved stud-size assumption with its original provenance."""
import hashlib
import json
from pathlib import Path
from company_profile import resolve

KEY='framing.stud_size'
DEPTHS={'2x4':3.5,'2x6':5.5}


def read_wall_depth_basis(job,plan_sha256):
    job=Path(job).resolve();path=job/'estimate_intake.json'
    if not path.exists():return None
    raw=path.read_bytes();intake=json.loads(raw)
    if intake.get('plan_sha256')!=plan_sha256:raise ValueError('Wall-depth intake belongs to another drawing')
    name=intake.get('company_profile_snapshot')
    if not isinstance(name,str):raise ValueError('Wall-depth intake needs its company profile snapshot')
    snapshot=(job/name).resolve()
    if not snapshot.is_relative_to(job):raise ValueError('Company snapshot must be inside the job')
    profile_raw=snapshot.read_bytes();profile_sha=hashlib.sha256(profile_raw).hexdigest()
    if profile_sha!=intake.get('company_profile_sha256'):raise ValueError('Wall-depth company snapshot changed')
    resolved=resolve(json.loads(profile_raw),intake.get('project_facts'),intake.get('project_overrides'))
    size=resolved['settings'].get(KEY);provenance=resolved['provenance'].get(KEY)
    if size is not None and not isinstance(size,str):raise ValueError('Nominal stud size must be text')
    if size!=intake['settings'].get(KEY) or provenance!=intake['provenance'].get(KEY):
        raise ValueError('Saved stud-size setting differs from its resolved profile or project override')
    return {'source_rule':KEY,'nominal_stud_size':size,'depth_inches':DEPTHS.get(size),
        'provenance':provenance,'intake_sha256':hashlib.sha256(raw).hexdigest(),
        'company_profile_sha256':profile_sha,'drawing_verified':False,
        'status':('Estimating assumption for candidate matching; not proof of wall material or plan compliance'
            if size in DEPTHS else 'Stud depth unavailable or unsupported; retain unfiltered geometry candidates')}
