"""Recognize supported native door symbols without approving opening roles."""
import hashlib
import json
import math
from pocket_symbol_candidates import pocket_matches
from sliding_symbol_candidates import sliding_matches


def validate_arc(points,center,radius,scale):
    """Check a swing about the drawn leaf hinge, avoiding unstable short-arc fits."""
    if len(points)<5:return None
    if any(len(p)!=2 or not all(math.isfinite(v) for v in p) for p in points):return None
    residual=max(abs(math.dist(p,center)-radius) for p in points)
    if not scale*(1-1e-9)<=radius<=scale*(4+1e-9) or residual>scale*.15/12:return None
    angles=[math.atan2(p[1]-center[1],p[0]-center[0]) for p in points]
    steps=[math.atan2(math.sin(b-a),math.cos(b-a)) for a,b in zip(angles,angles[1:])]
    sweep=abs(sum(steps))*180/math.pi
    if not 15<=sweep<=110 or not (all(s>0 for s in steps) or all(s<0 for s in steps)):return None
    # Corners on a coarse polygon must not masquerade as a swing curve.
    if max(map(abs,steps))*180/math.pi>12:return None
    return {'center_pt':center,'radius_pt':radius,'radial_residual_pt':residual,
            'sweep_degrees':sweep,'points_pt':points}


def paths_from_drawings(drawings):
    lines=[];curves=[]
    for index,drawing in enumerate(drawings):
        if (drawing.get('type') not in ('s','fs') or drawing.get('stroke_opacity',1)<=0
                or (drawing.get('color') and min(drawing['color'])>=.99)
                or drawing.get('dashes') not in (None,'[] 0')):continue
        chain=[]
        def finish():
            if len(chain)>=5:curves.append({'drawing_index':index,'points':chain[:]})
            chain.clear()
        for item in drawing['items']:
            if item[0] in ('re','qu'):
                finish();shape=item[1]
                vertices=([shape.tl,shape.tr,shape.br,shape.bl] if item[0]=='re'
                    else [shape.ul,shape.ur,shape.lr,shape.ll])
                lines.extend({'drawing_index':index,'points':[list(a),list(b)]}
                    for a,b in zip(vertices,vertices[1:]+vertices[:1]))
                continue
            if item[0]!='l':finish();continue
            a,b=list(item[1]),list(item[2]);lines.append({'drawing_index':index,'points':[a,b]})
            if chain and math.dist(chain[-1],a)>.02:finish()
            if not chain:chain.append(a)
            chain.append(b)
        finish()
    return lines,curves


def swing_matches(gap,width,scale,lines,curves):
    matches=[];tolerance=scale*3/12
    for curve in curves:
        if min(math.dist(p,g) for p in (curve['points'][0],curve['points'][-1]) for g in gap)>tolerance:continue
        endpoints=(curve['points'][0],curve['points'][-1])
        for line in lines:
            radius=math.dist(*line['points'])
            if abs(radius/scale*12-width)>1:continue
            for center,leaf_end in (line['points'],line['points'][::-1]):
                hinge=min(range(2),key=lambda n:math.dist(center,gap[n]))
                if math.dist(center,gap[hinge])>tolerance:continue
                closed=min(range(2),key=lambda n:math.dist(endpoints[n],gap[1-hinge]))
                if math.dist(endpoints[closed],gap[1-hinge])>tolerance:continue
                if math.dist(leaf_end,endpoints[1-closed])>scale*.25/12:continue
                arc=validate_arc(curve['points'],center,radius,scale)
                if not arc:continue
                candidate={**arc,'configuration':'single_hinged','method':'native_polyline_swing_and_leaf_at_tagged_gap',
                    'arc_drawing_index':curve['drawing_index'],'leaf_lines':[line],
                    'hinge_gap_endpoint':hinge,'closed_arc_endpoint':closed,
                    'hinge_offset_inches':math.dist(center,gap[hinge])/scale*12,
                    'closed_endpoint_offset_inches':math.dist(endpoints[closed],gap[1-hinge])/scale*12}
                if not any(math.dist(center,m['center_pt'])<.02 and math.dist(leaf_end,m['points_pt'][-1 if m['closed_arc_endpoint']==0 else 0])<.02 for m in matches):
                    matches.append(candidate)
    return matches


def double_swing_matches(gap,width,scale,lines,curves):
    middle=[(a+b)/2 for a,b in zip(*gap)]
    left=swing_matches([gap[0],middle],width/2,scale,lines,curves)
    right=swing_matches([middle,gap[1]],width/2,scale,lines,curves)
    direction=[b-a for a,b in zip(*gap)]
    def side(m):
        tip=m['points_pt'][-1 if m['closed_arc_endpoint']==0 else 0]
        return direction[0]*(tip[1]-m['center_pt'][1])-direction[1]*(tip[0]-m['center_pt'][0])
    pairs=[]
    for a in left:
        for b in right:
            if a['hinge_gap_endpoint']!=0 or b['hinge_gap_endpoint']!=1 or side(a)*side(b)<=0:continue
            closed_a=a['points_pt'][0 if a['closed_arc_endpoint']==0 else -1]
            closed_b=b['points_pt'][0 if b['closed_arc_endpoint']==0 else -1]
            if math.dist(closed_a,closed_b)>scale*.25/12:continue
            pairs.append({'configuration':'double_hinged','method':'native_opposed_hinges_with_meeting_swing_arcs',
                'leaves':[a,b],'drawn_panel_count':2})
    return pairs


def recognize(openings,drawings_by_page,plan_sha256):
    output=[]
    pages={page:paths_from_drawings(drawings) for page,drawings in drawings_by_page.items()}
    for opening in openings:
        nominal=opening.get('printed_nominal_size');matches=[]
        scale=opening.get('points_per_foot')
        if (not nominal or nominal.get('type_code') or not 12<=nominal['width_inches']<=96
                or not 60<=nominal['height_inches']<=120 or not isinstance(scale,(int,float)) or scale<=0):
            continue
        gap=opening['points'];lines,curves=pages.get(opening['page'],([],[]))
        width=nominal['width_inches']
        if abs(math.dist(*gap)/scale*12-width)>3:continue
        if width<=48:
            matches.extend(swing_matches(gap,width,scale,lines,curves))
            matches.extend(pocket_matches(gap,width,scale,lines))
        if width>=24:
            matches.extend(double_swing_matches(gap,width,scale,lines,curves))
        if width>=48:
            matches.extend(sliding_matches(gap,width,scale,lines))
        if not matches:continue
        binding={'plan_sha256':plan_sha256,'opening_source_sha256':opening['source_sha256'],
            'opening_points':gap,'scale':scale,'tag':opening['tag'],'matches':matches}
        current=opening['review_status']=='current_source_review'
        configuration=matches[0]['configuration'] if len(matches)==1 else None
        panels=2 if configuration in ('double_hinged','sliding_pair') else 1
        roles=(('special_interior_door',) if configuration=='pocket' else ('special_interior_door','exterior_door')
            if configuration in ('sliding_pair','double_hinged') else ('interior_door','exterior_door'))
        configurations=('sliding','bypass') if configuration=='sliding_pair' else (configuration,)
        corroborates=current and opening.get('door_configuration') in configurations and opening.get('drawn_panel_count')==panels
        conflict=current and (opening.get('role') not in roles
            or opening.get('door_configuration') not in (None,*configurations)
            or opening.get('drawn_panel_count') not in (None,panels))
        output.append({'opening_id':opening['opening_id'],'page':opening['page'],'tag':opening['tag'],
            'source_sha256':hashlib.sha256(json.dumps(binding,sort_keys=True,allow_nan=False).encode()).hexdigest(),
            'opening_source_sha256':opening['source_sha256'],'method':matches[0]['method'] if len(matches)==1 else 'competing_native_door_symbols',
            'configuration_candidate':configuration if not conflict else None,
            'drawn_panel_count_candidate':panels if len(matches)==1 and not conflict else None,
            'status':'ambiguous_symbols' if len(matches)>1 else 'conflicts_with_review' if conflict else
                'corroborates_review' if corroborates else 'stale_review_requires_reconciliation' if opening['review_status']=='stale_source_review' else 'candidate_requires_review',
            'matches':matches,'role_confirmed':False,'product_fit_verified':False,'purchase_released':False})
    return {'candidates':output,'coverage_certified':False,'purchase_released':False,
        'limitations':['Recognizes supported native single/paired swings, offset sliding panels and partially retracted pocket leaves at tagged gaps; it is not complete opening enumeration.',
            'A sliding-pair symbol alone does not establish an exterior sliding unit versus an interior bypass assembly.',
            'Door role, room assignment, handedness, product fit and final configuration still need source review.',
            'Missing symbols do not establish a wall, window, zero doors or excluded scope. Existing reviewed decisions are unchanged.']}


def from_plan(plan,openings,plan_sha256):
    import fitz
    if hashlib.sha256(plan.read_bytes()).hexdigest()!=plan_sha256:raise ValueError('Door symbol drawing source changed')
    with fitz.open(plan) as document:
        pages={page:document[page-1].get_drawings() for page in sorted({o['page'] for o in openings}) if 1<=page<=len(document)}
    return recognize(openings,pages,plan_sha256)
