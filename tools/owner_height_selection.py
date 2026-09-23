"""Validate an owner height choice against this plan's saved scenarios."""
import math


def select(evidence,plan_sha256,scenarios):
    matches=[s for s in scenarios if s['id']==evidence.get('selected_scenario')]
    height=evidence.get('wall_height_inches')
    if (evidence.get('source_kind')!='owner_confirmation' or evidence.get('plan_sha256')!=plan_sha256
            or type(height) not in (int,float) or not math.isfinite(height) or height<=0
            or len(matches)!=1 or matches[0]['wall_height_inches']!=height):
        raise ValueError('Height selection requires matching owner evidence and one scenario')
    return matches[0]
