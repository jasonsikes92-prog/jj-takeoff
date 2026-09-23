"""Visible parallel-stroke candidates within an explicitly selected plan view.

Neither line style nor apparent thickness proves wall meaning. These candidates
require review and must not be mapped directly to quantities for purchasing.
"""
import hashlib
import json
import math

METHOD='native_parallel_wall_strokes_v3'
DIAGONAL_METHOD='native_parallel_diagonal_wall_strokes_v1'


def face_intervals(segments,pairs):
    """Partition each pair where another same-style parallel face lies between it."""
    intervals=[]
    for pair_index,pair in enumerate(pairs):
        a,b=[segments[i] for i in pair['segments']]
        lower,upper=sorted([a['fixed'],b['fixed']])
        blockers=[(i,s) for i,s in enumerate(segments) if s['axis']==a['axis'] and s['style']==a['style']
            and lower+.001<s['fixed']<upper-.001
            and min(s['high'],pair['high'])-max(s['low'],pair['low'])>.001]
        cuts=sorted({pair['low'],pair['high']}|{max(pair['low'],s['low']) for _,s in blockers}
            |{min(pair['high'],s['high']) for _,s in blockers})
        for low,high in zip(cuts,cuts[1:]):
            if high-low<=.001:continue
            covering=[i for i,s in blockers if s['low']<(low+high)/2<s['high']]
            intervals.append({**pair,'pair_index':pair_index,'low':low,'high':high,
                'intervening_segment_indices':covering})
    return intervals


def candidates(page,points_per_foot,view_bounds_pt,allowed_styles=None,expected_depth_inches=None):
    if type(points_per_foot) not in (int,float) or not math.isfinite(points_per_foot) or points_per_foot<=0:
        raise ValueError('Positive finite calibrated view scale required')
    if expected_depth_inches is not None and (type(expected_depth_inches) not in (int,float)
            or not math.isfinite(expected_depth_inches) or expected_depth_inches<=0):
        raise ValueError('Expected wall depth must be positive and finite')
    bounds=list(view_bounds_pt)
    if (len(bounds)!=4 or any(type(v) not in (int,float) or not math.isfinite(v) for v in bounds)
            or not 0<=bounds[0]<bounds[2]<=page.rect.width
            or not 0<=bounds[1]<bounds[3]<=page.rect.height):
        raise ValueError('A valid plan-view rectangle inside the page is required')
    found={}
    styles=None if allowed_styles is None else {(tuple(s['color']),round(s['width_pt'],5)) for s in allowed_styles}
    for path,drawing in enumerate(page.get_drawings()):
        color=drawing.get('color')
        if (drawing.get('type')!='s' or color is None or min(color)>=.99
                or drawing.get('stroke_opacity',1)<=0 or drawing.get('dashes') not in ('[] 0',None)):
            continue
        style=(tuple(color),round(drawing.get('width',0),5))
        if styles is not None and style not in styles:continue
        for item,edge in enumerate(drawing['items']):
            if edge[0]!='l':continue
            a,b=edge[1:]
            axis=0 if abs(a.y-b.y)<.001 else 1 if abs(a.x-b.x)<.001 else None
            if axis is None:
                sign=1 if b.x>a.x else -1
                angle=round(math.atan2(sign*(b.y-a.y),sign*(b.x-a.x)),4)
                axis=(math.cos(angle),math.sin(angle));u=axis;v=(-u[1],u[0])
                if min(abs(component) for component in u)<1e-8:continue
                across=[sum(p[k]*v[k] for k in (0,1)) for p in (a,b)]
                if abs(across[0]-across[1])>.01:continue
                fixed=sum(across)/2;t0,t1=0.,1.
                for k in (0,1):
                    ends=sorted(((bounds[k]-a[k])/(b[k]-a[k]),(bounds[k+2]-a[k])/(b[k]-a[k])))
                    t0=max(t0,ends[0]);t1=min(t1,ends[1])
                if t1<=t0:continue
                low,high=sorted(sum((a[k]+t*(b[k]-a[k]))*u[k] for k in (0,1)) for t in (t0,t1))
            else:
                fixed=(a[1-axis]+b[1-axis])/2
                if not bounds[1-axis]<=fixed<=bounds[3-axis]:continue
                low=max(min(a[axis],b[axis]),bounds[axis])
                high=min(max(a[axis],b[axis]),bounds[axis+2])
            if high-low<=.001:continue
            key=(axis,round(fixed,5),round(low,5),round(high,5),style)
            source={'path':path,'item':item,'points_pt':[list(a),list(b)]}
            if key in found:found[key]['sources'].append(source)
            else:found[key]={'axis':axis,'fixed':fixed,'low':low,'high':high,'style':style,'sources':[source]}
    segments=list(found.values());pairs=[]
    for i,a in enumerate(segments):
        for j in range(i+1,len(segments)):
            b=segments[j]
            if a['axis']!=b['axis'] or a['style']!=b['style']:continue
            thickness=abs(a['fixed']-b['fixed'])/points_per_foot*12
            low=max(a['low'],b['low']);high=min(a['high'],b['high'])
            if 2.5-.0001<=thickness<=6+.0001 and high-low>=points_per_foot*2.5/12:
                pairs.append({'segments':[i,j],'low':low,'high':high,'thickness':thickness})
    intervals=face_intervals(segments,pairs)
    eligible={i:p for i,p in enumerate(intervals) if not p['intervening_segment_indices']
        and p['high']-p['low']>=points_per_foot*2.5/12}
    mismatched=[]
    if expected_depth_inches is not None:
        mismatched=[{'interval_index':i,**p} for i,p in eligible.items()
            if abs(p['thickness']-expected_depth_inches)>.125]
        eligible={i:p for i,p in eligible.items() if abs(p['thickness']-expected_depth_inches)<=.125}
    measurements=[];ambiguous=[];by_geometry={}
    for index,pair in eligible.items():
        conflicts=[j for j,other in eligible.items() if j!=index
            and set(pair['segments']) & set(other['segments'])
            and min(pair['high'],other['high'])-max(pair['low'],other['low'])>.001]
        if conflicts:
            ambiguous.append({'interval_index':index,'competing_interval_indices':conflicts,**pair});continue
        a,b=[segments[i] for i in pair['segments']];axis=a['axis']
        fixed=(a['fixed']+b['fixed'])/2;low,high=pair['low'],pair['high']
        short_outline=high-low<1.25*abs(a['fixed']-b['fixed'])
        diagonal=isinstance(axis,tuple)
        if diagonal:
            norm=math.hypot(*axis);u=tuple(v/norm for v in axis);v=(-u[1],u[0])
            point=lambda along,across:[along*u[k]+across*v[k] for k in (0,1)]
            lower,upper=sorted((a['fixed'],b['fixed']))
            for across in (lower,upper):
                for k in (0,1):
                    limits=sorted((bounds[edge]-across*v[k])/u[k] for edge in (k,k+2))
                    low=max(low,limits[0]);high=min(high,limits[1])
            if high-low<points_per_foot*2.5/12:continue
            short_outline=high-low<1.25*abs(a['fixed']-b['fixed'])
            outline=[point(low,lower),point(high,lower),point(high,upper),point(low,upper)]
            # Projection noise must not move the paired strip outside its source view.
            if any(not bounds[k]-.01<=p[k]<=bounds[k+2]+.01 for p in outline for k in (0,1)):continue
            points=outline if short_outline else [point(low,fixed),point(high,fixed)]
            strip=[min(p[0] for p in outline),min(p[1] for p in outline),
                   max(p[0] for p in outline),max(p[1] for p in outline)]
            key=json.dumps([page.number+1,'diagonal',sorted([round(v,5) for v in p] for p in outline)])
        else:
            points=[[low,fixed],[high,fixed]] if axis==0 else [[fixed,low],[fixed,high]]
            strip=([low,min(a['fixed'],b['fixed']),high,max(a['fixed'],b['fixed'])] if axis==0
                   else [min(a['fixed'],b['fixed']),low,max(a['fixed'],b['fixed']),high])
            if short_outline:
                x0,y0,x1,y1=strip
                points=[[x0,y0],[x1,y0],[x1,y1],[x0,y1]]
            key=json.dumps([page.number+1,[round(v,5) for v in strip]])
        sources=a['sources']+b['sources']
        if diagonal and short_outline and key not in by_geometry:
            tolerance=min(.01,points_per_foot*.001/12)
            matches=[existing for existing in measurements if existing['kind']=='area'
                and existing['source_method']==DIAGONAL_METHOD
                and all(any(math.dist(p,q)<=tolerance for q in existing['points']) for p in points)]
            if len(matches)==1:by_geometry[key]=matches[0]
        if key in by_geometry:
            existing=by_geometry[key]
            existing['source_edges'].extend(sources)
            existing['source_cad_paths']=sorted(set(existing['source_cad_paths'])|{s['path'] for s in sources})
            continue
        measurements.append({'id':'wall-stroke-'+hashlib.sha256(key.encode()).hexdigest()[:16],
            'label':f'Paired wall-face candidate {len(measurements)+1}',
            'page':page.number+1,'kind':'area' if short_outline else 'length','points':points,'points_per_foot':points_per_foot,
            'width_pt':page.rect.width,'height_pt':page.rect.height,'color':'#0e7490',
            'source_method':DIAGONAL_METHOD if diagonal else METHOD,'source_cad_paths':sorted({s['path'] for s in sources}),
            'source_edges':sources,'source_bounds_pt':strip,'view_bounds_pt':bounds,
            **({'source_outline_pt':outline,'source_direction':list(u)} if diagonal else {}),
            'drawn_thickness_inches':pair['thickness'],'orientation':'unresolved_short_piece' if short_outline else 'diagonal' if diagonal else 'horizontal' if axis==0 else 'vertical',
            'expected_depth_inches':expected_depth_inches,'depth_match_tolerance_inches':.125 if expected_depth_inches is not None else None,
            'dependent_rows':[],'certified':False,
            'scope_status':'Unreviewed parallel-stroke candidate; confirm wall meaning, layers, ends and openings'})
        by_geometry[key]=measurements[-1]
    return {'method':METHOD,'view_bounds_pt':bounds,'points_per_foot':points_per_foot,'allowed_styles':allowed_styles,
        'measurements':measurements,'segments':segments,'pair_candidates':pairs,'face_intervals':intervals,
        'length_candidates':sum(m['kind']=='length' for m in measurements),
        'short_piece_candidates':sum(m['kind']=='area' for m in measurements),
        'minimum_overlap_inches':2.5,
        'blocked_intervals':[p for p in intervals if p['intervening_segment_indices']],
        'short_unblocked_intervals':[p for p in intervals if not p['intervening_segment_indices'] and p['high']-p['low']<points_per_foot],
        'depth_mismatched_intervals':mismatched,'expected_depth_inches':expected_depth_inches,
        'depth_match_tolerance_inches':.125 if expected_depth_inches is not None else None,
        'ambiguous_pairs':ambiguous,
        'coverage_certified':False,'limitations':[
            'The selected view and its dimension-calibrated scale require source review.',
            'Only visible overlapping portions of same-style parallel line pairs at least 2.5 inches long are proposed; shorter portions remain outside the candidate search.',
            'Diagonal directions are grouped to four decimal places in radians with at most 0.01 point across-line residual; near-parallel pairs outside that envelope remain unmeasured.',
            'Pairs shorter than 1.25 times their separation retain an outline; no run direction is assigned.',
            'Parallel dimensions, equipment or finish layers can resemble walls. These are not classified walls.',
            'Intervals spanning another same-style parallel face are withheld; this identifies adjacency, not which physical layer is structural.',
            'An optional expected-depth match uses a 1/8-inch candidate search tolerance; it does not verify material, framing size or structural suitability.',
            'Competing pairs are withheld. No opening gaps, corners or missing ends are filled.',
            'Candidate thickness follows drawn stroke centerlines, not a structural member specification.']}
