"""Locate printed room labels inside derived interior regions without selecting finishes."""
import copy
import hashlib
import json
import re
from pathlib import Path
import fitz
from shapely.geometry import Polygon,box
from wall_enclosure_candidates import from_folder as wall_enclosures
from room_opening_connections import connections
from room_use_review import apply as apply_room_uses,read_review as room_use_review
from room_use_candidates import apply as infer_room_uses
from ceiling_note_candidates import page_notes,attach as attach_ceiling_notes
from ceiling_surface_review import apply as apply_ceiling_surfaces,read_review as ceiling_surface_review
from room_wall_surfaces import attach as attach_wall_surfaces

ROOM_LABEL=re.compile(r'(?:(?:MASTER|PRIMARY|GUEST) )?(?:BEDROOM|BED|BATHROOM|BATH|CLOSET)|'
    r'LIVING(?: ROOM)?|DINING(?: ROOM)?|KITCHEN|PANTRY|OFFICE|STUDY|LAUNDRY(?: ROOM)?|'
    r'UTILITY(?: ROOM)?|MUDROOM|FOYER|HALL(?:WAY)?|GARAGE|BONUS(?: ROOM)?|PLAYROOM|'
    r'FAMILY(?: ROOM)?|STORAGE|POWDER(?: ROOM)?|WC|WIC')


def page_labels(page):
    labels=[]
    for block in page.get_text('dict')['blocks']:
        for line in block.get('lines',[]):
            raw=''.join(span['text'] for span in line['spans']).strip()
            normalized=' '.join(raw.upper().split())
            name=re.sub(r'\s*#?\s*\d+$','',normalized).strip()
            if not ROOM_LABEL.fullmatch(name):continue
            bounds=list(line['bbox']);identity=hashlib.sha256(json.dumps([page.number+1,raw,bounds]).encode()).hexdigest()[:16]
            labels.append({'id':'room-label-'+identity,'page':page.number+1,'text':raw,'bounds_pt':bounds})
    return labels


def associate(enclosures,labels):
    regions=copy.deepcopy(enclosures['interior_region_candidates'])
    shapes={r['id']:Polygon(r['points'],r['holes']) for r in regions}
    if len(shapes)!=len(regions) or len({l['id'] for l in labels})!=len(labels):
        raise ValueError('Room regions and labels need unique source identities')
    matches={r['id']:[] for r in regions};unresolved=[]
    for label in labels:
        extent=box(*label['bounds_pt'])
        contained=[r['id'] for r in regions if r['page']==label['page'] and shapes[r['id']].covers(extent)]
        if len(contained)==1:matches[contained[0]].append(copy.deepcopy(label))
        else:
            intersects=[r['id'] for r in regions if r['page']==label['page'] and shapes[r['id']].intersects(extent)]
            unresolved.append({**label,'candidate_region_ids':intersects,
                'reason':'Label spans multiple or overlapping regions' if len(contained)>1 or len(intersects)>1
                    else 'Label touches a boundary or has no enclosed region'})
    for region in regions:
        attached=matches[region['id']];region['printed_labels']=attached
        boundary=shapes[region['id']].boundary
        uncertain=[copy.deepcopy(u) for u in enclosures.get('unresolved_wall_sources',[])
            if (u.get('page'),u.get('points_per_foot'))==(region['page'],region['points_per_foot'])
            and any(bounds and boundary.intersects(box(*bounds)) for bounds in (u.get('current_bounds_pt'),u.get('original_bounds_pt')))]
        if uncertain:region['boundary_source_issues']=uncertain
        region['association_status']=('single_printed_label' if len(attached)==1 else
            'multiple_labels_one_region' if attached else 'no_printed_room_label')
        region['room_use_confirmed']=False;region['finish_selection']=None
        region['association_review']=('Check whether these labels describe open-plan space or incomplete separating walls'
            if len(attached)>1 else 'Room use and finish limits require review' if attached else
            'No room use inferred for this unlabeled region')
    linked=connections(enclosures,regions)
    identity={'enclosure_source_sha256':enclosures['source_sha256'],'regions':regions,'labels':labels,'opening_connections':linked}
    return {'plan_sha256':enclosures['plan_sha256'],'measurement_version':enclosures['measurement_version'],
        'method':'printed_room_labels_in_wall_regions_v2',
        'source_sha256':hashlib.sha256(json.dumps(identity,sort_keys=True,allow_nan=False).encode()).hexdigest(),
        'regions':regions,'opening_connections':linked,'unresolved_labels':unresolved,'whole_floor_finish_quantity':None,'certified':False,
        'unresolved_wall_measurements':copy.deepcopy(enclosures.get('unresolved_wall_measurements',[])),
        'unresolved_gap_ids':list(enclosures.get('unresolved_gap_ids',[])),
        'limitations':['Printed labels are location candidates, not verified room use or finish selections.',
            'Several labels in one connected region do not create several quantities or justify dividing its area.',
            'Unlabeled regions remain visible; a closet, toilet room or circulation space is not guessed.',
            'Virtual opening closures, cabinetry, fixtures and material transitions require finish-scope review.',
            'Only supported native text labels are located; scanned or unfamiliar labels remain outside this matcher.']}


def from_folder(folder,state,include_surfaces=True):
    folder=Path(folder);plan=folder/'plan.pdf';enclosures=wall_enclosures(folder,state)
    if hashlib.sha256(plan.read_bytes()).hexdigest()!=state['plan_sha256']:
        raise ValueError('Room labels belong to a changed drawing')
    pages=sorted({r['page'] for r in enclosures['interior_region_candidates']})
    with fitz.open(plan) as doc:
        labels=[label for page in pages for label in page_labels(doc[page-1])]
        ceiling_notes=[note for page in pages for note in page_notes(doc[page-1])]
        rooms=infer_room_uses(apply_room_uses(associate(enclosures,labels),room_use_review(folder)))
        from equipment_room_candidates import apply as equipment_rooms
        rooms=equipment_rooms(rooms,doc)
        from closet_room_candidates import apply as closet_rooms
        rooms=closet_rooms(rooms,doc)
    if hashlib.sha256(plan.read_bytes()).hexdigest()!=state['plan_sha256']:
        raise ValueError('Drawing changed during room-label extraction')
    if not include_surfaces:return rooms
    rooms=attach_ceiling_notes(rooms,ceiling_notes)
    return attach_wall_surfaces(apply_ceiling_surfaces(rooms,ceiling_surface_review(folder)))
