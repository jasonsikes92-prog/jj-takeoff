"""Recompute unpriced cross-view window candidates from reviewed source pages."""
import hashlib
import json
from pathlib import Path
import fitz
from jnj_takeoff import window_cross_view_candidates


def sources_from_sheet_review(review):
    if not review.get('measurement_allowed',review.get('coverage_passed')):
        return None
    if review.get('measurement_scope')=='reviewed_subset':
        selected=review.get('measurement_role_pages',{})
        floors=[selected['floor']] if 'floor' in selected else []
        elevations=[selected['elevations']] if 'elevations' in selected else []
    else:
        roles=review.get('role_candidates',{})
        floors=roles.get('floor',[]);elevations=roles.get('elevations',[])
    if not floors or not elevations:return None
    return {'plan_sha256':review['plan_sha256'],'sheet_review_sha256':review['review_sha256'],
        'floor_pages':floors,'elevation_pages':elevations,
        'basis':'Window tag comparison within the reviewed measurement scope; no automatic count approval.'}


def from_plan(plan,sources):
    plan=Path(plan);digest=hashlib.sha256(plan.read_bytes()).hexdigest()
    if digest!=sources.get('plan_sha256'):raise ValueError('Window page review belongs to another drawing')
    if not sources.get('sheet_review_sha256') or not sources.get('basis'):
        raise ValueError('Window page review needs sheet-review provenance')
    with fitz.open(plan) as doc:
        groups=[sources.get(k) for k in ('floor_pages','elevation_pages')]
        if any(not isinstance(g,list) or not g for g in groups):
            raise ValueError('Window review requires floor and elevation pages')
        pages=[p for group in groups for p in group]
        if any(type(p) is not int or not 1<=p<=len(doc) for p in pages) or len(set(pages))!=len(pages):
            raise ValueError('Window source pages must be distinct valid PDF pages')
        result=window_cross_view_candidates([doc[p-1] for p in groups[0]],[doc[p-1] for p in groups[1]])
    if hashlib.sha256(plan.read_bytes()).hexdigest()!=digest:raise ValueError('Drawing changed during window review')
    return {**result,'plan_sha256':digest,'source_review':sources}


def from_folder(folder):
    folder=Path(folder);path=folder/'window_cross_view_sources.json'
    return from_plan(folder/'plan.pdf',json.loads(path.read_bytes())) if path.exists() else None
